"""
Tests for the calibrated decision policy.

Organised around the properties that separate this from every hand-tuned
threshold elsewhere in this codebase (`MandiDecisionEngine`'s `dir_conf > 0.7`,
checked directly against this project's own per-mandi directional-accuracy
table and found unreachable for several mandis):

  * the implied decline probability reads the whole calibrated band, not
    just its sign
  * a threshold is only ever chosen because its *measured* out-of-sample
    precision cleared a real bar -- an unpredictable target must come back
    with no threshold chosen, not a confident-looking default
  * precision/coverage bookkeeping matches a hand-count exactly
  * the row-level conversion from a price interval back to a probability is
    base-price-invariant (a %change is a %change regardless of which
    commodity's absolute price it is attached to)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.config import ForecastConfig
from mandisense_ai.forecasting.decision import (
    CANDIDATE_THRESHOLDS,
    ThresholdEvaluation,
    backtest_decision_policy,
    decide,
    decide_for_row,
    implied_probability_of_decline,
    run_decision_backtest,
)


def _config(**overrides):
    base = dict(
        horizons=(1,),
        min_train_rows=60,
        walk_forward_folds=3,
        use_seasonal_climatology=False,
        use_absence_features=False,
        use_model_blend=False,
        arrival_dropout_rate=0.0,
    )
    base.update(overrides)
    return ForecastConfig(**base)


class TestImpliedProbability:
    def test_band_entirely_above_zero_is_near_certain_rise(self):
        p = implied_probability_of_decline(0.01, 0.02, 0.05, 0.08)
        assert p < 0.05

    def test_band_entirely_below_zero_is_near_certain_decline(self):
        p = implied_probability_of_decline(-0.08, -0.05, -0.02, -0.01)
        assert p > 0.95

    def test_symmetric_band_around_zero_is_a_coin_flip(self):
        p = implied_probability_of_decline(-0.10, -0.02, 0.02, 0.10)
        assert p == pytest.approx(0.5, abs=1e-6)

    def test_band_skewed_toward_decline_is_correctly_high(self):
        """Even the 75th percentile is still negative -- most of the
        distribution sits below zero, so the implied decline probability
        should sit well above the 75th percentile's own level."""
        p = implied_probability_of_decline(-0.10, -0.05, -0.01, 0.05)
        assert p > 0.75

    def test_interpolation_is_exact_at_a_known_bracket_midpoint(self):
        # Zero sits exactly halfway between q25=-0.04 and q75=0.04.
        p = implied_probability_of_decline(-0.10, -0.04, 0.04, 0.10)
        assert p == pytest.approx(0.5, abs=1e-6)


class TestDecide:
    def test_high_decline_probability_calls_sell(self):
        assert decide(0.8, threshold=0.7) == "SELL"

    def test_low_decline_probability_calls_hold(self):
        assert decide(0.1, threshold=0.7) == "HOLD"  # P(rise)=0.9 >= 0.7

    def test_ambiguous_probability_calls_wait(self):
        assert decide(0.5, threshold=0.7) == "WAIT"

    def test_exactly_at_threshold_calls_sell_not_wait(self):
        assert decide(0.7, threshold=0.7) == "SELL"


class TestThresholdEvaluation:
    def test_precision_and_coverage_match_a_hand_count(self):
        evaluation = ThresholdEvaluation(threshold=0.7)
        evaluation.total_rows = 10
        evaluation.sell_calls = 4
        evaluation.sell_correct = 3
        evaluation.hold_calls = 2
        evaluation.hold_correct = 2

        assert evaluation.precision_sell == pytest.approx(0.75)
        assert evaluation.precision_hold == pytest.approx(1.0)
        assert evaluation.combined_precision == pytest.approx(5 / 6)
        assert evaluation.coverage == pytest.approx(0.6)

    def test_no_calls_reports_none_precision_not_a_crash(self):
        evaluation = ThresholdEvaluation(threshold=0.9)
        evaluation.total_rows = 10
        assert evaluation.precision_sell is None
        assert evaluation.combined_precision is None
        assert evaluation.coverage == 0.0


def _predictable_frame(n=800, seed=1):
    """A target with a real, learnable sign pattern: predominantly
    determined by a feature the model can see, plus modest noise -- a
    threshold should legitimately clear the precision bar here."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=n, freq="D")
    driver = rng.normal(0, 1, n)
    y = np.sign(driver) * 0.03 + rng.normal(0, 0.01, n)
    return pd.DataFrame({
        "date": dates, "commodity": "tomato", "mandi_id": "kolar_apmc",
        "modal_price": 1000.0, "driver": driver, "y_h1": y,
    })


def _unpredictable_frame(n=800, seed=2):
    """Pure noise: no feature carries any information about the target's
    sign. No threshold should be able to earn a real precision edge here."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "date": dates, "commodity": "tomato", "mandi_id": "kolar_apmc",
        "modal_price": 1000.0,
        "driver": rng.normal(0, 1, n),
        "y_h1": rng.normal(0, 0.05, n),
    })


class TestBacktestDecisionPolicy:
    def test_a_genuinely_predictable_target_earns_a_chosen_threshold(self):
        frame = _predictable_frame()
        result = backtest_decision_policy(frame, ["driver"], 1, _config(walk_forward_folds=4))

        assert result["status"] == "OK"
        assert result["verdict"] == "CALIBRATED"
        assert result["chosen_threshold"] is not None
        chosen = next(t for t in result["thresholds"] if t["threshold"] == result["chosen_threshold"])
        assert chosen["combined_precision"] >= 0.55

    def test_pure_noise_earns_no_chosen_threshold(self):
        """The honest-refusal path: an unpredictable target must not produce
        a confident-looking default threshold."""
        frame = _unpredictable_frame()
        result = backtest_decision_policy(frame, ["driver"], 1, _config(walk_forward_folds=4))

        assert result["status"] == "OK"
        assert result["verdict"] == "NO_THRESHOLD_CLEARS_BAR"
        assert result["chosen_threshold"] is None

    def test_insufficient_data_reports_status_without_crashing(self):
        frame = _predictable_frame(n=20)
        result = backtest_decision_policy(frame, ["driver"], 1, _config(min_train_rows=60))
        assert result["status"] == "INSUFFICIENT_DATA"

    def test_all_candidate_thresholds_are_reported_even_when_none_chosen(self):
        frame = _unpredictable_frame()
        result = backtest_decision_policy(frame, ["driver"], 1, _config(walk_forward_folds=4))
        reported = {t["threshold"] for t in result["thresholds"]}
        assert reported == set(CANDIDATE_THRESHOLDS)


class TestRunDecisionBacktest:
    def test_aggregates_across_horizons(self):
        frame = _predictable_frame(n=800)
        frame["y_h3"] = frame["y_h1"]  # reuse same signal for a second horizon
        result = run_decision_backtest(frame, _config(horizons=(1, 3), walk_forward_folds=4), prepared=(frame, ["driver"]))

        assert set(result["horizons"].keys()) == {"1", "3"}
        assert result["verdict"] == "OK"
        assert 1 in result["chosen_thresholds"] or "1" in result["chosen_thresholds"]


class TestDecideForRow:
    def test_matches_direct_probability_computation(self):
        base_price = 1000.0
        interval = {
            "p05": base_price * np.exp(-0.10),
            "p25": base_price * np.exp(-0.02),
            "p75": base_price * np.exp(0.02),
            "p95": base_price * np.exp(0.10),
        }
        result = decide_for_row(interval, base_price, threshold=0.7)
        assert result["probability_of_decline"] == pytest.approx(0.5, abs=1e-4)
        assert result["decision"] == "WAIT"

    def test_result_is_invariant_to_the_base_price(self):
        """The same %-shaped interval around a cheap and an expensive
        commodity must produce the same decision -- this is a check on
        relative price movement, not on absolute rupee levels."""
        for base_price in (30.0, 1000.0, 90000.0):
            interval = {
                "p05": base_price * np.exp(-0.10),
                "p25": base_price * np.exp(-0.06),
                "p75": base_price * np.exp(-0.03),
                "p95": base_price * np.exp(0.01),
            }
            result = decide_for_row(interval, base_price, threshold=0.6)
            assert result["decision"] == "SELL"

    def test_missing_interval_degrades_to_wait(self):
        result = decide_for_row(
            {"p05": None, "p25": None, "p75": None, "p95": None}, 1000.0, threshold=0.6
        )
        assert result["decision"] == "WAIT"
        assert result["probability_of_decline"] is None
