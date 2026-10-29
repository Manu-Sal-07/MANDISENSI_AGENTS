"""
Real historical price + volume data for the TraderOS commodity chart.

Backed by the Agmarknet market-level panel the farmer world is built from
(`farmer.world.MARKET_PANEL`): every row is a price a mandi actually reported
on that day, five commodities across the Bengaluru-Kolar belt, 2021 onwards.
Nothing is filled or interpolated, so a mandi that did not report on a day has
no row; candles and summaries use only days with a report. This is deliberately
independent of the cognition/forecast engine: it serves the raw observed price
series used for charting (candles, volume, comparisons), not model predictions.

(An earlier version read `data/processed/v4/*.csv`, a synthetic seasonal
backfill that was removed with the other synthetic data.)

Only Week / Month / Year timeframes are exposed on purpose: the source is one
reported price per day, so there is no genuine intraday signal to show.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

import pandas as pd

from mandisense_ai.forecasting.naming import world_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger("candle_data_service")

VALID_COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]

# Resample rule per timeframe. Week/Month/Year only; see module docstring.
_TIMEFRAME_RULES = {"week": "W-SUN", "month": "MS", "year": "YS"}

_lock = threading.Lock()
_cache: Dict[str, object] = {}


def _panel() -> pd.DataFrame:
    """The market panel as (date, mandi_id, commodity, price, arrivals); re-read when the file changes."""
    from mandisense_ai.farmer import world

    path = world.MARKET_PANEL
    if not path.exists():
        raise FileNotFoundError(f"Market panel not built at {path}; run scripts/build_farmer_world.py")
    mtime = path.stat().st_mtime
    with _lock:
        if _cache.get("mtime") == mtime:
            return _cache["df"]  # type: ignore[return-value]
    df = pd.read_parquet(path).rename(columns={"crop": "commodity"})
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", "mandi_id", "commodity", "price", "arrivals"]].sort_values("date")
    with _lock:
        _cache.update({"mtime": mtime, "df": df})
    return df


def _load_commodity_frame(commodity: str) -> pd.DataFrame:
    commodity = commodity.lower()
    df = _panel()
    out = df[df["commodity"] == commodity]
    if out.empty:
        raise FileNotFoundError(f"No observations for commodity '{commodity}'")
    return out


def invalidate_cache(commodity: Optional[str] = None) -> None:
    """Called after new rows are appended to the panel."""
    with _lock:
        _cache.clear()


def list_available_markets() -> Dict[str, List[str]]:
    markets: Dict[str, List[str]] = {}
    for commodity in VALID_COMMODITIES:
        try:
            df = _load_commodity_frame(commodity)
            markets[commodity] = sorted(df["mandi_id"].unique().tolist())
        except FileNotFoundError:
            markets[commodity] = []
    return markets


def get_daily_series(commodity: str, mandi_id: str) -> pd.DataFrame:
    df = _load_commodity_frame(commodity)
    series = df[df["mandi_id"] == world_market(mandi_id)][["date", "price", "arrivals"]].copy()
    # A row can carry a NaN price; a point-in-time lookup ("the price 7 days ago") must not land on one.
    series = series.dropna(subset=["price"])
    if series.empty:
        raise ValueError(f"No data for {commodity} @ {mandi_id}")
    return series.set_index("date").sort_index()


def get_daily_points(commodity: str, mandi_id: str) -> List[Dict[str, object]]:
    """Full daily-granularity series (date/price/arrivals), for consumers
    that need per-day resolution — a line chart, a seasonality breakdown,
    a day-by-day replay — rather than resampled candles."""
    series = get_daily_series(commodity, mandi_id)
    return [
        {
            "timestamp": ts.strftime("%Y-%m-%d"),
            "price": round(float(row["price"]), 2),
            "arrivals": round(float(row["arrivals"]), 1) if pd.notna(row["arrivals"]) else 0.0,
        }
        for ts, row in series.iterrows()
    ]


def resample_candles(commodity: str, mandi_id: str, timeframe: str) -> List[Dict[str, object]]:
    if timeframe not in _TIMEFRAME_RULES:
        raise ValueError(f"Unsupported timeframe '{timeframe}'. Use one of {list(_TIMEFRAME_RULES)}.")

    series = get_daily_series(commodity, mandi_id)
    rule = _TIMEFRAME_RULES[timeframe]

    ohlc = series["price"].resample(rule).agg(["first", "max", "min", "last", "count"])
    volume = series["arrivals"].resample(rule).sum(min_count=1)

    candles: List[Dict[str, object]] = []
    for ts, row in ohlc.iterrows():
        if row["count"] == 0 or pd.isna(row["first"]):
            continue
        vol = volume.loc[ts]
        candles.append({
            "time": ts.strftime("%Y-%m-%d"),
            "open": round(float(row["first"]), 2),
            "high": round(float(row["max"]), 2),
            "low": round(float(row["min"]), 2),
            "close": round(float(row["last"]), 2),
            "volume": round(float(vol), 1) if pd.notna(vol) else 0.0,
        })
    return candles


def get_summary(commodity: str, mandi_id: str) -> Dict[str, object]:
    series = get_daily_series(commodity, mandi_id)

    monthly_price = series["price"].resample("MS").mean()
    monthly_volume = series["arrivals"].resample("MS").sum(min_count=1)

    highest_month = monthly_price.idxmax()
    lowest_month = monthly_price.idxmin()
    highest_volume_month = monthly_volume.idxmax() if monthly_volume.notna().any() else None

    latest = series.iloc[-1]
    latest_date = series.index[-1]

    def _pct_change_since(days: int) -> Optional[float]:
        cutoff = latest_date - pd.Timedelta(days=days)
        window = series[series.index >= cutoff]
        if len(window) < 2:
            return None
        start_price = window["price"].iloc[0]
        if pd.isna(start_price) or not start_price:
            return None
        return round(float((latest["price"] - start_price) / start_price * 100), 2)

    one_year_ago = latest_date - pd.DateOffset(years=1)
    yoy_window = series[series.index <= one_year_ago]
    yoy_change = None
    if not yoy_window.empty:
        base_price = yoy_window["price"].iloc[-1]
        if not pd.isna(base_price) and base_price:
            yoy_change = round(float((latest["price"] - base_price) / base_price * 100), 2)

    return {
        "commodity": commodity,
        "mandi_id": mandi_id,
        "as_of": latest_date.strftime("%Y-%m-%d"),
        "current_price": round(float(latest["price"]), 2),
        "week_change_pct": _pct_change_since(7),
        "month_change_pct": _pct_change_since(30),
        "year_change_pct": _pct_change_since(365),
        "year_over_year_pct": yoy_change,
        "highest_month": {
            "month": highest_month.strftime("%Y-%m"),
            "avg_price": round(float(monthly_price.loc[highest_month]), 2),
        },
        "lowest_month": {
            "month": lowest_month.strftime("%Y-%m"),
            "avg_price": round(float(monthly_price.loc[lowest_month]), 2),
        },
        "highest_volume_month": (
            {
                "month": highest_volume_month.strftime("%Y-%m"),
                "total_arrivals": round(float(monthly_volume.loc[highest_volume_month]), 1),
            }
            if highest_volume_month is not None
            else None
        ),
        "data_points": int(len(series)),
        "history_start": series.index[0].strftime("%Y-%m-%d"),
    }


def get_comparison_series(commodities: List[str], mandi_id: str, timeframe: str) -> Dict[str, object]:
    """Normalized (% change from first point) series per commodity, so all
    five can be overlaid on one trend-comparison chart regardless of their
    very different absolute price levels (e.g. ginger vs potato)."""
    series_by_commodity: Dict[str, List[Dict[str, object]]] = {}
    performance: List[Dict[str, object]] = []

    for commodity in commodities:
        try:
            candles = resample_candles(commodity, mandi_id, timeframe)
        except (FileNotFoundError, ValueError):
            continue
        if not candles:
            continue

        base = candles[0]["close"]
        if not base:
            continue

        normalized = [
            {"time": c["time"], "value": round(((c["close"] - base) / base) * 100, 2)}
            for c in candles
        ]
        series_by_commodity[commodity] = normalized
        performance.append({"commodity": commodity, "change_pct": normalized[-1]["value"]})

    performance.sort(key=lambda item: item["change_pct"], reverse=True)

    return {
        "mandi_id": mandi_id,
        "timeframe": timeframe,
        "series": series_by_commodity,
        "ranking": performance,
    }
