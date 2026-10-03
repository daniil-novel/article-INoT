"""E2 — Ablation analysis and adversarial scenarios (§7.3).

Sub-experiments:
    E2a  - Component ablations:
             B3        : full Hybrid-INoT
             B3a       : no compression                 (compression=False)
             B3b       : no internal critic             (critic=False)
             B3c       : no external self-check gating  (self_check=False)
           Each component must give a statistically significant contribution.

    E2b  - Critic systematic-error scenario:
             50 tasks where B0 fails. Measure how often r_crit endorses an
             incorrect candidate. Article alarm threshold: > 20%.

    E2c  - Parallel tools scenario (H3 boundary):
             50 tasks from Synthetic Tool-Use Suite with parallelism in
             {2,3,4}. Compare wall-clock latency B3 vs B2; B3 degradation
             up to 30% is "acceptable".

    E2d  - Metric sensitivity:
             Re-rank B0..B3 with weights w ± 20% and λ ∈ {0, .25, .5, .75, 1}.
             Inversion of ranking ⇒ metric is fragile to the choice.
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

from ..architectures import HybridINoTAgent, make
from ..config import Config
from ..llm import make_client
from ..metrics import (
    holm_bonferroni,
    pairwise_compare,
    summarize_runs,
)
from ..runner import align_pairs, run_grid, save_results, summary_table
from ..tasks import build_synthetic_tool_use_suite, load_humaneval
from ..tools.synthetic import measure_synthetic_tool_latency, summarize_tool_latency

console = Console()


def run(
    cfg: Config,
    *,
    n: int = 20,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e2"),
    dry_run: bool = False,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    llm = make_client(cfg, dry_run=dry_run)
    findings: dict = {}
    try:
        findings["e2a"] = _e2a_ablation(cfg, llm, n=n, seeds=seeds, out_dir=out_dir / "e2a")
        findings["e2b"] = _e2b_critic_error(cfg, llm, n=min(n, 50), seeds=seeds, out_dir=out_dir / "e2b")
        findings["e2c"] = _e2c_parallel_tools(cfg, llm, n=min(n, 50), seeds=seeds, out_dir=out_dir / "e2c")
    finally:
        llm.close()

    findings["e2d"] = _e2d_sensitivity(out_dir / "e2a" / "runs.json", cfg, out_dir / "e2d")
    (out_dir / "summary.json").write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    return findings


# ---------------------------------------------------------------------------
def _e2a_ablation(cfg, llm, *, n, seeds, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = load_humaneval(n=n, context_target_tokens=2048, seed=42)
    agents = {
        "B3_full":  HybridINoTAgent(llm, cfg),
        "B3a_no_compression": HybridINoTAgent(llm, cfg, ablate={"compression": False}),
        "B3b_no_critic":      HybridINoTAgent(llm, cfg, ablate={"critic": False}),
        "B3c_no_self_check":  HybridINoTAgent(llm, cfg, ablate={"self_check": False}),
    }
    # Force unique architecture names so Summary distinguishes them
    for k, a in agents.items():
        a.name = k
    console.rule("[bold]E2a — component ablations[/bold]")
    results = run_grid(agents, tasks, seeds=seeds, progress_label="E2a")
    save_results(results, out_dir / "runs.json")
    sums = {}
    for k in agents:
        s = summarize_runs([r for r in results if r.architecture == k],
                           lam=cfg.get("metrics.lambda_maintainability", 0.5))
        sums[k] = s.__dict__
    (out_dir / "summary.json").write_text(json.dumps(sums, indent=2, default=str), encoding="utf-8")

    # Wilcoxon: does each ablated variant *significantly* hurt MAS_i?
    base = [r for r in results if r.architecture == "B3_full"]
    pairwise = []
    pvals = []

    def per_task_mas(r):
        return (
            (1.0 if r.passed else 0.0)
            * (max(0.0, min(1.0, r.verification.maintainability)) ** cfg.get("metrics.lambda_maintainability", 0.5))
        )
    for k in ("B3a_no_compression", "B3b_no_critic", "B3c_no_self_check"):
        sub = [r for r in results if r.architecture == k]
        a, b = align_pairs(base, sub, metric_a=per_task_mas, metric_b=per_task_mas)
        cmp = pairwise_compare(a, b, label=f"MAS B3 vs {k}",
                               bootstrap_resamples=cfg.get("statistics.bootstrap_resamples", 10000))
        pairwise.append({"label": cmp.label, "n": cmp.n,
                         "diff_mean": cmp.diff_mean, "p_value": cmp.p_value,
                         "ci": [cmp.bootstrap_ci_low, cmp.bootstrap_ci_high]})
        pvals.append(cmp.p_value)
    rejected = holm_bonferroni(pvals, alpha=cfg.get("statistics.alpha", 0.05))
    for d, rej in zip(pairwise, rejected):
        d["holm_rejected"] = bool(rej)
    (out_dir / "pairwise_vs_full.json").write_text(json.dumps(pairwise, indent=2, default=str), encoding="utf-8")

    table = summary_table([__make_summary(s) for s in sums.values()],
                          title="E2a — ablations on HumanEval @ ctx=2048")
    console.print(table)

    _plot_ablation(sums, out=out_dir / "fig_ablation_mas.png")
    return {"summaries": sums, "pairwise": pairwise}


def _e2b_critic_error(cfg, llm, *, n, seeds, out_dir: Path) -> dict:
    """Pick tasks where B0 fails; measure how often the B3 critic ENDORSES
    an incorrect candidate (i.e. picks a candidate whose tests fail)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = load_humaneval(n=n, context_target_tokens=512, seed=42)
    b0 = make("B0", llm=llm, config=cfg)
    b3 = HybridINoTAgent(llm, cfg)
    console.rule("[bold]E2b — critic systematic-error scenario[/bold]")
    b0_results = run_grid({"B0": b0}, tasks, seeds=[seeds[0]], progress_label="E2b probe")
    failing_ids = [r.task_id for r in b0_results if not r.passed]
    failing_tasks = [t for t in tasks if t.task_id in failing_ids]
    if not failing_tasks:
        return {"note": "B0 solved every task; cannot estimate critic error rate."}
    b3_results = run_grid({"B3": b3}, failing_tasks, seeds=seeds, progress_label="E2b B3")
    save_results(b0_results + b3_results, out_dir / "runs.json")

    # Critic endorses an incorrect candidate iff the chosen candidate's
    # external verification fails. We approximate by counting failed B3 runs.
    n_endorsed = sum(1 for r in b3_results if not r.passed)
    rate = n_endorsed / len(b3_results)
    alarm = rate > 0.20
    out = {
        "n_failing_for_b0": len(failing_tasks),
        "n_b3_runs": len(b3_results),
        "critic_endorsement_error_rate": float(rate),
        "alarm_threshold_exceeded": bool(alarm),
    }
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    console.print(f"[bold]E2b[/bold] critic endorsement error rate = {rate*100:.1f}%  "
                  f"({'ALARM' if alarm else 'within tolerance'})")
    return out


def _e2c_parallel_tools(cfg, llm, *, n, seeds, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = build_synthetic_tool_use_suite(n=n, seed=42)
    serial_tools = measure_synthetic_tool_latency(tasks, mode="serial")
    parallel_tools = measure_synthetic_tool_latency(tasks, mode="parallel")
    (out_dir / "tool_latency_serial.json").write_text(
        json.dumps([r.to_dict() for r in serial_tools], indent=2), encoding="utf-8")
    (out_dir / "tool_latency_parallel.json").write_text(
        json.dumps([r.to_dict() for r in parallel_tools], indent=2), encoding="utf-8")

    agents = {
        "B2_ClassicalMAS": make("B2", llm=llm, config=cfg),
        "B3_HybridINoT":   make("B3", llm=llm, config=cfg),
    }
    console.rule("[bold]E2c — parallel tools (H3 boundary)[/bold]")
    results = run_grid(agents, tasks, seeds=seeds, progress_label="E2c")
    save_results(results, out_dir / "runs.json")

    b2 = [r for r in results if r.architecture == "B2_ClassicalMAS"]
    b3 = [r for r in results if r.architecture == "B3_HybridINoT"]
    a, b = align_pairs(b2, b3, metric_a=lambda r: r.wall_clock_seconds,
                       metric_b=lambda r: r.wall_clock_seconds)
    cmp = pairwise_compare(b, a, label="latency B3-B2",
                           bootstrap_resamples=cfg.get("statistics.bootstrap_resamples", 10000))
    rel_slowdown = (np.mean(b) - np.mean(a)) / max(1e-9, np.mean(a))
    tool_serial = summarize_tool_latency(serial_tools)
    tool_parallel = summarize_tool_latency(parallel_tools)
    tool_slowdown = (
        tool_serial["mean_measured_latency_ms"] - tool_parallel["mean_measured_latency_ms"]
    ) / max(1e-9, tool_parallel["mean_measured_latency_ms"])
    h3_supported = bool(tool_slowdown > 0)  # serial Hybrid-style tools slower than parallel MAS tools
    out = {
        "n_pairs": cmp.n,
        "b2_mean_latency_s": float(np.mean(a)),
        "b3_mean_latency_s": float(np.mean(b)),
        "relative_slowdown_b3_over_b2": float(rel_slowdown),
        "wilcoxon_p": cmp.p_value,
        "ci_diff_b3_minus_b2": [cmp.bootstrap_ci_low, cmp.bootstrap_ci_high],
        "tool_serial_summary": tool_serial,
        "tool_parallel_summary": tool_parallel,
        "tool_relative_slowdown_serial_over_parallel": float(tool_slowdown),
        "h3_supported_parallel_tools_hurt_serial_hybrid": h3_supported,
        "acceptable_30pct_band": bool(rel_slowdown <= 0.30),
    }
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    console.print(json.dumps(out, indent=2, default=str))

    _plot_latency(a, b, out=out_dir / "fig_latency_b2_vs_b3.png")
    return out


def _e2d_sensitivity(runs_path: Path, cfg: Config, out_dir: Path) -> dict:
    """Re-rank arches by MAS_i with perturbed weights and λ values.

    Inversions in the ranking ⇒ metric is fragile.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if not runs_path.exists():
        return {"note": f"no E2a runs file at {runs_path}; skipping sensitivity"}
    from ..runner import load_results
    runs = load_results(runs_path)
    arches = sorted({r.architecture for r in runs})
    rankings = []
    for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
        for jitter in (-0.2, 0.0, 0.2):
            ranks = []
            for a in arches:
                sub = [r for r in runs if r.architecture == a]
                ranks.append((a, _compute_mas_with_maintainability_jitter(sub, lam=lam, jitter=jitter)))
            ranks.sort(key=lambda x: x[1], reverse=True)
            rankings.append({"lambda": lam, "weight_jitter": jitter,
                             "ranking": [r[0] for r in ranks],
                             "scores": {r[0]: r[1] for r in ranks}})
    # Detect inversion vs the "canonical" ranking (lambda=0.5, jitter=0)
    canonical = next(r["ranking"] for r in rankings
                     if r["lambda"] == 0.5 and r["weight_jitter"] == 0.0)
    inversions = sum(1 for r in rankings if r["ranking"] != canonical)
    out = {"canonical_ranking": canonical, "inversions_under_perturbation": inversions,
           "rankings": rankings}
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    console.print(f"[bold]E2d[/bold] inversions = {inversions} / {len(rankings)} perturbations")
    return out


# ---------------------------------------------------------------------------
def __make_summary(d):
    from ..metrics import Summary
    return Summary(**d)


def _compute_mas_with_maintainability_jitter(results, *, lam: float, jitter: float) -> float:
    if not results:
        return 0.0
    vals = []
    for r in results:
        success = 1.0 if r.passed else 0.0
        verified = 1.0 if (r.verification.tests_passed and r.verification.static_passed) else 0.0
        maintainability = max(0.0, min(1.0, r.verification.maintainability * (1.0 + jitter)))
        vals.append(min(success, verified) * (maintainability ** lam))
    return float(np.mean(vals))


def _plot_ablation(summaries: dict, out: Path) -> None:
    keys = list(summaries.keys())
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(keys, [summaries[k]["mas"] for k in keys], color=["#2c7", "#999", "#999", "#999"])
    ax.set_ylabel("MAS_i")
    ax.set_title("E2a — Ablation impact on MAS_i (HumanEval @ ctx=2048)")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_latency(b2: list[float], b3: list[float], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([b2, b3], labels=["B2 Classical-MAS", "B3 Hybrid-INoT"], showmeans=True)
    ax.set_ylabel("Wall-clock latency (s)")
    ax.set_title("E2c — Latency on parallel-tools tasks (H3)")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
