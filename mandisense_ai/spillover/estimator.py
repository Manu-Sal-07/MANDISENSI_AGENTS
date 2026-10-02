"""
Spillover effect estimation.

For each ordered pair (source, target), shock direction, and response horizon,
this module answers:

    When `source` enters a supply `shock_type`, what is `target`'s cumulative
    idiosyncratic return over the following `h` periods, relative to what it
    would normally have been?

The estimate is a difference in means: conditional response minus the
unconditional baseline over the same horizon, computed on common-factor-free
residual returns.

Inference is by **block bootstrap over episodes**, not over rows. Shock windows
overlap heavily and rows within an episode are strongly dependent, so row-level
standard errors understate uncertainty by roughly an order of magnitude.
Resampling whole episodes preserves that dependence structure. With typical
samples of 8-30 episodes the resulting intervals are wide - correctly so.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.spillover.config import DEFAULT_CONFIG, SpilloverConfig
from mandisense_ai.spillover.events import ShockEpisodes
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Publication states for an estimated edge.
STATUS_SIGNIFICANT = "SIGNIFICANT"
STATUS_INCONCLUSIVE = "INCONCLUSIVE"
STATUS_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class HorizonEffect:
    """Estimated response of one target at one horizon."""

    horizon: int
    elasticity: float
    ci_low: float
    ci_high: float
    baseline: float
    n_episodes: int
    status: str
    p_value: float = float("nan")
    """Two-sided bootstrap p-value for H0: effect == 0. Required for the
    false-discovery-rate correction applied across the full edge set."""

    @property
    def is_significant(self) -> bool:
        return self.status == STATUS_SIGNIFICANT

    def as_dict(self) -> Dict:
        return {
            "horizon": self.horizon,
            "elasticity": round(self.elasticity, 6),
            "ci_low": round(self.ci_low, 6),
            "ci_high": round(self.ci_high, 6),
            "baseline": round(self.baseline, 6),
            "n_episodes": self.n_episodes,
            "status": self.status,
            "p_value": (
                None if np.isnan(self.p_value) else round(float(self.p_value), 6)
            ),
        }


def _forward_cumulative_returns(residuals: pd.Series, horizon: int) -> pd.Series:
    """
    Cumulative residual return over the `horizon` periods *after* each period.

    Indexed at the observation point, so a value at time t describes the window
    (t, t+horizon]. Windows that would extend past the end of the sample are
    NaN, which keeps the estimator free of look-ahead padding.
    """
    forward = residuals.shift(-1).rolling(window=horizon, min_periods=horizon).sum()
    return forward.shift(-(horizon - 1))


def _episode_responses(
    forward: pd.Series,
    onsets: Sequence[pd.Timestamp],
) -> np.ndarray:
    """Collect one response value per episode, dropping truncated windows."""
    values = [forward.get(ts, np.nan) for ts in onsets]
    array = np.asarray(values, dtype=float)
    return array[~np.isnan(array)]


def _bootstrap_ci(
    responses: np.ndarray,
    baseline: float,
    config: SpilloverConfig,
    rng: np.random.Generator,
) -> Tuple[float, float, float]:
    """
    Percentile bootstrap CI and two-sided p-value for the mean effect,
    resampling whole episodes.

    Returns ``(ci_low, ci_high, p_value)``.
    """
    n = len(responses)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))

    draws = rng.integers(0, n, size=(config.bootstrap_iterations, n))
    means = responses[draws].mean(axis=1) - baseline

    alpha = 1.0 - config.confidence_level
    low = float(np.percentile(means, 100.0 * alpha / 2.0))
    high = float(np.percentile(means, 100.0 * (1.0 - alpha / 2.0)))

    # Two-sided bootstrap p-value: how much of the resampled distribution sits
    # on the opposite side of zero from the point estimate. The +1 correction
    # keeps p strictly positive, which matters because a reported p of exactly
    # zero would survive any FDR threshold on a finite number of resamples.
    iterations = len(means)
    tail = min(int((means <= 0).sum()), int((means >= 0).sum()))
    p_value = min(1.0, 2.0 * (tail + 1) / (iterations + 1))

    return (low, high, p_value)


def _classify(
    elasticity: float,
    ci_low: float,
    ci_high: float,
    n_episodes: int,
    config: SpilloverConfig,
) -> str:
    if n_episodes < config.min_episodes:
        return STATUS_INSUFFICIENT
    if abs(elasticity) < config.min_abs_elasticity:
        return STATUS_INCONCLUSIVE
    if config.require_ci_excludes_zero and not (ci_low > 0.0 or ci_high < 0.0):
        return STATUS_INCONCLUSIVE
    return STATUS_SIGNIFICANT


def estimate_pair(
    residuals: pd.DataFrame,
    source: str,
    target: str,
    episodes: ShockEpisodes,
    config: SpilloverConfig = DEFAULT_CONFIG,
    rng: Optional[np.random.Generator] = None,
) -> List[HorizonEffect]:
    """
    Estimate the response of ``target`` to shocks in ``source`` at every
    configured horizon.

    Args:
        residuals: idiosyncratic returns (period x commodity).
        source: commodity experiencing the shock.
        target: commodity whose response is measured.
        episodes: detected onsets for ``source``.
        config: build configuration.
        rng: random generator; supply one for reproducible bootstraps.

    Returns:
        One :class:`HorizonEffect` per horizon, in horizon order. An edge with
        too few episodes still returns effects, marked
        ``INSUFFICIENT_EVIDENCE``, so absence of evidence is visible in the
        artifact rather than silently omitted.
    """
    if rng is None:
        rng = np.random.default_rng(config.random_seed)

    if target not in residuals.columns:
        raise KeyError("Target commodity is not in the residual panel: " + repr(target))

    target_residuals = residuals[target]
    effects: List[HorizonEffect] = []

    for horizon in config.horizons:
        forward = _forward_cumulative_returns(target_residuals, horizon)
        responses = _episode_responses(forward, episodes.onsets)
        baseline = float(forward.mean(skipna=True))

        if len(responses) == 0 or np.isnan(baseline):
            effects.append(
                HorizonEffect(
                    horizon=horizon,
                    elasticity=float("nan"),
                    ci_low=float("nan"),
                    ci_high=float("nan"),
                    baseline=0.0 if np.isnan(baseline) else baseline,
                    n_episodes=0,
                    status=STATUS_INSUFFICIENT,
                )
            )
            continue

        elasticity = float(responses.mean() - baseline)
        ci_low, ci_high, p_value = _bootstrap_ci(responses, baseline, config, rng)
        status = _classify(elasticity, ci_low, ci_high, len(responses), config)

        effects.append(
            HorizonEffect(
                horizon=horizon,
                elasticity=elasticity,
                ci_low=ci_low,
                ci_high=ci_high,
                baseline=baseline,
                n_episodes=int(len(responses)),
                status=status,
                p_value=p_value,
            )
        )

    logger.debug(
        "Estimated %s -> %s (%s): %d horizons from %d episodes",
        source,
        target,
        episodes.shock_type,
        len(effects),
        episodes.n_episodes,
    )

    return effects


def benjamini_hochberg(p_values: Sequence[float], fdr: float) -> List[bool]:
    """
    Benjamini-Hochberg step-up procedure for false discovery rate control.

    Why this is mandatory here: the engine tests every ordered commodity pair
    against every shock direction. With 5 commodities that is 40 simultaneous
    hypotheses, so at a nominal 10% level roughly 4 edges would clear the bar by
    chance alone even if no spillover existed anywhere. Publishing those as
    "significant" would be the single easiest way for this feature to mislead.

    Args:
        p_values: per-hypothesis p-values. NaN entries are treated as
            non-discoveries rather than dropped, so the returned list always
            aligns positionally with the input.
        fdr: target false discovery rate (e.g. 0.10).

    Returns:
        Booleans marking which hypotheses survive the correction, aligned to
        the input order.
    """
    n_total = len(p_values)
    if n_total == 0:
        return []

    indexed = [
        (i, p) for i, p in enumerate(p_values) if p is not None and not np.isnan(p)
    ]
    survives = [False] * n_total
    if not indexed:
        return survives

    indexed.sort(key=lambda pair: pair[1])
    m = len(indexed)

    # Largest rank k whose p-value clears (k/m) * fdr; everything at or below
    # that rank is a discovery.
    cutoff_rank = 0
    for rank, (_, p) in enumerate(indexed, start=1):
        if p <= (rank / m) * fdr:
            cutoff_rank = rank

    for rank, (original_index, _) in enumerate(indexed, start=1):
        if rank <= cutoff_rank:
            survives[original_index] = True

    return survives


def peak_effect(effects: Sequence[HorizonEffect]) -> Optional[HorizonEffect]:
    """
    The horizon carrying the strongest *credible* response.

    Significant horizons are always preferred over merely large ones, so a
    noisy point estimate at a long horizon cannot outrank a well-identified
    shorter one.
    """
    usable = [e for e in effects if not np.isnan(e.elasticity)]
    if not usable:
        return None
    significant = [e for e in usable if e.is_significant]
    pool = significant or usable
    return max(pool, key=lambda e: abs(e.elasticity))
