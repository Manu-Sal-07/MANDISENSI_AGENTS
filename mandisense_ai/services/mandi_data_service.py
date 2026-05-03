import datetime
import threading
import time
from typing import Any, Dict, List, Optional

from mandisense_ai.lib.agmarknet_client import fetch_agmarknet_data
from mandisense_ai.lib.cache import get_cache, get_cache_entry, set_cache
from mandisense_ai.lib.logger import log_event, log_failure
from mandisense_ai.lib.validator import validate_mandi_data

LAST_API_CALL = 0.0
RATE_LIMIT_SECONDS = 15.0
CACHE_TTL_SECONDS = 3600
_RATE_LIMIT_LOCK = threading.Lock()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for record in data:
        name = str(record.get("name", "")).strip()
        normalized.append({
            "name": name.title(),
            "price": _safe_float(record.get("price"), 0.0),
            "arrival": _safe_float(record.get("arrival"), 0.0),
            "lat": _safe_float(record.get("lat"), 0.0),
            "lon": _safe_float(record.get("lon"), 0.0),
        })
    return normalized


def _cache_key(commodity: str) -> str:
    safe_commodity = str(commodity or "unknown").strip().lower() or "unknown"
    return f"mandi_snapshot:{safe_commodity}"


def _try_live_fetch(commodity: str) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    global LAST_API_CALL
    with _RATE_LIMIT_LOCK:
        now = time.monotonic()
        if now - LAST_API_CALL < RATE_LIMIT_SECONDS:
            return False, None
        LAST_API_CALL = now

    return True, fetch_agmarknet_data(commodity)


def _last_known_valid_snapshot(commodity: str) -> Optional[List[Dict[str, Any]]]:
    entry = get_cache_entry(_cache_key(commodity), include_expired=True)
    if not entry:
        return None
    data = entry.get("data")
    if validate_mandi_data(data):
        return _normalize_data(data)
    return None


def fallback_data(commodity: str) -> List[Dict[str, Any]]:
    snapshot = _last_known_valid_snapshot(commodity)
    if snapshot:
        return snapshot

    return [
        {
            "name": f"{str(commodity).strip().title() or 'Fallback'} Mandi",
            "price": 10000.0,
            "arrival": 50.0,
            "lat": 0.0,
            "lon": 0.0,
        }
    ]


def get_mandi_snapshot(commodity: str, location: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    start_time = time.time()
    source = "fallback"
    final_data: List[Dict[str, Any]] = fallback_data(commodity)
    error_msg: Optional[str] = None
    raw_data: Optional[List[Dict[str, Any]]] = None
    attempted_live = False
    cache_key = _cache_key(commodity)
    metadata: Dict[str, Any] = {"location": location} if location else {}

    try:
        attempted_live, raw_data = _try_live_fetch(commodity)
        if not attempted_live:
            error_msg = "External Agmarknet call skipped by rate limiter."
        elif raw_data is None:
            error_msg = "Live API unavailable, failed, or returned no parseable data."

        if raw_data is not None and validate_mandi_data(raw_data):
            normalized_live = _normalize_data(raw_data)
            if not validate_mandi_data(normalized_live):
                raise ValueError("Live data failed post-normalization validation.")
            final_data = normalized_live
            source = "live"
            set_cache(cache_key, final_data, ttl=CACHE_TTL_SECONDS)
        else:
            if raw_data is not None:
                error_msg = "Live Agmarknet data failed validation."

            cached_data = get_cache(cache_key)
            if cached_data and validate_mandi_data(cached_data):
                final_data = _normalize_data(cached_data)
                source = "cache"
                metadata["cache"] = "hit"
            else:
                metadata["cache"] = "miss"
                final_data = fallback_data(commodity)
                source = "fallback"
                error_msg = error_msg or "No valid live or cached mandi data available."

    except Exception as exc:
        log_failure("mandi_data_service", str(exc), commodity=commodity)
        final_data = fallback_data(commodity)
        source = "fallback"
        error_msg = f"Unexpected exception in mandi service: {exc}"

    if not validate_mandi_data(final_data):
        final_data = fallback_data(commodity)
        source = "fallback"
        error_msg = error_msg or "Final data failed validation; using fallback."

    latency_ms = (time.time() - start_time) * 1000
    metadata["attempted_live"] = attempted_live
    log_event(commodity, source, latency_ms, error_msg, metadata)

    return {
        "mandis": final_data,
        "source": source,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "OK",
    }


if __name__ == "__main__":
    print("--- TESTING MANDI DATA SERVICE LAYER ---")
    print("\nTest 1: Normal Fetch")
    result1 = get_mandi_snapshot("tomato")
    print(result1)
    print("\nTest 2: Immediate Re-fetch")
    result2 = get_mandi_snapshot("tomato")
    print(result2)
