"""Audit complete or partial exploratory INoT archives without rerunning them."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .. import codex_subscription as c
from ..audit_codex_pilot import inventory_attempt
from ..benchmark_bridge import _extract_fenced_block
from .inot import REPLICATE_ID, TREATMENT, ordered_tasks, plan, prompt_for


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_runtime(archive: Path, manifest: dict[str, Any]) -> None:
    runtime = c.read(archive / "runtime.json")
    provenance = c.read(archive / "runtime_provenance.json")
    if runtime.get("version") != c.CLI_VERSION or runtime.get("authentication") != "chatgpt":
        raise ValueError("CLI version or authentication provenance mismatch")
    if runtime.get("workers") != 2 or runtime.get("timeout_seconds") != 180:
        raise ValueError("runtime limits changed")
    if provenance.get("cli_version") != runtime.get("version") or provenance.get("prefix") != runtime.get("prefix"):
        raise ValueError("runtime prefix/version mismatch")
    if provenance.get("package_version") != "0.153.4" or not provenance.get("native_executable_sha256"):
        raise ValueError("missing official CLI package/binary provenance")
    if provenance.get("instructions_sha256") != sha256(archive / "instructions.txt"):
        raise ValueError("loaded instructions changed")
    if provenance.get("npm_lock_sha256") != sha256(archive / "npm-package-lock.json"):
        raise ValueError("npm lock changed")


def _check_argv(argv: list[str]) -> None:
    for flag in ("--ignore-user-config", "--strict-config", "--ephemeral", "--json", "--skip-git-repo-check"):
        if flag not in argv:
            raise ValueError("CLI flag changed: " + flag)
    if "--model" not in argv or argv[argv.index("--model") + 1] != c.MODEL:
        raise ValueError("CLI model changed")
    if "--sandbox" not in argv or argv[argv.index("--sandbox") + 1] != "read-only":
        raise ValueError("CLI sandbox changed")
    required = {
        "features.shell_tool": "false", "features.multi_agent": "false",
        "features.apps": "false", "features.plugins": "false",
        "features.in_app_browser": "false", "features.image_generation": "false",
        "tools.update_plan.enabled": "false", "tools.experimental_request_user_input.enabled": "false",
        "web_search": '"disabled"', "model_reasoning_effort": '"medium"',
    }
    for key, value in required.items():
        token = "-c"
        pairs = [argv[i + 1] for i, item in enumerate(argv[:-1]) if item == token]
        if key + "=" + value not in pairs:
            raise ValueError("CLI setting changed: " + key)


def validate_row_against_turn(row: dict[str, Any], parsed: dict[str, Any]) -> None:
    if row.get('model') != c.MODEL or row.get('seed') != REPLICATE_ID:
        raise ValueError('Saved model or repeat label changed')
    usage = parsed['usage']
    if row.get('total_tokens') != usage['input_tokens'] + usage['output_tokens']:
        raise ValueError('Saved total tokens differ from CLI usage')
    if row.get("final_text") != parsed["final_text"] or row.get("usage") != parsed["usage"]:
        raise ValueError("saved cell row differs from original CLI turn")
    if row.get("api_equivalent_usd") != parsed["api_equivalent_usd"] or row.get("uncached_sensitivity_usd") != parsed["uncached_sensitivity_usd"]:
        raise ValueError("saved cell valuation differs from original CLI turn")


def audit(archive: Path, tasks_path: Path, selection_path: Path, gate_path: Path, protocol_path: Path) -> dict[str, Any]:
    archive = archive.resolve()
    tasks = ordered_tasks(tasks_path)
    expected = plan(tasks, protocol_path, selection_path, gate_path, tasks_path)
    observed_manifest = c.read(archive / "manifest.json")
    if observed_manifest != expected:
        raise ValueError("archive manifest differs from frozen task/protocol/control inputs")
    for relative, expected_hash in {
        "protocol.md": expected["protocol_sha256"],
        "inot_source.py": expected["source_sha256_lf"],
        "factorial_runner.py": expected["shared_factorial_runner_sha256_lf"],
        "record_codex_runtime.py": expected["shared_runtime_capture_sha256_lf"],
        "audit_codex_pilot.py": expected["shared_archive_inventory_sha256_lf"],
    }.items():
        if sha256(archive / relative) != expected_hash:
            raise ValueError("archived source/protocol hash mismatch: " + relative)
    if sha256(archive / "selection.json") != expected["selection_sha256"]:
        raise ValueError("selection input changed")
    if sha256(archive / "control-gate.json") != expected["control_gate_sha256"]:
        raise ValueError("control gate input changed")
    _check_runtime(archive, expected)

    if c.read(archive / 'tasks.json') != tasks or (archive / 'instructions.txt').read_bytes() != c.BASE.encode('utf-8'):
        raise ValueError('Archived tasks or loaded instructions changed')
    if sha256(archive / 'runner_source.py') != expected['shared_runner_source_sha256_lf']:
        raise ValueError('Archived shared transport source changed')
    runtime = c.read(archive / 'runtime.json')
    provenance = c.read(archive / 'runtime_provenance.json')
    required_argv = c.cli_command(runtime['prefix'], provenance['empty_working_directory'], provenance['instructions_path'])
    taskmap = {task["task_id"]: task for task in tasks}
    rows = {}
    results_path = archive / "results.jsonl"
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["id"] in rows:
                    raise ValueError("duplicate result cell")
                rows[row["id"]] = row
    expected_ids = {cell["id"] for cell in expected["cells"]}
    if not set(rows).issubset(expected_ids):
        raise ValueError("unexpected result cell")
    cell_files = {f.stem: c.read(f) for f in (archive / 'cells').glob('*.json')}
    if cell_files != rows:
        raise ValueError('Cell files and original result JSONL disagree')
    checked_cells = []
    for cell in expected["cells"]:
        row = rows.get(cell["id"])
        if row is None:
            continue
        if any(row.get(key) != value for key, value in cell.items()):
            raise ValueError("result treatment label changed")
        if row.get("treatment") != TREATMENT or row.get("arm") != TREATMENT or row.get("replicate_id") != REPLICATE_ID:
            raise ValueError("result treatment missing or changed")
        folder = archive / "turns" / cell["id"]
        if not (folder / "events.jsonl").exists() or not (folder / "prompt.txt").exists():
            raise ValueError("complete cell is missing turn evidence")
        if (folder / "prompt.txt").read_bytes() != prompt_for(taskmap[cell["task_id"]]).encode("utf-8"):
            raise ValueError("prompt bytes differ from reconstructed INoT prompt")
        raw = (folder / "events.jsonl").read_bytes()
        parsed = c.parse_events(raw)
        actual_argv = c.read(folder / 'argv.json')
        if actual_argv != required_argv:
            raise ValueError('Exact CLI arguments differ from frozen transport')
        _check_argv(actual_argv)
        if c.read(folder / 'status.json').get('state') != 'completed':
            raise ValueError('Completed candidate contains an unfinished turn')
        result = c.read(folder / "result.json")
        if result.get("final_text") != parsed["final_text"] or result.get("usage") != parsed["usage"]:
            raise ValueError("saved result differs from CLI event stream")
        if result.get("api_equivalent_usd") != parsed["api_equivalent_usd"]:
            raise ValueError("usage valuation changed")
        if set(result.get('files_sha256', {})) != {'prompt.txt', 'argv.json', 'events.jsonl', 'stderr.txt'}:
            raise ValueError('Missing original turn file hashes')
        for name, digest in result['files_sha256'].items():
            if sha256(folder / name) != digest:
                raise ValueError('Original turn artifact changed: ' + name)
        validate_row_against_turn(row, parsed)
        checked_cells.append(cell["id"])
    turn_ids = {folder.name for folder in (archive / "turns").iterdir()}
    if not turn_ids.issubset(expected_ids):
        raise ValueError("unauthorized or orphan turn directory")
    for cell in expected['cells']:
        if cell['id'] in turn_ids and cell['id'] not in rows:
            folder = archive / 'turns' / cell['id']
            if (folder / 'prompt.txt').read_bytes() != prompt_for(taskmap[cell['task_id']]).encode('utf-8'):
                raise ValueError('Incomplete turn prompt changed')
            if c.read(folder / 'argv.json') != required_argv:
                raise ValueError('Incomplete turn CLI arguments changed')
    archive_state = c.read(archive / "status.json").get("state")
    if archive_state not in ('completed', 'blocked'):
        raise ValueError('Wait for terminal archive before auditing')
    if archive_state == "completed" and len(checked_cells) != len(expected["cells"]):
        raise ValueError("completed archive has missing result cells")
    inventory = inventory_attempt(archive)
    c.save(archive / "audit_inventory.json", inventory)
    complete = archive_state == "completed" and len(checked_cells) == len(expected["cells"]) and not inventory["status"].get("failures")
    return {"status": "complete" if complete else "partial", "assigned_cells": len(expected["cells"]),
            "observed_cells": len(checked_cells), "missing_cells": len(expected["cells"]) - len(checked_cells),
            "inventory": inventory}


def export_bigcodebench_code(results_path: Path, manifest_path: Path, out: Path, partial_status: bool = False) -> dict[str, Any]:
    """Export strict observed baseline code; never invent missing assignments."""
    manifest = c.read(manifest_path)
    rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = manifest["task_ids"]
    cells_by_task = {cell["task_id"]: cell for cell in manifest["cells"]}
    seen = set()
    exported = []
    for row in rows:
        if row.get("arm") != TREATMENT or row.get("treatment") != TREATMENT:
            raise ValueError("INoT export requires inot_algorithm_replication rows")
        task_id = row["task_id"]
        if task_id in seen or task_id not in ids:
            raise ValueError("duplicate or unexpected baseline task")
        seen.add(task_id)
        cell = cells_by_task.get(task_id)
        if cell is None or any(row.get(k) != v for k,v in cell.items()) or row.get('seed') != REPLICATE_ID or row.get("model") != c.MODEL or row.get("replicate_id") != REPLICATE_ID:
            raise ValueError("baseline export row does not match frozen INoT cell")
        extracted, ok = _extract_fenced_block(row.get("final_text", ""), "bigcodebench")
        exported.append({"task_id": task_id, "solution": extracted if ok else "", "format_extracted": ok,
                         "model": row["model"], "arm": row["arm"], "treatment": TREATMENT, "seed": row["seed"]})
    if len(seen) != len(set(ids)) and not partial_status:
        raise ValueError("complete baseline export requires every assigned task")
    status = "complete" if len(seen) == len(set(ids)) else "partial_explicit"
    out.mkdir(parents=True, exist_ok=False)
    exported.sort(key=lambda row: ids.index(row["task_id"]))
    out.joinpath("samples.jsonl").write_bytes(b"".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n" for row in exported))
    c.save(out / "assignment-manifest.json", {"assigned_task_ids": ids, "observed_task_ids": [row["task_id"] for row in exported], "status": status})
    return {"status": status, "observed": len(exported), "assigned": len(set(ids))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--gate", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(audit(args.archive, args.tasks, args.selection, args.gate, args.protocol)))


if __name__ == "__main__":
    main()
