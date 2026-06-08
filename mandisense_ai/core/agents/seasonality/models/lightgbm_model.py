"""
LightGBM Seasonality Model.

Why this model?
  LightGBM uses leaf-wise (best-first) tree growth instead of XGBoost's
  depth-wise strategy.  On sparse Agmarknet data (many missing arrivals days)
  this tends to produce lower validation MAPE because it allocates more
  capacity to high-error regions automatically.

  It is also significantly faster than XGBoost on large (>3 000 row) datasets,
  which matters when re-training all models during weekly weight recalibration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb

from mandisense_ai.core.agents.seasonality.models.base import BaseSeasonalityModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class LightGBMSeasonalityModel(BaseSeasonalityModel):
    """
    LightGBM wrapped as BaseSeasonalityModel.

    verbose=-1 silences LightGBM's internal progress prints;
    n_jobs=1 keeps per-model training deterministic.
    """

    model_name = "LightGBM"

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ):
        self._model = lgb.LGBMRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            n_jobs=1,
            random_state=random_state,
            verbose=-1,
        )
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LightGBMSeasonalityModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows.")
        self._model.fit(X.fillna(0), y)
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._model.predict(X.fillna(0).astype(float))
