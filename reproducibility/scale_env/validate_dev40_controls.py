"""Validate native upstream CLI control reports against the frozen dev-40 inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def samples(path: Path) -> tuple[list[str], dict[str, str]]:
    ids: list[str] = []
    solutions: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            task_id, solution = row.get("task_id"), row.get("solution")
            if not isinstance(task_id, str) or not isinstance(solution, str) or task_id in solutions:
                raise ValueError(f"invalid or duplicate sample row in {path}")
            ids.append(task_id)
            solutions[task_id] = solution
    return ids, solutions


def report(path: Path, expected_ids: list[str], expected_solutions: dict[str, str], kind: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    actual = data.get("eval", {})
    if list(actual) != expected_ids and set(actual) != set(expected_ids):
        raise ValueError(f"{kind}: report IDs differ from frozen 40-task set")
    statuses: dict[str, str] = {}
    for task_id in expected_ids:
        rows = actual.get(task_id)
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError(f"{kind}: expected one result for {task_id}")
        row = rows[0]
        if row.get("task_id") != task_id or row.get("solution") != expected_solutions[task_id]:
            raise ValueError(f"{kind}: evaluated solution differs for {task_id}")
        status = row.get("status")
        if status not in {"pass", "fail", "timeout"}:
            raise ValueError(f"{kind}: unknown status for {task_id}: {status!r}")
        statuses[task_id] = status
    return statuses


def validate_metadata(path: Path, expected_ids: list[str], samples_path: Path) -> dict:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if metadata.get("selected_ids") != expected_ids or metadata.get("network") != "none":
        raise ValueError(f"metadata selection/network mismatch: {path}")
    if metadata.get("cli_split") != "instruct" or metadata.get("dataset_partition") != "development (40 seeded IDs)":
        raise ValueError(f"metadata partition mismatch: {path}")
    if metadata.get("samples_source_sha256") != sha256(samples_path):
        raise ValueError(f"source sample hash mismatch: {path}")
    if metadata.get("staged_samples_sha256") != metadata.get("post_evaluator_staged_samples_sha256"):
        raise ValueError(f"pre/post staged sample hash mismatch: {path}")
    argv = metadata.get("argv", [])
    try:
        start = argv.index("-m")
    except ValueError as exc:
        raise ValueError(f"missing module invocation: {path}") from exc
    expected_tail = [
        "bigcodebench.evaluate", "instruct", "full", "--samples", "/run/input/samples.jsonl",
        "--execution", "local", "--selective_evaluate", ",".join(expected_ids),
        "--calibrated", "False", "--parallel", "2", "--no_gt", "True",
        "--save_pass_rate", "False", "--min_time_limit", "0.1", "--max_as_limit", "30720",
        "--max_data_limit", "30720", "--max_stack_limit", "10",
    ]
    if argv[start + 1:] != expected_tail:
        raise ValueError(f"CLI argv differs from frozen instruct/full invocation: {path}")
    required_provenance = ("vendor_tree_sha256", "dataset_sha256", "prepared_split_sha256", "requirements_sha256", "dockerfile_sha256")
    if any(not metadata.get("provenance", {}).get(key) for key in required_provenance):
        raise ValueError(f"incomplete provenance: {path}")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--incorrect", type=Path, required=True)
    parser.add_argument("--gold-samples", type=Path, required=True)
    parser.add_argument("--incorrect-samples", type=Path, required=True)
    parser.add_argument("--gold-metadata", type=Path, required=True)
    parser.add_argument("--incorrect-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ids, gold_solutions = samples(args.gold_samples)
    negative_ids, incorrect_solutions = samples(args.incorrect_samples)
    if ids != negative_ids or len(ids) != 40 or len(set(ids)) != 40:
        raise ValueError("gold and incorrect samples must contain the same 40 IDs in frozen order")
    gold = report(args.gold, ids, gold_solutions, "gold")
    incorrect = report(args.incorrect, ids, incorrect_solutions, "incorrect")
    for metadata_path, samples_path in ((args.gold_metadata, args.gold_samples), (args.incorrect_metadata, args.incorrect_samples)):
        validate_metadata(metadata_path, ids, samples_path)
    eligible = [task_id for task_id in ids if gold[task_id] == "pass" and incorrect[task_id] in {"fail", "timeout"}]
    result = {
        "schema": "bcb-dev40-control-gate-v1",
        "assigned_task_ids": ids,
        "assigned_count": 40,
        "controls_complete": True,
        "evaluable_task_ids": eligible,
        "evaluable_count": len(eligible),
        "ineligible_task_ids": [task_id for task_id in ids if task_id not in eligible],
        "status_by_task": {task_id: {"gold": gold[task_id], "incorrect": incorrect[task_id], "eligible": task_id in eligible} for task_id in ids},
        "gold_report_sha256": sha256(args.gold),
        "incorrect_report_sha256": sha256(args.incorrect),
        "gold_samples_sha256": sha256(args.gold_samples),
        "incorrect_samples_sha256": sha256(args.incorrect_samples),
        "gold_metadata_sha256": sha256(args.gold_metadata),
        "incorrect_metadata_sha256": sha256(args.incorrect_metadata),
        "cli_split": "instruct",
        "tests": "upstream original tests; no test edits",
        "network": "none",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "evaluable_count": len(eligible), "ineligible": result["ineligible_task_ids"]}))


if __name__ == "__main__":
    main()
