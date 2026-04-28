"""
RandomForestRegressor Seasonality Model.

Why this model?
  Random Forests build many decorrelated decision trees.  They are naturally
  robust to festival-driven outliers (via bootstrap sampling) and capture
  complex non-linear interactions between lag features, calendar signals, and
  arrival volumes without needing feature scaling.

  They also provide implicit feature importance rankings that can surface
  which seasonal signals matter most for a commodity × mandi pair.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from core.agents.seasonality.models.base import BaseSeasonalityModel
from utils.logger import get_logger

logger = get_logger(__name__)


class RandomForestSeasonalityModel(BaseSeasonalityModel):
    """
    Thin wrapper around sklearn RandomForestRegressor following BaseSeasonalityModel.

    Hyper-parameters are conservative defaults tuned for ~3 000–5 000 row
    Agmarknet datasets (7–10 years of daily mandi data).
    """

    model_name = "RandomForest"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 10,
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

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestSeasonalityModel":
        logger.info(f"[{self.model_name}] Fitting on {len(X)} rows, "
                    f"{X.shape[1]} features.")
        self._model.fit(X.fillna(0), y)
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        return self._model.predict(X.fillna(0))

    # ------------------------------------------------------------------ #
    @property
    def feature_importances_(self) -> np.ndarray:
        """Expose sklearn feature importances for explainability."""
        return self._model.feature_importances_
