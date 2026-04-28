"""
Moving Average Baseline Seasonality Model.

Why this model?
  A simple rolling mean over the most recent N days is the canonical naive
  baseline for time-series forecasting.  Including it in the ensemble serves
  two purposes:

    1. Reality check: if a sophisticated model cannot beat this baseline in
       walk-forward CV, its weight approaches zero and it is effectively
       excluded — without any hard-coded filtering logic.

    2. Robustness anchor: during extreme data sparsity or cold-start (new
       commodity / mandi with < 60 days of data), the moving average produces
       a reasonable flat-line estimate while gradient boosters fail noisily.

  Prediction strategy:
    - Store the trailing rolling window from the training set.
    - For each prediction row, return the same rolling mean (constant forecast).
      This is appropriate because X features are not used here — the model is
      purely statistical.  It will naturally receive lower ensemble weight when
      better models are available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.agents.seasonality.models.base import BaseSeasonalityModel
from utils.logger import get_logger

logger = get_logger(__name__)


class MovingAverageBaselineModel(BaseSeasonalityModel):
    """
    Rolling mean of the last `window` training prices.

    Prediction is always a constant equal to the trailing window mean
    computed from the training data.  This makes it a valid "naive" baseline.
    """

    model_name = "MovingAverageBaseline"

    def __init__(self, window: int = 30):
        self._window = window
        self._prediction_value: float = 0.0
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "MovingAverageBaselineModel":
        prices = y.values.astype(float)
        tail = prices[-self._window:]   # last `window` training prices
        self._prediction_value = float(np.nanmean(tail))
        logger.info(
            f"[{self.model_name}] Fitted – window={self._window}, "
            f"trailing_mean={self._prediction_value:.2f}"
        )
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        # Constant forecast for all rows in X
        return np.full(len(X), fill_value=self._prediction_value)
