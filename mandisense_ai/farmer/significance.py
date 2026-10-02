"""
The significance tests the farmer app's "earned call" rule rests on.

A sell/hold call is issued for a crop and district only if its out-of-sample
improvement over "the price will not change" survives a formal test *and* a
correction for having tested every series. These are the same estimators the
research papers use (Diebold-Mariano with the Harvey-Leybourne-Newbold small-
sample correction and Newey-West variance; Holm's step-down adjustment), kept
here so the deployed rule and the published evidence cannot drift apart.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def newey_west_var(d: np.ndarray, lag: int) -> float:
    d = d - d.mean()
    n = len(d)
    v = d @ d / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (d[k:] @ d[:-k]) / n
    return float(v)


def dm_test(loss_baseline, loss_model, dates, horizon: int):
    """HLN-corrected Diebold-Mariano test on the date-averaged loss difference.

    Averaging over dates first matters: several series share a date, and
    treating their errors as independent would overstate the evidence.
    Positive statistic: the model's loss is lower than the baseline's.
    Returns (statistic, two-sided p, number of dates)."""
    d = (
        pd.Series(np.asarray(loss_baseline) - np.asarray(loss_model))
        .groupby(np.asarray(dates)).mean().sort_index().to_numpy()
    )
    n = len(d)
    v = newey_west_var(d, max(horizon, 1))
    if v <= 0 or n < 10:
        return 0.0, 1.0, n
    stat = d.mean() / np.sqrt(v / n) * np.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
    return float(stat), float(2 * stats.t.sf(abs(stat), n - 1)), n


def holm(pvalues) -> np.ndarray:
    """Holm's step-down adjustment: controls the chance of *any* false claim
    across all the series tested, not just each one alone."""
    p = np.asarray(pvalues, float)
    order = np.argsort(p)
    adjusted = np.empty(len(p))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adjusted[i] = min(1.0, running)
    return adjusted
