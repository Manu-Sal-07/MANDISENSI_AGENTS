"""
Gradient Boosting Regressor Arrival Model.

Why this model?
  sklearn's GradientBoostingRegressor uses the classic Friedman (2001) algorithm
  with exact greedy split finding — different from XGBoost's approximate histogram
  method and LightGBM's leaf-wise growth.  This algorithmic diversity means:

    - It can find splits XGBoost and LightGBM miss on small-to-medium datasets
    - It is natively robust to outliers when using `loss='huber'`
    - It produces calibrated predictions (no numerical instabilities with small n)

  We use `loss='huber'` specifically because arrival-driven price changes include
  genuine extreme events (floods, strikes, border closures) that would dominate
  squared-error objectives.  Huber loss treats errors beyond `alpha` quantile as
  linear rather than quadratic, dramatically improving out-of-sample MAPE when
  supply shocks occur.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from mandisense_ai.core.agents.arrival.models.base import BaseArrivalModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class GradientBoostingArrivalModel(BaseArrivalModel):
    """sklearn GradientBoostingRegressor with Huber loss for supply-shock robustness."""

    model_name = "GradientBoosting"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        loss: str = "huber",
        random_state: int = 42,
    ):
        self._model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            loss=loss,
            random_state=random_state,
        )
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "GradientBoostingArrivalModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows (loss={self._model.loss}).")
        self._model.fit(X.fillna(0), y)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._model.predict(X.fillna(0))
