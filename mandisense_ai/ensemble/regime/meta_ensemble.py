"""
RegimeAwareMetaEnsemble — Master orchestration layer.

Integrates GARCH volatility estimation, HMM regime classification, and
adaptive weight calculation to produce final predictions with full
explainability.

Responsibilities:
  - Coordinate all regime detection components
  - Generate unified predictions from 3 agents
  - Provide comprehensive explainability
  - Handle edge cases with safe fallbacks
  - Support backtesting on historical data
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ensemble.regime.garch_estimator import GARCHVolatilityEstimator
from ensemble.regime.hmm_classifier import HMMRegimeClassifier
from ensemble.regime.weight_calculator import AdaptiveWeightCalculator
from ensemble.regime.alert_engine import VolatilityAlertEngine
from utils.logger import get_logger

logger = get_logger(__name__)

REGIME_NAMES = {1: "Stable", 2: "Medium Volatility", 3: "High Volatility", 4: "Crisis"}


class RegimeAwareMetaEnsemble:
    """
    Master orchestration layer for regime-aware ensemble forecasting.

    Parameters
    ----------
    historical_data : pd.DataFrame
        DataFrame with columns: date, modal_price, and optionally arrivals_tonnes.
        Must have at least 300 rows for meaningful volatility estimation.
    garch_rolling_step : int
        Re-fit GARCH every N days during rolling volatility (speed trade-off).
    """

    def __init__(self, historical_data: pd.DataFrame, garch_rolling_step: int = 5):
        required = {"date", "modal_price"}
        missing = required - set(historical_data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        self.historical_data = historical_data.copy()
        self._prepare_returns()

        self.garch_estimator: Optional[GARCHVolatilityEstimator] = None
        self.hmm_classifier: Optional[HMMRegimeClassifier] = None
        self.weight_calculator = AdaptiveWeightCalculator()
        self.alert_engine: Optional[VolatilityAlertEngine] = None

        self._garch_rolling_step = garch_rolling_step
        self._initialize_volatility_model()
        self._initialize_regime_model()

    def _prepare_returns(self) -> None:
        """Calculate returns from modal_price if not present."""
        if "returns" not in self.historical_data.columns:
            self.historical_data["returns"] = (
                self.historical_data["modal_price"].pct_change()
            )
        # Fill first NaN return with 0
        self.historical_data["returns"] = self.historical_data["returns"].fillna(0)

    def _initialize_volatility_model(self) -> None:
        """Fit GARCH model and initialise alert engine."""
        logger.info("[MetaEnsemble] Initialising GARCH volatility model...")
        returns = self.historical_data["returns"].dropna()

        self.garch_estimator = GARCHVolatilityEstimator(returns)
        self.garch_estimator.fit()

        # Compute rolling volatility for alert engine baseline
        rolling_vol = self.garch_estimator.get_rolling_volatility(
            step=self._garch_rolling_step
        )
        self.alert_engine = VolatilityAlertEngine(rolling_vol)

        logger.info(f"[MetaEnsemble] GARCH model fitted ({len(rolling_vol)} rolling obs)")

    def _initialize_regime_model(self) -> None:
        """Prepare features and fit HMM regime classifier."""
        logger.info("[MetaEnsemble] Initialising HMM regime classifier...")
        df = self.historical_data

        # GARCH volatility (in-sample conditional volatility, fast)
        cond_vol = self.garch_estimator.get_conditional_variance()
        df = df.iloc[-len(cond_vol):].copy()
        df["garch_volatility"] = cond_vol.values

        # Realised volatility (7-day rolling std)
        df["realized_volatility"] = df["returns"].rolling(7).std()

        # Momentum (7-day cumulative return)
        df["momentum"] = df["returns"].rolling(7).sum()

        # Volume stress
        if "arrivals_tonnes" in df.columns:
            mean_a = df["arrivals_tonnes"].mean()
            std_a = df["arrivals_tonnes"].std()
            df["volume_stress"] = (
                (df["arrivals_tonnes"] - mean_a) / (std_a + 1e-9)
            )
        else:
            df["volume_stress"] = 0.0

        # Drop NaN rows
        feature_data = df.dropna(
            subset=["garch_volatility", "realized_volatility", "momentum", "volume_stress"]
        )
        self._feature_data = feature_data  # cache for backtesting

        self.hmm_classifier = HMMRegimeClassifier(n_states=4)
        features = self.hmm_classifier.prepare_features(feature_data)
        self.hmm_classifier.fit(features)

        logger.info(f"[MetaEnsemble] HMM fitted on {len(features)} observations")

    # ------------------------------------------------------------------ #
    #  Primary API — Generate Forecast                                    #
    # ------------------------------------------------------------------ #
    def generate_forecast(
        self,
        agent_outputs: Dict[str, Dict[str, Any]],
        current_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Generate final ensemble prediction with regime awareness.

        Parameters
        ----------
        agent_outputs : dict
            {
                'seasonality': {prediction, confidence, metadata},
                'arrival':     {prediction, confidence, metadata},
                'external':    {prediction, confidence, metadata}
            }
        current_data : pd.DataFrame
            Recent market data (last 30–90 days) with modal_price, returns.

        Returns
        -------
        dict
            Comprehensive forecast including prediction, regime info,
            volatility alerts, weight breakdown, and explainability.
        """
        # Step 1: Estimate current & forecasted volatility
        current_vol = self._safe_forecast_volatility(horizon=1)
        forecasted_vol_7d = self._safe_forecast_volatility(horizon=7)

        # Step 2: Prepare features for regime detection
        regime_features = self._build_regime_features(current_data, current_vol)

        # Step 3: Detect current regime
        current_regime, transition_prob = self.hmm_classifier.predict_regime(regime_features)

        # Step 4: Update agent weights
        weights = self.weight_calculator.compute_weights(
            agent_outputs, current_regime, transition_prob
        )

        # Step 5: Weighted ensemble prediction
        final_prediction = sum(
            weights[agent] * agent_outputs[agent]["prediction"]
            for agent in weights
        )

        # Step 6: Ensemble confidence
        ensemble_confidence = sum(
            weights[agent] * agent_outputs[agent]["confidence"]
            for agent in weights
        )

        # Step 7: Volatility alerts
        alert_info = self.alert_engine.check_alert(current_vol, forecasted_vol_7d)

        # Step 8: Weight explanation
        weight_explanation = self.weight_calculator.get_weight_explanation(
            weights, current_regime
        )

        return {
            "final_prediction": final_prediction,
            "ensemble_confidence": ensemble_confidence,
            "regime": {
                "current_state": current_regime,
                "state_name": REGIME_NAMES[current_regime],
                "transition_probability": transition_prob,
                "confidence_level": "High" if transition_prob > 0.7 else "Medium",
            },
            "volatility": {
                "current": current_vol,
                "forecasted_7d": forecasted_vol_7d,
                "risk_category": self.alert_engine.get_risk_category(current_vol),
                "alert": alert_info,
            },
            "weights": weights,
            "weight_explanation": weight_explanation,
            "agent_contributions": {
                agent: {
                    "weight": weights[agent],
                    "prediction": agent_outputs[agent]["prediction"],
                    "confidence": agent_outputs[agent]["confidence"],
                    "contribution": weights[agent] * agent_outputs[agent]["prediction"],
                    "contribution_pct": (
                        (weights[agent] * agent_outputs[agent]["prediction"] / final_prediction * 100)
                        if final_prediction != 0 else 0.0
                    ),
                }
                for agent in weights
            },
            "metadata": {
                "timestamp": pd.Timestamp.now().isoformat(),
                "data_points_used": len(current_data),
                "regime_statistics": self.hmm_classifier.get_state_statistics().get(
                    current_regime, {}
                ),
            },
        }

    # ------------------------------------------------------------------ #
    #  Backtesting                                                        #
    # ------------------------------------------------------------------ #
    def backtest(
        self,
        test_data: pd.DataFrame,
        agent_outputs_history: List[Dict[str, Dict]],
    ) -> Dict[str, Any]:
        """
        Backtest ensemble performance on historical data.

        Parameters
        ----------
        test_data : pd.DataFrame
            Out-of-sample test data with returns and modal_price.
        agent_outputs_history : list[dict]
            One agent_outputs dict per test row.

        Returns
        -------
        dict
            Backtesting results with overall and regime-specific metrics.
        """
        predictions, actuals, regimes, weights_history = [], [], [], []

        for i in range(len(test_data)):
            agent_outputs = agent_outputs_history[i]
            current_window = test_data.iloc[: i + 1].tail(30)

            try:
                forecast = self.generate_forecast(agent_outputs, current_window)
                predictions.append(forecast["final_prediction"])
                regimes.append(forecast["regime"]["current_state"])
                weights_history.append(forecast["weights"])
            except Exception as exc:
                logger.warning(f"[MetaEnsemble] Backtest step {i} failed: {exc}")
                predictions.append(0.0)
                regimes.append(1)
                weights_history.append(self.weight_calculator.prev_weights)

            actuals.append(test_data.iloc[i]["returns"])

        preds = np.array(predictions)
        acts = np.array(actuals)
        mae = float(np.mean(np.abs(preds - acts)))
        rmse = float(np.sqrt(np.mean((preds - acts) ** 2)))

        regime_perf = {}
        for r in [1, 2, 3, 4]:
            mask = np.array(regimes) == r
            if mask.sum() > 0:
                regime_perf[r] = {
                    "mae": float(np.mean(np.abs(preds[mask] - acts[mask]))),
                    "n_observations": int(mask.sum()),
                }

        return {
            "overall_performance": {"mae": mae, "rmse": rmse, "n_predictions": len(preds)},
            "regime_performance": regime_perf,
            "weights_stability": self._calc_weight_stability(weights_history),
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    def _safe_forecast_volatility(self, horizon: int = 1) -> float:
        """Forecast with fallback to realised volatility."""
        try:
            return self.garch_estimator.forecast_volatility(horizon)
        except Exception as exc:
            logger.error(f"[MetaEnsemble] GARCH forecast failed: {exc}")
            fallback = float(self.historical_data["returns"].tail(30).std())
            return max(fallback, 0.001)

    def _build_regime_features(
        self, current_data: pd.DataFrame, current_vol: float
    ) -> np.ndarray:
        """Build scaled feature matrix for regime detection from recent data."""
        df = current_data.copy()
        df["garch_volatility"] = current_vol
        df["realized_volatility"] = df["returns"].rolling(7).std() if "returns" in df.columns else 0.0
        df["momentum"] = df["returns"].rolling(7).sum() if "returns" in df.columns else 0.0

        if "arrivals_tonnes" in df.columns:
            mean_a = self.historical_data["arrivals_tonnes"].mean()
            std_a = self.historical_data["arrivals_tonnes"].std()
            df["volume_stress"] = (df["arrivals_tonnes"] - mean_a) / (std_a + 1e-9)
        else:
            df["volume_stress"] = 0.0

        # Fill NaN from rolling calculations
        for col in ["realized_volatility", "momentum", "volume_stress"]:
            df[col] = df[col].fillna(0.0)

        tail = df.tail(30)
        return self.hmm_classifier.prepare_features(tail)

    @staticmethod
    def _calc_weight_stability(weights_history: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate stability metrics for weight changes over time."""
        if len(weights_history) < 2:
            return {"mean_change": 0.0, "max_change": 0.0, "stability_score": 1.0}

        changes = []
        for i in range(1, len(weights_history)):
            total_change = sum(
                abs(weights_history[i].get(a, 0) - weights_history[i - 1].get(a, 0))
                for a in weights_history[i]
            )
            changes.append(total_change)

        return {
            "mean_change": float(np.mean(changes)),
            "max_change": float(np.max(changes)),
            "stability_score": float(1.0 - np.mean(changes)),
        }

    # ------------------------------------------------------------------ #
    #  Model persistence                                                  #
    # ------------------------------------------------------------------ #
    def save_models(self, directory: str) -> None:
        """Save all sub-models to a directory."""
        from pathlib import Path
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        self.garch_estimator.save(str(path / "garch_model.pkl"))
        self.hmm_classifier.save(str(path / "hmm_model.pkl"))
        logger.info(f"[MetaEnsemble] All models saved to {directory}")

    def __repr__(self) -> str:
        return (
            f"<RegimeAwareMetaEnsemble "
            f"n_hist={len(self.historical_data)}, "
            f"garch={self.garch_estimator}, "
            f"hmm={self.hmm_classifier}>"
        )
