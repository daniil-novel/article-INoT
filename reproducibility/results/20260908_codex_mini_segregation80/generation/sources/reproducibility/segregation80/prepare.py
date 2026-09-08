#!/usr/bin/env python3
"""Prepare a frozen, four-arm single-call role-segregation extension.

This module only reads the frozen BigCodeBench inputs and writes model/evaluator
preparation artifacts.  It never calls a model or executes benchmark code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from ..benchmark_bridge import _prepare_output_row
except ImportError:  # direct execution from the repository root
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from benchmark_bridge import _prepare_output_row

COUNT = 80
ARM_NAMES = ("role_boundary", "neutral_boundary", "role_prose", "neutral_prose")
FORBIDDEN_MODEL_FIELDS = ("test", "canonical_solution", "complete_prompt", "gold", "reference")
EXPOSED_NUMBERS = {str(i) for i in range(8)}

COMMON_LEAD = "Use three internal checkpoints in this one response."
OPERATIONS = (
    "Analyze the requirements and edge cases and form a concise plan.",
    "Implement the requested function using that plan.",
    "Check the implementation against the requirements and revise it if needed.",
)
COMMON_TAIL = "Do not output checkpoint notes or commentary. Return exactly one fenced Python program."
LABELS = {"role": ("PLANNER", "IMPLEMENTER", "REVIEWER"), "neutral": ("STAGE 1", "STAGE 2", "STAGE 3")}


def prompt_suffix(role_factor: str, boundary_factor: str) -> str:
    labels = LABELS[role_factor]
    if boundary_factor == "explicit":
        body = "\n".join(f"[{label}] {operation}" for label, operation in zip(labels, OPERATIONS))
    elif boundary_factor == "prose":
        body = " ".join(f"{label}: {operation}" for label, operation in zip(labels, OPERATIONS))
    else:
        raise ValueError(f"unknown boundary factor: {boundary_factor}")
    return f"{COMMON_LEAD}\n{body}\n{COMMON_TAIL}"

TEMPLATES = {
    "role_boundary": prompt_suffix("role", "explicit"),
    "neutral_boundary": prompt_suffix("neutral", "explicit"),
    "role_prose": prompt_suffix("role", "prose"),
    "neutral_prose": prompt_suffix("neutral", "prose"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl_bytes(path: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    rows: list[dict[str, Any]] = []
    raw_by_id: dict[str, bytes] = {}
    with path.open("rb") as handle:
        for number, raw in enumerate(handle, 1):
            line = raw.rstrip(b"\r\n")
            if not line.strip():
                continue
            row = json.loads(line.decode("utf-8"))
            task_id = str(row["task_id"])
            if task_id in raw_by_id:
                raise ValueError(f"{path}:{number}: duplicate task_id {task_id}")
            rows.append(row)
            raw_by_id[task_id] = line
    return rows, raw_by_id


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def choose_ids(
    split_manifest: dict[str, Any],
    heldout_selection: dict[str, Any],
    count: int = COUNT,
) -> tuple[list[str], list[str]]:
    confirmatory = [str(x) for x in split_manifest["confirmatory_task_ids"]]
    heldout = [str(x) for x in heldout_selection["assigned_task_ids"]]
    dev = {str(x) for x in split_manifest["dev_task_ids"]}
    excluded = set(heldout) | dev | {f"BigCodeBench/{i}" for i in range(8)}
    candidates = [task_id for task_id in confirmatory if task_id not in excluded]
    if len(candidates) < count:
        raise ValueError(f"frozen confirmatory order has only {len(candidates)} fresh IDs")
    selected = candidates[:count]
    if len(set(selected)) != count:
        raise ValueError("selected IDs are not unique")
    return selected, candidates


def build_model_row(task: dict[str, Any], arm: str, source_row_sha256: str) -> dict[str, Any]:
    if arm not in TEMPLATES:
        raise ValueError(f"unknown arm: {arm}")
    row = _prepare_output_row(task)
    row["prompt"] = str(task["instruct_prompt"]) + "\n\n" + TEMPLATES[arm]
    row["metadata"] = {
        "source": "bigcodebench",
        "extension": "segregation80",
        "arm": arm,
        "role_factor": "role" if arm.startswith("role_") else "neutral",
        "boundary_factor": "explicit" if arm.endswith("boundary") else "prose",
        "source_row_sha256": source_row_sha256,
    }
    return row


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    heldout = json.loads(args.heldout_selection.read_text(encoding="utf-8"))
    if sha256_file(args.dataset) != split["source_sha256"]:
        raise ValueError("dataset hash differs from frozen split manifest")
    if sha256_file(args.confirmatory) != split["confirmatory_sha256"]:
        raise ValueError("confirmatory hash differs from frozen split manifest")
    source_rows, raw_by_id = read_jsonl_bytes(args.dataset)
    by_id = {str(row["task_id"]): row for row in source_rows}
    selected, candidate_order = choose_ids(split, heldout)
    if any(task_id not in by_id for task_id in selected):
        raise ValueError("selected ID is absent from source dataset")
    selected_rows = [by_id[task_id] for task_id in selected]

    input_dir = output / "input"
    evaluator_dir = output / "evaluator"
    input_dir.mkdir()
    evaluator_dir.mkdir()
    evaluator_path = evaluator_dir / "evaluator_dataset.jsonl"
    with evaluator_path.open("wb") as handle:
        for task_id in selected:
            handle.write(raw_by_id[task_id])
            handle.write(b"\n")

    write_jsonl(input_dir / "prepared.jsonl", [_prepare_output_row(row) for row in selected_rows])

    gold: list[dict[str, str]] = []
    incorrect: list[dict[str, str]] = []
    for row in selected_rows:
        solution = str(row["code_prompt"]) + str(row["canonical_solution"])
        gold.append({"task_id": str(row["task_id"]), "solution": solution})
        incorrect.append({
            "task_id": str(row["task_id"]),
            "solution": solution + "\n\n# Deliberately incorrect segregation80 control.\ndef task_func(*args, **kwargs):\n    return None\n",
        })
    write_jsonl(evaluator_dir / "gold.jsonl", gold)
    write_jsonl(evaluator_dir / "incorrect.jsonl", incorrect)

    model_hashes: dict[str, str] = {}
    for arm in ARM_NAMES:
        rows = [build_model_row(row, arm, sha256_bytes(raw_by_id[str(row["task_id"])])) for row in selected_rows]
        path = input_dir / f"{arm}.jsonl"
        write_jsonl(path, rows)
        model_hashes[arm] = sha256_file(path)

    selection = {
        "schema": "segregation80-selection-v1",
        "count": COUNT,
        "selection_rule": "first 80 confirmatory_task_ids after excluding heldout200 assigned IDs, dev40 IDs and BigCodeBench/0 through BigCodeBench/7",
        "assigned_task_ids": selected,
        "candidate_order_sha256": sha256_bytes("\n".join(candidate_order).encode("utf-8")),
        "assigned_ids_sha256": sha256_bytes("\n".join(selected).encode("utf-8")),
        "source_dataset_sha256": sha256_file(args.dataset),
        "split_manifest_sha256": sha256_file(args.split_manifest),
        "confirmatory_sha256": sha256_file(args.confirmatory),
        "heldout200_selection_sha256": sha256_file(args.heldout_selection),
        "source_row_sha256": {task_id: sha256_bytes(raw_by_id[task_id]) for task_id in selected},
        "model_input_sha256": sha256_file(input_dir / "prepared.jsonl"),
        "evaluator_dataset_sha256": sha256_file(evaluator_path),
        "model_outputs_present": False,
        "controls_complete": False,
    }
    selection_path = output / "selection.json"
    selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "segregation80-input-manifest-v1",
        "selection_sha256": sha256_file(selection_path),
        "model_arms": list(ARM_NAMES),
        "model_rows_per_arm": COUNT,
        "model_input_fields": ["task_id", "prompt", "context", "benchmark", "metadata"],
        "forbidden_model_fields": list(FORBIDDEN_MODEL_FIELDS),
        "model_input_sha256": model_hashes,
        "base_prepared_sha256": sha256_file(input_dir / "prepared.jsonl"),
        "evaluator_files": {
            name: {"path": str(evaluator_dir / name), "sha256": sha256_file(evaluator_dir / name)}
            for name in ("evaluator_dataset.jsonl", "gold.jsonl", "incorrect.jsonl")
        },
        "preparer_sha256": sha256_file(Path(__file__).resolve()),
        "bridge_sha256": sha256_file(Path(__file__).resolve().parents[1] / "benchmark_bridge.py"),
        "no_generation": True,
    }
    (output / "input_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return selection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--confirmatory", type=Path, required=True)
    parser.add_argument("--heldout-selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    prepare(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
