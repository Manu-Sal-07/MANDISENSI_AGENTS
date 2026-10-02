"""
Read-side API for the TraderOS commodity chart: candlestick history,
volume, cross-commodity trend comparison, and the live data.gov.in sync
job that keeps the underlying history a day fresher.

Deliberately independent of the cognition engine (api/cognition_router.py)
— this serves the raw observed price/volume series used for charting, not
model forecasts or trading directives.
"""
import asyncio

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from mandisense_ai.services import candle_data_service

router = APIRouter()

VALID_TIMEFRAMES = {"week", "month", "year"}
VALID_COMMODITIES = candle_data_service.VALID_COMMODITIES


@router.get("/markets")
async def get_markets():
    """Every commodity x mandi combination the chart can actually render."""
    return {"commodities": VALID_COMMODITIES, "markets": candle_data_service.list_available_markets()}


@router.get("/history/{commodity}/{mandi_id}")
async def get_history(commodity: str, mandi_id: str):
    """Full daily-granularity price/volume series for a real commodity x
    mandi pair — used by pages that need per-day resolution (a raw line
    chart, seasonality breakdown, day-by-day replay) rather than candles."""
    commodity = commodity.lower()
    if commodity not in VALID_COMMODITIES:
        raise HTTPException(status_code=404, detail=f"Unknown commodity '{commodity}'. Choose one of {VALID_COMMODITIES}.")
    try:
        points = candle_data_service.get_daily_points(commodity, mandi_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"commodity": commodity, "mandi_id": mandi_id, "history": points}


@router.get("/candles/{commodity}/{mandi_id}")
async def get_candles(commodity: str, mandi_id: str, timeframe: str = Query("month")):
    commodity = commodity.lower()
    if commodity not in VALID_COMMODITIES:
        raise HTTPException(status_code=404, detail=f"Unknown commodity '{commodity}'. Choose one of {VALID_COMMODITIES}.")
    if timeframe not in VALID_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"timeframe must be one of {sorted(VALID_TIMEFRAMES)}")

    try:
        candles = candle_data_service.resample_candles(commodity, mandi_id, timeframe)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"commodity": commodity, "mandi_id": mandi_id, "timeframe": timeframe, "candles": candles}


@router.get("/summary/{commodity}/{mandi_id}")
async def get_summary(commodity: str, mandi_id: str):
    commodity = commodity.lower()
    if commodity not in VALID_COMMODITIES:
        raise HTTPException(status_code=404, detail=f"Unknown commodity '{commodity}'.")
    try:
        return candle_data_service.get_summary(commodity, mandi_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/compare")
async def compare_commodities(
    mandi_id: str = Query(...),
    timeframe: str = Query("month"),
    commodities: Optional[str] = Query(None, description="Comma-separated; defaults to all 5"),
):
    if timeframe not in VALID_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"timeframe must be one of {sorted(VALID_TIMEFRAMES)}")
    selected = [c.strip().lower() for c in commodities.split(",")] if commodities else VALID_COMMODITIES
    return candle_data_service.get_comparison_series(selected, mandi_id, timeframe)


@router.post("/sync")
async def sync_live_prices():
    """Manually trigger the previous-day data.gov.in ingestion for all 5 commodities."""
    from mandisense_ai.ingestion.daily_price_sync import sync_all
    results = await asyncio.to_thread(sync_all)
    return {"status": "complete", "results": results}
