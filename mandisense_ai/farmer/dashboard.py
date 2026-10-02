"""
The farmer app's read model: everything a screen needs, assembled from the
farmer data world in one call.

Nothing here is computed from a guess. Prices and arrivals are recorded
Agmarknet prints; forecasts are the published store; and a sell/hold *call* is
issued only for a crop and district whose out-of-sample record earned one (see
`series_quality` in the model report). Everywhere else the response says so
explicitly (`call.type == "RANGE_ONLY"`), so a screen cannot present an
unearned verdict by accident.

Reasons are returned as structured codes with their numbers rather than as
sentences, so the interface can say the same thing in Kannada, Hindi or English
without this layer owning any language.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry, world
from mandisense_ai.farmer.reference import CROP_NAMES_KANNADA, shelf_profile
from mandisense_ai.farmer.seasonal_memory import seasonal_reading
from mandisense_ai.farmer.supply_signal import supply_reading
from mandisense_ai.farmer.transmission import neighbour_signal_series
from mandisense_ai.farmer.transport import RUPEES_PER_QUINTAL_PER_KM, compare_mandis

CROP_ORDER = ["tomato", "onion", "potato", "ginger", "garlic"]
HISTORY_DAYS = 120
SPARK_DAYS = 30
CALL_HORIZON_PREFERENCE = (5, 3, 7)
PRICE_MOVE_NOTE_PCT = 3.0
LAST_YEAR_NOTE_PCT = 10.0
MAX_TRIP_KM = {"highly_perishable": 60.0, "semi_perishable": 90.0, "storable": 120.0, "default": 90.0}
"""How far a load is worth carrying. A crop that loses 8% a day cannot take a
long haul, and the road time is a cost the per-kilometre rate does not show."""


def _pct(new: float, old: float) -> Optional[float]:
    return round((new - old) / old * 100, 1) if old and old > 0 else None


def _series(crop: str, district: str) -> pd.DataFrame:
    return world.district_series(crop, district)


def _quality(crop: str, district: str) -> Dict[str, Any]:
    report = world.model_report()
    return (report.get("series_quality") or {}).get(f"{crop}/{district}", {})


def live_pairs() -> List[Dict[str, str]]:
    frame = world.district_observations()
    if frame.empty:
        return []
    last = frame["date"].max()
    out = []
    for (crop, district), g in frame.groupby(["commodity", "mandi_id"]):
        if (last - g["date"].max()).days <= 14:
            out.append({"crop": crop, "district": district})
    return out


def catalog() -> Dict[str, Any]:
    pairs = live_pairs()
    service = world.forecast_service()
    status = service.status()
    report = world.model_report()
    quality = report.get("series_quality", {})
    crops_present = sorted({p["crop"] for p in pairs}, key=lambda c: CROP_ORDER.index(c) if c in CROP_ORDER else 99)

    districts = []
    for d in registry.DISTRICTS.values():
        crops = [
            {"crop": p["crop"], "has_call": bool(quality.get(f"{p['crop']}/{d.id}", {}).get("serves_call"))}
            for p in pairs if p["district"] == d.id
        ]
        crops.sort(key=lambda c: CROP_ORDER.index(c["crop"]) if c["crop"] in CROP_ORDER else 99)
        if not crops:
            continue
        districts.append({
            "id": d.id, "name": d.name, "name_kn": d.name_kn, "name_hi": d.name_hi,
            "lat": d.lat, "lon": d.lon,
            "mandis": [{"id": m.id, "name": m.name, "name_kn": m.name_kn, "name_hi": m.name_hi}
                       for m in registry.mandis_in(d.id)],
            "crops": crops,
        })

    frame = world.district_observations()
    return {
        "data_through": str(frame["date"].max().date()) if not frame.empty else None,
        "forecast_as_of": status.get("as_of_date"),
        "crops": [{"id": c, "name_kn": CROP_NAMES_KANNADA.get(c, c)} for c in crops_present],
        "districts": districts,
        "served_horizons": report.get("served_horizons", []),
    }


def _sparkline(series: pd.DataFrame) -> List[float]:
    return [round(float(v), 1) for v in series.tail(SPARK_DAYS)["modal_price"].to_numpy()]


def _changes(series: pd.DataFrame) -> Dict[str, Optional[float]]:
    if series.empty:
        return {"d1": None, "d7": None, "d30": None}
    s = series.set_index("date")["modal_price"]
    last_date, last = s.index[-1], float(s.iloc[-1])

    def back(days: int) -> Optional[float]:
        ref = s[s.index <= last_date - pd.Timedelta(days=days)]
        return _pct(last, float(ref.iloc[-1])) if len(ref) and (last_date - ref.index[-1]).days <= days + 6 else None

    return {"d1": back(1), "d7": back(7), "d30": back(30)}


def _forecast_rows(crop: str, district: str) -> List[Dict[str, Any]]:
    service = world.forecast_service()
    if not service.is_available:
        return []
    rows = []
    for r in service.get_curve(crop, district):
        if r.get("status") != "OK" or not r.get("horizon_days"):
            continue
        band = r.get("interval") or {}
        rows.append({
            "horizon": int(r["horizon_days"]),
            "date": r.get("target_date"),
            "price": r.get("forecast_price"),
            "p05": band.get("p05"), "p25": band.get("p25"), "p75": band.get("p75"), "p95": band.get("p95"),
            "change_pct": r.get("expected_change_pct"),
            "decision": r.get("decision"),
            "p_decline": r.get("decision_probability_of_decline"),
        })
    return sorted(rows, key=lambda r: r["horizon"])


def _call(crop: str, district: str, forecast: List[Dict[str, Any]], quality: Dict[str, Any]) -> Dict[str, Any]:
    """The call for a crop: issued only where the record earned it."""
    if not forecast:
        return {"type": "NONE", "reason": "no_forecast"}
    if not quality.get("serves_call"):
        return {"type": "RANGE_ONLY", "reason": "no_proven_call"}
    by_h = {r["horizon"]: r for r in forecast}
    row = next((by_h[h] for h in CALL_HORIZON_PREFERENCE if h in by_h), forecast[0])
    decision = row.get("decision")
    if decision not in ("SELL", "HOLD"):
        return {"type": "ABSTAINED", "horizon": row["horizon"], "decision": "WAIT",
                "expected_change_pct": row.get("change_pct")}
    p = row.get("p_decline")
    confidence = p if decision == "SELL" else (1 - p if p is not None else None)
    return {"type": "ADVISED", "decision": decision, "horizon": row["horizon"], "date": row["date"],
            "expected_change_pct": row.get("change_pct"),
            "confidence": round(confidence, 3) if confidence is not None else None}


def _mandis_today(crop: str, district: str) -> List[Dict[str, Any]]:
    prices = world.mandi_prices()
    if prices.empty:
        return []
    crop_rows = prices[prices["commodity"] == crop]
    if crop_rows.empty:
        return []
    newest = crop_rows["date"].max()
    latest = crop_rows.sort_values("date").groupby("mandi_id").tail(1)
    latest = latest[(newest - latest["date"]).dt.days <= 10]
    out = []
    for _, r in latest.iterrows():
        m = registry.MANDIS.get(r["mandi_id"])
        if m is None:
            continue
        out.append({
            "id": m.id, "name": m.name, "name_kn": m.name_kn, "name_hi": m.name_hi,
            "district": m.district, "in_district": m.district == district,
            "date": str(pd.Timestamp(r["date"]).date()),
            "price": round(float(r["modal_price"]), 1), "min": round(float(r["min_price"]), 1),
            "max": round(float(r["max_price"]), 1), "arrivals": round(float(r["arrivals"]), 1),
        })
    out.sort(key=lambda m: (not m["in_district"], -m["price"]))
    return out


def _closing_pairs(crop: str, district: str) -> List[Dict[str, Any]]:
    """Test B results (mandisense_ai/farmer/transmission.py) involving this
    district, where the gap is statistically shown to close and not just
    assumed to. Nothing here is a forecast of direction -- only of how fast a
    gap of either sign tends to narrow."""
    matrix = world.transmission_matrix()
    if not matrix.get("available"):
        return []
    pairs = matrix.get("test_b_spatial_gaps", {}).get("pairs", [])
    return [p for p in pairs if p["crop"] == crop and p["closes"] and district in (p["from"], p["to"])]


def gap_note(crop: str, district: str) -> Optional[Dict[str, Any]]:
    """Today's price gap to the nearest closing-pair neighbour district, with
    the measured half-life of that gap. Farmer-facing: one neighbour, one
    number, no model of which way the price will move -- only of how long a
    gap this size has tended to last."""
    closing = _closing_pairs(crop, district)
    if not closing:
        return None
    series = neighbour_signal_series(world.district_observations(), crop, district)
    if series is None or series.empty:
        return None
    current = float(series.iloc[-1])
    if abs(current) < 0.03:  # under 3%: not worth a farmer's attention
        return None
    # The neighbour-pair whose measured half-life applies to this district,
    # regardless of which side of the pair it was estimated from.
    half_lives = [p["half_life_weeks"] for p in closing if p["half_life_weeks"]]
    if not half_lives:
        return None
    half_life = float(np.median(half_lives))
    return {
        "gap_pct": round((np.exp(current) - 1) * 100, 1),
        "direction": "neighbours_dearer" if current > 0 else "neighbours_cheaper",
        "half_life_weeks": round(half_life, 1),
        "pairs": len(closing),
    }


def board(district: str, crop: str) -> Dict[str, Any]:
    district, crop = registry.resolve_place(district), str(crop).strip().lower()
    series = _series(crop, district)
    if series.empty:
        return {"status": "UNAVAILABLE", "reason": "No recorded prices for this crop in this district.",
                "district": district, "crop": crop}

    last = series.iloc[-1]
    last_date = pd.Timestamp(last["date"])
    recent = series[series["date"] > last_date - pd.Timedelta(days=HISTORY_DAYS)]
    history = [{"d": str(r.date.date()), "p": round(float(r.modal_price), 1),
                "a": round(float(r.arrivals), 1) if pd.notna(r.arrivals) else None}
               for r in recent.itertuples()]

    # The same stretch one year earlier, dated onto this year so the two lines
    # can be drawn over each other.
    ly = series[(series["date"] > last_date - pd.Timedelta(days=HISTORY_DAYS + 365))
                & (series["date"] <= last_date - pd.Timedelta(days=365 - 14))]
    history_last_year = [{"d": str((r.date + pd.Timedelta(days=365)).date()), "p": round(float(r.modal_price), 1)}
                         for r in ly.itertuples()]

    forecast = _forecast_rows(crop, district)
    quality = _quality(crop, district)
    call = _call(crop, district, forecast, quality)
    changes = _changes(series)
    supply = supply_reading(crop, district)
    seasonal = seasonal_reading(crop, district)
    profile = shelf_profile(crop)

    reasons: List[Dict[str, Any]] = []
    if changes["d7"] is not None and abs(changes["d7"]) >= PRICE_MOVE_NOTE_PCT:
        reasons.append({"code": "price_up_week" if changes["d7"] > 0 else "price_down_week", "value": changes["d7"]})
    if supply.get("status") == "OK" and supply.get("signal") in ("FLOOD", "DROUGHT"):
        reasons.append({"code": "arrivals_high" if supply["signal"] == "FLOOD" else "arrivals_low",
                        "value": supply.get("deviation_pct")})
    ly_pct = (seasonal.get("last_year") or {}).get("change_pct")
    if ly_pct is not None and abs(ly_pct) >= LAST_YEAR_NOTE_PCT:
        reasons.append({"code": "above_last_year" if ly_pct > 0 else "below_last_year", "value": ly_pct})
    if call.get("type") == "ADVISED" and call.get("expected_change_pct") is not None:
        reasons.append({"code": "model_expects_up" if call["expected_change_pct"] > 0 else "model_expects_down",
                        "value": call["expected_change_pct"], "days": call["horizon"]})
    if profile.category == "highly_perishable":
        reasons.append({"code": "spoils_fast", "value": profile.daily_loss_pct})
    gap = gap_note(crop, district)
    if gap:
        reasons.append({"code": "neighbours_dearer" if gap["direction"] == "neighbours_dearer" else "neighbours_cheaper",
                        "value": gap["gap_pct"], "weeks": gap["half_life_weeks"]})

    d = registry.DISTRICTS.get(district)
    return {
        "status": "OK",
        "district": district,
        "district_name": {"en": d.name, "kn": d.name_kn, "hi": d.name_hi} if d else None,
        "crop": crop,
        "price": {"value": round(float(last["modal_price"]), 1), "date": str(last_date.date()),
                  "age_days": int((pd.Timestamp.now().normalize() - last_date).days),
                  "arrivals": round(float(last["arrivals"]), 1) if pd.notna(last["arrivals"]) else None},
        "changes": changes,
        "history": history,
        "history_last_year": history_last_year,
        "forecast": forecast,
        "call": call,
        "reasons": reasons,
        "supply": supply if supply.get("status") == "OK" else None,
        "seasonal": seasonal if seasonal.get("status") == "OK" else None,
        "mandis": _mandis_today(crop, district),
        "shelf": {"days": profile.shelf_life_days, "daily_loss_pct": profile.daily_loss_pct, "category": profile.category},
        "accuracy": {k: quality.get(k) for k in ("forecasts", "skill_vs_no_change", "direction_right", "serves_call")},
        "gap": gap,
    }


def overview(district: str) -> Dict[str, Any]:
    district = registry.resolve_place(district)
    quality_all = world.model_report().get("series_quality", {})
    crops = []
    for c in CROP_ORDER:
        series = _series(c, district)
        if series.empty or (series["date"].max() < world.district_observations()["date"].max() - pd.Timedelta(days=14)):
            continue
        forecast = _forecast_rows(c, district)
        call = _call(c, district, forecast, quality_all.get(f"{c}/{district}", {}))
        ch = _changes(series)
        crops.append({
            "crop": c, "price": round(float(series.iloc[-1]["modal_price"]), 1),
            "date": str(series.iloc[-1]["date"].date()), "d7": ch["d7"], "d1": ch["d1"],
            "spark": _sparkline(series), "call": call,
        })
    d = registry.DISTRICTS.get(district)
    return {"district": district, "district_name": {"en": d.name, "kn": d.name_kn, "hi": d.name_hi} if d else None,
            "crops": crops}


def sell_plan(crop: str, mandi_id: str, quantity_quintals: float) -> Dict[str, Any]:
    """One answer for one load: sell here today, take it to a better mandi, or
    wait -- every rupee figure on the same basis (the price the farmer's own
    mandi printed, less what waiting or travelling costs)."""
    crop, mandi = str(crop).strip().lower(), registry.resolve_place(mandi_id)
    qty = float(quantity_quintals)
    district = registry.district_of(mandi)
    where = compare_mandis(crop, origin_mandi_id=mandi, quantity_quintals=qty)
    if where.get("status") != "OK":
        return {"status": "UNAVAILABLE", "reason": where.get("reason", "No recent mandi price for this crop.")}

    rows = where["mandis"]
    here = next((r for r in rows if r["mandi_id"] == mandi), None)
    if here is None:
        return {"status": "UNAVAILABLE", "reason": "This mandi has no recent price for this crop."}

    options = [{"choice": "sell_today", "mandi_id": here["mandi_id"], "mandi_name": here["mandi_name"],
                "mandi_name_kn": here["mandi_name_kn"], "mandi_name_hi": here["mandi_name_hi"],
                "target_date": here["as_of_date"], "price_per_quintal": here["gross_price_per_quintal"],
                "transport_cost_per_quintal": 0.0, "total": round(here["gross_price_per_quintal"] * qty, 2),
                "thin_for_load": here["thin_for_load"]}]

    # A mandi whose usual day is smaller than this load cannot take it at the
    # printed price, however good that price looks.
    profile = shelf_profile(crop)
    reach = MAX_TRIP_KM.get(profile.category, MAX_TRIP_KM["default"])
    better = [r for r in rows if r["mandi_id"] != mandi and not r["thin_for_load"]
              and not r["outlier"] and r["distance_km"] <= reach
              and r["net_total"] > options[0]["total"]]
    if better:
        b = better[0]
        # Where the district pair this trip exploits is one of the pairs
        # Test B (mandisense_ai/farmer/transmission.py) measured to close
        # within weeks, the gap is flagged as temporary, not a standing
        # reason to travel: the number is real today but has a measured
        # shelf life of its own.
        b_district = registry.district_of(b["mandi_id"])
        closing = [p for p in _closing_pairs(crop, district) if b_district in (p["from"], p["to"])]
        half_life = round(float(np.median([p["half_life_weeks"] for p in closing])), 1) if closing else None
        options.append({"choice": "travel", "mandi_id": b["mandi_id"], "mandi_name": b["mandi_name"],
                        "mandi_name_kn": b["mandi_name_kn"], "mandi_name_hi": b["mandi_name_hi"],
                        "target_date": b["as_of_date"], "price_per_quintal": b["gross_price_per_quintal"],
                        "transport_cost_per_quintal": b["transport_cost_per_quintal"],
                        "distance_km": b["distance_km"], "total": b["net_total"],
                        "typical_arrivals_tonnes": b["typical_arrivals_tonnes"],
                        "gap_half_life_weeks": half_life})

    # Waiting: only where the record earned a call, using the district's
    # expected move applied to this mandi's own price, less what the crop
    # loses sitting.
    forecast = _forecast_rows(crop, district)
    call = _call(crop, district, forecast, _quality(crop, district))
    waits = []
    if call.get("type") == "ADVISED" and call.get("decision") == "HOLD":
        for r in forecast:
            if r["horizon"] > profile.shelf_life_days or r.get("change_pct") is None:
                continue
            keep = max(0.0, (1 - profile.daily_loss_pct / 100.0) ** r["horizon"])
            exp = here["gross_price_per_quintal"] * (1 + r["change_pct"] / 100.0)
            lo = here["gross_price_per_quintal"] * (r["p05"] / r["price"]) if r.get("p05") and r.get("price") else None
            hi = here["gross_price_per_quintal"] * (r["p95"] / r["price"]) if r.get("p95") and r.get("price") else None
            waits.append({"choice": "wait", "mandi_id": here["mandi_id"], "mandi_name": here["mandi_name"],
                          "mandi_name_kn": here["mandi_name_kn"], "mandi_name_hi": here["mandi_name_hi"],
                          "target_date": r["date"], "horizon": r["horizon"],
                          "price_per_quintal": round(exp, 1), "transport_cost_per_quintal": 0.0,
                          "spoilage_pct": round((1 - keep) * 100, 1),
                          "total": round(exp * keep * qty, 2),
                          "range_low": round(lo * keep * qty, 2) if lo else None,
                          "range_high": round(hi * keep * qty, 2) if hi else None})
        waits = [w for w in waits if w["total"] > options[0]["total"]]
        if waits:
            options.append(max(waits, key=lambda w: w["total"]))

    best = max(options, key=lambda o: o["total"])
    return {"status": "OK", "crop": crop, "quantity_quintals": qty, "baseline_total": options[0]["total"],
            "best": best["choice"], "gain_vs_baseline": round(best["total"] - options[0]["total"], 2),
            "options": options, "call": call, "transport_rate_per_quintal_per_km": RUPEES_PER_QUINTAL_PER_KM,
            "shelf": {"days": profile.shelf_life_days, "daily_loss_pct": profile.daily_loss_pct, "category": profile.category}}


_CROP_WORDS = {
    "tomato": ["tomato", "tomatoes", "ಟೊಮೇಟೊ", "ಟೊಮ್ಯಾಟೊ", "टमाटर"],
    "onion": ["onion", "onions", "ಈರುಳ್ಳಿ", "ಉಳ್ಳಾಗಡ್ಡಿ", "प्याज", "प्याज़"],
    "potato": ["potato", "potatoes", "ಆಲೂಗಡ್ಡೆ", "आलू"],
    "ginger": ["ginger", "ಶುಂಠಿ", "अदरक"],
    "garlic": ["garlic", "ಬೆಳ್ಳುಳ್ಳಿ", "ಬೆಳ್ಳೂಳ್ಳಿ", "लहसुन"],
}


def ask(question: str, default_district: Optional[str] = None) -> Dict[str, Any]:
    """Read a typed or spoken question for the crop and place it names."""
    q = question.lower()
    crop = next((c for c, words in _CROP_WORDS.items() if any(w in q for w in words)), None)
    district = None
    for d in registry.DISTRICTS.values():
        if any(n.lower() in q for n in (d.name.split(" (")[0], d.name_kn.split(" (")[0], d.name_hi.split(" (")[0])):
            district = d.id
            break
    if district is None:
        for m in registry.MANDIS.values():
            if any(n.lower() in q for n in (m.name.split(" (")[0], m.name_kn, m.name_hi)):
                district = m.district
                break
    return {"crop": crop, "district": district or default_district, "understood": bool(crop)}


def mandi_page(mandi_id: str) -> Dict[str, Any]:
    """One mandi, every crop it reported lately, with the week's change."""
    mandi_id = registry.resolve_place(mandi_id)
    mandi = registry.MANDIS.get(mandi_id)
    prices = world.mandi_prices()
    if mandi is None or prices.empty:
        return {"status": "UNAVAILABLE", "reason": "This mandi is not in the recorded data."}

    mine = prices[prices["mandi_id"] == mandi_id]
    if mine.empty:
        return {"status": "UNAVAILABLE", "reason": "This mandi has not reported recently."}
    newest = prices["date"].max()
    crops = []
    for crop, g in mine.groupby("commodity"):
        g = g.sort_values("date")
        last = g.iloc[-1]
        if (newest - last["date"]).days > 10:
            continue
        ref = g[g["date"] <= last["date"] - pd.Timedelta(days=7)]
        crops.append({
            "crop": crop, "date": str(pd.Timestamp(last["date"]).date()),
            "price": round(float(last["modal_price"]), 1), "min": round(float(last["min_price"]), 1),
            "max": round(float(last["max_price"]), 1), "arrivals": round(float(last["arrivals"]), 1),
            "d7": _pct(float(last["modal_price"]), float(ref.iloc[-1]["modal_price"])) if len(ref) else None,
            "days_reported": int(len(g)),
        })
    crops.sort(key=lambda c: CROP_ORDER.index(c["crop"]) if c["crop"] in CROP_ORDER else 99)
    return {"status": "OK", "mandi": {"id": mandi.id, "name": mandi.name, "name_kn": mandi.name_kn, "name_hi": mandi.name_hi,
                                     "district": mandi.district}, "crops": crops}
