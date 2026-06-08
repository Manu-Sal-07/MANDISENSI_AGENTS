"""
Polynomial Regression Arrival Model (Optional).

Why this model?
  The price-elasticity relationship is not always log-linear.  At extreme
  supply shortage (arrivals → 0) or glut (arrivals >> 30d mean), the price
  response accelerates non-linearly.  A degree-2 polynomial expansion of the
  arrival features captures these quadratic effects without the full complexity
  of a gradient boosting model.

  This model is lightweight (linear solver on expanded features) and converges
  instantly — making it an ideal complement to the computationally heavier
  XGBoost / GradientBoosting models in the pool.

  Degree is capped at 2 to prevent the combinatorial feature explosion that
  degree ≥ 3 causes on the arrival feature set (~12 features → ~90 poly
  features at degree 2, vs ~360 at degree 3).

  Ridge regularisation (alpha=1.0) is applied on the expanded polynomial
  features to prevent overfitting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline

from mandisense_ai.core.agents.arrival.models.base import BaseArrivalModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class PolynomialArrivalModel(BaseArrivalModel):
    """Degree-2 Polynomial Regression (Ridge-regularised) for arrival features."""

    model_name = "PolynomialRegression"

    def __init__(self, degree: int = 2, ridge_alpha: float = 1.0):
        self._degree = min(degree, 2)   # hard cap at 2 for feature explosion prevention
        self._pipeline = Pipeline([
            ("scaler",  StandardScaler()),
            ("poly",    PolynomialFeatures(degree=self._degree, include_bias=False)),
            ("ridge",   Ridge(alpha=ridge_alpha)),
        ])
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "PolynomialArrivalModel":
        logger.info(
            f"[{self.model_name}] Fitting degree={self._degree} polynomial "
            f"on {len(X)} rows, {X.shape[1]} input features."
        )
        self._pipeline.fit(X.fillna(0).values, y)
        n_poly_features = self._pipeline.named_steps["poly"].n_output_features_
        logger.info(f"[{self.model_name}] Expanded to {n_poly_features} polynomial features.")
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._pipeline.predict(X.fillna(0).values)
