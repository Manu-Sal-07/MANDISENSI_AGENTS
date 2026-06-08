"""
GET /v1/model/status — Model registry and health information.
"""

from fastapi import APIRouter

from api.schemas.models import ModelStatusResponse
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status():
    """
    Report the status of Phase-1 and Phase-2.5 models.

    Includes per-regime R², MAE, training data size, and last trained timestamp.
    """
    phase2_info = {"status": "not_loaded", "models": {}}

    try:
        from mandisense_ai.ensemble.learned_ensemble import LearnedEnsemble
        le = LearnedEnsemble()
        if le.load():
            models_info = {}
            for regime, trained in le.models.items():
                models_info[regime] = {
                    "r2_val": round(trained.r2_val, 4),
                    "mae_val": round(trained.mae_val, 4),
                    "n_train": trained.n_train,
                    "last_trained": trained.trained_at,
                }
            phase2_info = {"status": "active", "models": models_info}
        else:
            phase2_info = {"status": "no_models", "models": {}}
    except Exception as e:
        logger.warning(f"[model_status] LearnedEnsemble error: {e}")
        phase2_info = {"status": "error", "error": str(e)}

    return ModelStatusResponse(
        phase1={"status": "active", "version": "1.5.0"},
        phase2=phase2_info,
    )
