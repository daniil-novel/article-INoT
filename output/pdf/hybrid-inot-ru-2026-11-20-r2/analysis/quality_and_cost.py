"""Recompute the shared-sample results from primary/assignment_outcomes.jsonl.

Run from the manuscript source directory:
    python analysis/quality_and_cost.py path/to/primary/assignment_outcomes.jsonl
"""

import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path


ARMS = ("single_roles", "multi_roles")


def read_tasks(path):
    tasks = defaultdict(lambda: {arm: {} for arm in ARMS})
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line, parse_float=Decimal)
            if row["arm"] in ARMS:
                repeats = tasks[row["task_id"]][row["arm"]]
                repeat_id = row["replicate_id"]
                if repeat_id in repeats:
                    raise ValueError(f"Duplicate assignment in {row['task_id']}, {row['arm']}")
                repeats[repeat_id] = row

    if not tasks:
        raise ValueError("No assignments for the two selected conditions")
    for task_id, arms in tasks.items():
        single, multi = arms["single_roles"], arms["multi_roles"]
        if len(single) != 3 or single.keys() != multi.keys():
            raise ValueError(f"Expected three matching assigned repeats in {task_id}")
    return tasks


def summarize(tasks):
    quality_tasks = set()
    resource_tasks = set()
    for task_id, arms in tasks.items():
        rows = [row for repeats in arms.values() for row in repeats.values()]
        if not all(row["generation_complete"] for row in rows):
            continue
        if all(type(row["quality"]) is bool for row in rows):
            quality_tasks.add(task_id)
        if all(
            row.get("total_tokens") is not None and row.get("api_equivalent_usd") is not None
            for row in rows
        ):
            resource_tasks.add(task_id)

    shared = quality_tasks & resource_tasks
    if not shared:
        raise ValueError("No tasks with complete test and usage data in both conditions")

    by_arm = {}
    for arm in ARMS:
        eligible = [row for task_id in sorted(shared) for row in tasks[task_id][arm].values()]
        successes = sum(row["quality"] for row in eligible)
        if successes == 0:
            raise ValueError(f"Cost per successful program is undefined for {arm}")
        tokens = sum(row["total_tokens"] for row in eligible)
        cost = sum(row["api_equivalent_usd"] for row in eligible)
        assigned = [row for task in tasks.values() for row in task[arm].values()]
        by_arm[arm] = {
            "complete_runs": len(eligible),
            "programs_passing_tests": successes,
            "success_percent": 100 * successes / len(eligible),
            "total_tokens": tokens,
            "tokens_per_run": tokens / len(eligible),
            "api_equivalent_usd": cost,
            "api_equivalent_usd_per_success": cost / successes,
            "known_successes_all_assignments": sum(row["quality"] is True for row in assigned),
            "unknown_tests_all_assignments": sum(row["quality"] is None for row in assigned),
        }

    single, multi = (by_arm[arm] for arm in ARMS)
    known_difference = single["known_successes_all_assignments"] - multi["known_successes_all_assignments"]
    assigned_per_arm = 3 * len(tasks)
    return {
        "assigned_tasks": len(tasks),
        "quality_tasks": len(quality_tasks),
        "resource_tasks": len(resource_tasks),
        "shared_tasks": len(shared),
        "by_arm": by_arm,
        "success_difference_pp": single["success_percent"] - multi["success_percent"],
        "api_equivalent_cost_reduction_percent": 100 * (
            1 - single["api_equivalent_usd"] / multi["api_equivalent_usd"]
        ),
        "api_equivalent_cost_per_success_reduction_percent": 100 * (
            1 - single["api_equivalent_usd_per_success"] / multi["api_equivalent_usd_per_success"]
        ),
        "possible_success_difference_pp_all_assignments": [
            100 * (known_difference - multi["unknown_tests_all_assignments"]) / assigned_per_arm,
            100 * (known_difference + single["unknown_tests_all_assignments"]) / assigned_per_arm,
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outcomes", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(read_tasks(args.outcomes)), indent=2, default=str))
