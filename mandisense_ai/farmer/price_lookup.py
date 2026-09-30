"""
Price on a Date -- the honesty check behind "My Money".

A savings claim ("MandiSense saved you Rs. 2,400") is only as trustworthy as
the number it is measured against. This looks up what the observation
archive actually recorded for a commodity/mandi near a given date, so a
client-side savings ledger can be verified against real prints rather than
trusting whatever number it cached when the recommendation was first shown.

Only ever reads the observation archive -- never a forecast -- because a
past date has a real, observed outcome and using a model's guess about its
own accuracy would be circular.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.forecasting.store import ObservationStore
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# A farmer's remembered "the day I checked" and the mandi's actual trading
# day rarely land on the same date (weekends, holidays, a market that did
# not print that day). Nearest available print within this window is a
# reasonable stand-in; beyond it, silence is more honest than a stale price.
MAX_LOOKBACK_DAYS = 5


def price_on_date(commodity: str, mandi_id: str, date: str) -> Dict[str, Any]:
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()

    try:
        target = pd.Timestamp(date)
    except Exception:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "ERROR", "reason": f"Could not parse date '{date}'.",
        }

    try:
        store = ObservationStore()
        series = store.read_series(resolved_commodity, resolved_mandi)
    except Exception as exc:
        logger.error("Price lookup failed: %s", exc)
        series = pd.DataFrame()

    if series.empty:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "This series has no recorded prices.",
        }

    series = series.copy()
    series["date"] = pd.to_datetime(series["date"])
    on_or_before = series[series["date"] <= target]
    if on_or_before.empty:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "No records on or before this date.",
        }

    row = on_or_before.sort_values("date").iloc[-1]
    gap_days = (target - row["date"]).days
    if gap_days > MAX_LOOKBACK_DAYS:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE",
            "reason": f"Nearest record is {gap_days} days before the requested date.",
        }

    return {
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "status": "OK",
        "requested_date": target.date().isoformat(),
        "matched_date": row["date"].date().isoformat(),
        "modal_price": float(row["modal_price"]),
        "gap_days": gap_days,
    }
