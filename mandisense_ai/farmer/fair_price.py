"""
Fair Price Check.

A farmer standing at the mandi gate, offered a price by a trader, needs one
number: is this offer fair, right now, for this crop, at this mandi. Every
other farmer surface in this system answers "what will happen" (a forecast);
this is the one that answers "is what is happening to me right now normal."

Two independent readings are combined, and each is reported on its own
because they answer slightly different questions:

  * where the offer sits against *today's actually observed* trades at this
    mandi (the min/modal/max the feed printed today, or the most recent day
    it printed) -- grounded in what really changed hands, available the
    moment ingestion runs even before a series is old enough to forecast
  * where it sits against the *calibrated* 1-day-ahead interval, when one
    exists -- a forward-looking band, not just a backward-looking one

Never fabricates a verdict from nothing: a mandi with no recent print at all
returns UNAVAILABLE rather than inventing a range for it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from mandisense_ai.farmer import registry, world
from mandisense_ai.forecasting.naming import canonical_commodity
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# How an offer's position inside today's observed range reads to a farmer.
# Bucketed on where the offer sits between the day's min and max, because a
# raw percentile number means nothing at a mandi gate but "top" and "bottom"
# do.
_VERDICT_COPY = {
    "well_below": {
        "en": "This offer is well below today's going rate. You can ask for more.",
        "kn": "ಈ ಬೆಲೆ ಇಂದಿನ ಮಾರುಕಟ್ಟೆ ದರಕ್ಕಿಂತ ಬಹಳ ಕಡಿಮೆ. ಹೆಚ್ಚು ಕೇಳಿ.",
    },
    "below": {
        "en": "This offer is a little below today's going rate.",
        "kn": "ಈ ಬೆಲೆ ಇಂದಿನ ದರಕ್ಕಿಂತ ಸ್ವಲ್ಪ ಕಡಿಮೆ.",
    },
    "fair": {
        "en": "This offer is within today's normal range.",
        "kn": "ಈ ಬೆಲೆ ಇಂದಿನ ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿಯಲ್ಲಿದೆ.",
    },
    "above": {
        "en": "This offer is above today's typical rate. A good price.",
        "kn": "ಈ ಬೆಲೆ ಇಂದಿನ ಸಾಮಾನ್ಯ ದರಕ್ಕಿಂತ ಹೆಚ್ಚು. ಒಳ್ಳೆಯ ಬೆಲೆ.",
    },
    "well_above": {
        "en": "This offer is well above today's typical rate. An excellent price.",
        "kn": "ಈ ಬೆಲೆ ಇಂದಿನ ದರಕ್ಕಿಂತ ಬಹಳ ಹೆಚ್ಚು. ಅತ್ಯುತ್ತಮ ಬೆಲೆ.",
    },
}


def _verdict_bucket(offered: float, low: float, high: float) -> str:
    if high <= low:
        return "fair"
    span = high - low
    position = (offered - low) / span
    if position < -0.15:
        return "well_below"
    if position < 0.05:
        return "below"
    if position <= 0.95:
        return "fair"
    if position <= 1.15:
        return "above"
    return "well_above"


def _recent(commodity: str, place: str) -> pd.DataFrame:
    """The latest week of prints for a place: a mandi's own min / modal / max
    where it reports them, otherwise its district's weighted price."""
    if place in registry.MANDIS:
        prices = world.mandi_prices()
        if prices.empty:
            return prices
        sub = prices[(prices["commodity"] == commodity) & (prices["mandi_id"] == place)]
        return sub.sort_values("date").tail(7)
    return world.district_series(commodity, place).tail(7)


def check_offer(
    commodity: str,
    mandi_id: str,
    offered_price: float,
    quantity_quintals: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Where an offered price sits against today's market for one series.

    Returns a status of OK or UNAVAILABLE (never a fabricated range). On OK,
    both readings that were available are included; a series can have the
    observed reading without the calibrated one (too new to forecast) but
    never the reverse, since a forecast implies observed history exists.
    """
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = registry.resolve_place(mandi_id)

    try:
        recent = _recent(resolved_commodity, resolved_mandi)
    except Exception as exc:
        logger.error("Fair price check: observation read failed: %s", exc)
        recent = pd.DataFrame()

    if recent.empty:
        return {
            "commodity": resolved_commodity,
            "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE",
            "reason": "No recent recorded trades for this crop at this mandi.",
        }

    latest = recent.iloc[-1]
    # Prefer the day's actual printed min/max when the feed carries them;
    # fall back to the trailing week's modal-price range when it does not,
    # so a farmer still gets a reading rather than nothing.
    day_min = latest.get("min_price")
    day_max = latest.get("max_price")
    if pd.isna(day_min) or pd.isna(day_max) or day_min is None or day_max is None or day_min <= 0:
        day_min = float(recent["modal_price"].min())
        day_max = float(recent["modal_price"].max())
    else:
        day_min, day_max = float(day_min), float(day_max)

    observed_reading = {
        "as_of_date": str(pd.Timestamp(latest["date"]).date()),
        "modal_price": round(float(latest["modal_price"]), 2),
        "range_low": round(day_min, 2),
        "range_high": round(day_max, 2),
        "verdict": _verdict_bucket(offered_price, day_min, day_max),
    }

    forecast_reading = None
    try:
        service = world.forecast_service()
        if service.is_available and registry.is_district(resolved_mandi):
            row = service.get_horizon(resolved_commodity, resolved_mandi, 1) or service.nearest_horizon(
                resolved_commodity, resolved_mandi, 1
            )
            if row and row.get("status") == "OK" and row.get("interval"):
                interval = row["interval"]
                if interval.get("p05") is not None and interval.get("p95") is not None:
                    forecast_reading = {
                        "horizon_days": row.get("horizon_days"),
                        "target_date": row.get("target_date"),
                        "range_low": round(float(interval["p05"]), 2),
                        "range_high": round(float(interval["p95"]), 2),
                        "verdict": _verdict_bucket(
                            offered_price, float(interval["p05"]), float(interval["p95"])
                        ),
                    }
    except Exception as exc:
        logger.warning("Fair price check: forecast reading unavailable: %s", exc)

    # The observed reading is the primary verdict -- it is grounded in trades
    # that actually happened today, where the forecast reading is a
    # calibrated *expectation*. When both exist and disagree, the farmer is
    # told both rather than one silently overriding the other.
    primary_verdict = observed_reading["verdict"]

    result: Dict[str, Any] = {
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "status": "OK",
        "offered_price": round(float(offered_price), 2),
        "verdict": primary_verdict,
        "message": _VERDICT_COPY[primary_verdict],
        "observed": observed_reading,
        "forecast": forecast_reading,
    }

    if quantity_quintals:
        qty = float(quantity_quintals)
        fair_value = observed_reading["modal_price"] * qty
        offered_value = float(offered_price) * qty
        result["quantity_quintals"] = qty
        result["offered_total"] = round(offered_value, 2)
        result["typical_total"] = round(fair_value, 2)
        result["difference"] = round(offered_value - fair_value, 2)

    return result
