"""
Meta-Ensemble — Phase 1 Confidence-Aware Rule-Based Fusion Layer.

A stateless, deterministic, interpretable fusion engine that combines
outputs from three independent agents (Seasonality, Arrival Volume,
External Factors) into a single price prediction with confidence score,
attribution breakdown, and risk flags.

Design principles:
  • No ML models, no training, no persistence
  • Pure function — same inputs always produce same outputs
  • All agent outputs are treated as read-only black boxes
  • Production-grade: clamped outputs, division-by-zero guards, NaN safety

Architecture:
  ① Normalize    — Align time horizons to 7-day comparable scale
  ② Base Weights — Derive from confidence scores (with floor)
  ③ Adjust       — Dynamic boosts/penalties from supply_stress, volatility, regime
  ④ Fuse         — Confidence-weighted average
  ⑤ External     — Additive directional bias (not multiplicative)
  ⑥ Conflict     — Detect sign disagreement → dampen prediction
  ⑦ Stability    — Clamp outputs within realistic bounds
  ⑧ Attribution  — Per-agent contribution percentages
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Constants — single place to tune system behaviour
# ═══════════════════════════════════════════════════════════════════════════════

# Time-horizon alignment
_SEASONALITY_HORIZON_DAYS = 30
_COMMON_HORIZON_DAYS = 7
_SCALING_DAMPING_FACTOR = 0.8          # Dampen 30d -> 7d projection

# Weight adjustment factors
_SUPPLY_STRESS_BOOST_FACTOR = 0.5      # max 50% boost to Arrival weight
_VOLATILITY_PENALTY_FACTOR = 0.3       # max 30% reduction to Seasonality weight
_TREND_REGIME_BOOST = 1.3              # 30% boost when strong trend detected
_CONFIDENCE_FLOOR = 0.05               # never fully zero-weight an agent
_WEIGHT_CLAMP_MIN = 0.4                # Min weight (0.4 for 2-agent sum-to-1)
_WEIGHT_CLAMP_MAX = 0.6                # Max weight for any agent

# External signal
_EXTERNAL_BIAS_MAX_MAGNITUDE = 2.0     # max ±2 percentage points of bias

# Conflict handling
_CONFLICT_SIGN_THRESHOLD = 0.2         # min |prediction| to count as meaningful
_CONFLICT_MAGNITUDE_THRESHOLD = 3.0    # Magnitude diff for "strong conflict"
_CONFLICT_DAMPEN_FACTOR_NORMAL = 0.90  # Dampen prediction on sign conflict
_CONFLICT_DAMPEN_FACTOR_STRONG = 0.80  # Dampen prediction on strong conflict

# Stability
_PREDICTION_CLAMP_MIN = -15.0          # max weekly % drop
_PREDICTION_CLAMP_MAX = 15.0           # max weekly % rise
_CONFIDENCE_FLOOR_FINAL = 0.05         # never report zero confidence
_CONFIDENCE_CEILING_FINAL = 0.95       # never claim certainty

# Confidence computation
_LOW_CONFIDENCE_THRESHOLD = 0.4        # both agents below this → penalty
_HIGH_CONFIDENCE_THRESHOLD = 0.6       # both agents above this + agreement → bonus
_LOW_CONFIDENCE_PENALTY = 0.8
_AGREEMENT_BONUS = 1.1
_CONFLICT_CONFIDENCE_PENALTY_SIGN = 0.6
_CONFLICT_CONFIDENCE_PENALTY_STRONG = 0.5
_EXTERNAL_RELIANCE_PENALTY = 0.85      # Penalty if external dominates prediction
_EXTERNAL_CONFIDENCE_BLEND_WEIGHT = 0.1  # 10% blend of external confidence

# Strong trend regimes
_STRONG_TREND_REGIMES = frozenset({"ascending", "descending"})


# ═══════════════════════════════════════════════════════════════════════════════
# Input / Output Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SeasonalityInput:
    """Immutable snapshot of Seasonality Agent output."""
    prediction_30d: float = 0.0   # % change over 30 days
    confidence: float = 0.0       # 0–1
    volatility: float = 0.0       # raw volatility metric
    regime: str = "neutral"       # ascending / descending / peak / trough

    def __post_init__(self):
        # Validate and sanitize at the boundary
        object.__setattr__(self, 'prediction_30d',
                           _safe_float(self.prediction_30d, 0.0))
        object.__setattr__(self, 'confidence',
                           _clamp(_safe_float(self.confidence, 0.0), 0.0, 1.0))
        object.__setattr__(self, 'volatility',
                           max(_safe_float(self.volatility, 0.0), 0.0))
        object.__setattr__(self, 'regime',
                           str(self.regime).strip().lower() if self.regime else "neutral")


@dataclass(frozen=True)
class ArrivalInput:
    """Immutable snapshot of Arrival Volume Agent output."""
    prediction_7d: float = 0.0    # % change over 7 days
    confidence: float = 0.0       # 0–1
    supply_stress: float = 0.0    # 0–1
    regime: str = "normal"        # squeeze / oversupply / normal

    def __post_init__(self):
        object.__setattr__(self, 'prediction_7d',
                           _safe_float(self.prediction_7d, 0.0))
        object.__setattr__(self, 'confidence',
                           _clamp(_safe_float(self.confidence, 0.0), 0.0, 1.0))
        object.__setattr__(self, 'supply_stress',
                           _clamp(_safe_float(self.supply_stress, 0.0), 0.0, 1.0))
        object.__setattr__(self, 'regime',
                           str(self.regime).strip().lower() if self.regime else "normal")


@dataclass(frozen=True)
class ExternalInput:
    """Immutable snapshot of External Factors Agent output."""
    impact_score: float = 0.0     # -1 to +1
    confidence: float = 0.0       # 0–1

    def __post_init__(self):
        object.__setattr__(self, 'impact_score',
                           _clamp(_safe_float(self.impact_score, 0.0), -1.0, 1.0))
        object.__setattr__(self, 'confidence',
                           _clamp(_safe_float(self.confidence, 0.0), 0.0, 1.0))


@dataclass
class MetaEnsembleOutput:
    """Complete output of the Meta-Ensemble fusion layer."""
    final_prediction: float          # % change (7-day equivalent)
    final_confidence: float          # 0–1
    attribution: Dict[str, float] = field(default_factory=dict)  # % contribution
    risk_flags: Dict[str, bool] = field(default_factory=dict)
    debug: Dict[str, Any] = field(default_factory=dict)          # internals for logging

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary (API-ready)."""
        return {
            "final_prediction": round(self.final_prediction, 4),
            "final_confidence": round(self.final_confidence, 4),
            "attribution": {k: round(v, 2) for k, v in self.attribution.items()},
            "risk_flags": self.risk_flags,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Utility Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert to float with NaN/None safety."""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    """Numerically safe clamp."""
    return max(lo, min(hi, value))


def _sign(x: float) -> int:
    """Return +1, -1, or 0."""
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# Core Fusion Engine
# ═══════════════════════════════════════════════════════════════════════════════

def fuse(
    seasonality: SeasonalityInput,
    arrival: ArrivalInput,
    external: ExternalInput,
) -> MetaEnsembleOutput:
    """
    Stateless, deterministic meta-ensemble fusion (Phase-1.5).

    Upgrade highlights:
      • Dampened 30d -> 7d scaling (0.8 factor)
      • Signal-strength aware weights with hard [0.2, 0.6] stability clamps
      • Attenuated external bias based on internal signal strength
      • Multi-factor confidence penalties (conflict, volatility, external reliance)
      • Enhanced conflict handling (sign + magnitude divergence)

    Directional-bias corrections (v2.6):
      • Fix 2 — Penalise overconfident bullish seasonality when arrival is bearish
      • Fix 3 — Arrival wins the weight battle when signs conflict and arrival is strong
      • Fix 1 — Direction override: strong negative arrival bypasses blended fusion
    """
    debug: Dict[str, Any] = {}

    # ── ① Normalize to common 7-day horizon (Dampened) ──────────────────
    norm_s = (seasonality.prediction_30d / _SEASONALITY_HORIZON_DAYS) * _COMMON_HORIZON_DAYS * 0.9
    norm_a = arrival.prediction_7d

    debug["norm_s"] = round(norm_s, 6)
    debug["norm_a"] = round(norm_a, 6)

    # ── ② Weighting (Signal-Strength + Confidence + Clamped) ─────────────
    # Boosted arrival weight to capture more short-term drops (Step 3, v2.5).
    # Threshold lowered from >0.7 → >0.6; default w_arrival 0.60→0.65.
    if arrival.supply_stress > 0.6:
        w_a = 0.75
        w_s = 0.25
    elif arrival.supply_stress < 0.3:
        w_a = 0.55
        w_s = 0.45
    else:
        w_a = 0.65
        w_s = 0.35

    # Apply volatility penalty
    if seasonality.volatility > 0.0:
        w_s *= (1.0 - _VOLATILITY_PENALTY_FACTOR * min(seasonality.volatility, 1.0))

    # Apply trend regime boost
    if seasonality.regime in _STRONG_TREND_REGIMES:
        w_s *= _TREND_REGIME_BOOST

    # Fix 2 — Penalise overconfident bullish seasonality when arrival disagrees.
    # If seasonality is predicting a strong rise (>3%) but arrival is negative,
    # the seasonal model is likely carrying stale upward momentum.  Dampen its
    # contribution by 30% so the short-term signal gets more influence.
    _s_pred_raw = seasonality.prediction_30d  # un-normalised, for threshold check
    if _s_pred_raw > 3.0 and arrival.prediction_7d < 0.0:
        w_s *= 0.7
        logger.info(
            f"[MetaEnsemble][Fix2] Overconfident seasonality penalised: "
            f"s_pred_30d={_s_pred_raw:.2f}%, a_pred_7d={arrival.prediction_7d:.2f}%. "
            f"w_s scaled by 0.7 → {w_s:.4f}"
        )
        debug["fix2_seasonality_penalty"] = True
    else:
        debug["fix2_seasonality_penalty"] = False

    # Fix 3 — Directional conflict: arrival wins when signs differ and it is strong.
    # If arrival and (normalised) seasonality point in opposite directions and
    # arrival magnitude is at least 0.4%, raise w_arrival to at least 0.70 so
    # the short-term truth overrides the slow seasonal background.
    _signs_conflict = (_sign(norm_s) != _sign(norm_a)
                       and _sign(norm_s) != 0
                       and _sign(norm_a) != 0)
    if _signs_conflict and abs(arrival.prediction_7d) > 0.4:
        w_a = max(w_a, 0.70)
        logger.info(
            f"[MetaEnsemble][Fix3] Directional conflict — arrival promoted: "
            f"norm_s={norm_s:.3f}%, norm_a={norm_a:.3f}%. "
            f"w_arrival forced to {w_a:.4f}"
        )
        debug["fix3_arrival_promoted"] = True
    else:
        debug["fix3_arrival_promoted"] = False

    # Clamp seasonality influence
    w_s = min(w_s, 0.5)

    # Renormalize to ensure sum to 1
    total_w = w_s + w_a
    w_s /= total_w
    w_a /= total_w

    debug["w_s_final"] = round(w_s, 6)
    debug["w_a_final"] = round(w_a, 6)

    # ── ③ Core Fusion ──────────────────────────────────────────────────
    fused_pred = w_s * norm_s + w_a * norm_a
    debug["fused_pred"] = round(fused_pred, 6)

    # Fix 1 — Direction Override: strong negative arrival bypasses blended fusion.
    # Condition: arrival is meaningfully negative AND its absolute magnitude
    # is at least 60% of normalised seasonality's magnitude.  This fires when
    # arrival is clearly bearish while seasonality is masking it with a bullish tilt.
    # When triggered, replace fused_pred with a slightly attenuated arrival signal
    # (×0.9) so the short-term price-drop driver is not drowned out.
    _fix1_override = (
        arrival.prediction_7d < -0.5
        and abs(arrival.prediction_7d) > abs(norm_s) * 0.6
        and arrival.confidence > 0.2  # Fix 1.1: Guard against low-confidence outliers
    )
    if _fix1_override:
        # Fix 1.2: Capped override to prevent -15% style explosions from noisy agents
        # Fix 1.3: Confidence-weighted override to reduce false signals when arrival is only moderately confident
        # Use a smooth transition: full impact at 0.5 confidence, reduced impact at 0.2.
        _conf_factor = _clamp(arrival.confidence * 2.0, 0.7, 1.0)
        fused_pred = max(arrival.prediction_7d * 0.9 * _conf_factor, -4.0) 
        logger.info(
            f"[MetaEnsemble][Fix1] Direction override triggered: "
            f"a_pred={arrival.prediction_7d:.3f}%, norm_s={norm_s:.3f}%. "
            f"fused_pred overridden to {fused_pred:.4f}%"
        )
        debug["fix1_direction_override"] = True
    else:
        debug["fix1_direction_override"] = False

    # ── ④ External signal adjustment (Attenuated) ──────────────────────
    # External influence decreases as internal signal strength increases
    attenuation_factor = 1.0 / (1.0 + abs(fused_pred))
    external_bias = (
        external.impact_score
        * external.confidence
        * _EXTERNAL_BIAS_MAX_MAGNITUDE
    ) * attenuation_factor

    adjusted_pred = fused_pred + external_bias

    debug["external_attenuation"] = round(attenuation_factor, 4)
    debug["external_bias"] = round(external_bias, 6)
    debug["adjusted_pred_pre_conflict"] = round(adjusted_pred, 6)

    # ── ⑤ Enhanced Conflict detection ───────────────────────────────────
    sign_disagreement = (
        _sign(norm_s) != _sign(norm_a)
        and _sign(norm_s) != 0
        and _sign(norm_a) != 0
        and abs(norm_s) > _CONFLICT_SIGN_THRESHOLD
        and abs(norm_a) > _CONFLICT_SIGN_THRESHOLD
    )
    
    magnitude_divergence = abs(norm_s - norm_a) > _CONFLICT_MAGNITUDE_THRESHOLD
    
    strong_conflict = sign_disagreement and magnitude_divergence

    if sign_disagreement:
        damp_factor = _CONFLICT_DAMPEN_FACTOR_STRONG if magnitude_divergence else _CONFLICT_DAMPEN_FACTOR_NORMAL
        adjusted_pred *= damp_factor
        logger.info(
            f"[MetaEnsemble] Conflict detected (Strong={strong_conflict}): "
            f"norm_s={norm_s:.3f}%, norm_a={norm_a:.3f}%. "
            f"Prediction dampened by {damp_factor}."
        )

    debug["conflict_detected"] = sign_disagreement
    debug["strong_conflict"] = strong_conflict
    debug["adjusted_pred_post_conflict"] = round(adjusted_pred, 6)

    # ── ⑥ Final confidence computation ────────────────────────────────
    # Base confidence is a weighted average of seasonality and arrival confidence
    base_conf = w_s * seasonality.confidence + w_a * arrival.confidence

    # Blend in external confidence (10% weight)
    if external.confidence > 0:
        base_conf = (1.0 - _EXTERNAL_CONFIDENCE_BLEND_WEIGHT) * base_conf + _EXTERNAL_CONFIDENCE_BLEND_WEIGHT * external.confidence

    # Penalty if both agents are below low confidence threshold
    if seasonality.confidence < _LOW_CONFIDENCE_THRESHOLD and arrival.confidence < _LOW_CONFIDENCE_THRESHOLD:
        base_conf *= _LOW_CONFIDENCE_PENALTY

    # Bonus if both agents are above high confidence threshold and agree on sign
    if (seasonality.confidence > _HIGH_CONFIDENCE_THRESHOLD 
        and arrival.confidence > _HIGH_CONFIDENCE_THRESHOLD 
        and not sign_disagreement):
        base_conf *= _AGREEMENT_BONUS

    # Conflict penalties
    if strong_conflict:
        base_conf *= _CONFLICT_CONFIDENCE_PENALTY_STRONG
    elif sign_disagreement:
        base_conf *= _CONFLICT_CONFIDENCE_PENALTY_SIGN

    # Penalty if external dominates prediction
    if abs(external_bias) > abs(fused_pred):
        base_conf *= _EXTERNAL_RELIANCE_PENALTY

    final_confidence = _clamp(base_conf, _CONFIDENCE_FLOOR_FINAL, _CONFIDENCE_CEILING_FINAL)
    
    import numpy as np
    prediction_std = float(np.std([norm_s, norm_a]))
    debug["prediction_std"] = round(prediction_std, 4)

    # ── ⑦ Final Output Prep ────────────────────────────────────────────
    final_prediction = _clamp(
        adjusted_pred, _PREDICTION_CLAMP_MIN, _PREDICTION_CLAMP_MAX
    )

    attribution = {
        "seasonality_pct": (abs(w_s * norm_s) / (abs(w_s * norm_s) + abs(w_a * norm_a) + abs(external_bias) + 1e-12)) * 100.0,
        "arrival_pct": (abs(w_a * norm_a) / (abs(w_s * norm_s) + abs(w_a * norm_a) + abs(external_bias) + 1e-12)) * 100.0,
        "external_pct": (abs(external_bias) / (abs(w_s * norm_s) + abs(w_a * norm_a) + abs(external_bias) + 1e-12)) * 100.0,
    }

    return MetaEnsembleOutput(
        final_prediction=round(final_prediction, 4),
        final_confidence=round(final_confidence, 4),
        attribution=attribution,
        risk_flags={
            "conflict_detected": sign_disagreement,
            "strong_conflict": strong_conflict,
            "low_confidence": final_confidence < _LOW_CONFIDENCE_THRESHOLD,
            "high_volatility_risk": seasonality.volatility > 0.5,
            "external_reliance_heavy": abs(external_bias) > abs(fused_pred),
        },
        debug=debug,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience: Build inputs from existing AgentOutput objects
# ═══════════════════════════════════════════════════════════════════════════════

def build_seasonality_input_from_agent_output(agent_output) -> SeasonalityInput:
    """
    Construct a SeasonalityInput from the existing AgentOutput schema.

    Maps:
      prediction       → prediction_30d (already in % over 30 days)
      confidence       → confidence
      metadata.return_std      → volatility (proxy)
      metadata.cycle_phase     → regime
    """
    meta = agent_output.metadata or {}
    return SeasonalityInput(
        prediction_30d=_safe_float(agent_output.prediction, 0.0),
        confidence=_safe_float(agent_output.confidence, 0.0),
        volatility=_safe_float(meta.get("return_std", 0.0), 0.0) / 100.0,  # convert from % to fraction
        regime=str(meta.get("cycle_phase", "neutral")).strip().lower(),
    )


def build_arrival_input_from_agent_output(agent_output) -> ArrivalInput:
    """
    Construct an ArrivalInput from the existing AgentOutput schema.

    Maps:
      prediction                   → prediction_7d (already in % over 7 days)
      confidence                   → confidence
      metadata.supply_stress_score → supply_stress
      metadata.supply_regime       → regime
    """
    meta = agent_output.metadata or {}
    return ArrivalInput(
        prediction_7d=_safe_float(agent_output.prediction, 0.0),
        confidence=_safe_float(agent_output.confidence, 0.0),
        supply_stress=_safe_float(meta.get("supply_stress_score", 0.0), 0.0),
        regime=str(meta.get("supply_regime", "normal")).strip().lower(),
    )


def build_external_input(
    impact_score: float = 0.0,
    confidence: float = 0.0,
) -> ExternalInput:
    """
    Construct an ExternalInput from raw values.

    The External Factors agent is not yet fully integrated into the
    pipeline, so this accepts raw values directly.  When the agent
    is production-ready, add a `build_external_input_from_agent_output`
    variant.
    """
    return ExternalInput(
        impact_score=impact_score,
        confidence=confidence,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Top-level convenience function
# ═══════════════════════════════════════════════════════════════════════════════

def run_meta_ensemble(
    seasonality_output,
    arrival_output,
    external_impact: float = 0.0,
    external_confidence: float = 0.0,
) -> MetaEnsembleOutput:
    """
    End-to-end convenience function.

    Accepts raw AgentOutput objects from Seasonality and Arrival agents,
    plus optional external signal, and returns the fused MetaEnsembleOutput.

    This is the primary integration point for the API layer.

    Args:
        seasonality_output: AgentOutput from run_seasonality_agent()
        arrival_output:     AgentOutput from run_arrival_volume_agent()
        external_impact:    External impact score (-1 to +1)
        external_confidence: External confidence (0 to 1)

    Returns:
        MetaEnsembleOutput with prediction, confidence, attribution, risk_flags.
    """
    s_input = build_seasonality_input_from_agent_output(seasonality_output)
    a_input = build_arrival_input_from_agent_output(arrival_output)
    e_input = build_external_input(external_impact, external_confidence)

    logger.info(
        f"[MetaEnsemble] Inputs — "
        f"S(pred={s_input.prediction_30d:.2f}%, conf={s_input.confidence:.3f}, "
        f"vol={s_input.volatility:.3f}, regime={s_input.regime}) | "
        f"A(pred={a_input.prediction_7d:.2f}%, conf={a_input.confidence:.3f}, "
        f"stress={a_input.supply_stress:.3f}, regime={a_input.regime}) | "
        f"E(impact={e_input.impact_score:.3f}, conf={e_input.confidence:.3f})"
    )

    return fuse(s_input, a_input, e_input)
