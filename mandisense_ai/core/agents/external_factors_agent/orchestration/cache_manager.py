import time
import json
import os

CACHE_FILE = "data/cache.json"
CACHE_EXPIRY = 1800 # 30 minutes

class CacheManager:
    def __init__(self):
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
    def _read_cache(self):
        if not os.path.exists(CACHE_FILE):
            return {}
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
            
    def _write_cache(self, data):
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
            
    def get_latest(self, commodity):
        cache = self._read_cache()
        if commodity in cache:
            record = cache[commodity]
            # Expiry logic
            if time.time() - record.get("last_updated", 0) <= CACHE_EXPIRY:
                return record
        return None
        
    def set(self, commodity, payload):
        cache = self._read_cache()
        payload["last_updated"] = time.time()
        cache[commodity] = payload
        self._write_cache(cache)
        
    def get_raw_input_hash(self):
        return self._read_cache().get("_data_hash", "")
        
    def set_raw_input_hash(self, hash_val):
        cache = self._read_cache()
        cache["_data_hash"] = hash_val
        self._write_cache(cache)

cache_manager = CacheManager()
