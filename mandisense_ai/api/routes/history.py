"""
GET /v1/prediction/history — Historical prediction performance.
"""

from fastapi import APIRouter, Query, Request

from api.schemas.models import HistoryResponse, HistoryEntry, HistorySummary
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/prediction/history", response_model=HistoryResponse)
async def get_prediction_history(
    request: Request,
    commodity: str = Query(..., min_length=1),
    mandi: str = Query(..., min_length=1),
    days: int = Query(30, ge=1, le=365),
):
    """
    Retrieve historical prediction accuracy for a commodity/mandi pair.

    Returns predictions, actual outcomes (where available), and summary statistics.
    """
    commodity_clean = commodity.strip().lower()
    mandi_clean = mandi.strip().lower()

    db_client = getattr(request.app.state, "db_client", None)
    if db_client and db_client.is_connected:
        try:
            records = await db_client.get_prediction_history(
                commodity=commodity_clean,
                mandi=mandi_clean,
                days=days,
                limit=500
            )
        except Exception as e:
            logger.warning(f"[history] DB fetch failed: {e}")
            records = []
    else:
        # Fallback to JSONL
        try:
            from mandisense_ai.ensemble.prediction_logger import PredictionLogger
            plogger = PredictionLogger()
            records = plogger.read_completed(
                commodity=commodity_clean,
                mandi=mandi_clean,
            )
            # Sort by timestamp descending, limit to requested days
            records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
            # Very basic date filter for JSONL (ignores exact day count for simplicity)
            records = records[:days]
        except Exception as e:
            logger.warning(f"[history] Fallback fetch failed: {e}")
            records = []

    entries = []
    errors = []
    correct_direction = 0
    total_with_actual = 0

    for r in records:
        actual = r.get("actual_7d_change")
        # DB provides final_prediction, JSONL provides phase1_prediction
        pred = r.get("final_prediction")
        if pred is None:
            pred = r.get("phase1_prediction", 0.0)

        err = abs(pred - actual) if actual is not None else None

        if actual is not None:
            errors.append(err)
            total_with_actual += 1
            if (pred > 0 and actual > 0) or (pred < 0 and actual < 0) or (pred == 0 and actual == 0):
                correct_direction += 1

        entries.append(HistoryEntry(
            date=r.get("timestamp", "")[:10],
            predicted_change=round(pred, 4),
            actual_change=round(actual, 4) if actual is not None else None,
            error=round(err, 4) if err is not None else None,
            confidence=round(r.get("final_confidence") or r.get("phase1_confidence", 0.0), 4),
        ))

    summary = HistorySummary(
        mean_absolute_error=round(sum(errors) / len(errors), 4) if errors else None,
        directional_accuracy=round(correct_direction / total_with_actual, 4) if total_with_actual else None,
        total_predictions=len(entries),
    )

    return HistoryResponse(
        commodity=commodity_clean,
        mandi=mandi_clean,
        predictions=entries,
        summary=summary,
    )
