"""Task-clustered analysis for the frozen 1,000-task, three-repeat study.

The unit of inference is the task.  Repeats are averaged within task before
the four paired contrasts are tested, so the 3,000 repeat observations are
never treated as independent tasks.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
from scipy.stats import ttest_1samp

ARMS = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
REPEATS = (101, 102, 103)
CONTRASTS = {
    "single_roles_minus_single_neutral": ("single_roles", "single_neutral"),
    "multi_roles_minus_multi_neutral": ("multi_roles", "multi_neutral"),
    "multi_neutral_minus_single_neutral": ("multi_neutral", "single_neutral"),
    "multi_roles_minus_single_roles": ("multi_roles", "single_roles"),
}
DIRECT_CONTRASTS = {f"direct_minus_{arm}": ("direct", arm) for arm in ARMS if arm != "direct"}
METRICS = ("total_tokens", "api_equivalent_usd", "uncached_sensitivity_usd")


def _bootstrap(values: list[float], seed: int = 20260909) -> list[float] | None:
    if len(values) < 2:
        return None
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    draws = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
    return [float(v) for v in np.quantile(draws, [.025, .975])]


def _holm(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues, key=lambda key: (pvalues[key], key))
    adjusted: dict[str, float] = {}
    running = 0.0
    m = len(ordered)
    for i, key in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * pvalues[key]))
        adjusted[key] = running
    return adjusted


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate(records: list[dict[str, Any]]) -> tuple[list[str], dict[tuple[str, str, int], dict[str, Any]]]:
    index: dict[tuple[str, str, int], dict[str, Any]] = {}
    task_order: list[str] = []
    for row in records:
        required = {"task_id", "arm", "replicate_id", "quality", "generation_complete"}
        missing = required - set(row)
        if missing:
            raise ValueError(f"missing fields: {sorted(missing)}")
        task, arm, repeat = row["task_id"], row["arm"], row["replicate_id"]
        if not isinstance(task, str) or arm not in ARMS or type(repeat) is not int or repeat not in REPEATS:
            raise ValueError("invalid task, arm, or repeat identifier")
        if task not in task_order:
            task_order.append(task)
        if row["quality"] is not None and type(row["quality"]) is not bool:
            raise ValueError("quality must be bool or null")
        if type(row["generation_complete"]) is not bool:
            raise ValueError("generation_complete must be bool")
        if row["generation_complete"] is not True and row["quality"] is not None:
            raise ValueError("incomplete generation cannot have a quality outcome")
        key = (task, arm, repeat)
        if key in index:
            raise ValueError(f"duplicate assignment: {key}")
        index[key] = row
    return task_order, index


def _quality_means(task_order: list[str], index: dict[tuple[str, str, int], dict[str, Any]], arm: str) -> dict[str, float]:
    result = {}
    for task in task_order:
        values = [index[(task, arm, repeat)]["quality"] for repeat in REPEATS if (task, arm, repeat) in index]
        if len(values) == 3 and all(type(v) is bool and index[(task, arm, repeat)]["generation_complete"] is True for repeat, v in zip(REPEATS, values)):
            result[task] = float(np.mean(values))
    return result


def _contrast_quality(task_order: list[str], index: dict[tuple[str, str, int], dict[str, Any]], a: str, b: str) -> dict[str, Any]:
    left, right = _quality_means(task_order, index, a), _quality_means(task_order, index, b)
    tasks = [t for t in task_order if t in left and t in right]
    differences = [left[t] - right[t] for t in tasks]
    degenerate = False
    if len(differences)>=2 and all(v == differences[0] for v in differences):
        degenerate = True
        if differences[0] == 0:
            p, t_stat = 1.0, 0.0
        else:
            p, t_stat = 0.0, None
    elif len(differences) >= 2:
        test = ttest_1samp(differences, 0.0)
        p = float(test.pvalue)
        t_stat = float(test.statistic)
    else:
        p = None
        t_stat = None
    return {"eligible_tasks": len(tasks), "task_ids": tasks, "mean_difference": float(np.mean(differences)) if differences else None,
            "t_statistic": t_stat, "two_sided_p": p, "bootstrap_95": _bootstrap(differences),
            "repeat_aggregation": "arithmetic mean of three boolean repeat outcomes within task",
            "degenerate_difference_vector": degenerate}


def _resource_contrast(task_order: list[str], index: dict[tuple[str, str, int], dict[str, Any]], a: str, b: str, metric: str) -> dict[str, Any]:
    left, right, diffs = [], [], []
    tasks = []
    for task in task_order:
        av = [index[(task, a, r)].get(metric) for r in REPEATS if (task, a, r) in index]
        bv = [index[(task, b, r)].get(metric) for r in REPEATS if (task, b, r) in index]
        if len(av) == len(bv) == 3 and all(_num(v) for v in av + bv) and all(index[(task, arm, r)].get("generation_complete") is True for arm in (a, b) for r in REPEATS):
            x, y = float(np.mean(av)), float(np.mean(bv))
            tasks.append(task); left.append(x); right.append(y); diffs.append(x - y)
    denom = sum(right)
    return {"eligible_tasks": len(tasks), "mean_difference": float(np.mean(diffs)) if diffs else None,
            "ratio_of_task_mean_sums": float(sum(left) / denom) if denom else None,
            "bootstrap_95": _bootstrap(diffs), "task_ids": tasks,
            "complete_three_repeat_pairs": True}


def _arm_summary(task_order: list[str], index: dict[tuple[str, str, int], dict[str, Any]], arm: str) -> dict[str, Any]:
    assigned = len(task_order)*len(REPEATS)
    recorded = sum((task, arm, r) in index for task in task_order for r in REPEATS)
    complete = sum(index[(task, arm, r)].get("generation_complete") is True for task in task_order for r in REPEATS if (task, arm, r) in index)
    quality = _quality_means(task_order, index, arm)
    known_repeat = [index[(task, arm, r)]["quality"] for task in task_order for r in REPEATS if (task, arm, r) in index and index[(task, arm, r)]["quality"] is not None]
    passes = sum(known_repeat)
    variances = []
    for task in task_order:
        vals = [index[(task, arm, r)]["quality"] for r in REPEATS if (task, arm, r) in index and index[(task, arm, r)]["quality"] is not None and index[(task, arm, r)].get("generation_complete") is True]
        if len(vals) == 3:
            variances.append(float(np.var(vals, ddof=1)))
    return {"arm": arm, "assigned": assigned, "recorded_assignments":recorded, "generation_complete": complete,
            "quality_observed_tasks": len(quality), "passes": int(passes),
            "known_repeat_outcomes": len(known_repeat), "pass_rate_observed": float(passes / len(known_repeat)) if known_repeat else None,
            "assigned_rate_bounds": [float(passes / assigned) if assigned else None,
                                     float((passes + assigned - len(known_repeat)) / assigned) if assigned else None],
            "complete_task_mean_sum": float(sum(quality.values())),
            "repeat_successes_by_id": {str(r): sum(index[(t, arm, r)]["quality"] for t in task_order if (t, arm, r) in index and index[(t, arm, r)]["quality"] is not None) for r in REPEATS},
            "within_task_repeat_variance_mean": float(np.mean(variances)) if variances else None,
            "within_task_repeat_variance_tasks": len(variances)}


def _subgroups(selection: dict[str, Any] | None, task_order: list[str]) -> dict[str, list[str]]:
    if not selection:
        return {}
    old = selection.get("prior_primary_task_ids", [])
    new = selection.get("new_task_ids", [])
    if not isinstance(old, list) or not isinstance(new, list) or set(old) & set(new):
        raise ValueError("selection subgroup IDs must be disjoint lists")
    if selection.get("assigned_task_ids") is not None and selection["assigned_task_ids"] != task_order:
        raise ValueError("selection assigned_task_ids differ from record task identity/order")
    if set(old) | set(new) != set(task_order) or len(old) != 200 or len(new) != 800:
        raise ValueError("selection must partition the 1,000 tasks into old200 and fresh800")
    return {"old200": old, "fresh800": new}


def summarize(records: list[dict[str, Any]], selection: dict[str, Any] | None = None) -> dict[str, Any]:
    task_order, index = _validate(records)
    if len(task_order) != 1000:
        raise ValueError("expected exactly 1,000 unique task clusters")
    if selection and 'assigned_task_ids' in selection:
        assigned=selection['assigned_task_ids']
        if len(assigned)!=1000 or set(assigned)!=set(task_order):raise ValueError('Selection task identity differs')
        task_order=assigned.copy()
    contrasts = {name: _contrast_quality(task_order, index, a, b) for name, (a, b) in CONTRASTS.items()}
    pvalues = {name: (x["two_sided_p"] if x["two_sided_p"] is not None else 1.0) for name, x in contrasts.items()}
    corrected = _holm(pvalues)
    for name, value in contrasts.items():
        value["holm_p"] = corrected.get(name) if value['two_sided_p'] is not None else None
        value["first_step_alpha"] = 0.05 / 4
    resources = {name: {metric: _resource_contrast(task_order, index, a, b, metric) for metric in METRICS}
                 for name, (a, b) in CONTRASTS.items()}
    direct = {name: _contrast_quality(task_order, index, a, b) for name, (a, b) in DIRECT_CONTRASTS.items()}
    interaction_tasks = []
    for task in task_order:
        means = {arm: _quality_means([task], index, arm).get(task) for arm in ("single_roles", "single_neutral", "multi_roles", "multi_neutral")}
        if all(v is not None for v in means.values()):
            interaction_tasks.append(means["multi_roles"] - means["multi_neutral"] - means["single_roles"] + means["single_neutral"])
    interaction = {"eligible_tasks": len(interaction_tasks), "mean": float(np.mean(interaction_tasks)) if interaction_tasks else None,
                   "bootstrap_95": _bootstrap(interaction_tasks), "descriptive_only": True}
    groups = _subgroups(selection, task_order) if selection else {}
    subgroup_results = {}
    for label, ids in groups.items():
        if not ids or not set(ids).issubset(set(task_order)):
            raise ValueError(f"selection subgroup {label} is not contained in records")
        subgroup_results[label] = {name: _contrast_quality(ids, index, a, b) for name, (a, b) in CONTRASTS.items()}
    missing = {"tasks": len(task_order), "assignments": len(records),
               "missing_rows": 15000 - len(records),
               "quality_unknown_assignments": sum(r["quality"] is None for r in records),
               "generation_incomplete_assignments": sum(r["generation_complete"] is not True for r in records)}
    return {"schema": "scale1000-task-cluster-analysis-v1", "tasks": 1000, "planned_candidates": 15000,
            "planned_cli_turns": 27000, "repeats": list(REPEATS), "arms": list(ARMS),
            "by_arm": [_arm_summary(task_order, index, arm) for arm in ARMS],
            "contrasts": contrasts, "resource_contrasts": resources, "descriptive_direct_contrasts": direct,
            "role_by_callcount_interaction": interaction, "subgroups": subgroup_results,
            "missingness": missing, "bootstrap": {"resamples": 10000, "seed": 20260909},
            "inference": {"primary": "paired task-level mean quality differences across three repeats; two-sided one-sample t-test",
                          "holm_family_size": 4, "holm_familywise_alpha": 0.05,
                          "asymptotic_large_n": True, "repeat_means_are_not_independent_tasks": True,
                          "noninferiority": "not assessed", "equivalence": "not assessed"},
            "power_sensitivity": power_sensitivity()}


def power_sensitivity() -> list[dict[str, float]]:
    nd = NormalDist()
    rows = []
    z = nd.inv_cdf(1 - (0.05 / 4) / 2)
    for discordance in (0.15, 0.30, 0.50):
        for rho in (0.0, 0.5, 0.8):
            for effect in (0.02, 0.05, 0.10):
                variance = discordance * (rho + (1 - rho) / 3) / 1000
                se = math.sqrt(variance)
                noncentral = effect / se if se else math.inf
                power = nd.cdf(-z - noncentral) + 1 - nd.cdf(z - noncentral)
                rows.append({"tasks": 1000, "discordance_d": discordance, "repeat_icc_rho": rho,
                             "effect": effect, "adjusted_two_sided_alpha": 0.0125,
                             "variance_formula": "d*(rho+(1-rho)/3)/n",
                             "approximate_sensitivity": float(power)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--power", action="store_true", help="write the pre-generation sensitivity grid without records")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("refusing to overwrite analysis")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    value = {"schema": "scale1000-power-sensitivity-v1", "power_sensitivity": power_sensitivity()} if args.power else summarize(
        [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines() if line.strip()],
        json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None)
    payload = (json.dumps(value, indent=2, allow_nan=False) + "\n").replace("\r\n", "\n")
    args.out.write_bytes(payload.encode("utf-8"))


if __name__ == "__main__":
    main()
