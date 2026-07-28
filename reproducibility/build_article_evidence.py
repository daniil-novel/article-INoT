from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
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


def read_e3_rows(paths: Path | list[Path]) -> list[dict]:
    selected = [paths] if isinstance(paths, Path) else paths
    return [row for path in selected for row in read_json(path)]


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
        b3["delta_pass_at_1_pp_vs_b2"] = 100 * (
            b3["pass_at_1"] - b2["pass_at_1"]
        )
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
        rng = np.random.default_rng(12345)
        sample_indices = rng.integers(0, len(keys), size=(10000, len(keys)))
        relative_gains = []
        for indices in sample_indices:
            sample_b2 = [b2[index] for index in indices]
            sample_b3 = [b3[index] for index in indices]
            q2 = mean(float(row["passed"]) for row in sample_b2)
            q3 = mean(float(row["passed"]) for row in sample_b3)
            u2 = 1000 * q2 / mean(row["total_tokens"] for row in sample_b2)
            u3 = 1000 * q3 / mean(row["total_tokens"] for row in sample_b3)
            relative_gains.append(100 * (u3 - u2) / u2 if u2 else np.nan)
        finite_gains = np.asarray(relative_gains, dtype=float)
        finite_gains = finite_gains[np.isfinite(finite_gains)]
        ci_low, ci_high = np.quantile(finite_gains, [0.025, 0.975])
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
                "relative_utok_gain_b3_vs_b2_pct": 100
                * (
                    mean(per_task_u3) - mean(per_task_u2)
                )
                / mean(per_task_u2),
                "relative_utok_gain_bootstrap_ci_pct": [
                    float(ci_low),
                    float(ci_high),
                ],
                "wilcoxon_p_utok": wilcoxon_p,
                "mcnemar_exact_p": mcnemar_p,
                "discordant_b2_only": b2_only,
                "discordant_b3_only": b3_only,
            }
        )
    p_values = [row["wilcoxon_p_utok"] for row in comparisons]
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    rejected = [False] * len(p_values)
    for rank, index in enumerate(order):
        if p_values[index] <= 0.05 / (len(p_values) - rank):
            rejected[index] = True
        else:
            break
    for row, decision in zip(comparisons, rejected):
        row["holm_bonferroni_rejected"] = decision
    return comparisons


def humaneval_input_profile(research_root: Path) -> dict:
    sys.path.insert(0, str(research_root / "src"))
    from inot.tasks import load_humaneval

    profile = {}
    for n in (5, 20):
        profile[str(n)] = {}
        tasks_by_context = {}
        for ctx in (256, 512, 1024, 2048, 4096, 8192, 16384):
            tasks = load_humaneval(
                n=n, context_target_tokens=ctx, seed=42
            )
            actual = [
                int(task.metadata["context_actual_tokens"]) for task in tasks
            ]
            tasks_by_context[str(ctx)] = {
                "task_ids": [task.metadata["original_id"] for task in tasks],
                "actual_context_tokens_min": min(actual),
                "actual_context_tokens_mean": mean(actual),
                "actual_context_tokens_max": max(actual),
            }
        profile[str(n)] = tasks_by_context
    return profile


def validate_real_runs(summary: dict, label: str) -> None:
    costs = [
        bucket["mean_cost_usd"]
        for arch in summary.values()
        for bucket in arch.values()
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
            "censoring": "left",
            "statement": f"tau_star <= {CONTEXTS[0]} target context tokens",
            "reason": "B3 weakly dominates B2 at every observed grid point",
        }
    if all(value < 0 for value in differences):
        return {
            "identified": False,
            "censoring": "right",
            "statement": f"tau_star > {CONTEXTS[-1]} target context tokens",
            "reason": "B3 is below B2 at every observed grid point",
        }
    for index in range(1, len(CONTEXTS)):
        if differences[index - 1] < 0 <= differences[index]:
            return {
                "identified": True,
                "censoring": None,
                "statement": (
                    f"{CONTEXTS[index - 1]} < tau_star <= {CONTEXTS[index]}"
                ),
                "reason": "the observed U_tok difference changes sign",
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
    differences = np.array(
        [
            subsets[ARCHS[0]][key]["cost_usd"]
            - subsets[ARCHS[1]][key]["cost_usd"]
            for key in keys
        ],
        dtype=float,
    )
    rng = np.random.default_rng(12345)
    indices = rng.integers(0, len(differences), size=(10000, len(differences)))
    bootstrap_monthly = differences[indices].mean(axis=1) * scale
    ci_low, ci_high = np.quantile(bootstrap_monthly, [0.025, 0.975])
    monthly_delta = float(differences.mean() * scale)
    sensitivity = [
        {
            "price_jitter": jitter,
            "monthly_delta_usd": monthly_delta * (1 + jitter),
        }
        for jitter in (-0.5, -0.25, 0.0, 0.25, 0.5)
    ]
    return {
        "method": "analytical extrapolation from paired real E3 API costs",
        "source": "tracked Gemini 3.1 Pro Preview HumanEval E3",
        "context_mix": {
            str(ctx): "equal weight (5 paired tasks)" for ctx in CONTEXTS
        },
        "n_paired_task_context_cases": len(keys),
        "extrapolate_to_tasks_per_month": scale,
        "delta_cost_per_task_b2_minus_b3_usd": float(differences.mean()),
        "delta_monthly_b2_minus_b3_usd": monthly_delta,
        "monthly_delta_bootstrap_ci_usd": [
            float(ci_low),
            float(ci_high),
        ],
        "inference_savings_positive_at_lower_ci": bool(ci_low > 0),
        "price_sensitivity": sensitivity,
        "scope_note": (
            "API inference only; hardware, energy, storage and operations "
            "costs were not measured"
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
            "Gemini 3.1 Pro Preview, "
            f"n={pro['B2_ClassicalMAS']['256']['n']}",
            pro,
        ),
        (
            "Gemini 3.1 Flash-Lite, "
            f"n={flash['B2_ClassicalMAS']['256']['n']}, seed=42",
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
    e6_contexts = [
        row["context_length"] for row in by_arch["B2_ClassicalMAS"]
    ]
    x = list(range(len(e6_contexts)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    bars = []
    for index, arch in enumerate(ARCHS):
        offset = (index - 0.5) * width
        values = [
            100 * row["cost_ratio_flash_over_pro"] for row in by_arch[arch]
        ]
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
    ax.set_title(labels["title"])
    ax.grid(axis="y", color="#d7dde3", linewidth=0.7)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_e5_sensitivity(
    summary: dict, output: Path, language: str = "ru"
) -> None:
    labels = {
        "ru": {
            "x": "Изменение цены токенов, %",
            "y": "Экономия B3 относительно B2, USD/10 000 задач",
            "title": "Чувствительность месячной стоимости инференса",
        },
        "en": {
            "x": "Token-price change, %",
            "y": "B3 savings versus B2, USD/10,000 tasks",
            "title": "Sensitivity of monthly inference cost",
        },
    }[language]
    rows = summary["price_sensitivity"]
    x = [100 * row["price_jitter"] for row in rows]
    y = [row["monthly_delta_usd"] for row in rows]
    ci_low, ci_high = summary["monthly_delta_bootstrap_ci_usd"]
    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    ax.plot(
        x,
        y,
        color="#3569a8",
        marker="o",
        markerfacecolor="white",
        linewidth=2,
    )
    ax.axhline(0, color="#263238", linewidth=1)
    ax.fill_between(
        x,
        [ci_low * (1 + value / 100) for value in x],
        [ci_high * (1 + value / 100) for value in x],
        color="#cfd8dc",
        alpha=0.65,
        label="95% bootstrap CI",
    )
    for xv, yv in zip(x, y):
        ax.text(xv, yv, f"${yv:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xlabel(labels["x"])
    ax.set_ylabel(labels["y"])
    ax.set_title(labels["title"])
    ax.grid(True, color="#d7dde3", linewidth=0.7)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
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
        "pro_e3_runs": args.research_root
        / "results/slide_e2e3_real/e3/runs.json",
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
    validate_real_runs(pro_e3, "tracked Pro E3")
    validate_real_runs(flash_e3, "Flash-Lite replication E3")

    evidence = {
        "research_repository": "https://github.com/daniil-novel/INoT_Research",
        "research_commit": commit,
        "article_evidence_date": "2026-07-26",
        "input_files": {
            name: {
                "path": str(path),
                "sha256": sha256(path),
            }
            for name, path in sources.items()
        },
        "tracked_pro_humaneval_e3": pro_e3,
        "tracked_pro_humaneval_e3_pairwise": paired_e3_statistics(
            sources["pro_e3_runs"]
        ),
        "tracked_pro_tau_star_interpretation": threshold_identification(pro_e3),
        "flash_lite_humaneval_e3_replication": flash_e3,
        "flash_lite_humaneval_e3_pairwise": paired_e3_statistics(
            flash_e3_paths
        ),
        "flash_lite_tau_star_interpretation": threshold_identification(flash_e3),
        "humaneval_input_profile": humaneval_input_profile(args.research_root),
        "tracked_e2_stats": read_json(sources["e2_stats"]),
        "tracked_e2_pairwise": read_json(sources["e2_pairwise"]),
        "tracked_e2_full_summary": read_json(sources["e2_full_summary"]),
        "tracked_e6_summary": read_json(sources["e6_summary"]),
        "tracked_e6_comparisons": read_json(sources["e6_comparisons"]),
        "tracked_e6_task_profile": {
            "suite": "controlled",
            "n_unique_base_cases": len(e6_controlled_task_ids),
            "families": e6_families,
            "base_task_ids": e6_controlled_task_ids,
        },
        "new_e4": read_json(sources["e4_summary"]),
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
            Counter(
                bucket["n"] for arch in pro_e3.values() for bucket in arch.values()
            )
        ),
        "flash_e3_bucket_sizes": dict(
            Counter(
                bucket["n"]
                for arch in flash_e3.values()
                for bucket in arch.values()
            )
        ),
    }

    args.output_root.mkdir(parents=True, exist_ok=True)
    figures = args.output_root.parent / "figures" / "generated"
    figures.mkdir(parents=True, exist_ok=True)
    (args.output_root / "evidence_snapshot.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plot_e3_replication(
        pro_e3, flash_e3, figures / "e3_humaneval_replication.png"
    )
    plot_e3_replication(
        pro_e3,
        flash_e3,
        figures / "e3_humaneval_replication_en.png",
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
