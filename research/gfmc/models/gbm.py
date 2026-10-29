"""Gradient-boosted baselines (LightGBM, XGBoost): one regressor per hold k,
trained on stacked (day, market) rows with the market as a categorical feature.

These are the strong "predict, then optimise" baselines. They are trained on
*observed* targets only, as is standard practice.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from gfmc.config import N_HOLD, SEED
from gfmc.models.base import PriceModel


def filled_targets(dd, idx: np.ndarray, econ) -> np.ndarray:
    """(n, M, K) log(realised price / ref); silent cells carry the fallback price."""
    ref = np.exp(np.nan_to_num(dd.ref_lp[idx], nan=0.0))[:, :, None]
    real = dd.realised_price(econ)[idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.nan_to_num(np.log(np.where(real > 0, real, np.nan) / ref), nan=0.0)


def _rows(dd, idx: np.ndarray, cols: np.ndarray, k: Optional[int], filled: Optional[np.ndarray] = None):
    """Stack (day, market) rows. With k given, keep rows with an observed target
    (or every eligible row when `filled` labels are supplied)."""
    n, M = len(idx), dd.M
    X = dd.X[idx][:, :, cols]                                  # (n, M, F)
    mk = np.broadcast_to(np.arange(M), (n, M))
    keep = dd.elig[idx].copy()
    if k is not None and filled is None:
        keep &= dd.obs[idx][:, :, k]
    X2 = np.concatenate([X, mk[:, :, None].astype(float)], axis=2)[keep]
    y = None
    if k is not None:
        y = (filled[:, :, k] if filled is not None else dd.Y[idx][:, :, k])[keep]
    return X2, y, keep


class LGBMModel(PriceModel):
    def __init__(self, labels: str = "observed", name: Optional[str] = None, **hp):
        assert labels in ("observed", "filled")
        self.labels = labels
        self.name = name or ("lightgbm" if labels == "observed" else "lightgbm_filled")
        self.hp = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=40,
                       subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0,
                       huber_delta=0.15)
        self.hp.update(hp)
        self.models: List = []
        self.cols = None

    def fit(self, dd, idx, econ, cols):
        import lightgbm as lgb

        self.cols = cols
        self.models = []
        hp = dict(self.hp)
        delta = hp.pop("huber_delta")
        filled = filled_targets(dd, idx, econ) if self.labels == "filled" else None
        for k in range(N_HOLD):
            X, y, _ = _rows(dd, idx, cols, k, filled)
            m = lgb.LGBMRegressor(objective="huber", alpha=delta, random_state=SEED + k, n_jobs=2,
                                  verbosity=-1, **hp)
            m.fit(X, y, categorical_feature=[X.shape[1] - 1])
            self.models.append(m)
        return self

    def predict(self, dd, idx):
        out = np.zeros((len(idx), dd.M, N_HOLD))
        X, _, keep = _rows(dd, idx, self.cols, None)
        for k, m in enumerate(self.models):
            plane = np.zeros(keep.shape)
            plane[keep] = m.predict(X)
            out[:, :, k] = plane
        return out


class XGBModel(PriceModel):
    name = "xgboost"

    def __init__(self, **hp):
        self.hp = dict(n_estimators=300, learning_rate=0.03, max_depth=4, min_child_weight=10,
                       subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0)
        self.hp.update(hp)
        self.models: List = []
        self.cols = None

    def fit(self, dd, idx, econ, cols):
        import xgboost as xgb

        self.cols = cols
        self.models = []
        for k in range(N_HOLD):
            X, y, _ = _rows(dd, idx, cols, k)
            m = xgb.XGBRegressor(objective="reg:pseudohubererror", random_state=SEED + k, n_jobs=2,
                                 tree_method="hist", verbosity=0, **self.hp)
            m.fit(X, y)
            self.models.append(m)
        return self

    def predict(self, dd, idx):
        out = np.zeros((len(idx), dd.M, N_HOLD))
        X, _, keep = _rows(dd, idx, self.cols, None)
        for k, m in enumerate(self.models):
            plane = np.zeros(keep.shape)
            plane[keep] = m.predict(X)
            out[:, :, k] = plane
        return out
