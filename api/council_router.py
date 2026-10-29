"""Agent council endpoints: each specialist's forecast, the fused forecast and the evaluation that decides whether it is trusted."""

from fastapi import APIRouter

router = APIRouter(prefix="/v1/council", tags=["Agent council"])


@router.get("/evaluation")
async def council_evaluation():
    """Walk-forward comparison of the council against the single served model, per horizon, with the promotion verdict."""
    from mandisense_ai.forecasting import council_service

    return council_service.evaluation()


@router.get("/{commodity}/{mandi_id}")
async def council_view(commodity: str, mandi_id: str):
    """Per-agent and fused forecasts for one series. `promoted` says whether the council replaces the single model at that horizon."""
    from mandisense_ai.forecasting import council_service

    return council_service.view(commodity, mandi_id)
