"""E1 — проверка H1 на HumanEval и controlled-context наборе.

Проверяет гипотезу H1:
    существует пороговая длина контекста τ⋆, после которой Hybrid-INoT
    даёт прирост U_tok не менее 15% относительно Classical-MAS, а pass@1
    не ухудшается более чем на 2 процентных пункта.

Сравниваемые конфигурации:
    CTRL NoAssistant | B0 SingleLarge | B1 SelfRefine | B2 ClassicalMAS | B3 HybridINoT

Каждая задача запускается на длинах контекста {512, 2048, 8192} и на выбранных
seed-ах. Параметр ``suite='both'`` включает одновременно HumanEval и
controlled-context benchmark из курсовой.

Статистика:
    * парный критерий Вилкоксона по per-task U_tok;
    * bootstrap CI 95% для ΔU_tok;
    * Holm-Bonferroni для множественных сравнений;
    * McNemar по парным pass/fail векторам B3 и B2.

Графики подписываются на английском, чтобы их можно было напрямую вставлять в
англоязычные материалы. Документы и текстовые выводы формируются на русском.
"""
from __future__ import annotations

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
from ..metrics import (
    holm_bonferroni,
    pairwise_compare,
    summarize_runs,
)
from ..metrics.stats import mcnemar_paired
from ..runner import (
    align_pairs,
    latency_breakdown_by_role,
    run_grid,
    save_results,
    summary_table,
)
from ..tasks import build_controlled_context_suite, load_humaneval
from ..types import RunResult

console = Console()


# ---------------------------------------------------------------------------
def run(
    cfg: Config,
    *,
    n: int = 20,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e1"),
    dry_run: bool = False,
    suite: str = "humaneval",
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    context_lengths = list(cfg.get("experiments.e1_context_lengths", [512, 2048, 8192]))
    suite_labels = _suite_labels(suite)

    llm = make_client(cfg, dry_run=dry_run)
    try:
        all_results: list[RunResult] = []
        for suite_label in suite_labels:
            for ctx_len in context_lengths:
                tasks = _load_suite(suite_label, n=n, context_target_tokens=ctx_len)
                agents = {
                    "CTRL_NoAssistant": make("CTRL", llm=llm, config=cfg),
                    "B0_SingleLarge":   make("B0", llm=llm, config=cfg),
                    "B1_SelfRefine":    make("B1", llm=llm, config=cfg),
                    "B2_ClassicalMAS":  make("B2", llm=llm, config=cfg),
                    "B3_HybridINoT":    make("B3", llm=llm, config=cfg),
                }
                console.rule(f"[bold]E1 :: {suite_label} :: длина контекста = {ctx_len} токенов[/bold]")
                r = run_grid(agents, tasks, seeds=seeds, progress_label=f"E1 {suite_label} ctx={ctx_len}")
                for x in r:
                    x.extra["suite_label"] = suite_label
                    x.extra["context_target_tokens"] = ctx_len
                all_results.extend(r)
                console.log(f"Cumulative spend: ${llm.spent_usd:.4f}")
    finally:
        llm.close()

    save_results(all_results, out_dir / "runs.json")

    # ---------- Сводки по каждому набору, архитектуре и контексту -----------
    summaries: dict[tuple[str, str, int], dict] = {}
    arch_names = ("CTRL_NoAssistant", "B0_SingleLarge", "B1_SelfRefine", "B2_ClassicalMAS", "B3_HybridINoT")
    for suite_label in suite_labels:
        for ctx_len in context_lengths:
            for arch in arch_names:
                subset = [r for r in all_results
                          if r.architecture == arch
                          and r.extra.get("suite_label") == suite_label
                          and r.extra.get("context_target_tokens") == ctx_len]
                s = summarize_runs(subset, lam=cfg.get("metrics.lambda_maintainability", 0.5))
                summaries[(suite_label, arch, ctx_len)] = s.__dict__

    (out_dir / "summary.json").write_text(
        json.dumps({f"{k[0]}::{k[1]}@ctx{k[2]}": v for k, v in summaries.items()}, indent=2, default=str),
        encoding="utf-8",
    )

    # ---------- Парные сравнения B3 и B2 по контекстам + Holm-Bonferroni ----
    pairwise: list[dict] = []
    pvals: list[float] = []

    # Per-task U_tok задаём как 1000 / total_tokens для успешного решения и 0
    # для неуспешного. Так средняя величина сохраняет смысл формулы U_tok.
    def _per_task_utok(r: RunResult) -> float:
        return (1000.0 / r.total_tokens) if (r.passed and r.total_tokens > 0) else 0.0

    for suite_label in suite_labels:
        for ctx_len in context_lengths:
            b2 = [r for r in all_results
                  if r.architecture == "B2_ClassicalMAS"
                  and r.extra.get("suite_label") == suite_label
                  and r.extra.get("context_target_tokens") == ctx_len]
            b3 = [r for r in all_results
                  if r.architecture == "B3_HybridINoT"
                  and r.extra.get("suite_label") == suite_label
                  and r.extra.get("context_target_tokens") == ctx_len]
            a, b = align_pairs(b2, b3, metric_a=_per_task_utok, metric_b=_per_task_utok)
            cmp = pairwise_compare(b, a, label=f"U_tok B3-B2 {suite_label} @ctx{ctx_len}",
                                   bootstrap_resamples=cfg.get("statistics.bootstrap_resamples", 10000),
                                   ci_level=cfg.get("statistics.ci_level", 0.95))
            # Парный binary pass/fail для McNemar.
            pa, pb = align_pairs(b2, b3, metric_a=lambda r: 1 if r.passed else 0,
                                 metric_b=lambda r: 1 if r.passed else 0)
            chi2, p_mc = mcnemar_paired(pa, pb)
            pairwise.append({
                "suite": suite_label,
                "context_length": ctx_len,
                "n_pairs": cmp.n,
                "wilcoxon_stat": cmp.statistic,
                "wilcoxon_p": cmp.p_value,
                "diff_mean": cmp.diff_mean,
                "ci_low": cmp.bootstrap_ci_low,
                "ci_high": cmp.bootstrap_ci_high,
                "mcnemar_chi2": chi2,
                "mcnemar_p_pass1": p_mc,
            })
            pvals.append(cmp.p_value)
    rejected = holm_bonferroni(pvals, alpha=cfg.get("statistics.alpha", 0.05))
    for d, rej in zip(pairwise, rejected):
        d["holm_bonferroni_rejected"] = bool(rej)
    (out_dir / "pairwise_b3_vs_b2.json").write_text(
        json.dumps(pairwise, indent=2), encoding="utf-8")

    # ---------- Текстовый вывод по H1 ---------------------------------------
    delta = float(cfg.get("experiments.delta_H1", 0.15))
    pp_tol = float(cfg.get("experiments.pass_at_1_tolerance_pp", 2.0)) / 100.0
    long_ctx = max(context_lengths)
    verdicts = {}
    verdict_md = f"# Вывод по H1 (E1, контекст={long_ctx} токенов)\n\n"
    for suite_label in suite_labels:
        s_b2 = summaries[(suite_label, "B2_ClassicalMAS", long_ctx)]
        s_b3 = summaries[(suite_label, "B3_HybridINoT", long_ctx)]
        rel_utok_gain = (s_b3["utok_per_kilo"] - s_b2["utok_per_kilo"]) / max(1e-12, s_b2["utok_per_kilo"])
        pass1_drop = s_b2["pass_at_1"] - s_b3["pass_at_1"]
        pvalue_long = next(d["wilcoxon_p"] for d in pairwise
                           if d["suite"] == suite_label and d["context_length"] == long_ctx)
        holm_long = next(d["holm_bonferroni_rejected"] for d in pairwise
                         if d["suite"] == suite_label and d["context_length"] == long_ctx)
        verdict = (
            "ПОДТВЕРЖДЕНА"
            if (rel_utok_gain >= delta and pass1_drop <= pp_tol and holm_long)
            else "НЕ ПОДТВЕРЖДЕНА"
        )
        verdicts[suite_label] = verdict
        verdict_md += (
            f"## {suite_label}\n\n"
            f"- ΔU_tok (B3-B2) / B2 = **{rel_utok_gain*100:+.2f}%**  (порог δ_H1 = {delta*100:.0f}%)\n"
            f"- падение pass@1 (B2-B3) = **{pass1_drop*100:+.2f} п.п.**  (допуск ≤ {pp_tol*100:.0f} п.п.)\n"
            f"- p-value Вилкоксона для per-task U_tok B3 vs B2 = **{pvalue_long:.4g}**\n"
            f"- отклонение H0 после Holm-Bonferroni при α=0.05: **{holm_long}**\n"
            f"- решение: **H1 {verdict}**\n\n"
        )
    h1_verdict = "ПОДТВЕРЖДЕНА" if all(v == "ПОДТВЕРЖДЕНА" for v in verdicts.values()) else "НЕ ПОДТВЕРЖДЕНА"
    verdict_md += f"## Итоговое решение\n\n**H1: {h1_verdict}**\n"
    (out_dir / "H1_VERDICT.md").write_text(verdict_md, encoding="utf-8")
    console.print(verdict_md)

    # ---------- Читаемая таблица для терминала -----------------------------
    flat_summaries = []
    for (suite_label, arch, ctx_len), s_dict in summaries.items():
        from ..metrics import Summary
        s = Summary(**s_dict)
        s.architecture = f"{suite_label}:{arch}@ctx{ctx_len}"
        flat_summaries.append(s)
    table = summary_table(flat_summaries, title="E1 — сводка по архитектурам и длинам контекста")
    console.print(table)
    with (out_dir / "table.txt").open("w", encoding="utf-8") as f:
        from rich.console import Console as _C
        _C(file=f, force_terminal=False, width=160).print(table)

    # ---------- Графики: подписи оставляем на английском -------------------
    _plot_grouped_bar(
        summaries, metric="mean_tokens", ylabel="Mean tokens / task",
        title="E1 — Token cost by architecture × context",
        out=out_dir / "fig_tokens_by_context.png",
    )
    _plot_grouped_line(
        summaries, metric="mean_cost_usd", ylabel="USD / task",
        title="E1 — Dollar cost vs context length",
        out=out_dir / "fig_cost_usd_by_context.png",
        threshold_context=cfg.get("experiments.h1_context_threshold_tokens", 2048),
    )
    _plot_grouped_line(
        summaries, metric="mean_cost_rub", ylabel="RUB / task",
        title="E1 — Ruble cost vs context length",
        out=out_dir / "fig_cost_rub_by_context.png",
        threshold_context=cfg.get("experiments.h1_context_threshold_tokens", 2048),
    )
    _plot_grouped_line(
        summaries, metric="utok_per_kilo", ylabel="U_tok = pass@1 / (tokens / 1000)",
        title="E1 — Token efficiency vs context length",
        out=out_dir / "fig_utok_by_context.png",
        threshold_context=cfg.get("experiments.h1_context_threshold_tokens", 2048),
    )
    _plot_grouped_line(
        summaries, metric="pass_at_1", ylabel="pass@1 (%)",
        title="E1 — pass@1 (%) vs context length",
        out=out_dir / "fig_pass_at_1_by_context.png",
        threshold_context=cfg.get("experiments.h1_context_threshold_tokens", 2048),
        value_scale=100.0,
    )
    _plot_cumulative_errors(all_results, out=out_dir / "fig_cumulative_errors.png")
    context_juggling = _context_juggling_summary(all_results)
    (out_dir / "context_juggling_summary.json").write_text(
        json.dumps(context_juggling, indent=2), encoding="utf-8")
    _plot_context_juggling(
        context_juggling,
        metric="mean_context_transfer_tokens",
        ylabel="Mean input/context tokens transmitted per task",
        title="E1 — Context transfer volume between role/model calls",
        out=out_dir / "fig_context_transfer_tokens.png",
        threshold_context=cfg.get("experiments.h1_context_threshold_tokens", 2048),
    )
    _plot_context_juggling(
        context_juggling,
        metric="mean_handoff_events",
        ylabel="Mean context handoff events per task",
        title="E1 — Context juggling frequency",
        out=out_dir / "fig_context_juggling_events.png",
        threshold_context=cfg.get("experiments.h1_context_threshold_tokens", 2048),
    )

    breakdown = latency_breakdown_by_role(all_results)
    (out_dir / "role_token_breakdown.json").write_text(
        json.dumps(breakdown, indent=2), encoding="utf-8")

    return {"verdict": h1_verdict, "summaries": summaries, "pairwise": pairwise}


# ---------------------------------------------------------------------------
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


def _plot_grouped_bar(
    summaries: dict,
    metric: str,
    ylabel: str,
    title: str,
    out: Path,
) -> None:
    series = sorted({(k[0], k[1]) for k in summaries.keys()})
    ctxs = sorted({k[2] for k in summaries.keys()})
    fig, ax = plt.subplots(figsize=(9, 5))
    bar_w = min(0.16, 0.75 / max(1, len(series)))
    x = np.arange(len(ctxs))
    for i, (suite_label, arch) in enumerate(series):
        vals = [summaries[(suite_label, arch, c)][metric] for c in ctxs]
        ax.bar(x + i * bar_w, vals, width=bar_w, label=f"{suite_label}:{arch.split('_', 1)[-1]}")
    ax.set_xticks(x + bar_w * (len(series) - 1) / 2)
    ax.set_xticklabels([f"|C0|≈{c}" for c in ctxs])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_grouped_line(
    summaries: dict,
    metric: str,
    ylabel: str,
    title: str,
    out: Path,
    *,
    threshold_context: int | None = None,
    value_scale: float = 1.0,
) -> None:
    series = sorted({(k[0], k[1]) for k in summaries.keys()})
    ctxs = sorted({k[2] for k in summaries.keys()})
    fig, ax = plt.subplots(figsize=(8, 5))
    for suite_label, arch in series:
        ys = [summaries[(suite_label, arch, c)][metric] * value_scale for c in ctxs]
        ax.plot(ctxs, ys, marker="o", label=f"{suite_label}:{arch.split('_', 1)[-1]}")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Context length |C0| (tokens)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    _add_context_threshold(ax, threshold_context)
    ax.legend(fontsize=8)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _context_juggling_summary(results: list[RunResult]) -> dict[str, dict]:
    grouped: dict[tuple[str, str, int], list[RunResult]] = {}
    for r in results:
        key = (
            str(r.extra.get("suite_label", r.task_id.split("/", 1)[0])),
            r.architecture,
            int(r.extra.get("context_target_tokens", 0)),
        )
        grouped.setdefault(key, []).append(r)

    out: dict[str, dict] = {}
    for (suite_label, arch, ctx), rows in grouped.items():
        handoffs = [_handoff_events(r) for r in rows]
        transfer_tokens = [r.total_input_tokens for r in rows]
        key = f"{suite_label}::{arch}@ctx{ctx}"
        out[key] = {
            "suite": suite_label,
            "architecture": arch,
            "context_length": ctx,
            "n": len(rows),
            "mean_handoff_events": float(np.mean(handoffs)) if handoffs else 0.0,
            "mean_context_transfer_tokens": float(np.mean(transfer_tokens)) if transfer_tokens else 0.0,
            "mean_total_tokens": float(np.mean([r.total_tokens for r in rows])) if rows else 0.0,
        }
    return out


def _handoff_events(r: RunResult) -> int:
    """Оценка числа context juggling events.

    Каждый LLM-вызов с ненулевым input считается отдельной передачей контекста.
    У Classical-MAS таких передач несколько, потому что роли вызываются
    отдельно; у Hybrid-INoT обычно один объединённый вызов; у CTRL их нет.
    """
    return sum(1 for u in r.usages if u.input_tokens > 0)


def _plot_context_juggling(
    summary: dict[str, dict],
    *,
    metric: str,
    ylabel: str,
    title: str,
    out: Path,
    threshold_context: int | None = None,
) -> None:
    rows = list(summary.values())
    series = sorted({(r["suite"], r["architecture"]) for r in rows})
    ctxs = sorted({int(r["context_length"]) for r in rows})
    by_key = {(r["suite"], r["architecture"], int(r["context_length"])): r for r in rows}
    fig, ax = plt.subplots(figsize=(8, 5))
    for suite_label, arch in series:
        ys = [by_key.get((suite_label, arch, c), {}).get(metric, 0.0) for c in ctxs]
        ax.plot(ctxs, ys, marker="o", label=f"{suite_label}:{arch.split('_', 1)[-1]}")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Context length |C0| (tokens)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    _add_context_threshold(ax, threshold_context)
    ax.legend(fontsize=8)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_cumulative_errors(results: list[RunResult], *, out: Path) -> None:
    grouped: dict[tuple[str, str], list[RunResult]] = {}
    for r in results:
        grouped.setdefault((str(r.extra.get("suite_label", "")), r.architecture), []).append(r)

    fig, ax = plt.subplots(figsize=(9, 5))
    for (suite_label, arch), rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda r: (
            int(r.extra.get("context_target_tokens", 0)),
            r.task_id,
            r.seed,
        ))
        cumulative = np.cumsum([0 if r.passed else 1 for r in rows])
        if len(cumulative):
            ax.plot(range(1, len(cumulative) + 1), cumulative, label=f"{suite_label}:{arch.split('_', 1)[-1]}")
    ax.set_xlabel("Run index (sorted by context, task, seed)")
    ax.set_ylabel("Cumulative errors")
    ax.set_title("E1 — Cumulative failed runs")
    ax.legend(fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _add_context_threshold(ax, threshold_context: int | None) -> None:
    if threshold_context is None:
        return
    ax.axvline(
        threshold_context,
        color="red",
        linestyle="--",
        linewidth=1.2,
        alpha=0.85,
        label=f"H1 threshold |C0|={threshold_context}",
    )
