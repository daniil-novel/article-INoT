from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib
import numpy as np
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXPECTED_COMMIT = "010211ee5775185e8330ab6cde06e912c2adcb9e"
ARCHS = ("B2_ClassicalMAS", "B3_HybridINoT")
CONTEXTS = (256, 1024, 4096, 16384)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def portable_source_path(path: Path, *, research_root: Path, article_root: Path) -> str:
    resolved = path.resolve()
    roots = (
        (research_root.resolve(), "INoT_Research"),
        (article_root.resolve(), "article-INoT"),
    )
    for root, label in roots:
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        return f"{label}/{relative.as_posix()}"
    raise ValueError(f"evidence path is outside declared repositories: {path}")


def read_e3_rows(paths: Path | list[Path]) -> list[dict]:
    selected = [paths] if isinstance(paths, Path) else paths
    return [row for path in selected for row in read_json(path)]


def validate_e3_rows(paths: Path | list[Path], *, expected_n: int, label: str) -> dict:
    rows = read_e3_rows(paths)
    expected_architectures = {"B0_SingleLarge", *ARCHS}
    expected_task_ids = {f"HumanEval/{index}" for index in range(expected_n)}
    keys: set[tuple[str, int, str, int]] = set()
    issues: list[str] = []
    model_names: set[str] = set()
    seeds: set[int] = set()
    bucket_sizes: Counter[tuple[str, int]] = Counter()
    compressed_proxy_counts: dict[int, list[int]] = defaultdict(list)

    for row in rows:
        architecture = str(row.get("architecture"))
        context = int(row.get("extra", {}).get("context_target_tokens", -1))
        task_with_context = str(row.get("task_id", ""))
        task_id = task_with_context.split("@ctx", 1)[0]
        seed = int(row.get("seed", -1))
        key = (task_id, seed, architecture, context)
        if key in keys:
            issues.append(f"duplicate key {key}")
        keys.add(key)
        seeds.add(seed)
        bucket_sizes[(architecture, context)] += 1

        if architecture not in expected_architectures:
            issues.append(f"unexpected architecture {architecture}")
        if context not in CONTEXTS:
            issues.append(f"unexpected context {context}")
        if task_id not in expected_task_ids:
            issues.append(f"unexpected task {task_id}")
        if not task_with_context.endswith(f"@ctx{context}"):
            issues.append(f"context suffix mismatch for {task_with_context}")

        total = int(row.get("total_tokens", -1))
        input_tokens = int(row.get("input_tokens", -1))
        output_tokens = int(row.get("output_tokens", -1))
        if total != input_tokens + output_tokens:
            issues.append(f"token total mismatch for {key}")
        if total <= 0 or float(row.get("cost_usd", 0)) <= 0:
            issues.append(f"non-positive paid usage for {key}")
        if architecture == "B3_HybridINoT":
            compressed_tokens = row.get("extra", {}).get("compressed_tokens")
            if compressed_tokens is None:
                issues.append(f"missing compressed token count for {key}")
            else:
                compressed_proxy_counts[context].append(int(compressed_tokens))

        usages = row.get("usages", [])
        if not usages:
            issues.append(f"missing usage trace for {key}")
            continue
        usage_input = sum(int(usage["input_tokens"]) for usage in usages)
        usage_output = sum(int(usage["output_tokens"]) for usage in usages)
        usage_cost = sum(float(usage["cost_usd"]) for usage in usages)
        if usage_input != input_tokens or usage_output != output_tokens:
            issues.append(f"usage token mismatch for {key}")
        if not math.isclose(
            usage_cost, float(row["cost_usd"]), rel_tol=0, abs_tol=1e-12
        ):
            issues.append(f"usage cost mismatch for {key}")
        model_names.update(str(usage["model"]) for usage in usages)

    expected_buckets = {
        (architecture, context): expected_n
        for architecture in expected_architectures
        for context in CONTEXTS
    }
    for bucket, expected_size in expected_buckets.items():
        if bucket_sizes[bucket] != expected_size:
            issues.append(
                f"bucket {bucket} has {bucket_sizes[bucket]}, expected {expected_size}"
            )
    expected_rows = len(expected_architectures) * len(CONTEXTS) * expected_n
    if len(rows) != expected_rows:
        issues.append(f"row count {len(rows)}, expected {expected_rows}")
    if issues:
        raise ValueError(f"{label} failed data-quality checks:\n" + "\n".join(issues))

    return {
        "label": label,
        "unit_of_analysis": "task x architecture x target-context x seed",
        "row_count": len(rows),
        "expected_row_count": expected_rows,
        "unique_key_count": len(keys),
        "architectures": sorted(expected_architectures),
        "contexts": list(CONTEXTS),
        "task_ids": sorted(expected_task_ids),
        "seeds": sorted(seeds),
        "models": sorted(model_names),
        "duplicate_keys": 0,
        "missing_buckets": 0,
        "token_accounting_mismatches": 0,
        "usage_trace_mismatches": 0,
        "paid_usage_positive": True,
        "compressed_context_proxy_tokens": {
            "selection_block_sum_budget": 4096,
            "serialized_count_includes_join_separators": True,
            "interpretation": (
                "the selector budgets block proxy counts before retained blocks "
                "are joined; the serialized count may therefore exceed 4096"
            ),
            "by_target_context": {
                str(context): {
                    "minimum": min(compressed_proxy_counts[context]),
                    "maximum": max(compressed_proxy_counts[context]),
                    "count_above_block_sum_budget": sum(
                        value > 4096 for value in compressed_proxy_counts[context]
                    ),
                    "row_count": len(compressed_proxy_counts[context]),
                }
                for context in CONTEXTS
            },
            "observed_maximum": max(
                value for values in compressed_proxy_counts.values() for value in values
            ),
        },
        "status": "pass",
    }


def summarize_e3(paths: Path | list[Path]) -> dict:
    rows = read_e3_rows(paths)
    summary: dict[str, dict[str, dict]] = {}
    keys = set()
    for row in rows:
        ctx = int(row["extra"]["context_target_tokens"])
        key = (row["task_id"], row["seed"], row["architecture"], ctx)
        if key in keys:
            raise ValueError(f"duplicate E3 run key: {key}")
        keys.add(key)
    for arch in ("B0_SingleLarge", *ARCHS):
        summary[arch] = {}
        for ctx in CONTEXTS:
            bucket = [
                row
                for row in rows
                if row["architecture"] == arch
                and int(row["extra"]["context_target_tokens"]) == ctx
            ]
            if not bucket:
                raise ValueError(f"missing E3 bucket {arch}@{ctx}")
            summary[arch][str(ctx)] = {
                "n": len(bucket),
                "pass_at_1": mean(float(row["passed"]) for row in bucket),
                "mean_tokens": mean(row["total_tokens"] for row in bucket),
                "mean_input_tokens": mean(row["input_tokens"] for row in bucket),
                "mean_output_tokens": mean(row["output_tokens"] for row in bucket),
                "mean_cost_usd": mean(row["cost_usd"] for row in bucket),
                "mean_latency_seconds": mean(
                    row["wall_clock_seconds"] for row in bucket
                ),
                "models": sorted(
                    {
                        usage["model"]
                        for row in bucket
                        for usage in row.get("usages", [])
                    }
                ),
            }
    for ctx in CONTEXTS:
        b2 = summary["B2_ClassicalMAS"][str(ctx)]
        b3 = summary["B3_HybridINoT"][str(ctx)]
        b3["token_savings_vs_b2_pct"] = 100 * (
            1 - b3["mean_tokens"] / b2["mean_tokens"]
        )
        b3["cost_savings_vs_b2_pct"] = 100 * (
            1 - b3["mean_cost_usd"] / b2["mean_cost_usd"]
        )
        b3["delta_pass_at_1_pp_vs_b2"] = 100 * (b3["pass_at_1"] - b2["pass_at_1"])
        b3["relative_utok_gain_vs_b2_pct"] = 100 * (
            (
                b3["pass_at_1"] * 1000 / b3["mean_tokens"]
                - b2["pass_at_1"] * 1000 / b2["mean_tokens"]
            )
            / (b2["pass_at_1"] * 1000 / b2["mean_tokens"])
        )
    return summary


def paired_e3_statistics(paths: Path | list[Path]) -> list[dict]:
    rows = read_e3_rows(paths)
    comparisons = []
    for ctx in CONTEXTS:
        subsets = {}
        for arch in ARCHS:
            subsets[arch] = {
                (row["task_id"], row["seed"]): row
                for row in rows
                if row["architecture"] == arch
                and int(row["extra"]["context_target_tokens"]) == ctx
            }
        keys = sorted(set(subsets[ARCHS[0]]) & set(subsets[ARCHS[1]]))
        if len(keys) < 2:
            raise ValueError(f"insufficient paired E3 rows at context {ctx}")
        b2 = [subsets[ARCHS[0]][key] for key in keys]
        b3 = [subsets[ARCHS[1]][key] for key in keys]
        per_task_u2 = np.array(
            [1000 * float(row["passed"]) / row["total_tokens"] for row in b2]
        )
        per_task_u3 = np.array(
            [1000 * float(row["passed"]) / row["total_tokens"] for row in b3]
        )
        differences = per_task_u3 - per_task_u2
        if np.any(per_task_u2 <= 0):
            raise ValueError(
                f"paired relative U_tok gain is undefined at context {ctx}"
            )
        per_task_relative_gains = 100 * (per_task_u3 / per_task_u2 - 1)
        if np.allclose(differences, 0):
            wilcoxon_p = 1.0
        else:
            wilcoxon_p = float(
                stats.wilcoxon(
                    per_task_u3,
                    per_task_u2,
                    zero_method="wilcox",
                    alternative="two-sided",
                ).pvalue
            )
        practical_margin_differences = per_task_relative_gains - 15.0
        practical_margin_p = (
            1.0
            if np.allclose(practical_margin_differences, 0)
            else float(
                stats.wilcoxon(
                    practical_margin_differences,
                    zero_method="wilcox",
                    alternative="greater",
                ).pvalue
            )
        )
        rng = np.random.default_rng(12345)
        sample_indices = rng.integers(0, len(keys), size=(10000, len(keys)))
        bootstrap_mean_gains = per_task_relative_gains[sample_indices].mean(axis=1)
        ci_low, ci_high = np.quantile(bootstrap_mean_gains, [0.025, 0.975])
        b2_only = sum(
            1 for row2, row3 in zip(b2, b3) if row2["passed"] and not row3["passed"]
        )
        b3_only = sum(
            1 for row2, row3 in zip(b2, b3) if not row2["passed"] and row3["passed"]
        )
        discordant = b2_only + b3_only
        mcnemar_p = (
            1.0
            if discordant == 0
            else float(
                stats.binomtest(
                    min(b2_only, b3_only), discordant, 0.5, alternative="two-sided"
                ).pvalue
            )
        )
        comparisons.append(
            {
                "context_target_tokens": ctx,
                "n_pairs": len(keys),
                "pass_at_1_b2": mean(float(row["passed"]) for row in b2),
                "pass_at_1_b3": mean(float(row["passed"]) for row in b3),
                "estimand": (
                    "mean within-task relative U_tok gain, 100 * mean(U_B3/U_B2 - 1)"
                ),
                "mean_within_task_relative_utok_gain_pct": float(
                    per_task_relative_gains.mean()
                ),
                "median_within_task_relative_utok_gain_pct": float(
                    np.median(per_task_relative_gains)
                ),
                "minimum_within_task_relative_utok_gain_pct": float(
                    per_task_relative_gains.min()
                ),
                "maximum_within_task_relative_utok_gain_pct": float(
                    per_task_relative_gains.max()
                ),
                "mean_within_task_relative_utok_gain_resampling_interval_pct": [
                    float(ci_low),
                    float(ci_high),
                ],
                "pairs_at_or_above_15_pct": int(np.sum(per_task_relative_gains >= 15)),
                "wilcoxon_p_utok": wilcoxon_p,
                "wilcoxon_one_sided_p_gain_above_15_pct": practical_margin_p,
                "inferential_scope": (
                    "conditional rank-based sensitivity analysis for the fixed "
                    "task set and single retained API run; the Wilcoxon test "
                    "targets a symmetric location shift, not the reported mean"
                ),
                "resampling_interval_scope": (
                    "2.5--97.5 percentile task-resampling stability interval; "
                    "not a design-based population confidence interval"
                ),
                "mcnemar_exact_p": mcnemar_p,
                "discordant_b2_only": b2_only,
                "discordant_b3_only": b3_only,
            }
        )
    for field, output_field in (
        ("wilcoxon_p_utok", "holm_reject_zero_gain"),
        (
            "wilcoxon_one_sided_p_gain_above_15_pct",
            "holm_reject_gain_le_15_pct",
        ),
    ):
        p_values = [row[field] for row in comparisons]
        order = sorted(range(len(p_values)), key=p_values.__getitem__)
        rejected = [False] * len(p_values)
        for rank, index in enumerate(order):
            if p_values[index] <= 0.05 / (len(p_values) - rank):
                rejected[index] = True
            else:
                break
        for row, decision in zip(comparisons, rejected):
            row[output_field] = decision
    return comparisons


def humaneval_input_profile(research_root: Path) -> dict:
    sys.path.insert(0, str(research_root / "src"))
    from inot.tasks import load_humaneval

    profile = {}
    for n in (5, 20):
        profile[str(n)] = {}
        tasks_by_context = {}
        for ctx in (256, 512, 1024, 2048, 4096, 8192, 16384):
            tasks = load_humaneval(n=n, context_target_tokens=ctx, seed=42)
            actual = [int(task.metadata["context_actual_tokens"]) for task in tasks]
            tasks_by_context[str(ctx)] = {
                "task_ids": [task.metadata["original_id"] for task in tasks],
                "actual_context_tokens_min": min(actual),
                "actual_context_tokens_mean": mean(actual),
                "actual_context_tokens_max": max(actual),
            }
        profile[str(n)] = tasks_by_context
    return profile


def exact_zero_harm_noninferiority_bound(
    *, n_pairs: int, alpha: float = 0.05, margin: float = 0.02
) -> dict:
    if n_pairs <= 0:
        raise ValueError("n_pairs must be positive")
    upper = 1 - alpha ** (1 / n_pairs)
    minimum_zero_harm_pairs = math.ceil(math.log(alpha) / math.log(1 - margin))
    return {
        "method": (
            "one-sided Clopper-Pearson zero-event reference bound under an "
            "iid Bernoulli task-sampling model"
        ),
        "n_unique_task_pairs": n_pairs,
        "observed_harmful_pairs_b2_pass_b3_fail": 0,
        "nominal_reference_level": 1 - alpha,
        "upper_bound_harm_probability": upper,
        "upper_bound_harm_percentage_points": 100 * upper,
        "noninferiority_margin_percentage_points": 100 * margin,
        "noninferiority_established": bool(upper < margin),
        "minimum_zero_harm_pairs_required": minimum_zero_harm_pairs,
        "upper_bound_if_all_164_humaneval_pairs_are_zero_harm": (
            100 * (1 - alpha ** (1 / 164))
        ),
        "scope_note": (
            "The four context cells reuse the same tasks, so the bound uses "
            "20 unique task pairs rather than 80 correlated observations. "
            "Because these are the first non-random HumanEval tasks and one "
            "retained API run, the nominal level is a planning reference, not "
            "design-valid population coverage."
        ),
    }


def context_scaling_slopes(
    paths: Path | list[Path],
    *,
    research_root: Path,
    n_tasks: int,
    label: str,
) -> dict:
    rows = read_e3_rows(paths)
    sys.path.insert(0, str(research_root / "src"))
    from inot.tasks import load_humaneval

    actual_context: dict[tuple[str, int], int] = {}
    for context in CONTEXTS:
        for task in load_humaneval(n=n_tasks, context_target_tokens=context, seed=42):
            actual_context[(str(task.metadata["original_id"]), context)] = int(
                task.metadata["context_actual_tokens"]
            )

    by_key = {
        (
            str(row["task_id"]).split("@ctx", 1)[0],
            str(row["architecture"]),
            int(row["extra"]["context_target_tokens"]),
        ): row
        for row in rows
    }
    task_ids = [f"HumanEval/{index}" for index in range(n_tasks)]
    per_task_slopes: dict[str, list[float]] = {arch: [] for arch in ARCHS}
    for task_id in task_ids:
        x = np.array(
            [actual_context[(task_id, context)] for context in CONTEXTS],
            dtype=float,
        )
        for architecture in ARCHS:
            y = np.array(
                [
                    by_key[(task_id, architecture, context)]["total_tokens"]
                    for context in CONTEXTS
                ],
                dtype=float,
            )
            per_task_slopes[architecture].append(float(np.polyfit(x, y, 1)[0]))

    rng = np.random.default_rng(12345)
    summaries = {}
    for architecture, values in per_task_slopes.items():
        array = np.asarray(values, dtype=float)
        indices = rng.integers(0, len(array), size=(10000, len(array)))
        bootstrap_means = array[indices].mean(axis=1)
        ci_low, ci_high = np.quantile(bootstrap_means, [0.025, 0.975])
        summaries[architecture] = {
            "n_task_slopes": len(array),
            "mean_gridwide_ols_slope_tokens_per_context_token": float(array.mean()),
            "median_gridwide_ols_slope_tokens_per_context_token": float(
                np.median(array)
            ),
            "mean_task_resampling_interval": [float(ci_low), float(ci_high)],
            "minimum_task_slope": float(array.min()),
            "maximum_task_slope": float(array.max()),
            "per_task_slopes": [float(value) for value in array],
        }

    b2 = np.asarray(per_task_slopes[ARCHS[0]], dtype=float)
    b3 = np.asarray(per_task_slopes[ARCHS[1]], dtype=float)
    paired_difference = b2 - b3
    difference_indices = rng.integers(
        0,
        len(paired_difference),
        size=(10000, len(paired_difference)),
    )
    bootstrap_difference = paired_difference[difference_indices].mean(axis=1)
    diff_ci_low, diff_ci_high = np.quantile(bootstrap_difference, [0.025, 0.975])
    return {
        "label": label,
        "model": sorted(
            {usage["model"] for row in rows for usage in row.get("usages", [])}
        ),
        "estimand": (
            "per-task OLS slope of total tokens against actual context "
            "tokens over four target-context cells"
        ),
        "contexts": list(CONTEXTS),
        "architectures": summaries,
        "paired_b2_minus_b3": {
            "mean_gridwide_ols_slope_difference": float(paired_difference.mean()),
            "mean_task_resampling_interval": [
                float(diff_ci_low),
                float(diff_ci_high),
            ],
            "wilcoxon_two_sided_p": float(stats.wilcoxon(paired_difference).pvalue),
            "all_task_differences_positive": bool(np.all(paired_difference > 0)),
        },
        "interpretation": (
            "grid-wide four-point linear summary, not a marginal derivative; "
            "B3 changes compression regime at the 4096-token boundary"
        ),
        "uncertainty_scope": (
            "task-resampling stability only; seed and repeated API-run "
            "uncertainty are not represented"
        ),
    }


def derive_e4_screening_diagnostic(summary: dict) -> dict:
    output = {
        "estimand": (
            "agreement of the small-model PASS/REJECT screen with the "
            "retained B0 external-verification outcome"
        ),
        "status": "exploratory_aggregate_only",
        "policy_effect_evaluated": False,
        "auditability_note": (
            "Per-case small-check decisions, costs and final candidate texts "
            "were not persisted; the confusion tables below are reconstructed "
            "from aggregate counts and cannot reproduce the original bootstrap."
        ),
        "datasets": {},
    }
    for dataset, values in summary.items():
        n = int(values["n_tasks"])
        failures = int(round(float(values["rho_0"]) * n))
        correct = n - failures
        failed_pass = int(round(float(values["rho_1"]) * n))
        failed_reject = failures - failed_pass
        small_pass = int(values["small_decision_counts"]["PASS"])
        small_reject = int(values["small_decision_counts"]["REJECT"])
        correct_pass = small_pass - failed_pass
        correct_reject = correct - correct_pass
        cells = (correct_pass, correct_reject, failed_pass, failed_reject)
        if min(cells) < 0 or small_pass + small_reject != n:
            raise ValueError(f"inconsistent aggregate E4 counts for {dataset}")

        aligned = correct_pass + failed_reject
        alpha = 0.05
        ci_low = (
            0.0
            if aligned == 0
            else float(stats.beta.ppf(alpha / 2, aligned, n - aligned + 1))
        )
        ci_high = (
            1.0
            if aligned == n
            else float(stats.beta.ppf(1 - alpha / 2, aligned + 1, n - aligned))
        )
        sensitivity_correct = correct_pass / correct if correct else math.nan
        specificity_failure = failed_reject / failures if failures else math.nan
        balanced_accuracy = float(
            np.nanmean([sensitivity_correct, specificity_failure])
        )
        output["datasets"][dataset] = {
            "n": n,
            "confusion_matrix": {
                "externally_correct_screen_pass": correct_pass,
                "externally_correct_screen_reject": correct_reject,
                "externally_failed_screen_pass": failed_pass,
                "externally_failed_screen_reject": failed_reject,
            },
            "agreement_accuracy": aligned / n,
            "agreement_clopper_pearson_reference_interval": [ci_low, ci_high],
            "reference_interval_scope": (
                "nominal 95% iid-binomial reference only; the fixed case set "
                "does not support design-based population coverage"
            ),
            "sensitivity_for_correct_candidates": sensitivity_correct,
            "specificity_for_failed_candidates": specificity_failure,
            "balanced_accuracy": balanced_accuracy,
            "mean_check_cost_usd": float(values["C_check_S"]),
            "mean_large_generation_cost_usd": float(values["C_rerun_L"]),
            "check_cost_as_pct_of_large_generation": (
                100 * float(values["C_check_S"]) / float(values["C_rerun_L"])
            ),
        }
    return output


def validate_real_runs(summary: dict, label: str) -> None:
    costs = [
        bucket["mean_cost_usd"] for arch in summary.values() for bucket in arch.values()
    ]
    models = {
        model
        for arch in summary.values()
        for bucket in arch.values()
        for model in bucket["models"]
    }
    if not costs or min(costs) <= 0 or not models:
        raise ValueError(f"{label} does not contain verifiable paid-model usage")


def threshold_identification(summary: dict) -> dict:
    differences = []
    for ctx in CONTEXTS:
        b2 = summary["B2_ClassicalMAS"][str(ctx)]
        b3 = summary["B3_HybridINoT"][str(ctx)]
        u2 = 1000 * b2["pass_at_1"] / b2["mean_tokens"]
        u3 = 1000 * b3["pass_at_1"] / b3["mean_tokens"]
        differences.append(u3 - u2)
    if all(value >= 0 for value in differences):
        return {
            "identified": False,
            "censoring": "unbracketed_left_boundary",
            "statement": (
                "no crossover is observed; a routing threshold is not "
                "identified by this grid"
            ),
            "reason": (
                "the always-internal B3 treatment weakly dominates B2 at "
                "every observed point, and behavior below the grid is unknown"
            ),
        }
    if all(value < 0 for value in differences):
        return {
            "identified": False,
            "censoring": "unbracketed_right_boundary",
            "statement": (
                "no crossover is observed; a routing threshold is not "
                "identified by this grid"
            ),
            "reason": (
                "the always-internal B3 treatment is below B2 at every "
                "observed point, and behavior above the grid is unknown"
            ),
        }
    for index in range(1, len(CONTEXTS)):
        if differences[index - 1] < 0 <= differences[index]:
            return {
                "identified": True,
                "censoring": None,
                "statement": (
                    "an observed-grid sign change lies between "
                    f"{CONTEXTS[index - 1]} and {CONTEXTS[index]} target tokens"
                ),
                "reason": (
                    "the observed U_tok difference changes sign; interpolation "
                    "or a routing threshold still requires a separate model"
                ),
            }
    return {
        "identified": False,
        "censoring": "non_monotone",
        "statement": "tau_star is not identifiable on the observed grid",
        "reason": "the observed U_tok difference is non-monotone",
    }


def derive_inference_cost_extrapolation(path: Path, scale: int = 10000) -> dict:
    rows = read_json(path)
    subsets = {
        arch: {
            (
                row["task_id"],
                row["seed"],
                int(row["extra"]["context_target_tokens"]),
            ): row
            for row in rows
            if row["architecture"] == arch
        }
        for arch in ARCHS
    }
    keys = sorted(set(subsets[ARCHS[0]]) & set(subsets[ARCHS[1]]))
    paired_rows = [
        {
            "task_id": str(key[0]).split("@ctx", 1)[0],
            "seed": key[1],
            "context": key[2],
            "cost_delta": (
                subsets[ARCHS[0]][key]["cost_usd"] - subsets[ARCHS[1]][key]["cost_usd"]
            ),
            "input_token_delta": (
                subsets[ARCHS[0]][key]["input_tokens"]
                - subsets[ARCHS[1]][key]["input_tokens"]
            ),
            "output_token_delta": (
                subsets[ARCHS[0]][key]["output_tokens"]
                - subsets[ARCHS[1]][key]["output_tokens"]
            ),
        }
        for key in keys
    ]
    by_task: defaultdict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in paired_rows:
        by_task[(row["task_id"], row["seed"])].append(row)
    for task_key, task_rows in by_task.items():
        contexts = {row["context"] for row in task_rows}
        if contexts != set(CONTEXTS):
            raise ValueError(
                f"cost extrapolation task {task_key} has contexts {contexts}"
            )
    task_cost_differences = np.array(
        [
            mean(row["cost_delta"] for row in task_rows)
            for task_rows in by_task.values()
        ],
        dtype=float,
    )
    task_input_differences = np.array(
        [
            mean(row["input_token_delta"] for row in task_rows)
            for task_rows in by_task.values()
        ],
        dtype=float,
    )
    task_output_differences = np.array(
        [
            mean(row["output_token_delta"] for row in task_rows)
            for task_rows in by_task.values()
        ],
        dtype=float,
    )
    rng = np.random.default_rng(12345)
    indices = rng.integers(
        0,
        len(task_cost_differences),
        size=(10000, len(task_cost_differences)),
    )
    bootstrap_monthly = task_cost_differences[indices].mean(axis=1) * scale
    ci_low, ci_high = np.quantile(bootstrap_monthly, [0.025, 0.975])
    monthly_delta = float(task_cost_differences.mean() * scale)
    leave_one_task_out = [
        float(np.delete(task_cost_differences, index).mean() * scale)
        for index in range(len(task_cost_differences))
    ]
    base_input_price = 2.0
    base_output_price = 12.0
    multipliers = (0.5, 0.75, 1.0, 1.25, 1.5)
    sensitivity = []
    for input_multiplier in multipliers:
        for output_multiplier in multipliers:
            monthly = (
                scale
                * (
                    base_input_price * input_multiplier * task_input_differences.mean()
                    + base_output_price
                    * output_multiplier
                    * task_output_differences.mean()
                )
                / 1_000_000
            )
            sensitivity.append(
                {
                    "input_price_multiplier": input_multiplier,
                    "output_price_multiplier": output_multiplier,
                    "savings_usd_per_10000_tasks": float(monthly),
                }
            )
    return {
        "method": "analytical extrapolation from paired real E3 API costs",
        "source": "tracked Gemini 3.1 Pro Preview HumanEval E3",
        "context_mix": {str(ctx): "equal weight (5 paired tasks)" for ctx in CONTEXTS},
        "n_paired_task_context_cases": len(keys),
        "n_unique_task_clusters": len(task_cost_differences),
        "extrapolate_to_tasks_per_month": scale,
        "delta_cost_per_task_b2_minus_b3_usd": float(task_cost_differences.mean()),
        "delta_monthly_b2_minus_b3_usd": monthly_delta,
        "task_cluster_resampling_stability_interval_usd": [
            float(ci_low),
            float(ci_high),
        ],
        "bootstrap_unit": (
            "HumanEval task; all four context cells retained within each "
            "resampled cluster"
        ),
        "leave_one_task_out_savings_usd": leave_one_task_out,
        "leave_one_task_out_range_usd": [
            float(min(leave_one_task_out)),
            float(max(leave_one_task_out)),
        ],
        "resampling_stability_interval_lower_positive": bool(ci_low > 0),
        "resampling_scope": (
            "2.5--97.5 percentile stability interval over the five fixed task "
            "clusters; it has no design-based population coverage target"
        ),
        "mean_input_token_delta_b2_minus_b3": float(task_input_differences.mean()),
        "mean_output_token_delta_b2_minus_b3": float(task_output_differences.mean()),
        "all_paired_input_token_deltas_positive": bool(
            all(row["input_token_delta"] > 0 for row in paired_rows)
        ),
        "all_paired_output_token_deltas_positive": bool(
            all(row["output_token_delta"] > 0 for row in paired_rows)
        ),
        "independent_input_output_price_sensitivity": {
            "base_prices_usd_per_million": {
                "input": base_input_price,
                "output": base_output_price,
            },
            "multipliers": list(multipliers),
            "grid": sensitivity,
            "minimum_savings_usd": float(
                min(row["savings_usd_per_10000_tasks"] for row in sensitivity)
            ),
            "maximum_savings_usd": float(
                max(row["savings_usd_per_10000_tasks"] for row in sensitivity)
            ),
        },
        "scope_note": (
            "API inference only and conditional on the five non-random pilot "
            "tasks with an equal context mixture; hardware, energy, storage, "
            "operations and population-level uncertainty were not measured"
        ),
    }


def plot_e3_replication(
    pro: dict, flash: dict, output: Path, language: str = "ru"
) -> None:
    labels = {
        "ru": {
            "x": "Длина контекста, токены",
            "y": "Средние токены на задачу (log)",
            "title": "Токенный расход B2 и B3 на HumanEval при росте контекста",
        },
        "en": {
            "x": "Target context length, tokens",
            "y": "Mean tokens per task (log)",
            "title": "B2 and B3 token use on HumanEval as context grows",
        },
    }[language]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), sharey=True)
    variants = [
        (
            f"Gemini 3.1 Pro Preview, n={pro['B2_ClassicalMAS']['256']['n']}",
            pro,
        ),
        (
            f"Gemini 3.1 Flash-Lite, n={flash['B2_ClassicalMAS']['256']['n']}, seed=42",
            flash,
        ),
    ]
    styles = {
        "B2_ClassicalMAS": {
            "color": "#263238",
            "marker": "s",
            "linestyle": "--",
            "label": "B2 Classical-MAS",
        },
        "B3_HybridINoT": {
            "color": "#3569a8",
            "marker": "o",
            "linestyle": "-",
            "label": "B3 Hybrid-INoT",
        },
    }
    for ax, (title, data) in zip(axes, variants):
        for arch in ARCHS:
            values = [data[arch][str(ctx)]["mean_tokens"] for ctx in CONTEXTS]
            ax.plot(CONTEXTS, values, linewidth=2, markersize=6, **styles[arch])
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks(CONTEXTS, ["256", "1k", "4k", "16k"])
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(labels["x"])
        ax.grid(True, which="major", color="#d7dde3", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel(labels["y"])
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.895),
    )
    fig.suptitle(
        labels["title"],
        y=0.985,
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.79))
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_context_scaling_slopes(
    pro: dict, flash: dict, output: Path, language: str = "ru"
) -> None:
    labels = {
        "ru": {
            "y": "OLS-наклон токенов по фактическому контексту",
            "title": "Линейная сводка расхода по четырём точкам",
            "note": "Среднее по задачам; 2.5–97.5% task-resampling",
        },
        "en": {
            "y": "OLS token slope over the four context cells",
            "title": "Four-point linear token-use summary",
            "note": "Task mean; 2.5–97.5% task-resampling range",
        },
    }[language]
    variants = (
        ("Gemini 3.1 Pro Preview", pro),
        ("Gemini 3.1 Flash-Lite", flash),
    )
    x = np.arange(len(variants), dtype=float)
    width = 0.34
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    for index, architecture in enumerate(ARCHS):
        means = [
            data["architectures"][architecture][
                "mean_gridwide_ols_slope_tokens_per_context_token"
            ]
            for _, data in variants
        ]
        intervals = [
            data["architectures"][architecture]["mean_task_resampling_interval"]
            for _, data in variants
        ]
        lower = [value - interval[0] for value, interval in zip(means, intervals)]
        upper = [interval[1] - value for value, interval in zip(means, intervals)]
        bars = ax.bar(
            x + (index - 0.5) * width,
            means,
            width,
            yerr=[lower, upper],
            capsize=4,
            color="#d9e2ec" if index == 0 else "#5f7f9f",
            edgecolor="#263238",
            hatch="//" if index == 0 else "..",
            label="B2 Classical-MAS" if index == 0 else "B3 Hybrid-INoT",
        )
        for bar, value in zip(bars, means):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.08,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
    ax.set_xticks(
        x,
        [
            f"{name}\n(n={data['architectures'][ARCHS[0]]['n_task_slopes']})"
            for name, data in variants
        ],
    )
    ax.set_ylim(0, 3.9)
    ax.set_ylabel(labels["y"])
    ax.set_title(labels["title"], pad=30)
    ax.text(
        0.5,
        1.01,
        labels["note"],
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#455a64",
    )
    ax.grid(axis="y", color="#d7dde3", linewidth=0.7)
    ax.legend(frameon=False, ncol=2, loc="upper center")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_e6_cost_ratio(
    comparisons: list[dict], output: Path, language: str = "ru"
) -> None:
    labels = {
        "ru": {
            "x": "Длина контекста, токены",
            "y": "Стоимость Flash-Lite / стоимость Pro, %",
            "title": "Относительная стоимость моделей в E6 (controlled, n=10)",
        },
        "en": {
            "x": "Target context length, tokens",
            "y": "Flash-Lite cost / Pro cost, %",
            "title": "Relative model cost in E6 (controlled, n=10)",
        },
    }[language]
    by_arch = {
        arch: sorted(
            [row for row in comparisons if row["architecture"] == arch],
            key=lambda row: row["context_length"],
        )
        for arch in ARCHS
    }
    e6_contexts = [row["context_length"] for row in by_arch["B2_ClassicalMAS"]]
    x = list(range(len(e6_contexts)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    bars = []
    for index, arch in enumerate(ARCHS):
        offset = (index - 0.5) * width
        values = [100 * row["cost_ratio_flash_over_pro"] for row in by_arch[arch]]
        group = ax.bar(
            [value + offset for value in x],
            values,
            width,
            color="#d9e2ec" if index == 0 else "#5f7f9f",
            edgecolor="#263238",
            hatch="//" if index == 0 else "..",
            label="B2 Classical-MAS" if index == 0 else "B3 Hybrid-INoT",
        )
        bars.extend(group)
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.25,
            f"{bar.get_height():.1f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_xticks(x, [str(value) for value in e6_contexts])
    ax.set_ylim(0, 12)
    ax.set_xlabel(labels["x"])
    ax.set_ylabel(labels["y"])
    ax.set_title(labels["title"], pad=30)
    ax.grid(axis="y", color="#d7dde3", linewidth=0.7)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_e5_sensitivity(summary: dict, output: Path, language: str = "ru") -> None:
    labels = {
        "ru": {
            "x": "Множитель цены выходных токенов",
            "y": "Множитель цены входных токенов",
            "title": "Экономия B3, USD на 10 000 задач",
            "note": "Независимое изменение цен; базовый тариф выделен рамкой",
        },
        "en": {
            "x": "Output-token price multiplier",
            "y": "Input-token price multiplier",
            "title": "B3 savings, USD per 10,000 tasks",
            "note": "Prices varied independently; base tariff is outlined",
        },
    }[language]
    sensitivity = summary["independent_input_output_price_sensitivity"]
    multipliers = sensitivity["multipliers"]
    grid_lookup = {
        (
            row["input_price_multiplier"],
            row["output_price_multiplier"],
        ): row["savings_usd_per_10000_tasks"]
        for row in sensitivity["grid"]
    }
    matrix = np.array(
        [
            [grid_lookup[(input_value, output_value)] for output_value in multipliers]
            for input_value in multipliers
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    image = ax.imshow(matrix, cmap="Blues", origin="lower", aspect="auto")
    for row_index, input_value in enumerate(multipliers):
        for column_index, output_value in enumerate(multipliers):
            value = matrix[row_index, column_index]
            normalized = (value - matrix.min()) / (matrix.max() - matrix.min())
            ax.text(
                column_index,
                row_index,
                f"${value:,.0f}",
                ha="center",
                va="center",
                color="white" if normalized > 0.58 else "#263238",
                fontsize=8,
                fontweight="bold" if input_value == output_value == 1.0 else "normal",
            )
    base_index = multipliers.index(1.0)
    ax.add_patch(
        plt.Rectangle(
            (base_index - 0.5, base_index - 0.5),
            1,
            1,
            fill=False,
            edgecolor="#263238",
            linewidth=2.2,
        )
    )
    ax.set_xticks(range(len(multipliers)), [f"{value:.2f}x" for value in multipliers])
    ax.set_yticks(range(len(multipliers)), [f"{value:.2f}x" for value in multipliers])
    ax.set_xlabel(labels["x"])
    ax.set_ylabel(labels["y"])
    ax.set_title(labels["title"], pad=30)
    ax.text(
        0.5,
        1.01,
        labels["note"],
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#455a64",
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("USD")
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--new-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    commit = git_commit(args.research_root)
    if commit != EXPECTED_COMMIT:
        raise ValueError(f"expected research commit {EXPECTED_COMMIT}, got {commit}")

    flash_e3_paths = sorted(args.new_results.glob("e3*/runs.json"))
    if not flash_e3_paths:
        raise FileNotFoundError(f"no E3 runs below {args.new_results}")
    sources = {
        "pro_e3_runs": args.research_root / "results/slide_e2e3_real/e3/runs.json",
        "e2_stats": args.research_root
        / "results/slide_e2e3_real/slide_e2_e3_stats.json",
        "e2_pairwise": args.research_root
        / "results/slide_e2e3_real/e2/e2a/pairwise_vs_full.json",
        "e2_full_summary": args.research_root
        / "results/slide_e2e3_real/e2/summary.json",
        "e6_summary": args.research_root / "results/e6/summary.json",
        "e6_comparisons": args.research_root / "results/e6/flash_vs_pro.json",
        "e6_runs": args.research_root / "results/e6/runs.json",
        "e4_summary": args.new_results / "e4/summary.json",
    }
    for path in flash_e3_paths:
        sources[f"flash_e3_runs_{path.parent.name}"] = path
    missing = [str(path) for path in sources.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("missing evidence files:\n" + "\n".join(missing))

    pro_e3 = summarize_e3(sources["pro_e3_runs"])
    flash_e3 = summarize_e3(flash_e3_paths)
    pro_e3_quality = validate_e3_rows(
        sources["pro_e3_runs"],
        expected_n=5,
        label="tracked Pro HumanEval E3",
    )
    flash_e3_quality = validate_e3_rows(
        flash_e3_paths,
        expected_n=20,
        label="Flash-Lite HumanEval E3 replication",
    )
    pro_slopes = context_scaling_slopes(
        sources["pro_e3_runs"],
        research_root=args.research_root,
        n_tasks=5,
        label="tracked Pro HumanEval E3",
    )
    flash_slopes = context_scaling_slopes(
        flash_e3_paths,
        research_root=args.research_root,
        n_tasks=20,
        label="Flash-Lite HumanEval E3 replication",
    )
    e6_runs = read_json(sources["e6_runs"])
    e6_controlled_task_ids = sorted(
        {
            row["task_id"].split("@ctx", 1)[0]
            for row in e6_runs
            if row.get("extra", {}).get("suite_label") == "controlled"
        }
    )
    e6_families = sorted(
        {task_id.split("/", 2)[1] for task_id in e6_controlled_task_ids}
    )
    e2_stats = read_json(sources["e2_stats"])
    e2_full_summary = read_json(sources["e2_full_summary"])
    e4_original = read_json(sources["e4_summary"])
    excluded_legacy_claims = [
        {
            "source": "tracked_e2_stats.e3_tau_star",
            "source_value": e2_stats.pop("e3_tau_star", None),
            "canonical_status": "not identified; no crossover is bracketed",
        },
        {
            "source": (
                "tracked_e2_full_summary.e2c."
                "h3_supported_parallel_tools_hurt_serial_hybrid"
            ),
            "source_value": e2_full_summary.get("e2c", {}).pop(
                "h3_supported_parallel_tools_hurt_serial_hybrid", None
            ),
            "canonical_status": (
                "not supported; deterministic tool timing is not a direct "
                "architecture-level test"
            ),
        },
    ]
    for dataset, values in e4_original.items():
        excluded_legacy_claims.append(
            {
                "source": (
                    f"new_e4_legacy_aggregate_inputs.{dataset}."
                    "h2_confirmed_lower_ci_gt_0"
                ),
                "source_value": values.pop("h2_confirmed_lower_ci_gt_0", None),
                "canonical_status": (
                    "not evaluated; aggregate screening counts do not identify "
                    "an integrated rerun-policy effect"
                ),
            }
        )
    validate_real_runs(pro_e3, "tracked Pro E3")
    validate_real_runs(flash_e3, "Flash-Lite replication E3")
    article_root = args.output_root.resolve().parent
    manuscript_sources = {
        name: {
            "path": f"article-INoT/{path.name}",
            "sha256": sha256(path),
        }
        for name, path in {
            "english_tex": article_root / "converted_article_springer.tex",
            "russian_tex": article_root / "converted_article_springer_ru.tex",
        }.items()
        if path.exists()
    }

    evidence = {
        "research_repository": "https://github.com/daniil-novel/INoT_Research",
        "research_commit": commit,
        "article_evidence_date": "2026-07-26",
        "analysis_revision_date": "2026-07-28",
        "analysis_code": {
            "path": "article-INoT/reproducibility/build_article_evidence.py",
            "sha256": sha256(Path(__file__)),
        },
        "manuscript_sources": manuscript_sources,
        "canonical_claim_status": {
            "resource_efficiency": (
                "observed descriptively for the fixed E3 task sets; conditional "
                "rank-based sensitivity analyses are reported"
            ),
            "quality_noninferiority_2pp": "not established",
            "h2_rerun_policy": "not evaluated",
            "h3_parallel_tool_penalty": "not supported",
            "tau_star_and_router": "not identified or evaluated",
        },
        "excluded_legacy_claims": excluded_legacy_claims,
        "recomputation_scope": {
            "recomputed_from_run_rows": [
                "Pro and Flash-Lite E3 aggregates and paired statistics",
                "data-quality checks and context-length profiles",
                "four-point OLS slope diagnostics",
                "E5 API-inference extrapolation and price sensitivity",
            ],
            "derived_from_aggregate_only_input": [
                "E4 screening confusion tables",
            ],
            "imported_precomputed_with_hash_but_not_recomputed": [
                "E2 aggregate and pairwise summaries",
                "E6 aggregate and comparison summaries",
            ],
            "not_independently_reverified": [
                "pass/fail labels because complete generated answers are absent",
                "original external verification executions",
            ],
        },
        "primary_estimand": {
            "treatment": (
                "end-to-end always-internal B3 bundle: one combined "
                "planner-worker-critic call, deterministic proxy compression "
                "above 4096 tokens, and external verification"
            ),
            "comparator": (
                "B2 Classical-MAS with separate planner, worker and critic "
                "calls over the uncompressed shared context"
            ),
            "scope": (
                "system-level package effect; orchestration and compression "
                "effects are not separately identified"
            ),
            "router_evaluated": False,
        },
        "input_files": {
            name: {
                "path": portable_source_path(
                    path,
                    research_root=args.research_root,
                    article_root=args.output_root.resolve().parent,
                ),
                "sha256": sha256(path),
            }
            for name, path in sources.items()
        },
        "e3_data_quality": {
            "tracked_pro": pro_e3_quality,
            "flash_lite_replication": flash_e3_quality,
        },
        "tracked_pro_humaneval_e3": pro_e3,
        "tracked_pro_humaneval_e3_pairwise": paired_e3_statistics(
            sources["pro_e3_runs"]
        ),
        "tracked_pro_context_scaling_slopes": pro_slopes,
        "tracked_pro_tau_star_interpretation": threshold_identification(pro_e3),
        "flash_lite_humaneval_e3_replication": flash_e3,
        "flash_lite_humaneval_e3_pairwise": paired_e3_statistics(flash_e3_paths),
        "flash_lite_context_scaling_slopes": flash_slopes,
        "flash_lite_quality_noninferiority_bound": (
            exact_zero_harm_noninferiority_bound(n_pairs=20)
        ),
        "flash_lite_tau_star_interpretation": threshold_identification(flash_e3),
        "humaneval_input_profile": humaneval_input_profile(args.research_root),
        "tracked_e2_stats": e2_stats,
        "tracked_e2_pairwise": read_json(sources["e2_pairwise"]),
        "tracked_e2_full_summary": e2_full_summary,
        "tracked_e6_summary": read_json(sources["e6_summary"]),
        "tracked_e6_comparisons": read_json(sources["e6_comparisons"]),
        "tracked_e6_task_profile": {
            "suite": "controlled",
            "n_unique_base_cases": len(e6_controlled_task_ids),
            "families": e6_families,
            "base_task_ids": e6_controlled_task_ids,
        },
        "new_e4_legacy_aggregate_inputs": e4_original,
        "new_e4_screening_diagnostic": derive_e4_screening_diagnostic(
            read_json(sources["e4_summary"])
        ),
        "inference_cost_extrapolation_from_tracked_e3": (
            derive_inference_cost_extrapolation(sources["pro_e3_runs"])
        ),
        "run_failures": [
            {
                "experiment": "E3 seed 123",
                "status": "excluded",
                "reason": (
                    "OpenRouter total key limit was reached before the final "
                    "context bucket and before runs.json was persisted"
                ),
            },
            {
                "experiment": "E5",
                "status": "excluded",
                "reason": (
                    "OpenRouter total key limit was reached before a complete "
                    "paired B2/B3 result set was persisted"
                ),
            },
        ],
    }
    evidence["quality_checks"] = {
        "pro_e3_models": sorted(
            {
                model
                for arch in pro_e3.values()
                for bucket in arch.values()
                for model in bucket["models"]
            }
        ),
        "flash_e3_models": sorted(
            {
                model
                for arch in flash_e3.values()
                for bucket in arch.values()
                for model in bucket["models"]
            }
        ),
        "pro_e3_bucket_sizes": dict(
            Counter(bucket["n"] for arch in pro_e3.values() for bucket in arch.values())
        ),
        "flash_e3_bucket_sizes": dict(
            Counter(
                bucket["n"] for arch in flash_e3.values() for bucket in arch.values()
            )
        ),
        "input_paths_are_portable": all(
            not Path(value["path"]).is_absolute()
            for value in evidence["input_files"].values()
        ),
        "primary_e3_grids_complete": (
            pro_e3_quality["status"] == "pass" and flash_e3_quality["status"] == "pass"
        ),
        "e4_policy_effect_reproducible": False,
        "complete_generated_answers_present": False,
        "pass_labels_independently_reverified": False,
    }

    args.output_root.mkdir(parents=True, exist_ok=True)
    figures = args.output_root.parent / "figures" / "generated"
    figures.mkdir(parents=True, exist_ok=True)
    (args.output_root / "evidence_snapshot.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    plot_e3_replication(pro_e3, flash_e3, figures / "e3_humaneval_replication.png")
    plot_e3_replication(
        pro_e3,
        flash_e3,
        figures / "e3_humaneval_replication_en.png",
        language="en",
    )
    plot_context_scaling_slopes(
        pro_slopes,
        flash_slopes,
        figures / "e3_context_scaling_slope.png",
    )
    plot_context_scaling_slopes(
        pro_slopes,
        flash_slopes,
        figures / "e3_context_scaling_slope_en.png",
        language="en",
    )
    plot_e6_cost_ratio(
        evidence["tracked_e6_comparisons"],
        figures / "e6_model_cost_ratio.png",
    )
    plot_e6_cost_ratio(
        evidence["tracked_e6_comparisons"],
        figures / "e6_model_cost_ratio_en.png",
        language="en",
    )
    plot_e5_sensitivity(
        evidence["inference_cost_extrapolation_from_tracked_e3"],
        figures / "e5_inference_cost_sensitivity.png",
    )
    plot_e5_sensitivity(
        evidence["inference_cost_extrapolation_from_tracked_e3"],
        figures / "e5_inference_cost_sensitivity_en.png",
        language="en",
    )


if __name__ == "__main__":
    main()
