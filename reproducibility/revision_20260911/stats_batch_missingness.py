"""Post-review missingness and original/continuation batch sensitivity.

This script reads only the frozen held-out-200 archive.  It makes no model
calls and writes all derived tables to this revision directory.  The unit of
analysis is the task (a task cluster in the original archive); each task has
one assigned cell per arm.  Batch is recovered from the continuation manifest
by cell id, not inferred from row order or from outcome availability.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARCHIVE = ROOT / "reproducibility/results/20260908_codex_mini_heldout200"
ANALYSIS = ARCHIVE / "analysis"
PROTOCOLS = ARCHIVE / "protocols"
OUT = HERE
OUT.mkdir(parents=True, exist_ok=True)

ARMS = ["single_neutral", "single_roles", "multi_neutral", "multi_roles", "direct"]
CONTRASTS = {
    "SR-SN": ("single_roles", "single_neutral"),
    "MR-MN": ("multi_roles", "multi_neutral"),
    "MN-SN": ("multi_neutral", "single_neutral"),
    "MR-SR": ("multi_roles", "single_roles"),
}
SEED = 20260911
BOOT = 10_000


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


candidate_path = ANALYSIS / "candidate_records.jsonl"
generation_path = PROTOCOLS / "heldout200_generation_manifest.json"
continuation_path = PROTOCOLS / "heldout200_continuation_manifest.json"
candidate = [json.loads(line) for line in candidate_path.read_text(encoding="utf-8").splitlines()]
assert len(candidate) == 996 and len({r["id"] for r in candidate}) == 996
generation = read_json(generation_path)
continuation = read_json(continuation_path)
planned = generation["shards"]
cells = [cell for shard in planned for cell in shard["manifest"]["cells"]]
assert len(cells) == 1000 and len({c["id"] for c in cells}) == 1000
pending = {c["id"] for c in continuation["pending_cells"]}
assert len(pending) == 540
assert all(c["id"] in pending for c in continuation["pending_cells"])
assert len([r for r in candidate if r.get("shard")]) == 539

by_id = {r["id"]: r for r in candidate}
records = {}
for cell in cells:
    rid = cell["id"]
    row = dict(cell)
    row["batch"] = "continuation" if rid in pending else "original"
    observed = by_id.get(rid)
    row["present_in_candidates"] = observed is not None
    row["analysis_status"] = observed.get("analysis_status") if observed else None
    row["missing_reason"] = None if observed else "submitted_incomplete_or_not_retained"
    row["quality"] = (1 if observed and observed.get("analysis_status") == "pass" else
                       0 if observed and observed.get("analysis_status") in {"fail", "timeout"} else None)
    for key in ("api_equivalent_usd", "uncached_sensitivity_usd", "total_tokens", "wall_seconds"):
        row[key] = observed.get(key) if observed else None
    row["task_cluster"] = row["task_id"]
    records[rid] = row

assert sum(r["batch"] == "original" for r in records.values()) == 460
assert sum(r["batch"] == "continuation" for r in records.values()) == 540
assert sum(r["present_in_candidates"] for r in records.values()) == 996
assert sum(r["analysis_status"] is None for r in records.values()) == 4 + 33  # four incomplete cells plus 33 retained control-gate exclusions

tasks = sorted({r["task_id"] for r in records.values()})
assert len(tasks) == 200
excluded = set(read_json(ANALYSIS / "summary.json").get("excluded_task_ids", []))
if not excluded:
    excluded = {r["task_id"] for r in candidate if r["analysis_status"] is None}
eligible = set(tasks) - excluded


def status(row):
    if row["analysis_status"] in {"pass", "fail", "timeout"}:
        return row["analysis_status"]
    return "unavailable"


def quality(row):
    return row["quality"]


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    k = (len(values) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def bootstrap(values, seed=SEED):
    """Task-cluster bootstrap percentile interval; descriptive only."""
    values = list(values)
    if not values:
        return {"n": 0, "mean": None, "ci95": [None, None], "seed": seed, "resamples": BOOT}
    rng = random.Random(seed)
    means = []
    n = len(values)
    for _ in range(BOOT):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    return {"n": n, "mean": sum(values) / n,
            "ci95": [percentile(means, .025), percentile(means, .975)],
            "seed": seed, "resamples": BOOT}


def arm_batch_summary(batch, arm):
    rows = [r for r in records.values() if r["batch"] == batch and r["arm"] == arm]
    observed = [r for r in rows if quality(r) is not None]
    return {
        "assigned": len(rows), "observed": len(observed),
        "unavailable": len(rows) - len(observed),
        "availability_rate": len(observed) / len(rows) if rows else None,
        "passes": sum(quality(r) == 1 for r in observed),
        "fails_including_timeout": sum(quality(r) == 0 for r in observed),
        "pass_rate_observed": (sum(quality(r) == 1 for r in observed) / len(observed)
                               if observed else None),
        "mean_api_equivalent_usd_observed": (sum(r["api_equivalent_usd"] for r in observed
                                                   if r["api_equivalent_usd"] is not None) /
                                              sum(r["api_equivalent_usd"] is not None for r in observed)
                                              if any(r["api_equivalent_usd"] is not None for r in observed) else None),
    }


def paired(batch, a, b, sample_tasks=None):
    sample_tasks = set(tasks if sample_tasks is None else sample_tasks)
    lookup = {(r["task_id"], r["arm"]): r for r in records.values()}
    pairs = []
    for task in sorted(sample_tasks):
        ra, rb = lookup[(task, a)], lookup[(task, b)]
        if ra["batch"] != batch or rb["batch"] != batch:
            continue
        if quality(ra) is None or quality(rb) is None:
            continue
        pairs.append((ra, rb))
    return pairs


def paired_summary(batch, name, a, b, sample_tasks=None):
    pairs = paired(batch, a, b, sample_tasks)
    diffs = [quality(ra) - quality(rb) for ra, rb in pairs]
    cost_diffs = [ra["api_equivalent_usd"] - rb["api_equivalent_usd"]
                  for ra, rb in pairs
                  if ra["api_equivalent_usd"] is not None and rb["api_equivalent_usd"] is not None]
    resource_pairs = []
    lookup = {(r["task_id"], r["arm"]): r for r in records.values()}
    for task in sorted(set(tasks if sample_tasks is None else sample_tasks)):
        ra, rb = lookup[(task, a)], lookup[(task, b)]
        if ra["batch"] == batch and rb["batch"] == batch and ra["api_equivalent_usd"] is not None and rb["api_equivalent_usd"] is not None:
            resource_pairs.append((ra, rb))
    resource_cost_diffs = [ra["api_equivalent_usd"] - rb["api_equivalent_usd"] for ra, rb in resource_pairs]
    return {
        "batch": batch, "contrast": name,
        "a": a, "b": b, "assigned_task_clusters": len(set(sample_tasks or tasks)),
        "complete_task_pairs": len(pairs),
        "coverage_of_assigned_tasks": len(pairs) / len(set(sample_tasks or tasks)) if sample_tasks else len(pairs) / len(tasks),
        "a_only_passes": sum(quality(ra) == 1 and quality(rb) == 0 for ra, rb in pairs),
        "b_only_passes": sum(quality(ra) == 0 and quality(rb) == 1 for ra, rb in pairs),
        "quality_difference_pp": 100 * sum(diffs) / len(diffs) if diffs else None,
        "quality_difference_descriptive_ci95_pp": [100 * x for x in bootstrap(diffs)["ci95"]] if diffs else [None, None],
        "quality_ci_type": "descriptive task-cluster bootstrap percentile interval; not provider/run uncertainty",
        "api_cost_difference_usd": sum(cost_diffs) / len(cost_diffs) if cost_diffs else None,
        "api_cost_descriptive_ci95_usd": bootstrap(cost_diffs, SEED + 1)["ci95"] if cost_diffs else [None, None],
        "api_cost_denominator": "quality-complete pairs (legacy field above)",
        "resource_complete_pairs": len(resource_pairs),
        "api_cost_difference_all_resource_pairs_usd": (sum(resource_cost_diffs) / len(resource_cost_diffs)
                                                        if resource_cost_diffs else None),
        "api_cost_ci95_all_resource_pairs_usd": (bootstrap(resource_cost_diffs, SEED + 2)["ci95"]
                                                  if resource_cost_diffs else [None, None]),
    }


batch_rows = []
for batch in ("original", "continuation"):
    for arm in ARMS:
        row = {"batch": batch, "arm": arm}
        row.update(arm_batch_summary(batch, arm))
        batch_rows.append(row)
with (OUT / "batch_arm_summary.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=batch_rows[0].keys())
    writer.writeheader(); writer.writerows(batch_rows)

paired_rows = []
for batch in ("original", "continuation"):
    for name, (a, b) in CONTRASTS.items():
        paired_rows.append(paired_summary(batch, name, a, b))

# A cross-batch pair has observed endpoints in different execution batches.
# It is retained as a coverage diagnostic only; it does not identify a batch
# or provider effect because batch is confounded with execution chronology.
cross_rows = []
for name, (a, b) in CONTRASTS.items():
    lookup = {(r["task_id"], r["arm"]): r for r in records.values()}
    counts = Counter()
    for task in tasks:
        ra, rb = lookup[(task, a)], lookup[(task, b)]
        if quality(ra) is None or quality(rb) is None:
            continue
        label = "original-original" if ra["batch"] == rb["batch"] == "original" else "continuation-continuation" if ra["batch"] == rb["batch"] == "continuation" else "cross-batch"
        counts[label] += 1
    cross_rows.append({"contrast": name, "original_original_pairs": counts["original-original"],
                       "continuation_continuation_pairs": counts["continuation-continuation"],
                       "cross_batch_complete_pairs": counts["cross-batch"],
                       "all_complete_pairs": sum(counts.values()),
                       "interpretation": "coverage diagnostic; no causal/provider-drift interpretation"})
with (OUT / "cross_batch_coverage.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=cross_rows[0].keys())
    writer.writeheader(); writer.writerows(cross_rows)
with (OUT / "batch_paired_contrasts.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=paired_rows[0].keys())
    writer.writeheader(); writer.writerows(paired_rows)


def interval(row):
    if quality(row) is None:
        return (0, 1)
    return (quality(row), quality(row))


def identification_bounds(sample_tasks, a, b):
    lookup = {(r["task_id"], r["arm"]): r for r in records.values()}
    lower = upper = 0
    missing_endpoints = 0
    for task in sorted(sample_tasks):
        la, ua = interval(lookup[(task, a)])
        lb, ub = interval(lookup[(task, b)])
        lower += la - ub; upper += ua - lb
        missing_endpoints += int(la != ua or lb != ub)
    n = len(set(sample_tasks))
    return {"task_clusters": n, "task_clusters_with_unobserved_endpoint": missing_endpoints,
            "lower_difference_pp": 100 * lower / n, "upper_difference_pp": 100 * upper / n}


bounds = {name: {"control_eligible_193": identification_bounds(eligible, a, b),
                 "all_assigned_200": identification_bounds(tasks, a, b)}
          for name, (a, b) in CONTRASTS.items()}

# Recompute and compare the published bounds independently from this script's
# task-arm table; this is a check against check_missingness.py, not a replacement.
published_path = ROOT / "reviews/2026-09-09-editorial/missingness-bounds.json"
if published_path.exists():
    published = read_json(published_path)
    for name, contrast in bounds.items():
        old = published["contrasts"][name]
        for key, old_key in (("control_eligible_193", "eligible_tasks"),
                             ("all_assigned_200", "all_assigned_tasks")):
            assert contrast[key]["task_clusters"] == old[old_key]["task_count"]
            assert contrast[key]["task_clusters_with_unobserved_endpoint"] == old[old_key]["tasks_with_unobserved_endpoint"]
            assert abs(contrast[key]["lower_difference_pp"] - old[old_key]["lower_difference_pp"]) < 1e-12
            assert abs(contrast[key]["upper_difference_pp"] - old[old_key]["upper_difference_pp"]) < 1e-12

payload = {
    "analysis": "Post hoc batch and missingness sensitivity; no new model calls.",
    "source_archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
    "source_sha256": {"candidate_records.jsonl": sha256(candidate_path),
                       "heldout200_generation_manifest.json": sha256(generation_path),
                       "heldout200_continuation_manifest.json": sha256(continuation_path)},
    "recovered_batch_rule": "continuation iff cell id occurs in heldout200_continuation_manifest.pending_cells; otherwise original",
    "assignment_counts": {"total": len(records), "original": 460, "continuation": 540,
                           "candidate_records": len(candidate), "submitted_incomplete": 4,
                           "control_ineligible_tasks": len(set(tasks) - eligible)},
    "estimand_notes": {
        "quality": "Pass=1; fail and native timeout=0 under the frozen archive's observed-failure rule; unavailable endpoint remains unknown in identification bounds.",
        "identification_bounds": "Sharp finite-sample ranges under independent 0/1 completion of each unknown endpoint; these are identification limits, not confidence intervals.",
        "batch": "Within-batch complete task pairs only. Original-only results have changed task-arm coverage and are not an unbiased counterfactual for a fully original run.",
        "ci": "Reported bootstrap intervals are descriptive task-cluster percentile intervals and do not quantify provider/model/run uncertainty or batch assignment uncertainty.",
    },
    "missingness_identification_bounds": bounds,
    "batch_arm_summary_csv": "batch_arm_summary.csv",
    "batch_paired_contrasts_csv": "batch_paired_contrasts.csv",
    "cross_batch_coverage_csv": "cross_batch_coverage.csv",
    "cross_batch_interpretation": "Cross-batch complete pairs are a coverage diagnostic only; batch is confounded with execution chronology and no provider-drift or causal batch effect is identified.",
}
(OUT / "batch_missingness_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Independent numerical cross-check: recompute all bounds from emitted CSV-like
# records and assert the task-arm inventory and monotonicity are intact.
assert len(records) == 1000
assert Counter(r["batch"] for r in records.values()) == Counter({"continuation": 540, "original": 460})
assert all(-100 <= x["lower_difference_pp"] <= x["upper_difference_pp"] <= 100
           for contrast in bounds.values() for x in contrast.values())
print(json.dumps({"assignment_counts": payload["assignment_counts"], "bounds": bounds,
                  "paired": paired_rows}, ensure_ascii=False, indent=2))
