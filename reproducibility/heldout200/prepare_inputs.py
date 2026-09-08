"""Freeze the held-out 200 allocation and prepare evaluator-only inputs.

This module performs only mechanical filtering and calls the unchanged bridge
row adapter.  It never emits task tests, reference patches, or prompts into
the public selection record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from ..benchmark_bridge import _prepare_output_row
except ImportError:  # direct script execution from the repository root
    from benchmark_bridge import _prepare_output_row


EXPOSED_NUMBERS = {str(i) for i in range(8)}
COUNT = 200


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_source_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    rows: list[dict[str, Any]] = []
    raw_by_id: dict[str, bytes] = {}
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, 1):
            record = raw.rstrip(b"\r\n")
            if not record.strip():
                continue
            row = json.loads(record.decode("utf-8"))
            task_id = str(row["task_id"])
            if task_id in raw_by_id:
                raise ValueError(f"duplicate task_id in source: {task_id}")
            rows.append(row)
            raw_by_id[task_id] = record
    return rows, raw_by_id


def selected_ids(manifest: dict[str, Any]) -> list[str]:
    reserved = [str(task_id) for task_id in manifest["confirmatory_task_ids"]]
    selected = [task_id for task_id in reserved if task_id.rsplit("/", 1)[-1] not in EXPOSED_NUMBERS]
    if len(selected) < COUNT:
        raise ValueError("confirmatory order has fewer than 200 unexposed IDs")
    result = selected[:COUNT]
    if len(set(result)) != COUNT:
        raise ValueError("held-out selection is not unique")
    return result


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if sha256_file(args.dataset) != manifest["source_sha256"]:
        raise ValueError("source dataset hash differs from frozen split manifest")
    if sha256_file(args.prepared) != manifest["confirmatory_sha256"]:
        raise ValueError("prepared argument must be the frozen confirmatory JSONL")
    ids = selected_ids(manifest)
    _, raw_by_id = read_source_rows(args.dataset)
    missing = [task_id for task_id in ids if task_id not in raw_by_id]
    if missing:
        raise ValueError(f"source dataset missing selected IDs: {missing[:3]}")

    # Re-read complete rows solely to pass the unchanged bridge adapter.
    rows, _ = read_source_rows(args.dataset)
    by_id = {str(row["task_id"]): row for row in rows}
    selected_rows = [by_id[task_id] for task_id in ids]
    model_rows = [_prepare_output_row(row) for row in selected_rows]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {args.output_dir}")
    evaluator_dataset = args.output_dir / "evaluator_dataset.jsonl"
    with evaluator_dataset.open("wb") as handle:
        for task_id in ids:
            handle.write(raw_by_id[task_id])
            handle.write(b"\n")
    write_jsonl(args.output_dir / "prepared.jsonl", model_rows)

    # The controls intentionally mirror the existing dev40 control construction,
    # while using the requested code_prompt + canonical_solution basis.
    gold: list[dict[str, str]] = []
    incorrect: list[dict[str, str]] = []
    for row in selected_rows:
        solution = str(row["code_prompt"]) + str(row["canonical_solution"])
        gold.append({"task_id": str(row["task_id"]), "solution": solution})
        incorrect.append({
            "task_id": str(row["task_id"]),
            "solution": solution + "\n\n# Deliberately incorrect held-out control.\ndef task_func(*args, **kwargs):\n    return None\n",
        })
    write_jsonl(args.output_dir / "gold.jsonl", gold)
    write_jsonl(args.output_dir / "incorrect.jsonl", incorrect)

    selection = {
        "schema": "heldout200-selection-v1",
        "protocol": "reproducibility/revision/HELDOUT200_PROTOCOL.md",
        "selection_rule": "first 200 confirmatory_task_ids after excluding BigCodeBench/0 through BigCodeBench/7",
        "count": COUNT,
        "ids": ids,
        "assigned_task_ids": ids,
        "ids_sha256": sha256_bytes("\n".join(ids).encode("utf-8")),
        "source_dataset_sha256": sha256_file(args.dataset),
        "frozen_confirmatory_sha256": sha256_file(args.prepared),
        "source_row_sha256": {task_id: sha256_bytes(raw_by_id[task_id]) for task_id in ids},
        "evaluator_dataset_sha256": sha256_file(evaluator_dataset),
        "model_input_sha256": sha256_file(args.output_dir / "prepared.jsonl"),
        "controls_prepared": True,
        "controls_complete": False,
        "evaluable_task_ids": [],
        "status_by_task": {},
        "model_outputs_present": False,
    }
    args.selection.parent.mkdir(parents=True, exist_ok=True)
    args.selection.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_out = {
        "schema": "heldout200-input-manifest-v1",
        "selection_sha256": sha256_file(args.selection),
        "files": {name: {"path": str(args.output_dir / name), "sha256": sha256_file(args.output_dir / name)}
                   for name in ("evaluator_dataset.jsonl", "prepared.jsonl", "gold.jsonl", "incorrect.jsonl")},
        "model_input_fields": ["task_id", "prompt", "context", "benchmark", "metadata"],
        "model_input_source_fields": ["instruct_prompt", "code_prompt"],
        "forbidden_model_fields": ["test", "canonical_solution"],
        "preparer_code_sha256": sha256_file(Path(__file__)),
        "bridge_code_sha256": sha256_file(Path(__file__).resolve().parents[1] / "benchmark_bridge.py"),
        "source_manifest_sha256": sha256_file(args.manifest),
        "controls_dispatched": False,
    }
    (args.output_dir / "input_manifest.json").write_text(
        json.dumps(manifest_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
