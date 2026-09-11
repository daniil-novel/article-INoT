"""Offline task-level analysis for the planned SCC/SR/SN 1,000-task series."""
from __future__ import annotations

import argparse, json, math, random, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from scipy import stats

METHODS = ("single_roles", "single_neutral", "scc_author_2024_codex_transport")
SCC = METHODS[2]
REPLICATES = (101, 102, 103)
PRIMARY_CONTRASTS = ((SCC, METHODS[0]), (SCC, METHODS[1]))
DESCRIPTIVE_CONTRAST = (METHODS[0], METHODS[1])
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260911


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _quality(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(f"quality must be bool or null, got {type(value).__name__}")


def _row_quality(row: dict[str, Any]) -> bool | None:
    """Use finish's observed format-failure rule; retain infrastructure unknown."""
    value = _quality(row.get("quality"))
    if value is None and row.get("outcome_type") in {"model_format_failure", "format_failure"}:
        return False
    if value is None and row.get("native_status") == "format_failure":
        return False
    return value


def _validate(rows: list[dict[str, Any]], strict: bool):
    required = {"task_id", "method", "replicate_id", "quality"}
    index = {}
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"record missing required fields: {sorted(missing)}")
        if row["method"] not in METHODS:
            raise ValueError(f"unknown method: {row['method']}")
        if row["replicate_id"] not in REPLICATES:
            raise ValueError(f"replicate_id must be one of {REPLICATES}, got {row['replicate_id']!r}")
        q = _quality(row["quality"])
        outcome = row.get("outcome_type")
        unavailable = {"control_ineligible", "generation_unavailable", "native_unavailable", "transport_failure",
                       "quota_failure", "authentication_failure", "provenance_failure", "model_workflow_failure"}
        if outcome in unavailable and q is not None:
            raise ValueError(f"{outcome} must have quality=null")
        if strict and outcome in {"model_format_failure", "format_failure"} and q is not False:
            raise ValueError(f"{outcome} must have quality=false after native evaluation")
        key = (str(row["task_id"]), row["method"], int(row["replicate_id"]))
        if key in index:
            raise ValueError(f"duplicate task/method/replicate cell: {key}")
        index[key] = row
    tasks = sorted({k[0] for k in index})
    if strict:
        if len(tasks) != 1000:
            raise ValueError(f"strict SCC series requires 1000 tasks, got {len(tasks)}")
        expected = {(task, method, rep) for task in tasks for method in METHODS for rep in REPLICATES}
        missing = sorted(expected - set(index))
        if missing:
            raise ValueError(f"strict SCC series missing {len(missing)} cells; first={missing[:3]}")
    return tasks, index


def _mean(values: Iterable[float | int | None], require_all: bool = True):
    values = list(values)
    if require_all and any(v is None for v in values):
        return None
    values = [float(v) for v in values if v is not None]
    return statistics.fmean(values) if values else None


def _quality_means(tasks, index):
    out = {}
    for task in tasks:
        for method in METHODS:
            vals = [_row_quality(index[(task, method, rep)]) if (task, method, rep) in index else None for rep in REPLICATES]
            out[(task, method)] = _mean(vals)
    return out


def _task_means(tasks, index, field):
    return {(task, method): _mean([_metric(index.get((task, method, rep), {}), field) for rep in REPLICATES])
            for task in tasks for method in METHODS}


def _metric(row: dict[str, Any], field: str):
    value = row.get(field)
    usage = row.get("resource_usage")
    if value is not None:
        return value
    if not isinstance(usage, dict) or not usage:
        return None
    # scc_export._resource exposes a known subtotal even when one or more
    # turns have no parseable usage.  Full-resource metrics are complete only
    # when every recorded turn is known; never zero-impute unknown turns.
    turns = usage.get("turns")
    unknown = usage.get("unknown_turns")
    known = usage.get("known_turns")
    complete = type(turns) is int and turns > 0 and unknown == 0 and known == turns
    if field == "known_api_equivalent_usd":
        return usage.get("known_api_equivalent_usd")
    if field == "known_input_tokens":
        return usage.get("input_tokens") if known is not None else None
    if field == "known_output_tokens":
        return usage.get("output_tokens") if known is not None else None
    if field == "api_equivalent_usd":
        return usage.get("known_api_equivalent_usd") if complete else None
    if field == "total_tokens":
        return (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) if complete else None
    return usage.get(field)


def _paired(means, tasks, left, right):
    return [means[(task, left)] - means[(task, right)] for task in tasks
            if means[(task, left)] is not None and means[(task, right)] is not None]


def _percentile(values, p):
    if not values:
        return None
    values = sorted(values); pos = (len(values) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] if lo == hi else values[lo] + (values[hi] - values[lo]) * (pos - lo)


def bootstrap(values: list[float], seed: int = BOOTSTRAP_SEED):
    """Conditional task-sampling percentile interval."""
    if not values:
        return {"n_tasks": 0, "mean": None, "ci95": [None, None], "seed": seed, "resamples": BOOTSTRAP_RESAMPLES}
    rng = random.Random(seed); n = len(values)
    samples = [sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAP_RESAMPLES)]
    return {"n_tasks": n, "mean": statistics.fmean(values), "ci95": [_percentile(samples, .025), _percentile(samples, .975)],
            "seed": seed, "resamples": BOOTSTRAP_RESAMPLES}


def _holm(pvalues):
    # The primary family is fixed at two pre-specified contrasts.  An
    # unestimable p-value remains null in output, but does not shrink the
    # multiplicity correction for the estimable member.
    family_size = len(pvalues)
    valid = sorted(((name, p) for name, p in pvalues.items() if p is not None), key=lambda x: x[1])
    adjusted = {name: None for name in pvalues}; running = 0.0
    for rank, (name, p) in enumerate(valid):
        running = max(running, min(1.0, (family_size - rank) * p)); adjusted[name] = running
    return adjusted


def _contrast(tasks, means, left, right):
    diffs = _paired(means, tasks, left, right); n = len(diffs)
    mean = statistics.fmean(diffs) if diffs else None
    sd = statistics.stdev(diffs) if n > 1 else None
    t_stat = mean / (sd / math.sqrt(n)) if mean is not None and sd not in (None, 0) else (0.0 if mean == 0 else None)
    p = float(2 * stats.t.sf(abs(t_stat), n - 1)) if t_stat is not None and n > 1 else None
    return {"left": left, "right": right, "n_tasks": n, "mean_difference": mean, "sd_task_differences": sd,
            "paired_t_statistic": t_stat, "t_statistic": t_stat, "p_two_sided": p, "p_value_two_sided": p,
            "bootstrap_task_sampling": bootstrap(diffs)}


def _quality_bounds(tasks, index, left, right):
    lower = upper = 0.0; unknown = 0
    for task in tasks:
        def extent(method):
            vals = [_row_quality(index[(task, method, rep)]) if (task, method, rep) in index else None for rep in REPLICATES]
            known = [int(v) for v in vals if v is not None]
            return sum(known) / 3, (sum(known) + 3 - len(known)) / 3, 3 - len(known)
        lo_l, hi_l, miss_l = extent(left); lo_r, hi_r, miss_r = extent(right)
        lower += lo_l - hi_r; upper += hi_l - lo_r; unknown += int(miss_l or miss_r)
    n = len(tasks)
    return {"task_count": n, "task_methods_with_unknown_repeats": unknown,
            "lower_difference": lower / n, "upper_difference": upper / n,
            "lower_difference_pp": 100 * lower / n, "upper_difference_pp": 100 * upper / n}


def _task_group(row):
    for key in ("subgroup", "task_group", "cohort", "task_cohort", "source_group"):
        if key in row and row[key] is not None:
            value = str(row[key]).lower().replace("-", "").replace("_", "")
            if "old200" in value or value in {"old", "original"}: return "old200"
            if "new800" in value or value in {"new", "extension"}: return "new800"
    return None


def _eligible_tasks(tasks, index, control_gate=None):
    if control_gate is not None:
        eligible_ids = control_gate.get("evaluable_task_ids")
        if eligible_ids is None:
            eligible_ids = control_gate.get("eligible_task_ids")
        if isinstance(eligible_ids, list):
            selected = [task for task in tasks if task in set(eligible_ids)]
            return selected, "supplied control gate evaluable_task_ids"
    labels = defaultdict(set)
    for row in index.values():
        label = None
        for key in ("control_eligible", "quality_eligible", "controls_complete"):
            if key in row: label = row[key] is True; break
        if label is None and "control_status" in row:
            label = str(row["control_status"]).lower() in {"eligible", "pass", "passed", "complete"}
        labels[row["task_id"]].add(label)
    if labels and all(any(v is not None for v in vals) for vals in labels.values()):
        selected = [task for task in tasks if labels.get(task) == {True}]
        return selected, "recorded control eligibility"
    control_excluded = {task for (task, _method, _rep), row in index.items()
                        if row.get("outcome_type") == "control_ineligible"}
    if control_excluded:
        return [task for task in tasks if task not in control_excluded], "finish outcome_type control_ineligible"
    return tasks, "control eligibility labels absent; all assigned tasks used"


def _subgroup_tasks(tasks, index, selection=None):
    if selection is not None:
        old = selection.get("prior_primary_task_ids")
        new = selection.get("new_task_ids")
        if isinstance(old, list) and isinstance(new, list):
            return {"old200": sorted(set(tasks) & set(old)), "new800": sorted(set(tasks) & set(new))}, "supplied selection prior_primary_task_ids/new_task_ids"
    groups = defaultdict(set)
    for row in index.values():
        group = _task_group(row)
        if group: groups[group].add(row["task_id"])
    return {group: sorted(values) for group, values in groups.items()}, "record-level subgroup labels"


def analyze(path: Path, strict: bool = False, selection: dict[str, Any] | None = None,
            control_gate: dict[str, Any] | None = None):
    rows = _rows(path); tasks, index = _validate(rows, strict)
    if strict and (selection is None or control_gate is None):
        raise ValueError("strict SCC analysis requires both selection and control gate inputs")
    eligible, eligibility_source = _eligible_tasks(tasks, index, control_gate)
    if strict:
        assigned_gate = control_gate.get("assigned_task_ids")
        eligible_gate = control_gate.get("evaluable_task_ids", control_gate.get("eligible_task_ids"))
        if isinstance(assigned_gate, list) and set(assigned_gate) != set(tasks):
            raise ValueError("strict control gate assigned_task_ids do not match the 1,000 analysis tasks")
        if not isinstance(eligible_gate, list) or len(eligible_gate) != 985 or not set(eligible_gate) <= set(tasks):
            raise ValueError("strict control gate must supply exactly 985 eligible task IDs within the assignment set")
        if len(eligible) != 985:
            raise ValueError(f"strict SCC analysis requires 985 control-eligible tasks, got {len(eligible)}")
        ineligible = set(tasks) - set(eligible)
        for (task, _method, _rep), row in index.items():
            if task in ineligible and _quality(row.get("quality")) is not None:
                raise ValueError("strict control-ineligible rows must have quality=null")
        old = selection.get("prior_primary_task_ids", [])
        new = selection.get("new_task_ids", [])
        if len(old) != 200 or len(new) != 800 or set(old) & set(new) or set(old) | set(new) != set(tasks):
            raise ValueError("strict selection must partition the 1,000 tasks into 200 old and 800 new tasks")
    quality = _quality_means(tasks, index); contrasts = {}; pvalues = {}
    for left, right in PRIMARY_CONTRASTS:
        name = f"{left}-{right}"; contrasts[name] = _contrast(tasks, quality, left, right); pvalues[name] = contrasts[name]["p_two_sided"]
    contrasts[f"{DESCRIPTIVE_CONTRAST[0]}-{DESCRIPTIVE_CONTRAST[1]}"] = _contrast(tasks, quality, *DESCRIPTIVE_CONTRAST)
    holm = _holm(pvalues)
    for name, adjusted in holm.items(): contrasts[name]["holm_adjusted_p"] = adjusted

    bounds = {"control_eligible": {"task_count": len(eligible)}, "all_assigned": {"task_count": len(tasks)}}
    for name, pair in {"SCC-SR": PRIMARY_CONTRASTS[0], "SCC-SN": PRIMARY_CONTRASTS[1], "SR-SN": DESCRIPTIVE_CONTRAST}.items():
        bounds["control_eligible"][name] = _quality_bounds(eligible, index, *pair)
        bounds["all_assigned"][name] = _quality_bounds(tasks, index, *pair)

    resource_candidates = ("api_equivalent_usd", "known_api_equivalent_usd", "known_input_tokens",
                           "known_output_tokens", "total_tokens", "resource_usd", "resource_cost")
    def _has_resource_field(field):
        for row in rows:
            usage = row.get("resource_usage")
            if field in row or (isinstance(usage, dict) and field in usage):
                return True
            if isinstance(usage, dict) and field in {"api_equivalent_usd", "known_api_equivalent_usd",
                                                     "known_input_tokens", "known_output_tokens", "total_tokens"}:
                if field == "api_equivalent_usd" and "known_api_equivalent_usd" in usage:
                    return True
                if field == "known_api_equivalent_usd" and "known_api_equivalent_usd" in usage:
                    return True
                if field in {"known_input_tokens", "known_output_tokens", "total_tokens"} and "turns" in usage:
                    return True
        return False
    resource_results = {}; resource_fields = [f for f in resource_candidates if _has_resource_field(f)]
    for field in resource_fields:
        means = _task_means(tasks, index, field); result = {}
        for left, right in PRIMARY_CONTRASTS + (DESCRIPTIVE_CONTRAST,):
            name = f"{left}-{right}"; diffs = _paired(means, tasks, left, right)
            pairs = [(means[(t, left)], means[(t, right)]) for t in tasks if means[(t, left)] is not None and means[(t, right)] is not None]
            ratios = [a / b for a, b in pairs if b != 0]
            result[name] = {"n_complete_task_pairs": len(diffs), "mean_paired_difference": statistics.fmean(diffs) if diffs else None,
                            "difference_bootstrap_task_sampling": bootstrap(diffs, BOOTSTRAP_SEED + 1),
                            "mean_paired_ratio": statistics.fmean(ratios) if ratios else None,
                            "ratio_of_means": (statistics.fmean([a for a, _ in pairs]) / statistics.fmean([b for _, b in pairs])
                                               if pairs and statistics.fmean([b for _, b in pairs]) != 0 else None),
                            "ratio_bootstrap_task_sampling": bootstrap(ratios, BOOTSTRAP_SEED + 2)}
        resource_results[field] = result

    groups, subgroup_source = _subgroup_tasks(tasks, index, selection)
    subgroup_results = {group: {name: _contrast(sorted(subset), quality, *pair) for name, pair in
                       {"SCC-SR": PRIMARY_CONTRASTS[0], "SCC-SN": PRIMARY_CONTRASTS[1], "SR-SN": DESCRIPTIVE_CONTRAST}.items()}
                        for group, subset in groups.items()}
    missing = Counter(str(row.get("outcome_type", row.get("native_status", "unknown"))) for row in rows if _row_quality(row) is None)
    return {"schema": "scc-analysis-v2", "analysis_timing": "planned/frozen SCC analysis contract; offline computation, no model calls",
            "strict_contract": {"enabled": strict, "expected_cells": 9000, "methods": list(METHODS), "replicates": list(REPLICATES)},
            "rows": len(rows), "task_count": len(tasks), "task_cluster_count": len(tasks), "unit": "task; mean of three repeats",
            "quality": {"unknown_quality_count": sum(missing.values()), "unknown_by_outcome_type": dict(missing), "null_quality_is_unknown": True, "model_format_failure_is_quality_false": True},
            "primary_family": [f"{SCC}-{METHODS[0]}", f"{SCC}-{METHODS[1]}"], "holm_alpha": 0.05,
            "contrasts": contrasts, "holm_adjusted_p": holm, "missingness_bounds": bounds,
            "control_eligibility": {"source": eligibility_source, "eligible_task_count": len(eligible)},
            "subgroups": subgroup_results, "subgroup_source": subgroup_source,
            "resources": resource_results,
            "interpretation": {"non_inferiority": "not assessed; no margin specified", "primary_tests": "Only SCC-SR and SCC-SN are in the two-test Holm family; SR-SN is descriptive.",
                               "repetition": "Replicate IDs are repeated executions, not provider seeds; task means prevent pseudoreplication.",
                               "ci": "Bootstrap intervals quantify conditional task-sampling uncertainty in observed complete pairs; they exclude provider/time variation and missingness mechanisms."}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--records", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--strict", action="store_true")
    parser.add_argument("--selection", type=Path); parser.add_argument("--control-gate", type=Path)
    args = parser.parse_args()
    if args.out.exists(): raise FileExistsError(f"Refuse to overwrite analysis: {args.out}")
    selection = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None
    control_gate = json.loads(args.control_gate.read_text(encoding="utf-8")) if args.control_gate else None
    result = analyze(args.records, strict=args.strict, selection=selection, control_gate=control_gate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"rows": result["rows"], "tasks": result["task_count"], "strict": args.strict}, ensure_ascii=False))


if __name__ == "__main__": main()
