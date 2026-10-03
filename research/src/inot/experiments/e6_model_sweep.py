"""E6 — сравнение дорогой и дешёвой модели внутри B2 и B3.

Задача эксперимента: понять, насколько `google/gemini-3.1-flash-lite`
хуже/лучше `google/gemini-3.1-pro-preview` в двух архитектурах:

* B2 Classical-MAS — традиционная мультиагентная схема;
* B3 Hybrid-INoT — внутренний ролевой цикл в одном LLM-вызове.

Документация и выводы формируются на русском, а подписи графиков оставлены
на английском для удобной вставки в статью.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from rich.console import Console

from ..architectures import make
from ..config import Config
from ..llm import make_client
from ..metrics import holm_bonferroni, pairwise_compare, summarize_runs
from ..runner import align_pairs, run_grid, save_results, summary_table
from ..tasks import build_controlled_context_suite, load_humaneval
from ..types import RunResult

console = Console()


def run(
    cfg: Config,
    *,
    n: int = 20,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e6"),
    dry_run: bool = False,
    suite: str = "controlled",
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    context_lengths = list(cfg.get("experiments.e6_context_lengths", [512, 2048, 8192]))
    model_specs = {
        "pro": cfg.get("experiments.e6_pro_model", cfg.large_model),
        "flash_lite": cfg.get("experiments.e6_flash_lite_model", cfg.small_model),
    }
    suite_labels = _suite_labels(suite)

    all_results: list[RunResult] = []
    # Важно: один OpenRouterClient на весь эксперимент, чтобы budget cap считал
    # суммарные траты, а не обнулялся для каждой модели.
    llm = make_client(cfg, dry_run=dry_run)
    try:
        for suite_label in suite_labels:
            for ctx_len in context_lengths:
                tasks = _load_suite(suite_label, n=n, context_target_tokens=ctx_len)
                for model_tier, model_id in model_specs.items():
                    tier_cfg = _config_with_large_model(cfg, model_id)
                    agents = {
                        "B2_ClassicalMAS": make("B2", llm=llm, config=tier_cfg),
                        "B3_HybridINoT": make("B3", llm=llm, config=tier_cfg),
                    }
                    console.rule(
                        f"[bold]E6 :: {suite_label} :: {model_tier} :: контекст = {ctx_len} токенов[/bold]"
                    )
                    rows = run_grid(
                        agents,
                        tasks,
                        seeds=seeds,
                        progress_label=f"E6 {suite_label} {model_tier} ctx={ctx_len}",
                    )
                    for r in rows:
                        r.extra["suite_label"] = suite_label
                        r.extra["context_target_tokens"] = ctx_len
                        r.extra["model_tier"] = model_tier
                        r.extra["model_id"] = model_id
                    all_results.extend(rows)
                    console.log(f"Суммарные траты: ${llm.spent_usd:.4f}")
    finally:
        llm.close()

    save_results(all_results, out_dir / "runs.json")

    summaries = _summaries(all_results, context_lengths, suite_labels, model_specs)
    (out_dir / "summary.json").write_text(
        json.dumps({f"{k[0]}::{k[1]}::{k[2]}@ctx{k[3]}": v for k, v in summaries.items()},
                   indent=2, default=str),
        encoding="utf-8",
    )

    comparisons = _compare_flash_vs_pro(
        all_results,
        context_lengths=context_lengths,
        suite_labels=suite_labels,
        bootstrap_resamples=cfg.get("statistics.bootstrap_resamples", 10000),
        alpha=cfg.get("statistics.alpha", 0.05),
    )
    (out_dir / "flash_vs_pro.json").write_text(json.dumps(comparisons, indent=2), encoding="utf-8")

    verdict_md = _verdict_markdown(comparisons)
    (out_dir / "E6_VERDICT.md").write_text(verdict_md, encoding="utf-8")
    console.print(verdict_md)

    flat = []
    from ..metrics import Summary
    for (suite_label, model_tier, arch, ctx), s_dict in summaries.items():
        s = Summary(**s_dict)
        s.architecture = f"{suite_label}:{model_tier}:{arch}@ctx{ctx}"
        flat.append(s)
    table = summary_table(flat, title="E6 — сравнение Gemini Pro и Flash-Lite")
    console.print(table)
    with (out_dir / "table.txt").open("w", encoding="utf-8") as f:
        from rich.console import Console as _C
        _C(file=f, force_terminal=False, width=180).print(table)

    _plot_metric(
        summaries,
        metric="pass_at_1",
        ylabel="pass@1 (%)",
        title="E6 — pass@1 degradation: Flash-Lite vs Pro",
        out=out_dir / "fig_pass_at_1_flash_vs_pro.png",
        value_scale=100.0,
    )
    _plot_metric(
        summaries,
        metric="mean_cost_usd",
        ylabel="USD / task",
        title="E6 — Cost: Flash-Lite vs Pro",
        out=out_dir / "fig_cost_usd_flash_vs_pro.png",
    )
    _plot_metric(
        summaries,
        metric="utok_per_kilo",
        ylabel="U_tok",
        title="E6 — Token efficiency: Flash-Lite vs Pro",
        out=out_dir / "fig_utok_flash_vs_pro.png",
    )
    _plot_degradation(
        comparisons,
        metric="pass_at_1_delta_pp",
        ylabel="Flash-Lite - Pro pass@1 (p.p.)",
        title="E6 — Quality degradation by architecture",
        out=out_dir / "fig_quality_degradation_pp.png",
    )

    return {"summaries": summaries, "comparisons": comparisons}


def _config_with_large_model(cfg: Config, model_id: str) -> Config:
    raw = copy.deepcopy(cfg.raw)
    raw.setdefault("llm", {})["large_model"] = model_id
    return Config(raw)


def _summaries(all_results, context_lengths, suite_labels, model_specs):
    summaries: dict[tuple[str, str, str, int], dict] = {}
    for suite_label in suite_labels:
        for model_tier in model_specs:
            for arch in ("B2_ClassicalMAS", "B3_HybridINoT"):
                for ctx in context_lengths:
                    subset = [
                        r for r in all_results
                        if r.extra.get("suite_label") == suite_label
                        and r.extra.get("model_tier") == model_tier
                        and r.architecture == arch
                        and r.extra.get("context_target_tokens") == ctx
                    ]
                    summaries[(suite_label, model_tier, arch, ctx)] = summarize_runs(subset).__dict__
    return summaries


def _compare_flash_vs_pro(
    all_results: list[RunResult],
    *,
    context_lengths: list[int],
    suite_labels: list[str],
    bootstrap_resamples: int,
    alpha: float,
) -> list[dict]:
    comparisons: list[dict] = []
    pvals: list[float] = []

    def per_task_utok(r: RunResult) -> float:
        return (1000.0 / r.total_tokens) if (r.passed and r.total_tokens > 0) else 0.0

    for suite_label in suite_labels:
        for arch in ("B2_ClassicalMAS", "B3_HybridINoT"):
            for ctx in context_lengths:
                pro = _subset(all_results, suite_label, "pro", arch, ctx)
                flash = _subset(all_results, suite_label, "flash_lite", arch, ctx)
                pro_utok, flash_utok = align_pairs(pro, flash, metric_a=per_task_utok, metric_b=per_task_utok)
                cmp = pairwise_compare(
                    flash_utok,
                    pro_utok,
                    label=f"U_tok Flash-Lite - Pro :: {suite_label}::{arch}@ctx{ctx}",
                    bootstrap_resamples=bootstrap_resamples,
                )
                pro_pass = np.mean([1.0 if r.passed else 0.0 for r in pro]) if pro else 0.0
                flash_pass = np.mean([1.0 if r.passed else 0.0 for r in flash]) if flash else 0.0
                pro_cost = np.mean([r.total_cost_usd for r in pro]) if pro else 0.0
                flash_cost = np.mean([r.total_cost_usd for r in flash]) if flash else 0.0
                item = {
                    "suite": suite_label,
                    "architecture": arch,
                    "context_length": ctx,
                    "n_pairs": cmp.n,
                    "pass_at_1_pro": float(pro_pass),
                    "pass_at_1_flash_lite": float(flash_pass),
                    "pass_at_1_delta_pp": float((flash_pass - pro_pass) * 100.0),
                    "mean_cost_usd_pro": float(pro_cost),
                    "mean_cost_usd_flash_lite": float(flash_cost),
                    "cost_ratio_flash_over_pro": float(flash_cost / pro_cost) if pro_cost else 0.0,
                    "utok_diff_mean_flash_minus_pro": cmp.diff_mean,
                    "utok_ci_low": cmp.bootstrap_ci_low,
                    "utok_ci_high": cmp.bootstrap_ci_high,
                    "wilcoxon_p_utok": cmp.p_value,
                }
                comparisons.append(item)
                pvals.append(cmp.p_value)
    rejected = holm_bonferroni(pvals, alpha=alpha)
    for item, reject in zip(comparisons, rejected):
        item["holm_bonferroni_rejected"] = bool(reject)
    return comparisons


def _subset(results, suite_label, model_tier, arch, ctx):
    return [
        r for r in results
        if r.extra.get("suite_label") == suite_label
        and r.extra.get("model_tier") == model_tier
        and r.architecture == arch
        and r.extra.get("context_target_tokens") == ctx
    ]


def _verdict_markdown(comparisons: list[dict]) -> str:
    lines = ["# Вывод E6: Gemini Pro vs Flash-Lite\n"]
    for arch in ("B2_ClassicalMAS", "B3_HybridINoT"):
        rows = [r for r in comparisons if r["architecture"] == arch]
        if not rows:
            continue
        mean_delta = float(np.mean([r["pass_at_1_delta_pp"] for r in rows]))
        mean_cost_ratio = float(np.mean([r["cost_ratio_flash_over_pro"] for r in rows]))
        lines.append(f"## {arch}\n")
        lines.append(f"- среднее изменение pass@1 Flash-Lite относительно Pro: **{mean_delta:+.2f} п.п.**")
        lines.append(f"- средняя доля стоимости Flash-Lite от Pro: **{mean_cost_ratio*100:.2f}%**")
        lines.append("- детализация по контекстам хранится в `flash_vs_pro.json`.\n")
    return "\n".join(lines)


def _plot_metric(summaries, *, metric: str, ylabel: str, title: str, out: Path, value_scale: float = 1.0) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    series = sorted({(k[0], k[1], k[2]) for k in summaries})
    ctxs = sorted({k[3] for k in summaries})
    for suite_label, model_tier, arch in series:
        ys = [summaries[(suite_label, model_tier, arch, ctx)][metric] * value_scale for ctx in ctxs]
        ax.plot(ctxs, ys, marker="o", label=f"{suite_label}:{model_tier}:{arch.split('_', 1)[-1]}")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Context length |C0| (tokens)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_degradation(comparisons, *, metric: str, ylabel: str, title: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    rows = sorted(comparisons, key=lambda r: (r["suite"], r["architecture"], r["context_length"]))
    labels = [f"{r['suite']}:{r['architecture'].split('_', 1)[-1]}:{r['context_length']}" for r in rows]
    vals = [r[metric] for r in rows]
    ax.bar(range(len(rows)), vals, color=["#4477aa" if "B2" in r["architecture"] else "#44aa77" for r in rows])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _suite_labels(suite: str) -> list[str]:
    if suite == "both":
        return ["humaneval", "controlled"]
    if suite in {"humaneval", "controlled"}:
        return [suite]
    raise ValueError("suite должен быть одним из: humaneval, controlled, both")


def _load_suite(suite: str, *, n: int, context_target_tokens: int):
    if suite == "humaneval":
        return load_humaneval(n=n, context_target_tokens=context_target_tokens, seed=42)
    if suite == "controlled":
        return build_controlled_context_suite(n=n, context_target_tokens=context_target_tokens, seed=42)
    raise ValueError(f"неизвестный suite: {suite}")
