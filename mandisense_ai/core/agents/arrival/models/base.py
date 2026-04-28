"""
Base interface for all Arrival Volume Models.

Every model in the arrival model pool must inherit from BaseArrivalModel
and implement:
  - fit(X, y)              → trains the model on the given feature matrix / target
  - predict(X) -> ndarray  → returns point predictions (7-day price change %)
  - name  (property)       → human-readable identifier used in weight registry

Target variable convention:
  All arrival models predict `target_7d_pct` — the percentage price change
  over the next 7 days, computed in ArrivalVolumeAgent._feature_engineer().
  This is a percentage (e.g., 3.5 means +3.5 %), NOT an absolute price.
"""

from __future__ import annotations

import abc
import numpy as np
import pandas as pd


class BaseArrivalModel(abc.ABC):
    """Abstract base for every arrival-volume sub-model."""

    model_name: str = "BaseArrivalModel"

    @abc.abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaseArrivalModel":
        """Train on (X, y).  Must return self for chaining."""

    @abc.abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return point predictions as a 1-D numpy array."""

    @property
    def name(self) -> str:
        return self.model_name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.model_name}>"
