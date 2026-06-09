import pandas as pd
import numpy as np
import time
import asyncio
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

# --- CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_V4_DIR = PROJECT_ROOT / "mandisense_ai" / "data" / "processed" / "v4"
WINDOW_SIZE = 14
DEFAULT_MODEL_VERSION = "v3"

class MandiDataService:
    _instance = None

    def __init__(self):
        # In-memory cache: {commodity: {mandi_id: dataframe}}
        self._cache = {}
        self._cache_expiry = {}
        self._metadata = {}
        self._locks = {} # STEP 1: CONCURRENCY CONTROL
        self.BASE_CACHE_TTL = 3600 * 6 
        
        # STEP 3: CIRCUIT BREAKER
        self._failure_count = 0
        self._circuit_open_until = 0
        self._circuit_threshold = 3
        
        # STEP 5: METRICS
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "external_fetches": 0,
            "failures": 0,
            "stale_data_usage": 0
        }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_lock(self, commodity: str):
        if commodity not in self._locks:
            self._locks[commodity] = asyncio.Lock()
        return self._locks[commodity]

    async def warm_up(self, commodities=None):
        if commodities is None:
            commodities = [f.stem for f in DATA_V4_DIR.glob("*.csv")]
        tasks = [self._load_into_cache(c) for c in commodities]
        await asyncio.gather(*tasks)

    async def _load_into_cache(self, commodity: str):
        # STEP 1: Locking
        async with self._get_lock(commodity):
            # STEP 3: Circuit Breaker Check
            if time.time() < self._circuit_open_until:
                print(f"Circuit open for {commodity}. Skipping external load.")
                return

            try:
                data_path = DATA_V4_DIR / f"{commodity}.csv"
                if not data_path.exists():
                    return
                    
                # STEP 9: TIMEOUT PROTECTION (Simulated)
                loop = asyncio.get_event_loop()
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, pd.read_csv, data_path),
                    timeout=5.0
                )
                
                df['date'] = pd.to_datetime(df['date'])
                mandi_data = {}
                mandi_meta = {}
                
                for m_id, m_df in df.groupby('mandi_id'):
                    m_df = m_df.sort_values('date').set_index('date')
                    m_df = m_df.resample('D').asfreq()
                    missing_mask = m_df['price'].isna()
                    m_df[['price', 'arrivals']] = m_df[['price', 'arrivals']].ffill(limit=2)
                    m_df['mandi_id'] = m_id
                    m_df['is_missing'] = missing_mask.astype(int)
                    mandi_meta[m_id] = {
                        "last_refreshed": datetime.now().isoformat(),
                        "version_id": f"v4_{commodity}_{m_id}"
                    }
                    mandi_data[m_id] = m_df.reset_index()

                self._cache[commodity] = mandi_data
                self._metadata[commodity] = mandi_meta
                
                # STEP 4: STAGGERED REFRESH (TTL ± 20%)
                stagger = random.uniform(0.8, 1.2)
                self._cache_expiry[commodity] = time.time() + (self.BASE_CACHE_TTL * stagger)
                self._failure_count = 0 # Reset on success
                self.metrics["external_fetches"] += 1
                
            except Exception as e:
                self._failure_count += 1
                self.metrics["failures"] += 1
                if self._failure_count >= self._circuit_threshold:
                    self._circuit_open_until = time.time() + 600 # 10 mins
                    print(f"Circuit OPEN for {commodity} due to {self._failure_count} failures.")
                raise e

    async def get_mandi_series(self, commodity: str, mandi_id: str, window: int = WINDOW_SIZE) -> Tuple[pd.DataFrame, bool, Dict]:
        self.metrics["total_requests"] += 1
        
        # Cache hit check
        is_cached = commodity in self._cache and time.time() < self._cache_expiry.get(commodity, 0)
        
        if not is_cached:
            try:
                await self._load_into_cache(commodity)
            except Exception:
                # Fallback to expired cache if external load fails
                if commodity not in self._cache:
                    raise
                print(f"Using expired cache for {commodity} as fallback.")

        if is_cached:
            self.metrics["cache_hits"] += 1
            
        commodity_cache = self._cache.get(commodity, {})
        if mandi_id not in commodity_cache:
            raise ValueError(f"Mandi {mandi_id} not found for {commodity}")
            
        df = commodity_cache[mandi_id]
        series = df.tail(window).copy()
        
        last_date = series['date'].max()
        days_diff = (datetime.now() - last_date).days
        is_stale = days_diff > 2
        
        if is_stale:
            self.metrics["stale_data_usage"] += 1
            
        return series, is_stale, self._metadata[commodity][mandi_id]

    async def prepare_inference_input(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        try:
            series, is_stale, meta = await self.get_mandi_series(commodity, mandi_id)
            
            return {
                "latest": series.iloc[-1:].copy(),
                "history": series.copy(),
                "is_stale": is_stale,
                "metadata": meta,
                "status": "success"
            }
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e),
                "is_stale": True
            }

    async def clear_cache(self, commodity: Optional[str] = None):
        """STEP 7: MANUAL REFRESH."""
        if commodity:
            self._cache.pop(commodity, None)
            self._cache_expiry.pop(commodity, None)
        else:
            self._cache.clear()
            self._cache_expiry.clear()

if __name__ == "__main__":
    # Test staggered refresh
    ds = MandiDataService.get_instance()
    asyncio.run(ds.warm_up(["tomato"]))
    print(f"Metrics: {ds.metrics}")
