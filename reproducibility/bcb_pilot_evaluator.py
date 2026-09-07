"""Narrow, development-only BigCodeBench pilot evaluator.

This intentionally evaluates only the first eight rows of the already prepared
development split. It uses the pinned upstream ``bigcodebench.eval`` sandbox
and the official tests from bigcodebench-v0.1.4. It is not the official
BigCodeBench CLI harness and its result must not be reported as a benchmark
score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from importlib import metadata
from pathlib import Path


SELECTED_TASK_IDS = [
    "BigCodeBench/325",
    "BigCodeBench/322",
    "BigCodeBench/1036",
    "BigCodeBench/1005",
    "BigCodeBench/361",
    "BigCodeBench/1087",
    "BigCodeBench/45",
    "BigCodeBench/309",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        p for p in root.rglob("*") if p.is_file() and not any(
            part in {".git", "__pycache__"} for part in p.relative_to(root).parts
        )
    ):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(path)))
        digest.update(b"\n")
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def package_freeze() -> list[str]:
    return sorted(
        f"{dist.metadata['Name']}=={dist.version}"
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    )


def control_code(problem: dict, kind: str) -> str:
    # ``complete_prompt`` contains the imports, signature, and docstring;
    # canonical_solution is the upstream reference body.
    if kind == "gold":
        return problem["complete_prompt"] + problem["canonical_solution"]
    if kind == "incorrect":
        return problem["complete_prompt"] + problem["canonical_solution"] + (
            "\n\n# Deliberately incorrect pilot control.\n"
            "def task_func(*args, **kwargs):\n    return None\n"
        )
    raise ValueError(f"unknown control: {kind}")


def analysis_outcome(status: str | None, controls: dict) -> str | None:
    """An unvalidated environment or unknown evaluator status is missing data."""
    eligible = (controls.get("gold", {}).get("status") == "pass"
                and controls.get("incorrect", {}).get("status") in {"fail", "timeout"})
    return status if eligible and status in {"pass", "fail", "timeout"} else None


def quality_summary(records: list[dict], task_ids: list[str]) -> dict:
    predictions = [r for r in records if r["control"] == "prediction"]
    if len(predictions) != len(task_ids) or {r['task_id'] for r in predictions} != set(task_ids):
        raise ValueError('Every assigned task must have exactly one prediction record')
    observed = [r['analysis_status'] for r in predictions if r['analysis_status'] is not None]
    passes = sum(s == 'pass' for s in observed)
    missing = len(task_ids) - len(observed)
    return {"denominator": len(task_ids), "evaluable_tasks": len(observed),
            "pass_count": passes, "missing_or_ineligible_count": missing,
            "evaluable_only_rate": passes / len(observed) if observed else None,
            "pessimistic_lower_bound": passes / len(task_ids),
            "optimistic_upper_bound": (passes + missing) / len(task_ids),
            "status_by_task": {r['task_id']: r['analysis_status'] for r in predictions}}


def evaluate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    prepared_path = root / "reproducibility/data/bigcodebench-split/prepared.jsonl"
    official_path = root / "reproducibility/data/bigcodebench-v0.1.4.jsonl"
    vendor_path = root / "reproducibility/vendor/bigcodebench"
    requirements_path = root / "reproducibility/pilot_env/requirements.txt"
    dockerfile_path = root / "reproducibility/pilot_env/Dockerfile"
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prepared = read_jsonl(prepared_path)
    prepared_ids = [row["task_id"] for row in prepared[: len(SELECTED_TASK_IDS)]]
    if prepared_ids != SELECTED_TASK_IDS:
        raise RuntimeError(
            "prepared.jsonl first eight task IDs changed: "
            f"expected {SELECTED_TASK_IDS}, got {prepared_ids}"
        )
    official = {row["task_id"]: row for row in read_jsonl(official_path)}
    missing = [task_id for task_id in SELECTED_TASK_IDS if task_id not in official]
    if missing:
        raise RuntimeError(f"official dataset missing selected IDs: {missing}")
    predictions = None
    if args.predictions:
        prediction_rows = read_jsonl(Path(args.predictions).resolve())
        prediction_ids = [row.get("task_id") for row in prediction_rows]
        if len(prediction_ids) != len(SELECTED_TASK_IDS) or set(prediction_ids) != set(SELECTED_TASK_IDS):
            raise RuntimeError(
                "predictions must contain exactly the selected eight unique IDs: "
                f"got {prediction_ids}"
            )
        predictions = sorted(prediction_rows, key=lambda row: SELECTED_TASK_IDS.index(row["task_id"]))
        if any(not isinstance(row.get("solution"), str) for row in prediction_rows):
            raise RuntimeError("each prediction row must contain a string solution")

    sys.path.insert(0, str(vendor_path))
    from bigcodebench.eval import untrusted_check  # noqa: PLC0415

    # These are the upstream evaluator defaults, made explicit for the run
    # record. The upstream function itself owns process isolation and limits.
    limits = {
        "max_as_limit": args.max_as_limit,
        "max_data_limit": args.max_data_limit,
        "max_stack_limit": args.max_stack_limit,
        "min_time_limit": args.min_time_limit,
        "gt_time_limit": args.gt_time_limit,
    }
    records = []
    for task_id in SELECTED_TASK_IDS:
        problem = official[task_id]
        for kind in ("gold", "incorrect"):
            started = time.time()
            try:
                status, details = untrusted_check(
                    control_code(problem, kind),
                    problem["test"],
                    problem["entry_point"],
                    args.max_as_limit,
                    args.max_data_limit,
                    args.max_stack_limit,
                    args.min_time_limit,
                    args.gt_time_limit,
                )
                details = dict(details)
                error = None
            except BaseException as exc:  # preserve infrastructure failures
                status, details = "evaluator_error", {}
                error = f"{type(exc).__name__}: {exc}"
            records.append(
                {
                    "task_id": task_id,
                    "control": kind,
                    "status": status,
                    "details": details,
                    "error": error,
                    "elapsed_seconds": round(time.time() - started, 3),
                }
            )

    controls_by_task = {
        task_id: {r["control"]: r for r in records if r["task_id"] == task_id}
        for task_id in SELECTED_TASK_IDS
    }
    if predictions is not None:
        for row in predictions:
            task_id = row["task_id"]
            problem = official[task_id]
            started = time.time()
            try:
                status, details = untrusted_check(
                    row["solution"],
                    problem["test"],
                    problem["entry_point"],
                    args.max_as_limit,
                    args.max_data_limit,
                    args.max_stack_limit,
                    args.min_time_limit,
                    args.gt_time_limit,
                )
                details = dict(details)
                error = None
            except BaseException as exc:
                status, details = "evaluator_error", {}
                error = f"{type(exc).__name__}: {exc}"
            control_state = controls_by_task[task_id]
            eligible = (
                control_state.get("gold", {}).get("status") == "pass"
                and control_state.get("incorrect", {}).get("status") in {"fail", "timeout"}
            )
            analysis_status = analysis_outcome(status, control_state)
            records.append(
                {
                    "task_id": task_id,
                    "control": "prediction",
                    "solution_sha256": hashlib.sha256(
                        row["solution"].encode("utf-8")
                    ).hexdigest(),
                    "status": status,
                    "analysis_status": analysis_status,
                    "analysis_eligible": eligible,
                    "details": details,
                    "error": error,
                    "elapsed_seconds": round(time.time() - started, 3),
                }
            )

    result = {
        "schema": "bcb-development-pilot-v1",
        "disclaimer": (
            "Eight-task development pilot only; not the official BigCodeBench CLI "
            "harness and not a full benchmark result."
        ),
        "selected_task_ids": SELECTED_TASK_IDS,
        "controls": ["gold", "incorrect"],
        "predictions": bool(predictions),
        "argv": sys.argv,
        "upstream_commit": "09dd993f46c3fbf3a799465bb96d524edcb0b199",
        "dataset_sha256": sha256(official_path),
        "prepared_split_sha256": sha256(prepared_path),
        "vendor_tree_sha256": tree_sha256(vendor_path),
        "requirements_sha256": sha256(requirements_path),
        "dockerfile_sha256": sha256(dockerfile_path),
        "image_ref": args.image_ref,
        "image_id": args.image_id,
        "pip_freeze": package_freeze(),
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "limits": limits,
        "network_expected_disabled": True,
        "prediction_analysis": (
            quality_summary(records, SELECTED_TASK_IDS)
            if predictions is not None
            else None
        ),
        "records": records,
    }
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "records": records}, indent=2))
    return 0 if all(r["error"] is None for r in records) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/workspace")
    parser.add_argument("--output", default="/out/pilot-controls.json")
    parser.add_argument("--max-as-limit", type=int, default=30 * 1024)
    parser.add_argument("--max-data-limit", type=int, default=30 * 1024)
    parser.add_argument("--max-stack-limit", type=int, default=10)
    parser.add_argument("--min-time-limit", type=float, default=0.1)
    parser.add_argument("--gt-time-limit", type=float, default=0.1)
    parser.add_argument("--image-ref", default="bcb-pilot:dev")
    parser.add_argument("--image-id", default=None)
    parser.add_argument("--predictions", default=None)
    return evaluate(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
