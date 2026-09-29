"""
Where to Sell -- net price after transport, across nearby mandis.

A higher price at a farther mandi is not automatically the better choice;
the only number that matters is what is left after getting the crop there.
This compares every tracked mandi within range on that basis, using each
mandi's own most recent observed price (never a forecast -- comparing today's
actual prices across mandis needs no model) and a straight-line-distance
transport cost estimate.

The per-quintal transport rate is a coarse, stated assumption
(`RUPEES_PER_QUINTAL_PER_KM`), not a routing or fuel-price API. It is shown
alongside every result rather than hidden inside the ranking, so a farmer who
knows their own transport is cheaper or dearer can judge how much the
ranking should move.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from mandisense_ai.farmer.reference import (
    MANDI_COORDINATES,
    MANDI_DISPLAY_NAMES,
    distance_between_mandis_km,
    haversine_km,
)
from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.forecasting.store import ObservationStore
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# A stated, coarse assumption -- real per-tonne-km rates for a shared tempo
# or tractor trip in this region are commonly in this range, but any real
# trip should be checked against what a farmer's own driver actually quotes.
RUPEES_PER_QUINTAL_PER_KM = 3.5
MAX_USEFUL_DISTANCE_KM = 120.0


def compare_mandis(
    commodity: str,
    origin_mandi_id: Optional[str] = None,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    quantity_quintals: float = 1.0,
) -> Dict[str, Any]:
    """
    Rank tracked mandis by net price for `commodity`, from an origin given
    either as a known mandi (farmer already at a mandi) or raw coordinates
    (farmer's own location).
    """
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    qty = float(quantity_quintals or 1.0)

    if origin_mandi_id:
        resolved_origin = canonical_market(origin_mandi_id) or str(origin_mandi_id).strip().lower()
        origin_point = MANDI_COORDINATES.get(resolved_origin)
    else:
        resolved_origin = None
        origin_point = (origin_lat, origin_lon) if origin_lat is not None and origin_lon is not None else None

    if origin_point is None:
        return {"status": "UNAVAILABLE", "reason": "No usable origin location was given."}

    try:
        observations = ObservationStore().read()
    except Exception as exc:
        logger.error("Where-to-sell: observation read failed: %s", exc)
        observations = pd.DataFrame()

    if observations.empty:
        return {"status": "UNAVAILABLE", "reason": "No observation data available."}

    subset = observations[observations["commodity"] == resolved_commodity].copy()
    subset["date"] = pd.to_datetime(subset["date"])

    results: List[Dict[str, Any]] = []
    for mandi_id, coords in MANDI_COORDINATES.items():
        distance_km = round(haversine_km(origin_point, coords), 1)
        if resolved_origin and mandi_id == resolved_origin:
            distance_km = 0.0
        if distance_km > MAX_USEFUL_DISTANCE_KM:
            continue

        series = subset[subset["mandi_id"] == mandi_id].sort_values("date")
        if series.empty:
            continue
        latest = series.iloc[-1]
        price = float(latest["modal_price"])
        transport_cost_per_quintal = round(distance_km * RUPEES_PER_QUINTAL_PER_KM, 2)
        net_price = round(price - transport_cost_per_quintal, 2)

        results.append({
            "mandi_id": mandi_id,
            "mandi_name": MANDI_DISPLAY_NAMES.get(mandi_id, mandi_id),
            "distance_km": distance_km,
            "as_of_date": str(pd.Timestamp(latest["date"]).date()),
            "gross_price_per_quintal": round(price, 2),
            "transport_cost_per_quintal": transport_cost_per_quintal,
            "net_price_per_quintal": net_price,
            "net_total": round(net_price * qty, 2),
        })

    if not results:
        return {"status": "UNAVAILABLE", "reason": "No nearby mandi has recent data for this crop."}

    results.sort(key=lambda r: r["net_price_per_quintal"], reverse=True)
    best = results[0]

    return {
        "status": "OK",
        "commodity": resolved_commodity,
        "quantity_quintals": qty,
        "transport_rate_per_quintal_per_km": RUPEES_PER_QUINTAL_PER_KM,
        "mandis": results,
        "best_mandi_id": best["mandi_id"],
        "best_over_worst": round(best["net_price_per_quintal"] - results[-1]["net_price_per_quintal"], 2)
        if len(results) > 1 else 0.0,
    }
