"""
Permutation placebo for the spillover pipeline.

Every step of this engine - common-factor removal, episode clustering, forward
windows, block bootstrap, FDR - is designed to avoid manufacturing signal. This
module checks that claim empirically instead of trusting it.

Method: keep the price panel, the residualisation and the number of shock
episodes exactly as they are, but move the shock dates to random positions.
Under randomised dates no genuine transmission can exist, so any edge the
pipeline still calls SIGNIFICANT is a false positive. Repeating this many times
gives a measured false-discovery rate for the pipeline as a whole.

Interpretation: the observed count of real edges must stand well clear of the
placebo distribution. If a real build yields nine significant edges and the
placebo routinely yields eight, the feature is measuring its own machinery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from mandisense_ai.spillover.common_factor import decompose
from mandisense_ai.spillover.config import (
    DEFAULT_CONFIG,
    SHOCK_GLUT,
    SHOCK_SQUEEZE,
    SpilloverConfig,
)
from mandisense_ai.spillover.estimator import (
    STATUS_INSUFFICIENT,
    benjamini_hochberg,
    estimate_pair,
    peak_effect,
)
from mandisense_ai.spillover.events import ShockEpisodes, detect_episodes
from mandisense_ai.spillover.panel import build_panel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def _count_significant(
    residuals: pd.DataFrame,
    episodes_by_key: Dict[str, ShockEpisodes],
    commodities: List[str],
    config: SpilloverConfig,
    rng: np.random.Generator,
) -> int:
    """Run the estimation + FDR stack and count surviving edges."""
    candidate_p: List[float] = []
    candidate_ok: List[bool] = []

    for shock_type in (SHOCK_SQUEEZE, SHOCK_GLUT):
        for source in commodities:
            episodes = episodes_by_key.get(f"{source}:{shock_type}")
            if episodes is None or episodes.n_episodes < config.min_episodes:
                continue
            for target in commodities:
                if target == source:
                    continue
                effects = estimate_pair(residuals, source, target, episodes, config, rng)
                peak = peak_effect(effects)
                if peak is None or np.isnan(peak.elasticity):
                    continue
                if peak.status == STATUS_INSUFFICIENT:
                    continue
                candidate_p.append(peak.p_value)
                candidate_ok.append(peak.is_significant)

    if not candidate_p:
        return 0

    survives = benjamini_hochberg(candidate_p, config.fdr_level)
    return sum(1 for ok, keep in zip(candidate_ok, survives) if ok and keep)


def _randomise(
    episodes: ShockEpisodes,
    index: pd.DatetimeIndex,
    config: SpilloverConfig,
    rng: np.random.Generator,
) -> ShockEpisodes:
    """
    Place the same number of onsets at random positions.

    Onsets are drawn without replacement and are kept clear of the tail so that
    forward windows remain computable, matching the real estimator's behaviour.
    """
    usable = len(index) - max(config.horizons) - 1
    count = min(episodes.n_episodes, max(usable, 0))
    if count <= 0:
        return ShockEpisodes(episodes.commodity, episodes.shock_type, [])
    positions = rng.choice(usable, size=count, replace=False)
    return ShockEpisodes(
        episodes.commodity,
        episodes.shock_type,
        sorted(index[p] for p in positions),
    )


def run_placebo(
    processed_dir: Path,
    config: SpilloverConfig = DEFAULT_CONFIG,
    n_permutations: int = 100,
) -> Dict[str, Any]:
    """
    Compare the real number of significant edges with a placebo distribution.

    Args:
        processed_dir: directory of processed parquet datasets.
        config: build configuration; the placebo must use the same one as the
            real build or the comparison is meaningless.
        n_permutations: number of randomised repetitions.

    Returns:
        A diagnostic dict including the observed count, placebo percentiles and
        an empirical p-value for the observed count.
    """
    from mandisense_ai.spillover.build import build_spillover_matrix

    panel = build_panel(processed_dir, config)
    residuals = decompose(panel.returns, config).residuals
    real_episodes = detect_episodes(panel.regimes, config)

    # The observed count comes from the real build path rather than a
    # reimplementation, so the placebo can never be compared against a
    # subtly different estimator than the one that ships.
    observed = len(
        build_spillover_matrix(processed_dir, config, run_holdout=False).actionable_edges
    )

    rng = np.random.default_rng(config.random_seed)

    index = residuals.index
    placebo_counts: List[int] = []
    for iteration in range(n_permutations):
        shuffled = {
            key: _randomise(episodes, index, config, rng)
            for key, episodes in real_episodes.items()
        }
        placebo_counts.append(
            _count_significant(residuals, shuffled, panel.commodities, config, rng)
        )
        if (iteration + 1) % 25 == 0:
            logger.info("Placebo progress: %d/%d", iteration + 1, n_permutations)

    counts = np.asarray(placebo_counts, dtype=float)
    # Empirical p-value: how often chance alone matches the observed count.
    exceedances = int((counts >= observed).sum())
    empirical_p = (exceedances + 1) / (n_permutations + 1)

    return {
        "observed_significant_edges": observed,
        "n_permutations": n_permutations,
        "placebo_mean": round(float(counts.mean()), 3),
        "placebo_std": round(float(counts.std()), 3),
        "placebo_max": int(counts.max()),
        "placebo_p50": float(np.percentile(counts, 50)),
        "placebo_p95": float(np.percentile(counts, 95)),
        "empirical_p_value": round(empirical_p, 4),
        "verdict": (
            "PASS" if empirical_p <= 0.05 else "FAIL"
        ),
        "note": (
            "Placebo re-runs the full pipeline with shock dates randomised. "
            "The observed edge count must sit clearly above the placebo "
            "distribution; PASS means chance reproduced it in <=5% of runs."
        ),
    }
