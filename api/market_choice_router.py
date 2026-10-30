"""
Market-choice API: where and when to sell, with a verified revenue floor.

Thin wrappers around `mandisense_ai/market_choice/`. Like the other farmer and
trader endpoints, a case the system cannot honestly answer returns
`status: "UNAVAILABLE"` with a reason rather than an error, and responses carry
structured fields and codes; the frontend composes the wording.

    GET /v1/market-choice/crops
    GET /v1/market-choice/recommend/{crop}     farmer: best place and day, expected net, guaranteed floor
    GET /v1/market-choice/matrix/{crop}        trader: every mandi x hold, net, floor, chance open
    GET /v1/market-choice/calibration/{crop}   trader: backtest, floor calibration, error multiplier
    GET /v1/market-choice/evidence             the research behind it (decision study, leakage audit, floors)

None of these endpoints trains or fits anything at request time.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/market-choice", tags=["market-choice"])


def _origin(district, mandi_id, lat, lon):
    from mandisense_ai.market_choice.service import resolve_origin

    origin = resolve_origin(district, mandi_id, lat, lon)
    if origin is None:
        raise HTTPException(400, "Provide a district, a mandi_id, or both lat and lon.")
    return origin


@router.get("/crops")
async def crops():
    from mandisense_ai.market_choice.service import crops_summary

    return crops_summary()


@router.get("/recommend/{crop}")
async def recommend(
    crop: str,
    district: Optional[str] = Query(None),
    mandi_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    quantity_quintals: float = Query(10.0, gt=0, le=10000),
    alpha: float = Query(0.10, ge=0.01, le=0.5),
    transport_per_q_km: Optional[float] = Query(None, gt=0, le=20),
    top: int = Query(5, ge=1, le=12),
):
    from mandisense_ai.market_choice.service import recommend as _recommend

    return _recommend(crop.lower(), _origin(district, mandi_id, lat, lon), quantity_quintals, alpha, transport_per_q_km, top)


@router.get("/matrix/{crop}")
async def matrix(
    crop: str,
    district: Optional[str] = Query(None),
    mandi_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    alpha: float = Query(0.10, ge=0.01, le=0.5),
    transport_per_q_km: Optional[float] = Query(None, gt=0, le=20),
):
    from mandisense_ai.market_choice.service import matrix as _matrix

    return _matrix(crop.lower(), _origin(district, mandi_id, lat, lon), alpha, transport_per_q_km)


@router.get("/calibration/{crop}")
async def calibration(crop: str):
    from mandisense_ai.market_choice.service import calibration as _calibration

    return _calibration(crop)


@router.get("/evidence")
async def evidence():
    from mandisense_ai.market_choice.service import research_evidence

    return research_evidence()


@router.get("/explain/{crop}")
async def explain(
    crop: str,
    district: Optional[str] = Query(None),
    mandi_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    quantity_quintals: float = Query(10.0, gt=0, le=10000),
    alpha: float = Query(0.10, ge=0.01, le=0.5),
    transport_per_q_km: Optional[float] = Query(None, gt=0, le=20),
    lang: str = Query("en", pattern="^(en|kn|hi)$"),
    use_llm: bool = Query(True),
):
    """Plain-language reasons for the recommendation. The model, if used, only phrases reasons: every figure, name and date
    is inserted by code, and the response says who wrote the text."""
    from mandisense_ai.market_choice.service import explain_recommendation

    return explain_recommendation(crop.lower(), _origin(district, mandi_id, lat, lon), quantity_quintals, alpha,
                                  transport_per_q_km, lang, use_llm)


# ----------------------------------------------------------------- insights (mandisense_ai/market_choice/insights.py)
@router.get("/breakdown/{crop}")
async def breakdown(
    crop: str,
    district: Optional[str] = Query(None),
    mandi_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    quantity_quintals: float = Query(10.0, gt=0, le=10000),
    alpha: float = Query(0.10, ge=0.01, le=0.5),
    transport_per_q_km: Optional[float] = Query(None, gt=0, le=20),
):
    """Why this mandi: price, fee, spoilage, transport and handling for the advice and the usual alternatives."""
    from mandisense_ai.market_choice import insights

    return insights.breakdown(crop.lower(), _origin(district, mandi_id, lat, lon), quantity_quintals, alpha, transport_per_q_km)


@router.get("/simulate/{crop}")
async def simulate(
    crop: str,
    district: Optional[str] = Query(None),
    mandi_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    quantity_quintals: float = Query(10.0, gt=0, le=10000),
    alpha: float = Query(0.10, ge=0.01, le=0.5),
    transport_per_q_km: Optional[float] = Query(None, gt=0, le=20),
    spoilage_per_day: Optional[float] = Query(None, ge=0, le=0.2),
    market_fee: Optional[float] = Query(None, ge=0, le=0.2),
    handling_per_trip: Optional[float] = Query(None, ge=0, le=500),
    max_hold_days: int = Query(3, ge=0, le=3),
):
    """What if my costs differ: the advice under your costs, and the costs at which it would change."""
    from mandisense_ai.market_choice import insights

    return insights.simulate(crop.lower(), _origin(district, mandi_id, lat, lon), quantity_quintals, alpha, transport_per_q_km,
                             spoilage_per_day, market_fee, handling_per_trip, max_hold_days)


@router.get("/crowd/{crop}")
async def crowd(
    crop: str,
    district: Optional[str] = Query(None),
    mandi_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    farmers: int = Query(200, ge=1, le=20000),
    quantity_per_farmer: float = Query(10.0, gt=0, le=1000),
    alpha: float = Query(0.10, ge=0.01, le=0.5),
    price_flexibility: float = Query(0.115, ge=0, le=1),
):
    """What if many farmers follow the same advice, and a split that avoids crashing one mandi's price."""
    from mandisense_ai.market_choice import insights

    return insights.crowd(crop.lower(), _origin(district, mandi_id, lat, lon), farmers, quantity_per_farmer, alpha, price_flexibility)


@router.get("/reporting-value/{crop}")
async def reporting_value(crop: str, window_days: int = Query(365, ge=90, le=1500)):
    """What silent mandis cost a farmer who travels to them, per mandi, from the ingested prices."""
    from mandisense_ai.market_choice import insights

    return insights.reporting_value(crop.lower(), window_days)


@router.get("/track-record/{crop}")
async def track_record(crop: str):
    """How the served advice did on days it was not fitted on."""
    from mandisense_ai.market_choice import insights

    return insights.track_record(crop.lower())
