import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.routes import predict, decision, query, discovery
from backend.app.services.model_loader import init_engines, engines
from backend.app.schemas.response import HealthResponse
import time
import collections

# --- CONFIGURATION ---
RATE_LIMIT_PER_MIN = 100
client_requests = collections.defaultdict(list)

app = FastAPI(
    title="MandiSense AI Production API",
    description="Refined infrastructure with high availability and observability.",
    version="1.1.0"
)

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STEP 2: SIMPLE RATE LIMITING MIDDLEWARE
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()
    
    # Filter requests in the last 60 seconds
    client_requests[client_ip] = [t for t in client_requests[client_ip] if now - t < 60]
    
    if len(client_requests[client_ip]) >= RATE_LIMIT_PER_MIN:
        return JSONResponse(
            status_code=429,
            content={"status": "error", "message": "Rate limit exceeded. Please wait.", "fallback_decision": "WAIT"}
        )
    
    client_requests[client_ip].append(now)
    response = await call_next(request)
    return response

# STEP 8: STRUCTURED ERROR HANDLING
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"An internal error occurred: {str(exc)}",
            "fallback_decision": "WAIT"
        }
    )

# Startup
@app.on_event("startup")
async def startup_event():
    # STEP 6: MODEL VERSIONING (Config driven)
    await init_engines(version="v3")

# STEP 10: ENHANCED HEALTH CHECK
@app.get("/health")
async def health():
    from backend.app.services import model_loader
    ds = model_loader.engines.data_service
    return {
        "status": "ok",
        "model_version": model_loader.engines.version,
        "cache_status": "ready" if len(ds._cache) > 0 else "warming_up",
        "data_freshness": "recent" if ds.metrics["stale_data_usage"] == 0 else "stale_detected",
        "models_loaded": len(ds._cache)
    }

# STEP 5: OBSERVABILITY METRICS
@app.get("/metrics")
async def metrics():
    from backend.app.services import model_loader
    return model_loader.engines.data_service.metrics

# STEP 7: MANUAL REFRESH
@app.post("/refresh-cache")
async def refresh_cache(commodity: str = None):
    from backend.app.services import model_loader
    await model_loader.engines.data_service.clear_cache(commodity)
    return {"status": "success", "message": f"Cache cleared for {commodity if commodity else 'all'}"}

# Routes
app.include_router(predict.router, prefix="/predict", tags=["Forecasting"])
app.include_router(decision.router, prefix="/decision", tags=["Intelligence"])
app.include_router(query.router, prefix="/query", tags=["Advisory"])
app.include_router(discovery.router, prefix="/discovery", tags=["Discovery"])

@app.get("/")
async def root():
    return {
        "message": "MandiSense AI Backend is Online",
        "version": "v3",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    # Use 127.0.0.1 for better local browser compatibility
    uvicorn.run(app, host="127.0.0.1", port=8000)
