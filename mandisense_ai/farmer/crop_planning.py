"""
What to Plant Next Season.

Deliberately not a forecast: the published models look 7 days ahead (see
`forecasting/config.FORECAST_HORIZONS`), which cannot say anything honest
about a harvest months away. What *can* be said honestly is what this mandi's
history shows about each crop's seasonal pattern -- some crops are reliably
worth more at certain times of year than others, and that pattern is exactly
what the climatology table already captures for each series individually
(see `seasonal_memory.py`). This compares that pattern across every tracked
crop at one mandi, for one target month, and labels it as a historical
pattern throughout rather than borrowing a forecast's authority.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, TARGET_COMMODITIES, ForecastConfig
from mandisense_ai.farmer import registry, world
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def _bucket_of_month(month: int, bucket_days: int) -> List[int]:
    """Every seasonal bucket whose midpoint falls in the given month."""
    buckets = []
    for day_of_year in range(1, 366, max(1, bucket_days // 3)):
        date = pd.Timestamp(year=2024, dayofyear=min(day_of_year, 365))
        if date.month == month:
            buckets.append(int(day_of_year // bucket_days))
    return sorted(set(buckets))


def seasonal_crop_comparison(
    mandi_id: str,
    target_month: int,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """
    For each tracked crop at `mandi_id`, how its price in `target_month`
    has historically compared to its own yearly average -- ranked so the
    crop most reliably *above* its own norm in that month sorts first.
    """
    resolved_mandi = registry.series_place(mandi_id)
    if not (1 <= target_month <= 12):
        return {"status": "ERROR", "reason": "target_month must be 1-12."}

    try:
        observations = world.district_observations()
    except Exception as exc:
        logger.error("Crop planning: observation read failed: %s", exc)
        return {"status": "UNAVAILABLE", "reason": "Observation data unavailable."}

    if observations.empty:
        return {"status": "UNAVAILABLE", "reason": "No observation data available."}

    subset = observations[observations["mandi_id"] == resolved_mandi].copy()
    if subset.empty:
        return {"status": "UNAVAILABLE", "reason": f"No history recorded for {resolved_mandi}."}

    subset["date"] = pd.to_datetime(subset["date"])
    subset["month"] = subset["date"].dt.month
    subset["year"] = subset["date"].dt.year

    results: List[Dict[str, Any]] = []
    for commodity in TARGET_COMMODITIES:
        crop_rows = subset[subset["commodity"] == commodity]
        if len(crop_rows) < 30:
            continue

        yearly_mean = float(crop_rows["modal_price"].mean())
        month_rows = crop_rows[crop_rows["month"] == target_month]
        if month_rows.empty or yearly_mean <= 0:
            continue

        # Per-year deviation from that year's own annual mean, so a crop
        # whose price has simply trended up over the archive is not
        # mistaken for one that is seasonally strong in this month.
        per_year = crop_rows.groupby("year")["modal_price"].mean().rename("year_mean")
        month_with_year_mean = month_rows.merge(per_year, on="year", how="left")
        month_with_year_mean = month_with_year_mean[month_with_year_mean["year_mean"] > 0]
        if month_with_year_mean.empty:
            continue

        deviations = (
            (month_with_year_mean["modal_price"] - month_with_year_mean["year_mean"])
            / month_with_year_mean["year_mean"]
        )
        years_observed = int(month_with_year_mean["year"].nunique())

        results.append({
            "commodity": commodity,
            "years_observed": years_observed,
            "avg_deviation_from_own_yearly_mean_pct": round(float(deviations.mean()) * 100, 1),
            "consistency": round(float((deviations > 0).mean()) * 100, 1) if len(deviations) else None,
        })

    if not results:
        return {"status": "UNAVAILABLE", "reason": "Not enough multi-year history at this mandi to compare crops."}

    results.sort(key=lambda r: r["avg_deviation_from_own_yearly_mean_pct"], reverse=True)

    return {
        "status": "OK",
        "mandi_id": resolved_mandi,
        "target_month": target_month,
        "disclaimer": (
            "Historical seasonal pattern only, not a forecast -- this system's "
            "forecasts look 7 days ahead and cannot honestly predict a harvest "
            "months out. Ranked by how each crop has historically performed in "
            "this month relative to its own yearly average price at this mandi."
        ),
        "crops": results,
    }
