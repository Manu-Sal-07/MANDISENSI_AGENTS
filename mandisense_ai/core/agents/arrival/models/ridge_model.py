"""
Ridge Regression Arrival Model.

Why this model?
  Ridge regression (L2 regularisation) prevents the multi-collinearity problem
  that is endemic in the arrival feature set: `arrivals_7d_mean`,
  `arrivals_30d_mean`, and the lag columns are all highly correlated.

  Without regularisation, OLS coefficients become numerically unstable when
  features are correlated.  Ridge shrinks all coefficients simultaneously,
  giving a stable linear estimate that is particularly reliable when the supply
  structure is changing (post-regime-break) and tree-based models are
  over-fitting to the recent anomalous period.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from core.agents.arrival.models.base import BaseArrivalModel
from utils.logger import get_logger

logger = get_logger(__name__)


class RidgeArrivalModel(BaseArrivalModel):
    """Ridge Regression for arrival-driven 7-day price-change % prediction."""

    model_name = "Ridge"

    def __init__(self, alpha: float = 1.0):
        self._ridge = Ridge(alpha=alpha)
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RidgeArrivalModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows, alpha={self._ridge.alpha}.")
        X_scaled = self._scaler.fit_transform(X.fillna(0).values)
        self._ridge.fit(X_scaled, y)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        X_scaled = self._scaler.transform(X.fillna(0).values)
        return self._ridge.predict(X_scaled)
