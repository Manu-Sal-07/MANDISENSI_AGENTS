"""
Base interface for all Seasonality Models.

Every model in the seasonality model pool must inherit from BaseSeasonalityModel
and implement:
  - fit(X, y)              → trains the model on the given feature matrix / target
  - predict(X) -> ndarray  → returns point predictions
  - name  (property)       → human-readable identifier used in weight registry

Why an ABC here?
  TieredModelPipeline iterates over a dict of {name: model}.  Having a shared
  interface means we can add / remove models without touching the pipeline code.
"""

from __future__ import annotations

import abc
import numpy as np
import pandas as pd
from typing import Any


class BaseSeasonalityModel(abc.ABC):
    """Abstract base for every seasonality sub-model."""

    # ------------------------------------------------------------------ #
    #  Subclasses MUST provide a class-level name attribute               #
    # ------------------------------------------------------------------ #
    model_name: str = "BaseSeasonalityModel"

    @abc.abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaseSeasonalityModel":
        """Train on (X, y).  Must return self for chaining."""

    @abc.abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return point predictions as a 1-D numpy array."""

    # ------------------------------------------------------------------ #
    #  Optional helpers with sensible defaults                            #
    # ------------------------------------------------------------------ #
    @property
    def name(self) -> str:
        return self.model_name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.model_name}>"
