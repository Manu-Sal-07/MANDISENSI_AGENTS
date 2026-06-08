"""
Tiered Model Pipeline — Seasonality Ensemble Orchestrator.

Thin wrapper around AgentEnsemble for SeasonalityAgent.

All ensemble logic (walk-forward CV, inverse-MAPE weighting, weighted
prediction, logging) lives in ensemble.agent_ensemble.AgentEnsemble.
This class provides the public API that SeasonalityAgent calls, which
has been stable since Phase 1.

Public API (backward-compatible):
  pipeline.train_and_select(df, feature_cols, target) -> dict
    Returns: {top_models, weights, metrics, metrics_festival}

  pipeline.ensemble_predict(models_dict, weights, X_future) -> np.ndarray

  pipeline.last_ensemble  -> AgentEnsemble instance after last train_and_select()
    → call pipeline.last_ensemble.get_ensemble_log() for full audit dict
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from mandisense_ai.core.agents.seasonality.models import SEASONALITY_MODEL_REGISTRY
from mandisense_ai.ensemble.agent_ensemble import AgentEnsemble
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class TieredModelPipeline:
    """
    Seasonality pipeline — delegates to AgentEnsemble.

    Parameters
    ----------
    horizon : int
        Forecast horizon in days (used by SeasonalityAgent for rolling forecast).
    top_n : int
        Max models in the final ensemble (default 9 = all seasonality models).
    n_splits : int
        TimeSeriesSplit folds for walk-forward CV.
    """

    def __init__(self, horizon: int = 30, top_n: int = 9, n_splits: int = 5):
        self.horizon  = horizon
        self.top_n    = top_n
        self.n_splits = n_splits

        # Populated after train_and_select(); available for downstream logging
        self.last_ensemble: Optional[AgentEnsemble] = None

    # ------------------------------------------------------------------ #
    # Backward-compatible helpers (SeasonalityAgent calls these directly)
    # ------------------------------------------------------------------ #
    def create_features_labels(
        self, df: pd.DataFrame, target_col: str, lag_cols: List[str]
    ):
        """Extract (X, y) from dataframe.  Kept for backward compatibility."""
        return df[lag_cols].copy(), df[target_col].copy()

    # ------------------------------------------------------------------ #
    def train_and_select(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target: str,
    ) -> Dict[str, Any]:
        """
        Train all seasonality models via AgentEnsemble walk-forward CV.

        Returns
        -------
        dict with keys matching SeasonalityAgent's expectations:
          top_models       : {name: fitted_model}
          weights          : {name: float}
          metrics          : {name: avg_MAPE}
          metrics_festival : {name: festival_MAPE}
        """
        X = df[feature_cols].fillna(0)
        y = df[target]
        regime = (
            df["is_festival"]
            if "is_festival" in df.columns
            else pd.Series(np.zeros(len(df)), index=df.index)
        )

        # Build a fresh AgentEnsemble from the seasonality registry
        ensemble = AgentEnsemble(
            models=SEASONALITY_MODEL_REGISTRY,
            n_splits=self.n_splits,
            top_n=self.top_n,
        )
        ensemble.fit(X, y, regime_flags=regime)

        # Persist for external logging access
        self.last_ensemble = ensemble

        # Reconstruct festival MAPE from CV fold errors (already tracked internally)
        # festival_mape is stored per-model inside the ensemble's cv_results during fit
        # We expose a flat view matching the original dict structure
        festival_mapes = {
            name: round(float(np.mean(folds)), 6)
            for name, folds in ensemble.cv_fold_errors.items()
        }

        log = ensemble.get_ensemble_log()
        logger.info(
            f"[TieredModelPipeline] Ensemble complete — "
            f"best={log['ranked_models'][0][0] if log['ranked_models'] else 'n/a'}, "
            f"n_active={ensemble.n_active_models}"
        )

        return {
            "top_models":       ensemble._fitted_models,
            "weights":          ensemble.weights,
            "metrics":          ensemble.errors,
            "metrics_festival": festival_mapes,
        }

    # ------------------------------------------------------------------ #
    def ensemble_predict(
        self,
        models_dict: Dict[str, Any],
        weights: Dict[str, float],
        X_future: pd.DataFrame,
    ) -> np.ndarray:
        """
        Weighted prediction using the pre-fitted models from train_and_select.

        models_dict and weights are passed in from SeasonalityAgent (which
        holds them from the train_and_select() return dict) — this preserves
        the existing calling convention.

        For new code, prefer: ensemble.predict(X_future) directly.
        """
        if self.last_ensemble is not None:
            # Fast path: delegate entirely to the ensemble object
            return self.last_ensemble.predict(X_future)

        # Fallback: manual weighted sum (used if last_ensemble is not set)
        if not models_dict:
            logger.warning("[TieredModelPipeline] ensemble_predict called with empty models_dict.")
            return np.zeros(len(X_future))

        X_clean    = X_future.fillna(0)
        total_w    = sum(weights.get(n, 0) for n in models_dict) + 1e-12
        result     = np.zeros(len(X_clean))

        for name, model in models_dict.items():
            w = weights.get(name, 0.0) / total_w
            try:
                preds = model.predict(X_clean)
                if np.all(np.isfinite(preds)):
                    result += preds * w
            except Exception as exc:
                logger.warning(f"[TieredModelPipeline][{name}] predict failed: {exc}")

        return result
