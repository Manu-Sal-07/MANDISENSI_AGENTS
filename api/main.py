from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sys
import os

# ── Path Configuration ────────────────────────────────────────────────
# Ensure the root and mandisense_ai directories are in the path
# so we can import run_agents and its internal modules (core, ensemble, etc.)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "mandisense_ai"))

try:
    from run_agents import run_pipeline
except ImportError as e:
    # Fallback for different execution contexts
    print(f"Warning: Could not import run_agents from BASE_DIR. Error: {e}")
    sys.path.append(os.getcwd())
    from run_agents import run_pipeline

# ── FastAPI App Initialization ────────────────────────────────────────
app = FastAPI(
    title="MandiSense AI API",
    description="Production-ready FastAPI service for multi-agent commodity price forecasting.",
    version="1.0.0"
)

# ── Request/Response Schemas ──────────────────────────────────────────
class PredictRequest(BaseModel):
    commodity: str = Field(..., example="tomato", description="Name of the commodity (e.g., tomato, onion)")
    mandi: str = Field(..., example="kolar", description="Name of the market/mandi (e.g., kolar, lasalgaon)")

# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/v1/health")
async def health_check():
    """
    Standard health check endpoint.
    Used by monitoring tools to ensure the service is alive.
    """
    return {"status": "ok"}

@app.post("/v1/predict")
async def predict(request: PredictRequest):
    """
    Execute the multi-agent prediction pipeline.
    
    Returns:
        JSON-safe dictionary containing:
        - status: success/error
        - commodity: requested commodity
        - mandi: requested mandi
        - results: Individual agent outputs and Meta-Ensemble fused prediction
        - debug: Internal weights and signals (for transparency)
    """
    try:
        # Trigger the refactored pipeline from run_agents.py
        result = run_pipeline(request.commodity, request.mandi)
        
        # Check for internal pipeline errors
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "Pipeline Execution Failed",
                    "message": result.get("message", "Unknown error")
                }
            )
            
        return result
        
    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected crashes to ensure the service stays up
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Internal Server Error",
                "message": str(e)
            }
        )

# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # In production, this would be run via: uvicorn api.main:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
