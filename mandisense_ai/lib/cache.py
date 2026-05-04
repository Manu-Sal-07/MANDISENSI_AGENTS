import copy
import json
import os
import threading
import time
import uuid
from typing import Any, Dict, Optional

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

from mandisense_ai.lib.logger import log_failure

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(PACKAGE_ROOT, "data", "cache.json")
_MIN_TTL_SECONDS = 1800
_MAX_TTL_SECONDS = 3600
_CACHE_LOCK = threading.RLock()
_redis_client: Optional[Any] = None


def _normalize_ttl(ttl_seconds: Optional[int]) -> int:
    if ttl_seconds is None:
        return _MAX_TTL_SECONDS
    return max(_MIN_TTL_SECONDS, min(_MAX_TTL_SECONDS, int(ttl_seconds)))


def _get_redis_client() -> Optional[Any]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if redis is None:
        return None
    try:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            client = redis.Redis.from_url(redis_url, decode_responses=True)
        else:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD") or None
            client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        log_failure("mandi_cache", f"redis client unavailable: {exc}")
        _redis_client = None
        return None


def _redis_get(key: str) -> Optional[str]:
    client = _get_redis_client()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as exc:
        log_failure("mandi_cache", f"redis get failed: {exc}", metadata={"key": key})
        return None


def _redis_set(key: str, value: str, ttl: int) -> bool:
    client = _get_redis_client()
    if client is None:
        return False
    try:
        return client.setex(key, ttl, value)
    except Exception as exc:
        log_failure("mandi_cache", f"redis set failed: {exc}", metadata={"key": key})
        return False


def _load_cache() -> Dict[str, Any]:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log_failure("mandi_cache", f"cache load failed: {exc}")
        return {}


def _save_cache(data: Dict[str, Any]) -> None:
    cache_dir = os.path.dirname(CACHE_FILE)
    os.makedirs(cache_dir, exist_ok=True)
    temp_path = os.path.join(cache_dir, f"cache-{uuid.uuid4().hex}.json")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(temp_path, CACHE_FILE)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def _prune_expired(cache: Dict[str, Any]) -> None:
    now = time.time()
    expired_keys = []
    for key, entry in list(cache.items()):
        if not isinstance(entry, dict):
            expired_keys.append(key)
            continue
        expires_at = entry.get("expires_at")
        if expires_at is None or expires_at <= now:
            expired_keys.append(key)
    for key in expired_keys:
        cache.pop(key, None)


def _load_file_entry(key: str, include_expired: bool = False) -> Optional[Dict[str, Any]]:
    cache = _load_cache()
    if not include_expired:
        _prune_expired(cache)
    entry = cache.get(key)
    if not isinstance(entry, dict):
        return None
    return entry


def _decode_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(entry, dict):
        return None
    try:
        expires_at = float(entry.get("expires_at", 0.0) or 0.0)
    except (TypeError, ValueError):
        log_failure("mandi_cache", "malformed cache expiry", metadata={"key": entry})
        return None
    return {
        "data": copy.deepcopy(entry.get("data")),
        "created_at": entry.get("created_at"),
        "expires_at": expires_at,
        "ttl_seconds": entry.get("ttl_seconds"),
        "hit": expires_at > time.time(),
        "expired": expires_at <= time.time(),
    }


def get_cache_entry(key: str, include_expired: bool = False) -> Optional[Dict[str, Any]]:
    if not include_expired:
        raw = _redis_get(key)
        if raw is not None:
            try:
                entry = json.loads(raw)
                decoded = _decode_entry(entry)
                if decoded and decoded.get("hit"):
                    return decoded
            except Exception as exc:
                log_failure("mandi_cache", f"redis cache decode failed: {exc}", metadata={"key": key})
        file_entry = _load_file_entry(key, include_expired=False)
        return _decode_entry(file_entry) if file_entry else None

    file_entry = _load_file_entry(key, include_expired=True)
    if file_entry:
        return _decode_entry(file_entry)
    raw = _redis_get(key)
    if raw is None:
        return None
    try:
        entry = json.loads(raw)
        return _decode_entry(entry)
    except Exception as exc:
        log_failure("mandi_cache", f"redis cache decode failed: {exc}", metadata={"key": key})
        return None


def get_cache(key: str) -> Optional[Any]:
    entry = get_cache_entry(key)
    if not entry or not entry.get("hit"):
        return None
    return copy.deepcopy(entry.get("data"))


def set_cache(
    key: str,
    data: Any,
    ttl: Optional[int] = None,
    ttl_seconds: Optional[int] = None,
) -> None:
    if data is None:
        return
    if ttl is None:
        ttl = ttl_seconds
    normalized_ttl = _normalize_ttl(ttl)
    now = time.time()
    expires_at = now + normalized_ttl
    entry = {
        "data": copy.deepcopy(data),
        "created_at": now,
        "expires_at": expires_at,
        "ttl_seconds": normalized_ttl,
    }
    with _CACHE_LOCK:
        try:
            _redis_set(key, json.dumps(entry), normalized_ttl)
        except Exception:
            pass
        cache = _load_cache()
        cache[key] = entry
        try:
            _save_cache(cache)
        except Exception as exc:
            log_failure("mandi_cache", f"cache save failed: {exc}", metadata={"key": key})
