"""Common interface for every price-vector predictor in the study.

A model maps the features known on the morning of decision day t to a
predicted log-return of every market at every hold k, relative to that
market's last observed (forward-filled) price. Decisions are then derived from
the predictions by `gfmc.policy`, so all models are scored on the same
decision problem with the same economics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from gfmc.config import Economics
from gfmc.dataset import DecisionData


class PriceModel(ABC):
    name: str = "model"

    @abstractmethod
    def fit(self, dd: DecisionData, idx: np.ndarray, econ: Economics, cols: np.ndarray) -> "PriceModel":
        """Fit on decision positions `idx` using feature columns `cols`."""

    @abstractmethod
    def predict(self, dd: DecisionData, idx: np.ndarray) -> np.ndarray:
        """(len(idx), M, N_HOLD) predicted log(P[t+k] / ref)."""


class RandomWalk(PriceModel):
    """Tomorrow's price equals the last observed price (the forecasting benchmark)."""

    name = "random_walk"

    def fit(self, dd, idx, econ, cols):
        return self

    def predict(self, dd, idx):
        return np.zeros((len(idx), dd.M, dd.Y.shape[2]))


def price_from_logret(dd: DecisionData, idx: np.ndarray, yhat: np.ndarray) -> np.ndarray:
    """(n, M, N_HOLD) predicted price level in Rs/quintal."""
    ref = np.exp(np.nan_to_num(dd.ref_lp[idx], nan=0.0))
    return ref[:, :, None] * np.exp(yhat)


def standardise(X_train: np.ndarray, mask: np.ndarray, eps: float = 1e-6):
    """Mean / std of features over eligible training rows; returns a callable."""
    rows = X_train[mask]
    mu = rows.mean(0)
    sd = rows.std(0)
    sd = np.where(sd < eps, 1.0, sd)

    def apply(x: np.ndarray) -> np.ndarray:
        return np.clip((x - mu) / sd, -6.0, 6.0)

    return apply
