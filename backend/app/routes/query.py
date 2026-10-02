from fastapi import APIRouter, HTTPException
from backend.app.schemas.request import QueryRequest
from backend.app.schemas.response import QueryResponse
from backend.app.services import model_loader
from mandisense_ai.core.orchestrator.query_orchestrator import QueryOrchestrator

router = APIRouter()

# `model_loader.engines` is populated by a background warmup task with a
# 15-second timeout whose failures are logged and swallowed (see
# `api/main.py`), so it is routinely still None when the first request
# lands. This endpoint dereferenced it unguarded and turned that race into
# a 500 on every farmer question asked before warmup finished -- the same
# defect fixed for the discovery routes in `discovery.py`, for the same
# reason: `QueryOrchestrator` (and the `DecisionOrchestrator` it wraps)
# reads the already-published forecast store and runs no model at request
# time, so it has no warmup to wait for in the first place.
_ORCHESTRATOR = QueryOrchestrator()


def _query_orchestrator():
    engines = getattr(model_loader, "engines", None)
    return getattr(engines, "query_orch", None) or _ORCHESTRATOR


@router.post("/", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        res = await _query_orchestrator().handle_user_query(request.query)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")
