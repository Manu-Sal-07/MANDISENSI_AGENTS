"""
Unified MandiSense AI Application Entrypoint.
Merges production inference routes with discovery/data routes into a single FastAPI instance.
"""

import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root directory is in sys.path
# This must happen BEFORE any local imports
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, os.path.join(BASE_DIR, "mandisense_ai"))

# ── 1. Import existing inference app ──────────────────────────────────
from api.main import app

# ── 2. Import Discovery/Legacy Routers ─────────────────────────────────
from backend.app.routes import discovery, query, decision, predict as legacy_predict
from backend.app.services.model_loader import init_engines


# ── 3. Configure Unified App ──────────────────────────────────────────
# We keep the app object from api.main but extend it with discovery routes.

# Discovery routes used by the frontend
app.include_router(discovery.router, prefix="/discovery", tags=["Discovery"])
app.include_router(query.router, prefix="/query", tags=["Advisory"])
app.include_router(decision.router, prefix="/decision", tags=["Intelligence"])

# Optional: Map the /api prefix used by some frontend versions to the new discovery routes
app.include_router(discovery.router, prefix="/api", tags=["Frontend Compatibility"])

# Map legacy predict endpoint if needed, ensuring it doesn't conflict with /v1/predict
app.include_router(legacy_predict.router, prefix="/api/predict", tags=["Legacy Compatibility"])

# ── 4. Unified Startup Logic ─────────────────────────────────────────
@app.on_event("startup")
async def unified_startup():
    logging.info("[UnifiedApp] Initializing Legacy Engines for Discovery routes...")
    try:
        # The legacy backend requires model_loader initialization
        await init_engines(version="v3")
        logging.info("[UnifiedApp] Legacy engines initialized successfully.")
    except Exception as e:
        logging.error(f"[UnifiedApp] Failed to initialize legacy engines: {e}")
        # We don't crash here because the core inference (api/main.py) has its own startup

@app.get("/")
async def root_redirect():
    return {
        "message": "MandiSense AI Unified Backend is Online",
        "endpoints": {
            "inference": "/v1/predict",
            "discovery_feed": "/discovery/feed",
            "health": "/v1/health"
        }
    }
