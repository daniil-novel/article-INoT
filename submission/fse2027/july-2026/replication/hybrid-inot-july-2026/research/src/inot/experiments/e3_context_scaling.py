"""E3 — Scaling on context length, empirical estimate of τ⋆ (§7.4).

Plot U_tok(|C0|) for B0 / B2 / B3 across context lengths {256, 1024, 4096,
16384}. The article defines τ⋆ as the smallest context length at which
U_tok^{B3} ≥ U_tok^{B2}. We:

1. Run all three on each context length × seed.
2. Fit U_tok^{B3-B2} as a piecewise function of |C0|.
3. Report τ⋆ as the linear-interpolation crossing point of the two
   broken-line curves of mean U_tok.
4. Bootstrap τ⋆ over the seeds → 95% CI.

Outputs (in ``results/e3/``):
    runs.json
    fig_utok_vs_context.png
    fig_delta_utok_vs_context.png
    tau_star.json   — point estimate + bootstrap CI
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
from ..metrics import compute_utok, summarize_runs
from ..runner import run_grid, save_results, summary_table
from ..tasks import load_humaneval

console = Console()


def run(
    cfg: Config,
    *,
    n: int = 20,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e3"),
    dry_run: bool = False,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    context_lengths = list(cfg.get("experiments.e3_context_lengths", [256, 1024, 4096, 16384]))

    llm = make_client(cfg, dry_run=dry_run)
    all_results = []
    try:
        for ctx_len in context_lengths:
            tasks = load_humaneval(n=n, context_target_tokens=ctx_len, seed=42)
            agents = {
                "B0_SingleLarge":  make("B0", llm=llm, config=cfg),
                "B2_ClassicalMAS": make("B2", llm=llm, config=cfg),
                "B3_HybridINoT":   make("B3", llm=llm, config=cfg),
            }
            console.rule(f"[bold]E3 :: |C0|={ctx_len}[/bold]")
            res = run_grid(agents, tasks, seeds=seeds, progress_label=f"E3 ctx={ctx_len}")
            for r in res:
                r.extra["context_target_tokens"] = ctx_len
            all_results.extend(res)
            console.log(f"Cumulative spend: ${llm.spent_usd:.4f}")
    finally:
        llm.close()
    save_results(all_results, out_dir / "runs.json")

    # --- per-(arch, ctx) U_tok ---------------------------------------------
    archs = ["B0_SingleLarge", "B2_ClassicalMAS", "B3_HybridINoT"]
    matrix: dict[str, list[float]] = {a: [] for a in archs}
    for ctx_len in context_lengths:
        for a in archs:
            sub = [r for r in all_results
                   if r.architecture == a and r.extra.get("context_target_tokens") == ctx_len]
            matrix[a].append(compute_utok(sub))

    diff_b3_b2 = [b3 - b2 for b3, b2 in zip(matrix["B3_HybridINoT"], matrix["B2_ClassicalMAS"])]
    tau_star = _find_crossing(context_lengths, matrix["B3_HybridINoT"], matrix["B2_ClassicalMAS"])

    # Bootstrap τ⋆ over seeds (re-fit on each resample)
    boot = _bootstrap_tau_star(all_results, archs, context_lengths,
                               n_resamples=cfg.get("statistics.bootstrap_resamples", 10000),
                               seed=12345)
    tau_payload = {
        "context_lengths": context_lengths,
        "utok_curves": matrix,
        "delta_utok_b3_minus_b2": diff_b3_b2,
        "tau_star_point_estimate": tau_star,
        "tau_star_bootstrap_ci": [boot["lo"], boot["hi"]],
        "tau_star_bootstrap_median": boot["median"],
        "tau_star_finite_share": boot["finite_share"],
        "h1_practically_supported": (
            tau_star is not None and tau_star < context_lengths[-1]
        ),
    }
    (out_dir / "tau_star.json").write_text(json.dumps(tau_payload, indent=2), encoding="utf-8")

    # --- pretty summary by ctx --------------------------------------------
    flat = []
    for ctx_len in context_lengths:
        for a in archs:
            sub = [r for r in all_results
                   if r.architecture == a and r.extra.get("context_target_tokens") == ctx_len]
            s = summarize_runs(sub, lam=cfg.get("metrics.lambda_maintainability", 0.5))
            s.architecture = f"{a}@ctx{ctx_len}"
            flat.append(s)
    table = summary_table(flat, title="E3 — by architecture × context length")
    console.print(table)
    with (out_dir / "table.txt").open("w", encoding="utf-8") as f:
        from rich.console import Console as _C
        _C(file=f, force_terminal=False, width=160).print(table)

    # --- plots ------------------------------------------------------------
    _plot_curves(context_lengths, matrix,
                 title="E3 — U_tok vs context length (Q per 1000 tokens)",
                 ylabel="U_tok",
                 out=out_dir / "fig_utok_vs_context.png",
                 mark_tau=tau_star)
    _plot_diff(context_lengths, diff_b3_b2,
               title="E3 — ΔU_tok = U_tok(B3) - U_tok(B2)",
               out=out_dir / "fig_delta_utok_vs_context.png",
               tau=tau_star)

    console.print(f"[bold]E3[/bold] τ⋆ ≈ {tau_star} tokens   95% bootstrap CI = "
                  f"[{boot['lo']}, {boot['hi']}]   "
                  f"H1 practically supported = {tau_payload['h1_practically_supported']}")
    return tau_payload


# ---------------------------------------------------------------------------
def _find_crossing(xs, ys_b3, ys_b2):
    """Return smallest x where ys_b3 >= ys_b2; linear interpolation between
    consecutive samples. Returns None if no crossing in [min, max]."""
    diffs = [b3 - b2 for b3, b2 in zip(ys_b3, ys_b2)]
    for i in range(1, len(xs)):
        if diffs[i - 1] < 0 <= diffs[i]:
            x0, x1 = xs[i - 1], xs[i]
            d0, d1 = diffs[i - 1], diffs[i]
            t = -d0 / (d1 - d0) if d1 != d0 else 0.5
            return float(x0 + t * (x1 - x0))
        if diffs[i] >= 0 and diffs[i - 1] >= 0 and i == 1:
            return float(xs[0])
    if all(d >= 0 for d in diffs):
        return float(xs[0])
    return None


def _bootstrap_tau_star(all_results, archs, context_lengths, n_resamples: int, seed: int) -> dict:
    """Bootstrap by resampling tasks within each (arch, ctx) bucket."""
    rng = np.random.default_rng(seed)
    by_bucket: dict[tuple, list] = {}
    for r in all_results:
        key = (r.architecture, r.extra.get("context_target_tokens"))
        by_bucket.setdefault(key, []).append(r)
    finite, samples = 0, []
    for _ in range(n_resamples):
        ys_b3, ys_b2 = [], []
        for ctx in context_lengths:
            b3 = by_bucket.get(("B3_HybridINoT", ctx), [])
            b2 = by_bucket.get(("B2_ClassicalMAS", ctx), [])
            if not b3 or not b2:
                ys_b3.append(0.0)
                ys_b2.append(0.0)
                continue
            idx_b3 = rng.integers(0, len(b3), size=len(b3))
            idx_b2 = rng.integers(0, len(b2), size=len(b2))
            ys_b3.append(compute_utok([b3[i] for i in idx_b3]))
            ys_b2.append(compute_utok([b2[i] for i in idx_b2]))
        x = _find_crossing(context_lengths, ys_b3, ys_b2)
        if x is not None:
            finite += 1
            samples.append(x)
    if not samples:
        return {"lo": None, "hi": None, "median": None, "finite_share": 0.0}
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return {"lo": float(lo), "hi": float(hi), "median": float(np.median(samples)),
            "finite_share": finite / n_resamples}


def _plot_curves(xs, matrix, *, title, ylabel, out: Path, mark_tau):
    fig, ax = plt.subplots(figsize=(8, 5))
    for a, ys in matrix.items():
        ax.plot(xs, ys, marker="o", label=a.split("_", 1)[-1])
    if mark_tau is not None:
        ax.axvline(mark_tau, color="red", linestyle="--", label=f"τ⋆ ≈ {mark_tau:.0f}")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Context length |C0| (tokens)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_diff(xs, diffs, *, title, out: Path, tau):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axhline(0, color="black", lw=0.8)
    ax.plot(xs, diffs, marker="s", color="#444")
    if tau is not None:
        ax.axvline(tau, color="red", linestyle="--", label=f"τ⋆ ≈ {tau:.0f}")
        ax.legend()
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Context length |C0| (tokens)")
    ax.set_ylabel("ΔU_tok (B3 - B2)")
    ax.set_title(title)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
