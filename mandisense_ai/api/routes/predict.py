"""
POST /v1/predict — Core prediction endpoint.
"""

from fastapi import APIRouter, HTTPException, Request

from api.schemas.models import PredictRequest, PredictResponse
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request):
    """
    Generate a 7-day price change prediction for a commodity/mandi pair.

    Runs the full pipeline: Agents → Phase-1.5 Fusion → Phase-2.5 Learned Correction.
    Results are cached for 1 hour.
    """
    controller = getattr(request.app.state, "controller", None)
    if controller is None:
        raise HTTPException(503, "Prediction engine not initialized")

    try:
        result = await controller.predict(
            commodity=req.commodity,
            mandi=req.mandi,
            use_learned=req.use_learned,
        )
        return result
    except RuntimeError as e:
        logger.error(f"[predict] Agent failure: {e}")
        raise HTTPException(503, f"Agent execution failed: {e}")
    except Exception as e:
        logger.error(f"[predict] Unexpected error: {e}", exc_info=True)
        raise HTTPException(500, "Internal prediction error")
