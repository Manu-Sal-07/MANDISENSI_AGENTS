"""
My Harvest in Rupees -- the sell window.

Turns the published forecast curve into what it means for *this* farmer's
actual harvest: not "+3.2%" but "sell Thursday: ₹62,000-₹71,000". A percentage
is the right unit for a trader comparing series; it is the wrong one for a
decision about one truckload, where the number that matters is what lands in
hand.

The best day is chosen by expected rupee value, and every day's own risk
(how wide its calibrated band is, in rupees) travels with it -- a farmer
comparing "best expected" against "safest" is a real choice this exposes
rather than hides behind a single recommended day.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def plan_harvest(
    commodity: str,
    mandi_id: str,
    quantity_quintals: float,
) -> Dict[str, Any]:
    """Every published horizon for this series, converted to rupees for
    `quantity_quintals`, plus which day maximises expected rupee return."""
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()
    qty = float(quantity_quintals)

    try:
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
        if not service.is_available:
            return {
                "commodity": resolved_commodity, "mandi_id": resolved_mandi,
                "status": "UNAVAILABLE", "reason": "No published forecast store yet.",
                "days": [],
            }
        curve = service.get_curve(resolved_commodity, resolved_mandi)
    except Exception as exc:
        logger.error("Harvest plan: forecast lookup failed: %s", exc)
        curve = []

    if not curve:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "This series is not tracked.",
            "days": [],
        }

    first = curve[0]
    base_price = first.get("last_observed_price")
    as_of_date = first.get("as_of_date")

    days: List[Dict[str, Any]] = []
    if base_price:
        days.append({
            "horizon_days": 0,
            "target_date": as_of_date,
            "label": "today",
            "status": "OK",
            "expected_total": round(base_price * qty, 2),
            "range_low": round(base_price * qty, 2),
            "range_high": round(base_price * qty, 2),
            "price_per_quintal": round(float(base_price), 2),
        })

    for row in curve:
        if row.get("status") != "OK" or not row.get("horizon_days"):
            days.append({
                "horizon_days": row.get("horizon_days"),
                "target_date": row.get("target_date"),
                "label": f"{row.get('horizon_days')}-day" if row.get("horizon_days") else "unknown",
                "status": row.get("status", "UNAVAILABLE"),
                "reason": row.get("reason"),
                "expected_total": None,
                "range_low": None,
                "range_high": None,
                "price_per_quintal": None,
            })
            continue

        point = row.get("forecast_price")
        interval = row.get("interval") or {}
        p05, p95 = interval.get("p05"), interval.get("p95")

        entry = {
            "horizon_days": row["horizon_days"],
            "target_date": row.get("target_date"),
            "label": f"{row['horizon_days']}-day",
            "status": "OK",
            "expected_total": round(point * qty, 2) if point is not None else None,
            "range_low": round(p05 * qty, 2) if p05 is not None else None,
            "range_high": round(p95 * qty, 2) if p95 is not None else None,
            "price_per_quintal": round(float(point), 2) if point is not None else None,
            "decision": row.get("decision"),
            "interval_source": row.get("interval_source"),
        }
        days.append(entry)

    priced_days = [d for d in days if d.get("expected_total") is not None]
    best_day = max(priced_days, key=lambda d: d["expected_total"]) if priced_days else None
    safest_day = (
        min(
            (d for d in priced_days if d["range_low"] is not None and d["range_high"] is not None),
            key=lambda d: (d["range_high"] - d["range_low"]),
        )
        if any(d.get("range_low") is not None for d in priced_days)
        else None
    )

    return {
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "status": "OK",
        "quantity_quintals": qty,
        "as_of_date": as_of_date,
        "days": days,
        "best_day": best_day["target_date"] if best_day else None,
        "best_day_horizon": best_day["horizon_days"] if best_day else None,
        "safest_day": safest_day["target_date"] if safest_day else None,
    }
