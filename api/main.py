import time
import asyncio
import logging
import json
import uuid
from contextvars import ContextVar
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import sys
import os
from collections import defaultdict
from pathlib import Path

# ── Context Variables ──────────────────────────────────────────────────
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="unknown")

# ── Path Configuration ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "mandisense_ai"))

from mandisense_ai.db.connection import ping_db_async
from mandisense_ai.lib.cache import ping_redis
from run_agents import run_pipeline

# ── Logging Configuration ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("mandisense_api")

def log_event(event_name: str, **kwargs):
    log_data = {
        "event": event_name,
        "request_id": REQUEST_ID.get(),
        "timestamp": time.time()
    }
    log_data.update(kwargs)
    logger.info(json.dumps(log_data))

# ── Rate Limiter (Simple In-Memory) ───────────────────────────────────
class RateLimiter:
    def __init__(self, limit: int = 10, window: int = 1):
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)

    async def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > now - self.window]
        if len(self.requests[client_ip]) >= self.limit:
            return False
        self.requests[client_ip].append(now)
        return True

limiter = RateLimiter(limit=10, window=1)

# ── FastAPI App Initialization ────────────────────────────────────────
app = FastAPI(
    title="MandiSense AI API",
    description="High-reliability FastAPI service for multi-agent price forecasting.",
    version="1.2.0"
)

# ── Request/Response Schemas ──────────────────────────────────────────
class PredictRequest(BaseModel):
    commodity: str = Field(..., example="tomato")
    mandi: str = Field(..., example="kolar")

class PredictResponse(BaseModel):
    request_id: str
    prediction: float
    confidence: float
    status: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_breakdown: Dict[str, Any] = Field(default_factory=dict)

# ── Middleware ────────────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    REQUEST_ID.set(request_id)
    
    client_ip = request.client.host if request.client else "unknown"
    if not await limiter.is_allowed(client_ip):
        log_event("rate_limit_exceeded", client_ip=client_ip)
        return Response(
            content=json.dumps({"error": "Rate limit exceeded (10 req/s)"}),
            status_code=429,
            media_type="application/json"
        )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ── Startup Validation ────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    REQUEST_ID.set("system-init")
    log_event("startup_initiated")
    
    db_ok = await ping_db_async()
    redis_ok = ping_redis()
    
    if not db_ok:
        logger.warning("ALARM: Database is unreachable. Proceeding in degraded mode.")
    if not redis_ok:
        logger.warning("ALARM: Redis is unreachable. Proceeding without caching.")
    
    try:
        log_event("model_warmup_started")
        models_root = Path(os.path.join(BASE_DIR, "mandisense_ai", "models"))
        valid_model = None
        if models_root.exists():
            for c_dir in models_root.iterdir():
                if c_dir.is_dir() and not c_dir.name.startswith("."):
                    for m_dir in c_dir.iterdir():
                        if m_dir.is_dir() and (m_dir / "seasonality" / "bundle.pkl").exists():
                            valid_model = (c_dir.name, m_dir.name)
                            break
                    if valid_model: break
        
        warmup_commodity, warmup_mandi = valid_model or ("tomato", "kolar")
        log_event("model_warmup_executing", commodity=warmup_commodity, mandi=warmup_mandi)
        _ = run_pipeline(warmup_commodity, warmup_mandi) 
        log_event("model_warmup_completed")
    except Exception as e:
        logger.error(f"FATAL: Core model warmup failed: {e}")
        sys.exit(1)

    logger.info("System initialized successfully")
    log_event("startup_completed")

# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/v1/health")
async def health_check():
    """Detailed health check for all subsystems."""
    db_ok = await ping_db_async()
    redis_ok = ping_redis()
    
    status = "ok"
    if not db_ok or not redis_ok:
        status = "degraded"
        
    return {
        "status": status,
        "services": {
            "api": "alive",
            "redis": "ok" if redis_ok else "degraded",
            "db": "ok" if db_ok else "degraded"
        }
    }

@app.post("/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Prediction with tracing, timeout, and failure transparency."""
    start_time = time.time()
    req_id = REQUEST_ID.get()
    
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(run_pipeline, request.commodity, request.mandi),
            timeout=10.0
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        if result.get("status") == "error":
            log_event("prediction_error", 
                      commodity=request.commodity, mandi=request.mandi, 
                      error=result.get("message"))
            return PredictResponse(
                request_id=req_id,
                prediction=0.0,
                confidence=0.1,
                status="fallback",
                reason=result.get("message", "Pipeline error")
            )

        log_event("prediction_request", 
                  commodity=request.commodity, mandi=request.mandi, 
                  latency_ms=duration_ms)
        
        meta_res = result.get("results", {}).get("meta_ensemble", {})
        return PredictResponse(
            request_id=req_id,
            prediction=float(meta_res.get("prediction", 0.0)),
            confidence=float(meta_res.get("confidence", 0.0)),
            status="success",
            metadata=result.get("results", {}),
            model_breakdown=result.get("results", {}).get("seasonality", {}).get("model_breakdown", {})
        )
        
    except asyncio.TimeoutError:
        duration_ms = (time.time() - start_time) * 1000
        log_event("prediction_timeout", 
                  commodity=request.commodity, mandi=request.mandi, 
                  duration_ms=duration_ms)
        return PredictResponse(
            request_id=req_id,
            prediction=0.0,
            confidence=0.1,
            status="fallback",
            reason="timeout"
        )
    except Exception as e:
        log_event("prediction_fatal", error=str(e))
        return PredictResponse(
            request_id=req_id,
            prediction=0.0,
            confidence=0.1,
            status="fallback",
            reason=f"exception: {str(e)}"
        )

# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

