"""Shared runner utilities used by every experiment module.

Provides:
    run_grid(architectures, tasks, seeds, ...)  -> list[RunResult]
    save_results(results, path)
    load_results(path)
    align_pairs(results_a, results_b)           -> matched (a,b) lists by (task,seed)
    summary_table(per_arch_summaries)           -> pretty rich.table.Table
    latency_breakdown_by_role(usages)           -> dict[role, mean_tokens]

The runner is intentionally synchronous: experiments are I/O bound on the LLM
side, but ordered execution gives reproducible cost numbers and easier debug.
A simple ProgressBar is exposed so long runs are visible.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Sequence

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from .architectures import BaseAgent
from .llm import BudgetExceeded
from .metrics import Summary
from .types import RunResult, Task

log = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
def run_grid(
    agents: dict[str, BaseAgent],
    tasks: Sequence[Task],
    seeds: Sequence[int],
    *,
    progress_label: str = "running",
) -> list[RunResult]:
    """Cartesian product: (agent, task, seed). Errors are logged & captured."""
    total = len(agents) * len(tasks) * len(seeds)
    results: list[RunResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("/"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as pbar:
        outer = pbar.add_task(progress_label, total=total)
        for arch_name, agent in agents.items():
            for task in tasks:
                for seed in seeds:
                    pbar.update(outer, description=f"{arch_name} :: {task.task_id} (seed={seed})")
                    try:
                        r = agent.run(task, seed=seed)
                    except Exception as exc:  # noqa: BLE001
                        if _is_infrastructure_error(exc):
                            log.exception("infrastructure error on %s/%s seed=%s", arch_name, task.task_id, seed)
                            raise
                        log.exception("agent crash on %s/%s seed=%s", arch_name, task.task_id, seed)
                        from .types import VerificationResult
                        r = RunResult(
                            task_id=task.task_id, architecture=arch_name, seed=seed,
                            final_solution="", verification=VerificationResult(
                                passed=False, error_message=f"crash: {exc}"
                            ),
                        )
                    results.append(r)
                    pbar.advance(outer)
    return results


def _is_infrastructure_error(exc: Exception) -> bool:
    if isinstance(exc, (BudgetExceeded, httpx.HTTPError)):
        return True
    msg = str(exc)
    return (
        "OPENROUTER_API_KEY" in msg
        or "Insufficient credits" in msg
        or "BudgetExceeded" in msg
        or "OpenRouter call failed" in msg
    )


# ---------------------------------------------------------------------------
def save_results(results: Sequence[RunResult], path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in results]
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_results(path: Path | str) -> list[RunResult]:
    """Read JSON results file back into RunResult objects (lossy on extras)."""
    from .types import VerificationResult, TokenUsage
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[RunResult] = []
    for d in raw:
        v = VerificationResult(
            passed=d["passed"],
            tests_passed=d.get("tests_passed", False),
            static_passed=d.get("static_passed", False),
            security_passed=d.get("security_passed", False),
            maintainability=d.get("maintainability", 0.0),
        )
        usages = [TokenUsage(**u) for u in d.get("usages", [])]
        out.append(RunResult(
            task_id=d["task_id"], architecture=d["architecture"], seed=d["seed"],
            final_solution="", verification=v, usages=usages,
            wall_clock_seconds=d.get("wall_clock_seconds", 0.0),
            iterations_used=d.get("iterations_used", 0),
            rerun_count=d.get("rerun_count", 0),
            routed_external=d.get("routed_external", False),
            extra=d.get("extra", {}),
        ))
    return out


# ---------------------------------------------------------------------------
def align_pairs(
    results_a: Sequence[RunResult],
    results_b: Sequence[RunResult],
    *,
    metric_a, metric_b,
) -> tuple[list[float], list[float]]:
    """Match by (task_id, seed) and return aligned metric arrays."""
    key_a = {(r.task_id, r.seed): r for r in results_a}
    pairs_a, pairs_b = [], []
    for rb in results_b:
        ra = key_a.get((rb.task_id, rb.seed))
        if ra is None:
            continue
        pairs_a.append(metric_a(ra))
        pairs_b.append(metric_b(rb))
    return pairs_a, pairs_b


# ---------------------------------------------------------------------------
def summary_table(summaries: Iterable[Summary], *, title: str = "Per-architecture summary") -> Table:
    table = Table(title=title, show_lines=False, header_style="bold cyan")
    table.add_column("Architecture", style="bold")
    table.add_column("n", justify="right")
    table.add_column("pass@1", justify="right")
    table.add_column("VCR", justify="right")
    table.add_column("MAS_i", justify="right")
    table.add_column("tokens/task", justify="right")
    table.add_column("input/output", justify="right")
    table.add_column("USD/task", justify="right")
    table.add_column("RUB/task", justify="right")
    table.add_column("U_tok (Q/Ktok)", justify="right")
    table.add_column("Q$ (per USD)", justify="right")
    table.add_column("latency (s)", justify="right")
    table.add_column("iters", justify="right")
    for s in summaries:
        table.add_row(
            s.architecture,
            str(s.n),
            f"{s.pass_at_1:.3f}",
            f"{s.vcr:.3f}",
            f"{s.mas:.3f}",
            f"{s.mean_tokens:.0f}",
            f"{s.mean_input_tokens:.0f}/{s.mean_output_tokens:.0f}",
            f"${s.mean_cost_usd:.5f}",
            f"₽{s.mean_cost_rub:.2f}",
            f"{s.utok_per_kilo:.4f}",
            f"{s.q_per_dollar:.2f}",
            f"{s.mean_latency_seconds:.2f}",
            f"{s.mean_iterations:.2f}",
        )
    return table


# ---------------------------------------------------------------------------
def latency_breakdown_by_role(results: Sequence[RunResult]) -> dict[str, dict[str, float]]:
    bucket: dict[str, list[float]] = {}
    for r in results:
        for u in r.usages:
            bucket.setdefault(u.role, []).append(u.total_tokens)
    return {role: {"mean_tokens": (sum(v) / len(v)) if v else 0.0,
                   "n_calls": len(v)} for role, v in bucket.items()}
