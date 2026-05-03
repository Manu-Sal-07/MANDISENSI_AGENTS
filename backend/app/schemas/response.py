from pydantic import BaseModel
from typing import Optional, Dict, Any

class PredictResponse(BaseModel):
    commodity: str
    mandi_id: str
    target_date: Optional[str] = None
    predicted_price: Optional[float] = None
    predicted_arrivals: Optional[float] = None
    confidence: Optional[float] = None
    trend: Optional[str] = None
    volatility: Optional[str] = None
    explanation: Optional[str] = None
    status: Optional[str] = "success"

class DecisionResponse(BaseModel):
    commodity: str
    mandi_id: str
    decision: str
    confidence: float
    risk_level: str
    signal_strength: Optional[str] = None
    price_change_pct: float
    reasoning: str
    raw_inference: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    decision: str
    summary: str
    reasoning: str
    market_insight: str
    metadata: Optional[Dict[str, Any]] = None
    raw_inference: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    model_version: Optional[str] = None
    cache_status: Optional[str] = None
