"""Audit the SWE dev1 completion archive without executing Docker or models.

The audit joins the frozen ten-cell assignment, the original two observed
evaluations, and a prospective eight-cell completion archive.  It is strict
about completed cells and conservative about interrupted turns: unavailable
usage is reported as unknown and never replaced with zero.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .. import codex_subscription as c
from ..benchmark_bridge import _extract_fenced_block

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = ROOT / "reproducibility/runs/swe-completion-v1"
DEFAULT_ORIGINAL_ROOT = ROOT / "reproducibility/runs/swe-smoke-dev1"
TASK_ID = "pvlib__pvlib-python-1606"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def files_tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): sha(p)
        for p in sorted(root.rglob("*"), key=lambda x: x.relative_to(root).as_posix().encode())
        if p.is_file()
    }


def _normal_patch(value: str) -> str:
    return value.replace("\r\n", "\n").rstrip("\n")


def _cell_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in manifest["cells"]}


def _task_map(path: Path) -> dict[str, dict[str, Any]]:
    data = jsonl(path) if path.suffix == ".jsonl" else read(path)
    return {str(row["task_id"]): row for row in data}


def verify_original_tree(original_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    expected = manifest.get("original_tree", {})
    actual = files_tree(original_root / "generation")
    return {
        "ok": expected == actual,
        "expected_file_count": len(expected),
        "actual_file_count": len(actual),
        "expected_tree_sha256": hashlib.sha256(
            "".join(f"{k}\0{v}\n" for k, v in sorted(expected.items())).encode()
        ).hexdigest(),
        "actual_tree_sha256": hashlib.sha256(
            "".join(f"{k}\0{v}\n" for k, v in sorted(actual.items())).encode()
        ).hexdigest(),
        "unexpected_or_changed": sorted(set(expected) ^ set(actual)),
    }


def _stage_dirs(generation: Path, cell_id: str) -> list[Path]:
    return sorted(
        (p for p in (generation / "turns").glob(f"{cell_id}-*") if p.is_dir()),
        key=lambda p: int(p.name.rsplit("-", 1)[1]),
    )


def audit_generation_cell(generation: Path, cell: dict[str, Any], tasks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cell_id = str(cell["id"])
    errors: list[str] = []
    stages = _stage_dirs(generation, cell_id)
    history: list[str] = []
    turn_rows: list[dict[str, Any]] = []
    known_turns = 0
    unknown_turns = 0
    known_total_tokens = 0
    known_api_equivalent_usd = 0.0
    task = tasks.get(str(cell["task_id"]))
    for stage_dir in stages:
        stage = int(stage_dir.name.rsplit("-", 1)[1])
        prompt_path = stage_dir / "prompt.txt"
        if task is not None and prompt_path.exists():
            try:
                expected_prompt = c.prompt_for(task, cell, stage, history)
                if prompt_path.read_bytes() != expected_prompt.encode("utf-8"):
                    errors.append(f"stage {stage}: forwarded prompt differs")
            except Exception as exc:
                errors.append(f"stage {stage}: prompt reconstruction failed: {exc}")
        result_path = stage_dir / "result.json"
        events_path = stage_dir / "events.jsonl"
        if result_path.exists() and events_path.exists():
            try:
                parsed = c.parse_events(events_path.read_bytes())
                saved = read(result_path)
                for name, expected in saved.get('files_sha256', {}).items():
                    if not (stage_dir / name).is_file() or sha(stage_dir / name) != expected:
                        errors.append(f'stage {stage}: changed archived {name}')
                if saved.get("final_text") != parsed["final_text"] or saved.get("usage") != parsed["usage"]:
                    errors.append(f"stage {stage}: saved result differs from raw events")
                history.append(parsed["final_text"])
                known_turns += 1
                known_total_tokens += parsed["usage"]["input_tokens"] + parsed["usage"]["output_tokens"]
                known_api_equivalent_usd += parsed["api_equivalent_usd"]
                turn_rows.append({"stage": stage, "known_usage": True, "result_sha256": sha(result_path)})
            except Exception as exc:
                errors.append(f"stage {stage}: invalid completed trace: {exc}")
                unknown_turns += 1
                turn_rows.append({"stage": stage, "known_usage": False})
        else:
            unknown_turns += 1
            turn_rows.append({"stage": stage, "known_usage": False})

    cell_path = generation / "cells" / f"{cell_id}.json"
    row = read(cell_path) if cell_path.exists() else None
    complete = row is not None and len(history) == int(cell["cli_turns"])
    if row is not None:
        if not history or row.get("final_text") != history[-1]:
            errors.append("cell final_text does not match final parsed stage")
        if len(history) == int(cell["cli_turns"]):
            if row.get("total_tokens") != known_total_tokens:
                errors.append("cell total_tokens does not match parsed stage usage")
            if row.get("api_equivalent_usd") is not None and abs(row["api_equivalent_usd"] - known_api_equivalent_usd) > 1e-12:
                errors.append("cell API valuation does not match parsed stage usage")
        expected_patch, format_valid = _extract_fenced_block(row.get("final_text", ""), "swebench")
    else:
        expected_patch, format_valid = "", False
    return {
        "cell_id": cell_id,
        "task_id": cell["task_id"],
        "arm": cell["arm"],
        "replicate_id": cell["replicate_id"],
        "cli_turns": cell["cli_turns"],
        "generation_status": "completed" if complete and not errors else "incomplete" if row is None else "invalid",
        "generation_complete": complete and not errors,
        "generation_result_sha256": sha(cell_path) if cell_path.exists() else None,
        "generation_format_valid": format_valid,
        "final_text": row.get("final_text") if row else None,
        "extracted_patch_sha256": hashlib.sha256(expected_patch.encode()).hexdigest() if format_valid else None,
        "known_turns": known_turns,
        "unknown_turns": unknown_turns,
        "known_total_tokens": known_total_tokens,
        "known_api_equivalent_usd": known_api_equivalent_usd,
        "turns": turn_rows,
        "total_tokens": row.get("total_tokens") if row else None,
        "api_equivalent_usd": row.get("api_equivalent_usd") if row else None,
        "errors": errors,
    }


def audit_prediction(archive: Path, cell: dict[str, Any], generation_row: dict[str, Any], expected_label: str | None = None) -> dict[str, Any]:
    path = archive / "predictions" / f"{cell['id']}.jsonl"
    if expected_label is not None:
        path = archive / "predictions" / f"{expected_label}.jsonl"
    result = {"prediction_path": str(path), "prediction_sha256": sha(path) if path.exists() else None}
    if not path.exists():
        result["prediction_status"] = "missing"
        return result
    rows = jsonl(path)
    if len(rows) != 1:
        result["prediction_status"] = "invalid_row_count"
        return result
    pred = rows[0]
    expected_patch, format_valid = _extract_fenced_block(generation_row.get("final_text", ""), "swebench")
    expected_label = expected_label or f"completion-{cell['arm']}--r{cell['replicate_id']}"
    ok = (
        pred.get("instance_id") == cell["task_id"]
        and pred.get("model_name_or_path") == expected_label
        and isinstance(pred.get("model_patch"), str)
        and pred["model_patch"] == expected_patch
    )
    result.update({"prediction_status": "valid" if ok else "invalid_join", "format_valid": format_valid,
                   "model_patch_sha256": hashlib.sha256(pred.get("model_patch", "").encode()).hexdigest()})
    return result


def audit_native(eval_dir: Path, prediction: dict[str, Any] | None) -> dict[str, Any]:
    join_path = eval_dir / "join_validation.json"
    if not join_path.exists():
        return {"native_status": "missing", "join_sha256": None}
    saved = read(join_path)
    provenance_path = eval_dir / "provenance.json"
    argv_path = eval_dir / "argv.json"
    snap = eval_dir / "input" / "predictions.jsonl"
    if not provenance_path.exists() or not argv_path.exists() or not snap.exists() or prediction is None:
        return {"native_status": "invalid_input_join", "join_sha256": sha(join_path)}
    provenance = read(provenance_path)
    rows = jsonl(snap)
    if len(rows) != 1:
        return {"native_status": "invalid_input_join", "join_sha256": sha(join_path)}
    pred = rows[0]
    source = Path(prediction["prediction_path"])
    if not source.exists() or snap.read_bytes() != source.read_bytes():
        return {"native_status": "invalid_input_join", "join_sha256": sha(join_path), "native_input_matches_prediction": False}
    run_id = provenance.get("run_id")
    report_dir = eval_dir / "logs" / "evaluation" / str(run_id)
    try:
        from .evaluate_predictions import validate_join
        recomputed = validate_join(report_dir, pred["instance_id"], pred["model_name_or_path"], pred.get("model_patch"), provenance.get("status") == "outer_timeout")
    except Exception:
        return {"native_status": "invalid_join", "join_sha256": sha(join_path)}
    comparable = ("classification", "status", "report_sha256", "results_sha256", "report_task_id_exact", "report_flags_valid", "patch_bytes_match", "artifact_hashes")
    if any(saved.get(key) != recomputed.get(key) for key in comparable):
        return {"native_status": "invalid_join", "join_sha256": sha(join_path), "recomputed": recomputed}
    classification = recomputed["classification"]
    resolved = False if recomputed["status"] == "complete" and classification in {
        "native_application_rejection", "invalid_candidate_patch", "candidate_test_or_patch_failure"
    } else None
    if recomputed["status"] == "complete" and classification == "completed":
        flags = recomputed.get("report_flags") or {}
        resolved = flags.get("resolved") if type(flags.get("resolved")) is bool else None
    result = {"native_status": recomputed["status"], "classification": classification,
              "resolved": resolved, "join_sha256": sha(join_path),
              "native_input_matches_prediction": True, "recomputed": recomputed,
              "environment": {k: provenance.get(k) for k in ('source_commit','dataset_sha256','original_parquet_sha256','custom_image_id','controller_image_id')}}
    return result


def original_usage_counts(original_root: Path) -> tuple[int, int, int, float]:
    known = unknown = 0
    tokens = 0
    valuation = 0.0
    for folder in (original_root / "generation" / "turns").iterdir():
        if not folder.is_dir():
            continue
        result = folder / "result.json"
        events = folder / "events.jsonl"
        if result.exists() and events.exists():
            try:
                parsed = c.parse_events(events.read_bytes())
                saved = read(result)
                if parsed["usage"] == saved.get("usage"):
                    known += 1
                    tokens += parsed["usage"]["input_tokens"] + parsed["usage"]["output_tokens"]
                    valuation += parsed["api_equivalent_usd"]
                    continue
            except Exception:
                pass
        unknown += 1
    return known, unknown, tokens, valuation


def find_control(root: Path, label: str) -> dict[str, Any]:
    if not root.is_dir():
        return {"status": "missing", "label": label}
    results_files = list(root.rglob("results.json"))
    join_path = root / "join_validation.json"
    snap = root / "input" / "predictions.jsonl"
    if len(results_files) != 1 or not join_path.exists() or not snap.exists():
        return {"status": "invalid", "label": label, "reason": "control provenance/join/snapshot incomplete"}
    native = audit_native(root, {"prediction_path": str(snap)})
    expected = label == "gold"
    expectation_met = native.get("native_status") == "complete" and native.get("resolved") is expected
    return {"status": "verified" if expectation_met else "invalid", "label": label,
            "results_sha256": sha(results_files[0]), "join_sha256": native.get("join_sha256"),
            "native_status": native.get("native_status"), "resolved": native.get("resolved"),
            "expected": expected, "expectation_met": expectation_met, "environment": native.get('environment')}


def audit(archive: Path, out: Path, original_root: Path | None = None, controls: Path | None = None) -> dict[str, Any]:
    archive = archive.resolve(); original_root = (original_root or archive.parent).resolve()
    manifest = read(archive / "manifest.json")
    original_manifest = {"original_tree": manifest.get("original_tree", {})}
    tree = verify_original_tree(original_root, original_manifest)
    tasks = _task_map(archive / "tasks.jsonl")
    cells = _cell_map(manifest)
    rows: list[dict[str, Any]] = []
    new_known = new_unknown = 0
    for cell in manifest.get("cells", []):
        cid = str(cell["id"])
        gen = audit_generation_cell(archive / "generation" / cid, cell, tasks)
        pred = audit_prediction(archive, cell, {"final_text": gen.get("final_text")} ) if gen["generation_complete"] else {"prediction_status": "missing"}
        native = audit_native(archive / "evaluations" / cid, pred if pred.get("prediction_status") == "valid" else None)
        row = {**cell, "attempt": "completion", "deadline_seconds": 600,
               "attempt_kind": "recovery_after_started_failure" if cell['original_status'] == 'started_incomplete' else 'first_submission_after_stop',
               **gen, **pred, **native}
        rows.append(row); new_known += gen["known_turns"]; new_unknown += gen["unknown_turns"]

    original_manifest_path = original_root / "generation" / "manifest.json"
    original_rows = jsonl(original_root / "generation" / "results.jsonl") if (original_root / "generation" / "results.jsonl").exists() else []
    original_by_id = {str(row["id"]): row for row in original_rows}
    original_tasks = _task_map(original_root / "generation" / "tasks.json")
    for cell in manifest.get("original_inventory", []):
        if cell.get("original_status") != "completed":
            continue
        cid = str(cell["id"]); gen_row = original_by_id.get(cid, {})
        gen = audit_generation_cell(original_root / "generation", cell, original_tasks)
        eval_name = f"{cell['arm']}--r{cell['replicate_id']}"
        pred = audit_prediction(original_root, cell, {"final_text": gen.get("final_text")}, expected_label=eval_name) if gen["generation_complete"] else {"prediction_status": "missing"}
        native = audit_native(original_root / "evaluations" / eval_name, pred if pred.get("prediction_status") == "valid" else None)
        rows.append({**cell, "attempt": "original", "deadline_seconds": 180, "attempt_kind": "original_first_attempt", **gen, **pred, **native,
                     "total_tokens": gen_row.get("total_tokens"), "api_equivalent_usd": gen_row.get("api_equivalent_usd")})

    control_root = (controls or archive / "controls")
    controls_result = {"gold": find_control(control_root / "gold", "gold"), "negative": find_control(control_root / "negative", "negative")}
    control_environment = controls_result['gold'].get('environment')
    environment_match = bool(control_environment) and controls_result['negative'].get('environment') == control_environment and all(r.get('environment') == control_environment for r in rows)
    original_known, original_unknown, original_tokens, original_valuation = original_usage_counts(original_root)
    original_turns = original_known + original_unknown
    summary = {
        "schema": "swe-dev1-completion-evidence-v1", "assignment_count": len(manifest.get("original_inventory", [])),
        "rows": rows, "original_tree": tree, "controls": controls_result, "all_native_environments_match_controls": environment_match,
        "turn_usage": {"original_submitted_turns": original_turns, "original_known_turns": original_known, "original_unknown_turns": original_unknown,
                        "new_assigned_turns": sum(int(x["cli_turns"]) for x in manifest.get("cells", [])),
                        "new_known_turns": new_known, "new_unknown_turns": new_unknown,
                        "original_known_total_tokens": original_tokens, "original_known_api_equivalent_usd": original_valuation,
                        "new_known_total_tokens": sum(r.get("known_total_tokens", 0) for r in rows if r.get("attempt") == "completion"),
                        "new_known_api_equivalent_usd": sum(r.get("known_api_equivalent_usd", 0) for r in rows if r.get("attempt") == "completion")},
        "source_hashes": {"manifest": sha(archive / "manifest.json"), "tasks": sha(archive / "tasks.jsonl"),
                          "protocol": sha(archive / "protocol.md") if (archive / "protocol.md").exists() else None,
                          "original_manifest": sha(original_manifest_path) if original_manifest_path.exists() else None,
                          "archived_sources": {p.relative_to(archive).as_posix(): sha(p) for p in sorted((archive / "sources").rglob("*")) if p.is_file()}},
        "status": "valid" if (
            tree["ok"] and len(rows) == 10 and environment_match
            and all(r.get("generation_complete") and r.get("prediction_status") == "valid" and r.get("native_status") == "complete" and not r.get("errors", []) for r in rows)
            and all(v.get("expectation_met") for v in controls_result.values())
        ) else "invalid",
    }
    out = out.resolve(); out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["id", "arm", "replicate_id", "attempt", "generation_status", "native_status", "classification", "resolved", "known_turns", "unknown_turns", "total_tokens", "api_equivalent_usd", "generation_result_sha256", "prediction_sha256", "join_sha256"]
    with (out / "rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows({k: row.get(k) for k in fields} for row in rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--original-root", type=Path, default=DEFAULT_ORIGINAL_ROOT)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = audit(args.archive, args.out, args.original_root, args.controls)
    print(json.dumps({"status": summary["status"], "rows": len(summary["rows"])}, ensure_ascii=False))
    if summary['status'] != 'valid':
        raise SystemExit(1)


if __name__ == "__main__":
    main()
