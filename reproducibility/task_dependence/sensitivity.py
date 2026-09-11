"""Supplementary quality intervals with source-related tasks resampled together."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from .audit import ROOT, digest, encoded
from reproducibility.evidence_manifest import verify

REPEATS = (101, 102, 103)
GRAPHS = ("union_070_code_exact", "prompt_050", "prompt_070", "prompt_090")
CONTRASTS = {
    "factorial": [("single_roles", "single_neutral"), ("multi_roles", "multi_neutral"),
                   ("multi_neutral", "single_neutral"), ("multi_roles", "single_roles")],
    "scc": [("scc_author_2024_codex_transport", "single_roles"),
            ("scc_author_2024_codex_transport", "single_neutral")],
}


def family_bootstrap(values: dict[str, float], groups: list[list[str]], *, draws=10000, seed=20260911):
    flattened = [task for group in groups for task in group]
    if len(flattened) != len(set(flattened)) or not set(values) <= set(flattened):
        raise ValueError("Groups overlap or omit observed tasks")
    if any(not np.isfinite(value) or not -1 <= value <= 1 for value in values.values()):
        raise ValueError("Invalid paired binary-quality mean difference")
    observed = [[values[task] for task in group if task in values] for group in groups]
    observed = [group for group in observed if group]
    sizes = np.array([len(group) for group in observed], dtype=np.int64)
    sums = np.array([sum(group) for group in observed], dtype=float)
    n = int(sizes.sum()); count = len(observed)
    report = {"tasks": n, "families": count, "mean_task_difference": float(sums.sum() / n) if n else None,
        "family_balanced_difference": float(np.mean(sums / sizes)) if n else None,
        "size_effective_family_count": float(n * n / (sizes @ sizes)) if n else None,
        "largest_family_share": float(sizes.max() / n) if n else None,
        "ci95": None, "bootstrap_variance": None, "degenerate_draws": None,
        "resamples": draws, "seed": seed, "interval_status": "unestimable_fewer_than_two_families"}
    if count < 2: return report, np.array([], dtype=float)
    rng = np.random.default_rng(seed); samples = np.empty(draws, dtype=float)
    for start in range(0, draws, 128):
        indices = rng.integers(0, count, size=(min(128, draws - start), count))
        samples[start:start + len(indices)] = sums[indices].sum(axis=1) / sizes[indices].sum(axis=1)
    report.update(ci95=[float(x) for x in np.quantile(samples, [.025, .975])],
        bootstrap_variance=float(np.var(samples, ddof=1)), degenerate_draws=bool(np.ptp(samples) == 0),
        interval_status="degenerate" if np.ptp(samples) == 0 else "estimated")
    return report, samples


def paired_means(rows, assigned, eligible, study):
    methods = {method for pair in CONTRASTS[study] for method in pair}
    if study == "factorial": methods.add("direct")
    field = "arm" if study == "factorial" else "method"
    index = {}
    for row in rows:
        key = row["task_id"], row[field], row["replicate_id"]
        if key in index: raise ValueError("Duplicate assignment")
        if row.get("quality") is not None and type(row["quality"]) is not bool:
            raise ValueError("Quality must be an observed boolean or explicit null")
        if row["task_id"] not in eligible and row.get("quality") is not None:
            raise ValueError("Control-ineligible quality is observed")
        index[key] = row.get("quality")
    expected = {(task, method, repeat) for task in assigned for method in methods for repeat in REPEATS}
    if set(index) != expected: raise ValueError("Ledger is not the complete frozen assignment matrix")
    result = {}
    for left, right in CONTRASTS[study]:
        values = {}
        for task in sorted(eligible):
            a = [index[(task, left, repeat)] for repeat in REPEATS]
            b = [index[(task, right, repeat)] for repeat in REPEATS]
            if all(value is not None for value in a + b):
                values[task] = sum(int(x) - int(y) for x, y in zip(a, b)) / 3
        result[left + "_minus_" + right] = values
    return result


def run(root: Path, study: str, audit: Path, output: Path):
    if output.exists(): raise FileExistsError("Refusing to overwrite supplementary analysis")
    generation = root / "generation"
    if not (generation / "status.json").is_file() or json.loads((generation / "status.json").read_text()).get("state") != "generation_finished":
        raise ValueError("Generation is not terminal")
    if (generation / "DISPATCH.lock").exists() or not (root / "analysis/summary.json").is_file():
        raise ValueError("Main generation or analysis is incomplete")
    verify(audit)
    selection_path = ROOT / "reproducibility/scale1000/inputs-v1/selection.json"
    selection = json.loads(selection_path.read_text()); source_summary = json.loads((audit / "summary.json").read_text())
    if source_summary["selection_sha256"] != digest(selection_path.read_bytes()):
        raise ValueError("Source audit belongs to another allocation")
    gate_path = ROOT / "reproducibility/results/20260908_scale1000_preflight/controls-v3/heldout200_control_gate.json"
    gate = json.loads(gate_path.read_text()); assigned = set(selection["assigned_task_ids"])
    eligible = set(gate["evaluable_task_ids"])
    if set(gate["assigned_task_ids"]) != assigned or len(assigned) != 1000 or len(eligible) != 985:
        raise ValueError("Frozen task/control allocation changed")
    records = root / ("analysis/candidate_records.jsonl" if study == "factorial" else "candidate_records.jsonl")
    rows = [json.loads(line) for line in records.read_text(encoding="utf-8").splitlines() if line.strip()]
    values = paired_means(rows, assigned, eligible, study)
    partitions = json.loads((audit / "partitions.json").read_text())
    summaries = {}; samples = {}
    for name in GRAPHS:
        groups = partitions[name]["assigned_components"]
        if set(task for group in groups for task in group) != assigned:
            raise ValueError("Source partition differs from assigned IDs")
        summaries[name] = {}
        for contrast, differences in values.items():
            result, draws = family_bootstrap(differences, groups)
            summaries[name][contrast] = result; samples[name + "--" + contrast] = draws
    output.mkdir(parents=True)
    for name, draws in samples.items():
        (output / (name + ".json")).write_bytes(encoded(draws.tolist()))
    report = {"schema": "source-family-quality-sensitivity-v1", "study": study, "supplementary_only": True,
        "records_sha256": digest(records.read_bytes()), "partitions_sha256": digest((audit / "partitions.json").read_bytes()),
        "control_gate_sha256": digest(gate_path.read_bytes()), "graphs": summaries,
        "interpretation": "Observed complete pairs; graph-conditional descriptive intervals, no new hypothesis family or exclusions."}
    (output / "summary.json").write_bytes(encoded(report))
    return {"study": study, "rows": len(rows), "graphs": len(summaries)}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--run-root", type=Path, required=True)
    p.add_argument("--study", choices=sorted(CONTRASTS), required=True)
    p.add_argument("--audit", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); print(json.dumps(run(a.run_root, a.study, a.audit, a.output)))
