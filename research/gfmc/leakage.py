"""Contribution 1: do decomposition-hybrid gains survive a leak-free evaluation?

Setup. A price series is decomposed into components (STL or VMD); one small
forecaster per component predicts the component h days ahead from that
component's own recent lags; the component forecasts are summed. This is the
common recipe of the STL-LSTM, CEEMDAN-TDNN, VMD-LSTM and ICEEMDAN-VMD-GRU
family reviewed in the project's literature survey.

Two protocols differ in exactly one thing - *how the components at and before
the forecast origin t are computed*:

  published   Decompose the WHOLE series once (train and test together), then
              split. The component at t then depends on data after t (both
              STL and VMD are two-sided smoothers). Forecasters are trained on
              components before the refit date and applied to lagged
              components of the global decomposition.

  causal      At every origin t decompose only y[: t + 1] and read the lags
              from that decomposition; training components come from
              decomposing y[: refit + 1]. This is what a deployed system can
              actually do.

Because decomposition at the end of a window behaves differently from decomposition
in its interior, a naive causal port (train on interior components, apply to endpoint
components) is handicapped by a train/test mismatch. We therefore report FOUR variants:

  published         literature recipe: one model per component, global decomposition
  published_joint   same global decomposition, one joint model on all components' lags
  causal_percomp    one model per component, trained on interior components of y[:r+1]
                    (the naive causal port - handicapped by the mismatch)
  causal_joint      one joint model; training AND test features are endpoint components
                    of decompositions of the data available at each origin (consistent)

published_joint vs causal_joint differ ONLY in whether components may see the future,
which isolates leakage from model structure and from the endpoint mismatch.

A forecaster on the raw (undecomposed) series and the random walk are included
as controls. Everything else (forecaster, lags, refit schedule, test origins,
scoring on days where the target price was really reported) is identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from gfmc import stats
from gfmc.decomp import DECOMPOSERS, future_sensitivity

LAGS = 14


# --------------------------------------------------------------- forecasters
def make_forecaster(name: str):
    if name == "ridge":
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    if name == "lgbm":
        import lightgbm as lgb

        return lgb.LGBMRegressor(n_estimators=150, learning_rate=0.05, num_leaves=8, min_child_samples=30,
                                 subsample=0.8, subsample_freq=1, reg_lambda=5.0, random_state=0, n_jobs=1,
                                 verbosity=-1)
    raise KeyError(name)


def lag_features(w: np.ndarray) -> np.ndarray:
    """(n, L) window of one component -> level + differences to the latest value."""
    last = w[:, -1:]
    return np.concatenate([last, last - w[:, :-1]], axis=1)


def windows(c: np.ndarray, L: int = LAGS) -> np.ndarray:
    """(T-L+1, L): row i is c[i : i+L], i.e. the window ending at index i+L-1."""
    return np.lib.stride_tricks.sliding_window_view(c, L)


def joint_features(win: np.ndarray) -> np.ndarray:
    """(n, L, C) windows -> (n, L*C) level + differences, concatenated over components."""
    return np.concatenate([lag_features(win[:, :, c]) for c in range(win.shape[2])], axis=1)


def fit_component_models(comps: np.ndarray, upto: int, h: int, forecaster: str):
    """Train one forecaster per component on comps[: upto + 1] (targets known by `upto`)."""
    models = []
    for c in range(comps.shape[1]):
        x = comps[: upto + 1, c]
        W = windows(x, LAGS)                                   # window i ends at index i+L-1
        ends = np.arange(LAGS - 1, len(x))
        keep = ends + h <= upto
        X = lag_features(W[keep])
        y = x[ends[keep] + h] - x[ends[keep]]
        m = make_forecaster(forecaster)
        m.fit(X, y)
        models.append(m)
    return models


def predict_sum(models, win: np.ndarray) -> np.ndarray:
    """win: (n, L, C) lagged component windows -> (n,) predicted change of the SUM of components."""
    total = np.zeros(win.shape[0])
    for c, m in enumerate(models):
        total += m.predict(lag_features(win[:, :, c]))
    return total


# --------------------------------------------------------------- one series
def _causal_window(decomposer: Callable, y: np.ndarray, t: int) -> np.ndarray:
    return decomposer(y[: t + 1])[-LAGS:, :]                   # (L, C) lags as a deployed system sees them


def run_series(y: np.ndarray, observed: np.ndarray, dates: pd.DatetimeIndex, decomposer_name: str,
               forecaster: str, hs: Sequence[int] = (1, 7), test_start: str = "2024-01-01", step: int = 3,
               refit_days: int = 90, n_jobs: int = 1, min_history: int = 365) -> pd.DataFrame:
    """Walk-forward benchmark for one log-price series. Returns per-origin forecasts of the h-day change."""
    decomposer = DECOMPOSERS[decomposer_name]
    T = len(y)
    t0 = int(dates.searchsorted(pd.Timestamp(test_start)))
    refits = list(range(t0, T, refit_days))
    hmax = max(hs)
    all_origins = list(range(min_history, T - hmax, step))        # one grid serves training and test origins
    comps_global = decomposer(y)                                  # published practice: one decomposition of everything
    cwin = np.stack(Parallel(n_jobs=n_jobs)(delayed(_causal_window)(decomposer, y, t) for t in all_origins))
    gwin = np.stack([comps_global[t - LAGS + 1: t + 1, :] for t in all_origins])
    pos = {t: i for i, t in enumerate(all_origins)}
    oarr = np.array(all_origins)
    raw_all = np.stack([y[t - LAGS + 1: t + 1] for t in all_origins])

    rows: List[Dict] = []
    for h in hs:
        for j, r in enumerate(refits):
            nxt = refits[j + 1] if j + 1 < len(refits) else T
            test_o = [t for t in all_origins if r <= t < nxt and observed[t + h]]
            if not test_o:
                continue
            tt = np.array(test_o)
            ti = np.array([pos[t] for t in test_o])
            truth = y[tt + h] - y[tt]
            # origins whose h-day target is known by the refit date
            tr = np.flatnonzero(oarr + h <= r)
            ytr = y[oarr[tr] + h] - y[oarr[tr]]

            # 1) published: per-component models on the global decomposition (literature recipe)
            pg = predict_sum(fit_component_models(comps_global, r, h, forecaster), gwin[ti])
            # 2) causal_percomp: per-component models on interior components of y[:r+1]
            pc = predict_sum(fit_component_models(decomposer(y[: r + 1]), r, h, forecaster), cwin[ti])
            # 3) published_joint / 4) causal_joint: one joint model, identical structure
            pj = make_forecaster(forecaster).fit(joint_features(gwin[tr]), ytr).predict(joint_features(gwin[ti]))
            cj = make_forecaster(forecaster).fit(joint_features(cwin[tr]), ytr).predict(joint_features(cwin[ti]))
            # control: the same forecaster on the raw series
            pr = make_forecaster(forecaster).fit(lag_features(raw_all[tr]), ytr).predict(lag_features(raw_all[ti]))
            for k, t in enumerate(tt):
                rows.append({"date": dates[t], "h": h, "truth": truth[k], "published": pg[k], "causal_percomp": pc[k],
                             "published_joint": pj[k], "causal_joint": cj[k], "raw": pr[k], "rw": 0.0})
    df = pd.DataFrame(rows)
    df["decomposer"], df["forecaster"] = decomposer_name, forecaster
    return df


PROTOCOLS = ("published", "published_joint", "causal_percomp", "causal_joint", "raw")


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """MAE skill versus the random walk per protocol, and the paired leakage gap
    (published_joint vs causal_joint: identical model structure, only look-ahead differs)."""
    out = []
    for (dec, fc, h), g in df.groupby(["decomposer", "forecaster", "h"]):
        mae_rw = np.abs(g["truth"]).mean()
        row = {"decomposer": dec, "forecaster": fc, "h": h, "n": len(g)}
        err = {k: np.abs(g[k] - g["truth"]).to_numpy() for k in PROTOCOLS}
        for k in PROTOCOLS:
            row[f"skill_{k}"] = 1 - err[k].mean() / mae_rw
        row["leak_gap_skill"] = row["skill_published_joint"] - row["skill_causal_joint"]
        d = stats.paired_report(err["causal_joint"], err["published_joint"], seed=int(h))   # >0: causal has HIGHER error
        row["leak_gap_ci_lo"], row["leak_gap_ci_hi"] = d["ci_lo"] / mae_rw, d["ci_hi"] / mae_rw   # skill-gap CI (causal error - published error)
        row["leak_p"] = d["p"]
        d2 = stats.paired_report(err["causal_joint"], err["raw"], seed=int(h) + 100)       # does causal decomposition beat raw?
        row["causal_minus_raw_mae"], row["causal_vs_raw_p"] = d2["mean_diff"], d2["p"]
        d3 = stats.paired_report(err["causal_joint"], np.abs(g["truth"]).to_numpy(), seed=int(h) + 200)
        row["causal_minus_rw_mae"], row["causal_vs_rw_p"] = d3["mean_diff"], d3["p"]
        out.append(row)
    return pd.DataFrame(out)


def sensitivity_table(y: np.ndarray, dates: pd.DatetimeIndex, decomposer_name: str, n_origins: int = 12,
                      seed: int = 0) -> Dict[str, float]:
    """Median / max change in components at day t when only the future is altered (0 when causal)."""
    rng = np.random.default_rng(seed)
    t0 = int(dates.searchsorted(pd.Timestamp("2024-01-01")))
    ts = rng.integers(t0, len(y) - 30, n_origins)
    f = DECOMPOSERS[decomposer_name]
    vals = np.array([future_sensitivity(f, y, int(t)) for t in ts])
    return {"decomposer": decomposer_name, "median_future_sensitivity": float(np.median(vals)),
            "max_future_sensitivity": float(vals.max())}
