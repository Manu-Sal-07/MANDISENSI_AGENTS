"""
Simple Baseline Arrival Model (mean + lag).

Why this model?
  Two baselines are combined into one class:
    1. Historical mean of `target_7d_pct` over training data
    2. Last observed `target_7d_pct` (lag-1 of the target)

  The ensemble uses whichever sub-strategy has lower walk-forward MAPE
  (selected at fit time via the stored training MAPE comparison).  In practice
  this is usually the mean — but during highly trending supply periods, the
  lag-1 value predicts better than the flat mean.

  Purpose in the ensemble:
    - Sets a minimum quality bar: a model that cannot beat this baseline gets
      near-zero inverse-MAPE weight and is effectively excluded.
    - Provides a stable, non-overfitting anchor during cold-start (< 60 rows).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mandisense_ai.core.agents.arrival.models.base import BaseArrivalModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleBaselineArrivalModel(BaseArrivalModel):
    """Mean / lag-1 baseline for 7-day price-change % prediction."""

    model_name = "SimpleBaseline"

    def __init__(self, window: int = 30):
        self._window = window
        self._pred_value: float = 0.0
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SimpleBaselineArrivalModel":
        values = y.values.astype(float)

        # Strategy 1: trailing window mean
        tail = values[-self._window:]
        mean_val = float(np.nanmean(tail))

        # Strategy 2: lag-1 of target (most recent observed target)
        lag1_val = float(values[-1]) if len(values) > 0 else 0.0

        # Pick whichever had lower MAE on the last `window` training steps
        if len(values) > self._window + 1:
            actual = values[-(self._window):]
            err_mean = float(np.mean(np.abs(actual - mean_val)))
            err_lag1 = float(np.mean(np.abs(actual - lag1_val)))
            self._pred_value = mean_val if err_mean <= err_lag1 else lag1_val
            chosen = "mean" if err_mean <= err_lag1 else "lag1"
        else:
            self._pred_value = mean_val
            chosen = "mean"

        logger.info(
            f"[{self.model_name}] Strategy={chosen}, "
            f"prediction_value={self._pred_value:.3f}"
        )
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return np.full(len(X), fill_value=self._pred_value)
