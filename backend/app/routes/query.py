from fastapi import APIRouter, HTTPException
from backend.app.schemas.request import QueryRequest
from backend.app.schemas.response import QueryResponse
from backend.app.services import model_loader

router = APIRouter()

@router.post("/", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        res = await model_loader.engines.query_orch.handle_user_query(request.query)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")
