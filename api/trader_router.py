"""
Trader feature API.

Thin wrappers around `mandisense_ai/trader/` — see that package for what
each feature computes and why. Same convention as `api/farmer_router.py`:
one router, one prefix, canonical id resolution and honest refusal statuses
delegated entirely to the modules underneath.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/trader", tags=["trader"])


# ── Spread scanner (spatial arbitrage) ───────────────────────────────────────


@router.get("/spreads/{commodity}")
async def spreads(
    commodity: str,
    quantity_quintals: float = Query(20.0, gt=0),
    transport_rate_override: Optional[float] = Query(None, gt=0),
    max_results: int = Query(12, ge=1, le=50),
):
    from mandisense_ai.trader.arbitrage import scan_spreads

    return scan_spreads(commodity, quantity_quintals, max_results, transport_rate_override)


# ── Volatility & regimes ──────────────────────────────────────────────────


@router.get("/volatility/{commodity}/{mandi_id}")
async def volatility(commodity: str, mandi_id: str, timeline_points: int = Query(180, ge=10, le=1000)):
    from mandisense_ai.trader.volatility import volatility_profile

    return volatility_profile(commodity, mandi_id, timeline_points)


# ── Historical analogs ────────────────────────────────────────────────────


@router.get("/analogs/{commodity}/{mandi_id}")
async def analogs(
    commodity: str,
    mandi_id: str,
    window: int = Query(30, ge=10, le=120),
    horizon_days: int = Query(7, ge=1, le=30),
    top_k: int = Query(15, ge=1, le=30),
):
    from mandisense_ai.trader.analogs import find_analogs

    return find_analogs(commodity, mandi_id, window, horizon_days, top_k)


# ── Evidence-based scenarios ──────────────────────────────────────────────


@router.get("/scenarios/{commodity}/{mandi_id}")
async def scenarios(commodity: str, mandi_id: str, horizon_days: int = Query(5, ge=1, le=30)):
    from mandisense_ai.trader.scenarios import run_all

    return run_all(commodity, mandi_id, horizon_days)


@router.get("/scenarios/{commodity}/{mandi_id}/{scenario}")
async def one_scenario(commodity: str, mandi_id: str, scenario: str, horizon_days: int = Query(5, ge=1, le=30)):
    from mandisense_ai.trader.scenarios import run_scenario

    result = run_scenario(commodity, mandi_id, scenario, horizon_days)
    if result.get("status") == "ERROR":
        raise HTTPException(400, result.get("reason", "Invalid scenario."))
    return result


# ── Fair forward price ────────────────────────────────────────────────────


@router.get("/forward-price/{commodity}/{mandi_id}")
async def forward_price(
    commodity: str,
    mandi_id: str,
    horizon_days: int = Query(7, ge=1, le=14),
    quantity_quintals: float = Query(10.0, gt=0),
):
    from mandisense_ai.trader.forward import fair_forward_price

    result = fair_forward_price(commodity, mandi_id, horizon_days, quantity_quintals)
    if result.get("status") == "ERROR":
        raise HTTPException(400, result.get("reason", "Invalid request."))
    return result


# ── Position book & risk ──────────────────────────────────────────────────


class AddPositionRequest(BaseModel):
    book_id: str = Field(..., min_length=1)
    commodity: str
    mandi_id: str
    quantity_quintals: float = Field(..., gt=0)
    avg_cost: Optional[float] = None
    side: str = "LONG"


@router.post("/positions")
async def add_position(payload: AddPositionRequest):
    from mandisense_ai.trader.positions import add_position as _add_position

    result = _add_position(
        payload.book_id, payload.commodity, payload.mandi_id,
        payload.quantity_quintals, payload.avg_cost, payload.side,
    )
    if result.get("status") == "ERROR":
        raise HTTPException(400, result.get("reason", "Could not add position."))
    return result


@router.get("/positions")
async def list_positions(book_id: str = Query(..., min_length=1)):
    from mandisense_ai.trader.positions import list_positions as _list_positions

    return {"book_id": book_id, "positions": _list_positions(book_id)}


@router.delete("/positions/{position_id}")
async def delete_position(position_id: str, book_id: str = Query(..., min_length=1)):
    from mandisense_ai.trader.positions import delete_position as _delete_position

    result = _delete_position(book_id, position_id)
    if result.get("status") == "ERROR":
        raise HTTPException(404, result.get("reason", "Position not found."))
    return result


@router.get("/positions/risk")
async def assess_risk(book_id: str = Query(..., min_length=1), horizon_days: int = Query(5, ge=1, le=30)):
    from mandisense_ai.trader.positions import assess_book

    return assess_book(book_id, horizon_days)
