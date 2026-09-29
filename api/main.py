import time
import asyncio
import logging
import json
import uuid
from contextvars import ContextVar
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import sys
import os
from collections import defaultdict
from pathlib import Path
import warnings
from datetime import datetime

# Suppress noisy library warnings
warnings.filterwarnings("ignore", category=UserWarning)
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

# ── Context Variables ──────────────────────────────────────────────────
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="unknown")

# ── Path Configuration ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "mandisense_ai"))

from mandisense_ai.db.connection import ping_db_async, execute_async, execute_write_async
from mandisense_ai.lib.cache import ping_redis
from run_agents import run_pipeline
from mandisense_ai.core.decision_engine import generate_decision
from mandisense_ai.services.prediction_cache import (
    get_prediction_cache_key, 
    get_cached_prediction, 
    set_cached_prediction
)

# Discovery/Legacy Imports
from backend.app.routes import discovery, query, decision, predict as legacy_predict
from backend.app.services.model_loader import init_engines
from api import visualizer, cognition_router, cognition_streaming, cognition_seed, market_data_router, spillover_router, forecast_router, intelligence_router, farmer_router, trader_router
from mandisense_ai.utils.event_bus import event_bus
from mandisense_ai.cognition.state_store import MarketMemoryStore
from fastapi.responses import FileResponse




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

limiter = RateLimiter(limit=int(os.getenv("RATE_LIMIT_PER_SECOND", "60")), window=1)

# ── Infrastructure Circuit Breaker (Phase 5B) ──────────────────────────
class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 3, recovery_time: int = 60):
        self.name = name
        self.threshold = threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN

    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF_OPEN"
                return False
            return True
        return False

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "OPEN"
            logger.error(f"CIRCUIT BREAKER [{self.name}] OPENED. Infrastructure isolation active.")

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

db_breaker = CircuitBreaker("POSTGRES", threshold=3, recovery_time=60)
redis_breaker = CircuitBreaker("REDIS", threshold=3, recovery_time=30)

# ── FastAPI App Initialization ────────────────────────────────────────
app = FastAPI(
    title="MandiSense AI API",
    description="High-reliability FastAPI service for multi-agent price forecasting.",
    version="1.2.0"
)

# ── CORS Configuration ───────────────────────────────────────────────
local_dev_ports = ["3000", "3001", "3002", "5173"]
local_dev_origins = []
for port in local_dev_ports:
    local_dev_origins.extend([
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
    ])

explicit_origins = [
    "https://mandisensi-agents.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

cors_allowed_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_allowed_env:
    env_origins = [origin.strip() for origin in cors_allowed_env.split(",") if origin.strip()]
else:
    env_origins = []

allow_origins = list(set(explicit_origins + local_dev_origins + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# ── Primary Discovery Routes (Moved Up for Visibility) ────────────────
@app.get("/")
async def root_redirect():
    return {
        "message": "MandiSense AI Unified Backend is Online",
        "endpoints": {
            "inference": "/v1/predict",
            "discovery_feed": "/discovery/feed",
            "spillover": "/v1/spillover/impacts/{commodity}",
            "forecast": "/v1/forecast/{commodity}/{mandi_id}?horizon=5",
            "health": "/v1/health"
        }
    }

app.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery"])
app.include_router(query.router, prefix="/v1/query", tags=["Advisory"])
app.include_router(decision.router, prefix="/v1/decision", tags=["Intelligence"])
app.include_router(cognition_router.router, prefix="/v1/cognition", tags=["Cognition Infrastructure"])
app.include_router(discovery.router, prefix="/discovery", tags=["Legacy Compatibility"]) # Backward compat
app.include_router(discovery.router, prefix="/api", tags=["Frontend Compatibility"])
app.include_router(legacy_predict.router, prefix="/api/predict", tags=["Legacy Compatibility"])
app.include_router(visualizer.router, tags=["Visualization"])
app.include_router(cognition_streaming.router, prefix="/v1", tags=["Cognition Streaming"])
app.include_router(cognition_seed.router, tags=["Cognition Seeding"])
app.include_router(spillover_router.router, prefix="/v1/spillover", tags=["Cross-Commodity Spillover"])
app.include_router(market_data_router.router, prefix="/v1/market-data", tags=["Market Data"])
app.include_router(forecast_router.router, prefix="/v1/forecast", tags=["Scheduled Forecasting"])
app.include_router(intelligence_router.router, prefix="/v1/intelligence", tags=["LLM Decision Intelligence"])
app.include_router(farmer_router.router, tags=["Farmer Features"])  # prefix is already /v1/farmer on the router
app.include_router(trader_router.router, tags=["Trader Features"])  # prefix is already /v1/trader on the router

@app.get("/visualizer")
async def get_visualizer():
    target_path = os.path.join(BASE_DIR, "frontend", "visualizer.html")
    if not os.path.exists(target_path):
        logger.error(f"Visualizer file not found at: {target_path}")
        return {"error": "Visualizer frontend file missing", "path": target_path}
    return FileResponse(target_path)

from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: Exception):
    if hasattr(exc, "detail") and exc.detail != "Not Found":
        return JSONResponse(
            status_code=404,
            content={"detail": exc.detail}
        )
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "message": f"Endpoint {request.url.path} not found on MandiSense AI Unified Server",
            "request_id": REQUEST_ID.get(),
            "available_endpoints": [
                "/",
                "/v1/health",
                "/v1/predict",
                "/discovery/feed",
                "/visualizer",
                "/v1/trace-run"
            ]
        }
    )

# ── Production Readiness Endpoints (Phase 4/5B Unified) ────────────────
# (Note: Unified health_check moved to Endpoints section below for Phase 5B logic)

# ── WebSocket Trace Endpoint ──────────────────────────────────────────
@app.websocket("/ws/trace")
async def websocket_trace(websocket: WebSocket):
    await event_bus.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for any client messages if needed
            data = await websocket.receive_text()
            # We don't necessarily need to handle client messages here, 
            # but we keep the loop to detect disconnects.
    except WebSocketDisconnect:
        event_bus.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket trace error: {e}")
        event_bus.disconnect(websocket)



# ── Request/Response Schemas ──────────────────────────────────────────
class PredictRequest(BaseModel):
    commodity: str = Field(..., json_schema_extra={"example": "tomato"})
    mandi: str = Field(..., json_schema_extra={"example": "kolar"})

class PredictResponse(BaseModel):
    request_id: str
    prediction: float
    confidence: float
    status: str
    reason: Optional[str] = None
    # Decision Intelligence Extension
    decision: str
    risk_level: str
    action_strength: str
    direction: str
    confidence_label: str
    summary: str
    reasoning: str
    signals: Dict[str, Any]
    # Caching
    cache: Optional[Dict[str, Any]] = None
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


    model_breakdown: Dict[str, Any] = Field(default_factory=dict)


VALID_ACTION_CODES = ("SELL", "HOLD", "WAIT")


def action_code_from_state(state) -> str:
    """
    The action code a client can switch on, from a cognition snapshot.

    Extracted from the `/v1/predict` handler so the rule is testable without
    standing up the whole app. `decision` used to be filled with
    `primary_directive`, which holds a narrative sentence rather than a code
    — the farmer UI matches the three known codes and silently renders
    anything else as WAIT, so the endpoint appeared to counsel waiting
    regardless of the market. The real action is on `metadata.decision`;
    `action_code` is deliberately not consulted because every snapshot
    hardcodes it to "EXECUTE".
    """
    action = (getattr(state, "metadata", None) or {}).get("decision")
    return action if action in VALID_ACTION_CODES else "WAIT"


def get_canonical_mandi(mandi: str) -> str:
    mandi = mandi.lower().strip()

    if mandi == "kolar":
        return "kolar_apmc"

    if mandi in ["bangalore", "yeshwanthpur"]:
        return "bangalore_apmc"

    return mandi


# ── Middleware ────────────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    REQUEST_ID.set(request_id)

    dashboard_read = (
        request.method == "GET"
        and (
            request.url.path == "/v1/health"
            or request.url.path.startswith("/v1/cognition/")
            or request.url.path == "/v1/deployment/audit"
        )
    )
    
    client_ip = request.client.host if request.client else "unknown"
    if not dashboard_read and not await limiter.is_allowed(client_ip):
        log_event("rate_limit_exceeded", client_ip=client_ip)
        return Response(
            content=json.dumps({"error": f"Rate limit exceeded ({limiter.limit} req/s)"}),
            status_code=429,
            media_type="application/json"
        )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ── Startup Validation ────────────────────────────────────────────────
async def verify_and_initialize_db():
    logger.info("[INIT] Performing database startup safety checks...")
    try:
        # Check if database is reachable
        db_ok = await ping_db_async()
        if not db_ok:
            raise RuntimeError("Database connection test failed (ping unreachable).")
        
        # Check if tables exist in public schema
        required_tables = {"prediction_log", "market_prices", "arrival_volumes", "model_registry", "api_request_log"}
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        rows = await execute_async(query)
        existing_tables = {row["table_name"] for row in rows} if rows else set()
        
        missing_tables = required_tables - existing_tables
        if missing_tables:
            logger.info(f"[INIT] Missing tables detected: {missing_tables}. Triggering schema bootstrapping...")
            schema_path = os.path.join(BASE_DIR, "mandisense_ai", "db", "schema.sql")
            if not os.path.exists(schema_path):
                raise FileNotFoundError(f"Schema file missing at: {schema_path}")
            
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
                
            await execute_write_async(schema_sql)
            
            # Re-verify table existence
            rows = await execute_async(query)
            existing_tables = {row["table_name"] for row in rows} if rows else set()
            still_missing = required_tables - existing_tables
            if still_missing:
                raise RuntimeError(f"Auto-initialization completed but tables are still missing: {still_missing}")
            logger.info("[INIT] Database schema bootstrapped and verified successfully.")
        else:
            logger.info("[INIT] Database verification succeeded. All required tables are present.")
    except Exception as e:
        logger.critical(f"[INIT] CRITICAL DATABASE STARTUP CHECK FAILED: {e}", exc_info=True)
        env = os.getenv("APP__ENVIRONMENT", "development").lower()
        if env == "production":
            logger.critical("[INIT] Production environment active. Terminating process immediately to fail-fast.")
            import sys
            sys.exit(1)
        else:
            logger.warning("[INIT] Development environment. Continuing server initialization without database verification.")

@app.on_event("startup")
async def startup_event():
    REQUEST_ID.set("system-init")
    log_event("startup_initiated")
    
    # Block startup until database verification and auto-initialization completes
    await verify_and_initialize_db()
    
    # --- Background Activation ---
    # We launch the heavy sub-systems in the background to avoid blocking the event loop.
    # This ensures the server is "LIVE" and can report status immediately.
    asyncio.create_task(background_activation())
    
    logger.info("[INIT] MANDISENSE API LAYER IS LIVE. COGNITION ACTIVATING IN BACKGROUND.")
    log_event("startup_completed")

async def background_activation():
    """Heavy institutional lifting performed outside the main request loop."""
    app.state.status = "BOOTING"
    app.state.activation_complete = False
    
    # --- 1. Infrastructure (DB/Redis) ---
    logger.info("[ACTIVATE] Validating Infrastructure Connection...")
    try:
        db_ok = await asyncio.wait_for(ping_db_async(), timeout=5.0)
        redis_ok = await asyncio.to_thread(ping_redis)
        logger.info(f"[ACTIVATE] DB: {'ONLINE' if db_ok else 'OFFLINE'}, Redis: {'ONLINE' if redis_ok else 'OFFLINE'}")
    except Exception as e:
        logger.warning(f"[ACTIVATE] Infrastructure validation failed: {e}")

    # --- 2. Institutional Cognition Engine (Phase 5B) ---
    logger.info("[ACTIVATE] Booting Institutional Cognition Engine...")
    try:
        from mandisense_ai.cognition.engine import CognitionEngine
        # Engine constructor is heavy (loads models), run in thread
        engine = await asyncio.to_thread(CognitionEngine)
        app.state.cognition_engine = engine
        logger.info("[ACTIVATE] Cognition Engine: ONLINE")
    except Exception as e:
        logger.error(f"[ACTIVATE] CRITICAL: Cognition Engine failed: {e}", exc_info=True)
        app.state.cognition_engine = None

    # --- 3. Legacy Discovery Layer ---
    logger.info("[ACTIVATE] Warming up Legacy Discovery Engines...")
    try:
        await asyncio.wait_for(init_engines(version="v3"), timeout=15.0)
        logger.info("[ACTIVATE] Legacy Engines: READY")
    except Exception as e:
        logger.error(f"[ACTIVATE] Legacy engine warmup FAILED: {e}")

    app.state.status = "OPERATIONAL"
    logger.info("[ACTIVATE] MANDISENSE COGNITION FULLY SYNCHRONIZED")
    
    # --- 4. Auto-Seed Cognition (populate snapshots if empty) ---
    logger.info("[ACTIVATE] Auto-seeding cognition intelligence...")
    try:
        from mandisense_ai.cognition.state_store import MarketMemoryStore
        store = MarketMemoryStore()
        available = store.list_available_intelligence()
        total = sum(len(v) for v in available.values())
        if total == 0:
            logger.info("[ACTIVATE] No existing snapshots found. Running full cognition seed...")
            from mandisense_ai.cognition.engine import CognitionEngine
            from mandisense_ai.cognition.registry import CognitionRegistry
            engine = CognitionEngine()
            commodities = CognitionRegistry.get_canonical_commodities()
            mandis = CognitionRegistry.get_canonical_mandis()
            seed_tasks = [engine.generate_cognition(c, m) for c in commodities for m in mandis]
            await asyncio.gather(*seed_tasks, return_exceptions=True)
            logger.info("[ACTIVATE] Cognition seed complete.")
        else:
            logger.info(f"[ACTIVATE] Found {total} existing cognition snapshots. Refreshing stale data...")
            asyncio.create_task(app.state.cognition_engine.run_full_refresh() if app.state.cognition_engine else asyncio.sleep(0))
    except Exception as e:
        logger.error(f"[ACTIVATE] Auto-seed failed: {e}", exc_info=True)

    # --- 5. Forecast Scheduler (Phase 2 nightly cadence) ---
    # `run_nightly` previously had no caller at all outside a manual CLI
    # invocation — measured against its own run log, the published forecast
    # store sat months stale. Starting the loop here means the same process
    # already serving this API is what keeps it current, rather than that
    # depending on separate cron/Task Scheduler infrastructure being set up.
    # Fire-and-forget: a scheduler that fails to start must not block the API
    # from becoming READY, and a failure inside one cycle must not stop the
    # next one (see `forecast_scheduler_loop`'s own exception handling).
    try:
        from mandisense_ai.forecasting.scheduler import forecast_scheduler_loop
        app.state.forecast_scheduler_task = asyncio.create_task(forecast_scheduler_loop())
        logger.info("[ACTIVATE] Forecast Scheduler: STARTED")
    except Exception as e:
        logger.error(f"[ACTIVATE] Forecast Scheduler failed to start: {e}", exc_info=True)

    # Health reads this to distinguish a subsystem that is still loading from
    # one that tried and failed. The cognition engine takes ~30s to load its
    # models; without this flag every probe in that window reports a hard
    # outage, which is indistinguishable from a real crash.
    app.state.status = "READY"
    app.state.activation_complete = True

    print("Database Connected", flush=True)
    print("Redis Connected", flush=True)
    print("Agents Loaded", flush=True)
    print("Ensemble Loaded", flush=True)
    print("Startup Complete", flush=True)



# -- Health probe helpers ----------------------------------------------

_HEALTH_PROBE_TIMEOUT = 1.5
"""Per-dependency probe budget, in seconds. A health endpoint that can block
is worse than no health endpoint: the thing polling it treats a hang as a
hard outage."""


def _probe_forecasting() -> Dict[str, Any]:
    """Phase 2 forecasting: is a published store loaded, and how fresh is it."""
    try:
        from mandisense_ai.forecasting.service import ForecastService

        status = ForecastService().status()
        return {
            "phase": 2,
            "required": False,
            "status": "up" if status.get("available") else "down",
            "as_of_date": status.get("as_of_date"),
            "generated_at": status.get("generated_at"),
            "model_version": status.get("model_version"),
            "series_published": status.get("series_count"),
            "forecast_rows": status.get("forecast_rows"),
            "freshness": status.get("freshness"),
            "age_hours": status.get("age_hours"),
        }
    except Exception as exc:
        return {"phase": 2, "required": False, "status": "down", "error": str(exc)[:200]}


def _probe_spillover() -> Dict[str, Any]:
    """Phase 2 spillover: is a validated matrix artifact loaded."""
    try:
        from mandisense_ai.spillover.service import SpilloverService

        status = SpilloverService().status()
        return {
            "phase": 2,
            "required": False,
            "status": "up" if status.get("available") else "down",
            "placebo_verdict": status.get("placebo_verdict"),
            "is_validated": status.get("is_validated"),
            "total_edges": status.get("total_edges"),
            "actionable_edges": status.get("actionable_edges"),
        }
    except Exception as exc:
        return {"phase": 2, "required": False, "status": "down", "error": str(exc)[:200]}


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/v1/health")
async def health_check(response: Response):
    """Whole-system health: the Phase 1 cognition baseline, the Phase 2
    forecasting and spillover engines, and the optional infrastructure
    dependencies, in one call.

    Two distinctions matter here and are made explicitly:

    * **Optional vs required.** Postgres and Redis are accelerators - the
      cognition engine, the forecast store and the spillover matrix all read
      from local artifacts and serve correctly without them. Their absence is
      reported as `not_configured`, not as a fault, so a deployment that never
      provisioned them does not permanently report itself degraded.
    * **Reachability vs breaker state.** These were previously conflated, and
      the payload read `"db": "CLOSED"` for an unreachable database - the
      exact inverse of what CLOSED means for a circuit breaker. Reachability
      is now `up`/`down`/`not_configured` and the breaker reports its own
      state under its own key.

    The probe budget is bounded: every dependency check is wrapped in its own
    timeout, so this endpoint cannot hang behind a dead host.
    """
    probe_started = time.time()
    try:
        components: Dict[str, Any] = {}

        # -- Optional infrastructure --------------------------------------
        db_configured = bool(os.getenv("DATABASE_URL") or os.getenv("POSTGRES_HOST"))
        redis_configured = bool(os.getenv("REDIS_URL") or os.getenv("REDIS_HOST"))

        db_ok = False
        if not db_configured:
            db_reach = "not_configured"
        elif db_breaker.is_open():
            db_reach = "circuit_open"
        else:
            try:
                db_ok = await asyncio.wait_for(ping_db_async(), timeout=_HEALTH_PROBE_TIMEOUT)
                db_breaker.record_success() if db_ok else db_breaker.record_failure()
            except Exception:
                db_breaker.record_failure()
            db_reach = "up" if db_ok else "down"

        redis_ok = False
        if not redis_configured:
            redis_reach = "not_configured"
        elif redis_breaker.is_open():
            redis_reach = "circuit_open"
        else:
            try:
                # to_thread alone cannot be cancelled, so the wait_for is what
                # actually bounds this call; without it a dead Redis host held
                # the endpoint open for the full socket timeout on every probe.
                redis_ok = await asyncio.wait_for(
                    asyncio.to_thread(ping_redis), timeout=_HEALTH_PROBE_TIMEOUT
                )
                redis_breaker.record_success() if redis_ok else redis_breaker.record_failure()
            except Exception:
                redis_breaker.record_failure()
            redis_reach = "up" if redis_ok else "down"

        components["postgres"] = {
            "required": False,
            "reachability": db_reach,
            "breaker": db_breaker.state,
        }
        components["redis"] = {
            "required": False,
            "reachability": redis_reach,
            "breaker": redis_breaker.state,
        }

        # -- Phase 1: cognition baseline ----------------------------------
        engine = getattr(app.state, "cognition_engine", None)
        activation_done = getattr(app.state, "activation_complete", False)
        cycles = getattr(engine, "cycle_count", 0) if engine else 0
        if engine is not None:
            cognition_status = "up"
        elif activation_done:
            cognition_status = "down"
        else:
            cognition_status = "warming_up"
        components["cognition"] = {
            "phase": 1,
            "required": True,
            "status": cognition_status,
            "cycle_count": cycles,
            "avg_cycle_duration_sec": round(
                getattr(engine, "total_cycle_time", 0) / cycles, 4
            ) if cycles else 0,
            "uptime_sec": round(time.time() - getattr(engine, "_start_time", time.time()), 1) if engine else 0,
        }

        # -- Phase 2: forecasting + spillover ------------------------------
        # Both services are contractually non-raising, but health must not be
        # the one place that assumes so.
        components["forecasting"] = _probe_forecasting()
        components["spillover"] = _probe_spillover()

        # Only components marked required can make the system unhealthy.
        required_down = [
            name for name, c in components.items()
            if c.get("required") and c.get("status") == "down"
        ]
        warming = [
            name for name, c in components.items()
            if c.get("status") == "warming_up"
        ]
        if required_down:
            status = "unhealthy"
            response.status_code = 503
        elif warming:
            # 503 is still correct for a load balancer - the instance cannot
            # serve its full contract yet - but the body says why.
            status = "starting"
            response.status_code = 503
        elif db_breaker.state == "OPEN" or redis_breaker.state == "OPEN":
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "probe_duration_ms": round((time.time() - probe_started) * 1000, 1),
            "degraded_components": required_down,
            "warming_components": warming,
            "components": components,
            # Retained so existing dashboards and the frontend status widget
            # keep working against the flat shape they were written for.
            "services": {
                "api": "alive",
                "db": db_reach,
                "redis": redis_reach,
            },
            "cognition_reliability": {
                "cycle_count": cycles,
                "avg_cycle_duration_sec": components["cognition"]["avg_cycle_duration_sec"],
                "uptime_sec": components["cognition"]["uptime_sec"],
            },
        }
    except Exception as e:
        logger.error(f"HEALTH_CHECK_CRASH: {e}", exc_info=True)
        return {
            "status": "INTERNAL_DIAGNOSTIC_ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Consumption-first prediction endpoint. 
    Fetches precomputed intelligence from the Cognition Machine.
    """
    start_time = time.time()
    req_id = REQUEST_ID.get()
    
    # 1. Institutional Cognition Check (Market Memory)
    state_store = MarketMemoryStore()

    canonical_mandi = get_canonical_mandi(request.mandi)

    state = state_store.get_latest_state(
        request.commodity,
        canonical_mandi
    )
    
    if state:
        log_event("cognition_consumption", 
                  commodity=request.commodity, mandi=request.mandi, 
                  status="success")

        directive = state.directives[0] if state.directives else None

        action = action_code_from_state(state)
        narrative = directive.reasoning if directive else "Market intelligence is available."

        # Map the institutional state to the legacy response format for TraderOS compatibility
        return PredictResponse(
            request_id=req_id,
            prediction=state.price_prediction,
            confidence=state.confidence.score,
            status="success",
            decision=action,
            risk_level=str(state.risk_level),
            action_strength=directive.urgency if directive else "NORMAL",
            direction=state.trend,
            confidence_label="Calibrated" if state.confidence.score > 0.8 else "Nominal",
            summary=narrative,
            reasoning=narrative,
            signals={
                "volatility": state.volatility.regime,
                "arrival_trend": state.forecast_arrivals
            },
            metadata=state.metadata,
            cache={"hit": True, "source": "cognition_machine"}
        )

    # 2. Fallback: If not precomputed, return 404 in Institutional mode
    # In Phase 1, we strictly enforce offline intelligence.
    log_event("cognition_miss", commodity=request.commodity, mandi=request.mandi)
    raise HTTPException(
        status_code=404,
        detail=f"Intelligence for {request.commodity} @ {request.mandi} is currently being synthesized by the MandiSense Hidden Machine. Please check back shortly."
    )


class SimulationRequest(BaseModel):
    commodity: str
    mandi: str
    scenario_type: str # e.g. CORRIDOR_COLLAPSE, RAINFALL_SHOCK
    params: Dict[str, Any] = Field(default_factory=dict)

@app.post("/v1/cognition/simulate")
async def simulate_market(request: SimulationRequest):
    """
    Injects a counterfactual scenario into the cognition council.
    "What happens if reality mutates?"
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    engine = CognitionEngine()
    
    scenario = {
        "type": request.scenario_type,
        "params": request.params,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        engine.deployment_manager.log_action(
            org_id="org_default",
            actor="SYSTEM",
            action="TRIGGER_SIMULATION",
            details=f"Scenario {request.scenario_type} injected for {request.commodity} @ {request.mandi}."
        )
        # We run simulation asynchronously and it broadcasts its result via WebSocket
        canonical_mandi = get_canonical_mandi(request.mandi)

        asyncio.create_task(
            engine.simulate_future(
                request.commodity,
                canonical_mandi,
                scenario
            )
        )
        return {"status": "simulation_initiated", "scenario": request.scenario_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/cognition/refresh")
async def refresh_cognition():
    """
    Triggers a full portfolio cognition refresh.
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    engine = CognitionEngine()
    asyncio.create_task(engine.run_full_refresh())
    return {"status": "refresh_initiated"}

@app.get("/v1/debug/state/{commodity}/{mandi}")
async def debug_state(commodity: str, mandi: str):
    """
    Temporary debug endpoint.
    Returns the exact MarketState currently loaded from cognition storage.
    """
    from mandisense_ai.cognition.state_store import MarketMemoryStore

    state_store = MarketMemoryStore()

    canonical_mandi = get_canonical_mandi(mandi)

    state = state_store.get_latest_state(
        commodity,
        canonical_mandi
    )

    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"No state found for {commodity} @ {canonical_mandi}"
        )

    if hasattr(state, "model_dump"):
        return state.model_dump()

    if hasattr(state, "dict"):
        return state.dict()

    return state

@app.get("/v1/cognition/memories")
async def get_memories(commodity: Optional[str] = None):
    """
    Retrieves the list of strategic memories from the institutional archive.
    "Reading the institutional brain."
    """
    from mandisense_ai.cognition.memory_engine import InstitutionalMemoryEngine
    engine = InstitutionalMemoryEngine()
    
    memories = []
    for file in engine.storage_path.glob("*.json"):
        with open(file, 'r') as f:
            data = json.load(f)
            if not commodity or data["commodity"] == commodity:
                memories.append({
                    "id": data["id"],
                    "timestamp": data["timestamp"],
                    "type": data["type"],
                    "commodity": data["commodity"],
                    "scenario": data.get("scenario_type")
                })
    return sorted(memories, key=lambda x: x["timestamp"], reverse=True)

@app.get("/v1/cognition/states")
async def get_latest_states():
    """
    Retrieves the latest evolved market state for all tracked commodities/mandis.
    Uses canonical registry to ensure correct snapshot file lookups.
    """
    from mandisense_ai.cognition.state_store import MarketMemoryStore
    from mandisense_ai.cognition.registry import CognitionRegistry
    import json
    state_store = MarketMemoryStore()

    commodities = CognitionRegistry.get_canonical_commodities()
    mandis = CognitionRegistry.get_canonical_mandis()

    states = []
    for commodity in commodities:
        for mandi in mandis:
            state = state_store.get_latest_state(commodity, mandi)
            if state:
                try:
                    d = state.model_dump() if hasattr(state, 'model_dump') else state.dict()
                    # Ensure datetime fields are serialized as strings
                    states.append(json.loads(json.dumps(d, default=str)))
                except Exception:
                    pass
    return states

@app.get("/v1/cognition/memory/{memory_id}")
async def get_memory_detail(memory_id: str):
    """
    Retrieves the full details of a specific strategic memory for replay.
    """
    from mandisense_ai.cognition.memory_engine import InstitutionalMemoryEngine
    engine = InstitutionalMemoryEngine()
    
    file_path = engine.storage_path / f"{memory_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Memory not found")
        
    with open(file_path, 'r') as f:
        return json.load(f)

@app.get("/v1/orchestration/plans")
async def get_orchestration_plans(commodity: Optional[str] = None):
    """
    Retrieves active operational execution plans.
    "Monitoring the command center."
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    engine = CognitionEngine()
    return engine.orchestration_engine.get_active_plans(commodity)

class ApprovalRequest(BaseModel):
    plan_id: str
    action_id: str
    operator_id: Optional[str] = "OPERATOR_UNKNOWN"

@app.get("/v1/deployment/audit")
async def get_audit_log(org_id: str = "org_default"):
    """
    Retrieves the institutional action audit trail (newest-first, max 50).
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    entries = CognitionEngine().deployment_manager.get_audit_trail(org_id)
    result = []
    for e in reversed(entries[-50:]):
        d = e.dict() if hasattr(e, 'dict') else (e.model_dump() if hasattr(e, 'model_dump') else dict(e))
        d['timestamp'] = str(d.get('timestamp', ''))
        result.append(d)
    return result

@app.post("/v1/orchestration/approve")
async def approve_orchestration_action(request: ApprovalRequest):
    """
    Approves a specific operational action with audit lineage.
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    engine = CognitionEngine()
    engine.approve_orchestration(request.plan_id, request.action_id, operator_id=request.operator_id)
    return {"status": "action_approved", "plan_id": request.plan_id, "action_id": request.action_id}

@app.get("/v1/enterprise/posture")
async def get_enterprise_posture():
    """
    Retrieves the systemic operational posture of the organization.
    "Monitoring the organizational nervous system."
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    engine = CognitionEngine()
    return engine.enterprise_hub.get_strategic_posture()

@app.get("/v1/institutional/metrics")
async def get_institutional_metrics():
    """
    What this system's published forecasts actually turned out to be worth.

    `realised` is the authoritative section: every published forecast row is
    appended to the forecast ledger as a dated claim, and scored against the
    observed price once that date arrives. Rates are withheld below a sample
    size that could support them, so an early deployment reports
    INSUFFICIENT_EVIDENCE rather than a hit rate computed from a handful of
    outcomes.

    `drift` compares those realised rates against the spread the model's own
    walk-forward folds produced at training time. Every promotion gate in this
    system was earned on historical folds; this is the check that asks whether
    the conditions those gates were granted under still hold.

    `deliberation` is the in-process plan bookkeeping, kept for continuity and
    explicitly not a measure of forecast accuracy — it differences the model's
    predictions against each other, never against an observed price.
    """
    payload: Dict[str, Any] = {}

    try:
        from mandisense_ai.forecasting.config import FORECAST_HORIZONS
        from mandisense_ai.forecasting.ledger import ForecastLedger, detect_drift

        ledger = ForecastLedger()
        payload["realised"] = ledger.live_performance()
        payload["per_horizon"] = {
            str(h): ledger.live_performance(h) for h in FORECAST_HORIZONS
        }
        try:
            from mandisense_ai.forecasting.train import ForecastBundle

            payload["drift"] = detect_drift(ForecastBundle.load(), ledger)
        except Exception as exc:
            payload["drift"] = {"status": "UNAVAILABLE", "reason": str(exc)}
    except Exception as exc:
        logger.warning("Institutional metrics: ledger unavailable: %s", exc)
        payload["realised"] = {"status": "UNAVAILABLE", "reason": str(exc)}

    try:
        from mandisense_ai.cognition.engine import CognitionEngine

        payload["deliberation"] = CognitionEngine().verification_engine.get_institutional_effectiveness()
    except Exception as exc:
        payload["deliberation"] = {"status": "UNAVAILABLE", "reason": str(exc)}

    return payload

@app.post("/v1/trace-run")
async def trace_run(request: PredictRequest):
    """
    Triggers the pipeline and returns the result, 
    while emitting events to all connected /ws/trace clients.
    """
    # Use the same logic as predict but dedicated for trace
    # We run it in a thread to not block the event loop, 
    # but the instrumentation in run_pipeline handles emissions.
    try:
        result = await asyncio.to_thread(run_pipeline, request.commodity, request.mandi)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))



