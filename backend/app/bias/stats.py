"""Shared statistical helpers used across bias metrics.

Kept dependency-light (numpy/scipy/statsmodels) and explicit so every number is auditable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class ProportionTest:
    rate_a: float
    rate_b: float
    diff: float
    z: float
    p_value: float
    n_a: int
    n_b: int


def two_proportion_ztest(succ_a: int, n_a: int, succ_b: int, n_b: int) -> ProportionTest:
    """Two-sided two-proportion z-test for difference in rates."""
    if n_a == 0 or n_b == 0:
        return ProportionTest(0.0, 0.0, 0.0, 0.0, 1.0, n_a, n_b)
    p_a, p_b = succ_a / n_a, succ_b / n_b
    pooled = (succ_a + succ_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    if se == 0:
        return ProportionTest(p_a, p_b, p_a - p_b, 0.0, 1.0, n_a, n_b)
    z = (p_a - p_b) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return ProportionTest(round(p_a, 4), round(p_b, 4), round(p_a - p_b, 4),
                          round(z, 4), round(float(p), 6), n_a, n_b)


def mann_whitney(a: list[float], b: list[float]) -> tuple[float, float]:
    """Return (effect_size, p_value). Effect size = rank-biserial correlation."""
    if len(a) < 2 or len(b) < 2:
        return 0.0, 1.0
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rank_biserial = 1 - (2 * u) / (len(a) * len(b))
    return round(float(rank_biserial), 4), round(float(p), 6)


def cohens_d(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    a_arr, b_arr = np.asarray(a), np.asarray(b)
    pooled_sd = math.sqrt(
        ((len(a) - 1) * a_arr.var(ddof=1) + (len(b) - 1) * b_arr.var(ddof=1))
        / (len(a) + len(b) - 2)
    )
    if pooled_sd == 0:
        return 0.0
    return round(float((a_arr.mean() - b_arr.mean()) / pooled_sd), 4)


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[float]:
    """Return BH-adjusted q-values, same order as input. Robust to empty input."""
    if not p_values:
        return []
    from statsmodels.stats.multitest import multipletests

    _, q, _, _ = multipletests(p_values, alpha=alpha, method="fdr_bh")
    return [round(float(x), 6) for x in q]
