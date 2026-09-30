"""
This Time Last Year -- seasonal memory.

Every other feature in this module needs a live forecast, which needs enough
recent *contiguous* history (see `forecasting/features.py` segment-aware
gate). This one does not: it only reads what actually happened in past
years, so it keeps working through exactly the gap that leaves every other
feature reporting UNAVAILABLE -- a resumed series with one print has no
forecast, but it still has three years of the same calendar week to compare
against.

Two numbers, both grounded in printed trades, never a model output:

  * this year's most recent price against the multi-year median for this
    same time of year (the persisted climatology table, see
    `forecasting/seasonal.py`)
  * this year's most recent price against the literal price a year ago in
    the same calendar bucket
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.farmer import registry, world
from mandisense_ai.forecasting.naming import canonical_commodity
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def _bucket_of(date: pd.Timestamp, bucket_days: int) -> int:
    return int(date.dayofyear // bucket_days)


def seasonal_reading(
    commodity: str,
    mandi_id: str,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = registry.series_place(mandi_id)

    try:
        series = world.district_series(resolved_commodity, resolved_mandi)
    except Exception as exc:
        logger.error("Seasonal memory: observation read failed: %s", exc)
        series = pd.DataFrame()

    if series.empty:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "No recorded history for this crop at this mandi.",
        }

    series = series.copy()
    series["date"] = pd.to_datetime(series["date"])
    latest = series.iloc[-1]
    latest_date = pd.Timestamp(latest["date"])
    latest_price = float(latest["modal_price"])
    bucket = _bucket_of(latest_date, config.seasonal_bucket_days)

    # Literal same-period-last-year: a print within the same calendar bucket,
    # exactly one year (± bucket width) earlier -- not "365 rows back", since
    # the feed is gappy and a positional offset would land on the wrong week.
    one_year_ago = latest_date - pd.Timedelta(days=365)
    window = series[
        (series["date"] >= one_year_ago - pd.Timedelta(days=config.seasonal_bucket_days))
        & (series["date"] <= one_year_ago + pd.Timedelta(days=config.seasonal_bucket_days))
    ]
    last_year_entry = None
    if not window.empty:
        # Nearest print to the anniversary date, not just any print in the window.
        closest = window.iloc[(window["date"] - one_year_ago).abs().argsort().iloc[0]]
        last_year_price = float(closest["modal_price"])
        last_year_entry = {
            "date": str(pd.Timestamp(closest["date"]).date()),
            "price": round(last_year_price, 2),
            "change_pct": round((latest_price - last_year_price) / last_year_price * 100, 2)
            if last_year_price > 0 else None,
        }

    # Multi-year norm from the persisted climatology table (see
    # `forecasting/seasonal.py`), when a trained bundle has one.
    norm_entry = None
    try:
        from mandisense_ai.forecasting.train import ForecastBundle

        bundle = ForecastBundle.load(world.BUNDLE_DIR)
        table = getattr(bundle, "seasonal_climatology_table", {}) or {}
        entry = table.get((resolved_commodity, resolved_mandi, bucket))
        if entry and entry.get("median_price", 0) > 0:
            median_price = float(entry["median_price"])
            norm_entry = {
                "median_price": round(median_price, 2),
                "reference_years": entry.get("reference_years"),
                "deviation_pct": round((latest_price - median_price) / median_price * 100, 2),
            }
    except Exception as exc:
        logger.warning("Seasonal memory: climatology table unavailable: %s", exc)

    return {
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "status": "OK",
        "as_of_date": str(latest_date.date()),
        "current_price": round(latest_price, 2),
        "last_year": last_year_entry,
        "seasonal_norm": norm_entry,
    }
