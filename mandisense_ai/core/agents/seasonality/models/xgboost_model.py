"""
XGBoost Seasonality Model.

Why this model?
  XGBoost is the strongest single-model performer on tabular time-series data
  with exogenous features.  Its sequential boosting strategy corrects residual
  errors iteratively, making it excellent at capturing non-linear price jumps
  caused by supply shocks and festival demand spikes.

  early_stopping_rounds is NOT used here because we do a walk-forward CV
  externally; fitting is done on the full training fold at fixed n_estimators.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from core.agents.seasonality.models.base import BaseSeasonalityModel
from utils.logger import get_logger

logger = get_logger(__name__)


class XGBoostSeasonalityModel(BaseSeasonalityModel):
    """
    XGBoost wrapped as a BaseSeasonalityModel.

    Hyper-parameters chosen to prevent overfitting on ~3 000–5 000 row datasets:
      - max_depth=6 (shallower trees reduce variance)
      - subsample=0.8, colsample_bytree=0.8 (stochastic boosting)
      - learning_rate=0.05 (slow learner needs more trees but generalises better)
    """

    model_name = "XGBoost"

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: int = 6,
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
            n_jobs=1,           # keep deterministic; parallelism is at agent level
            random_state=random_state,
            verbosity=0,
        )
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "XGBoostSeasonalityModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows.")
        self._model.fit(X.fillna(0), y)
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._model.predict(X.fillna(0).astype(float))
