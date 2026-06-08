"""
XGBoost Arrival Model.

Why this model?
  XGBoost is the current single-model baseline in ArrivalVolumeAgent.  It is
  kept as-is in the pool so the transition from single-model to ensemble
  produces identical or better results: the existing tuned XGB simply receives
  a fractional weight instead of weight=1.0.

  The arrival feature set is richer in supply-shock signals (arrival_deviation_pct,
  rolling_elasticity, consecutive_decline_days) than the seasonality feature set,
  which makes gradient boosting particularly effective here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from mandisense_ai.core.agents.arrival.models.base import BaseArrivalModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class XGBoostArrivalModel(BaseArrivalModel):
    """XGBoost for 7-day price-change % prediction."""

    model_name = "XGBoost"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ):
        self._model = XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            objective="reg:squarederror",
            n_jobs=1,
            random_state=random_state,
            verbosity=0,
        )
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "XGBoostArrivalModel":
        logger.info(f"[{self.model_name}] Fitting arrival model on {len(X)} rows.")
        self._model.fit(X.fillna(0), y)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._model.predict(X.fillna(0).astype(float))
