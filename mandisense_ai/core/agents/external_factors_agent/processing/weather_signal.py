"""
Weather signal conversion for the External Factors Agent.

Pipeline:
    mandi -> coordinates -> weather data -> weather features -> signal [-1, 1]

The output is intentionally normalized and compact so it can be combined with
policy/festival signals into a downstream external impact score.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from mandisense_ai.utils.logger import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - direct script fallback
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from mandisense_ai.core.agents.external_factors_agent.ingestion.weather_fetcher import fetch_weather
except Exception:
    from mandisense_ai.core.agents.external_factors_agent.ingestion.weather_fetcher import fetch_weather


try:
    from mandisense_ai.cognition.world_model.topology import MarketRegistry
except ImportError:
    # Fallback for standalone scripts
    class MarketRegistry:
        @classmethod
        def resolve_coordinates(cls, mandi_id: str): return (12.9716, 77.5946) # Bengaluru fallback

EPSILON = 1e-6


@dataclass(frozen=True)
class WeatherFeatures:
    recent_rain_7d: float
    baseline_rain_30d: float
    rainfall_deviation: float
    recent_temp_7d: float
    baseline_temp_30d: float
    temp_anomaly: float
    decayed_rain_7d: float
    decayed_temp_7d: float


def _normalize_name(value: str) -> str:
    return str(value).strip().lower().replace("_", " ")


def resolve_mandi_coordinates(mandi: str, district: Optional[str] = None) -> Tuple[float, float]:
    """
    Resolve mandi coordinates using the Institutional Market Registry.
    """
    coords = MarketRegistry.resolve_coordinates(mandi)
    if coords:
        return coords
    
    if district:
        coords = MarketRegistry.resolve_coordinates(district)
        if coords:
            return coords

    raise KeyError(f"INTEGRITY FAILURE: No coordinates found for '{mandi}' @ '{district or 'unknown_dist'}'")


def _weighted_recent_mean(values: pd.Series, half_life_days: float = 3.0) -> float:
    arr = pd.to_numeric(values, errors="coerce").to_numpy(dtype="float64")
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return 0.0
    age = np.arange(len(arr) - 1, -1, -1, dtype="float64")
    weights = np.exp(-np.log(2.0) * age / max(half_life_days, EPSILON))
    return float(np.average(arr, weights=weights))


def _smooth_series(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.sort_values("date").copy()
    clean["temperature_smooth"] = (
        clean["temperature"].rolling(window=3, min_periods=1).mean()
    )
    clean["precipitation_smooth"] = (
        clean["precipitation"].rolling(window=3, min_periods=1).mean()
    )
    return clean


def build_weather_features(weather_df: pd.DataFrame, current_date: str) -> WeatherFeatures:
    """
    Engineer weather features using only dates <= current_date.
    """
    current = pd.to_datetime(current_date, errors="raise").normalize()
    df = weather_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["date"]).sort_values("date")
    df = df[df["date"] <= current].copy()

    if df.empty:
        raise ValueError("No weather data available on or before current_date")

    expected = pd.date_range(current - pd.Timedelta(days=29), current, freq="D")
    df = pd.DataFrame({"date": expected}).merge(df, on="date", how="left")
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").interpolate(
        method="linear", limit_direction="both"
    )
    df["temperature"] = df["temperature"].ffill().bfill()
    df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0).clip(lower=0.0)
    df = _smooth_series(df)

    recent = df.tail(7)
    baseline = df.tail(30)

    recent_rain_7d = float(recent["precipitation_smooth"].sum())
    baseline_rain_30d = float(baseline["precipitation_smooth"].mean())
    rainfall_deviation = (recent_rain_7d - baseline_rain_30d) / (baseline_rain_30d + EPSILON)

    recent_temp_7d = float(recent["temperature_smooth"].mean())
    baseline_temp_30d = float(baseline["temperature_smooth"].mean())
    temp_anomaly = recent_temp_7d - baseline_temp_30d

    decayed_rain_7d = _weighted_recent_mean(recent["precipitation_smooth"], half_life_days=3.0) * 7.0
    decayed_temp_7d = _weighted_recent_mean(recent["temperature_smooth"], half_life_days=3.0)

    return WeatherFeatures(
        recent_rain_7d=recent_rain_7d,
        baseline_rain_30d=baseline_rain_30d,
        rainfall_deviation=float(rainfall_deviation),
        recent_temp_7d=recent_temp_7d,
        baseline_temp_30d=baseline_temp_30d,
        temp_anomaly=float(temp_anomaly),
        decayed_rain_7d=float(decayed_rain_7d),
        decayed_temp_7d=float(decayed_temp_7d),
    )


def weather_features_to_signal(features: WeatherFeatures) -> Dict[str, Any]:
    rain_signal = 0.0
    if features.rainfall_deviation < -0.3:
        rain_signal = 0.7
    elif features.rainfall_deviation > 0.3:
        rain_signal = -0.5

    temp_signal = 0.0
    if features.temp_anomaly > 3.0:
        temp_signal = 0.4
    elif features.temp_anomaly < -3.0:
        temp_signal = -0.3

    weather_signal = (0.7 * rain_signal) + (0.3 * temp_signal)
    weather_signal = float(np.clip(weather_signal, -1.0, 1.0))

    return {
        "weather_signal": round(weather_signal, 6),
        "components": {
            "rain_signal": round(float(rain_signal), 6),
            "temp_signal": round(float(temp_signal), 6),
        },
        "features": {
            "recent_rain_7d": round(features.recent_rain_7d, 6),
            "baseline_rain_30d": round(features.baseline_rain_30d, 6),
            "rainfall_deviation": round(features.rainfall_deviation, 6),
            "recent_temp_7d": round(features.recent_temp_7d, 6),
            "baseline_temp_30d": round(features.baseline_temp_30d, 6),
            "temp_anomaly": round(features.temp_anomaly, 6),
            "decayed_rain_7d": round(features.decayed_rain_7d, 6),
            "decayed_temp_7d": round(features.decayed_temp_7d, 6),
        },
    }


def get_weather_signal(
    mandi: str,
    commodity: str,
    date: str,
    *,
    district: Optional[str] = None,
    weather_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Return normalized weather impact signal for a mandi/commodity/date.

    Uses only the 30 days ending at `date`, so no future weather leaks into
    the signal. `weather_df` can be supplied by tests or upstream batch jobs;
    otherwise Open-Meteo data is fetched through weather_fetcher.
    """
    lat = lon = 0.0
    try:
        current = pd.to_datetime(date, errors="raise").normalize()
        start = current - pd.Timedelta(days=29)
        lat, lon = resolve_mandi_coordinates(mandi, district=district)

        if weather_df is None:
            weather_df = fetch_weather(
                lat,
                lon,
                start.strftime("%Y-%m-%d"),
                current.strftime("%Y-%m-%d"),
            )

        features = build_weather_features(weather_df, current.strftime("%Y-%m-%d"))
        output = weather_features_to_signal(features)
        output.update(
            {
                "mandi": mandi,
                "commodity": commodity,
                "date": current.strftime("%Y-%m-%d"),
                "coordinates": {"latitude": lat, "longitude": lon},
            }
        )
        return output
    except Exception as exc:
        logger.error(f"Weather signal failed for {commodity}/{mandi} @ {date}: {exc}", exc_info=True)
        return {
            "weather_signal": 0.0,
            "components": {"rain_signal": 0.0, "temp_signal": 0.0},
            "mandi": mandi,
            "commodity": commodity,
            "date": str(date),
            "coordinates": {"latitude": lat, "longitude": lon},
            "error": str(exc),
        }

