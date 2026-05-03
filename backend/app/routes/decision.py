from fastapi import APIRouter, HTTPException
from backend.app.schemas.request import DecisionRequest
from backend.app.schemas.response import DecisionResponse
from backend.app.services import model_loader

router = APIRouter()

@router.post("/", response_model=DecisionResponse)
async def get_decision(request: DecisionRequest):
    try:
        res = await model_loader.engines.decision_orch.get_actionable_decision(request.commodity, request.mandi_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision error: {str(e)}")
