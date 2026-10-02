"""
Spillover matrix build orchestration.

Runs the full offline pipeline:

    processed parquets
      -> aligned weekly panel
      -> common-factor / seasonality removal
      -> regime-based shock episode detection
      -> per-pair event study with episode block bootstrap
      -> holdout sign-agreement check
      -> versioned SpilloverMatrix artifact

This is an **offline** build. Nothing here runs inside a request. The API only
ever reads the artifact this module produces.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from mandisense_ai.spillover.common_factor import decompose
from mandisense_ai.spillover.config import (
    DEFAULT_CONFIG,
    SHOCK_GLUT,
    SHOCK_SQUEEZE,
    SpilloverConfig,
)
from mandisense_ai.spillover.estimator import (
    STATUS_INCONCLUSIVE,
    STATUS_INSUFFICIENT,
    STATUS_SIGNIFICANT,
    HorizonEffect,
    benjamini_hochberg,
    estimate_pair,
    peak_effect,
)
from mandisense_ai.spillover.events import detect_episodes
from mandisense_ai.spillover.matrix import SpilloverEdge, SpilloverMatrix
from mandisense_ai.spillover.panel import CommodityPanel, build_panel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def _half_life(effects: List[HorizonEffect], peak: Optional[HorizonEffect]) -> Optional[float]:
    """
    Periods after the peak at which the response decays to half its magnitude.

    Returned as a linear interpolation between bracketing horizons. ``None``
    when the effect has not halved within the estimated window, which is itself
    informative: the signal outlives the horizons we measured.
    """
    if peak is None or peak.elasticity == 0 or math.isnan(peak.elasticity):
        return None

    target = abs(peak.elasticity) / 2.0
    after = [e for e in effects if e.horizon > peak.horizon and not math.isnan(e.elasticity)]
    previous = peak

    for effect in sorted(after, key=lambda e: e.horizon):
        if abs(effect.elasticity) <= target:
            span = effect.horizon - previous.horizon
            drop = abs(previous.elasticity) - abs(effect.elasticity)
            if drop <= 0:
                return float(effect.horizon - peak.horizon)
            fraction = (abs(previous.elasticity) - target) / drop
            crossing = previous.horizon + fraction * span
            return float(max(0.0, crossing - peak.horizon))
        previous = effect

    return None


def _holdout_agreement(
    panel: CommodityPanel,
    config: SpilloverConfig,
) -> Dict[str, object]:
    """
    Out-of-sample sanity check.

    Re-estimates every edge on the leading (1 - holdout_fraction) of the panel
    and reports how often the sign of the in-sample peak effect is reproduced
    on the held-out tail.

    Interpretation requires care, which is why two figures are reported. Shock
    episodes are rare, so a 30% tail typically contains only a handful per
    commodity. A pair with two test episodes produces an essentially random
    sign, and pooling those with well-evidenced pairs drags the headline number
    toward 50% regardless of whether the underlying edges are real. The
    ``powered_*`` figures therefore restrict the comparison to pairs that clear
    the episode floor on *both* sides of the split; the ``raw_*`` figures keep
    every pair for transparency. Neither gates publication - with samples this
    size that would amount to tuning on the holdout - but both are recorded in
    the artifact so the evidence is visible rather than implied.
    """
    n = panel.n_periods
    split = int(n * (1.0 - config.holdout_fraction))
    if split < config.min_overlap_periods // 2:
        return {"status": "SKIPPED", "reason": "panel too short to split"}

    index = panel.prices.index
    train_returns = panel.returns.loc[index[:split]]
    test_returns = panel.returns.loc[index[split:]]
    train_regimes = panel.regimes.loc[index[:split]]
    test_regimes = panel.regimes.loc[index[split:]]

    try:
        train_residuals = decompose(train_returns, config).residuals
        test_residuals = decompose(test_returns, config).residuals
    except ValueError as exc:
        return {"status": "SKIPPED", "reason": str(exc)}

    train_episodes = detect_episodes(train_regimes, config)
    test_episodes = detect_episodes(test_regimes, config)

    raw_agree = raw_compared = 0
    powered_agree = powered_compared = 0
    rng = np.random.default_rng(config.random_seed)

    for key, train_ep in train_episodes.items():
        source = train_ep.commodity
        test_ep = test_episodes.get(key)
        if test_ep is None or test_ep.n_episodes == 0 or train_ep.n_episodes == 0:
            continue

        well_powered = (
            train_ep.n_episodes >= config.min_episodes
            and test_ep.n_episodes >= config.min_episodes
        )

        for target in panel.commodities:
            if target == source or target not in train_residuals.columns:
                continue
            train_peak = peak_effect(
                estimate_pair(train_residuals, source, target, train_ep, config, rng)
            )
            test_peak = peak_effect(
                estimate_pair(test_residuals, source, target, test_ep, config, rng)
            )
            if train_peak is None or test_peak is None:
                continue
            if math.isnan(train_peak.elasticity) or math.isnan(test_peak.elasticity):
                continue

            matched = np.sign(train_peak.elasticity) == np.sign(test_peak.elasticity)
            raw_compared += 1
            raw_agree += int(matched)
            if well_powered:
                powered_compared += 1
                powered_agree += int(matched)

    test_episode_counts = {k: v.n_episodes for k, v in sorted(test_episodes.items())}

    return {
        "status": "OK",
        "train_periods": int(split),
        "test_periods": int(n - split),
        "raw_pairs_compared": raw_compared,
        "raw_sign_agreement": (
            round(raw_agree / raw_compared, 4) if raw_compared else None
        ),
        "powered_pairs_compared": powered_compared,
        "powered_sign_agreement": (
            round(powered_agree / powered_compared, 4) if powered_compared else None
        ),
        "min_episodes_for_powered": config.min_episodes,
        "test_episodes_by_pair": test_episode_counts,
        "note": (
            "Sign agreement between in-sample and held-out estimates. "
            "'powered' restricts to pairs clearing the episode floor on both "
            "sides of the split; 'raw' includes every pair and is dominated by "
            "pairs with too few test episodes to carry a meaningful sign. "
            "Diagnostic only; does not gate edge publication."
        ),
    }


def _apply_fdr(
    edges: List[SpilloverEdge],
    config: SpilloverConfig,
) -> List[SpilloverEdge]:
    """
    Apply Benjamini-Hochberg false discovery rate control across all edges.

    Each edge contributes one hypothesis: the p-value of its peak horizon. An
    edge whose peak does not survive the correction is downgraded from
    SIGNIFICANT to INCONCLUSIVE - the point estimate and interval are retained
    so the evidence remains inspectable, but the edge stops being actionable.

    The testing family is **every edge on which a test was actually run**, not
    just the ones that already cleared their interval. Restricting the family
    to prior winners would be selecting on the outcome and then correcting
    within the selected set, which is circular and leaves the correction with
    almost no power to reject anything.

    Edges marked INSUFFICIENT_EVIDENCE are the one legitimate exclusion: they
    were never tested, having failed the episode floor before inference ran.
    """
    if not config.apply_fdr_correction:
        return edges

    family = [
        i for i, edge in enumerate(edges) if edge.status != STATUS_INSUFFICIENT
    ]
    if not family:
        return edges

    p_values: List[float] = []
    for index in family:
        edge = edges[index]
        peak = next(
            (e for e in edge.effects if e.horizon == edge.peak_horizon),
            None,
        )
        p_values.append(peak.p_value if peak is not None else float("nan"))

    survives = benjamini_hochberg(p_values, config.fdr_level)

    corrected = list(edges)
    demoted = 0
    for position, index in enumerate(family):
        edge = corrected[index]
        # Only SIGNIFICANT edges can be demoted; the rest are in the family
        # purely to size the correction correctly.
        if edge.status != STATUS_SIGNIFICANT or survives[position]:
            continue
        corrected[index] = SpilloverEdge(
            source=edge.source,
            target=edge.target,
            shock_type=edge.shock_type,
            effects=edge.effects,
            peak_horizon=edge.peak_horizon,
            peak_elasticity=edge.peak_elasticity,
            status=STATUS_INCONCLUSIVE,
            n_episodes=edge.n_episodes,
            half_life_periods=edge.half_life_periods,
        )
        demoted += 1

    logger.info(
        "FDR correction at q=%.2f over a family of %d tested edges: "
        "%d demoted from SIGNIFICANT to INCONCLUSIVE",
        config.fdr_level,
        len(family),
        demoted,
    )
    return corrected


def build_spillover_matrix(
    processed_dir: Path,
    config: SpilloverConfig = DEFAULT_CONFIG,
    run_holdout: bool = True,
) -> SpilloverMatrix:
    """
    Build the spillover matrix from processed market data.

    Args:
        processed_dir: directory containing the processed parquet datasets.
        config: build configuration.
        run_holdout: whether to compute the out-of-sample diagnostic.

    Returns:
        A fully populated :class:`SpilloverMatrix` (not yet written to disk).

    Raises:
        ValueError: if the panel cannot support estimation at all. Callers
            building artifacts should let this propagate - a silent empty
            matrix is worse than a failed build.
    """
    logger.info("Building spillover matrix from %s", processed_dir)

    panel = build_panel(processed_dir, config)
    decomposition = decompose(panel.returns, config)
    residuals = decomposition.residuals
    episodes = detect_episodes(panel.regimes, config)

    rng = np.random.default_rng(config.random_seed)
    edges: List[SpilloverEdge] = []

    for shock_type in (SHOCK_SQUEEZE, SHOCK_GLUT):
        for source in panel.commodities:
            source_episodes = episodes.get(f"{source}:{shock_type}")
            if source_episodes is None:
                continue

            for target in panel.commodities:
                if target == source:
                    continue

                effects = estimate_pair(
                    residuals, source, target, source_episodes, config, rng
                )
                peak = peak_effect(effects)

                if source_episodes.n_episodes < config.min_episodes:
                    status = STATUS_INSUFFICIENT
                elif peak is not None and peak.is_significant:
                    status = STATUS_SIGNIFICANT
                else:
                    status = STATUS_INCONCLUSIVE

                edges.append(
                    SpilloverEdge(
                        source=source,
                        target=target,
                        shock_type=shock_type,
                        effects=effects,
                        peak_horizon=peak.horizon if peak else None,
                        peak_elasticity=(
                            peak.elasticity
                            if peak and not math.isnan(peak.elasticity)
                            else None
                        ),
                        status=status,
                        n_episodes=source_episodes.n_episodes,
                        half_life_periods=_half_life(effects, peak),
                    )
                )

    edges = _apply_fdr(edges, config)

    diagnostics: Dict[str, object] = {
        "panel": panel.describe(),
        "common_factor": decomposition.as_dict(),
        "episodes": {k: v.n_episodes for k, v in sorted(episodes.items())},
    }
    if run_holdout:
        diagnostics["holdout"] = _holdout_agreement(panel, config)

    matrix = SpilloverMatrix(
        edges=edges,
        commodities=panel.commodities,
        markets=panel.markets,
        frequency=config.frequency,
        config=config.as_dict(),
        diagnostics=diagnostics,
        panel_hash=panel.data_hash,
        built_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        "Spillover build complete: %d edges, %d actionable",
        len(matrix.edges),
        len(matrix.actionable_edges),
    )
    return matrix
