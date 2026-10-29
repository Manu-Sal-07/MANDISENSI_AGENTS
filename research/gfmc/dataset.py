"""The decision dataset: one row per decision day, everything the farmer knows
(features through yesterday) and everything that later happened (realised
prices), aligned so that leakage is structurally impossible.

Arrays are indexed by *decision-day position* d = 0..D-1 which maps to panel
day t = days[d]. Information used for decision day t ends at s = t - 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from gfmc import econ
from gfmc.config import (CROP_SPOILAGE, DEFAULT_ECON, K_MAX, MAX_STALENESS_ELIGIBLE, N_HOLD, WARMUP_DAYS,
                         Economics)
from gfmc.data import registry
from gfmc.data.panel import Panel
from gfmc.features import FeatureSet, build_features


@dataclass(frozen=True)
class DecisionData:
    panel: Panel
    fs: FeatureSet
    days: np.ndarray            # (D,) panel day index t of each decision
    X: np.ndarray               # (D, M, F) features known at s = t-1
    ref_lp: np.ndarray          # (D, M) forward-filled log price at s
    elig: np.ndarray            # (D, M) bool, market offered to the farmer
    Y: np.ndarray               # (D, M, N_HOLD) log(P[t+k]/ref) ; NaN where unreported
    obs: np.ndarray             # (D, M, N_HOLD) bool, price at t+k observed
    P_obs: np.ndarray           # (D, M, N_HOLD) observed price (NaN where not)
    P_ref: np.ndarray           # (D, N_HOLD) mean reported price on day t+k (fallback base)
    gate_ref: np.ndarray        # (D,) mean reported price on day t (farm-gate base)
    valid: np.ndarray           # (D,) bool, day usable for training and scoring

    @property
    def D(self) -> int:
        return len(self.days)

    @property
    def M(self) -> int:
        return self.panel.M

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.panel.dates[self.days]

    def span(self, start: str, end: str) -> np.ndarray:
        """Decision-position indices with date in [start, end) and a valid day."""
        d = self.dates
        return np.flatnonzero((d >= pd.Timestamp(start)) & (d < pd.Timestamp(end)) & self.valid)

    def realised_price(self, econ_: Economics) -> np.ndarray:
        """(D, M, N_HOLD) price the farmer actually receives for each (market, hold).

        Observed if the mandi reported on t+k, else the discounted fallback.
        """
        fb = econ_.fallback_discount * self.P_ref[:, None, :]
        return np.where(self.obs, self.P_obs, fb)

    def realised_revenue(self, origin: Tuple[float, float], econ_: Economics) -> np.ndarray:
        """(D, A) realised net revenue of every action from one farmer origin."""
        dist = self.panel.dist_km(origin)
        price = np.nan_to_num(self.realised_price(econ_), nan=0.0)
        gate = np.nan_to_num(self.gate_ref, nan=0.0)
        return econ.revenue_from_prices(price, gate, dist, econ_)

    def action_mask(self) -> np.ndarray:
        """(D, A) bool: actions the farmer is offered (eligible markets + farm-gate)."""
        m = np.repeat(self.elig, N_HOLD, axis=1)
        return np.concatenate([m, np.ones((self.D, 1), dtype=bool)], axis=1)


def econ_for(crop: str, base: Economics = DEFAULT_ECON) -> Economics:
    """Crop-specific shelf-life; every other assumption is shared."""
    return base.but(spoilage_per_day=CROP_SPOILAGE.get(crop, base.spoilage_per_day))


def build_decision_data(panel: Panel, warmup: int = WARMUP_DAYS) -> DecisionData:
    fs = build_features(panel)
    T, M = panel.T, panel.M
    mask, price = panel.mask, panel.price

    t_all = np.arange(warmup + 1, T - K_MAX)            # t such that s = t-1 >= warmup and t+K_MAX <= T-1
    s = t_all - 1
    X = fs.X[s]
    ref_lp = fs.lp[s]

    elig = (fs.stale[s] <= MAX_STALENESS_ELIGIBLE) & ~np.isnan(ref_lp)

    Y = np.full((len(t_all), M, N_HOLD), np.nan)
    P_obs = np.full((len(t_all), M, N_HOLD), np.nan)
    P_ref = np.full((len(t_all), N_HOLD), np.nan)
    for k in range(N_HOLD):
        pk = price[t_all + k]                                   # (D, M)
        P_obs[:, :, k] = pk
        with np.errstate(invalid="ignore", divide="ignore"):
            Y[:, :, k] = np.log(pk) - ref_lp
        n = np.sum(~np.isnan(pk), axis=1)
        P_ref[:, k] = np.where(n > 0, np.nansum(pk, axis=1) / np.maximum(n, 1), np.nan)
    obs = ~np.isnan(P_obs)

    pt = price[t_all]
    n0 = np.sum(~np.isnan(pt), axis=1)
    gate_ref = np.where(n0 > 0, np.nansum(pt, axis=1) / np.maximum(n0, 1), np.nan)

    valid = ~np.isnan(P_ref).any(1) & ~np.isnan(gate_ref) & elig.any(1)
    return DecisionData(panel=panel, fs=fs, days=t_all, X=X, ref_lp=ref_lp, elig=elig, Y=Y, obs=obs,
                        P_obs=P_obs, P_ref=P_ref, gate_ref=gate_ref, valid=valid)


def origin_coords() -> Dict[str, Tuple[float, float]]:
    return dict(registry.ORIGINS)
