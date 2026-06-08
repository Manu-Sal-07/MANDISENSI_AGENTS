"""
Lag-based Linear Regression Seasonality Model.

Why this model?
  Auto-regressive (lag-only) linear models are the classical building block of
  ARIMA-family forecasters.  In an ensemble context they add complementary
  signal: while tree-based models capture non-linear feature interactions, this
  model provides a *linear projection from the recent price history* — exactly
  what matters when the commodity is in a stable, trend-following regime.

  Feature set used: ONLY lag columns (`price_lag_*`) from X.  Other columns
  (calendar dummies, arrivals) are deliberately excluded to keep this model
  focused on auto-regressive structure and to diversify ensemble predictions.

  If no lag columns exist in X, the model falls back to using all columns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from mandisense_ai.core.agents.seasonality.models.base import BaseSeasonalityModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Column name substring that identifies lag features
_LAG_SUBSTRING = "price_lag"


class LagLinearModel(BaseSeasonalityModel):
    """
    LinearRegression trained exclusively on price-lag columns.

    This model deliberately ignores calendar and arrival features so that
    its predictions are driven purely by recent price momentum — providing
    diversity relative to the tree-based models in the ensemble.
    """

    model_name = "LagLinear"

    def __init__(self):
        self._lr = LinearRegression()
        self._scaler = StandardScaler()
        self._lag_cols: list[str] = []
        self._fitted = False

    # ------------------------------------------------------------------ #
    def _select_lag_cols(self, X: pd.DataFrame) -> list[str]:
        lag_cols = [c for c in X.columns if _LAG_SUBSTRING in c]
        if not lag_cols:
            logger.warning(
                f"[{self.model_name}] No '{_LAG_SUBSTRING}' columns found; "
                "using all columns as fallback."
            )
            lag_cols = list(X.columns)
        return lag_cols

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LagLinearModel":
        self._lag_cols = self._select_lag_cols(X)
        logger.info(
            f"[{self.model_name}] Fitting on lag cols: {self._lag_cols} "
            f"({len(X)} rows)."
        )
        X_lag = X[self._lag_cols].fillna(0).values
        X_scaled = self._scaler.fit_transform(X_lag)
        self._lr.fit(X_scaled, y)
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        # Only use the same lag columns; fill missing with 0
        X_lag = X.reindex(columns=self._lag_cols, fill_value=0).fillna(0).values
        X_scaled = self._scaler.transform(X_lag)
        return self._lr.predict(X_scaled)
