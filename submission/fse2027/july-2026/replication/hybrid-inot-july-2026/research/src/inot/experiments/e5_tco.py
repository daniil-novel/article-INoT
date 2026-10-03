"""E5 — TCO on real measurements (§7.6).

Replaces the synthetic TCO in the article's old Table 4 with a concrete
measurement on N tasks for B2 vs B3. We also vary token prices ±50% and
extrapolate to ``e5_extrapolate_to`` tasks/month with a bootstrap CI.

Outputs:
    runs.json
    tco_summary.json
    fig_tco_extrapolation.png
    fig_price_sensitivity.png
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
from ..metrics import bootstrap_ci, summarize_runs
from ..runner import run_grid, save_results, summary_table
from ..tasks import load_humaneval

console = Console()


def run(
    cfg: Config,
    *,
    n: int = 40,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e5"),
    dry_run: bool = False,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    llm = make_client(cfg, dry_run=dry_run)
    extrapolate_to = int(cfg.get("experiments.e5_extrapolate_to", 10000))
    try:
        # Mixed context lengths to mirror "different lengths" in §7.6
        tasks = []
        for ctx in (512, 2048, 8192):
            tasks.extend(load_humaneval(n=max(1, n // 3), context_target_tokens=ctx, seed=42))
        agents = {
            "B2_ClassicalMAS": make("B2", llm=llm, config=cfg),
            "B3_HybridINoT":   make("B3", llm=llm, config=cfg),
        }
        console.rule("[bold]E5 — TCO comparison B2 vs B3[/bold]")
        results = run_grid(agents, tasks, seeds=seeds, progress_label="E5")
    finally:
        llm.close()
    save_results(results, out_dir / "runs.json")

    b2 = [r for r in results if r.architecture == "B2_ClassicalMAS"]
    b3 = [r for r in results if r.architecture == "B3_HybridINoT"]
    s_b2 = summarize_runs(b2, lam=cfg.get("metrics.lambda_maintainability", 0.5))
    s_b3 = summarize_runs(b3, lam=cfg.get("metrics.lambda_maintainability", 0.5))
    delta_per_task = s_b2.mean_cost_usd - s_b3.mean_cost_usd
    delta_extrap = delta_per_task * extrapolate_to

    # Bootstrap monthly TCO difference at base prices
    per_task_diff_arr = _aligned_diff([r.total_cost_usd for r in b2],
                                      [r.total_cost_usd for r in b3])
    ci_lo, ci_hi = bootstrap_ci(
        per_task_diff_arr, statistic=np.mean,
        resamples=cfg.get("statistics.bootstrap_resamples", 10000),
        ci_level=cfg.get("statistics.ci_level", 0.95),
    )
    monthly_ci = (ci_lo * extrapolate_to, ci_hi * extrapolate_to)

    # Price sensitivity ±50%
    sensitivity = []
    for jitter in (-0.5, -0.25, 0.0, 0.25, 0.5):
        scaled_b2 = [c * (1 + jitter) for c in [r.total_cost_usd for r in b2]]
        scaled_b3 = [c * (1 + jitter) for c in [r.total_cost_usd for r in b3]]
        diff = float(np.mean(scaled_b2) - np.mean(scaled_b3)) * extrapolate_to
        sensitivity.append({"price_jitter": jitter, "monthly_delta_usd": diff})

    summary = {
        "extrapolate_to_tasks_per_month": extrapolate_to,
        "n_per_arch": len(b2),
        "B2": s_b2.__dict__,
        "B3": s_b3.__dict__,
        "delta_cost_per_task_b2_minus_b3_usd": delta_per_task,
        "delta_monthly_b2_minus_b3_usd": delta_extrap,
        "monthly_delta_bootstrap_ci_usd": list(monthly_ci),
        "tco_savings_significant_at_lower_ci": monthly_ci[0] > 0,
        "price_sensitivity": sensitivity,
    }
    (out_dir / "tco_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    table = summary_table([s_b2, s_b3], title="E5 — B2 vs B3 (mixed context lengths)")
    console.print(table)
    with (out_dir / "table.txt").open("w", encoding="utf-8") as f:
        from rich.console import Console as _C
        _C(file=f, force_terminal=False, width=160).print(table)

    _plot_extrapolation(per_task_diff_arr, extrapolate_to, monthly_ci,
                        out=out_dir / "fig_tco_extrapolation.png")
    _plot_sensitivity(sensitivity, out=out_dir / "fig_price_sensitivity.png")
    console.print(f"[bold]E5[/bold] monthly Δcost (B2-B3) ≈ ${delta_extrap:.2f}  "
                  f"95% CI = [{monthly_ci[0]:.2f}, {monthly_ci[1]:.2f}]")
    return summary


def _aligned_diff(a: list[float], b: list[float]) -> np.ndarray:
    n = min(len(a), len(b))
    return np.array([a[i] - b[i] for i in range(n)])


def _plot_extrapolation(diff: np.ndarray, scale: int, ci, out: Path):
    monthly = diff * scale
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(monthly, bins=30, color="#37a", edgecolor="black", alpha=0.85)
    ax.axvline(float(np.mean(monthly)), color="red", linestyle="--",
               label=f"mean = ${np.mean(monthly):+.2f}/mo")
    ax.axvline(0, color="black", lw=0.8)
    ax.axvspan(ci[0], ci[1], color="orange", alpha=0.2, label=f"95% CI [{ci[0]:.1f}, {ci[1]:.1f}]")
    ax.set_xlabel("Monthly USD savings B2 − B3 (extrapolated)")
    ax.set_ylabel("Bootstrap density")
    ax.set_title("E5 — Monthly TCO delta (positive ⇒ B3 cheaper)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_sensitivity(records: list[dict], out: Path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = [r["price_jitter"] * 100 for r in records]
    ys = [r["monthly_delta_usd"] for r in records]
    ax.plot(xs, ys, marker="o", color="#3a3")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Token-price perturbation (%)")
    ax.set_ylabel("Monthly Δcost B2 − B3 (USD)")
    ax.set_title("E5 — Sensitivity of monthly TCO delta to ±50% price")
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
