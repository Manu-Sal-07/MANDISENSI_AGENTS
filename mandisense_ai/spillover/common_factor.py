"""
Common-factor removal.

The central identification problem for cross-commodity spillover is that most
observed co-movement is *not* spillover. Monsoon strength, diesel prices,
festival demand and national policy move every commodity at once. A model that
reports raw co-movement as "spillover" is really reporting "it rained".

This module estimates a single common market factor as the first principal
component of standardised returns, then removes each commodity's exposure to
it. What remains - the idiosyncratic return - is the only place a genuine
commodity-to-commodity transmission can live.

Optionally removes calendar-month means as well, so that harvest cycles that
happen to align across commodities are not read as transmission either.

Leave-one-out estimation
------------------------
Removing a common component from k series mechanically induces negative
correlation among the residuals - roughly -1/(k-1), which is -0.25 at k=5.
This is a property of the projection, not a market fact, and it is large
enough to be worth stating plainly.

The engine estimates the factor for commodity j from the other k-1 commodities
so that j's own noise never enters the factor used to clean j. Measurement
shows this **reduces but does not remove** the effect: each residual still
carries the other series' noise through the shared factor. No projection-based
method escapes this entirely; the bias shrinks as k grows, which is a concrete
argument for widening the commodity panel.

Two things keep it from contaminating published edges. First, the estimator
measures *forward* windows from a shock onset, whereas the induced correlation
is contemporaneous. Second, and decisively, the build is validated by a
permutation placebo (see ``spillover.validate``) that re-runs the entire
pipeline on randomised shock dates; if the machinery manufactured edges from
this artifact, the placebo would show it.

Implementation note: PCA is computed via SVD on the standardised matrix rather
than an eigendecomposition of the covariance matrix, which is the numerically
stable route and avoids a scikit-learn dependency in the estimation path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.spillover.config import SpilloverConfig, DEFAULT_CONFIG
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CommonFactorResult:
    """Outcome of the decomposition."""

    residuals: pd.DataFrame
    """Idiosyncratic returns: what spillover estimation operates on."""

    factor: Optional[pd.Series]
    """The estimated common market factor (None if removal disabled)."""

    loadings: Dict[str, float]
    """Each commodity's beta on the common factor."""

    variance_explained: float
    """Share of panel variance absorbed by the common factor."""

    seasonality_removed: bool

    leave_one_out: bool = False
    """Whether each commodity was cleaned with a factor excluding itself."""

    def as_dict(self) -> Dict:
        return {
            "loadings": {k: round(v, 6) for k, v in self.loadings.items()},
            "variance_explained": round(self.variance_explained, 6),
            "seasonality_removed": self.seasonality_removed,
            "factor_removed": self.factor is not None,
            "leave_one_out": self.leave_one_out,
            "mechanical_residual_correlation": (
                0.0
                if self.leave_one_out or self.factor is None
                else round(-1.0 / max(1, len(self.loadings) - 1), 6)
            ),
        }


def _remove_monthly_seasonality(returns: pd.DataFrame) -> pd.DataFrame:
    """Subtract each commodity's calendar-month mean return."""
    out = returns.copy()
    months = out.index.month
    for column in out.columns:
        monthly_mean = out[column].groupby(months).transform("mean")
        out[column] = out[column] - monthly_mean
    return out


def _first_principal_component(frame: pd.DataFrame) -> np.ndarray:
    """
    First principal component scores of a standardised frame.

    Returns scores in standardised units, aligned to ``frame``'s rows.
    """
    means = frame.mean()
    stds = frame.std(ddof=0).replace(0.0, np.nan)
    if stds.isna().any():
        dead = list(stds[stds.isna()].index)
        raise ValueError(f"Zero-variance commodities cannot be decomposed: {dead}")

    standardised = ((frame - means) / stds).to_numpy(dtype=float)
    u, s, _ = np.linalg.svd(standardised, full_matrices=False)
    return u[:, 0] * s[0]


def _project_out(y: np.ndarray, factor: np.ndarray) -> Tuple[np.ndarray, float]:
    """Remove a series' exposure to a factor. Returns (residual, beta)."""
    denominator = float(np.dot(factor, factor))
    beta = float(np.dot(y, factor) / denominator) if denominator > 0 else 0.0
    return y - beta * factor, beta


def decompose(
    returns: pd.DataFrame,
    config: SpilloverConfig = DEFAULT_CONFIG,
) -> CommonFactorResult:
    """
    Split returns into a common factor and idiosyncratic residuals.

    Args:
        returns: period x commodity log returns. NaNs are dropped rowwise.
        config: build configuration.

    Returns:
        A :class:`CommonFactorResult`. When common-factor removal is disabled
        the residuals are the (optionally deseasonalised) input returns.
    """
    clean = returns.dropna(how="any")
    if clean.empty:
        raise ValueError("Cannot decompose an empty return panel")

    working = _remove_monthly_seasonality(clean) if config.remove_seasonality else clean.copy()

    if not config.remove_common_factor:
        return CommonFactorResult(
            residuals=working,
            factor=None,
            loadings={c: 0.0 for c in working.columns},
            variance_explained=0.0,
            seasonality_removed=config.remove_seasonality,
        )

    # Panel-wide factor, reported for diagnostics and used as the fallback when
    # the panel is too narrow for a leave-one-out construction.
    means = working.mean()
    stds = working.std(ddof=0).replace(0.0, np.nan)
    if stds.isna().any():
        # A zero-variance column carries no information and would produce a
        # divide-by-zero in standardisation.
        dead = list(stds[stds.isna()].index)
        raise ValueError(f"Zero-variance commodities cannot be decomposed: {dead}")

    standardised = ((working - means) / stds).to_numpy(dtype=float)
    _, singular_values, _ = np.linalg.svd(standardised, full_matrices=False)
    total_variance = float((singular_values ** 2).sum())
    variance_explained = (
        float((singular_values[0] ** 2) / total_variance) if total_variance > 0 else 0.0
    )

    panel_factor = _first_principal_component(working)
    factor = pd.Series(panel_factor, index=working.index, name="common_factor")

    # Leave-one-out requires at least three commodities: with two, dropping the
    # target leaves a single series, which is not a common factor in any
    # meaningful sense.
    use_leave_one_out = working.shape[1] >= 3

    residuals = pd.DataFrame(index=working.index, columns=working.columns, dtype=float)
    loadings: Dict[str, float] = {}

    for column in working.columns:
        y = working[column].to_numpy(dtype=float)
        if use_leave_one_out:
            others = working.drop(columns=[column])
            column_factor = _first_principal_component(others)
        else:
            column_factor = panel_factor

        residual, beta = _project_out(y, column_factor)
        residuals[column] = residual
        loadings[column] = beta

    logger.info(
        "Common factor explains %.1f%% of panel variance (leave_one_out=%s); loadings=%s",
        variance_explained * 100.0,
        use_leave_one_out,
        {k: round(v, 3) for k, v in loadings.items()},
    )

    return CommonFactorResult(
        residuals=residuals,
        factor=factor,
        loadings=loadings,
        variance_explained=variance_explained,
        seasonality_removed=config.remove_seasonality,
        leave_one_out=use_leave_one_out,
    )
