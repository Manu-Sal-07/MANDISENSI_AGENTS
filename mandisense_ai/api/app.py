"""
FastAPI Application Factory — MandiSense AI Production API.

Creates and configures the FastAPI application with:
  • Versioned API routes (/v1/...)
  • CORS middleware
  • Request ID injection
  • Startup/shutdown lifecycle hooks (Redis + PostgreSQL)
  • Prometheus metrics (optional)
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from utils.logger import get_logger
import monitoring.metrics as metrics

logger = get_logger(__name__)

# Global instances (initialized at startup)
_controller = None
_db_client = None
_start_time = None


def get_controller():
    """Dependency: returns the global PredictionController."""
    return _controller


def get_db_client():
    """Dependency: returns the global AsyncDBClient."""
    return _db_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global _controller, _db_client, _start_time
    _start_time = time.monotonic()

    # ── 1. Initialize PostgreSQL (async) ──────────────────────────────
    logger.info("[API] Initializing AsyncDBClient...")
    from db.client import AsyncDBClient
    _db_client = AsyncDBClient()
    await _db_client.init()

    # ── 2. Initialize Redis (optional) ────────────────────────────────
    redis_client = None
    try:
        import redis.asyncio as aioredis
        import os
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info(f"[API] Redis connected at {redis_url}")
    except Exception as e:
        logger.warning(f"[API] Redis unavailable, caching disabled: {e}")
        redis_client = None

    # ── 3. Initialize Orchestrator ────────────────────────────────────
    logger.info("[API] Initializing PredictionController...")
    from orchestrator.prediction_controller import PredictionController
    _controller = PredictionController(redis_client=redis_client, db_client=_db_client)
    
    # Update Active Models Gauge
    if _controller._learned_ensemble and _controller._learned_ensemble.is_ready:
        metrics.ACTIVE_MODELS_GAUGE.set(len(_controller._learned_ensemble.models))
    else:
        metrics.ACTIVE_MODELS_GAUGE.set(0)
        
    logger.info("[API] Startup complete")

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────
    if redis_client:
        await redis_client.close()
    if _db_client:
        await _db_client.close()
    logger.info("[API] Shutdown complete")


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="MandiSense AI",
        description="Multi-agent commodity price prediction API",
        version="2.5.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID & Metrics Middleware ───────────────────────────────
    @app.middleware("http")
    async def add_request_id_and_metrics(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
        request.state.request_id = request_id
        start = time.perf_counter()

        # Skip metrics for /metrics to avoid noise
        if request.url.path == "/metrics":
            return await call_next(request)

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            metrics.HTTP_REQUESTS_TOTAL.labels(
                method=request.method, endpoint=request.url.path, status=status_code
            ).inc()
            raise e

        elapsed = time.perf_counter() - start
        
        # Record Metrics
        metrics.HTTP_REQUESTS_TOTAL.labels(
            method=request.method, endpoint=request.url.path, status=status_code
        ).inc()
        metrics.HTTP_REQUEST_LATENCY.labels(
            method=request.method, endpoint=request.url.path
        ).observe(elapsed)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed * 1000:.1f}"
        return response

    # ── Register Routes ───────────────────────────────────────────────
    from api.routes.predict import router as predict_router
    from api.routes.history import router as history_router
    from api.routes.model_status import router as model_router
    from api.routes.health import router as health_router

    # ── Prometheus Metrics Endpoint ───────────────────────────────────
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    app.include_router(predict_router, prefix="/v1", tags=["Predictions"])
    app.include_router(history_router, prefix="/v1", tags=["History"])
    app.include_router(model_router, prefix="/v1", tags=["Model"])
    app.include_router(health_router, prefix="/v1", tags=["Health"])

    return app


# Module-level app instance for uvicorn
app = create_app()

