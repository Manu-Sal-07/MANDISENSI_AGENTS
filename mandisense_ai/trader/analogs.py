"""
Historical analog finder: "when has this market looked like this before,
and what happened next?"

Replaces the Market Explorer's "Analogous Historical Periods" panel, which
read `historical_analogs` from cognition state — a field empty on every one
of the 75 tracked series.

Method, kept deliberately simple enough to explain in one sentence:

  1. Take the last `window` prints and express them as a cumulative-return
     path from the first print (so a ₹900 tomato and a ₹2,400 tomato with
     the same shape of move compare as equals).
  2. Slide the same-length window across the series' own history and
     measure the Euclidean distance between each past path and today's.
  3. Keep the `top_k` closest past windows that do not overlap each other
     (a window shifted by one print is not a second, independent analog)
     and that finished at least `horizon_days` before the present (so their
     "what happened next" is fully known, never partly the present).
  4. Report the calendar-true forward return after each analog: the first
     print on or after its end date + `horizon_days`.

The output is the *spread of past outcomes*, with its sample size, never a
single predicted number. It is labelled as empirical precedent, not a
forecast, because nearest-neighbour similarity on a short path is weak
evidence on its own and a trader should see how many cases it rests on.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from mandisense_ai.trader.data import forward_returns, resolve, series

MIN_ANALOGS = 8


def find_analogs(
    commodity: str,
    mandi_id: str,
    window: int = 30,
    horizon_days: int = 7,
    top_k: int = 15,
) -> Dict[str, Any]:
    c, m = resolve(commodity, mandi_id)
    frame = series(c, m)
    needed = window * 4 + horizon_days
    if len(frame) < needed:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "commodity": c,
            "mandi_id": m,
            "reason": f"{len(frame)} prints on record; at least {needed} are needed to search for {window}-print analogs.",
        }

    prices = frame["price"].to_numpy(dtype=float)
    dates = frame["date"].reset_index(drop=True)
    fwd = forward_returns(frame.reset_index(drop=True), horizon_days).to_numpy()

    def path(end: int) -> np.ndarray:
        segment = prices[end - window + 1 : end + 1]
        return segment / segment[0] - 1.0

    current_end = len(prices) - 1
    current = path(current_end)
    current_start_date = dates.iloc[current_end - window + 1]

    candidates = []
    for end in range(window - 1, current_end):
        # The analog's outcome window must close before today's pattern began.
        if dates.iloc[end] + pd.Timedelta(days=horizon_days) >= current_start_date:
            break
        if np.isnan(fwd[end]):
            continue
        candidates.append((float(np.sqrt(np.mean((path(end) - current) ** 2))), end))

    candidates.sort()
    chosen: List[tuple] = []
    min_gap = max(1, window // 2)
    for distance, end in candidates:
        if all(abs(end - e) >= min_gap for _, e in chosen):
            chosen.append((distance, end))
        if len(chosen) >= top_k:
            break

    if len(chosen) < MIN_ANALOGS:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "commodity": c,
            "mandi_id": m,
            "reason": f"Only {len(chosen)} non-overlapping analog(s) found; at least {MIN_ANALOGS} are needed before an outcome spread means anything.",
        }

    outcomes = np.array([fwd[end] for _, end in chosen])
    pct = (np.exp(outcomes) - 1) * 100

    analogs = [
        {
            "start": str(pd.Timestamp(dates.iloc[end - window + 1]).date()),
            "end": str(pd.Timestamp(dates.iloc[end]).date()),
            "distance": round(distance, 4),
            "similarity": round(1 / (1 + distance * 10), 3),
            "forward_return_pct": round(float((np.exp(fwd[end]) - 1) * 100), 2),
            "path": [round(float(v) * 100, 2) for v in path(end)],
        }
        for distance, end in chosen
    ]

    # Unconditional baseline: the same-horizon outcome over the whole
    # history. Without it, "rose in 11 of 15 analogs" is uninterpretable —
    # if prices rose 70% of the time regardless, the analogs add nothing.
    all_fwd = fwd[~np.isnan(fwd)]
    base_pct = (np.exp(all_fwd) - 1) * 100

    return {
        "status": "OK",
        "commodity": c,
        "mandi_id": m,
        "as_of": str(pd.Timestamp(dates.iloc[-1]).date()),
        "window_prints": window,
        "horizon_days": horizon_days,
        "current_path": [round(float(v) * 100, 2) for v in current],
        "analogs": analogs,
        "outcome": {
            "n": int(len(pct)),
            "share_up": round(float((pct > 0).mean()), 3),
            "median_pct": round(float(np.median(pct)), 2),
            "p10_pct": round(float(np.percentile(pct, 10)), 2),
            "p90_pct": round(float(np.percentile(pct, 90)), 2),
        },
        "baseline": {
            "n": int(len(base_pct)),
            "share_up": round(float((base_pct > 0).mean()), 3),
            "median_pct": round(float(np.median(base_pct)), 2),
        },
        "disclaimer": "Empirical precedent from this series' own history, not a forecast.",
    }
