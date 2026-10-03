import math

from inot.metrics.core import compute_mas, compute_q_dollar, compute_utok, summarize_runs
from inot.metrics.stats import bootstrap_ci, holm_bonferroni, mcnemar_paired, pairwise_compare
from inot.types import RunResult, TokenUsage, VerificationResult


def _run(task_id: str, passed: bool, tokens: int, cost: float, maintainability: float = 1.0) -> RunResult:
    return RunResult(
        task_id=task_id,
        architecture="B-test",
        seed=42,
        final_solution="def f(): return 1",
        verification=VerificationResult(
            passed=passed,
            tests_passed=passed,
            static_passed=True,
            security_passed=True,
            maintainability=maintainability,
        ),
        usages=[
            TokenUsage(
                model="test/model",
                input_tokens=tokens // 2,
                output_tokens=tokens - tokens // 2,
                cost_usd=cost,
            )
        ],
        wall_clock_seconds=0.5,
    )


def test_core_metrics_match_article_formulas():
    runs = [
        _run("a", True, tokens=1000, cost=0.01, maintainability=1.0),
        _run("b", False, tokens=3000, cost=0.03, maintainability=0.5),
    ]

    assert compute_utok(runs) == 0.25
    assert compute_q_dollar(runs) == 25.0
    assert compute_mas(runs, lam=0.5) == 0.5

    summary = summarize_runs(runs, lam=0.5)
    assert summary.pass_at_1 == 0.5
    assert summary.mean_tokens == 2000
    assert summary.mean_cost_rub == 0.0
    assert summary.utok_per_kilo == 0.25
    assert summary.q_per_dollar == 25.0


def test_holm_bonferroni_preserves_input_order():
    rejected = holm_bonferroni([0.06, 0.001, 0.02], alpha=0.05)
    assert rejected == [False, True, True]


def test_pairwise_compare_reports_positive_mean_difference():
    result = pairwise_compare([4, 5, 6, 7], [1, 2, 3, 4], bootstrap_resamples=200, seed=1)
    assert result.n == 4
    assert result.diff_mean == 3.0
    assert result.test == "wilcoxon-signed-rank"
    assert result.bootstrap_ci_low <= result.diff_mean <= result.bootstrap_ci_high


def test_bootstrap_ci_handles_empty_and_constant_samples():
    assert bootstrap_ci([], resamples=10) == (0.0, 0.0)
    lo, hi = bootstrap_ci([2, 2, 2], resamples=50, seed=7)
    assert math.isclose(lo, 2.0)
    assert math.isclose(hi, 2.0)


def test_mcnemar_paired_counts_discordant_pairs():
    chi2, p = mcnemar_paired([1, 1, 0, 0], [1, 0, 1, 1])
    assert chi2 == 0.0
    assert 0.0 <= p <= 1.0
