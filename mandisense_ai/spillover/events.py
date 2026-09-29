"""
Shock event detection.

A spillover question is inherently conditional: "when commodity A is *hit*,
what happens to B?" That requires a defensible definition of "hit".

Rather than inventing one, this module reuses ``supply_regime`` - the supply
stress classification the preprocessing pipeline already computes from arrival
deviation, elasticity and supply momentum. Using an existing, independently
derived state variable avoids tuning a shock threshold until the results look
good.

Episode clustering is the load-bearing detail. A single onion squeeze can hold
the regime flag for many consecutive weeks. Counting each week as an event
would inflate the sample by an order of magnitude and shrink confidence
intervals to meaninglessness. Only *onsets*, separated by a minimum gap, count.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import pandas as pd

from mandisense_ai.spillover.config import (
    DEFAULT_CONFIG,
    GLUT_REGIMES,
    SHOCK_GLUT,
    SHOCK_SQUEEZE,
    SQUEEZE_REGIMES,
    SpilloverConfig,
)
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_REGIME_SETS: Dict[str, Sequence[str]] = {
    SHOCK_SQUEEZE: SQUEEZE_REGIMES,
    SHOCK_GLUT: GLUT_REGIMES,
}


@dataclass(frozen=True)
class ShockEpisodes:
    """Detected onsets for one (commodity, shock_type) pair."""

    commodity: str
    shock_type: str
    onsets: List[pd.Timestamp]

    @property
    def n_episodes(self) -> int:
        return len(self.onsets)

    def as_dict(self) -> Dict:
        return {
            "commodity": self.commodity,
            "shock_type": self.shock_type,
            "n_episodes": self.n_episodes,
            "onsets": [str(ts.date()) for ts in self.onsets],
        }


def _cluster_onsets(
    flagged: pd.Series,
    min_gap_periods: int,
) -> List[pd.Timestamp]:
    """
    Reduce a boolean regime series to independent episode onsets.

    An onset is a transition from not-in-regime to in-regime. Onsets within
    ``min_gap_periods`` of the previous accepted onset are folded into it, so a
    regime that flickers off and on again still counts once.
    """
    flagged = flagged.fillna(False).astype(bool)
    if not flagged.any():
        return []

    previous = flagged.shift(1, fill_value=False)
    transitions = flagged & ~previous

    positions = {ts: i for i, ts in enumerate(flagged.index)}
    accepted: List[pd.Timestamp] = []
    last_position = None

    for timestamp in flagged.index[transitions]:
        position = positions[timestamp]
        if last_position is not None and (position - last_position) < min_gap_periods:
            continue
        accepted.append(timestamp)
        last_position = position

    return accepted


def detect_episodes(
    regimes: pd.DataFrame,
    config: SpilloverConfig = DEFAULT_CONFIG,
) -> Dict[str, ShockEpisodes]:
    """
    Detect shock episodes for every commodity and shock direction.

    Args:
        regimes: period x commodity frame of ``supply_regime`` labels.
        config: build configuration.

    Returns:
        Mapping of ``"{commodity}:{shock_type}"`` to :class:`ShockEpisodes`.
        Commodities with no regime data yield empty episode lists rather than
        raising, so a partially instrumented panel still produces an artifact.
    """
    detected: Dict[str, ShockEpisodes] = {}

    if regimes.empty:
        logger.warning("No supply_regime data available; no episodes detected")
        return detected

    for commodity in regimes.columns:
        series = regimes[commodity]
        for shock_type, labels in _REGIME_SETS.items():
            flagged = series.isin(labels)
            onsets = _cluster_onsets(flagged, config.min_gap_periods)
            key = f"{commodity}:{shock_type}"
            detected[key] = ShockEpisodes(
                commodity=commodity,
                shock_type=shock_type,
                onsets=onsets,
            )
            logger.debug(
                "%s %s: %d flagged periods -> %d independent episodes",
                commodity,
                shock_type,
                int(flagged.sum()),
                len(onsets),
            )

    return detected
