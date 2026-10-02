"""
Configuration for the cross-commodity spillover engine.

Every threshold that affects a published number lives here so the artifact
can record exactly which configuration produced it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple

# Regime labels emitted by the preprocessing pipeline (supply_regime column).
SQUEEZE_REGIMES: Tuple[str, ...] = ("squeeze", "squeeze_accelerating")
GLUT_REGIMES: Tuple[str, ...] = ("glut", "glut_accelerating")

# Shock direction identifiers used throughout the engine and the artifact.
SHOCK_SQUEEZE = "SQUEEZE"
SHOCK_GLUT = "GLUT"


@dataclass(frozen=True)
class SpilloverConfig:
    """Immutable configuration for a spillover build."""

    # --- Panel construction -------------------------------------------------
    frequency: str = "W"
    """Resample frequency. Weekly is the shortest interval at which every
    commodity in the panel reliably has an observation."""

    min_overlap_periods: int = 104
    """Minimum number of jointly-observed periods (2 years weekly) required
    before any estimation is attempted."""

    # --- Common factor ------------------------------------------------------
    remove_common_factor: bool = True
    """Strip the first principal component of returns. Without this, shared
    supply shocks (monsoon, fuel, festival demand) masquerade as spillover."""

    remove_seasonality: bool = True
    """Remove each commodity's calendar-month mean return, so harvest cycles
    are not mistaken for cross-commodity transmission."""

    # --- Event detection ----------------------------------------------------
    horizons: Tuple[int, ...] = (1, 2, 3, 4)
    """Response horizons in panel periods (weeks) measured after shock onset."""

    min_gap_periods: int = 4
    """Consecutive onsets closer together than this are treated as one
    episode. Prevents a single multi-week event counting many times."""

    # --- Inference ----------------------------------------------------------
    min_episodes: int = 8
    """Evidence floor. Below this an edge is published as INSUFFICIENT_EVIDENCE
    rather than as a number that looks authoritative but is not."""

    bootstrap_iterations: int = 2000
    confidence_level: float = 0.90
    random_seed: int = 20260916
    """Fixed so a rebuild on unchanged data reproduces the artifact exactly."""

    # --- Publication gates --------------------------------------------------
    min_abs_elasticity: float = 0.01
    """Effects smaller than 1% are economically meaningless here; they are
    reported but never marked significant."""

    require_ci_excludes_zero: bool = True
    """An edge is only SIGNIFICANT if its bootstrap CI excludes zero."""

    fdr_level: float = 0.10
    """Target false discovery rate for the Benjamini-Hochberg correction
    applied across all edges. The engine tests every ordered pair against every
    shock direction simultaneously, so without this roughly one in ten edges
    would clear a nominal 90% interval by chance alone."""

    apply_fdr_correction: bool = True
    """Disable only for diagnostics. Publishing uncorrected edges from a
    simultaneous test of this size is not defensible."""

    # --- Holdout validation -------------------------------------------------
    holdout_fraction: float = 0.30
    """Trailing share of the panel reserved for out-of-sample sign agreement."""

    def as_dict(self) -> Dict:
        payload = asdict(self)
        payload["horizons"] = list(self.horizons)
        return payload


DEFAULT_CONFIG = SpilloverConfig()
