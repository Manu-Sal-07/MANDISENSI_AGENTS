"""
Dynamic Weighter for Ensemble.

Applies Exponential Moving Average (EMA) smoothing and dynamic
regime-based boosts to update base weights.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

try:
    from mandisense_ai.ensemble.feedback_store import FeedbackStore
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from ensemble.feedback_store import FeedbackStore
    from utils.logger import get_logger

logger = get_logger(__name__)


class DynamicWeighter:
    """Adjusts model weights dynamically using rolling performance and active regimes."""

    def __init__(self, feedback_store: FeedbackStore, alpha: float = 0.3):
        self.store = feedback_store
        self.alpha = alpha  # EMA decay factor. Higher means more responsive to recent errors.

        # Define which models get boosted under which conditions
        self.festival_models = ["STLLinearRegression", "SARIMA", "PolynomialRegression"]
        self.shock_models = ["GradientBoosting", "RandomForest", "XGBoost"]

    def adjust_weights(
        self,
        base_weights: Dict[str, float],
        agent_type: str,
        commodity: str,
        mandi: str,
        regimes: Dict[str, bool],
        boost_factor: float = 1.3
    ) -> Dict[str, float]:
        """
        Adjust weights by combining base weights with rolling errors and regime boosts.

        Args:
            base_weights: Inverse-MAPE weights calculated from the CV phase.
            agent_type: "Seasonality" or "ArrivalVolume".
            commodity: Commodity string.
            mandi: Mandi string.
            regimes: Dictionary of active regimes from RegimeDetector.
            boost_factor: Multiplier for models that match active regimes.

        Returns:
            Normalized dynamically adjusted weights.
        """
        if not base_weights:
            return {}

        dynamic_weights = {}
        total_weight = 0.0

        for model_name, base_w in base_weights.items():
            # 1. Rolling Performance Adjustment
            rolling_mape = self.store.get_rolling_mape(
                agent_type=agent_type,
                commodity=commodity,
                mandi=mandi,
                model_name=model_name,
                n_days=30
            )

            if rolling_mape is not None and rolling_mape > 0:
                historical_w = 1.0 / rolling_mape
                # EMA smoothing
                smoothed_w = self.alpha * historical_w + (1 - self.alpha) * base_w
            else:
                smoothed_w = base_w

            # 2. Regime-Based Adjustment
            boost = 1.0
            if regimes.get("festival") and model_name in self.festival_models:
                logger.info(f"[{agent_type}] Boosting {model_name} due to Festival regime.")
                boost *= boost_factor
                
            if regimes.get("supply_shock") and model_name in self.shock_models:
                logger.info(f"[{agent_type}] Boosting {model_name} due to Supply Shock regime.")
                boost *= boost_factor

            adjusted_w = smoothed_w * boost
            dynamic_weights[model_name] = adjusted_w
            total_weight += adjusted_w

        # Normalize
        if total_weight > 0:
            for name in dynamic_weights:
                dynamic_weights[name] /= total_weight
        else:
            # Fallback to base weights
            return base_weights

        return dynamic_weights
