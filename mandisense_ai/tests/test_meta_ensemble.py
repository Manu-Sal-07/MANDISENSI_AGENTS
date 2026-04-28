"""
Tests for Meta-Ensemble — Phase 1 Fusion Layer.

Covers:
  • Normal operation with realistic inputs
  • Edge cases (zero confidence, extreme predictions, NaN inputs)
  • Conflict detection and dampening
  • Weight adjustment mechanics
  • Attribution correctness
  • Stability constraints (clamping)
  • Determinism (same inputs → same outputs)
"""

import math
import pytest
from ensemble.meta_ensemble import (
    SeasonalityInput,
    ArrivalInput,
    ExternalInput,
    MetaEnsembleOutput,
    fuse,
    _safe_float,
    _clamp,
    _sign,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Test Utilities
# ═══════════════════════════════════════════════════════════════════════════════

class TestSafeFloat:
    def test_normal_value(self):
        assert _safe_float(3.14) == 3.14

    def test_none_returns_default(self):
        assert _safe_float(None, 42.0) == 42.0

    def test_nan_returns_default(self):
        assert _safe_float(float("nan"), -1.0) == -1.0

    def test_inf_returns_default(self):
        assert _safe_float(float("inf"), 0.0) == 0.0

    def test_string_returns_default(self):
        assert _safe_float("not_a_number", 5.0) == 5.0

    def test_string_number(self):
        assert _safe_float("3.5") == 3.5


class TestClamp:
    def test_within_range(self):
        assert _clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_range(self):
        assert _clamp(-5.0, 0.0, 1.0) == 0.0

    def test_above_range(self):
        assert _clamp(10.0, 0.0, 1.0) == 1.0


class TestSign:
    def test_positive(self):
        assert _sign(3.5) == 1

    def test_negative(self):
        assert _sign(-0.1) == -1

    def test_zero(self):
        assert _sign(0.0) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Test Input Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestInputValidation:
    def test_seasonality_confidence_clamped(self):
        s = SeasonalityInput(confidence=1.5)
        assert s.confidence == 1.0

    def test_seasonality_negative_confidence(self):
        s = SeasonalityInput(confidence=-0.3)
        assert s.confidence == 0.0

    def test_arrival_supply_stress_clamped(self):
        a = ArrivalInput(supply_stress=2.0)
        assert a.supply_stress == 1.0

    def test_external_impact_clamped(self):
        e = ExternalInput(impact_score=-5.0)
        assert e.impact_score == -1.0

    def test_regime_normalisation(self):
        s = SeasonalityInput(regime="  ASCENDING  ")
        assert s.regime == "ascending"

    def test_none_regime_defaults(self):
        s = SeasonalityInput(regime=None)
        assert s.regime == "neutral"


# ═══════════════════════════════════════════════════════════════════════════════
# Test Core Fusion — Worked Example from Design Doc
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkedExample:
    """Reproduces the exact example from the design document."""

    def setup_method(self):
        self.s = SeasonalityInput(
            prediction_30d=6.0,
            confidence=0.75,
            volatility=0.3,
            regime="ascending",
        )
        self.a = ArrivalInput(
            prediction_7d=-2.5,
            confidence=0.60,
            supply_stress=0.8,
            regime="squeeze",
        )
        self.e = ExternalInput(
            impact_score=0.4,
            confidence=0.55,
        )
        self.result = fuse(self.s, self.a, self.e)

    def test_conflict_detected(self):
        """Seasonality positive, Arrival negative → conflict."""
        assert self.result.risk_flags["conflict_detected"] is True

    def test_prediction_near_zero(self):
        """Conflict dampening should push prediction toward zero."""
        assert abs(self.result.final_prediction) < 1.0

    def test_confidence_reduced(self):
        """Conflict should reduce confidence below base level."""
        assert self.result.final_confidence < 0.65

    def test_attribution_sums_to_100(self):
        total = sum(self.result.attribution.values())
        assert abs(total - 100.0) < 0.5  # allow rounding tolerance

    def test_arrival_dominates_attribution(self):
        """Arrival has larger magnitude prediction → higher attribution."""
        assert self.result.attribution["arrival_pct"] > self.result.attribution["seasonality_pct"]


# ═══════════════════════════════════════════════════════════════════════════════
# Test Agreement Scenario
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgreementScenario:
    """Both agents agree on direction with high confidence."""

    def setup_method(self):
        self.s = SeasonalityInput(
            prediction_30d=9.0,   # → norm_s = 2.1%
            confidence=0.80,
            volatility=0.1,
            regime="ascending",
        )
        self.a = ArrivalInput(
            prediction_7d=3.0,
            confidence=0.70,
            supply_stress=0.2,
            regime="normal",
        )
        self.e = ExternalInput(impact_score=0.3, confidence=0.5)
        self.result = fuse(self.s, self.a, self.e)

    def test_no_conflict(self):
        assert self.result.risk_flags["conflict_detected"] is False

    def test_positive_prediction(self):
        assert self.result.final_prediction > 0.0

    def test_high_confidence(self):
        """Agreement + high individual confidence → boosted final confidence."""
        assert self.result.final_confidence > 0.6

    def test_not_low_confidence_flag(self):
        assert self.result.risk_flags["low_confidence"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Test Dynamic Weight Adjustments
# ═══════════════════════════════════════════════════════════════════════════════

class TestDynamicWeights:
    def test_high_supply_stress_boosts_arrival(self):
        """High supply stress should shift weight toward Arrival."""
        s = SeasonalityInput(prediction_30d=7.0, confidence=0.70, volatility=0.0, regime="neutral")
        a = ArrivalInput(prediction_7d=3.0, confidence=0.70, supply_stress=0.9, regime="squeeze")
        e = ExternalInput()

        result = fuse(s, a, e)
        # Arrival weight should be higher than Seasonality weight
        assert result.debug["w_a_final"] > result.debug["w_s_final"]

    def test_high_volatility_penalises_seasonality(self):
        """High volatility should reduce Seasonality weight."""
        s = SeasonalityInput(prediction_30d=7.0, confidence=0.70, volatility=0.9, regime="neutral")
        a = ArrivalInput(prediction_7d=3.0, confidence=0.70, supply_stress=0.0, regime="normal")
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.debug["w_s_final"] < result.debug["w_a_final"]

    def test_trend_regime_boosts_seasonality(self):
        """Ascending/descending regime should boost Seasonality weight."""
        # With trend boost
        s_trend = SeasonalityInput(prediction_30d=7.0, confidence=0.50, volatility=0.0, regime="ascending")
        # Without trend boost
        s_neutral = SeasonalityInput(prediction_30d=7.0, confidence=0.50, volatility=0.0, regime="trough")
        a = ArrivalInput(prediction_7d=3.0, confidence=0.50, supply_stress=0.0, regime="normal")
        e = ExternalInput()

        result_trend = fuse(s_trend, a, e)
        result_neutral = fuse(s_neutral, a, e)

        assert result_trend.debug["w_s_final"] > result_neutral.debug["w_s_final"]


# ═══════════════════════════════════════════════════════════════════════════════
# Test External Signal
# ═══════════════════════════════════════════════════════════════════════════════

class TestExternalSignal:
    def test_zero_impact_no_effect(self):
        """External with zero impact should not change the fused prediction."""
        s = SeasonalityInput(prediction_30d=7.0, confidence=0.70)
        a = ArrivalInput(prediction_7d=3.0, confidence=0.70)
        e_zero = ExternalInput(impact_score=0.0, confidence=0.50)

        result = fuse(s, a, e_zero)
        assert result.debug["external_bias"] == 0.0

    def test_zero_confidence_no_effect(self):
        """External with zero confidence should not affect prediction."""
        s = SeasonalityInput(prediction_30d=7.0, confidence=0.70)
        a = ArrivalInput(prediction_7d=3.0, confidence=0.70)
        e = ExternalInput(impact_score=0.8, confidence=0.0)

        result = fuse(s, a, e)
        assert result.debug["external_bias"] == 0.0

    def test_max_bias_bounded(self):
        """Maximum external bias should be ±2.0 percentage points."""
        s = SeasonalityInput(prediction_30d=0.0, confidence=0.50)
        a = ArrivalInput(prediction_7d=0.0, confidence=0.50)
        e = ExternalInput(impact_score=1.0, confidence=1.0)

        result = fuse(s, a, e)
        assert abs(result.debug["external_bias"]) <= 2.01  # small tolerance


# ═══════════════════════════════════════════════════════════════════════════════
# Test Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_all_zeros(self):
        """All inputs zero → prediction ≈ 0, confidence at floor."""
        s = SeasonalityInput()
        a = ArrivalInput()
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.final_prediction == 0.0
        assert result.final_confidence >= 0.05  # floor

    def test_extreme_prediction_clamped(self):
        """Very large prediction should be clamped to ±15%."""
        s = SeasonalityInput(prediction_30d=200.0, confidence=0.90)  # → norm_s = 46.67%
        a = ArrivalInput(prediction_7d=50.0, confidence=0.90)
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.final_prediction <= 15.0
        assert result.final_prediction >= -15.0

    def test_negative_extreme_clamped(self):
        """Very large negative prediction should be clamped."""
        s = SeasonalityInput(prediction_30d=-200.0, confidence=0.90)
        a = ArrivalInput(prediction_7d=-50.0, confidence=0.90)
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.final_prediction >= -15.0

    def test_both_low_confidence(self):
        """Both agents with very low confidence → low_confidence flag True."""
        s = SeasonalityInput(prediction_30d=5.0, confidence=0.15)
        a = ArrivalInput(prediction_7d=3.0, confidence=0.20)
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.risk_flags["low_confidence"] is True

    def test_confidence_never_exceeds_ceiling(self):
        """Even with perfect inputs, confidence should cap at 0.95."""
        s = SeasonalityInput(prediction_30d=5.0, confidence=1.0, regime="ascending")
        a = ArrivalInput(prediction_7d=2.0, confidence=1.0, supply_stress=0.0)
        e = ExternalInput(impact_score=0.5, confidence=1.0)

        result = fuse(s, a, e)
        assert result.final_confidence <= 0.95


# ═══════════════════════════════════════════════════════════════════════════════
# Test Determinism
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterminism:
    def test_same_inputs_same_outputs(self):
        """Calling fuse multiple times with identical inputs must yield identical results."""
        s = SeasonalityInput(prediction_30d=4.5, confidence=0.65, volatility=0.2, regime="ascending")
        a = ArrivalInput(prediction_7d=-1.0, confidence=0.55, supply_stress=0.4, regime="normal")
        e = ExternalInput(impact_score=0.2, confidence=0.4)

        results = [fuse(s, a, e) for _ in range(10)]

        # All predictions and confidences must be identical
        preds = [r.final_prediction for r in results]
        confs = [r.final_confidence for r in results]

        assert all(p == preds[0] for p in preds)
        assert all(c == confs[0] for c in confs)


# ═══════════════════════════════════════════════════════════════════════════════
# Test Conflict Handling Specifics
# ═══════════════════════════════════════════════════════════════════════════════

class TestConflictHandling:
    def test_no_conflict_when_same_sign(self):
        """No conflict when both agents predict same direction."""
        s = SeasonalityInput(prediction_30d=10.0, confidence=0.70)   # norm_s ≈ 2.33
        a = ArrivalInput(prediction_7d=3.0, confidence=0.70)
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.risk_flags["conflict_detected"] is False

    def test_no_conflict_when_magnitudes_tiny(self):
        """No conflict when predictions are below threshold despite opposite signs."""
        s = SeasonalityInput(prediction_30d=0.5, confidence=0.70)   # norm_s ≈ 0.117
        a = ArrivalInput(prediction_7d=-0.1, confidence=0.70)
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.risk_flags["conflict_detected"] is False

    def test_conflict_dampens_prediction(self):
        """Conflict should make the absolute prediction smaller."""
        s = SeasonalityInput(prediction_30d=15.0, confidence=0.70)  # norm_s = 3.5
        a = ArrivalInput(prediction_7d=-4.0, confidence=0.70)
        e = ExternalInput()

        result = fuse(s, a, e)
        assert result.risk_flags["conflict_detected"] is True
        # The dampened prediction should be less in magnitude
        # than the undampened value
        assert abs(result.final_prediction) < abs(result.debug["adjusted_pred_pre_conflict"])


# ═══════════════════════════════════════════════════════════════════════════════
# Test Output Schema
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputSchema:
    def test_to_dict_keys(self):
        s = SeasonalityInput(prediction_30d=5.0, confidence=0.70)
        a = ArrivalInput(prediction_7d=2.0, confidence=0.60)
        e = ExternalInput()

        result = fuse(s, a, e)
        d = result.to_dict()

        assert "final_prediction" in d
        assert "final_confidence" in d
        assert "attribution" in d
        assert "risk_flags" in d
        assert "debug" not in d  # debug excluded from API output

    def test_attribution_has_three_keys(self):
        s = SeasonalityInput(prediction_30d=5.0, confidence=0.70)
        a = ArrivalInput(prediction_7d=2.0, confidence=0.60)
        e = ExternalInput(impact_score=0.3, confidence=0.5)

        result = fuse(s, a, e)
        assert set(result.attribution.keys()) == {"seasonality_pct", "arrival_pct", "external_pct"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
