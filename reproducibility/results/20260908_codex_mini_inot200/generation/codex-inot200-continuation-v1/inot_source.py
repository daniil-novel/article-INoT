"""Prepare and run an exploratory INoT algorithm replication on held-out tasks.

This wrapper uses the audited Codex CLI transport only.  The treatment is the
algorithm-level PromptCode/debate instruction, not the ordinary direct arm.
It is deliberately separate from the frozen five-arm held-out plan.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import threading
import time

from .. import codex_subscription as c
from ..audit_codex_pilot import inventory_attempt
from ..record_codex_runtime import capture

TREATMENT = "inot_algorithm_replication"
REPLICATE_ID = 5
TIMEOUT_SECONDS = 180
WORKERS = 2

# Independently worded compact PromptCode synthesis of arXiv:2507.08664v1,
# Sections 3.1 and 3.3, Listings 1 and 3.  The pseudo-code is LLM-read
# guidance, not Python executed by the host.  Keep it below 140 words.
INOT_DESCRIPTION = (
    "<PromptCode><Role>Executor reads this conceptual hybrid Python/natural "
    "language procedure; do not execute code or claim hidden agents.</Role> "
    "<ReasoningLogic>Initialize virtual A and B for the task; obtain "
    "result_A, thought_A and result_B, thought_B. Set agreement=False. "
    "for round in 1..10: argument_A/B; critique_A critiques B and "
    "critique_B critiques A; rebuttal_A/B answer the opposite critique; "
    "result_A,thought_A=update(rebuttal_B); result_B,thought_B=update(rebuttal_A); "
    "agreement=(result_A==result_B); if agreement: break. "
    "final_result=result_A if agreement else result_A (latest A fallback). "
    "</ReasoningLogic></PromptCode> Return final_result in the requested "
    "format, with no tools, tests, unavailable evidence, or hidden-agent "
    "claims. Omit image augmentation for this text task."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def ordered_tasks(path: Path) -> list[dict]:
    """Validate through the shared loader while preserving frozen file order."""
    validated = c.tasks_from(path)
    ordered = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if sorted(ordered, key=lambda task: task["task_id"]) != validated:
        raise ValueError("Task file changed during validation")
    return ordered


def prompt_for(task: dict) -> str:
    text = INOT_DESCRIPTION + "\n\nTASK\n" + task["prompt"] + "\nFULL SUPPLIED CONTEXT\n" + task["context"]
    text += "\n\n" + c.FINAL
    if len(text.encode("utf-8")) > 65536:
        raise ValueError("Full input exceeds the fixed UTF-8 byte guard")
    return text


def word_count() -> int:
    return len(INOT_DESCRIPTION.split())


def plan(tasks: list[dict], protocol_path: Path, selection_path: Path, gate_path: Path, tasks_path: Path | None = None) -> dict:
    ids = [task["task_id"] for task in tasks]
    if len(ids) != 200 or len(set(ids)) != 200:
        raise ValueError("INoT exploratory plan requires the exact 200 held-out task IDs")
    selection = c.read(selection_path)
    gate = c.read(gate_path)
    if selection.get("assigned_task_ids") != ids or selection.get("count") != 200:
        raise ValueError("tasks differ from frozen heldout selection")
    if gate.get("assigned_task_ids") != ids or gate.get("controls_complete") is not True:
        raise ValueError("control gate does not cover the exact selected task order")
    eligible = gate.get("evaluable_task_ids")
    if not isinstance(eligible, list) or not set(eligible).issubset(ids):
        raise ValueError("control gate evaluability is invalid")
    if tasks_path is not None:
        task_bytes = sha256(tasks_path)
        if task_bytes != selection.get("model_input_sha256") or task_bytes != gate.get("prepared_split_sha256"):
            raise ValueError("task bytes differ from frozen selection or control gate")
    if word_count() > 140:
        raise ValueError("INoT source-derived description exceeds 140 words")
    cells = [{"task_id": task_id, "arm": TREATMENT, "replicate_id": REPLICATE_ID,
              "cli_turns": 1, "id": hashlib.sha256(f"{task_id}|{TREATMENT}|{REPLICATE_ID}".encode()).hexdigest()[:24]}
             for task_id in ids]
    random.Random(20260908).shuffle(cells)
    body = {
        "schema": "codex-inot-heldout200-v1",
        "treatment": TREATMENT,
        "model_requested": c.MODEL,
        "cli_version_required": c.CLI_VERSION,
        "reasoning_effort": "medium",
        "timeout_seconds": TIMEOUT_SECONDS,
        "workers": WORKERS,
        "retries": 0,
        "task_count": len(ids),
        "task_ids": ids,
        "tasks_sha256": c.digest(tasks),
        "task_file_sha256": sha256(tasks_path) if tasks_path is not None else None,
        "selection_sha256": sha256(selection_path),
        "control_gate_sha256": sha256(gate_path),
        "control_gate_source_tree_sha256": gate.get("source_tree_sha256"),
        "control_gate_prepared_split_sha256": gate.get("prepared_split_sha256"),
        "evaluable_task_ids": eligible,
        "replicate_id": REPLICATE_ID,
        "order_seed": 20260908,
        "cells": cells,
        "planned_generations": len(cells),
        "planned_cli_turns": len(cells),
        "source_sha256_lf": source_hash(),
        "shared_runner_source_sha256_lf": c.source_hash(),
        "shared_factorial_runner_sha256_lf": hashlib.sha256((Path(__file__).resolve().parents[1] / "factorial_runner.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "shared_runtime_capture_sha256_lf": hashlib.sha256((Path(__file__).resolve().parents[1] / "record_codex_runtime.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "shared_archive_inventory_sha256_lf": hashlib.sha256((Path(__file__).resolve().parents[1] / "audit_codex_pilot.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "protocol_sha256": sha256(protocol_path),
        "method_source": "arXiv:2507.08664v1, Sections 3.1 and 3.3, Listings 1 and 3",
        "description_word_count": word_count(),
        "stopping_interpretation": "paper prose: agreement OR ten rounds; Listing 3 while-condition is ambiguous; this replication returns Agent A's latest answer after ten rounds without agreement",
        "image_augmentation": "omitted for text-only tasks",
        "scope": "exploratory held-out comparison; not author-validated native INoT code",
    }
    return {**body, "manifest_sha256": c.digest(body)}


def run(tasks_path: Path, manifest_path: Path, archive: Path, protocol_path: Path, selection_path: Path, gate_path: Path, npm_root: Path) -> dict:
    tasks = ordered_tasks(tasks_path)
    manifest = c.read(manifest_path)
    if manifest != plan(tasks, protocol_path, selection_path, gate_path, tasks_path):
        raise ValueError("Frozen INoT plan differs from tasks, protocol, or implementation")
    archive = archive.resolve()
    archive.mkdir(parents=True, exist_ok=False)
    c.save(archive / "manifest.json", manifest)
    c.save(archive / "tasks.json", tasks)
    (archive / "protocol.md").write_bytes(protocol_path.read_bytes())
    (archive / "selection.json").write_bytes(selection_path.read_bytes())
    (archive / "control-gate.json").write_bytes(gate_path.read_bytes())
    (archive / "inot_source.py").write_bytes(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))
    for name in ("factorial_runner.py", "record_codex_runtime.py", "audit_codex_pilot.py"):
        (archive / name).write_bytes((Path(__file__).resolve().parents[1] / name).read_bytes().replace(b"\r\n", b"\n"))
    cwd = archive / "empty"
    cwd.mkdir()
    instructions = archive / "instructions.txt"
    instructions.write_bytes(c.BASE.encode("utf-8"))
    expected_entry = npm_root.resolve() / "node_modules/@openai/codex/bin/codex.js"
    node = __import__("shutil").which("node")
    if not node or not expected_entry.is_file():
        raise ValueError("official Codex Node entry is missing from the explicit npm root")
    prefix = [node, str(expected_entry)]
    version = subprocess.check_output(prefix + ["--version"], text=True).strip()
    if version != c.CLI_VERSION:
        raise ValueError(f"Frozen CLI version required: {c.CLI_VERSION}; got {version}")
    auth = subprocess.run(prefix + ["login", "status"], capture_output=True, text=True)
    if auth.returncode or "ChatGPT" not in auth.stdout + auth.stderr:
        raise ValueError("ChatGPT subscription login required")
    c.save(archive / "runtime.json", {"version": version, "prefix": prefix, "authentication": "chatgpt",
                                        "workers": WORKERS, "timeout_seconds": TIMEOUT_SECONDS,
                                        "treatment": TREATMENT, "started_unix": time.time()})
    capture(archive, npm_root, Path(c.__file__))
    c.save(archive / "status.json", {"state": "started", "started_unix": time.time(),
                                      "assigned_generations": len(manifest["cells"]), "treatment": TREATMENT})
    (archive / "turns").mkdir()
    (archive / "cells").mkdir()
    command = c.cli_command(prefix, cwd.resolve(), instructions.resolve())
    by_id = {task["task_id"]: task for task in tasks}
    stop = threading.Event()
    lock = threading.Lock()
    rows: list[dict] = []

    def one(cell: dict) -> dict | None:
        if stop.is_set():
            return None
        try:
            result = c.archive_turn(archive / "turns" / cell["id"], command, prompt_for(by_id[cell["task_id"]]), TIMEOUT_SECONDS)
            row = {**cell, "model": c.MODEL, "treatment": TREATMENT,
                   "seed": REPLICATE_ID, "seed_field_semantics": "replicate label only; CLI sampling seed not set",
                   "final_text": result["final_text"], "usage": result["usage"],
                   "total_tokens": result["usage"]["input_tokens"] + result["usage"]["output_tokens"],
                   "api_equivalent_usd": result["api_equivalent_usd"],
                   "uncached_sensitivity_usd": result["uncached_sensitivity_usd"],
                   "wall_seconds": result["wall_seconds"], "actual_api_charge_usd": None}
            c.save(archive / "cells" / f"{cell['id']}.json", row)
            with lock:
                print(json.dumps({"completed_cell": cell["id"], "task": cell["task_id"], "treatment": TREATMENT}), flush=True)
            return row
        except Exception:
            stop.set()
            raise

    failures = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(one, cell): cell for cell in manifest["cells"]}
        for future in as_completed(futures):
            try:
                row = future.result()
                if row:
                    rows.append(row)
            except Exception as exc:
                failures.append({"cell": futures[future]["id"], "reason": str(exc)})
    rows.sort(key=lambda row: row["id"])
    (archive / "results.jsonl").write_bytes(b"".join(c.canonical(row) + b"\n" for row in rows))
    status = {"state": "completed" if len(rows) == len(manifest["cells"]) and not failures else "blocked",
              "completed_generations": len(rows), "assigned_generations": len(manifest["cells"]), "failures": failures}
    c.save(archive / "status.json", status)
    c.save(archive / "inventory.json", inventory_attempt(archive))
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--gate", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--npm-root", type=Path, default=Path("tmp/codex-runtime"))
    args = parser.parse_args()
    if args.command == "plan":
        if args.manifest.exists():
            raise ValueError("Refuse to overwrite a frozen INoT plan")
        c.save(args.manifest, plan(ordered_tasks(args.tasks), args.protocol, args.selection, args.gate, args.tasks))
    else:
        if args.archive is None:
            parser.error("--archive is required to run")
        status = run(args.tasks, args.manifest, args.archive, args.protocol, args.selection, args.gate, args.npm_root)
        print(json.dumps(status))
        if status["state"] != "completed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
