"""
Forecast API.

Serves the nightly-published forecast store. Nothing here loads a model or
builds a feature — a request is a lookup against a table that the scheduled
job already computed and validated.

The responses distinguish four outcomes deliberately, because collapsing them
is how a forecasting product starts lying to its users:

    503                        the nightly job has not published anything yet
    200 + INSUFFICIENT_HISTORY we track this mandi but cannot forecast it yet
    200 + DORMANT              it has not traded recently enough to forecast
    200 + REBUILDING_HISTORY   it has resumed trading but lacks enough
                              contiguous history for its windowed features
    200 + OK                   a real forecast, with its interval and freshness
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.forecasting.service import get_forecast_service

router = APIRouter()


class IntervalModel(BaseModel):
    p05: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    p95: Optional[float] = None


class ForecastPoint(BaseModel):
    horizon_days: Optional[int] = None
    target_date: Optional[str] = None
    status: str
    reason: Optional[str] = None
    forecast_price: Optional[float] = None
    expected_change_pct: Optional[float] = None
    direction: Optional[str] = None
    interval: Optional[IntervalModel] = None
    interval_source: Optional[str] = None
    """`row_conditional_quantile` where a dedicated quantile model has
    measurably calibrated out of sample for this horizon (its width reflects
    this row's own volatility/seasonal signals); `pooled_residual` otherwise
    (a fold-fixed offset from the point forecast — see `quantile.py`)."""
    prediction_source: Optional[str] = None
    """`xgboost_linear_blend` where a walk-forward measurement showed an
    inverse-error-weighted blend of the point model and a regularised linear
    model beating the point model alone for this horizon; `xgboost` (the
    point model only) otherwise — see `train.py`'s `blend_models`."""
    decision: Optional[str] = None
    """SELL/HOLD/WAIT, from the calibrated interval read against a threshold
    whose SELL/HOLD precision was *measured* on held-out folds for this
    horizon (see `decision.py`) — WAIT for every row at a horizon where no
    threshold cleared the bar, rather than an unvalidated confident call."""
    decision_probability_of_decline: Optional[float] = None
    """Where the calibrated band places zero return, as a probability —
    the number `decision` was thresholded against."""
    model_skill: Optional[float] = None


class ForecastResponse(BaseModel):
    commodity: str
    mandi_id: str
    as_of_date: Optional[str] = None
    last_observed_price: Optional[float] = None
    data_lag_days: Optional[int] = None
    history_rows: Optional[int] = None
    freshness: str
    generated_at: Optional[str] = None
    points: List[ForecastPoint] = Field(default_factory=list)
    caveat: str


CAVEAT = (
    "Forecasts are produced by a scheduled offline job: market observations "
    "are ingested nightly from the public Agmarknet feed, features and "
    "predictions are recomputed in batch, and this endpoint reads the result. "
    "Intervals are empirical — they reflect how wrong this model actually was "
    "on held-out historical folds, not a normality assumption. Measured skill "
    "over a naive 'price unchanged' forecast is a few percent, so treat the "
    "interval as the decision-relevant output rather than the point estimate."
)


def _require_service():
    service = get_forecast_service()
    if not service.is_available:
        status = service.status()
        raise HTTPException(
            status_code=503,
            detail=(
                f"Forecasts unavailable ({status.get('reason', 'unknown')}). "
                "Run scripts/run_nightly_job.py to ingest data and publish forecasts."
            ),
        )
    return service


def _to_points(rows: List[Dict[str, Any]]) -> List[ForecastPoint]:
    points: List[ForecastPoint] = []
    for row in rows:
        interval = row.get("interval") or None
        points.append(
            ForecastPoint(
                horizon_days=row.get("horizon_days"),
                target_date=row.get("target_date"),
                status=row.get("status", "UNKNOWN"),
                reason=row.get("reason"),
                forecast_price=row.get("forecast_price"),
                expected_change_pct=row.get("expected_change_pct"),
                direction=row.get("direction"),
                interval=IntervalModel(**interval) if isinstance(interval, dict) else None,
                interval_source=row.get("interval_source"),
                prediction_source=row.get("prediction_source"),
                decision=row.get("decision"),
                decision_probability_of_decline=row.get("decision_probability_of_decline"),
                model_skill=row.get("model_skill"),
            )
        )
    return points


@router.get("/status")
async def forecast_status() -> Dict[str, Any]:
    """Freshness, coverage and interval calibration. Never fails."""
    service = get_forecast_service()
    payload = service.status()
    payload["interval_calibration"] = service.calibration()
    return payload


@router.post("/reload")
async def reload_forecasts() -> Dict[str, Any]:
    """Pick up a newly published store without restarting the API."""
    service = get_forecast_service()
    return {"reloaded": service.reload(), "status": service.status()}


@router.get("/series")
async def forecast_series() -> Dict[str, Any]:
    """Every (commodity, mandi) pair present in the current store."""
    service = _require_service()
    return {
        "series": service.available_series(),
        "promoted_horizons": service.promoted_horizons(),
    }


@router.get("/readiness")
async def forecast_readiness() -> Dict[str, Any]:
    """
    How close each tracked series is to being forecastable.

    The feed publishes a daily snapshot rather than history, so a newly seen
    mandi has to be observed for a while before it can be forecast. This makes
    that wait measurable instead of leaving it looking like a broken pipeline.
    """
    service = _require_service()
    rows = service.readiness()
    ready = [r for r in rows if r.get("state") == "OK"]
    return {
        "as_of_date": service.status().get("as_of_date"),
        "series_total": len(rows),
        "series_ready": len(ready),
        "series": rows,
    }


@router.get("/{commodity}/{mandi_id}", response_model=ForecastResponse)
async def forecast_for_series(
    commodity: str,
    mandi_id: str,
    horizon: Optional[int] = Query(
        None,
        ge=1,
        le=30,
        description="Days ahead. Omit for the full published curve; the nearest "
                    "published horizon is returned when an exact match is unavailable.",
    ),
) -> ForecastResponse:
    """
    Forecast curve for one commodity at one mandi.

    This is the endpoint behind a question like "what is tomato in Hoskote
    doing over the next five days".
    """
    service = _require_service()

    # Resolve through the same canonical mapping the ingestion and backfill
    # paths use. The cognition layer and the TraderOS views address this market
    # as `bangalore_apmc` while the observation store keys it as
    # `bangalore_yeshwanthpur`; without this the two halves of the product
    # address different series and every such lookup 404s.
    resolved_commodity = canonical_commodity(commodity) or commodity.strip().lower()
    resolved_mandi = canonical_market(mandi_id) or mandi_id.strip().lower()

    curve = service.get_curve(resolved_commodity, resolved_mandi)
    if not curve:
        known = service.available_series()
        raise HTTPException(
            status_code=404,
            detail=(
                f"No forecast record for {resolved_commodity} @ {resolved_mandi}. "
                f"{len(known)} series are currently tracked; the nightly job only "
                "publishes series it has enough history for."
            ),
        )

    if horizon is not None:
        exact = service.get_horizon(resolved_commodity, resolved_mandi, horizon)
        selected = [exact] if exact else []
        if not selected:
            nearest = service.nearest_horizon(resolved_commodity, resolved_mandi, horizon)
            # A refusal row (no horizon) is still the honest answer here.
            selected = [nearest] if nearest else [curve[0]]
        rows = selected
    else:
        rows = curve

    head = curve[0]
    return ForecastResponse(
        commodity=resolved_commodity,
        mandi_id=resolved_mandi,
        as_of_date=head.get("as_of_date"),
        last_observed_price=head.get("last_observed_price"),
        data_lag_days=head.get("data_lag_days"),
        history_rows=head.get("history_rows"),
        freshness=service.freshness(),
        generated_at=service.status().get("generated_at"),
        points=_to_points(rows),
        caveat=CAVEAT,
    )
