import json
import redis
from backend.config.settings import settings

r = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    decode_responses=True,
)


def get_cache(key: str):
    try:
        value = r.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def set_cache(key: str, value, ttl: int = 3600):
    try:
        r.setex(key, ttl, json.dumps(value))
    except Exception:
        pass
