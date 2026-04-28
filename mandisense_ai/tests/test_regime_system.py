"""
Test suite for the Regime Detection & Adaptive Weight System (Objective 2).

Covers:
  - Unit tests for each component
  - Integration tests for the full pipeline
  - Performance benchmarks
"""

import time
import pytest
import numpy as np
import pandas as pd


# ====================================================================== #
#  Fixtures                                                               #
# ====================================================================== #

@pytest.fixture
def synthetic_returns():
    """Generate synthetic daily returns mimicking agricultural commodity behaviour."""
    np.random.seed(42)
    n = 1000
    # Three volatility regimes
    low_vol = np.random.normal(0, 0.02, n // 3)
    mid_vol = np.random.normal(0, 0.05, n // 3)
    high_vol = np.random.normal(0, 0.10, n - 2 * (n // 3))
    returns = np.concatenate([low_vol, mid_vol, high_vol])
    dates = pd.date_range("2015-01-01", periods=len(returns), freq="D")
    return pd.Series(returns, index=dates, name="returns")


@pytest.fixture
def synthetic_historical_data(synthetic_returns):
    """Build a DataFrame matching the MetaEnsemble's expected input."""
    prices = (1 + synthetic_returns).cumprod() * 1000
    df = pd.DataFrame({
        "date": synthetic_returns.index,
        "modal_price": prices.values,
        "returns": synthetic_returns.values,
        "arrivals_tonnes": np.random.lognormal(7, 0.5, len(synthetic_returns)),
    })
    return df


@pytest.fixture
def mock_agent_outputs():
    """Standard mock agent outputs for testing."""
    return {
        "seasonality": {"prediction": 0.03, "confidence": 0.75, "metadata": {}},
        "arrival": {"prediction": -0.01, "confidence": 0.82, "metadata": {}},
        "external": {"prediction": 0.05, "confidence": 0.65, "metadata": {}},
    }


# ====================================================================== #
#  1. GARCH Volatility Estimator Tests                                    #
# ====================================================================== #

class TestGARCHVolatilityEstimator:

    def test_fit_converges(self, synthetic_returns):
        from ensemble.regime.garch_estimator import GARCHVolatilityEstimator

        estimator = GARCHVolatilityEstimator(synthetic_returns)
        result = estimator.fit()

        assert result is not None
        assert estimator.fitted_results is not None

    def test_forecast_positive(self, synthetic_returns):
        from ensemble.regime.garch_estimator import GARCHVolatilityEstimator

        estimator = GARCHVolatilityEstimator(synthetic_returns)
        estimator.fit()

        vol = estimator.forecast_volatility(horizon=1)
        assert vol > 0
        assert vol < 10.0  # Sanity upper bound

    def test_forecast_raises_if_unfitted(self, synthetic_returns):
        from ensemble.regime.garch_estimator import GARCHVolatilityEstimator

        estimator = GARCHVolatilityEstimator(synthetic_returns)
        with pytest.raises(ValueError, match="fitted"):
            estimator.forecast_volatility()

    def test_conditional_variance_length(self, synthetic_returns):
        from ensemble.regime.garch_estimator import GARCHVolatilityEstimator

        estimator = GARCHVolatilityEstimator(synthetic_returns)
        estimator.fit()

        cond_var = estimator.get_conditional_variance()
        assert len(cond_var) == len(synthetic_returns)
        assert (cond_var > 0).all()

    def test_rolling_volatility_no_nan(self, synthetic_returns):
        from ensemble.regime.garch_estimator import GARCHVolatilityEstimator

        estimator = GARCHVolatilityEstimator(synthetic_returns, window=252)
        estimator.fit()

        rolling = estimator.get_rolling_volatility(step=50)
        assert not rolling.isna().any(), "Rolling volatility should have no NaN"
        assert len(rolling) > 0

    def test_benchmark_garch_fit(self, synthetic_returns):
        """GARCH fitting must complete in < 5 seconds."""
        from ensemble.regime.garch_estimator import GARCHVolatilityEstimator

        start = time.time()
        estimator = GARCHVolatilityEstimator(synthetic_returns)
        estimator.fit()
        elapsed = time.time() - start

        print(f"GARCH fitting time: {elapsed:.2f}s")
        assert elapsed < 5.0


# ====================================================================== #
#  2. HMM Regime Classifier Tests                                        #
# ====================================================================== #

class TestHMMRegimeClassifier:

    def test_fit_and_predict(self):
        from ensemble.regime.hmm_classifier import HMMRegimeClassifier

        np.random.seed(42)
        features = np.random.randn(500, 4)
        classifier = HMMRegimeClassifier(n_states=4)
        classifier.fit(features)

        assert classifier.fitted
        state, prob = classifier.predict_regime(features[-30:])
        assert state in [1, 2, 3, 4]
        assert 0.0 <= prob <= 1.0

    def test_state_ordering(self):
        """States must be ordered by ascending mean volatility."""
        from ensemble.regime.hmm_classifier import HMMRegimeClassifier

        np.random.seed(42)
        # Create features with clear volatility gradient
        n_each = 200
        low = np.column_stack([
            np.random.normal(0.01, 0.005, n_each),
            np.random.normal(0.01, 0.005, n_each),
            np.random.normal(0, 0.01, n_each),
            np.random.normal(0, 0.5, n_each),
        ])
        high = np.column_stack([
            np.random.normal(0.10, 0.02, n_each),
            np.random.normal(0.10, 0.02, n_each),
            np.random.normal(0, 0.05, n_each),
            np.random.normal(0, 0.5, n_each),
        ])
        features = np.vstack([low, high])

        classifier = HMMRegimeClassifier(n_states=4)
        classifier.fit(features)
        stats = classifier.get_state_statistics()

        # States should be ordered by mean volatility
        vols = [stats[s]["mean_volatility"] for s in range(1, 5)]
        assert vols == sorted(vols), f"States not sorted by volatility: {vols}"

    def test_regime_probabilities_sum_to_one(self):
        from ensemble.regime.hmm_classifier import HMMRegimeClassifier

        np.random.seed(42)
        features = np.random.randn(300, 4)
        classifier = HMMRegimeClassifier(n_states=4)
        classifier.fit(features)

        probs = classifier.get_regime_probabilities(features[-30:])
        assert abs(probs.sum() - 1.0) < 1e-6

    def test_predict_unfitted_raises(self):
        from ensemble.regime.hmm_classifier import HMMRegimeClassifier

        classifier = HMMRegimeClassifier(n_states=4)
        with pytest.raises(ValueError, match="fitted"):
            classifier.predict_regime(np.random.randn(10, 4))

    def test_benchmark_hmm_prediction(self):
        """HMM prediction must complete in < 50ms."""
        from ensemble.regime.hmm_classifier import HMMRegimeClassifier

        np.random.seed(42)
        features = np.random.randn(1000, 4)
        classifier = HMMRegimeClassifier(n_states=4)
        classifier.fit(features)

        start = time.time()
        classifier.predict_regime(features[-30:])
        elapsed_ms = (time.time() - start) * 1000

        print(f"HMM prediction time: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 50


# ====================================================================== #
#  3. Adaptive Weight Calculator Tests                                    #
# ====================================================================== #

class TestAdaptiveWeightCalculator:

    def test_weights_sum_to_one(self, mock_agent_outputs):
        from ensemble.regime.weight_calculator import AdaptiveWeightCalculator

        calc = AdaptiveWeightCalculator()
        weights = calc.compute_weights(mock_agent_outputs, current_regime=2, transition_prob=0.8)
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_constraints_enforced(self, mock_agent_outputs):
        """Min 0.1, max 0.7 must always hold."""
        from ensemble.regime.weight_calculator import AdaptiveWeightCalculator

        calc = AdaptiveWeightCalculator()
        # Create extreme error disparity
        calc.error_tracker["seasonality"].extend([0.001] * 14)
        calc.error_tracker["arrival"].extend([10.0] * 14)
        calc.error_tracker["external"].extend([5.0] * 14)

        weights = calc.compute_weights(mock_agent_outputs, current_regime=1, transition_prob=0.9)

        for w in weights.values():
            assert w >= 0.1 - 1e-6, f"Weight {w} below minimum 0.1"
            assert w <= 0.7 + 1e-6, f"Weight {w} above maximum 0.7"

    def test_regime_changes_shift_weights(self, mock_agent_outputs):
        """Different regimes should produce different weight distributions."""
        from ensemble.regime.weight_calculator import AdaptiveWeightCalculator

        calc = AdaptiveWeightCalculator()

        w_stable = calc.compute_weights(mock_agent_outputs, current_regime=1, transition_prob=0.9)
        calc.prev_weights = {"seasonality": 0.33, "arrival": 0.33, "external": 0.34}
        w_crisis = calc.compute_weights(mock_agent_outputs, current_regime=4, transition_prob=0.9)

        # In crisis, external should have higher weight than in stable
        assert w_crisis["external"] > w_stable["external"]

    def test_smoothing_on_low_transition_prob(self, mock_agent_outputs):
        """Low transition prob should blend with previous weights."""
        from ensemble.regime.weight_calculator import AdaptiveWeightCalculator

        calc = AdaptiveWeightCalculator()
        initial = calc.prev_weights.copy()

        # Low confidence → weights should be closer to previous
        w_low = calc.compute_weights(mock_agent_outputs, current_regime=4, transition_prob=0.3)

        # Reset and try high confidence
        calc2 = AdaptiveWeightCalculator()
        w_high = calc2.compute_weights(mock_agent_outputs, current_regime=4, transition_prob=0.9)

        # Low confidence weights should be closer to uniform (initial)
        dist_low = sum(abs(w_low[a] - initial[a]) for a in w_low)
        dist_high = sum(abs(w_high[a] - initial[a]) for a in w_high)
        assert dist_low <= dist_high + 0.01  # Allow small tolerance

    def test_weight_explanation(self, mock_agent_outputs):
        from ensemble.regime.weight_calculator import AdaptiveWeightCalculator

        calc = AdaptiveWeightCalculator()
        weights = calc.compute_weights(mock_agent_outputs, current_regime=3, transition_prob=0.8)
        explanation = calc.get_weight_explanation(weights, regime=3)

        assert "regime" in explanation
        assert "dominant_agent" in explanation
        assert "reasoning" in explanation

    def test_benchmark_weight_calculation(self, mock_agent_outputs):
        """Weight calculation must complete in < 20ms."""
        from ensemble.regime.weight_calculator import AdaptiveWeightCalculator

        calc = AdaptiveWeightCalculator()
        for _ in range(30):
            calc.update_error("seasonality", 0.05, 0.04)
            calc.update_error("arrival", -0.02, -0.01)
            calc.update_error("external", 0.1, 0.08)

        start = time.time()
        calc.compute_weights(mock_agent_outputs, current_regime=2, transition_prob=0.8)
        elapsed_ms = (time.time() - start) * 1000

        print(f"Weight calculation time: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 20


# ====================================================================== #
#  4. Volatility Alert Engine Tests                                       #
# ====================================================================== #

class TestVolatilityAlertEngine:

    def test_normal_no_alert(self):
        from ensemble.regime.alert_engine import VolatilityAlertEngine

        hist = pd.Series(np.random.lognormal(0, 0.3, 1000))
        engine = VolatilityAlertEngine(hist)

        alert = engine.check_alert(hist.mean())
        assert not alert["alert_triggered"]
        assert alert["level"] == "NORMAL"

    def test_warning_alert(self):
        from ensemble.regime.alert_engine import VolatilityAlertEngine

        hist = pd.Series(np.random.lognormal(0, 0.3, 1000))
        engine = VolatilityAlertEngine(hist)

        # Just above 2σ
        high_vol = hist.mean() + 2.1 * hist.std()
        alert = engine.check_alert(high_vol)
        assert alert["alert_triggered"]
        assert alert["level"] == "WARNING"

    def test_critical_alert(self):
        from ensemble.regime.alert_engine import VolatilityAlertEngine

        hist = pd.Series(np.random.lognormal(0, 0.3, 1000))
        engine = VolatilityAlertEngine(hist)

        high_vol = hist.mean() + 3.1 * hist.std()
        alert = engine.check_alert(high_vol)
        assert alert["alert_triggered"]
        assert alert["level"] == "CRITICAL"

    def test_extreme_alert(self):
        from ensemble.regime.alert_engine import VolatilityAlertEngine

        hist = pd.Series(np.random.lognormal(0, 0.3, 1000))
        engine = VolatilityAlertEngine(hist)

        extreme_vol = hist.mean() + 4.1 * hist.std()
        alert = engine.check_alert(extreme_vol)
        assert alert["alert_triggered"]
        assert alert["level"] == "EXTREME"

    def test_forecast_alert(self):
        from ensemble.regime.alert_engine import VolatilityAlertEngine

        hist = pd.Series(np.random.lognormal(0, 0.3, 1000))
        engine = VolatilityAlertEngine(hist)

        high_forecast = hist.mean() + 3 * hist.std()
        alert = engine.check_alert(hist.mean(), forecasted_volatility=high_forecast)
        assert alert["forecast_alert"] is not None

    def test_risk_categories(self):
        from ensemble.regime.alert_engine import VolatilityAlertEngine

        hist = pd.Series(np.random.lognormal(0, 0.3, 1000))
        engine = VolatilityAlertEngine(hist)

        assert engine.get_risk_category(hist.mean()) == "Low"
        assert engine.get_risk_category(hist.mean() + 2.5 * hist.std()) == "Medium"
        assert engine.get_risk_category(hist.mean() + 3.5 * hist.std()) == "High"
        assert engine.get_risk_category(hist.mean() + 4.5 * hist.std()) == "Extreme"


# ====================================================================== #
#  5. End-to-End Integration Tests                                        #
# ====================================================================== #

class TestRegimeAwareMetaEnsemble:

    def test_end_to_end_pipeline(self, synthetic_historical_data, mock_agent_outputs):
        from ensemble.regime.meta_ensemble import RegimeAwareMetaEnsemble

        ensemble = RegimeAwareMetaEnsemble(
            synthetic_historical_data, garch_rolling_step=50
        )

        forecast = ensemble.generate_forecast(
            mock_agent_outputs, synthetic_historical_data.tail(90)
        )

        # Validate output structure
        assert "final_prediction" in forecast
        assert "regime" in forecast
        assert "weights" in forecast
        assert "volatility" in forecast
        assert "agent_contributions" in forecast
        assert "weight_explanation" in forecast

        # Validate regime classification
        assert forecast["regime"]["current_state"] in [1, 2, 3, 4]
        assert forecast["regime"]["state_name"] in [
            "Stable", "Medium Volatility", "High Volatility", "Crisis"
        ]

        # Validate weights sum to 1
        assert abs(sum(forecast["weights"].values()) - 1.0) < 1e-6

        # Validate volatility info
        assert forecast["volatility"]["current"] > 0
        assert forecast["volatility"]["risk_category"] in [
            "Low", "Medium", "High", "Extreme"
        ]

    def test_forecast_uses_all_agents(self, synthetic_historical_data, mock_agent_outputs):
        from ensemble.regime.meta_ensemble import RegimeAwareMetaEnsemble

        ensemble = RegimeAwareMetaEnsemble(
            synthetic_historical_data, garch_rolling_step=50
        )

        forecast = ensemble.generate_forecast(
            mock_agent_outputs, synthetic_historical_data.tail(90)
        )

        # All three agents should appear in contributions
        for agent in ["seasonality", "arrival", "external"]:
            assert agent in forecast["agent_contributions"]
            assert forecast["agent_contributions"][agent]["weight"] > 0

    def test_prediction_is_weighted_sum(self, synthetic_historical_data, mock_agent_outputs):
        from ensemble.regime.meta_ensemble import RegimeAwareMetaEnsemble

        ensemble = RegimeAwareMetaEnsemble(
            synthetic_historical_data, garch_rolling_step=50
        )

        forecast = ensemble.generate_forecast(
            mock_agent_outputs, synthetic_historical_data.tail(90)
        )

        # Manually verify weighted sum
        expected = sum(
            forecast["weights"][a] * mock_agent_outputs[a]["prediction"]
            for a in forecast["weights"]
        )
        assert abs(forecast["final_prediction"] - expected) < 1e-10
