"""
GET /v1/health — System health check.
"""

import time

from fastapi import APIRouter, Request

from api.schemas.models import HealthResponse
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_boot_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Lightweight health check for load balancers and monitoring.

    Reports component-level health for: db, cache, agents, models.
    """
    components = {}
    overall = "healthy"

    # Check Database
    try:
        db = getattr(request.app.state, "db_client", None)
        if db and db.is_connected:
            ping_ok = await db.ping()
            components["db"] = "ok" if ping_ok else "error"
            if not ping_ok:
                overall = "degraded"
        else:
            components["db"] = "disabled"
    except Exception:
        components["db"] = "error"
        overall = "degraded"

    # Check Redis
    try:
        ctrl = getattr(request.app.state, "controller", None)
        if ctrl and ctrl.redis:
            await ctrl.redis.ping()
            components["cache"] = "ok"
        else:
            components["cache"] = "disabled"
    except Exception:
        components["cache"] = "error"
        overall = "degraded"

    # Check agent imports
    try:
        from core.agents.seasonality_agent import run_seasonality_agent
        from core.agents.arrival_volume_agent import run_arrival_volume_agent
        components["agents"] = "ok"
    except Exception:
        components["agents"] = "error"
        overall = "unhealthy"

    # Check learned models
    try:
        from ensemble.learned_ensemble import LearnedEnsemble
        le = LearnedEnsemble()
        if le.load():
            components["learned_models"] = "ok"
        else:
            components["learned_models"] = "no_models"
    except Exception:
        components["learned_models"] = "error"

    uptime = time.monotonic() - _boot_time

    return HealthResponse(
        status=overall,
        uptime_seconds=round(uptime, 1),
        components=components,
    )
