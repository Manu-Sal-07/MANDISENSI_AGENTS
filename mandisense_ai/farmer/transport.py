"""
Where to Sell -- net price after transport, across nearby mandis.

A higher price at a farther mandi is not automatically the better choice; the
only number that matters is what is left after getting the crop there. This
compares every mandi in reach on that basis, using each mandi's own most
recent *recorded* price (never a forecast: comparing today's actual prices
across mandis needs no model) and a straight-line transport cost estimate.

The per-quintal transport rate is a coarse, stated assumption
(`RUPEES_PER_QUINTAL_PER_KM`), not a routing or fuel-price API. It is returned
with every result rather than hidden inside the ranking, so a farmer who knows
their own transport is cheaper or dearer can judge how much the ranking should
move.

A mandi whose latest print is older than `MAX_PRICE_AGE_DAYS` is left out:
comparing a price from last month with one from today would rank the stale one
on nothing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry, world
from mandisense_ai.forecasting.naming import canonical_commodity
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

RUPEES_PER_QUINTAL_PER_KM = 3.5
MAX_USEFUL_DISTANCE_KM = 120.0
MAX_PRICE_AGE_DAYS = 10
RECENT_PRINTS = 3
OUTLIER_RATIO = 1.5
"""A single day's print at a small mandi can jump on a handful of crates. The
comparison uses the arrivals-weighted price of each mandi's last few prints,
so one thin day cannot rank a market first."""


def _origin_point(origin_mandi_id: Optional[str], lat: Optional[float], lon: Optional[float]):
    if origin_mandi_id:
        place = registry.resolve_place(origin_mandi_id)
        if place in registry.MANDIS:
            m = registry.MANDIS[place]
            return place, (m.lat, m.lon)
        if place in registry.DISTRICTS:
            d = registry.DISTRICTS[place]
            return place, (d.lat, d.lon)
        return None, None
    if lat is not None and lon is not None:
        return None, (lat, lon)
    return None, None


def compare_mandis(
    commodity: str,
    origin_mandi_id: Optional[str] = None,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    quantity_quintals: float = 1.0,
) -> Dict[str, Any]:
    """Rank mandis by net price for `commodity` from an origin given as a
    mandi, a district, or raw coordinates."""
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    qty = float(quantity_quintals or 1.0)

    origin_id, origin_point = _origin_point(origin_mandi_id, origin_lat, origin_lon)
    if origin_point is None:
        return {"status": "UNAVAILABLE", "reason": "No usable origin location was given."}

    prices = world.mandi_prices()
    if prices.empty:
        return {"status": "UNAVAILABLE", "reason": "No mandi price data available."}

    crop = prices[prices["commodity"] == resolved_commodity]
    if crop.empty:
        return {"status": "UNAVAILABLE", "reason": "No mandi reports this crop."}

    newest = crop["date"].max()
    ordered = crop.sort_values("date")
    latest = ordered.groupby("mandi_id").tail(1)
    latest = latest[(newest - latest["date"]).dt.days <= MAX_PRICE_AGE_DAYS]
    recent = ordered.groupby("mandi_id").tail(RECENT_PRINTS)
    load_tonnes = qty / 10.0

    results: List[Dict[str, Any]] = []
    for _, row in latest.iterrows():
        mandi = registry.MANDIS.get(row["mandi_id"])
        if mandi is None:
            continue
        window = recent[recent["mandi_id"] == row["mandi_id"]]
        weights = window["arrivals"].to_numpy(dtype=float)
        smoothed = float(np.average(window["modal_price"], weights=weights)) if weights.sum() > 0 else float(window["modal_price"].mean())
        typical_tonnes = float(window["arrivals"].mean())
        distance_km = 0.0 if origin_id == mandi.id else round(
            registry.haversine_km(origin_point, (mandi.lat, mandi.lon)), 1
        )
        if distance_km > MAX_USEFUL_DISTANCE_KM:
            continue
        price = smoothed
        transport = round(distance_km * RUPEES_PER_QUINTAL_PER_KM, 2)
        net = round(price - transport, 2)
        results.append({
            "mandi_id": mandi.id,
            "mandi_name": mandi.name,
            "mandi_name_kn": mandi.name_kn,
            "mandi_name_hi": mandi.name_hi,
            "district": mandi.district,
            "distance_km": distance_km,
            "as_of_date": str(pd.Timestamp(row["date"]).date()),
            "gross_price_per_quintal": round(price, 2),
            "min_price_per_quintal": round(float(row["min_price"]), 2),
            "max_price_per_quintal": round(float(row["max_price"]), 2),
            "latest_price_per_quintal": round(float(row["modal_price"]), 2),
            "arrivals_tonnes": round(float(row["arrivals"]), 1),
            "typical_arrivals_tonnes": round(typical_tonnes, 1),
            "thin_for_load": bool(typical_tonnes < load_tonnes),
            "transport_cost_per_quintal": transport,
            "net_price_per_quintal": net,
            "net_total": round(net * qty, 2),
        })

    if not results:
        return {"status": "UNAVAILABLE", "reason": "No mandi in reach has a recent price for this crop."}

    # A price far above or below what comparable mandis print is usually a
    # different grade or a handful of crates, not a real gap a load could use.
    # It stays in the list, flagged, and is never recommended.
    if len(results) >= 3:
        # Volume-weighted median: the markets that actually move the crop
        # define what a normal price is, not the count of small ones.
        ranked = sorted(results, key=lambda r: r["gross_price_per_quintal"])
        weights = np.array([max(r["typical_arrivals_tonnes"], 0.1) for r in ranked])
        median = float(ranked[int(np.searchsorted(np.cumsum(weights), weights.sum() / 2))]["gross_price_per_quintal"])
        for r in results:
            r["outlier"] = bool(r["gross_price_per_quintal"] > OUTLIER_RATIO * median
                                or r["gross_price_per_quintal"] < median / OUTLIER_RATIO)
    else:
        for r in results:
            r["outlier"] = False

    results.sort(key=lambda r: r["net_price_per_quintal"], reverse=True)
    best = next((r for r in results if not r["outlier"]), results[0])

    return {
        "status": "OK",
        "commodity": resolved_commodity,
        "quantity_quintals": qty,
        "transport_rate_per_quintal_per_km": RUPEES_PER_QUINTAL_PER_KM,
        "mandis": results,
        "best_mandi_id": best["mandi_id"],
        "best_over_worst": round(best["net_price_per_quintal"] - min(r["net_price_per_quintal"] for r in results), 2)
        if len(results) > 1 else 0.0,
    }
