"""
Lasso Regression Arrival Model.

Why this model?
  The arrival feature set contains many engineered columns (multiple lag lengths,
  rolling means at 7/30 days, YoY deviations, momentum slopes).  Many of these
  are redundant or collinear.  Lasso drives redundant feature coefficients to
  exactly zero, producing a sparse model that is:

    - More interpretable  : only the truly predictive arrival signals survive
    - Less prone to overfit: fewer effective parameters relative to dataset size
    - Regime-resilient    : drops features from the old regime automatically

  alpha=0.05 is chosen to retain ~50% of features; tunable via __init__.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso
from sklearn.preprocessing import StandardScaler

from core.agents.arrival.models.base import BaseArrivalModel
from utils.logger import get_logger

logger = get_logger(__name__)


class LassoArrivalModel(BaseArrivalModel):
    """Lasso Regression for arrival-driven 7-day price-change % prediction."""

    model_name = "Lasso"

    def __init__(self, alpha: float = 0.05, max_iter: int = 3000):
        self._lasso = Lasso(alpha=alpha, max_iter=max_iter)
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LassoArrivalModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows, alpha={self._lasso.alpha}.")
        X_scaled = self._scaler.fit_transform(X.fillna(0).values)
        self._lasso.fit(X_scaled, y)
        n_selected = int(np.sum(self._lasso.coef_ != 0))
        logger.info(f"[{self.model_name}] {n_selected}/{X.shape[1]} arrival features selected.")
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        X_scaled = self._scaler.transform(X.fillna(0).values)
        return self._lasso.predict(X_scaled)
