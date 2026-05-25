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
    def __init__(self):
        self.sources: Dict[str, TelemetrySource] = {
            "weather_hub_v1": TelemetrySource(id="weather_hub_v1", type="WEATHER", last_sync=datetime.now()),
            "logistics_stream_in": TelemetrySource(id="logistics_stream_in", type="LOGISTICS", last_sync=datetime.now()),
            "mandi_direct_feed": TelemetrySource(id="mandi_direct_feed", type="MANDI_FEED", last_sync=datetime.now())
        }

    def get_source_status(self) -> List[TelemetrySource]:
        for src in self.sources.values():
            delta = (datetime.now() - src.last_sync).total_seconds()
            
            # Freshness Calculation
            if delta < 300: # 5 mins
                src.freshness_score = 1.0
            elif delta < 3600: # 1 hour
                src.freshness_score = 0.8
            elif delta < 86400: # 1 day
                src.freshness_score = 0.4
            else:
                src.freshness_score = 0.1
                src.status = "STALE"

            # Aggregate Trust Score
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
