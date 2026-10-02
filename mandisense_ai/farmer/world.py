"""
The farmer data world: where its data, models and forecasts live, and the
accessors every farmer feature reads them through.

The farmer surface runs on its own real-data store, not the shared
observation and forecast stores the trader analytics read. Two reasons:

* The shared store also holds a synthetic Karnataka set that does not match
  real Agmarknet prices; a farmer must never be shown a price from it.
* Retraining or republishing the farmer forecasts must not be able to move a
  number on any trader screen.

Every farmer module goes through this file, so there is exactly one place that
decides which store a farmer feature reads.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from mandisense_ai.forecasting.ledger import ForecastLedger
from mandisense_ai.forecasting.service import ForecastService
from mandisense_ai.forecasting.store import ObservationStore

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = _PACKAGE_ROOT / "data" / "farmer"
SOURCE_DIR = DATA_DIR / "source"
DISTRICT_OBSERVATIONS = DATA_DIR / "district_observations.parquet"
MANDI_PRICES = DATA_DIR / "mandi_prices.parquet"

MODEL_DIR = _PACKAGE_ROOT / "models" / "farmer"
BUNDLE_DIR = MODEL_DIR / "forecast_models"
FORECAST_STORE = MODEL_DIR / "forecast_store.json"
MODEL_REPORT = MODEL_DIR / "model_report.json"
LEDGER = MODEL_DIR / "forecast_ledger.parquet"
TRANSMISSION_MATRIX = MODEL_DIR / "transmission_matrix.json"

_SERVICE: Optional[ForecastService] = None
_SERVICE_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}


def forecast_service() -> ForecastService:
    """The farmer forecast reader (separate store and cache from the trader's)."""
    global _SERVICE
    if _SERVICE is None:
        with _SERVICE_LOCK:
            if _SERVICE is None:
                _SERVICE = ForecastService(store_path=FORECAST_STORE)
    return _SERVICE


def observation_store() -> ObservationStore:
    return ObservationStore(DISTRICT_OBSERVATIONS)


def ledger() -> ForecastLedger:
    return ForecastLedger(LEDGER)


def _cached_parquet(key: str, path: Path) -> pd.DataFrame:
    """Parquet read cached on file modification time, so a rebuilt store is
    picked up without a restart and a request never re-reads an unchanged one."""
    if not path.exists():
        return pd.DataFrame()
    key = f"{key}:{path}"
    stamp = path.stat().st_mtime
    hit = _CACHE.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    frame = pd.read_parquet(path)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
    _CACHE[key] = (stamp, frame)
    return frame


def district_observations() -> pd.DataFrame:
    return _cached_parquet("district", DISTRICT_OBSERVATIONS)


def mandi_prices() -> pd.DataFrame:
    """Per-mandi daily prices (min / modal / max / arrivals), one row per
    mandi, crop and date, with variety and grade merged by arrivals weight."""
    return _cached_parquet("mandi", MANDI_PRICES)


def district_series(commodity: str, district_id: str) -> pd.DataFrame:
    frame = district_observations()
    if frame.empty:
        return frame
    sub = frame[(frame["commodity"] == commodity) & (frame["mandi_id"] == district_id)]
    return sub.sort_values("date")


def transmission_matrix() -> Dict[str, Any]:
    """Cross-commodity and cross-district transmission results (see
    scripts/build_transmission.py and mandisense_ai/farmer/transmission.py).
    Read-only, cached on file modification time like the other artifacts."""
    key = "transmission"
    if not TRANSMISSION_MATRIX.exists():
        return {"available": False}
    stamp = TRANSMISSION_MATRIX.stat().st_mtime
    hit = _CACHE.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        data = {"available": True, **json.loads(TRANSMISSION_MATRIX.read_text(encoding="utf-8"))}
    except Exception:
        return {"available": False}
    _CACHE[key] = (stamp, data)
    return data


def model_report() -> Dict[str, Any]:
    if not MODEL_REPORT.exists():
        return {"available": False}
    try:
        return {"available": True, **json.loads(MODEL_REPORT.read_text(encoding="utf-8"))}
    except Exception:
        return {"available": False}
