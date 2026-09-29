"""
Hold-or-Rot.

The same forecast, run through two different crops, should not produce the
same advice. A calibrated 3% expected rise means something completely
different for onion (keeps for months) than for tomato (unsellable inside a
week): holding tomato for a 3% gain almost never clears what it loses to
spoilage in the same days, while onion can absorb weeks of storage loss for
the same gain. No other feature in this system prices that trade-off in
rupees, because none of them knows a crop's shelf life -- only this one
combines the forecast with `reference.SHELF_PROFILES`.

The verdict is computed, not asserted: for every day up to the shorter of
the crop's shelf life and the longest published horizon, net value is
(forecast price at that day) x (1 - cumulative spoilage) x quantity, compared
against selling today. Whichever day maximises that net value is the
recommendation, and the spoilage cost that was charged against it is shown
so the number is checkable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mandisense_ai.farmer.reference import shelf_profile
from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def hold_or_sell(
    commodity: str,
    mandi_id: str,
    quantity_quintals: Optional[float] = 1.0,
) -> Dict[str, Any]:
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()
    qty = float(quantity_quintals or 1.0)
    profile = shelf_profile(resolved_commodity)

    try:
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
        curve = service.get_curve(resolved_commodity, resolved_mandi) if service.is_available else []
    except Exception as exc:
        logger.error("Hold-or-rot: forecast lookup failed: %s", exc)
        curve = []

    if not curve:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "This series is not tracked.",
            "shelf_profile": {
                "shelf_life_days": profile.shelf_life_days,
                "category": profile.category,
            },
        }

    base_price = curve[0].get("last_observed_price")
    if not base_price:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "No current observed price.",
        }

    sell_today_value = float(base_price) * qty

    options: List[Dict[str, Any]] = []
    for row in curve:
        horizon = row.get("horizon_days")
        if row.get("status") != "OK" or not horizon:
            continue
        if horizon > profile.shelf_life_days:
            # Past this point the crop is unsellable at any price -- showing
            # a forecast for it would imply a choice that does not exist.
            continue

        point = row.get("forecast_price")
        if point is None:
            continue

        # Compounding daily loss, not simple subtraction: a crop losing 8%/day
        # does not lose 40% over 5 days, it loses 1 - 0.92^5 ~= 34%, and the
        # difference matters most for exactly the fast-spoiling crops this
        # feature exists for.
        surviving_fraction = max(0.0, (1 - profile.daily_loss_pct / 100.0) ** horizon)
        gross_value = float(point) * qty
        net_value = gross_value * surviving_fraction
        spoilage_cost = gross_value - net_value

        options.append({
            "horizon_days": horizon,
            "target_date": row.get("target_date"),
            "price_per_quintal": round(float(point), 2),
            "gross_value": round(gross_value, 2),
            "spoilage_cost": round(spoilage_cost, 2),
            "net_value": round(net_value, 2),
            "gain_vs_sell_today": round(net_value - sell_today_value, 2),
            "decision": row.get("decision"),
            "probability_of_decline": row.get("decision_probability_of_decline"),
        })

    best = max(options, key=lambda o: o["net_value"]) if options else None
    recommend_hold = bool(best and best["net_value"] > sell_today_value)

    return {
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "status": "OK",
        "quantity_quintals": qty,
        "shelf_profile": {
            "shelf_life_days": profile.shelf_life_days,
            "daily_loss_pct": profile.daily_loss_pct,
            "category": profile.category,
        },
        "sell_today_value": round(sell_today_value, 2),
        "options": options,
        "recommendation": "HOLD" if recommend_hold else "SELL",
        "best_option": best,
        "reasoning": (
            f"Waiting {best['horizon_days']} day(s) is worth "
            f"{'more' if recommend_hold else 'less'} than selling today, after "
            f"accounting for {profile.category.replace('_', ' ')} spoilage."
            if best else
            f"This crop's shelf life ({profile.shelf_life_days} days) is shorter "
            "than any horizon with a published forecast -- sell today."
        ),
    }
