"""Offline preparation and guarded recovery for the SCC-2000 continuation.

This module deliberately delegates schedule construction and execution policy to
the frozen revision dispatcher.  Preparation and recovery are offline; the
generate entry invokes the frozen worker and therefore may call the model.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.revision_20260911 import scc_dispatch  # noqa: E402
from reproducibility.revision_20260911 import scc_controls  # noqa: E402

BLOCKS = 2000
CELLS = BLOCKS * 3
REPEATS = (101, 102, 103)
METHODS = ("single_roles", "single_neutral", "scc_author_2024_codex_transport")
SCHEMA = "scc-continuation-2000-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(cli.canonical(value)).hexdigest()


def _read(path: Path) -> Any:
    return cli.read(path)


def _source_inventory(original_manifest: dict) -> dict[str, str]:
    return {name: normalized_sha(ROOT / name) for name in sorted(original_manifest["source_files_sha256"])}


def _blocks(planned: list[dict]) -> list[list[dict]]:
    if len(planned) % 3:
        raise ValueError("SCC schedule is not composed of three-cell blocks")
    return [planned[i:i + 3] for i in range(0, len(planned), 3)]


def selected_prefix(planned: list[dict], blocks: int = BLOCKS) -> list[dict]:
    groups = _blocks(planned)
    if len(groups) < blocks:
        raise ValueError("Frozen SCC schedule is shorter than the requested prefix")
    selected = [cell for group in groups[:blocks] for cell in group]
    for group in groups[:blocks]:
        if (len(group) != 3 or {c["method"] for c in group} != set(METHODS)
                or len({c["task_id"] for c in group}) != 1
                or len({c["replicate_id"] for c in group}) != 1
                or len({c["id"] for c in group}) != 3):
            raise ValueError("SCC prefix contains a partial or non-factorial block")
    return selected


def _inventory(root: Path, selected_ids: set[str], planned_by_id: dict[str, dict] | None = None) -> dict:
    assignments = root / "assignments"
    touched = []
    for folder in sorted(assignments.iterdir()) if assignments.is_dir() else []:
        if not folder.is_dir():
            continue
        files = {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()}
        status = folder / "status.json"
        if planned_by_id is not None:
            if folder.name not in planned_by_id:
                raise ValueError("Touched assignment falls outside the continuation prefix: " + folder.name)
            cell = folder / "cell.json"
            if not cell.is_file() or _read(cell) != planned_by_id[folder.name]:
                raise ValueError("Existing cell identity differs from the frozen schedule: " + folder.name)
        touched.append({"id": folder.name, "selected": folder.name in selected_ids,
                        "status_sha256": sha(status) if status.is_file() else None,
                        "files_sha256": files})
    return {"assignment_count": len(touched), "assignments": touched,
            "snapshot_sha256": canonical_digest(touched)}


def _validate_frozen(inputs: Path, gate: Path, manifest: Path) -> tuple[dict, list[dict]]:
    frozen, planned = scc_dispatch.plan(inputs.resolve(), gate.resolve(), manifest.resolve())
    if frozen != _read(manifest):
        raise ValueError("Existing frozen SCC manifest differs from the current plan")
    if frozen.get("planned_assignments") != 9000 or len(planned) != 9000:
        raise ValueError("Continuation requires the frozen 9000-cell SCC schedule")
    return frozen, planned


def prepare(*, original_root: Path, inputs: Path, gate_dir: Path, manifest: Path,
            amendment: Path, output: Path, selection: Path | None = None,
            npm_root: Path | None = None) -> dict:
    """Create the immutable continuation selection manifest offline."""
    original_root, inputs, gate_dir, manifest, amendment, output = [p.resolve() for p in
        (original_root, inputs, gate_dir, manifest, amendment, output)]
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite continuation output: {output}")
    if not amendment.is_file():
        raise FileNotFoundError(amendment)
    frozen, planned = _validate_frozen(inputs, gate_dir, manifest)
    selected = selected_prefix(planned)
    selected_ids = {x["id"] for x in selected}
    planned_by_id = {x["id"]: x for x in planned}
    inventory = _inventory(original_root, selected_ids, planned_by_id)
    outside = [x["id"] for x in inventory["assignments"] if not x["selected"]]
    if outside:
        raise ValueError("Touched assignment falls outside the continuation prefix: " + outside[0])
    if len(selected) != CELLS or len(selected_ids) != CELLS:
        raise ValueError("Continuation selection must contain exactly 6000 unique cells")
    if selection is None:
        selection = inputs / "selection.json"
    record = {
        "schema": SCHEMA, "blocks": BLOCKS, "cells": CELLS,
        "block_size": 3, "order_seed": frozen["order_seed"],
        "selected_ids": [x["id"] for x in selected],
        "selected_cells": selected,
        "all_ids": [x["id"] for x in planned],
        "selected_cells_digest": canonical_digest(selected),
        "counts_by_task": {k: sum(c["task_id"] == k for c in selected)
                           for k in sorted({c["task_id"] for c in selected})},
        "counts_by_repeat": {str(k): sum(c["replicate_id"] == k for c in selected) for k in REPEATS},
        "original_manifest_sha256": sha(manifest),
        "original_manifest_content_digest": canonical_digest(frozen),
        "source_files_sha256": _source_inventory(frozen),
        "amendment_sha256": normalized_sha(amendment),
        "adapter_source_sha256": normalized_sha(Path(__file__)),
        "old_inventory": inventory,
        "runtime": {"model": frozen["model"], "reasoning_effort": frozen["reasoning_effort"],
                     "cli_version": frozen["cli_version"], "workers": frozen["workers"],
                     "generated_test_parallelism": frozen["generated_test_parallelism"]},
        "prepared_unix": time.time(),
    }
    output.mkdir(parents=True)
    cli.save(output / "selection_manifest.json", record)
    cli.save(output / "original_manifest.json", frozen)
    return record


def require_fresh_heartbeat(path: Path, now: float | None = None) -> None:
    if (path.parent / "PAUSED.json").exists():
        raise RuntimeError("Reserve pause latch blocks dispatch")
    check = _read(path)
    remaining, checked = check.get("remaining_percent"), check.get("checked_unix")
    if (check.get("allow_model_work") is not True or check.get("reserve_percent") != 65
            or type(remaining) not in (int, float) or not math.isfinite(remaining) or remaining <= 65
            or type(checked) not in (int, float) or not math.isfinite(checked)
            or not -2 <= (time.time() if now is None else now) - checked <= 75):
        raise RuntimeError("Missing, stale or insufficient reserve heartbeat blocks dispatch")


@contextlib.contextmanager
def selection_adapter(selected_ids: set[str] | list[str], heartbeat: Path | None = None) -> Iterator[None]:
    """Temporarily constrain the frozen coordinator while retaining ledger IDs."""
    wanted = set(selected_ids)
    original = scc_dispatch.coordinate_assignments

    def wrapped(pending, payload_for, executor, workers, known, guard, progress=None):
        chosen = [c for c in pending if c["id"] in wanted]
        unselected = [c for c in pending if c["id"] not in wanted]
        def guarded_payload(cell):
            if heartbeat is not None:
                require_fresh_heartbeat(heartbeat)
            return payload_for(cell)
        result = original(chosen, guarded_payload, executor, workers, known, guard, progress)
        result["pending"] = list(result["pending"]) + unselected
        result["unselected_pending"] = unselected
        return result

    scc_dispatch.coordinate_assignments = wrapped
    try:
        yield
    finally:
        scc_dispatch.coordinate_assignments = original


def continuation_status(*, root: Path, selected_ids: set[str] | list[str], lock: Path | None = None) -> dict:
    root = root.resolve(); selected = set(selected_ids)
    states = {}; untouched = []
    for ident in selected:
        status = root / "assignments" / ident / "status.json"
        if not status.is_file():
            untouched.append(ident); continue
        states[ident] = _read(status).get("state")
    terminal = {"completed", "infrastructure_failure", "model_or_workflow_failure", "paused"}
    active_lock = bool(lock and lock.exists())
    return {"schema": SCHEMA, "selected_cells": len(selected), "terminal_cells": sum(v in terminal for v in states.values()),
            "untouched_selected_cells": len(untouched), "active_lock": active_lock,
            "state": "completed" if not untouched and all(v in terminal for v in states.values()) and not active_lock else "paused",
            "counts_by_state": {s: list(states.values()).count(s) for s in sorted(set(states.values()))}}


def load_selection(path: Path, *, amendment: Path | None = None) -> dict:
    """Read a prepared selection and verify its bound files without refreshing it."""
    record = _read(path.resolve())
    if record.get("schema") != SCHEMA or record.get("blocks") != BLOCKS or record.get("cells") != CELLS:
        raise ValueError("Invalid SCC continuation selection manifest")
    if amendment is not None and normalized_sha(amendment.resolve()) != record.get("amendment_sha256"):
        raise ValueError("Continuation amendment changed")
    if normalized_sha(Path(__file__)) != record.get("adapter_source_sha256"):
        raise ValueError("Continuation adapter source changed")
    if len(record.get("selected_ids", [])) != CELLS or len(set(record["selected_ids"])) != CELLS:
        raise ValueError("Continuation selection does not contain exactly 6000 cells")
    cells = record.get("selected_cells", [])
    if canonical_digest(cells) != record.get("selected_cells_digest") or [c["id"] for c in cells] != record["selected_ids"]:
        raise ValueError("Selection cells or order changed")
    return record


def validate_generate(*, selection_manifest: Path, amendment: Path, reserve_guard: Path,
                      recovery_manifest: Path, original_manifest: Path, workers: int = 8,
                      user_authorization: Path | None = None, threshold: float = 65.0,
                      inputs: Path | None = None, gate_dir: Path | None = None,
                      checkout: Path = ROOT, host_python: Path = Path(r"C:/Python311/python.exe")) -> dict:
    """Perform the fresh, read-only launch checks required by the continuation."""
    selection = load_selection(selection_manifest, amendment=amendment)
    original = _read(original_manifest.resolve())
    if sha(original_manifest.resolve()) != selection.get("original_manifest_sha256"):
        raise ValueError("Original frozen manifest changed")
    if threshold != 65.0 or inputs is None or gate_dir is None:
        raise ValueError("Frozen prefix and reserve checks are mandatory")
    recovery = validate_recovery(selection, recovery_manifest)
    guard_dir = reserve_guard.resolve().parent
    watcher = _read(guard_dir / "watch.lock")
    processes = process_inventory(host_python, checkout)
    matched = [p for p in processes if p["pid"] == watcher.get("pid") and p["module"] == "reproducibility.revision_20260911.subscription_guard"
               and p["cwd_matches"] and p["watch"] and abs(p["created"] - watcher.get("created", 0)) < .01]
    if len(matched) != 1 or (guard_dir / "PAUSED.json").exists():
        raise ValueError("A live reserve watcher without a pause latch is required")
    guard_command = [str(host_python), "-m", "reproducibility.revision_20260911.subscription_guard", "check", "--root", str(checkout), "--out", str(guard_dir)]
    check = subprocess.run(guard_command, cwd=checkout, capture_output=True, text=True)
    try: guard = json.loads(check.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError): guard = {}
    available = guard.get("remaining_percent")
    if check.returncode or guard.get("allow_model_work") is not True or isinstance(available, bool) or not isinstance(available, (int, float)) or not math.isfinite(available) or available <= threshold or guard.get("reserve_percent") != threshold or guard.get("latched", False):
        raise ValueError("Fresh reserve guard check failed")
    if user_authorization is None or not user_authorization.is_file() or not all(x in user_authorization.read_text(encoding="utf-8").lower() for x in ("prefix2000", "reserve65", "authorized resume")):
        raise ValueError("User authorization record is required")
    _, planned = _validate_frozen(inputs, gate_dir, original_manifest)
    prefix = selected_prefix(planned)
    if canonical_digest(prefix) != selection.get("selected_cells_digest") or [c["id"] for c in prefix] != selection["selected_ids"]:
        raise ValueError("Continuation selection differs from recomputed frozen prefix")
    frozen_paths = [selection_manifest, amendment, Path(__file__), recovery_manifest, user_authorization]
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *map(str, frozen_paths)], cwd=checkout, capture_output=True, text=True)
    if tracked.returncode: raise ValueError("Selection, amendment and adapter must be tracked")
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *map(str, frozen_paths)], cwd=checkout)
    if clean.returncode: raise ValueError("Selection, amendment or adapter differs from HEAD")
    if original.get("workers") != workers or workers != 8:
        raise ValueError("Continuation requires exactly eight workers")
    if original.get("model") != "gpt-5.6-luna" or original.get("reasoning_effort") != "medium" or original.get("cli_version") != "codex-cli 0.153.4":
        raise ValueError("Frozen Luna runtime does not match the continuation pin")
    return {"ok": True, "threshold": threshold, "reserve_remaining_percent": available,
            "selected_cells": selection["cells"], "workers": workers,
            "guard_command": guard_command, "guard_evidence": guard,
            "watcher": matched[0], "recovery_verified": recovery}


def generate(*, inputs: Path, gate_dir: Path, manifest: Path, out: Path, npm_root: Path,
             selection_manifest: Path, amendment: Path, reserve_guard: Path,
             recovery_manifest: Path, user_authorization: Path, workers: int = 8,
             known_guard: float = 285.0) -> dict:
    """Resume the frozen dispatcher through the selected-prefix adapter."""
    checks = validate_generate(selection_manifest=selection_manifest, amendment=amendment,
        reserve_guard=reserve_guard, recovery_manifest=recovery_manifest,
        original_manifest=manifest, workers=workers, user_authorization=user_authorization,
        inputs=inputs, gate_dir=gate_dir)
    selected = set(load_selection(selection_manifest, amendment=amendment)["selected_ids"])
    cli.save(selection_manifest.parent / "launch_check.json", checks)
    with selection_adapter(selected, reserve_guard):
        status = scc_dispatch.dispatch_processes(inputs.resolve(), gate_dir.resolve(), manifest.resolve(), out.resolve(), npm_root.resolve(), workers, known_guard)
    final = continuation_status(root=out, selected_ids=selected, lock=out / "DISPATCH.lock")
    cli.save(out / "continuation_status.json", final)
    if final["state"] != "completed":
        raise RuntimeError("Selected continuation cells remain untouched or nonterminal")
    return {"checks": checks, "status": status, "continuation_status": final}


def _turn_is_nonterminal(turn: Path) -> bool:
    if (turn / "result.json").exists(): return False
    events = turn / "events.jsonl"
    if not events.is_file(): return False
    rows = [json.loads(x) for x in events.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    return any(r.get("type") == "turn.started" for r in rows) and not any(r.get("type") == "turn.completed" for r in rows)


def process_inventory(host_python: Path, checkout: Path = ROOT) -> list[dict]:
    """Read process identity via the host runtime, without substring matching."""
    code = '''import json,os,psutil,sys
root=os.path.normcase(os.path.abspath(sys.argv[1])); rows=[]
for p in psutil.process_iter():
 try:
  args=p.cmdline(); idx=args.index('-m') if '-m' in args else -1
  module=args[idx+1] if idx>=0 and idx+1<len(args) else None
  action=args[idx+2] if idx>=0 and idx+2<len(args) else None
  rows.append(dict(pid=p.pid,created=p.create_time(),module=module,action=action,watch='watch' in args,cwd_matches=os.path.normcase(os.path.abspath(p.cwd()))==root))
 except psutil.NoSuchProcess: pass
 except psutil.AccessDenied: rows.append(dict(pid=p.pid,created=0,module=None,watch=False,cwd_matches=False,unreadable=True))
print(json.dumps(rows))'''
    return json.loads(subprocess.check_output([str(host_python), "-c", code, str(checkout)], text=True))


def assert_recovery_idle(lock: Path, processes: list[dict]) -> None:
    pid = int(lock.read_text(encoding="utf-8").strip()) if lock.is_file() else None
    modules = {"reproducibility.revision_20260911.scc_dispatch", "reproducibility.scc2000.continuation", "reproducibility.revision_20260911.start_scc_study"}
    for p in processes:
        generator = p["module"] in modules and (p["module"] != "reproducibility.scc2000.continuation" or p.get("action") == "generate")
        if p["pid"] == pid or (p["pid"] != os.getpid() and generator and p["cwd_matches"]):
            raise RuntimeError("Live or reused dispatcher PID; recovery refused before mutation")


def validate_recovery(selection: dict, recovery_manifest: Path) -> dict:
    record = _read(recovery_manifest)
    if record.get("schema") != SCHEMA or record.get("recovered") != 8 or not record.get("lock_released"):
        raise ValueError("Recovery manifest is missing or invalid")
    base = recovery_manifest.parent
    root = Path(record["original_root"])
    changes = {r["id"]: r for r in record["assignments"]}
    if len(changes) != 8: raise ValueError("Recovery must identify eight distinct assignments")
    pause = _read(base / "historical_pause.json")
    if sha(base / "historical_pause.json") != record["pause_sha256"] or pause.get("reason") != "user_subscription_reserve" or pause.get("remaining_percent") != 55 or pause.get("allow_model_work") is not False:
        raise ValueError("Historical interruption evidence changed")
    if sha(base / "DISPATCH.lock") != record["lock_sha256"]:
        raise ValueError("Preserved lock changed")
    old = selection["old_inventory"]
    if canonical_digest(old["assignments"]) != old["snapshot_sha256"]:
        raise ValueError("Old inventory digest changed")
    if {p.name for p in (root / "assignments").iterdir() if p.is_dir()} != {r["id"] for r in old["assignments"]}:
        raise ValueError("Assignments changed after the freeze")
    for row in old["assignments"]:
        folder = root / "assignments" / row["id"]
        actual = {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()}
        expected = dict(row["files_sha256"])
        if row["id"] in changes:
            recovered = changes[row["id"]]
            copy = base / "assignments" / row["id"]
            copied = {p.relative_to(copy).as_posix(): sha(p) for p in copy.rglob("*") if p.is_file()}
            if copied != expected or copied != recovered["files_sha256"]:
                raise ValueError("Preserved interrupted assignment changed")
            expected["status.json"] = recovered["after_status_sha256"]
            if _read(folder / "status.json").get("state") != "paused":
                raise ValueError("Interrupted assignment is not a paused unknown")
        if actual != expected: raise ValueError("Pre-existing assignment bytes changed: " + row["id"])
    return {"recovered": 8, "old_assignments_verified": old["assignment_count"]}


def recover(*, original_root: Path, recovery: Path, historical_pause: Path,
            host_python: Path = Path(r"C:/Python311/python.exe"), lock: Path | None = None) -> dict:
    """Archive original bytes and terminalize only the eight interrupted statuses."""
    original_root, recovery = original_root.resolve(), recovery.resolve()
    assignments = original_root / "assignments"; candidates = []; lock = lock or (original_root / "DISPATCH.lock")
    assert_recovery_idle(lock, process_inventory(host_python))
    lock_bytes = lock.read_bytes() if lock.is_file() else None
    if lock_bytes is None: raise ValueError("Historical dispatcher lock required")
    pause_bytes = historical_pause.read_bytes(); pause = json.loads(pause_bytes)
    if pause.get("reason") != "user_subscription_reserve" or pause.get("remaining_percent") != 55 or pause.get("allow_model_work") is not False:
        raise ValueError("Historical reserve interruption evidence is required")
    for folder in sorted(assignments.iterdir()) if assignments.is_dir() else []:
        status = folder / "status.json"
        if not folder.is_dir() or not status.is_file() or (folder / "candidate.py").exists(): continue
        if _read(status).get("state") != "initializing": continue
        turns = sorted((folder / "turns").glob("[0-9][0-9][0-9]")) if (folder / "turns").is_dir() else []
        if turns and _turn_is_nonterminal(turns[-1]): candidates.append(folder)
    if len(candidates) != 8: raise ValueError(f"Expected exactly eight interrupted assignments, found {len(candidates)}")
    recovery.mkdir(parents=True, exist_ok=False)
    rows = []
    for folder in candidates:
        dest = recovery / "assignments" / folder.name; dest.mkdir(parents=True)
        files = {}
        for p in folder.rglob("*"):
            if p.is_file():
                rel = p.relative_to(folder); target = dest / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes()); files[rel.as_posix()] = sha(p)
        original = _read(folder / "status.json")
        cli.save(folder / "status.json", {"state": "paused", "generation_complete": False,
            "outcome_type": "external_account_reserve_interruption", "reason": "external account reserve interruption",
            "original_status_sha256": sha(dest / "status.json"), "recovery_directory": str(dest), "finished_unix": time.time()})
        rows.append({"id": folder.name, "original_status": original, "files_sha256": files,
                     "after_status_sha256": sha(folder / "status.json")})
    if lock_bytes is not None:
        (recovery / "DISPATCH.lock").write_bytes(lock_bytes)
    (recovery / "historical_pause.json").write_bytes(pause_bytes)
    assert_recovery_idle(lock, process_inventory(host_python))
    lock.unlink()
    record = {"schema": SCHEMA, "recovered": len(rows), "assignments": rows, "lock_released": True,
              "original_root": str(original_root), "lock_sha256": sha(recovery / "DISPATCH.lock"),
              "pause_sha256": sha(recovery / "historical_pause.json"), "created_unix": time.time()}
    cli.save(recovery / "recovery_manifest.json", record)
    return record


def main() -> None:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("prepare")
    for name in ("original-root", "inputs", "gate-dir", "manifest", "amendment", "output"):
        q.add_argument("--" + name, type=Path, required=True)
    q.add_argument("--selection", type=Path); q.add_argument("--npm-root", type=Path)
    r = sub.add_parser("recover"); r.add_argument("--original-root", type=Path, required=True); r.add_argument("--recovery", type=Path, required=True); r.add_argument("--host-python", type=Path, default=Path(r"C:/Python311/python.exe")); r.add_argument("--lock", type=Path)
    r.add_argument("--historical-pause", type=Path, required=True)
    g = sub.add_parser("generate")
    for name in ("inputs", "gate-dir", "manifest", "out", "npm-root", "selection-manifest", "amendment", "reserve-guard", "recovery-manifest", "user-authorization"):
        g.add_argument("--" + name, type=Path, required=True)
    g.add_argument("--workers", type=int, default=8); g.add_argument("--known-guard", type=float, default=285.0)
    a = p.parse_args()
    if a.command == "prepare":
        result = prepare(original_root=a.original_root, inputs=a.inputs, gate_dir=a.gate_dir, manifest=a.manifest, amendment=a.amendment, output=a.output, selection=a.selection, npm_root=a.npm_root)
    elif a.command == "recover":
        result = recover(original_root=a.original_root, recovery=a.recovery, historical_pause=a.historical_pause, host_python=a.host_python, lock=a.lock)
    else:
        result = generate(inputs=a.inputs, gate_dir=a.gate_dir, manifest=a.manifest, out=a.out, npm_root=a.npm_root, selection_manifest=a.selection_manifest, amendment=a.amendment, reserve_guard=a.reserve_guard, recovery_manifest=a.recovery_manifest, user_authorization=a.user_authorization, workers=a.workers, known_guard=a.known_guard)
    print(json.dumps({k: v for k, v in result.items() if k in {"schema", "blocks", "cells", "recovered", "lock_released", "status", "continuation_status"}}, ensure_ascii=False))


if __name__ == "__main__": main()
