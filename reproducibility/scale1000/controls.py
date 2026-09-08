#!/usr/bin/env python3
"""Freeze the scale-1000 native control gate after both controls finish.

The builder validates both native folders against the exact evaluator-only
gold/incorrect inputs, checks identical images and provenance, then writes an
exclusive gate file and revalidates it through the heldout evidence schema.
It never runs the evaluator or a model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..heldout200.evidence import environment_from_gate
from ..scale_env.validate_native import sha256, validate_native


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def metadata(folder: Path) -> dict[str, Any]:
    return json.loads((folder / "run-metadata.json").read_text(encoding="utf-8"))


def expected_rows(path: Path, assigned: list[str]) -> dict[str, str]:
    rows = read_jsonl(path)
    if [str(row.get("task_id")) for row in rows] != assigned:
        raise ValueError(f"control input order differs from frozen assignment: {path}")
    return {str(row["task_id"]): str(row["solution"]) for row in rows}


def build_gate(controls_dir: Path, input_dir: Path, selection_path: Path) -> dict[str, Any]:
    gate_path = controls_dir / "heldout200_control_gate.json"
    if gate_path.exists():
        raise FileExistsError(f"immutable control gate already exists: {gate_path}")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    assigned = [str(x) for x in selection["assigned_task_ids"]]
    if len(assigned) != 1000 or len(set(assigned)) != 1000:
        raise ValueError("scale1000 selection must contain exactly 1000 unique IDs")
    frozen_gold = expected_rows(input_dir / "evaluator/gold.jsonl", assigned)
    frozen_incorrect = expected_rows(input_dir / "evaluator/incorrect.jsonl", assigned)
    roots = {kind: controls_dir / kind for kind in ("gold", "incorrect")}
    if not all((root / "run-metadata.json").is_file() for root in roots.values()):
        raise FileNotFoundError("both native control metadata files are required")

    metas = {kind: metadata(root) for kind, root in roots.items()}
    required_environment = (
        "image_id", "base_image_id", "upstream_commit_verified", "network", "cli_split",
        "package_freeze_sha256", "nltk_resources_sha256",
    )
    for field in required_environment:
        if metas["gold"].get(field) != metas["incorrect"].get(field):
            raise ValueError(f"gold/incorrect environment mismatch: {field}")
    if metas["gold"].get("provenance") != metas["incorrect"].get("provenance"):
        raise ValueError("gold/incorrect provenance differs")
    provenance = metas["gold"].get("provenance", {})
    for field, selection_key in (("dataset_sha256", "evaluator_dataset_sha256"), ("prepared_split_sha256", "model_input_sha256")):
        if provenance.get(field) != selection.get(selection_key):
            raise ValueError(f"native provenance does not match frozen input: {field}")

    env = {**{field: metas["gold"][field] for field in required_environment}, **provenance}
    results: dict[str, dict[str, Any]] = {}
    for kind, expected in (("gold", frozen_gold), ("incorrect", frozen_incorrect)):
        report = validate_native(roots[kind], expected, env)
        if not report["ok"]:
            raise ValueError(f"native {kind} validation failed: {report['errors']}")
        results[kind] = report

    status_by_task = {
        task_id: {kind: results[kind]["statuses"][task_id] for kind in ("gold", "incorrect")}
        for task_id in assigned
    }
    evaluable = [task_id for task_id in assigned if status_by_task[task_id]["gold"] == "pass" and status_by_task[task_id]["incorrect"] == "fail"]
    gate = {
        "schema": "scale1000-control-gate-v1",
        "controls_complete": True,
        "assigned_task_ids": assigned,
        "evaluable_task_ids": evaluable,
        "status_by_task": status_by_task,
        "image_id": metas["gold"]["image_id"],
        "base_image_id": metas["gold"]["base_image_id"],
        "source_tree_sha256": provenance["vendor_tree_sha256"],
        "dataset_sha256": provenance["dataset_sha256"],
        "prepared_split_sha256": provenance["prepared_split_sha256"],
        "requirements_sha256": provenance.get("requirements_sha256"),
        "dockerfile_sha256": provenance.get("dockerfile_sha256"),
        "package_freeze_sha256": metas["gold"]["package_freeze_sha256"],
        "nltk_resources_sha256": metas["gold"]["nltk_resources_sha256"],
        "selection_sha256": sha256(selection_path),
        "model_input_sha256": selection["model_input_sha256"],
        "evaluator_dataset_sha256": selection["evaluator_dataset_sha256"],
        "gold_metadata_sha256": sha256(roots["gold"] / "run-metadata.json"),
        "gold_report_sha256": sha256(roots["gold"] / "input/samples_eval_results.json"),
        "gold_samples_sha256": sha256(roots["gold"] / "input/samples.jsonl"),
        "incorrect_metadata_sha256": sha256(roots["incorrect"] / "run-metadata.json"),
        "incorrect_report_sha256": sha256(roots["incorrect"] / "input/samples_eval_results.json"),
        "incorrect_samples_sha256": sha256(roots["incorrect"] / "input/samples.jsonl"),
        "no_retry": True,
    }
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    with gate_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(gate, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    # Reuse the established gate schema and validator, including byte hashes,
    # environment equality, staged-input provenance and status derivation.
    environment_from_gate(controls_dir)
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-dir", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    args = parser.parse_args(argv)
    build_gate(args.controls_dir, args.input_dir, args.selection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
