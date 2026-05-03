"""
Open-Meteo historical weather fetcher for External Factors Agent.

Fetches hourly temperature and precipitation from the Open-Meteo archive API,
aggregates to daily features, cleans gaps, and returns a deterministic
DataFrame:

    date | temperature | precipitation

The module is reusable across agents and supports file-based response caching
to avoid repeated API calls for the same location/date range.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import requests

try:
    from utils.logger import get_logger

    logger = get_logger(__name__)
except Exception:  # pragma: no cover - fallback for direct script use
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_CACHE_DIR = Path("data/cache/weather")
HOURLY_VARIABLES = ("temperature_2m", "precipitation")


class WeatherFetchError(RuntimeError):
    """Raised when weather data cannot be fetched or normalized."""


def _validate_inputs(lat: float, lon: float, start_date: str, end_date: str) -> tuple[float, float, pd.Timestamp, pd.Timestamp]:
    latitude = float(lat)
    longitude = float(lon)
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude out of range: {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude out of range: {longitude}")

    start = pd.to_datetime(start_date, errors="raise").normalize()
    end = pd.to_datetime(end_date, errors="raise").normalize()
    if start > end:
        raise ValueError(f"start_date must be <= end_date: {start_date} > {end_date}")
    return latitude, longitude, start, end


def _cache_key(lat: float, lon: float, start_date: str, end_date: str) -> str:
    payload = {
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "hourly": list(HOURLY_VARIABLES),
        "source": "open_meteo_archive_v1",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _read_cache(cache_path: Path) -> Optional[Dict[str, Any]]:
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Weather cache read failed for {cache_path}: {exc}")
        return None


def _write_cache(cache_path: Path, payload: Dict[str, Any]) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Weather cache write failed for {cache_path}: {exc}")


def _request_open_meteo(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    timeout: int,
    max_retries: int,
    backoff_seconds: float,
) -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
    }

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if "hourly" not in payload:
                raise WeatherFetchError(f"Open-Meteo response missing hourly payload: {payload}")
            return payload
        except Exception as exc:
            last_error = exc
            logger.warning(f"Open-Meteo request failed attempt={attempt}/{max_retries}: {exc}")
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)

    raise WeatherFetchError(f"Open-Meteo request failed after {max_retries} attempts: {last_error}")


def _payload_to_daily_frame(payload: Dict[str, Any], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    hourly = payload.get("hourly", {})
    time_values = hourly.get("time")
    temp_values = hourly.get("temperature_2m")
    precip_values = hourly.get("precipitation")

    if time_values is None or temp_values is None or precip_values is None:
        raise WeatherFetchError("Open-Meteo hourly data missing time/temperature_2m/precipitation")

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(time_values, errors="coerce", utc=False),
            "temperature": pd.to_numeric(pd.Series(temp_values), errors="coerce"),
            "precipitation": pd.to_numeric(pd.Series(precip_values), errors="coerce"),
        }
    ).dropna(subset=["timestamp"])

    if df.empty:
        raise WeatherFetchError("Open-Meteo returned no usable weather rows")

    df["date"] = df["timestamp"].dt.normalize()
    daily = (
        df.groupby("date", as_index=False)
        .agg(
            temperature=("temperature", "mean"),
            precipitation=("precipitation", "sum"),
        )
        .sort_values("date")
    )

    full_dates = pd.DataFrame({"date": pd.date_range(start=start, end=end, freq="D")})
    daily = full_dates.merge(daily, on="date", how="left")

    daily["temperature"] = daily["temperature"].interpolate(method="linear", limit_direction="both")
    daily["temperature"] = daily["temperature"].ffill().bfill()
    daily["precipitation"] = daily["precipitation"].fillna(0.0)
    daily["precipitation"] = daily["precipitation"].clip(lower=0.0)

    if daily[["temperature", "precipitation"]].isna().any().any():
        raise WeatherFetchError("Weather cleaning failed: NaNs remain after filling gaps")

    daily["temperature"] = daily["temperature"].astype("float32")
    daily["precipitation"] = daily["precipitation"].astype("float32")
    return daily[["date", "temperature", "precipitation"]].sort_values("date").reset_index(drop=True)


def fetch_weather(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    *,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
) -> pd.DataFrame:
    """
    Fetch historical weather and return clean daily data.

    Args:
        lat: Latitude for the mandi/location.
        lon: Longitude for the mandi/location.
        start_date: Inclusive start date, YYYY-MM-DD.
        end_date: Inclusive end date, YYYY-MM-DD.
        cache_dir: Directory for cached Open-Meteo JSON responses.
        use_cache: Use cached response when available.
        timeout: Per-request HTTP timeout in seconds.
        max_retries: Number of HTTP attempts before failing.
        backoff_seconds: Linear retry backoff multiplier.

    Returns:
        DataFrame with columns: date, temperature, precipitation.
    """
    latitude, longitude, start, end = _validate_inputs(lat, lon, start_date, end_date)
    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")

    cache_path = Path(cache_dir) / f"{_cache_key(latitude, longitude, start_s, end_s)}.json"
    payload = _read_cache(cache_path) if use_cache else None
    if payload is None:
        logger.info(f"Fetching Open-Meteo weather lat={latitude}, lon={longitude}, {start_s}..{end_s}")
        payload = _request_open_meteo(
            latitude,
            longitude,
            start_s,
            end_s,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        if use_cache:
            _write_cache(cache_path, payload)
    else:
        logger.info(f"Loaded weather response from cache: {cache_path}")

    return _payload_to_daily_frame(payload, start=start, end=end)


def fetch_weather_batch(
    locations: Iterable[Dict[str, Any]],
    *,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch weather for many locations/date ranges.

    Each location dict must contain: latitude, longitude, start_date, end_date.
    Optional key: id/name/mandi, used as the output dictionary key.
    """
    results: Dict[str, pd.DataFrame] = {}
    for idx, item in enumerate(locations):
        key = str(item.get("id") or item.get("name") or item.get("mandi") or idx)
        results[key] = fetch_weather(
            item["latitude"],
            item["longitude"],
            item["start_date"],
            item["end_date"],
            cache_dir=cache_dir,
            use_cache=use_cache,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
    return results


def weather_to_dict(df: pd.DataFrame) -> Dict[str, List[Any]]:
    """Convert a clean weather DataFrame to the required aligned dict format."""
    ordered = df[["date", "temperature", "precipitation"]].sort_values("date")
    return {
        "date": ordered["date"].dt.strftime("%Y-%m-%d").tolist(),
        "temperature": ordered["temperature"].astype(float).replace({np.nan: None}).tolist(),
        "precipitation": ordered["precipitation"].astype(float).replace({np.nan: None}).tolist(),
    }

