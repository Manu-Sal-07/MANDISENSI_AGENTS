"""
Runtime access to the published forecast store.

Contract with the API layer:

* **Read-only.** No model is loaded, no features are built, no pandas is
  imported on this path. The nightly job did that work already.
* **Never raises into a request.** A missing, corrupt or incompatible store
  degrades to "unavailable" rather than a 500. Forecasting is a feature of the
  product, not a dependency of it.
* **Freshness is reported, never assumed.** Every answer carries how old the
  underlying run and observation are. The failure mode this replaces is the
  old engine, which served a number computed from a CSV frozen 137 days
  earlier with no indication anything was wrong.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from mandisense_ai.forecasting.config import DEFAULT_CONFIG
from mandisense_ai.forecasting.store import ForecastStore
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

FRESHNESS_FRESH = "FRESH"
FRESHNESS_STALE = "STALE"
FRESHNESS_UNKNOWN = "UNKNOWN"


class ForecastService:
    """Process-wide cached reader for the forecast store."""

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self._store_path = Path(store_path) if store_path else None
        self._store: Optional[ForecastStore] = None
        self._error: Optional[str] = None
        self._loaded = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------ lifecycle

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                self._store = ForecastStore.load(self._store_path)
                self._error = None
                logger.info(
                    "Forecast store loaded (%d rows, as_of %s)",
                    len(self._store.forecasts), self._store.as_of_date,
                )
            except FileNotFoundError:
                self._store, self._error = None, "forecast_not_generated"
                logger.warning("Forecast store not found — run the nightly job")
            except Exception as exc:
                self._store, self._error = None, f"forecast_store_unreadable: {exc}"
                logger.error("Forecast store unreadable: %s", exc)
            finally:
                self._loaded = True

    def reload(self) -> bool:
        """Pick up a freshly published store without a process restart."""
        with self._lock:
            self._loaded = False
            self._store = None
            self._error = None
        self._ensure_loaded()
        return self._store is not None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._store is not None

    # --------------------------------------------------------------- reads

    def freshness(self) -> str:
        self._ensure_loaded()
        if self._store is None:
            return FRESHNESS_UNKNOWN
        age = self._store.age_hours()
        if age is None:
            return FRESHNESS_UNKNOWN
        return FRESHNESS_FRESH if age <= DEFAULT_CONFIG.fresh_max_age_hours else FRESHNESS_STALE

    def status(self) -> Dict[str, Any]:
        """Always safe to call; used by health dashboards."""
        self._ensure_loaded()
        if self._store is None:
            return {"available": False, "reason": self._error or "unknown"}
        payload = self._store.summary()
        payload["available"] = True
        payload["freshness"] = self.freshness()
        return payload

    def get_curve(self, commodity: str, mandi_id: str) -> List[Dict[str, Any]]:
        """Every published horizon for a series, including refusal rows."""
        self._ensure_loaded()
        if self._store is None:
            return []
        try:
            return self._store.get(
                str(commodity).strip().lower(), str(mandi_id).strip().lower()
            )
        except Exception as exc:
            logger.error("Forecast lookup failed for %s/%s: %s", commodity, mandi_id, exc)
            return []

    def get_horizon(
        self, commodity: str, mandi_id: str, horizon: int
    ) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()
        if self._store is None:
            return None
        try:
            return self._store.get_horizon(
                str(commodity).strip().lower(), str(mandi_id).strip().lower(), int(horizon)
            )
        except Exception as exc:
            logger.error("Forecast horizon lookup failed: %s", exc)
            return None

    def nearest_horizon(
        self, commodity: str, mandi_id: str, requested: int
    ) -> Optional[Dict[str, Any]]:
        """
        Closest published horizon to the one asked for.

        A trader asking for four days should get the three- or five-day
        forecast with the substitution stated, rather than a 404 — but the
        response records what was actually served so the gap is never hidden.
        """
        curve = [row for row in self.get_curve(commodity, mandi_id) if row.get("horizon_days")]
        if not curve:
            return None
        return min(curve, key=lambda row: abs(int(row["horizon_days"]) - int(requested)))

    def available_series(self) -> List[Dict[str, str]]:
        self._ensure_loaded()
        return self._store.available_series() if self._store else []

    def readiness(self) -> List[Dict[str, Any]]:
        """Per-series progress toward eligibility, as of the last nightly run."""
        self._ensure_loaded()
        if self._store is None:
            return []
        return list(self._store.diagnostics.get("readiness", []))

    def calibration(self) -> Dict[str, Any]:
        """Measured out-of-sample coverage of the published intervals."""
        self._ensure_loaded()
        if self._store is None:
            return {}
        return dict(self._store.diagnostics.get("interval_calibration", {}))

    def promoted_horizons(self) -> List[int]:
        self._ensure_loaded()
        if self._store is None:
            return []
        return list(self._store.diagnostics.get("promoted_horizons", []))


_SERVICE: Optional[ForecastService] = None
_SERVICE_LOCK = threading.Lock()


def get_forecast_service() -> ForecastService:
    global _SERVICE
    if _SERVICE is None:
        with _SERVICE_LOCK:
            if _SERVICE is None:
                _SERVICE = ForecastService()
    return _SERVICE
