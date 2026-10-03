"""Core metric formulas (17)-(23) of Anonymous authors (2026).

Conventions:
    * `Q` (article §6.1) = pass@1 on a single dataset; on a heterogeneous
      dataset it becomes a class-weighted sum but here every experiment has
      a single class so Q == pass@1 == E[V(Y)].
    * `T` is the *mean* total tokens per task (so U_tok is per-task, not
      summed across the corpus); the article writes "качество на 1000 токенов"
      so we report U_tok in those units.
    * `C_inf` is per-task USD; `Q$` is "quality per dollar".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median, pstdev

from ..types import RunResult


@dataclass
class Summary:
    architecture: str
    n: int
    pass_at_1: float            # Q (formula context)
    mean_tokens: float          # T̄
    mean_input_tokens: float
    mean_output_tokens: float
    mean_cost_usd: float        # C̄_inf
    mean_cost_rub: float
    mean_latency_seconds: float
    mean_iterations: float
    mean_rerun_count: float
    routed_external_share: float
    mean_maintainability: float
    utok_per_kilo: float        # U_tok = Q / (T/1000)  (formula (17))
    q_per_dollar: float         # Q$ (formula (18))
    vcr: float                  # Verified Candidate Rate (formula (19))
    mas: float                  # MAS_i averaged (formula (20))
    extras: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-result helpers
# ---------------------------------------------------------------------------
def pass_at_1(results: list[RunResult]) -> float:
    if not results:
        return 0.0
    return sum(1.0 for r in results if r.passed) / len(results)


def compute_utok(results: list[RunResult]) -> float:
    """U_tok = Q / mean(T) per 1000 tokens (formula (17))."""
    if not results:
        return 0.0
    Q = pass_at_1(results)
    mean_T = mean(r.total_tokens for r in results) or 1
    return Q * 1000.0 / mean_T


def compute_q_dollar(results: list[RunResult]) -> float:
    if not results:
        return 0.0
    Q = pass_at_1(results)
    mean_C = mean(r.total_cost_usd for r in results) or 1e-12
    return Q / mean_C


def compute_vcr(results: list[RunResult]) -> float:
    """VCR = (1/N) Σ I[tests ∧ static ∧ security]  (formula (19))."""
    if not results:
        return 0.0
    return sum(
        1.0 for r in results
        if r.verification.tests_passed
        and r.verification.static_passed
        and r.verification.security_passed
    ) / len(results)


def compute_mas(results: list[RunResult], lam: float = 0.5) -> float:
    """MAS_i = min(Success_i, Verified_i) · M_i^λ  averaged across tasks (formula (20))."""
    if not results:
        return 0.0
    vals: list[float] = []
    for r in results:
        success = 1.0 if r.passed else 0.0
        verified = 1.0 if (r.verification.tests_passed and r.verification.static_passed) else 0.0
        M = max(0.0, min(1.0, r.verification.maintainability))
        vals.append(min(success, verified) * (M ** lam))
    return sum(vals) / len(vals)


# ---------------------------------------------------------------------------
# Aggregator used by every experiment
# ---------------------------------------------------------------------------
def summarize_runs(results: list[RunResult], *, lam: float = 0.5) -> Summary:
    if not results:
        return Summary(
            architecture="?", n=0, pass_at_1=0.0, mean_tokens=0.0,
            mean_input_tokens=0.0, mean_output_tokens=0.0, mean_cost_usd=0.0,
            mean_cost_rub=0.0,
            mean_latency_seconds=0.0, mean_iterations=0.0,
            mean_rerun_count=0.0, routed_external_share=0.0,
            mean_maintainability=0.0, utok_per_kilo=0.0, q_per_dollar=0.0,
            vcr=0.0, mas=0.0,
        )
    arch = results[0].architecture
    n = len(results)
    return Summary(
        architecture=arch,
        n=n,
        pass_at_1=pass_at_1(results),
        mean_tokens=mean(r.total_tokens for r in results),
        mean_input_tokens=mean(r.total_input_tokens for r in results),
        mean_output_tokens=mean(r.total_output_tokens for r in results),
        mean_cost_usd=mean(r.total_cost_usd for r in results),
        mean_cost_rub=mean(r.total_cost_rub for r in results),
        mean_latency_seconds=mean(r.wall_clock_seconds for r in results),
        mean_iterations=mean(r.iterations_used for r in results),
        mean_rerun_count=mean(r.rerun_count for r in results),
        routed_external_share=sum(1 for r in results if r.routed_external) / n,
        mean_maintainability=mean(r.verification.maintainability for r in results),
        utok_per_kilo=compute_utok(results),
        q_per_dollar=compute_q_dollar(results),
        vcr=compute_vcr(results),
        mas=compute_mas(results, lam=lam),
        extras={
            "tokens_std": pstdev(r.total_tokens for r in results) if n > 1 else 0.0,
            "tokens_median": median(r.total_tokens for r in results),
            "cost_std": pstdev(r.total_cost_usd for r in results) if n > 1 else 0.0,
            "cost_rub_std": pstdev(r.total_cost_rub for r in results) if n > 1 else 0.0,
        },
    )
