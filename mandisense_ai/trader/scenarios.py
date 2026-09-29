"""
Evidence-based scenarios: "when this has happened here before, what did the
price do next?"

Replaces the Intelligence Lab's counterfactuals, which were hand-written
formulas — e.g. "Arrival Increase" was `basePct + diff(0.25) − forecast×0.05`
— and the backend `/simulate` endpoint that only ever answered
`"simulation_initiated"`. Neither consulted any data about how a price
responds to anything.

A scenario here is a *condition on this series' own history*. The condition
is evaluated on every past date; the dates that satisfied it are the
episodes; and the forward price moves after those episodes are the answer:

    ARRIVAL_SURGE     arrivals ≥ 30% above their trailing-30-print mean
    ARRIVAL_DROUGHT   arrivals ≥ 30% below it
    PRICE_RALLY       price up ≥ 10% over the last 5 prints
    PRICE_SLUMP       price down ≥ 10% over the last 5 prints
    VOLATILITY_SPIKE  20-print volatility above its own 90th percentile

Three safeguards keep the answer honest:

  * **Episodes are de-clustered.** A surge that lasts six days is one
    episode, not six independent observations; only the first day of a run
    (and at least `horizon_days` after the previous kept episode) counts.
  * **Every result carries the unconditional baseline**, so "prices fell
    after 9 of 12 surges" is read against how often they fall anyway.
  * **Below `MIN_EPISODES` no verdict is given.** Two past cases is an
    anecdote; the response says how many there were and stops.

The output is precedent, not a forecast, and is labelled as such.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd

from mandisense_ai.trader.data import forward_returns, resolve, series

MIN_EPISODES = 8

SCENARIOS: Dict[str, Dict[str, str]] = {
    "arrival_surge": {"label": "Arrivals surge", "needs": "arrivals",
                      "definition": "Arrivals at least 30% above their trailing 30-print average"},
    "arrival_drought": {"label": "Arrivals dry up", "needs": "arrivals",
                        "definition": "Arrivals at least 30% below their trailing 30-print average"},
    "price_rally": {"label": "Price rallies", "needs": "price",
                    "definition": "Price up at least 10% over the last 5 prints"},
    "price_slump": {"label": "Price slumps", "needs": "price",
                    "definition": "Price down at least 10% over the last 5 prints"},
    "volatility_spike": {"label": "Volatility spikes", "needs": "price",
                         "definition": "20-print volatility above its own 90th percentile"},
}


def _condition(frame: pd.DataFrame, scenario: str) -> pd.Series:
    if scenario in ("arrival_surge", "arrival_drought"):
        base = frame["arrivals"].rolling(30, min_periods=15).mean().shift(1)
        dev = (frame["arrivals"] - base) / base
        return dev >= 0.30 if scenario == "arrival_surge" else dev <= -0.30
    if scenario in ("price_rally", "price_slump"):
        move = frame["price"] / frame["price"].shift(5) - 1
        return move >= 0.10 if scenario == "price_rally" else move <= -0.10
    if scenario == "volatility_spike":
        vol = np.log(frame["price"]).diff().rolling(20, min_periods=10).std()
        return vol > vol.expanding(min_periods=60).quantile(0.90).shift(1)
    raise ValueError(scenario)


def _declustered(flags: pd.Series, dates: pd.Series, horizon_days: int) -> List[int]:
    kept: List[int] = []
    last_date = None
    prev = False
    for i, on in enumerate(flags.to_numpy()):
        if on and not prev:
            d = dates.iloc[i]
            if last_date is None or (d - last_date).days >= horizon_days:
                kept.append(i)
                last_date = d
        prev = bool(on)
    return kept


def run_scenario(
    commodity: str,
    mandi_id: str,
    scenario: str,
    horizon_days: int = 5,
) -> Dict[str, Any]:
    c, m = resolve(commodity, mandi_id)
    if scenario not in SCENARIOS:
        return {"status": "ERROR", "reason": f"scenario must be one of {sorted(SCENARIOS)}"}

    frame = series(c, m)
    if len(frame) < 200:
        return {"status": "INSUFFICIENT_HISTORY", "commodity": c, "mandi_id": m,
                "reason": f"{len(frame)} prints on record; at least 200 are needed."}

    if SCENARIOS[scenario]["needs"] == "arrivals" and frame["arrivals"].notna().mean() < 0.5:
        return {"status": "UNAVAILABLE", "commodity": c, "mandi_id": m,
                "reason": "This series has too few recorded arrival volumes to test an arrivals scenario."}

    frame = frame.reset_index(drop=True)
    flags = _condition(frame, scenario).fillna(False)
    fwd = forward_returns(frame, horizon_days)
    episodes = [i for i in _declustered(flags, frame["date"], horizon_days) if not np.isnan(fwd.iloc[i])]

    baseline = (np.exp(fwd.dropna()) - 1) * 100
    meta = SCENARIOS[scenario]
    common = {
        "commodity": c, "mandi_id": m, "scenario": scenario, "label": meta["label"],
        "definition": meta["definition"], "horizon_days": horizon_days,
        "disclaimer": "Precedent from this series' own history, not a forecast.",
        "baseline": {
            "n": int(len(baseline)),
            "share_down": round(float((baseline < 0).mean()), 3),
            "median_pct": round(float(baseline.median()), 2),
        },
    }

    if len(episodes) < MIN_EPISODES:
        return {**common, "status": "INSUFFICIENT_EVIDENCE", "episodes": int(len(episodes)),
                "reason": f"Only {len(episodes)} independent past episode(s); at least {MIN_EPISODES} are needed before an outcome means anything."}

    outcome = (np.exp(fwd.iloc[episodes].to_numpy()) - 1) * 100
    already_in = bool(flags.iloc[-1])
    recent = [
        {
            "date": str(pd.Timestamp(frame["date"].iloc[i]).date()),
            "price": round(float(frame["price"].iloc[i]), 2),
            "forward_return_pct": round(float(o), 2),
        }
        for i, o in list(zip(episodes, outcome))[-8:]
    ]

    return {
        **common,
        "status": "OK",
        "as_of": str(pd.Timestamp(frame["date"].iloc[-1]).date()),
        "condition_active_now": already_in,
        "episodes": int(len(episodes)),
        "outcome": {
            "share_down": round(float((outcome < 0).mean()), 3),
            "median_pct": round(float(np.median(outcome)), 2),
            "p10_pct": round(float(np.percentile(outcome, 10)), 2),
            "p90_pct": round(float(np.percentile(outcome, 90)), 2),
            "mean_pct": round(float(outcome.mean()), 2),
        },
        "edge_vs_baseline_pct": round(float(np.median(outcome) - baseline.median()), 2),
        "recent_episodes": recent,
    }


def run_all(commodity: str, mandi_id: str, horizon_days: int = 5) -> Dict[str, Any]:
    c, m = resolve(commodity, mandi_id)
    return {
        "status": "OK", "commodity": c, "mandi_id": m, "horizon_days": horizon_days,
        "scenarios": [run_scenario(c, m, key, horizon_days) for key in SCENARIOS],
    }
