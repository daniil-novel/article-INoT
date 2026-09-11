"""Prepare a bounded SCC/SR/SN smoke on the three exposed pilot IDs.

Default mode is preparation only. `--execute` deliberately requires an
explicit opt-in and uses the same spawned assignment worker with an isolated
output directory; it is never part of the 9000-cell denominator.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, time, multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from reproducibility import codex_luna_subscription as cli  # noqa: E402
from reproducibility.revision_20260911 import scc_dispatch as d  # noqa: E402

IDS = ("BigCodeBench/325", "BigCodeBench/322", "BigCodeBench/1036")

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(tasks_path: Path, out: Path) -> dict:
    if out.exists(): raise FileExistsError(f"Refuse to replace an existing development plan: {out}")
    source_tasks = {t["task_id"]: t for t in cli.tasks_from(tasks_path)}
    if set(source_tasks) != set(IDS):
        raise ValueError("Development task file does not contain the pinned three IDs")
    tasks = [source_tasks[task_id] for task_id in IDS]
    assigned = cli.read(ROOT / "reproducibility/scale1000/inputs-v1/selection.json")["assigned_task_ids"]
    if set(IDS) & set(assigned): raise ValueError("Development IDs overlap the main allocation")
    cells = []
    for task in tasks:
        for method in d.METHODS:
            cell = {"task_id": task["task_id"], "replicate_id": 0, "method": method,
                    "max_upstream_round": 2 if method == d.METHOD else 0,
                    "cli_turns": 1 if method != d.METHOD else 4}
            cells.append({**cell, "id": cli.digest(cell)[:24]})
    record = {"schema": "scc-dev-smoke-v1", "task_ids": list(IDS), "methods": list(d.METHODS),
              "cells": cells, "worker": "reproducibility.revision_20260911.scc_dispatch.run_assignment_worker",
              "source_sha256": {name: sha(ROOT / name) for name in (
                  "reproducibility/revision_20260911/scc_dispatch.py",
                  "reproducibility/external_baselines/scc.py",
                  "reproducibility/codex_luna_subscription.py")},
              "task_file_sha256": sha(tasks_path), "prepared_unix": time.time(), "model_calls": 0}
    out.parent.mkdir(parents=True, exist_ok=True); cli.save(out, record)
    return record

def execute(record: dict, tasks_path: Path, manifest_path: Path, execution_root: Path, npm_root: Path) -> dict:
    tasks = {t["task_id"]: t for t in cli.tasks_from(tasks_path)}
    gen = execution_root.resolve() / "generation"; gen.mkdir(parents=True, exist_ok=False)
    empty = gen / "empty"; empty.mkdir()
    instruction_paths = {}
    for method, text in ((d.METHOD, d.scc.INSTRUCTIONS), ("single_roles", cli.BASE), ("single_neutral", cli.BASE)):
        path = gen / f"instructions-{method}.txt"; path.write_bytes(text.encode()); instruction_paths[method] = path
    (gen / "instructions.txt").write_bytes(cli.BASE.encode())
    os.environ["CODEX_STUDY_CLI_JS"] = str(npm_root.resolve() / "node_modules/@openai/codex/bin/codex.js")
    prefix = cli.resolved_prefix(); version = subprocess.check_output(prefix + ["--version"], text=True).strip()
    if version != cli.CLI_VERSION: raise ValueError("CLI version mismatch")
    auth = subprocess.run(prefix + ["login", "status"], capture_output=True, text=True)
    if auth.returncode or "ChatGPT" not in auth.stdout + auth.stderr: raise ValueError("ChatGPT login required")
    runtime = {"version": version, "prefix": prefix, "authentication": "chatgpt", "workers": 1,
               "timeout_seconds": 600, "dev_smoke": True, "started_unix": time.time()}
    cli.save(gen / "runtime.json", runtime); d.capture(gen, npm_root, Path(d.__file__))
    commands = {m: cli.cli_command(prefix, empty.resolve(), p.resolve()) for m, p in instruction_paths.items()}
    cli.save(gen / "commands.json", commands); cli.save(gen / "manifest.json", record); cli.save(gen / "tasks.json", list(tasks.values()))
    cli.save(gen / "status.json", {"state": "running", "dev_smoke": True, "planned_assignments": 9})
    for name, digest in record["source_sha256"].items():
        if sha(ROOT / name) != digest: raise ValueError("Development source changed after preparation")
        destination = gen / "sources" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    ctx = multiprocessing.get_context("spawn"); manager = ctx.Manager(); semaphore = manager.BoundedSemaphore(2)
    completed = 0
    stop_reason = None
    try:
        with ProcessPoolExecutor(max_workers=1, mp_context=ctx, initializer=d._worker_init, initargs=(semaphore,)) as pool:
            for cell in record["cells"]:
                assignment = gen / "assignments" / cell["id"]
                result = pool.submit(d.run_assignment_worker, {"assignment": str(assignment), "task": tasks[cell["task_id"]],
                        "cell": cell, "command": commands[cell["method"]]}).result()
                cli.save(gen / f"result-{cell['id']}.json", result)
                completed += 1
                if result.get("stop_hint") or result.get("state") != "completed":
                    stop_reason = result.get("stop_hint") or result.get("state")
                    break
    finally:
        manager.shutdown()
    cli.save(gen / "status.json", {"state": "generation_finished" if completed == 9 else "paused", "dev_smoke": True,
                                    "assignments_attempted": completed, "planned_assignments": 9,
                                    "stop_reason": stop_reason, "finished_unix": time.time()})
    return {"execution_root": str(execution_root), "assignments": len(record["cells"]), "model_calls": "recorded in turns"}

def main():
    p = argparse.ArgumentParser(); p.add_argument("--tasks", type=Path, default=Path("reproducibility/results/20260909_scc_dev3/native-preparation/prepared.jsonl")); p.add_argument("--out", type=Path, required=True); p.add_argument("--execute", action="store_true"); p.add_argument("--execution-root", type=Path); p.add_argument("--npm-root", type=Path, default=Path("tmp/codex-runtime"))
    a = p.parse_args(); record = prepare(a.tasks.resolve(), a.out.resolve())
    result = {"ok": True, "tasks": record["task_ids"], "assignments": len(record["cells"]), "model_calls": 0}
    if a.execute:
        if a.execution_root is None: raise ValueError("--execution-root is required with --execute")
        result.update(execute(record, a.tasks.resolve(), a.out.resolve(), a.execution_root, a.npm_root))
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__": main()
