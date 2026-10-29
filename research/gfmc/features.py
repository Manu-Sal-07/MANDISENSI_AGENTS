"""Causal feature construction.

Every feature at index s uses data from days <= s only. A decision on day
t = s + 1 therefore never sees day t. Features come in two named groups so
the silence contribution can be ablated exactly:

* ``base``    - own price history and returns, own staleness / report rate,
                arrivals, cross-market common factor, volatility, calendar.
                Includes *own* silence (staleness, report rate), so the base
                model is already a strong treatment of missing data.
* ``silence`` - *network* silence: how many neighbouring mandis failed to
                report, distance-weighted, its recent history and the share of
                traded volume that is silent.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from gfmc.data.panel import Panel, ffill_price, staleness

RETURN_LAGS = (1, 3, 7, 14, 28)
RATE_WINDOWS = (7, 14, 30)
STALE_CAP = 30
NEIGHBOUR_SCALE_KM = 25.0


@dataclass(frozen=True)
class FeatureSet:
    X: np.ndarray                    # (T, M, F)
    names: Tuple[str, ...]
    groups: Dict[str, np.ndarray]    # group name -> column indices
    lp: np.ndarray                   # (T, M) forward-filled log price (NaN before first report)
    stale: np.ndarray                # (T, M) days since last report

    def cols(self, *groups: str) -> np.ndarray:
        return np.concatenate([self.groups[g] for g in groups])


def _shift(a: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(a, np.nan, dtype=float)
    if n == 0:
        return a.astype(float)
    out[n:] = a[:-n]
    return out


def _roll_mean(a: np.ndarray, w: int, minp: int = 1) -> np.ndarray:
    return pd.DataFrame(a).rolling(w, min_periods=minp).mean().to_numpy()


def _expanding_mean(a: np.ndarray) -> np.ndarray:
    """Mean of everything seen so far (causal); never uses later rows."""
    return pd.DataFrame(a).expanding(min_periods=1).mean().to_numpy()


def _roll_std(a: np.ndarray, w: int, minp: int = 3) -> np.ndarray:
    return pd.DataFrame(a).rolling(w, min_periods=minp).std().to_numpy()


def neighbour_weights(coords: np.ndarray) -> np.ndarray:
    """(M, M) row-normalised distance weights, zero diagonal."""
    from gfmc.data.registry import haversine_km

    M = len(coords)
    w = np.zeros((M, M))
    for i in range(M):
        for j in range(M):
            if i != j:
                w[i, j] = 1.0 / (1.0 + haversine_km(tuple(coords[i]), tuple(coords[j])) / NEIGHBOUR_SCALE_KM)
    return w / w.sum(1, keepdims=True)


def build_features(panel: Panel) -> FeatureSet:
    T, M = panel.T, panel.M
    mask = panel.mask
    fp = ffill_price(panel.price)
    lp = np.log(fp)
    stale = staleness(mask, cap=STALE_CAP)

    cols: List[np.ndarray] = []
    names: List[str] = []
    group_of: List[str] = []

    def add(name: str, arr: np.ndarray, group: str) -> None:
        cols.append(np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0))
        names.append(name)
        group_of.append(group)

    # --- cross-market common factor over markets that are fresh enough to trust
    fresh = (stale <= 3) & ~np.isnan(lp)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cm = np.where(fresh.any(1), np.nanmean(np.where(fresh, lp, np.nan), axis=1), np.nan)
    cm = pd.Series(cm).ffill().to_numpy()
    cmM = np.repeat(cm[:, None], M, axis=1)

    add("own_dev", lp - cmM, "base")
    add("cm_level", cmM - _expanding_mean(cmM), "base")
    for h in RETURN_LAGS:
        add(f"ret_{h}", lp - _shift(lp, h), "base")
    for h in (1, 7, 28):
        add(f"cm_ret_{h}", cmM - _shift(cmM, h), "base")
    dret = lp - _shift(lp, 1)
    add("vol_14", _roll_std(dret, 14), "base")
    add("cm_vol_14", np.repeat(_roll_std(np.diff(cm, prepend=np.nan)[:, None], 14), M, axis=1), "base")
    add("stale", np.minimum(stale, STALE_CAP) / STALE_CAP, "base")
    for w in RATE_WINDOWS:
        add(f"report_rate_{w}", _roll_mean(mask.astype(float), w), "base")

    arr = np.log1p(pd.DataFrame(panel.arrivals).ffill().to_numpy())
    add("log_arrivals", arr - _expanding_mean(arr), "base")
    add("arrivals_dev_28", arr - _roll_mean(arr, 28, 5), "base")

    # --- calendar of the *decision* day t = s + 1
    dow = (panel.dates.dayofweek.to_numpy() + 1) % 7
    for nm, v, per in (("dow", dow, 7), ("month", panel.dates.month.to_numpy(), 12)):
        add(f"{nm}_sin", np.repeat(np.sin(2 * np.pi * v / per)[:, None], M, 1), "base")
        add(f"{nm}_cos", np.repeat(np.cos(2 * np.pi * v / per)[:, None], M, 1), "base")
    add("tomorrow_is_sunday", np.repeat(((dow == 6).astype(float))[:, None], M, 1), "base")

    # --- network silence
    W = neighbour_weights(panel.coords)
    silent = (~mask).astype(float)
    nb_silence = silent @ W.T                                  # (T, M) weighted share of neighbours silent
    add("nb_silence_0", nb_silence, "silence")
    add("nb_silence_l1", _shift(nb_silence, 1), "silence")
    add("nb_silence_m7", _roll_mean(nb_silence, 7), "silence")
    add("nb_silence_delta", nb_silence - _roll_mean(nb_silence, 7), "silence")
    add("n_reporting", np.repeat(mask.sum(1, keepdims=True) / M, M, 1), "silence")
    add("own_silent_nb_active", silent * (1.0 - nb_silence), "silence")

    mass = (silent.mean(1) >= 0.5).astype(float)
    last = -1_000_000
    since = np.zeros(T)
    for t in range(T):
        last = t if mass[t] else last
        since[t] = min(t - last, 60) / 60.0
    add("since_mass_silence", np.repeat(since[:, None], M, 1), "silence")

    vol = pd.DataFrame(np.nan_to_num(panel.arrivals, nan=0.0)).rolling(90, min_periods=10).mean().to_numpy()
    share = vol / np.maximum(vol.sum(1, keepdims=True), 1e-9)
    add("silent_volume_share", np.repeat((silent * share).sum(1, keepdims=True), M, 1), "silence")
    add("nb_stale_wmean", (np.minimum(stale, STALE_CAP) / STALE_CAP) @ W.T, "silence")

    X = np.stack(cols, axis=-1)
    groups = {g: np.array([i for i, gg in enumerate(group_of) if gg == g]) for g in ("base", "silence")}
    return FeatureSet(X=X, names=tuple(names), groups=groups, lp=lp, stale=stale)
