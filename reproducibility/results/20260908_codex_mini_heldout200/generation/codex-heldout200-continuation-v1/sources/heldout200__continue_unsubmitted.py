"""Continue only held-out cells that never created an original turn archive.

The ``freeze`` command is intentionally unusable until the original parent
and every shard have terminal statuses.  The ``run`` command requires the
resulting immutable manifest and refuses any changed source or archive.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable

from .. import codex_subscription as c
from ..record_codex_runtime import capture

TERMINAL = {"completed", "blocked"}
DEPENDENCIES = ("codex_subscription.py", "factorial_runner.py", "audit_codex_pilot.py",
                "record_codex_runtime.py", "benchmark_bridge.py",
                "heldout200/generate.py", "heldout200/analyze.py",
                "heldout200/continue_unsubmitted.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def tree_snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root).as_posix()): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def state(path: Path) -> str | None:
    return read_json(path).get("state") if path.is_file() else None


def original_inventory(parent: Path) -> dict[str, Any]:
    status_path = parent / "status.json"
    parent_state = state(status_path)
    if parent_state not in TERMINAL:
        raise ValueError("original parent archive is not terminal")
    root_plan = read_json(parent / "manifest.json")
    expected_shards = {s["name"]: s for s in root_plan.get("shards", [])}
    shards = []
    for shard in sorted((parent / "shards").iterdir()):
        if not shard.is_dir():
            continue
        shard_state = state(shard / "status.json")
        if shard_state not in TERMINAL:
            raise ValueError(f"original shard is not terminal: {shard.name}")
        completion = parent / "inputs" / shard.name / "completion.json"
        if not completion.is_file():
            raise ValueError(f"missing complete shard inventory: {shard.name}")
        manifest = read_json(shard / "manifest.json")
        cells = manifest.get("cells", [])
        if shard.name not in expected_shards or manifest != expected_shards[shard.name].get("manifest"):
            raise ValueError(f"shard manifest differs from frozen parent plan: {shard.name}")
        cell_ids = {c["id"] for c in cells}
        for cell_file in (shard / "cells").glob("*.json"):
            if cell_file.stem not in cell_ids or not cell_started(shard, cell_file.stem):
                raise ValueError(f"cell archive has no corresponding turn: {shard.name}/{cell_file.name}")
        for turn in (shard / "turns").iterdir():
            match = re.fullmatch(r"(.+)-(\d+)", turn.name)
            if not match or match.group(1) not in cell_ids:
                raise ValueError(f"unexpected original turn directory: {shard.name}/{turn.name}")
        shards.append({
            "name": shard.name,
            "state": shard_state,
            "cells": cells,
            "cell_count": len(cells),
            "turn_directories": sorted(p.name for p in (shard / "turns").iterdir()) if (shard / "turns").exists() else [],
            "tree_sha256": c.digest(tree_snapshot(shard)),
            "archive_tree": tree_snapshot(shard),
            "manifest_sha256": sha(shard / "manifest.json"),
            "completion_sha256": sha(completion),
        })
    if len(shards) != 4 or set(expected_shards) != {s["name"] for s in shards}:
        raise ValueError("expected four original shard inventories")
    return {"parent_state": parent_state, "parent_tree": tree_snapshot(parent), "shards": shards}


def cell_started(shard: Path, cell_id: str) -> bool:
    turns = shard / "turns"
    return turns.exists() and any(p.is_dir() and p.name.startswith(cell_id + "-") for p in turns.iterdir())


def pending_cells(parent: Path, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    pending = []
    for record in inventory["shards"]:
        shard = parent / "shards" / record["name"]
        for cell in record["cells"]:
            if not cell_started(shard, cell["id"]):
                pending.append({**cell, "shard": record["name"]})
    return pending


def freeze(tasks: Path, parent: Path, protocol: Path, source_root: Path, out: Path) -> dict[str, Any]:
    if out.exists():
        raise ValueError("refuse to overwrite continuation manifest")
    inventory = original_inventory(parent)
    task_rows = c.tasks_from(tasks)
    original_tasks = parent / "tasks.json"
    if not original_tasks.is_file() or c.digest(task_rows) != c.digest(sorted(read_json(original_tasks), key=lambda t: t["task_id"])):
        raise ValueError("continuation tasks differ semantically from original parent tasks")
    task_bytes = sha(tasks)
    dependency_paths = {name: source_root / name for name in DEPENDENCIES}
    dependencies = {name: sha_lf(path) for name, path in dependency_paths.items()}
    pending = pending_cells(parent, inventory)
    body = {
        "schema": "codex-heldout200-continuation-v1",
        "protocol_sha256": sha(protocol),
        "original_parent_archive_sha256": c.digest(inventory["parent_tree"]),
        "original_parent_manifest_sha256": sha(parent / "manifest.json"),
        "original_control_gate_sha256": sha(parent / "control-gate.json") if (parent / "control-gate.json").is_file() else None,
        "original_parent_plan": read_json(parent / "manifest.json"),
        "original_inventory": inventory,
        "tasks_sha256": task_bytes,
        "dependency_sha256": dependencies,
        "source_root": str(source_root.resolve()),
        "pending_cells": pending,
        "pending_count": len(pending),
        "workers_per_shard": 2,
        "max_shards": 4,
        "timeout_seconds": 180,
        "no_retry": True,
        "allocation_exhausted": len(pending) == 0,
    }
    result = {**body, "manifest_sha256": c.digest(body)}
    c.save(out, result)
    return result


def validate_frozen(manifest: dict[str, Any], tasks: Path, parent: Path, protocol: Path, source_root: Path) -> None:
    if sha(tasks) != manifest["tasks_sha256"] or sha(protocol) != manifest["protocol_sha256"]:
        raise ValueError("frozen task/protocol source changed")
    frozen_body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if c.digest(frozen_body) != manifest["manifest_sha256"]:
        raise ValueError("continuation manifest hash changed")
    current = original_inventory(parent)
    if c.digest(current["parent_tree"]) != manifest["original_parent_archive_sha256"]:
        raise ValueError("original parent archive changed")
    for name, digest in manifest["dependency_sha256"].items():
        if sha_lf(source_root / name) != digest:
            raise ValueError(f"frozen dependency changed: {name}")
    now = pending_cells(parent, current)
    if now != manifest["pending_cells"]:
        raise ValueError("pending cell inventory changed")


def run_shard_cells(
    shard_name: str,
    cells: list[dict[str, Any]],
    tasks_by_id: dict[str, dict[str, Any]],
    archive: Path,
    prefix: list[str],
    instructions: Path,
    workers: int = 2,
    timeout: int = 180,
    transport: Callable[..., dict[str, Any]] = c.archive_turn,
    stop: threading.Event | None = None,
    progress_path: Path | None = None,
    progress_lock: threading.Lock | None = None,
    submit_counter: list[int] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stop = stop or threading.Event()
    shard_out = (archive / "shards" / shard_name).resolve()
    shard_out.mkdir(parents=True, exist_ok=False)
    (shard_out / "turns").mkdir()
    (shard_out / "cells").mkdir()
    (shard_out / "empty").mkdir()
    if runtime_context is None and transport is c.archive_turn:
        raise ValueError('Production transport requires archived child runtime provenance')
    child_instructions = shard_out / 'instructions.txt'
    child_instructions.write_bytes(c.BASE.encode('utf-8'))
    if runtime_context is not None:
        original = archive / 'original-shards' / shard_name
        for name in ('manifest.json', 'tasks.json'):
            shutil.copyfile(original / name, shard_out / name)
        c.save(shard_out / 'continuation_cells.json', [{k:v for k,v in cell.items() if k != 'shard'} for cell in cells])
        parent_runtime = c.read(archive / 'runtime.json')
        c.save(shard_out / 'runtime.json', {**parent_runtime, 'started_unix': time.time()})
        capture(shard_out, Path(runtime_context['npm_root']), Path(c.__file__))
    c.save(shard_out / 'status.json', {'state':'started', 'assigned_generations':len(cells), 'started_unix':time.time()})
    command = c.cli_command(prefix, (shard_out / "empty").resolve(), child_instructions.resolve())
    q: queue.Queue[dict[str, Any]] = queue.Queue()
    for cell in cells:
        q.put(cell)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    lock = threading.Lock()

    def worker() -> None:
        while not stop.is_set():
            try:
                cell = q.get_nowait()
            except queue.Empty:
                return
            try:
                history: list[str] = []
                turns: list[dict[str, Any]] = []
                for stage in range(cell["cli_turns"]):
                    prompt = c.prompt_for(tasks_by_id[cell["task_id"]], cell, stage, history)
                    if progress_path is not None and progress_lock is not None and submit_counter is not None:
                        with progress_lock:
                            submit_counter[0] += 1
                            with progress_path.open("a", encoding="utf-8") as event_file:
                                event_file.write(json.dumps({"event": "cell_submit", "order": submit_counter[0], "shard": shard_name, "cell": cell["id"], "stage": stage, "started_unix": time.time()}) + "\n")
                    result = transport(shard_out / "turns" / f"{cell['id']}-{stage}", command, prompt, timeout)
                    history.append(result["final_text"])
                    turns.append(result)
                usage = {k: sum(t["usage"][k] for t in turns) for k in ("input_tokens", "cached_input_tokens", "output_tokens")}
                reasoning = [t["usage"].get("reasoning_output_tokens") for t in turns]
                usage["reasoning_output_tokens"] = sum(reasoning) if all(v is not None for v in reasoning) else None
                row = {**cell, "model": c.MODEL, "seed": cell["replicate_id"], "seed_field_semantics": "replicate label only; CLI sampling seed not set", "final_text": history[-1], "usage": usage, "total_tokens": usage["input_tokens"] + usage["output_tokens"], "api_equivalent_usd": sum(t["api_equivalent_usd"] for t in turns), "uncached_sensitivity_usd": sum(t["uncached_sensitivity_usd"] for t in turns), "wall_seconds": sum(t["wall_seconds"] for t in turns), "actual_api_charge_usd": None}
                c.save(shard_out / "cells" / f"{cell['id']}.json", row)
                with lock: rows.append(row)
            except Exception as exc:
                reason = str(exc)
                with lock: failures.append({"cell": cell["id"], "reason": reason})
                if _failure_stops(reason, shard_out / "turns" / f"{cell['id']}-{max(0, len(history))}"): stop.set()
            finally:
                q.task_done()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda _: worker(), range(workers)))
    rows.sort(key=lambda r: r["id"])
    (shard_out / "results.jsonl").write_bytes(b"".join(c.canonical(r) + b"\n" for r in rows))
    attempted = len({f["cell"] for f in failures}) + len(rows)
    status = {"state": "completed" if not failures and len(rows) == len(cells) else "blocked", "assigned_generations": len(cells), "attempted_generations": attempted, "completed_generations": len(rows), "failures": failures, "allocation_exhausted": attempted == len(cells) and not stop.is_set()}
    c.save(shard_out / "status.json", status)
    return status


def _failure_stops(reason: str, turn_folder: Path) -> bool:
    text = reason.lower()
    if "timeout" in text or "full input exceeds" in text or "byte guard" in text:
        return False
    evidence = ""
    for name in ("stderr.txt", "events.jsonl"):
        p = turn_folder / name
        if p.exists(): evidence += p.read_text(encoding="utf-8", errors="replace").lower()
    if any(t in evidence for t in ('quota', 'usage limit', 'rate limit', 'unauthorized', 'authentication', '401', '403')):
        return True
    known_transport = ("stream disconnected before completion", "transport error: network error",
                       "error decoding response body")
    if any(t in evidence for t in known_transport):
        return False
    # Quota/auth and every unclassified provider error conservatively stop the
    # continuation; the cell that created the archive is never retried.
    return True


def run(tasks: Path, parent: Path, protocol: Path, source_root: Path, manifest_path: Path, archive: Path, npm_root: Path, max_shards: int = 4) -> dict[str, Any]:
    tasks, parent, protocol, source_root, manifest_path, archive, npm_root = [p.resolve() for p in (tasks, parent, protocol, source_root, manifest_path, archive, npm_root)]
    manifest = read_json(manifest_path)
    validate_frozen(manifest, tasks, parent, protocol, source_root)
    if archive.exists():
        raise ValueError("refuse to overwrite continuation archive")
    archive.mkdir(parents=True)
    c.save(archive / "manifest.json", manifest)
    c.save(archive / "tasks.json", [json.loads(x) for x in tasks.read_text(encoding="utf-8-sig").splitlines() if x.strip()])
    (archive / "protocol.md").write_bytes(protocol.read_bytes())
    (archive / "original-parent-inventory.json").write_text(json.dumps(manifest["original_inventory"], indent=2) + "\n", encoding="utf-8")
    if (parent / "control-gate.json").is_file(): (archive / "original-control-gate.json").write_bytes((parent / "control-gate.json").read_bytes())
    (archive / "sources").mkdir()
    for name in DEPENDENCIES:
        target = archive / "sources" / name.replace("/", "__")
        target.write_bytes((source_root / name).read_bytes())
    for record in manifest["original_inventory"]["shards"]:
        src = parent / "shards" / record["name"]
        dst = archive / "original-shards" / record["name"]
        dst.mkdir(parents=True)
        for name in ("manifest.json", "tasks.json", "runtime.json", "instructions.txt"):
            if (src / name).is_file(): shutil.copyfile(src / name, dst / name)
        inp = parent / "inputs" / record["name"]
        if (inp / "tasks.jsonl").is_file(): shutil.copyfile(inp / "tasks.jsonl", dst / "tasks.jsonl")
    (archive / "empty").mkdir()
    (archive / "turns").mkdir()
    (archive / "cells").mkdir()
    if not 1 <= max_shards <= 4: raise ValueError("max_shards must be between one and four")
    node = shutil.which("node")
    expected_entry = npm_root.resolve() / "node_modules/@openai/codex/bin/codex.js"
    if not node or not expected_entry.is_file(): raise ValueError("official Codex Node entry missing from explicit npm root")
    prefix = [node, str(expected_entry)]
    version = subprocess.check_output(prefix + ["--version"], text=True).strip()
    if version != c.CLI_VERSION: raise ValueError("frozen CLI version mismatch")
    auth = subprocess.run(prefix + ["login", "status"], capture_output=True, text=True)
    if auth.returncode or "ChatGPT" not in auth.stdout + auth.stderr:
        raise ValueError("ChatGPT subscription login required")
    instructions = archive / "instructions.txt"; instructions.write_bytes(c.BASE.encode())
    c.save(archive / "runtime.json", {"version": version, "prefix": prefix,
                                       "authentication": "chatgpt", "workers": 2,
                                       "timeout_seconds": 180, "started_unix": time.time()})
    capture(archive, npm_root, Path(c.__file__))
    stop = threading.Event(); task_rows = c.tasks_from(tasks); by_id = {t["task_id"]: t for t in task_rows}
    c.save(archive / "status.json", {"state": "started", "started_unix": time.time(), "assigned_generations": manifest["pending_count"], "max_shards": max_shards})
    progress = archive / "progress.jsonl"; progress_lock = threading.Lock(); submit_counter = [0]
    by_shard: dict[str, list[dict[str, Any]]] = {}
    for cell in manifest["pending_cells"]: by_shard.setdefault(cell["shard"], []).append(cell)
    reports: list[dict[str, Any]] = []
    names = list(by_shard)
    for start in range(0, len(names), max_shards):
        wave = names[start:start + max_shards]
        if stop.is_set(): break
        with ThreadPoolExecutor(max_workers=len(wave)) as pool:
            futures = {pool.submit(run_shard_cells, name, by_shard[name], by_id, archive, prefix, instructions, 2, 180, c.archive_turn, stop, progress, progress_lock, submit_counter, {"npm_root":str(npm_root)}): name for name in wave}
            for future in as_completed(futures): reports.append({"shard": futures[future], **future.result()})
    attempted = sum(r.get("attempted_generations", 0) for r in reports)
    complete = attempted == manifest["pending_count"] and not stop.is_set()
    status = {"state": "completed" if complete and all(r["state"] == "completed" for r in reports) else "blocked", "assigned_generations": manifest["pending_count"], "attempted_generations": attempted, "reports": reports, "allocation_exhausted": complete}
    c.save(archive / "status.json", status)
    return status


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); s = p.add_subparsers(dest="command", required=True)
    f = s.add_parser("freeze")
    for n in ("tasks", "parent", "protocol", "source-root", "out"): f.add_argument("--" + n, type=Path, required=True)
    r = s.add_parser("run")
    for n in ("tasks", "parent", "protocol", "source-root", "manifest", "archive"): r.add_argument("--" + n, type=Path, required=True)
    r.add_argument("--npm-root", type=Path, default=Path("tmp/codex-runtime"))
    r.add_argument("--max-shards", type=int, default=4)
    a = p.parse_args()
    if a.command == "freeze": freeze(a.tasks, a.parent, a.protocol, a.source_root, a.out); return 0
    result = run(a.tasks, a.parent, a.protocol, a.source_root, a.manifest, a.archive, a.npm_root, a.max_shards); print(json.dumps(result)); return 0 if result["state"] == "completed" else 1


if __name__ == "__main__": raise SystemExit(main())
