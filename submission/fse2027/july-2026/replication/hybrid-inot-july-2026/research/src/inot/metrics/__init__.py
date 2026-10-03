"""Metrics (formulas (17)-(23) of the article) and statistical tests (§7.1).

Public surface:
    summarize_runs(results)             -> Summary       (per-architecture stats)
    compute_utok(results, weights)      -> dict          (formula (17))
    compute_q_dollar(results)           -> dict          (formula (18))
    compute_vcr(results)                -> dict          (formula (19))
    compute_mas(results, weights, lam)  -> dict          (formula (20))
    pairwise_compare(a, b)              -> ComparisonRes (Wilcoxon + bootstrap)
    holm_bonferroni(pvalues)            -> list[bool]    (rejected? per hypothesis)
"""
from .core import (
    Summary,
    summarize_runs,
    compute_utok,
    compute_q_dollar,
    compute_vcr,
    compute_mas,
    pass_at_1,
)
from .stats import (
    ComparisonResult,
    pairwise_compare,
    holm_bonferroni,
    bootstrap_ci,
)

__all__ = [
    "Summary",
    "summarize_runs",
    "compute_utok",
    "compute_q_dollar",
    "compute_vcr",
    "compute_mas",
    "pass_at_1",
    "ComparisonResult",
    "pairwise_compare",
    "holm_bonferroni",
    "bootstrap_ci",
]
