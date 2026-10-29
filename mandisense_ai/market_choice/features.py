"""Causal features. Every feature at index s uses data from days <= s only, so a
decision on day s+1 never sees day s+1. Own staleness and own report rate are
included; network-silence features are not, because the GFMC study found they
add nothing beyond a mandi's own report history."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.market_choice.panel import Panel, ffill_price, staleness

RETURN_LAGS = (1, 3, 7, 14, 28)
RATE_WINDOWS = (7, 14, 30)
STALE_CAP = 30


@dataclass(frozen=True)
class FeatureSet:
    X: np.ndarray                 # (T, M, F)
    names: Tuple[str, ...]
    lp: np.ndarray                # (T, M) forward-filled log price (NaN before the first report)
    stale: np.ndarray             # (T, M)


def _shift(a: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(a, np.nan, dtype=float)
    if n == 0:
        return a.astype(float)
    out[n:] = a[:-n]
    return out


def _roll_mean(a, w, minp=1):
    return pd.DataFrame(a).rolling(w, min_periods=minp).mean().to_numpy()


def _roll_std(a, w, minp=3):
    return pd.DataFrame(a).rolling(w, min_periods=minp).std().to_numpy()


def _expanding_mean(a):
    return pd.DataFrame(a).expanding(min_periods=1).mean().to_numpy()


def build_features(panel: Panel) -> FeatureSet:
    T, M = panel.T, panel.M
    mask = panel.mask
    lp = np.log(ffill_price(panel.price))
    stale = staleness(mask, cap=STALE_CAP)

    cols: List[np.ndarray] = []
    names: List[str] = []

    def add(name: str, arr: np.ndarray) -> None:
        cols.append(np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0))
        names.append(name)

    fresh = (stale <= 3) & ~np.isnan(lp)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cm = np.where(fresh.any(1), np.nanmean(np.where(fresh, lp, np.nan), axis=1), np.nan)
    cm = pd.Series(cm).ffill().to_numpy()
    cmM = np.repeat(cm[:, None], M, axis=1)

    add("own_dev", lp - cmM)
    add("cm_level", cmM - _expanding_mean(cmM))
    for h in RETURN_LAGS:
        add(f"ret_{h}", lp - _shift(lp, h))
    for h in (1, 7, 28):
        add(f"cm_ret_{h}", cmM - _shift(cmM, h))
    dret = lp - _shift(lp, 1)
    add("vol_14", _roll_std(dret, 14))
    add("cm_vol_14", np.repeat(_roll_std(np.diff(cm, prepend=np.nan)[:, None], 14), M, axis=1))
    add("stale", np.minimum(stale, STALE_CAP) / STALE_CAP)
    for w in RATE_WINDOWS:
        add(f"report_rate_{w}", _roll_mean(mask.astype(float), w))
    arr = np.log1p(pd.DataFrame(panel.arrivals).ffill().to_numpy())
    add("log_arrivals", arr - _expanding_mean(arr))
    add("arrivals_dev_28", arr - _roll_mean(arr, 28, 5))

    dow = (panel.dates.dayofweek.to_numpy() + 1) % 7          # weekday of the decision day (s + 1)
    for nm, v, per in (("dow", dow, 7), ("month", panel.dates.month.to_numpy(), 12)):
        add(f"{nm}_sin", np.repeat(np.sin(2 * np.pi * v / per)[:, None], M, 1))
        add(f"{nm}_cos", np.repeat(np.cos(2 * np.pi * v / per)[:, None], M, 1))
    add("tomorrow_is_sunday", np.repeat(((dow == 6).astype(float))[:, None], M, 1))

    return FeatureSet(X=np.stack(cols, axis=-1), names=tuple(names), lp=lp, stale=stale)
