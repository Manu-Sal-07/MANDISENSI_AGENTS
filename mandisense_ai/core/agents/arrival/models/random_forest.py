"""
RandomForest Arrival Model.

Why this model?
  Random Forests are excellent at capturing threshold-like supply-demand
  dynamics.  For example: "if arrivals drop > 40% AND it's a festival window
  → price spikes > 10%".  Decision trees naturally model these conjunctions,
  and bagging (bootstrap aggregation) averages out noise from individual trees.

  The bootstrap also makes RF relatively robust to the occasional extreme
  supply-shock row that would dominate a gradient booster's loss.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from core.agents.arrival.models.base import BaseArrivalModel
from utils.logger import get_logger

logger = get_logger(__name__)


class RandomForestArrivalModel(BaseArrivalModel):
    """Random Forest for 7-day price-change % prediction."""

    model_name = "RandomForest"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 8,
        min_samples_leaf: int = 5,
        random_state: int = 42,
    ):
        self._model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            n_jobs=-1,
            random_state=random_state,
        )
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestArrivalModel":
        logger.info(f"[{self.model_name}] Fitting arrival model on {len(X)} rows.")
        self._model.fit(X.fillna(0), y)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._model.predict(X.fillna(0))
