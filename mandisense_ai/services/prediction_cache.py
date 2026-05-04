"""
Production-grade prediction caching service for MandiSense AI.
Provides deterministic, daily-based caching for ML inferences.
"""

import json
import logging
from datetime import date
from typing import Optional, Any, Dict

from mandisense_ai.lib.cache import _redis_get, _redis_set, ping_redis
import logging

logger = logging.getLogger("mandisense_api")


# Standard TTL: 24 hours
DEFAULT_TTL = 86400

def get_prediction_cache_key(commodity: str, mandi: str) -> str:
    """
    Generates a deterministic cache key for a commodity/mandi on the current date.
    Format: commodity:mandi:YYYY-MM-DD
    """
    clean_commodity = str(commodity).strip().lower().replace(" ", "_")
    clean_mandi = str(mandi).strip().lower().replace(" ", "_")
    current_date = date.today().isoformat()
    return f"{clean_commodity}:{clean_mandi}:{current_date}"

def get_cached_prediction(key: str, request_id: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to retrieve a cached prediction from Redis.
    """
    try:
        raw_data = _redis_get(key)
        if raw_data:
            cached_res = json.loads(raw_data)
            
            # Attach current request_id and set cache hit flag
            cached_res["request_id"] = request_id
            cached_res["cache"] = {"hit": True}
            
            logger.info(json.dumps({
                "event": "cache_hit",
                "key": key,
                "request_id": request_id
            }))
            return cached_res
    except Exception as e:
        logger.warning(json.dumps({
            "event": "cache_error",
            "error": str(e),
            "request_id": request_id
        }))
    return None

def set_cached_prediction(key: str, prediction_data: Dict[str, Any], request_id: str):
    """
    Persists a prediction in Redis with a 24-hour TTL.
    Does not cache fallback or error responses.
    """
    # Safety Check: Don't cache fallbacks or errors
    if prediction_data.get("status") != "success":
        return

    try:
        # Create a copy to avoid modifying the original response object
        data_to_cache = prediction_data.copy()
        
        # Remove request_id and cache hit flag from the stored value
        # to ensure it's clean for the next retrieval
        if "request_id" in data_to_cache:
            del data_to_cache["request_id"]
        if "cache" in data_to_cache:
            del data_to_cache["cache"]
            
        success = _redis_set(key, json.dumps(data_to_cache), DEFAULT_TTL)
        
        if success:
            logger.info(json.dumps({
                "event": "cache_miss",
                "key": key,
                "request_id": request_id
            }))
    except Exception as e:
        logger.warning(json.dumps({
            "event": "cache_error",
            "error": str(e),
            "request_id": request_id
        }))
