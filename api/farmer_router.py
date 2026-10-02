"""
Farmer feature API.

Every endpoint here is a thin, testable wrapper around one module in
`mandisense_ai/farmer/` — see that package for what each feature actually
computes and why. Kept as one router file, mounted once in `api/main.py`,
so the whole farmer-facing surface has one place to audit for consistency
(status codes, error shape, canonical id resolution).

None of these endpoints run a model at request time; every one either reads
the already-published forecast store or the observation archive directly,
matching the rest of this system's offline-training/online-serving split
(see `forecasting/config.py`).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/farmer", tags=["farmer"])


# ── Fair Price Check ────────────────────────────────────────────────────────


@router.get("/fair-price/{commodity}/{mandi_id}")
async def fair_price_check(
    commodity: str,
    mandi_id: str,
    offered_price: float = Query(..., gt=0),
    quantity_quintals: Optional[float] = Query(None, gt=0),
):
    from mandisense_ai.farmer.fair_price import check_offer

    return check_offer(commodity, mandi_id, offered_price, quantity_quintals)


# ── My Harvest in Rupees ─────────────────────────────────────────────────────


@router.get("/harvest/{commodity}/{mandi_id}")
async def harvest_plan(commodity: str, mandi_id: str, quantity_quintals: float = Query(..., gt=0)):
    from mandisense_ai.farmer.harvest import plan_harvest

    return plan_harvest(commodity, mandi_id, quantity_quintals)


# ── Hold or Rot ──────────────────────────────────────────────────────────────


@router.get("/hold-or-sell/{commodity}/{mandi_id}")
async def hold_or_sell(commodity: str, mandi_id: str, quantity_quintals: float = Query(1.0, gt=0)):
    from mandisense_ai.farmer.storage import hold_or_sell as _hold_or_sell

    return _hold_or_sell(commodity, mandi_id, quantity_quintals)


# ── This Time Last Year ──────────────────────────────────────────────────────


@router.get("/seasonal-memory/{commodity}/{mandi_id}")
async def seasonal_memory(commodity: str, mandi_id: str):
    from mandisense_ai.farmer.seasonal_memory import seasonal_reading

    return seasonal_reading(commodity, mandi_id)


# ── Where to Sell ─────────────────────────────────────────────────────────────


@router.get("/where-to-sell/{commodity}")
async def where_to_sell(
    commodity: str,
    origin_mandi_id: Optional[str] = Query(None),
    origin_lat: Optional[float] = Query(None),
    origin_lon: Optional[float] = Query(None),
    quantity_quintals: float = Query(1.0, gt=0),
):
    from mandisense_ai.farmer.transport import compare_mandis

    if not origin_mandi_id and (origin_lat is None or origin_lon is None):
        raise HTTPException(400, "Provide either origin_mandi_id or both origin_lat and origin_lon.")
    return compare_mandis(commodity, origin_mandi_id, origin_lat, origin_lon, quantity_quintals)


# ── Supply Flood Warning ─────────────────────────────────────────────────────


@router.get("/supply-signal/{commodity}/{mandi_id}")
async def supply_signal(commodity: str, mandi_id: str):
    from mandisense_ai.farmer.supply_signal import supply_reading

    return supply_reading(commodity, mandi_id)


# ── Track Record ─────────────────────────────────────────────────────────────


@router.get("/track-record/{commodity}/{mandi_id}")
async def track_record(commodity: str, mandi_id: str, horizon_days: Optional[int] = Query(None)):
    from mandisense_ai.farmer.track_record import track_record as _track_record

    return _track_record(commodity, mandi_id, horizon_days)


# ── What to Plant Next Season ────────────────────────────────────────────────


@router.get("/crop-planning/{mandi_id}")
async def crop_planning(mandi_id: str, target_month: int = Query(..., ge=1, le=12)):
    from mandisense_ai.farmer.crop_planning import seasonal_crop_comparison

    return seasonal_crop_comparison(mandi_id, target_month)


# ── Price Alerts ──────────────────────────────────────────────────────────────


class CreateAlertRequest(BaseModel):
    phone: str = Field(..., min_length=6)
    commodity: str
    mandi_id: str
    alert_type: str
    threshold: Optional[float] = None


@router.post("/alerts")
async def create_alert(payload: CreateAlertRequest):
    from mandisense_ai.farmer.alerts import create_alert as _create_alert

    result = _create_alert(
        payload.phone, payload.commodity, payload.mandi_id, payload.alert_type, payload.threshold
    )
    if result.get("status") == "ERROR":
        raise HTTPException(400, result.get("reason", "Could not create alert."))
    return result


@router.get("/alerts")
async def list_alerts(phone: str = Query(..., min_length=6)):
    from mandisense_ai.farmer.alerts import list_alerts as _list_alerts

    return {"phone": phone, "alerts": _list_alerts(phone)}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, phone: str = Query(..., min_length=6)):
    from mandisense_ai.farmer.alerts import delete_alert as _delete_alert

    result = _delete_alert(phone, alert_id)
    if result.get("status") == "ERROR":
        raise HTTPException(404, result.get("reason", "Alert not found."))
    return result


# ── Village Truck Sharing ─────────────────────────────────────────────────────


class PostTripRequest(BaseModel):
    mandi_id: str
    travel_date: str
    total_capacity_quintals: float = Field(..., gt=0)
    posted_by_phone: str = Field(..., min_length=6)
    posted_by_name: Optional[str] = None


@router.post("/truck-share/trips")
async def post_trip(payload: PostTripRequest):
    from mandisense_ai.farmer.truck_share import post_trip as _post_trip

    result = _post_trip(
        payload.mandi_id, payload.travel_date, payload.total_capacity_quintals,
        payload.posted_by_phone, payload.posted_by_name,
    )
    if result.get("status") == "ERROR":
        raise HTTPException(400, result.get("reason", "Could not post trip."))
    return result


@router.get("/truck-share/trips")
async def list_trips(mandi_id: Optional[str] = Query(None), on_or_after: Optional[str] = Query(None)):
    from mandisense_ai.farmer.truck_share import list_trips as _list_trips

    return {"trips": _list_trips(mandi_id, on_or_after)}


class JoinTripRequest(BaseModel):
    quantity_quintals: float = Field(..., gt=0)
    joiner_phone: str = Field(..., min_length=6)
    joiner_name: Optional[str] = None


@router.post("/truck-share/trips/{trip_id}/join")
async def join_trip(trip_id: str, payload: JoinTripRequest):
    from mandisense_ai.farmer.truck_share import join_trip as _join_trip

    result = _join_trip(trip_id, payload.quantity_quintals, payload.joiner_phone, payload.joiner_name)
    if result.get("status") == "ERROR":
        raise HTTPException(400, result.get("reason", "Could not join trip."))
    return result


# ── Price on a Date (verification for the client-side "My Money" ledger) ─────


@router.get("/price-on-date/{commodity}/{mandi_id}")
async def price_on_date(commodity: str, mandi_id: str, date: str = Query(..., min_length=8)):
    from mandisense_ai.farmer.price_lookup import price_on_date as _price_on_date

    return _price_on_date(commodity, mandi_id, date)


# ── Reference data (mandi list for map pickers, etc.) ────────────────────────


@router.get("/mandis")
async def list_mandis():
    from mandisense_ai.farmer import registry

    return {
        "mandis": [
            {"mandi_id": m.id, "mandi_name": m.name, "mandi_name_kn": m.name_kn, "mandi_name_hi": m.name_hi,
             "district": m.district, "lat": m.lat, "lon": m.lon}
            for m in registry.MANDIS.values()
        ]
    }


@router.get("/mandis/nearest")
async def nearest_mandis_endpoint(lat: float = Query(...), lon: float = Query(...), limit: int = Query(5, ge=1, le=20)):
    from mandisense_ai.farmer import registry

    ranked = sorted(registry.MANDIS.values(), key=lambda m: registry.haversine_km((lat, lon), (m.lat, m.lon)))
    return {"mandis": [
        {"mandi_id": m.id, "mandi_name": m.name, "distance_km": round(registry.haversine_km((lat, lon), (m.lat, m.lon)), 1)}
        for m in ranked[:limit]
    ]}


# ── The farmer app's read model ─────────────────────────────────────────────
# One call per screen; see mandisense_ai/farmer/dashboard.py.


@router.get("/catalog")
async def farmer_catalog():
    from mandisense_ai.farmer.dashboard import catalog

    return catalog()


@router.get("/nearest-district")
async def nearest_district_endpoint(lat: float = Query(...), lon: float = Query(...)):
    from mandisense_ai.farmer import registry

    district, km = registry.nearest_district(lat, lon)
    return {"district": district.id, "distance_km": km}


@router.get("/overview/{district}")
async def farmer_overview(district: str):
    from mandisense_ai.farmer.dashboard import overview

    return overview(district)


@router.get("/mandi/{mandi_id}")
async def farmer_mandi(mandi_id: str):
    from mandisense_ai.farmer.dashboard import mandi_page

    return mandi_page(mandi_id)


@router.get("/board/{district}/{crop}")
async def farmer_board(district: str, crop: str):
    from mandisense_ai.farmer.dashboard import board

    return board(district, crop)


@router.get("/sell-plan/{crop}/{mandi_id}")
async def farmer_sell_plan(crop: str, mandi_id: str, quantity_quintals: float = Query(..., gt=0)):
    from mandisense_ai.farmer.dashboard import sell_plan

    return sell_plan(crop, mandi_id, quantity_quintals)


@router.get("/accuracy")
async def farmer_accuracy():
    from mandisense_ai.farmer import world

    return world.model_report()


@router.get("/ask")
async def farmer_ask(q: str = Query(..., min_length=1, max_length=300), district: Optional[str] = None):
    from mandisense_ai.farmer.dashboard import ask

    return ask(q, district)
