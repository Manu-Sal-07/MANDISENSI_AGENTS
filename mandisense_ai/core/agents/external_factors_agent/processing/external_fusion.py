"""
External signal fusion engine for the External Factors Agent.

Combines weather, news, and policy signals into a bounded external impact score
and confidence score for downstream price adjustment.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

WEIGHTS = {
    "weather": 0.4,
    "policy": 0.35,
    "news": 0.25,
}
MAX_BIAS = 0.02


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))


def _has_conflict(values: Tuple[float, float, float]) -> bool:
    positive = any(v > 0 for v in values)
    negative = any(v < 0 for v in values)
    return positive and negative


def _agreement_factor(effective_signals: Tuple[float, float, float]) -> float:
    nonzero = [value for value in effective_signals if abs(value) > 1e-9]
    if not nonzero:
        return 0.0
    positive = any(v > 0 for v in nonzero)
    negative = any(v < 0 for v in nonzero)
    if positive and negative:
        return 0.7
    if len(nonzero) >= 2:
        return 1.05
    return 1.0


def compute_external_impact(
    weather_signal: float,
    news_signal: float,
    policy_signal: float,
    weather_conf: float,
    news_conf: float,
    policy_conf: float,
) -> Dict[str, float]:
    """Compute the bounded external impact score and confidence."""
    weather_signal = _safe_float(weather_signal)
    news_signal = _safe_float(news_signal)
    policy_signal = _safe_float(policy_signal)

    weather_conf = _clamp(_safe_float(weather_conf), 0.0, 1.0)
    news_conf = _clamp(_safe_float(news_conf), 0.0, 1.0)
    policy_conf = _clamp(_safe_float(policy_conf), 0.0, 1.0)

    weather_eff = weather_signal * weather_conf
    policy_eff = policy_signal * policy_conf
    news_eff = news_signal * news_conf

    impact_score_raw = (
        WEIGHTS["weather"] * weather_eff
        + WEIGHTS["policy"] * policy_eff
        + WEIGHTS["news"] * news_eff
    )

    if _has_conflict((weather_eff, policy_eff, news_eff)):
        impact_score_raw *= 0.7

    impact_score = _clamp(impact_score_raw, -1.0, 1.0)
    impact_score = impact_score * MAX_BIAS

    total_weight = (
        WEIGHTS["weather"] * weather_conf
        + WEIGHTS["policy"] * policy_conf
        + WEIGHTS["news"] * news_conf
    )

    agreement_factor = _agreement_factor((weather_eff, policy_eff, news_eff))
    final_confidence = _clamp(total_weight * agreement_factor, 0.0, 1.0)

    if _has_conflict((weather_eff, policy_eff, news_eff)):
        final_confidence *= 0.85
        final_confidence = _clamp(final_confidence, 0.0, 1.0)

    logger.debug(
        "Computed external impact: weather_eff=%.4f policy_eff=%.4f news_eff=%.4f "
        "impact_score=%.6f confidence=%.4f",
        weather_eff,
        policy_eff,
        news_eff,
        impact_score,
        final_confidence,
    )

    return {
        "impact_score": float(impact_score),
        "confidence": float(final_confidence),
        "components": {
            "weather": float(weather_eff),
            "policy": float(policy_eff),
            "news": float(news_eff),
        },
    }
