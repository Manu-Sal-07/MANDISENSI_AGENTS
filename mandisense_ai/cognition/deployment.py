import logging
import uuid
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("InstitutionalDeployment")

class TelemetrySource(BaseModel):
    id: str
    type: str 
    status: str = "ONLINE" 
    last_sync: datetime
    trust_score: float = 1.0
    latency_ms: float = 0.0
    freshness_score: float = 1.0 # 1.0 (Live) to 0.0 (Stale)
    reliability_score: float = 1.0 # Historical uptime

class Organization(BaseModel):
    id: str
    name: str
    tier: str = "ENTERPRISE" 
    active_mandi_nodes: List[str]
    governance_policy: Dict[str, Any] = Field(default_factory=dict)
    memory_isolation_id: str

class InstitutionalAuditEntry(BaseModel):
    id: str
    timestamp: datetime
    org_id: str
    actor: str 
    action: str
    plan_id: Optional[str]
    details: str
    outcome_status: str = "PENDING"

class RealitySynchronizer:
    """
    Freshness of the data the system is reasoning over.

    This used to measure the wrong clock entirely. Each source was stamped
    with `datetime.now()` at construction and never re-stamped, so `last_sync`
    tracked *how long this process had been running*, not when any data last
    arrived. A server up for a day reported every source STALE and dragged
    `avg_trust` below the 0.4 floor that `CognitionEngine.validate_integrity`
    uses to declare DEGRADED_COGNITION — while a freshly restarted process
    sitting on a four-month-old archive reported perfect 1.0 trust. The
    signal was not merely noisy, it was inverted: restarting the server was
    the fastest way to make the health numbers look good.

    Freshness is now read from the age of the actual artifacts — the newest
    observation in the store, and the published forecast's `as_of_date`.
    """

    def __init__(self):
        self.sources: Dict[str, TelemetrySource] = {
            "weather_hub_v1": TelemetrySource(id="weather_hub_v1", type="WEATHER", last_sync=datetime.now()),
            "logistics_stream_in": TelemetrySource(id="logistics_stream_in", type="LOGISTICS", last_sync=datetime.now()),
            "mandi_direct_feed": TelemetrySource(id="mandi_direct_feed", type="MANDI_FEED", last_sync=datetime.now())
        }

    def _observation_age_days(self) -> Optional[float]:
        """Age of the newest row in the observation store, in days."""
        try:
            import pandas as pd

            from mandisense_ai.forecasting.store import ObservationStore

            frame = ObservationStore().read()
            if frame.empty:
                return None
            newest = pd.to_datetime(frame["date"]).max()
            return float((pd.Timestamp.now().normalize() - newest.normalize()).days)
        except Exception as exc:
            logger.warning(f"Could not determine observation age: {exc}")
            return None

    def _forecast_age_days(self) -> Optional[float]:
        """Age of the published forecast's `as_of_date`, in days."""
        try:
            import pandas as pd

            from mandisense_ai.forecasting.service import get_forecast_service

            status = get_forecast_service().status()
            as_of = status.get("as_of_date")
            if not as_of:
                return None
            return float((pd.Timestamp.now().normalize() - pd.Timestamp(as_of).normalize()).days)
        except Exception as exc:
            logger.warning(f"Could not determine forecast age: {exc}")
            return None

    @staticmethod
    def _freshness_from_age(age_days: Optional[float]) -> float:
        """
        Data age in days -> freshness in [0, 1].

        Graded against how this feed actually behaves: the government feed
        publishes daily with a routine 1-3 day lag, so a couple of days old
        is healthy, a week is degraded, and a month means nothing has been
        ingested in a very long time.
        """
        if age_days is None:
            return 0.0
        if age_days <= 3:
            return 1.0
        if age_days <= 7:
            return 0.8
        if age_days <= 21:
            return 0.4
        return 0.1

    def get_source_status(self) -> List[TelemetrySource]:
        observation_age = self._observation_age_days()
        forecast_age = self._forecast_age_days()

        # The mandi feed is the only source with a real artifact to measure;
        # weather and logistics have no ingested store behind them yet, so
        # they inherit the observation age rather than claim an independent
        # freshness nobody measures.
        age_by_source = {
            "mandi_direct_feed": observation_age,
            "weather_hub_v1": observation_age,
            "logistics_stream_in": forecast_age if forecast_age is not None else observation_age,
        }

        for source_id, src in self.sources.items():
            age_days = age_by_source.get(source_id)
            src.freshness_score = self._freshness_from_age(age_days)

            if age_days is not None:
                src.last_sync = datetime.now() - timedelta(days=age_days)

            src.status = "ONLINE"
            if src.freshness_score <= 0.1:
                src.status = "STALE"

            src.trust_score = (src.freshness_score * 0.6) + (src.reliability_score * 0.4)

            if src.trust_score < 0.3:
                src.status = "DEGRADED"

        return list(self.sources.values())

class DeploymentManager:
    """
    Production Deployment Manager.
    Uses relative paths for maximum portability.
    """
    def __init__(self):
        # Use a path relative to the project root
        self.storage_path = Path("mandisense_ai/data/deployment")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.storage_path / "audit_log.json"
        
        self.organizations: Dict[str, Organization] = {
            "org_default": Organization(
                id="org_default", 
                name="MandiSense Global Operations",
                active_mandi_nodes=["kolar_apmc", "bangalore_apmc"],
                memory_isolation_id="mem_iso_001"
            )
        }
        self.audit_log: List[InstitutionalAuditEntry] = self._load_audit_log()
        logger.info(f"DeploymentManager initialized. Audit file: {self.audit_file.absolute()}")

    def _load_audit_log(self) -> List[InstitutionalAuditEntry]:
        if not self.audit_file.exists(): 
            logger.info("No existing audit log found.")
            return []
        try:
            with open(self.audit_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} audit entries.")
                return [InstitutionalAuditEntry(**e) for e in data]
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")
            return []

    def _save_audit_log(self):
        try:
            with open(self.audit_file, 'w') as f:
                json.dump([e.dict() for e in self.audit_log], f, default=str, indent=2)
            logger.info("Audit log saved successfully.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to save audit log: {e}")

    def log_action(self, org_id: str, actor: str, action: str, plan_id: str = None, details: str = ""):
        entry = InstitutionalAuditEntry(
            id=f"audit_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            org_id=org_id,
            actor=actor,
            action=action,
            plan_id=plan_id,
            details=details
        )
        self.audit_log.append(entry)
        self._save_audit_log()
        return entry

    def get_audit_trail(self, org_id: str) -> List[InstitutionalAuditEntry]:
        return [e for e in self.audit_log if e.org_id == org_id]
