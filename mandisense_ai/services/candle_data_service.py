"""
Real historical price + volume data for the TraderOS commodity chart.

Backed by the canonical v4 processed dataset — 5 commodities x 15 Karnataka
APMC mandis, daily granularity from 2023-01-02 onward. This is deliberately
independent of the cognition/forecast engine: it serves the raw observed
price series used purely for charting (candles, volume, comparisons), not
model predictions or trading directives.

Only Week / Month / Year timeframes are exposed on purpose — the source
data is a daily close, so there is no genuine intraday/minute-level signal
to show, and pretending otherwise would just be a hand-wavy chart.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from mandisense_ai.utils.logger import get_logger

logger = get_logger("candle_data_service")

_V4_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "v4"
VALID_COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]

# Resample rule per timeframe. Week/Month/Year only — see module docstring.
_TIMEFRAME_RULES = {"week": "W-SUN", "month": "MS", "year": "YS"}

_lock = threading.Lock()
_cache: Dict[str, Dict[str, object]] = {}


def _csv_path(commodity: str) -> Path:
    return _V4_DIR / f"{commodity.lower()}.csv"


def _load_commodity_frame(commodity: str) -> pd.DataFrame:
    commodity = commodity.lower()
    path = _csv_path(commodity)
    if not path.exists():
        raise FileNotFoundError(f"No processed dataset for commodity '{commodity}' at {path}")

    mtime = path.stat().st_mtime
    with _lock:
        cached = _cache.get(commodity)
        if cached and cached["mtime"] == mtime:
            return cached["df"]  # type: ignore[return-value]

    df = pd.read_csv(path, usecols=["date", "mandi_id", "commodity", "price", "arrivals"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    with _lock:
        _cache[commodity] = {"mtime": mtime, "df": df}

    return df


def invalidate_cache(commodity: Optional[str] = None) -> None:
    """Called by the live sync job after it appends new rows to a CSV."""
    with _lock:
        if commodity:
            _cache.pop(commodity.lower(), None)
        else:
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
    series = df[df["mandi_id"] == mandi_id][["date", "price", "arrivals"]].copy()
    # ~6% of days are flagged is_missing in the source data and carry a NaN
    # price. Resampling into candles already skips these safely, but a
    # point-in-time lookup (e.g. "the price 7 days ago") must not be allowed
    # to land on one of them, or every stat derived from it turns into NaN.
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
