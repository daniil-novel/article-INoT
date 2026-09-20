"""Reproduce the primary source-component bootstrap from retained ledgers."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPEATS = (101, 102, 103)
GRAPHS = ("union_070_code_exact", "prompt_050", "prompt_070", "prompt_090")
CONTRASTS = (
    ("single_roles", "single_neutral"),
    ("multi_roles", "multi_neutral"),
    ("multi_neutral", "single_neutral"),
    ("multi_roles", "single_roles"),
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    selection = read(ROOT / "primary/selection.json")
    assigned = set(selection["assigned_task_ids"])
    gate = read(ROOT / "primary/control_gate.json")
    eligible = set(gate["evaluable_task_ids"])
    rows = [json.loads(line) for line in (ROOT / "primary/assignment_outcomes.jsonl").read_text(encoding="utf-8").splitlines() if line]
    index = {(r["task_id"], r["arm"], int(r["replicate_id"])): r.get("quality") for r in rows}
    partitions = read(ROOT / "primary/source_partitions.json")
    retained = read(ROOT / "primary/source_sensitivity/summary.json")

    values = {}
    for left, right in CONTRASTS:
        name = f"{left}_minus_{right}"
        values[name] = {}
        for task in eligible:
            a = [index[(task, left, repeat)] for repeat in REPEATS]
            b = [index[(task, right, repeat)] for repeat in REPEATS]
            if all(value is not None for value in a + b):
                values[name][task] = sum(int(x) - int(y) for x, y in zip(a, b)) / 3

    checked = 0
    for graph in GRAPHS:
        groups = partitions[graph]["assigned_components"]
        assert {task for group in groups for task in group} == assigned
        for contrast, task_values in values.items():
            observed = [[task_values[t] for t in group if t in task_values] for group in groups]
            observed = [group for group in observed if group]
            sizes = np.array([len(group) for group in observed], dtype=np.int64)
            sums = np.array([sum(group) for group in observed], dtype=float)
            rng = np.random.default_rng(20260911)
            draws = np.empty(10000, dtype=float)
            for start in range(0, 10000, 128):
                indices = rng.integers(0, len(observed), size=(min(128, 10000 - start), len(observed)))
                draws[start:start + len(indices)] = sums[indices].sum(axis=1) / sizes[indices].sum(axis=1)
            saved = np.array(read(ROOT / "primary/source_sensitivity" / f"{graph}--{contrast}.json"))
            if not np.array_equal(draws, saved):
                raise SystemExit(f"source bootstrap draws differ: {graph}/{contrast}")
            summary = retained["graphs"][graph][contrast]
            if not np.array_equal(np.quantile(draws, [.025, .975]), np.array(summary["ci95"])):
                raise SystemExit(f"source bootstrap interval differs: {graph}/{contrast}")
            if summary["tasks"] != int(sizes.sum()) or summary["families"] != len(observed):
                raise SystemExit(f"source bootstrap counts differ: {graph}/{contrast}")
            checked += 1
    print(f"Reproduced {checked} source-component bootstrap distributions and intervals.")


if __name__ == "__main__":
    main()
