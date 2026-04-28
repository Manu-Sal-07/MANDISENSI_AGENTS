"""
API Request & Response Schemas.

Pydantic models for input validation and output serialization.
All API boundaries use these schemas — no raw dicts cross the wire.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════════

class PredictRequest(BaseModel):
    """POST /v1/predict"""
    commodity: str = Field(..., min_length=1, max_length=50, examples=["tomato"])
    mandi: str = Field(..., min_length=1, max_length=100, examples=["kolar"])
    use_learned: bool = Field(True, description="Include Phase-2.5 learned correction")

    @field_validator("commodity", "mandi")
    @classmethod
    def normalize_lowercase(cls, v: str) -> str:
        return v.strip().lower()


class HistoryQuery(BaseModel):
    """GET /v1/prediction/history query params"""
    commodity: str = Field(..., min_length=1)
    mandi: str = Field(..., min_length=1)
    days: int = Field(30, ge=1, le=365)


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionDetail(BaseModel):
    price_change_7d_pct: float
    confidence: float
    direction: Literal["bullish", "bearish", "neutral"]


class Attribution(BaseModel):
    seasonality_pct: float
    arrival_pct: float
    external_pct: float


class RiskFlags(BaseModel):
    conflict_detected: bool = False
    strong_conflict: bool = False
    low_confidence: bool = False
    high_volatility_risk: bool = False
    external_reliance_heavy: bool = False


class Phase2Info(BaseModel):
    mode: str = "phase1_only"
    alpha: float = 1.0
    regime_detected: str = "normal"
    learned_residual: float = 0.0
    soft_regime_weights: Optional[Dict[str, float]] = None


class ResponseMetadata(BaseModel):
    model_version: str = "v2.5.0"
    generated_at: str
    latency_ms: float
    cached: bool = False


class PriceRange(BaseModel):
    min: float
    max: float


class FarmerGuidance(BaseModel):
    decision: Literal["SELL", "WAIT"]
    price_range: PriceRange
    confidence_label: Literal["High", "Medium", "Low"]
    risk_label: Literal["High", "Medium", "Low"]
    explanation: List[str]


class PredictResponse(BaseModel):
    request_id: str
    commodity: str
    mandi: str
    prediction: PredictionDetail
    attribution: Attribution
    risk_flags: RiskFlags
    phase2_info: Phase2Info
    farmer_guidance: FarmerGuidance
    metadata: ResponseMetadata


# ── History ───────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    date: str
    predicted_change: float
    actual_change: Optional[float] = None
    error: Optional[float] = None
    confidence: float


class HistorySummary(BaseModel):
    mean_absolute_error: Optional[float] = None
    directional_accuracy: Optional[float] = None
    total_predictions: int = 0


class HistoryResponse(BaseModel):
    commodity: str
    mandi: str
    predictions: List[HistoryEntry]
    summary: HistorySummary


# ── Model Status ──────────────────────────────────────────────────────

class RegimeModelStatus(BaseModel):
    r2_val: float
    mae_val: float = 0.0
    n_train: int
    last_trained: str


class ModelStatusResponse(BaseModel):
    phase1: Dict[str, str]
    phase2: Dict[str, Any]


# ── Health ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    uptime_seconds: float
    components: Dict[str, str]
    version: str = "v2.5.0"


# ═══════════════════════════════════════════════════════════════════════════════
# Action System (Alerts & Watchlist)
# ═══════════════════════════════════════════════════════════════════════════════

class WatchlistAddRequest(BaseModel):
    commodity: str = Field(..., min_length=1)
    mandi: str = Field(..., min_length=1)

class WatchlistItem(BaseModel):
    id: str
    commodity: str
    mandi: str
    added_at: str

class AlertCreateRequest(BaseModel):
    commodity: str
    mandi: str
    alert_type: Literal["PRICE_DROP", "PRICE_RISE", "TREND_CHANGE"]
    threshold_price: Optional[float] = None

class AlertItem(BaseModel):
    id: str
    commodity: str
    mandi: str
    alert_type: str
    threshold_price: Optional[float] = None
    status: Literal["ACTIVE", "TRIGGERED", "DISMISSED"]
    created_at: str
