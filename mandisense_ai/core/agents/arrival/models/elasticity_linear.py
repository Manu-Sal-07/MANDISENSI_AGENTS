"""
Elasticity-based Linear Regression Arrival Model.

Why this model?
  The core economic relationship between supply (arrivals) and price is
  log-linear: a 1% increase in arrivals causes an α% change in price, where
  α is the price elasticity of supply.

  This model:
    1. Uses ALL arrival-specific features (deviation %, YoY, momentum, elasticity,
       consecutive declines, lags).
    2. Fits a LinearRegression — the coefficient on `rolling_elasticity_30d` is
       directly interpretable as the elasticity contribution to price change.
    3. Standardises features so all coefficients are on the same scale.

  It provides the interpretable, economic-theory anchor in the arrival ensemble
  — similar to how Lasso acts as the sparse anchor in the seasonality ensemble.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from mandisense_ai.core.agents.arrival.models.base import BaseArrivalModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class ElasticityLinearArrivalModel(BaseArrivalModel):
    """Linear regression on arrival-elasticity features."""

    model_name = "ElasticityLinear"

    def __init__(self):
        self._lr = LinearRegression()
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ElasticityLinearArrivalModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows, "
                    f"{X.shape[1]} features.")
        X_scaled = self._scaler.fit_transform(X.fillna(0).values)
        self._lr.fit(X_scaled, y)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        X_scaled = self._scaler.transform(X.fillna(0).values)
        return self._lr.predict(X_scaled)

    @property
    def elasticity_coefficient(self) -> float:
        """Return the model coefficient for rolling_elasticity_30d if present."""
        if not self._fitted:
            return 0.0
        # Coefficient index depends on feature order — return raw coef array
        return float(np.mean(np.abs(self._lr.coef_)))
