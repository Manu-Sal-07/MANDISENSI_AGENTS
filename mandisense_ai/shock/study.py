"""
Event study of supply shocks: what happens to a crop's own price after an
arrival glut or squeeze, and how much of that is real.

This complements `farmer/transmission.py`, which asks whether a shock to one
crop moves ANOTHER crop (cross-commodity) and whether price gaps between
districts close (spatial). Neither answers the question a farmer asks first:
"arrivals of MY crop just jumped; what does that do to MY price?". This module
does, with the same publication discipline:

  * shocks are onsets of a log-arrival z-score >= 1.5 (glut) or <= -1.5
    (squeeze) against a trailing, lagged 60-day norm (`arrival_surprise`), at
    least 7 days apart, so a shock never uses its own future;
  * the effect is the crop's log price change over h days after onset, minus the
    mean change of the other crops in the same district over the same window
    (so a market-wide move is not mistaken for a crop-specific response);
  * the interval is a moving-block bootstrap over weeks;
  * a circular-shift placebo (onset dates moved by at least 90 days) gives a
    p-value that respects how shocks cluster in time;
  * p-values are Holm-adjusted over every crop, direction and horizon tested;
  * the smallest effect the sample could have detected (2.8 standard errors, 80%
    power at 5%) is reported with every result, so "no effect" is never confused
    with "too few episodes to tell".

Tiers: ROBUST (adjusted p < 0.05, placebo p <= 0.05, interval excludes zero, same
sign in >= 75% of districts with enough episodes), SUGGESTIVE (interval excludes
zero but a check above fails), NONE otherwise.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.farmer.significance import holm
from mandisense_ai.farmer.transmission import (BLOCK_WEEKS, MIN_EPISODES, MIN_STABILITY_SHARE, PLACEBO_MIN_SHIFT_DAYS,
                                                NearestLookup, _block_bootstrap_ci, arrival_surprise, onsets)

HORIZONS = (3, 7, 14)
DIRECTIONS = ("glut", "squeeze")
PLACEBO_DRAWS = 400
SEED = 20261029


def _lookups(obs: pd.DataFrame, district: str) -> Dict[str, NearestLookup]:
    d = obs[obs["mandi_id"] == district]
    return {c: NearestLookup(g.sort_values("date").set_index("date")["modal_price"]) for c, g in d.groupby("commodity")
            if len(g) >= 60}


def _change(look: NearestLookup, t0: pd.Timestamp, h: int) -> Optional[float]:
    a, b = look.at(t0), look.at(t0 + pd.Timedelta(days=h))
    return None if a is None or b is None else b - a


_CTX: Dict[Any, Any] = {}


def _context(obs: pd.DataFrame, crop: str, direction: str):
    """Per-district price lookups, z-series span and onsets; built once, reused by every placebo draw."""
    key = (id(obs), crop, direction)
    if key not in _CTX:
        out = {}
        for district in sorted(obs["mandi_id"].unique()):
            d_obs = obs[(obs["mandi_id"] == district) & (obs["commodity"] == crop)]
            if len(d_obs) < 120:
                continue
            looks = _lookups(obs, district)
            if crop not in looks:
                continue
            z = arrival_surprise(d_obs)
            out[district] = (looks, z.index.min(), z.index.max(), onsets(z, direction))
        _CTX.clear()
        _CTX[key] = out
    return _CTX[key]


_GRID: Dict[Any, Any] = {}


def _grid(obs: pd.DataFrame, crop: str, direction: str, district: str, h: int):
    """Own-crop and peer-mean h-day price change for every calendar day of the district's span (NaN where unmatched)."""
    key = (id(obs), crop, district, h)
    if key not in _GRID:
        looks, zmin, zmax, _ = _context(obs, crop, direction)[district]
        days = pd.date_range(zmin, zmax, freq="D")
        own = np.full(len(days), np.nan)
        peer = np.full(len(days), np.nan)
        for i, t0 in enumerate(days):
            o = _change(looks[crop], t0, h)
            if o is None:
                continue
            ps = [v for c, lk in looks.items() if c != crop and (v := _change(lk, t0, h)) is not None]
            own[i], peer[i] = o, (float(np.mean(ps)) if ps else 0.0)
        _GRID[key] = (own, peer)
    return _GRID[key]


def _episodes(obs: pd.DataFrame, crop: str, direction: str, h: int, shift_days: Optional[Dict[str, int]] = None
              ) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for district, (looks, zmin, zmax, starts) in _context(obs, crop, direction).items():
        span = max((zmax - zmin).days, 1)
        off = 0 if (shift_days is None or not starts) else shift_days[district] % span   # placebo: same shocks, moved in time
        own, peer = _grid(obs, crop, direction, district, h)
        for t in starts:
            k = (int((t - zmin).days) + off) % span if off else int((t - zmin).days)
            if 0 <= k < len(own) and np.isfinite(own[k]):
                rows.append({"district": district, "date": zmin + pd.Timedelta(days=k), "own": own[k], "peer": peer[k]})
    return pd.DataFrame(rows)


def _summary(ep: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if ep.empty:
        return None
    excess = (ep["own"] - ep["peer"]).to_numpy()
    n = len(ep)
    se = float(excess.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    return {"n": n, "excess": float(excess.mean()), "raw_mean": float(ep["own"].mean()), "raw_median": float(ep["own"].median()),
            "p10": float(ep["own"].quantile(0.10)), "p90": float(ep["own"].quantile(0.90)),
            "share_down": float((ep["own"] < 0).mean()), "se": se, "mde": 2.8 * se if np.isfinite(se) else None}


def study_crop(obs: pd.DataFrame, crop: str, direction: str, h: int) -> Dict[str, Any]:
    ep = _episodes(obs, crop, direction, h)
    base = _summary(ep)
    if base is None or base["n"] < MIN_EPISODES:
        return {"crop": crop, "direction": direction, "horizon": h, "status": "INSUFFICIENT_EPISODES", "n": 0 if base is None else base["n"]}
    excess = (ep["own"] - ep["peer"]).to_numpy()
    lo, hi = _block_bootstrap_ci(excess, ep["date"].astype(str).to_numpy(), BLOCK_WEEKS, 1000, SEED)

    rng = np.random.default_rng(SEED + h)
    districts = sorted(obs["mandi_id"].unique())
    draws = []
    for _ in range(PLACEBO_DRAWS):
        shifts = {d: int(rng.integers(PLACEBO_MIN_SHIFT_DAYS, 1500)) for d in districts}
        pe = _episodes(obs, crop, direction, h, shift_days=shifts)
        if len(pe) >= MIN_EPISODES:
            draws.append(float((pe["own"] - pe["peer"]).mean()))
    placebo_p = float((np.sum(np.abs(draws) >= abs(base["excess"])) + 1) / (len(draws) + 1)) if draws else None

    per_district = {}
    for d, g in ep.groupby("district"):
        if len(g) >= MIN_EPISODES:
            per_district[d] = float((g["own"] - g["peer"]).mean())
    same_sign = [np.sign(v) == np.sign(base["excess"]) for v in per_district.values()]
    stable = bool(len(same_sign) >= 3 and np.mean(same_sign) >= MIN_STABILITY_SHARE)

    t = base["excess"] / base["se"] if base["se"] else 0.0
    from scipy import stats as sps
    raw_p = float(2 * (1 - sps.t.cdf(abs(t), df=max(base["n"] - 1, 1))))
    return {"crop": crop, "direction": direction, "horizon": h, "status": "OK", "n": base["n"], "effect": base["excess"],
            "ci": [lo, hi], "raw_mean": base["raw_mean"], "raw_median": base["raw_median"], "p10": base["p10"], "p90": base["p90"],
            "share_down": base["share_down"], "mde": base["mde"], "raw_p": raw_p, "placebo_p": placebo_p,
            "districts": {"n": len(per_district), "effects": per_district, "stable": stable}}


def run_study(obs: pd.DataFrame, crops: Optional[List[str]] = None) -> Dict[str, Any]:
    crops = crops or sorted(obs["commodity"].unique())
    results = [study_crop(obs, c, d, h) for c in crops for d in DIRECTIONS for h in HORIZONS]
    ok = [r for r in results if r["status"] == "OK"]
    adj = holm([r["raw_p"] for r in ok]) if ok else []
    for r, a in zip(ok, adj):
        r["holm_p"] = float(a)
        excludes = (r["ci"][0] > 0) or (r["ci"][1] < 0)
        placebo_ok = r["placebo_p"] is not None and r["placebo_p"] <= 0.05
        if r["holm_p"] < 0.05 and placebo_ok and excludes and r["districts"]["stable"]:
            r["tier"] = "ROBUST"
        elif excludes:
            r["tier"] = "SUGGESTIVE"
        else:
            r["tier"] = "NONE"
    for r in results:
        r.setdefault("tier", "NONE")
    return {"results": results, "n_tested": len(ok), "n_robust": sum(r["tier"] == "ROBUST" for r in ok),
            "n_suggestive": sum(r["tier"] == "SUGGESTIVE" for r in ok),
            "rules": {"z_onset": 1.5, "min_gap_days": 7, "horizons_days": list(HORIZONS), "min_episodes": MIN_EPISODES,
                      "placebo_draws": PLACEBO_DRAWS, "placebo_min_shift_days": PLACEBO_MIN_SHIFT_DAYS, "holm_over": len(ok)}}
