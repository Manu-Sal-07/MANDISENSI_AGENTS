"""
Mandi-to-mandi spread scanner (spatial arbitrage).

For one commodity, every ordered pair of tracked mandis (buy at A, sell at
B) is scored on the one number a trader actually earns: **the margin still
there when the truck arrives**, net of transport.

A raw sticker-price gap answers the wrong question. Measured on this
archive, most day-to-day gaps between two mandis are print noise that
reverts at the very next print; chasing one means arriving to find it gone.
But some pairs also carry a *structural* spread — one mandi persistently
dearer than another — which does not need to "survive" anything because it
is there every day. The scanner separates the two with an AR(1) fit on the
pair's own log-price spread over the last two years of shared prints:

    Δs_t = a + b·s_{t-1}        (−1 < b < 0: mean-reverting)
    μ    = −a / b               the pair's structural spread
    E[s_{t+k}] = μ + (s_t − μ)·(1 + b)^k

With k = trip time in prints (≈ days for these near-daily series), the
expected spread on arrival is what gets priced and ranked. When b ≥ 0 there
is no measurable reversion and today's gap is carried forward unchanged
(random-walk expectation) — stated in the result, not hidden.

Two plain-language checks travel with each result so the model can be
questioned: `half_life_days` of the transient part, and `closure` — of past
days this pair's spread sat as far from normal as today, how often it had
closed half-way within the trip.

Transport rate and truck speed are stated assumptions, reported with every
response.
"""

from __future__ import annotations

from itertools import permutations
from math import ceil, log
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.farmer.reference import (
    MANDI_COORDINATES,
    MANDI_DISPLAY_NAMES,
    distance_between_mandis_km,
)
from mandisense_ai.trader.data import resolve, series, snapshot
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

AVERAGE_TRUCK_SPEED_KMPH = 35.0
"""Door-to-door average for a loaded tempo on district roads. Stated, not measured."""

HANDLING_DAYS = 0.5
"""Loading, unloading and the auction wait, on top of driving time."""

MIN_COMMON_PRINTS = 60
"""Fewer shared dates than this and the AR(1) fit is noise."""

HISTORY_DAYS = 730


VEHICLES = (
    # (capacity quintals, hire rupees per km, label). Hire is charged for the
    # round trip -- a hired truck returns empty -- so cost = rate x km x 2.
    # These are stated regional estimates, not a quote; every response
    # reports which vehicle and rate were assumed so they can be checked.
    (10, 22.0, "small tempo"),
    (40, 32.0, "light truck"),
    (100, 45.0, "10-tonne truck"),
)


def transport_plan(distance_km: float, quantity_quintals: float) -> Dict[str, Any]:
    """Cheapest vehicle mix for a load, and what it costs per quintal.

    Per-quintal transport falls steeply with load: the same 100 km costs a
    two-quintal farmer roughly ten times more per quintal than a trader
    filling a truck. A flat per-quintal-km rate (fine for the farmer tool,
    which is sized to smallholder loads) would hide the one lever a trader
    actually controls, so the trader scanner prices the real load.
    """
    qty = max(float(quantity_quintals), 0.1)
    best = None
    for capacity, rate, label in VEHICLES:
        trucks = ceil(qty / capacity)
        cost = trucks * rate * distance_km * 2
        if best is None or cost < best["trip_cost"]:
            best = {"vehicle": label, "vehicles_needed": trucks, "rate_per_km": rate,
                    "capacity_quintals": capacity, "trip_cost": round(cost, 2)}
    best["per_quintal"] = round(best["trip_cost"] / qty, 2)
    return best


def _trip_days(distance_km: float) -> float:
    return round(distance_km / AVERAGE_TRUCK_SPEED_KMPH / 24.0 + HANDLING_DAYS, 2)


def _spread_history(a: pd.DataFrame, b: pd.DataFrame) -> Optional[pd.Series]:
    """Log spread log(B/A) on the dates both mandis printed, last two years."""
    if a.empty or b.empty:
        return None
    cutoff = max(a["date"].max(), b["date"].max()) - pd.Timedelta(days=HISTORY_DAYS)
    joined = a[a["date"] >= cutoff].merge(b[b["date"] >= cutoff], on="date", suffixes=("_a", "_b"))
    if len(joined) < MIN_COMMON_PRINTS:
        return None
    return pd.Series(
        np.log(joined["price_b"].to_numpy() / joined["price_a"].to_numpy()),
        index=joined["date"].to_numpy(),
    )


def fit_ar1(spread: pd.Series) -> Optional[Tuple[float, float]]:
    """(b, mu) for a mean-reverting spread, or None when it does not revert."""
    s = spread.to_numpy()
    lagged, delta = s[:-1], np.diff(s)
    n = len(lagged)
    if n < MIN_COMMON_PRINTS or np.std(lagged) == 0:
        return None
    b, a = np.polyfit(lagged, delta, 1)

    # Statistical significance, not just sign. A pure random walk fits a
    # small negative b from sampling noise alone on every finite sample --
    # verified directly: 300 simulated random-walk steps fit b = -0.0012,
    # which without this check would have been reported as a confident
    # half-life. Standard OLS slope standard error; reject unless b is at
    # least ~2 SE below zero (roughly a one-sided 95% test).
    residuals = delta - (a + b * lagged)
    if n <= 2:
        return None
    sigma2 = float(np.sum(residuals**2)) / (n - 2)
    sxx = float(np.sum((lagged - lagged.mean()) ** 2))
    if sxx <= 0:
        return None
    se_b = (sigma2 / sxx) ** 0.5
    if se_b == 0 or b >= -2 * se_b:
        return None
    mu = float(-a / b)
    # b <= -1 is a spread that fully reverts within one print (overshooting
    # slightly from estimation noise). Rejecting it would treat the *most*
    # transient spreads as permanent and rank them highest — exactly
    # backwards. Clamp to full one-step reversion instead.
    return max(float(b), -1.0), mu


def expected_spread_after(current: float, fit: Optional[Tuple[float, float]], steps: int) -> float:
    """E[s_{t+steps}] under the AR(1) fit; a random walk when there is no fit."""
    if fit is None:
        return current
    b, mu = fit
    return mu + (current - mu) * (1.0 + b) ** steps


def _closure_rate(spread: pd.Series, current: float, within_prints: int) -> Dict[str, Any]:
    s = spread.to_numpy()
    centre = float(np.median(s))
    now_dev = abs(current - centre)
    if now_dev == 0:
        return {"episodes": 0, "closed": 0, "rate": None}
    episodes = closed = 0
    for i in range(len(s) - within_prints):
        dev = abs(s[i] - centre)
        if dev < now_dev * 0.8:
            continue
        episodes += 1
        future = np.abs(s[i + 1 : i + 1 + within_prints] - centre)
        if len(future) and future.min() <= dev / 2:
            closed += 1
    return {
        "episodes": episodes,
        "closed": closed,
        "rate": round(closed / episodes, 3) if episodes >= 5 else None,
    }


def scan_spreads(
    commodity: str,
    quantity_quintals: float = 20.0,
    max_results: int = 12,
    transport_rate_override: Optional[float] = None,
) -> Dict[str, Any]:
    """Rank buy-at-A / sell-at-B pairs by expected net margin on arrival.

    `transport_rate_override` (rupees per quintal per km) replaces the
    vehicle model for a trader who knows their own contracted rate.
    """
    c, _ = resolve(commodity)
    universe = list(MANDI_COORDINATES.keys())
    snap = snapshot(c, universe=universe)
    prices: Dict[str, Dict[str, Any]] = snap["prices"]  # type: ignore[assignment]

    if len(prices) < 2:
        return {
            "status": "UNAVAILABLE",
            "commodity": c,
            "reason": "Fewer than two tracked mandis have a comparable recent print for this commodity.",
            "stale_mandis": snap["stale"],
        }

    qty = float(quantity_quintals)
    rows: List[Dict[str, Any]] = []
    # One series per mandi, built once — not twice per pair (210 pairs).
    history = {m: series(c, m) for m in prices}

    for buy, sell in permutations(prices.keys(), 2):
        distance = distance_between_mandis_km(buy, sell)
        if distance is None:
            continue
        buy_price = prices[buy]["price"]
        sell_price = prices[sell]["price"]
        if transport_rate_override is not None:
            plan = {"vehicle": "trader-supplied rate", "vehicles_needed": None,
                    "per_quintal": round(distance * transport_rate_override, 2)}
        else:
            plan = transport_plan(distance, qty)
        transport = plan["per_quintal"]
        trip_days = _trip_days(distance)
        steps = max(1, ceil(trip_days))
        current = float(np.log(sell_price / buy_price))

        spread = _spread_history(history[buy], history[sell])
        fit = fit_ar1(spread) if spread is not None else None
        expected = expected_spread_after(current, fit, steps)

        expected_sell = buy_price * float(np.exp(expected))
        expected_net = round(expected_sell - buy_price - transport, 2)
        today_net = round(sell_price - buy_price - transport, 2)
        structural_net = (
            round(buy_price * float(np.exp(fit[1])) - buy_price - transport, 2) if fit else None
        )

        # Only pairs worth considering on arrival: either the expected margin
        # at arrival is positive, or today's gap is (shown so a trader sees
        # the ones that vanish before the truck gets there, ranked below).
        if expected_net <= 0 and today_net <= 0:
            continue

        rows.append({
            "buy_mandi": buy,
            "buy_mandi_name": MANDI_DISPLAY_NAMES.get(buy, buy),
            "sell_mandi": sell,
            "sell_mandi_name": MANDI_DISPLAY_NAMES.get(sell, sell),
            "buy_price": round(buy_price, 2),
            "sell_price": round(sell_price, 2),
            "buy_price_date": prices[buy]["date"],
            "sell_price_date": prices[sell]["date"],
            "distance_km": distance,
            "trip_days": trip_days,
            "transport_cost_per_quintal": transport,
            "vehicle": plan["vehicle"],
            "vehicles_needed": plan["vehicles_needed"],
            "today_net_per_quintal": today_net,
            "expected_net_on_arrival_per_quintal": expected_net,
            "expected_net_on_arrival_pct": round(expected_net / buy_price * 100, 2) if buy_price else None,
            "expected_net_total": round(expected_net * qty, 2),
            "structural_net_per_quintal": structural_net,
            "half_life_days": (
                (round(log(2) / -log(1 + fit[0]), 2) if fit[0] > -1 else 0.0) if fit else None
            ),
            "model": "ar1_mean_reversion" if fit else ("random_walk" if spread is not None else "no_history"),
            "history_prints": int(len(spread)) if spread is not None else 0,
            "closure": _closure_rate(spread, current, steps) if spread is not None else None,
            "survives_trip": expected_net > 0,
        })

    rows.sort(key=lambda r: (not r["survives_trip"], -r["expected_net_on_arrival_per_quintal"]))

    return {
        "status": "OK",
        "commodity": c,
        "as_of": snap["as_of"],
        "mandis_compared": len(prices),
        "stale_mandis": snap["stale"],
        "quantity_quintals": qty,
        "assumptions": {
            "transport_model": (
                f"trader-supplied {transport_rate_override} rupees/quintal/km"
                if transport_rate_override is not None
                else "cheapest vehicle mix for the load; round-trip hire"
            ),
            "vehicles": [
                {"capacity_quintals": cap, "rate_per_km": rate, "label": label}
                for cap, rate, label in VEHICLES
            ],
            "average_truck_speed_kmph": AVERAGE_TRUCK_SPEED_KMPH,
            "handling_days": HANDLING_DAYS,
            "history_days": HISTORY_DAYS,
        },
        "opportunities": rows[:max_results],
        "survivors": sum(1 for r in rows if r["survives_trip"]),
        "vanishing": sum(1 for r in rows if not r["survives_trip"]),
    }
