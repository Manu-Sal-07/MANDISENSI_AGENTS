from fastapi import APIRouter, HTTPException
from backend.app.schemas.request import PredictRequest
from backend.app.schemas.response import PredictResponse
from backend.app.services import model_loader

router = APIRouter()

@router.post("/", response_model=PredictResponse)
async def predict(request: PredictRequest):
    try:
        res = await model_loader.engines.inference_orch.run_inference(request.commodity, request.mandi_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
