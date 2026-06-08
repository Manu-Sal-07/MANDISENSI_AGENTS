"""
Lasso Regression Seasonality Model.

Why this model?
  Lasso (L1 regularisation) performs implicit feature selection by driving
  irrelevant feature coefficients exactly to zero.  On high-dimensional feature
  sets (many lag columns, calendar dummies, rolling stats) this produces a
  sparse, interpretable model that generalises well.

  Particularly useful after a regime change: Lasso will automatically drop
  features that were predictive in the old regime but are noisy in the new one,
  stabilising predictions faster than tree-based models.

  LassoCV could auto-select alpha, but we fix alpha=0.01 to keep training fast
  in the weekly recalibration loop.  Alpha is tunable via __init__.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso
from sklearn.preprocessing import StandardScaler

from mandisense_ai.core.agents.seasonality.models.base import BaseSeasonalityModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class LassoSeasonalityModel(BaseSeasonalityModel):
    """Lasso Regression with internal StandardScaler."""

    model_name = "Lasso"

    def __init__(self, alpha: float = 0.01, max_iter: int = 3000):
        self._lasso = Lasso(alpha=alpha, max_iter=max_iter)
        self._scaler = StandardScaler()
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LassoSeasonalityModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows, alpha={self._lasso.alpha}.")
        X_scaled = self._scaler.fit_transform(X.fillna(0).values)
        self._lasso.fit(X_scaled, y)
        n_nonzero = int(np.sum(self._lasso.coef_ != 0))
        logger.info(f"[{self.model_name}] {n_nonzero}/{X.shape[1]} features selected (non-zero coef).")
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        X_scaled = self._scaler.transform(X.fillna(0).values)
        return self._lasso.predict(X_scaled)

    # ------------------------------------------------------------------ #
    @property
    def selected_features(self) -> list[int]:
        """Indices of features with non-zero coefficients after fitting."""
        if not self._fitted:
            return []
        return list(np.where(self._lasso.coef_ != 0)[0])
