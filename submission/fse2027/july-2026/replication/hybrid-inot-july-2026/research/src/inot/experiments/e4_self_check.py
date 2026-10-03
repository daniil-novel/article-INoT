"""E4 — Small-model self-check, verifies hypothesis H2 (§7.5).

Tests whether condition (16) of the article holds:
    C^S_check < (rho_0 - rho_1) * C^L_rerun

Procedure:
1. Run B0 (single large) on N HumanEval tasks; record per-task verification.
2. For each B0 candidate, query the SMALL model with the ``small_check``
   prompt → PASS/REJECT. Store its decision.
3. Estimate:
     rho_0 = P(rerun needed without small) = P(B0 fails)
     rho_1 = P(rerun needed with small)    = P(B0 fails AND small says PASS)
     C^S_check  = mean cost of the small-check call
     C^L_rerun  = mean cost of one B0 call (the rerun cost on large model)
4. Bootstrap a 95% CI for the gap  (rho_0 - rho_1) * C^L_rerun - C^S_check.
   H2 confirmed iff lower CI > 0 on both HumanEval AND SWE-bench Lite.

Outputs:
    runs.json
    H2_VERDICT.md
    summary.json
    fig_h2_savings.png
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
from ..metrics import bootstrap_ci
from ..runner import run_grid, save_results
from ..tasks import build_synthetic_tool_use_suite, load_humaneval, load_swebench_lite
from ..verification import extract_code

console = Console()


def run(
    cfg: Config,
    *,
    n: int = 20,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e4"),
    dry_run: bool = False,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    llm = make_client(cfg, dry_run=dry_run)
    findings = {}
    try:
        findings["humaneval"] = _run_dataset(
            cfg, llm, tasks=load_humaneval(n=n, context_target_tokens=512, seed=42),
            seeds=seeds, label="humaneval", out_dir=out_dir / "humaneval",
        )
        # SWE-bench Lite is optional (network/auth gated); fall back to
        # synthetic tool-use suite so the H2 check still has a second dataset.
        swe = load_swebench_lite(n=min(n, 30))
        if not swe:
            console.log("[yellow]SWE-bench Lite unavailable; using Synthetic Tool-Use Suite as second dataset.[/yellow]")
            swe = build_synthetic_tool_use_suite(n=min(n, 30), seed=42)
            label = "synthetic_tool_use_suite"
        else:
            label = "swebench_lite"
        findings[label] = _run_dataset(
            cfg, llm, tasks=swe, seeds=seeds, label=label,
            out_dir=out_dir / label,
        )
    finally:
        llm.close()

    # H2 verdict requires both datasets to confirm
    confirmed = all(f["h2_confirmed_lower_ci_gt_0"] for f in findings.values())
    md = "# H2 Verdict (E4)\n\nCondition (16): C_check^S < (ρ0 − ρ1) · C_rerun^L\n\n"
    for ds, f in findings.items():
        md += (
            f"## {ds}\n\n"
            f"- ρ0 (P[rerun needed w/o small check])     = **{f['rho_0']:.4f}**\n"
            f"- ρ1 (P[rerun needed w/  small check])     = **{f['rho_1']:.4f}**\n"
            f"- C_check^S (mean small-check cost, USD)   = **${f['C_check_S']:.6f}**\n"
            f"- C_rerun^L (mean large rerun cost, USD)   = **${f['C_rerun_L']:.6f}**\n"
            f"- Expected savings (ρ0−ρ1)·C_rerun^L       = **${f['expected_savings']:.6f}**\n"
            f"- Net economic margin per task             = **${f['net_margin']:.6f}**\n"
            f"- Bootstrap 95% CI for net margin          = "
            f"[${f['ci_low']:.6f}, ${f['ci_high']:.6f}]\n"
            f"- Lower CI > 0 ⇒ H2 confirmed on this dataset: **{f['h2_confirmed_lower_ci_gt_0']}**\n\n"
        )
    md += f"\n## Decision\n\n**H2: {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}**\n"
    (out_dir / "H2_VERDICT.md").write_text(md, encoding="utf-8")
    console.print(md)
    (out_dir / "summary.json").write_text(
        json.dumps(findings, indent=2, default=str), encoding="utf-8")
    return findings


# ---------------------------------------------------------------------------
def _run_dataset(cfg, llm, *, tasks, seeds, label, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    console.rule(f"[bold]E4 :: {label}[/bold]")
    b0 = make("B0", llm=llm, config=cfg)
    b0_results = run_grid({"B0": b0}, tasks, seeds=seeds, progress_label=f"E4 {label} B0")
    save_results(b0_results, out_dir / "runs_b0.json")

    # Small-model pre-screening (does it endorse a wrong candidate?)
    small_decisions = []
    small_costs = []
    rerun_costs = [r.total_cost_usd for r in b0_results]   # one B0 call ≡ one rerun
    for r in b0_results:
        sol_code = extract_code(r.final_solution, None)
        msgs = [
            {"role": "system",
             "content": "You are a fast pre-screener. Reply with ONE WORD: PASS or REJECT."},
            {"role": "user",
             "content": f"Task:\n{_task_prompt(tasks, r.task_id)}\n\nCandidate code:\n{sol_code}\n\nReply PASS or REJECT."},
        ]
        check = llm.chat(msgs, model=cfg.small_model, role="small_check",
                         architecture="E4_smallcheck", iteration=0, seed=r.seed,
                         max_tokens=8)
        small_costs.append(check.usage.cost_usd)
        decision = "PASS" if "PASS" in check.text.upper() else "REJECT"
        small_decisions.append(decision)

    # Estimate rho_0 / rho_1
    n = len(b0_results)
    if n == 0:
        return {"note": "no runs"}
    rho_0 = sum(0 if r.passed else 1 for r in b0_results) / n
    rho_1 = sum(
        1 for r, d in zip(b0_results, small_decisions)
        if (not r.passed) and d == "PASS"
    ) / n
    C_check_S = float(np.mean(small_costs)) if small_costs else 0.0
    C_rerun_L = float(np.mean(rerun_costs)) if rerun_costs else 0.0
    savings = (rho_0 - rho_1) * C_rerun_L
    margin = savings - C_check_S

    # Bootstrap CI for the per-task margin: per-task margin = saved_$ - check_$.
    # saved$_i = (1 if r0_i fails AND small says REJECT else 0) * rerun_cost_i
    per_task_savings = np.array([
        (1.0 if (not r.passed and d == "REJECT") else 0.0) * cost
        for r, d, cost in zip(b0_results, small_decisions, rerun_costs)
    ])
    per_task_check = np.array(small_costs)
    per_task_margin = per_task_savings - per_task_check
    ci_low, ci_high = bootstrap_ci(per_task_margin, statistic=np.mean,
                                   resamples=cfg.get("statistics.bootstrap_resamples", 10000),
                                   ci_level=cfg.get("statistics.ci_level", 0.95))
    confirmed = ci_low > 0

    out = {
        "n_tasks": n,
        "rho_0": rho_0,
        "rho_1": rho_1,
        "C_check_S": C_check_S,
        "C_rerun_L": C_rerun_L,
        "expected_savings": savings,
        "net_margin": margin,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "h2_confirmed_lower_ci_gt_0": bool(confirmed),
        "small_decision_counts": {
            "PASS": sum(1 for d in small_decisions if d == "PASS"),
            "REJECT": sum(1 for d in small_decisions if d == "REJECT"),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    _plot_h2(per_task_margin, label, out=out_dir / "fig_h2_savings.png")
    return out


def _task_prompt(tasks, task_id: str) -> str:
    for t in tasks:
        if t.task_id == task_id:
            return t.prompt
    return ""


def _plot_h2(margins: np.ndarray, label: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(margins, bins=30, color="#3a7", edgecolor="black", alpha=0.85)
    ax.axvline(float(np.mean(margins)), color="red", linestyle="--", label=f"mean = {np.mean(margins):+.5f}")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Per-task net margin $\\$_{savings} - \\$_{check}$ (USD)")
    ax.set_ylabel("count")
    ax.set_title(f"E4/H2 — Distribution of per-task net margin ({label})")
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
