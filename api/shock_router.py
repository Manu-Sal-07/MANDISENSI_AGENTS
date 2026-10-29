"""
Supply-shock and spillover API.

    GET /v1/shock/radar                      every crop x district: arrivals vs norm, what usually follows, neighbour gap
    GET /v1/shock/radar/{crop}/{district}    one series
    GET /v1/shock/study                      the event-study table behind the claims (tiers, n, detectability)

`audience=farmer` shows a price-response claim only if it passes the strict evidence tier; `audience=trader`
shows every tier, sample sizes, the cross-crop watch and per-mandi arrival levels. Same convention as the other
routers: a case the system cannot honestly answer returns `status: "UNAVAILABLE"`.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/v1/shock", tags=["shock"])


@router.get("/radar")
async def radar(audience: str = Query("trader", pattern="^(farmer|trader)$"), crop: Optional[str] = None, district: Optional[str] = None):
    from mandisense_ai.shock.service import radar as _radar

    return _radar(audience, crop.lower() if crop else None, district.lower() if district else None)


@router.get("/radar/{crop}/{district}")
async def radar_one(crop: str, district: str, audience: str = Query("farmer", pattern="^(farmer|trader)$")):
    from mandisense_ai.shock.service import radar as _radar

    out = _radar(audience, crop.lower(), district.lower())
    if out.get("status") == "OK":
        out["item"] = out["items"][0] if out["items"] else None
        if out["item"] is None:
            return {"status": "UNAVAILABLE", "crop": crop, "district": district, "reason": "No arrival series for this crop and district."}
    return out


@router.get("/study")
async def study(audience: str = Query("trader", pattern="^(farmer|trader)$")):
    from mandisense_ai.shock.service import study_table

    return study_table(audience)
