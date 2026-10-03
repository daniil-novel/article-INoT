"""Statistical tests prescribed in §3.2 / §7.1 of the article:

* Wilcoxon signed-rank (paired, non-parametric) for matched samples.
* Bootstrap percentile CI (10⁴ resamples by default) for any statistic.
* Holm–Bonferroni correction for family-wise error rate when several H1
  comparisons are made simultaneously.
* McNemar for paired binary outcomes (pass/fail), used by E1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from scipy import stats


@dataclass
class ComparisonResult:
    label: str
    n: int
    statistic: float
    p_value: float
    diff_mean: float
    diff_median: float
    bootstrap_ci_low: float
    bootstrap_ci_high: float
    test: str

    def is_significant(self, alpha: float = 0.05) -> bool:
        return self.p_value < alpha


# ---------------------------------------------------------------------------
# Wilcoxon signed-rank for paired continuous metrics (§3.2 cite)
# ---------------------------------------------------------------------------
def pairwise_compare(
    a: Sequence[float],
    b: Sequence[float],
    *,
    label: str = "",
    bootstrap_resamples: int = 10_000,
    ci_level: float = 0.95,
    seed: int = 12345,
) -> ComparisonResult:
    """Paired comparison: returns Wilcoxon-test result + bootstrap CI on (a-b).

    Both arrays must be aligned by task index. NaNs are dropped pairwise.
    """
    arr_a = np.asarray(a, dtype=float)
    arr_b = np.asarray(b, dtype=float)
    if arr_a.shape != arr_b.shape:
        raise ValueError(f"shape mismatch: {arr_a.shape} vs {arr_b.shape}")
    mask = ~(np.isnan(arr_a) | np.isnan(arr_b))
    arr_a, arr_b = arr_a[mask], arr_b[mask]
    n = len(arr_a)
    if n < 2:
        return ComparisonResult(label=label, n=n, statistic=float("nan"), p_value=1.0,
                                diff_mean=0.0, diff_median=0.0,
                                bootstrap_ci_low=0.0, bootstrap_ci_high=0.0,
                                test="insufficient-data")

    diffs = arr_a - arr_b
    if np.allclose(diffs, 0):
        return ComparisonResult(label=label, n=n, statistic=0.0, p_value=1.0,
                                diff_mean=0.0, diff_median=0.0,
                                bootstrap_ci_low=0.0, bootstrap_ci_high=0.0,
                                test="wilcoxon-zero-diff")

    try:
        wstat, p = stats.wilcoxon(arr_a, arr_b, zero_method="wilcox", alternative="two-sided")
    except ValueError:
        wstat, p = float("nan"), 1.0
    lo, hi = bootstrap_ci(diffs, statistic=np.mean,
                          resamples=bootstrap_resamples, ci_level=ci_level, seed=seed)
    return ComparisonResult(
        label=label, n=n,
        statistic=float(wstat), p_value=float(p),
        diff_mean=float(np.mean(diffs)),
        diff_median=float(np.median(diffs)),
        bootstrap_ci_low=lo, bootstrap_ci_high=hi,
        test="wilcoxon-signed-rank",
    )


# ---------------------------------------------------------------------------
# Bootstrap percentile CI (§7.1)
# ---------------------------------------------------------------------------
def bootstrap_ci(
    data: Sequence[float],
    *,
    statistic: Callable[[np.ndarray], float] = np.mean,
    resamples: int = 10_000,
    ci_level: float = 0.95,
    seed: int = 12345,
) -> tuple[float, float]:
    arr = np.asarray(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(resamples, len(arr)))
    samples = arr[idx]
    stat_values = np.apply_along_axis(statistic, 1, samples)
    alpha = (1.0 - ci_level) / 2.0
    lo, hi = np.quantile(stat_values, [alpha, 1.0 - alpha])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Holm–Bonferroni FWER correction (§3.2)
# ---------------------------------------------------------------------------
def holm_bonferroni(pvalues: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Returns rejection mask, ordered to match the input ``pvalues``.

    Implements the classic Holm step-down: with sorted p_(1) <= ... <= p_(m),
    reject the k-th hypothesis iff p_(k) <= alpha / (m - k + 1).
    """
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    rejected = [False] * m
    for k, idx in enumerate(order):
        threshold = alpha / (m - k)
        if pvalues[idx] <= threshold:
            rejected[idx] = True
        else:
            break
    return rejected


# ---------------------------------------------------------------------------
# McNemar for paired binary outcomes (used in E1 for pass/fail)
# ---------------------------------------------------------------------------
def mcnemar_paired(a: Sequence[int], b: Sequence[int]) -> tuple[float, float]:
    """Returns (chi-square statistic with continuity correction, p-value)."""
    arr_a = np.asarray(a, dtype=int)
    arr_b = np.asarray(b, dtype=int)
    b01 = int(np.sum((arr_a == 0) & (arr_b == 1)))
    b10 = int(np.sum((arr_a == 1) & (arr_b == 0)))
    if b01 + b10 == 0:
        return 0.0, 1.0
    chi2 = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)
    p = 1 - stats.chi2.cdf(chi2, df=1)
    return float(chi2), float(p)
