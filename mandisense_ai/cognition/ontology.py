from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class MarketRegime(str, Enum):
    STABLE_EXPANSION = "STABLE_EXPANSION"
    TRANSITIONAL_STRESS = "TRANSITIONAL_STRESS"
    SUPPLY_COMPRESSION = "SUPPLY_COMPRESSION"
    ELEVATED_VOLATILITY = "ELEVATED_VOLATILITY"
    RECOVERY_STABILIZATION = "RECOVERY_STABILIZATION"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CognitionStatus(str, Enum):
    FULL_COGNITION = "FULL_COGNITION"
    PARTIAL_COGNITION = "PARTIAL_COGNITION"
    DEGRADED_COGNITION = "DEGRADED_COGNITION"
    STALE_COGNITION = "STALE_COGNITION"
    TELEMETRY_DEGRADED = "TELEMETRY_DEGRADED"
    ORCHESTRATION_UNSAFE = "ORCHESTRATION_UNSAFE"
    INFRASTRUCTURE_DEGRADED = "INFRASTRUCTURE_DEGRADED"
    COGNITION_FAILED = "COGNITION_FAILED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"

class IntelligenceFreshness(BaseModel):
    last_computed: datetime
    expiration_threshold_minutes: int = 240 # Default 4 hours
    integrity_score: float = 1.0 # 0.0 to 1.0

    @property
    def age_minutes(self) -> float:
        return (datetime.now() - self.last_computed).total_seconds() / 60

    @property
    def is_stale(self) -> bool:
        return self.age_minutes > self.expiration_threshold_minutes

class ConfidenceState(BaseModel):
    score: float
    stability: float # Historical consistency of the signal
    decay_rate: float = 0.01 # Loss of confidence per hour
    last_updated: datetime = Field(default_factory=datetime.now)

    def calculate_current_confidence(self) -> float:
        hours_passed = (datetime.now() - self.last_updated).total_seconds() / 3600
        decayed_score = self.score - (hours_passed * self.decay_rate)
        return max(0.0, min(1.0, decayed_score))

class VolatilityState(BaseModel):
    regime: str # e.g., "low", "high"
    score: float
    is_escalating: bool
    momentum: float # Rate of change in volatility

class DirectiveState(BaseModel):
    primary_directive: str
    action_code: str
    urgency: str
    reasoning: str
    confidence_at_synthesis: float

class AgentSignalState(BaseModel):
    agent_id: str
    signal: str
    confidence: float
    weight: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DeliberationState(BaseModel):
    agents: List[AgentSignalState]
    contradictions: List[str]
    dominant_agent_id: str
    chaos_score: float

class MarketState(BaseModel):
    """
    The Core Ontology Object for MandiSense.
    Represents the evolved truth of a specific market (Commodity + Mandi).
    """
    commodity: str
    mandi_id: str
    timestamp: datetime
    price_prediction: float
    confidence: ConfidenceState
    volatility: VolatilityState
    regime: MarketRegime
    risk_level: RiskLevel
    integrity_status: CognitionStatus = CognitionStatus.FULL_COGNITION
    directives: List[DirectiveState]
    forecast_arrivals: float
    trend: str # "upward", "downward", "stable"
    
    deliberation: DeliberationState
    
    freshness: IntelligenceFreshness
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(use_enum_values=True)
