"""Freeze/export and post-generation collection for the segregation-80 study.

This module deliberately has no model entry point.  ``export`` reads an already
archived dispatch and writes evaluator samples; ``collect`` joins those samples
to immutable native reports and the complete generation ledger.  Missing work is
represented explicitly instead of being dropped from the 320-cell denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .. import benchmark_bridge as bridge
from .. import codex_subscription as c
from ..heldout200.evidence import environment_from_gate
from ..scale_env.validate_native import sha256, validate_native
from . import dispatch
from .prepare import ARM_NAMES

ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_json(value: Any) -> str:
    return c.digest(value)


def _cells(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cells = manifest.get("cells")
    if not isinstance(cells, list) or len(cells) != 320:
        raise ValueError("segregation manifest must contain exactly 320 cells")
    result = {x["id"]: x for x in cells}
    if len(result) != len(cells):
        raise ValueError("duplicate cell id in frozen manifest")
    return result


def _verify_dispatch_inputs(archive: Path, inputs: Path, gate: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _json(manifest_path)
    if manifest != dispatch.plan(inputs, gate):
        raise ValueError("dispatch manifest does not match frozen inputs, gate, or sources")
    saved = archive / "manifest.json"
    if saved.exists() and _json(saved) != manifest:
        raise ValueError("archive manifest differs from frozen dispatch manifest")
    return manifest


def _cell_record(archive: Path, cell: dict[str, Any]) -> dict[str, Any] | None:
    path = archive / "cells" / (cell["id"] + ".json")
    return _json(path) if path.exists() else None


def _verify_turn(archive: Path, cell: dict[str, Any], record: dict[str, Any], prompt: str, runtime: dict[str, Any]) -> dict[str, Any]:
    """Reparse the retained CLI evidence and compare it with the saved result."""
    if any(record.get(k) != v for k, v in cell.items()):
        raise ValueError('Cell labels or frozen prompt identity changed')
    turn = archive / "turns" / cell["id"]
    if not turn.is_dir():
        raise ValueError(f"missing turn archive: {cell['id']}")
    prompt_bytes = (turn / "prompt.txt").read_bytes()
    if prompt_bytes != prompt.encode("utf-8"):
        raise ValueError(f"prompt bytes differ from frozen arm input: {cell['id']}")
    if _digest_bytes(prompt_bytes) != cell["prompt_sha256"]:
        raise ValueError(f"prompt hash mismatch: {cell['id']}")
    argv = _json(turn / "argv.json")
    status = _json(turn / "status.json")
    events = turn / "events.jsonl"
    result_path = turn / "result.json"
    if not events.exists():
        raise ValueError(f"events missing: {cell['id']}")
    if record.get("generation_complete"):
        if status.get("state") != "completed" or not result_path.exists():
            raise ValueError(f"completed cell has no completed result: {cell['id']}")
        parsed = c.parse_events(events.read_bytes())
        saved = _json(result_path)
        for key in ("final_text", "usage", "api_equivalent_usd", "uncached_sensitivity_usd"):
            if parsed.get(key) != saved.get(key) or parsed.get(key) != record.get(key):
                raise ValueError(f"saved/parsed result mismatch ({key}): {cell['id']}")
        files = saved.get("files_sha256", {})
        for name in ("prompt.txt", "argv.json", "events.jsonl", "stderr.txt"):
            if files.get(name) != sha256(turn / name):
                raise ValueError(f"turn evidence hash mismatch ({name}): {cell['id']}")
    else:
        if status.get("state") not in ("blocked", "started"):
            raise ValueError(f"unexpected incomplete status: {cell['id']}")
    if runtime.get("version") != c.CLI_VERSION:
        raise ValueError("archived CLI version differs from frozen version")
    instructions = archive / "instructions.txt"
    if not instructions.exists() or instructions.read_bytes() != c.BASE.encode("utf-8"):
        raise ValueError("archived instruction file differs from frozen CLI policy")
    if not isinstance(runtime.get("prefix"), list) or not runtime["prefix"]:
        raise ValueError("runtime lacks portable CLI prefix")
    try:
        cwd = Path(argv[argv.index("--cd") + 1])
        archived_instruction = next(json.loads(value.split('=', 1)[1]) for value in argv if value.startswith('model_instructions_file='))
    except (ValueError, IndexError, StopIteration):
        raise ValueError("archived argv has no --cd working directory")
    # Reconstruct configuration from the old path string without dereferencing it.
    # The actual instruction bytes come only from this portable archive.
    expected_argv = c.cli_command(runtime["prefix"], cwd, Path(archived_instruction))
    if argv != expected_argv:
        raise ValueError(f"archived CLI argv differs from frozen configuration: {cell['id']}")
    interrupted = None
    for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            interrupted = event["usage"]
    if record.get("interrupted_usage") != interrupted and not record.get("generation_complete"):
        raise ValueError(f"interrupted usage differs from raw events: {cell['id']}")
    if record.get("generation_complete"):
        usage = record.get("usage", {})
        if record.get("total_tokens") != usage.get("input_tokens", 0) + usage.get("output_tokens", 0):
            raise ValueError(f"total token accounting mismatch: {cell['id']}")
    return {"argv": argv, "status": status, "turn": str(turn),
            "instruction_sha256": _digest_bytes(instructions.read_bytes()),
            "interrupted_usage": interrupted}


def _extract(text: str) -> tuple[str, bool]:
    return bridge._extract_fenced_block(text, "bigcodebench")


def export_candidates(archive: Path, inputs: Path, gate: Path, manifest_path: Path, out: Path) -> None:
    manifest = _verify_dispatch_inputs(archive, inputs, gate, manifest_path)
    cells = _cells(manifest)
    rows = {a: {r["task_id"]: r for r in c.tasks_from(inputs / "input" / (a + ".jsonl"))} for a in ARM_NAMES}
    runtime_path = archive / "runtime.json"
    if not runtime_path.exists() or _json(archive / "status.json").get("state") not in ("completed", "incomplete"):
        raise ValueError("generation archive must have a terminal status before export")
    runtime = _json(runtime_path)
    assigned = list(manifest["assigned_task_ids"])
    exported: dict[str, list[dict[str, Any]]] = {a: [] for a in ARM_NAMES}
    ledger: list[dict[str, Any]] = []
    argv_digest = None
    instruction_digest = None
    for cell in manifest["cells"]:
        record = _cell_record(archive, cell)
        prompt = dispatch.full_prompt(rows[cell["arm"]][cell["task_id"]])
        if record is not None:
            evidence = _verify_turn(archive, cell, record, prompt, runtime)
            current_argv_digest = _digest_json(evidence["argv"])
            if argv_digest is None:
                argv_digest = current_argv_digest
                instruction_digest = evidence["instruction_sha256"]
            elif current_argv_digest != argv_digest or evidence["instruction_sha256"] != instruction_digest:
                raise ValueError("CLI argv or instruction file changed between turns")
        else:
            evidence = None
        item = {"id": cell["id"], "task_id": cell["task_id"], "arm": cell["arm"],
                "generation_complete": bool(record and record.get("generation_complete")),
                "failure_reason": record.get("failure_reason") if record else "generation record missing"}
        if record:
            for key in ("usage", "interrupted_usage", "total_tokens", "api_equivalent_usd", "uncached_sensitivity_usd"):
                if key in record:
                    item[key] = record[key]
        if evidence:
            item["argv_sha256"] = _digest_json(evidence["argv"])
        if record and record.get("generation_complete"):
            solution, format_ok = _extract(record.get("final_text", ""))
            exported[cell["arm"]].append({"task_id": cell["task_id"], "solution": solution})
            item.update({"format_extracted": format_ok, "solution_sha256": _digest_bytes(solution.encode("utf-8"))})
        ledger.append(item)
    out = out.resolve()
    if out.exists():
        raise ValueError("refusing to overwrite candidate export")
    out.mkdir(parents=True)
    sample_hashes = {}
    for arm in ARM_NAMES:
        # Assignment order is the frozen order, rather than completion order.
        by_id = {r["task_id"]: r for r in exported[arm]}
        ordered = [by_id[t] for t in assigned if t in by_id]
        data = b"".join(c.canonical(r) + b"\n" for r in ordered)
        path = out / (arm + ".jsonl")
        path.write_bytes(data)
        sample_hashes[arm] = {"sha256": _digest_bytes(data), "task_ids": [r["task_id"] for r in ordered]}
    _write_json(out / "generation_ledger.json", ledger)
    export_manifest = {
        "schema": "segregation80-export-v1", "frozen_manifest_sha256": _digest_json(manifest),
        "archive_manifest_sha256": _digest_bytes((archive / "manifest.json").read_bytes()) if (archive / "manifest.json").exists() else None,
        "assigned_task_ids": assigned, "arms": list(ARM_NAMES), "planned_candidates": 320,
        "sample_hashes": sample_hashes,
        "cli_argv_sha256": argv_digest, "instructions_sha256": instruction_digest,
        "generation_complete": sum(x["generation_complete"] for x in ledger),
        "ledger_sha256": sha256(out / "generation_ledger.json"),
        "exported_solution_source": "result.json final_text -> exactly one python fenced block; empty solution retained when extraction fails",
    }
    _write_json(out / "export_manifest.json", export_manifest)


def collect_results(archive: Path, export_dir: Path, native_dir: Path, gate_dir: Path, manifest_path: Path, out: Path, inputs: Path | None = None) -> None:
    manifest = _json(manifest_path)
    if _digest_json(manifest) != _json(export_dir / "export_manifest.json")["frozen_manifest_sha256"]:
        raise ValueError("export was made from a different frozen generation manifest")
    export_meta = _json(export_dir / "export_manifest.json")
    if not archive.exists() or not (archive / "status.json").exists() or _json(archive / "status.json").get("state") not in ("completed", "incomplete"):
        raise ValueError("generation archive must be terminal before collection")
    runtime = _json(archive / "runtime.json")
    cells = _cells(manifest)
    inputs_dir = inputs or (ROOT / "reproducibility" / "segregation80" / "inputs-v2")
    _verify_dispatch_inputs(archive, inputs_dir, gate_dir / 'heldout200_control_gate.json', manifest_path)
    rows = {a: {r["task_id"]: r for r in c.tasks_from(inputs_dir / "input" / (a + ".jsonl"))} for a in ARM_NAMES}
    # Rebuild every record from the archived cell and turn evidence.  The
    # export ledger is diagnostic and cannot affect the collected estimand.
    rebuilt: dict[str, dict[str, Any]] = {}
    for cell in manifest["cells"]:
        record = _cell_record(archive, cell)
        if record is None:
            rebuilt[cell["id"]] = {"id": cell["id"], "task_id": cell["task_id"], "arm": cell["arm"], "generation_complete": False, "failure_reason": "generation record missing"}
            continue
        prompt = dispatch.full_prompt(rows[cell["arm"]][cell["task_id"]])
        _verify_turn(archive, cell, record, prompt, runtime)
        rebuilt[cell["id"]] = {"id": cell["id"], "task_id": cell["task_id"], "arm": cell["arm"], **record}
    ledger = [rebuilt[cell["id"]] for cell in manifest["cells"]]
    ledger_by_id = rebuilt
    environment = environment_from_gate(gate_dir)
    control_gate = _json(gate_dir / "heldout200_control_gate.json")
    control_ids = list(control_gate.get("assigned_task_ids", []))
    if control_ids != list(manifest["assigned_task_ids"]):
        raise ValueError("native control gate task order differs from generation assignment")
    eligible_ids = [tid for tid in control_ids
                    if control_gate.get("status_by_task", {}).get(tid, {}).get("gold") == "pass"
                    and control_gate.get("status_by_task", {}).get(tid, {}).get("incorrect") == "fail"]
    native_status: dict[str, dict[str, str | None]] = {}
    native_audit: dict[str, Any] = {}
    assigned = list(manifest["assigned_task_ids"])
    for arm in ARM_NAMES:
        sample_path = export_dir / (arm + ".jsonl")
        sample_rows = [json.loads(x) for x in sample_path.read_text(encoding="utf-8").splitlines() if x.strip()] if sample_path.exists() else []
        source_by_task = {entry['task_id']: entry for entry in ledger if entry['arm'] == arm and entry.get('generation_complete')}
        reconstructed = [{'task_id': t, 'solution': _extract(source_by_task[t]['final_text'])[0]} for t in assigned if t in source_by_task]
        if sample_rows != reconstructed or sha256(sample_path) != export_meta['sample_hashes'][arm]['sha256']:
            raise ValueError(f'Export differs from exact original generated programs: {arm}')
        expected = {r["task_id"]: r["solution"] for r in sample_rows}
        folder = native_dir / arm
        checked = validate_native(folder, expected, environment) if expected else {"ok": True, "errors": [], "statuses": {}}
        if expected and not checked["ok"]:
            raise ValueError(f"native evidence failed integrity for {arm}: {checked['errors']}")
        if expected and (folder / "input" / "samples.jsonl").exists():
            staged = [json.loads(x) for x in (folder / "input" / "samples.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            if staged != sample_rows:
                raise ValueError(f"native staged code differs from exported code: {arm}")
        native_status[arm] = checked["statuses"]
        native_audit[arm] = {"expected_task_ids": list(expected), "validation": checked}
    records = []
    generation_ledger = []
    for cell in manifest["cells"]:
        entry = ledger_by_id.get(cell["id"])
        complete = bool(entry and entry.get("generation_complete"))
        status = native_status[cell["arm"]].get(cell["task_id"]) if complete else None
        eligible = cell["task_id"] in eligible_ids
        quality = (status == "pass") if complete and eligible and status in ("pass", "fail", "timeout") else None
        reason = "native_pass_fail_timeout" if quality is not None else ("control_unavailable" if complete and not eligible else "generation_missing")
        row = {"task_id": cell["task_id"], "arm": cell["arm"], "quality": quality,
               "outcome_type": reason, "generation_complete": complete, "native_status": status,
               "cell_id": cell["id"]}
        if entry:
            for key in ("total_tokens", "api_equivalent_usd", "uncached_sensitivity_usd"):
                row[key] = entry.get(key)
            generation_ledger.append({**entry, "usage_known": bool(entry.get("usage") or entry.get("interrupted_usage"))})
        else:
            generation_ledger.append({"id": cell["id"], "task_id": cell["task_id"], "arm": cell["arm"], "usage_known": False, "failure_reason": "generation record missing"})
        records.append(row)
    out = out.resolve()
    if out.exists():
        raise ValueError("refusing to overwrite collection")
    out.mkdir(parents=True)
    for name, value in (("candidate_records.jsonl", records), ("generation_ledger.json", generation_ledger)):
        if name.endswith(".jsonl"):
            (out / name).write_bytes(b"".join(c.canonical(r) + b"\n" for r in value))
        else:
            _write_json(out / name, value)
    _write_json(out / "native_audit.json", native_audit)
    _write_json(out / "collection_manifest.json", {
        "schema": "segregation80-collection-v1", "frozen_manifest_sha256": _digest_json(manifest),
        "export_manifest_sha256": sha256(export_dir / "export_manifest.json"),
        "generation_ledger_sha256": sha256(out / "generation_ledger.json"),
        "candidate_records_sha256": sha256(out / "candidate_records.jsonl"),
        "assigned_candidates": len(records), "quality_observed": sum(r["quality"] is not None for r in records),
        "native_arms": list(ARM_NAMES), "native_audit": native_audit,
    })


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    e = sub.add_parser("export")
    for name in ("archive", "inputs", "gate", "manifest", "out"):
        e.add_argument("--" + name, type=Path, required=True)
    q = sub.add_parser("collect")
    for name in ("archive", "export-dir", "native-dir", "gate-dir", "manifest", "out"):
        q.add_argument("--" + name, type=Path, required=True)
    q.add_argument("--inputs", type=Path)
    a = p.parse_args()
    if a.command == "export":
        export_candidates(a.archive, a.inputs, a.gate, a.manifest, a.out)
    else:
        collect_results(a.archive, a.export_dir, a.native_dir, a.gate_dir, a.manifest, a.out, a.inputs)


if __name__ == "__main__":
    main()
