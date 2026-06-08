"""
Ridge Regression Seasonality Model.

Why this model?
  Ridge (L2 regularisation) is a high-bias, low-variance model.  It acts as a
  strong, stable anchor in the ensemble — when commodity prices are in a
  relatively stable seasonal pattern, Ridge typically beats tree-based models
  in out-of-sample MAPE, earning a higher inverse-MAPE weight automatically.

  It also serves as the go-to fallback model for mandis with limited data
  (< 500 rows), where gradient boosters tend to overfit.

  Feature standardisation is applied internally so raw feature magnitudes
  (arrival tonnes vs price lags) don't bias the regularisation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from mandisense_ai.core.agents.seasonality.models.base import BaseSeasonalityModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class RidgeSeasonalityModel(BaseSeasonalityModel):
    """Ridge Regression with internal StandardScaler."""

    model_name = "Ridge"

    def __init__(self, alpha: float = 1.0):
        self._ridge = Ridge(alpha=alpha)
        self._scaler = StandardScaler()
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RidgeSeasonalityModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows, alpha={self._ridge.alpha}.")
        X_filled = X.fillna(0).values
        X_scaled = self._scaler.fit_transform(X_filled)
        self._ridge.fit(X_scaled, y)
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        X_scaled = self._scaler.transform(X.fillna(0).values)
        return self._ridge.predict(X_scaled)
