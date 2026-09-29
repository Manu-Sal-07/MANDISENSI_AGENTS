"""
Volatility profile and data-derived regimes.

The Market Explorer's regime timeline was permanently "Unknown": the price
history it reads carries no regime field, and regimes existed only on
cognition-engine states for 10 of 75 series. Regimes here are computed from
each series' own returns, so every series with history gets one.

Realised volatility is the rolling standard deviation of print-to-print log
returns. Because these series are near-daily, "20-print volatility" is close
to "20-trading-day volatility", and it is reported as a daily percentage —
not annualised, because annualising assumes a trading calendar these
markets do not keep.

Regimes are percentile bands of a series' *own* volatility history, not
fixed thresholds: 3% daily volatility is calm for tomato and turbulent for
garlic, and a fixed cut-off would call one commodity permanently turbulent.

  CALM        below the 33rd percentile of its own history
  NORMAL      33rd to 80th
  TURBULENT   above the 80th
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from mandisense_ai.trader.data import resolve, series

WINDOWS = (10, 20, 60)
REGIME_WINDOW = 20
MIN_PRINTS = 80


def _regime(pct: float) -> str:
    if pct < 33:
        return "CALM"
    if pct <= 80:
        return "NORMAL"
    return "TURBULENT"


def volatility_profile(commodity: str, mandi_id: str, timeline_points: int = 180) -> Dict[str, Any]:
    c, m = resolve(commodity, mandi_id)
    frame = series(c, m)
    if len(frame) < MIN_PRINTS:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "commodity": c,
            "mandi_id": m,
            "reason": f"{len(frame)} prints on record; at least {MIN_PRINTS} are needed to rank volatility against its own history.",
        }

    frame = frame.copy()
    frame["ret"] = np.log(frame["price"]).diff()
    windows: Dict[str, Any] = {}
    for w in WINDOWS:
        vol = frame["ret"].rolling(w, min_periods=max(5, w // 2)).std() * 100
        frame[f"vol_{w}"] = vol
        history = vol.dropna()
        current = float(history.iloc[-1]) if len(history) else None
        pct = float((history < current).mean() * 100) if current is not None else None
        windows[str(w)] = {
            "current_daily_pct": round(current, 3) if current is not None else None,
            "percentile": round(pct, 1) if pct is not None else None,
            "median_daily_pct": round(float(history.median()), 3) if len(history) else None,
            "p90_daily_pct": round(float(history.quantile(0.9)), 3) if len(history) else None,
        }

    vol = frame[f"vol_{REGIME_WINDOW}"]
    # Percentile of each day's volatility against the history up to and
    # including that day -- an expanding rank, so a past regime label is what
    # a trader could have known then, not a verdict rewritten with hindsight.
    ranks = vol.expanding(min_periods=REGIME_WINDOW * 2).apply(
        lambda s: (s[:-1] < s[-1]).mean() * 100 if len(s) > 1 else np.nan, raw=True
    )
    frame["regime"] = [(_regime(r) if pd.notna(r) else None) for r in ranks]

    segments: List[Dict[str, Any]] = []
    for row in frame.dropna(subset=["regime"]).itertuples():
        day = str(pd.Timestamp(row.date).date())
        if segments and segments[-1]["regime"] == row.regime:
            segments[-1]["end"] = day
            segments[-1]["prints"] += 1
        else:
            segments.append({"regime": row.regime, "start": day, "end": day, "prints": 1})

    current_regime = segments[-1]["regime"] if segments else None
    recent = frame.dropna(subset=[f"vol_{REGIME_WINDOW}"]).tail(timeline_points)

    return {
        "status": "OK",
        "commodity": c,
        "mandi_id": m,
        "as_of": str(pd.Timestamp(frame["date"].iloc[-1]).date()),
        "prints": int(len(frame)),
        "windows": windows,
        "current_regime": current_regime,
        "regime_share": {
            r: round(sum(s["prints"] for s in segments if s["regime"] == r) / max(1, sum(s["prints"] for s in segments)), 3)
            for r in ("CALM", "NORMAL", "TURBULENT")
        },
        "regime_segments": segments[-40:],
        "series": [
            {
                "date": str(pd.Timestamp(r.date).date()),
                "price": round(float(r.price), 2),
                "vol_20_daily_pct": round(float(getattr(r, f"vol_{REGIME_WINDOW}")), 3),
                "regime": r.regime,
            }
            for r in recent.itertuples()
        ],
        "method": "rolling std of print-to-print log returns; regimes are expanding percentiles of the series' own 20-print volatility",
    }
