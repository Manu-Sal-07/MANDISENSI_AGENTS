"""
Price on a Date -- the honesty check behind "My Money".

A savings claim ("MandiSense saved you Rs. 2,400") is only as trustworthy as
the number it is measured against. This looks up what the recorded prices
actually say near a given date, so the client-side ledger can be verified
against real prints rather than against whatever it cached when the
recommendation was first shown.

Only ever reads recorded prices -- never a forecast -- because a past date has
a real outcome and using a model's guess about its own accuracy would be
circular.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from mandisense_ai.farmer import registry, world
from mandisense_ai.forecasting.naming import canonical_commodity
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# A remembered "the day I checked" and the mandi's actual trading day rarely
# land on the same date (weekends, holidays). The nearest earlier print within
# this window stands in; beyond it, silence is more honest than a stale price.
MAX_LOOKBACK_DAYS = 5


def _series(commodity: str, place: str) -> pd.DataFrame:
    if place in registry.MANDIS:
        prices = world.mandi_prices()
        if not prices.empty:
            sub = prices[(prices["commodity"] == commodity) & (prices["mandi_id"] == place)]
            if not sub.empty:
                return sub.sort_values("date")
        # A mandi with no print that far back falls through to its district.
        place = registry.district_of(place)
    return world.district_series(commodity, place)


def price_on_date(commodity: str, mandi_id: str, date: str) -> Dict[str, Any]:
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    place = registry.resolve_place(mandi_id)

    try:
        target = pd.Timestamp(date)
    except Exception:
        return {"commodity": resolved_commodity, "mandi_id": place, "status": "ERROR",
                "reason": f"Could not parse date '{date}'."}

    series = _series(resolved_commodity, place)
    if series.empty:
        return {"commodity": resolved_commodity, "mandi_id": place, "status": "UNAVAILABLE",
                "reason": "This series has no recorded prices."}

    on_or_before = series[series["date"] <= target]
    if on_or_before.empty:
        return {"commodity": resolved_commodity, "mandi_id": place, "status": "UNAVAILABLE",
                "reason": "No records on or before this date."}

    row = on_or_before.iloc[-1]
    gap_days = (target - row["date"]).days
    if gap_days > MAX_LOOKBACK_DAYS:
        return {"commodity": resolved_commodity, "mandi_id": place, "status": "UNAVAILABLE",
                "reason": f"Nearest record is {gap_days} days before the requested date."}

    return {
        "commodity": resolved_commodity,
        "mandi_id": place,
        "status": "OK",
        "requested_date": target.date().isoformat(),
        "matched_date": row["date"].date().isoformat(),
        "modal_price": float(row["modal_price"]),
        "gap_days": gap_days,
    }
