"""Response builders for the market-choice API.

Follows the convention of the other farmer and trader endpoints: structured
fields and codes, no composed sentences, and an explicit status
("OK" | "UNAVAILABLE") instead of an error when the system cannot honestly
speak. The frontend composes the wording in English, Kannada and Hindi.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from mandisense_ai.farmer import registry
from mandisense_ai.market_choice import econ as E
from mandisense_ai.market_choice.config import (ALPHAS, DEFAULT_ALPHA, EVIDENCE_FILE, N_HOLD, TRANSPORT_PRESETS)
from mandisense_ai.market_choice.engine import ENGINE, ORIGINS

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def resolve_origin(district: Optional[str], mandi_id: Optional[str], lat: Optional[float], lon: Optional[float]
                   ) -> Optional[Dict[str, Any]]:
    if lat is not None and lon is not None:
        d, km = registry.nearest_district(lat, lon)
        return {"lat": float(lat), "lon": float(lon), "kind": "point", "label": "Your location",
                "nearest_district": d.id, "nearest_district_km": km}
    if mandi_id:
        m = registry.MANDIS.get(registry.resolve_place(mandi_id))
        if m:
            return {"lat": m.lat, "lon": m.lon, "kind": "mandi", "label": m.name, "label_kn": m.name_kn, "label_hi": m.name_hi,
                    "nearest_district": m.district}
    if district:
        d = registry.DISTRICTS.get(registry.resolve_place(district))
        if d:
            return {"lat": d.lat, "lon": d.lon, "kind": "district", "label": d.name, "label_kn": d.name_kn, "label_hi": d.name_hi,
                    "nearest_district": d.id}
    return None


def _option(ev: Dict[str, Any], a: int, quantity: float) -> Dict[str, Any]:
    panel = ev["panel"]
    m, k = E.decode(a, panel.M)
    sale = ev["decision_day"] + timedelta(days=int(k))
    base = {"hold_days": int(k), "sale_date": str(sale.date()), "weekday": WEEKDAYS[sale.weekday()],
            "is_sunday": bool(sale.weekday() == 6),
            "expected_net_per_q": round(float(ev["r_hat"][a]), 0), "floor_per_q": round(float(ev["floor"][a]), 0),
            "total_expected": round(float(ev["r_hat"][a]) * quantity, 0), "total_floor": round(float(ev["floor"][a]) * quantity, 0)}
    if m is None:
        return {"kind": "farm_gate", "mandi_id": None, "mandi_name": "Farm gate", "mandi_name_kn": "ಜಮೀನಿನಲ್ಲೇ ಮಾರಾಟ",
                "mandi_name_hi": "खेत पर बिक्री", "district": None, "distance_km": 0.0, "chance_open": 1.0,
                "expected_price": round(float(ev["r_hat"][a]), 0),
                **{**base, "hold_days": 0, "sale_date": str(ev["decision_day"].date()), "weekday": WEEKDAYS[ev["decision_day"].weekday()],
                   "is_sunday": bool(ev["decision_day"].weekday() == 6)}}
    mid = panel.markets[m]
    md = registry.MANDIS[mid]
    return {"kind": "mandi", "mandi_id": mid, "mandi_name": md.name, "mandi_name_kn": md.name_kn, "mandi_name_hi": md.name_hi,
            "district": md.district, "distance_km": round(float(ev["dist"][m]), 1), "expected_price": round(float(ev["price"][m, k]), 0),
            "chance_open": round(float(np.clip(ev["prep"][m, k], 0.0, 1.0)), 2), **base}


def _baseline(ev: Dict[str, Any], kind: str, quantity: float) -> Optional[Dict[str, Any]]:
    elig = ev["elig"]
    if not elig.any():
        return None
    if kind == "nearest":
        m = int(np.argmin(np.where(elig, ev["dist"], np.inf)))
    elif kind == "highest_yesterday":
        m = int(np.argmax(np.where(elig, ev["last_price"], -np.inf)))
    else:
        return _option(ev, E.n_actions(ev["panel"].M) - 1, quantity)
    return _option(ev, m * N_HOLD, quantity)


def evidence_for(meta: Dict[str, Any]) -> Dict[str, Any]:
    bt = meta.get("backtest", {})
    if bt.get("status") != "OK":
        return {"status": bt.get("status", "UNAVAILABLE")}
    return {
        "status": "OK", "level": bt["evidence_level"], "window": bt["window"], "scored_days": bt["scored_days"],
        "mean_net_revenue": bt["mean_net_revenue"], "gain_vs_highest_yesterday": bt["gain_vs_highest_yesterday"],
        "gain_vs_nearest": bt["gain_vs_nearest"], "share_of_oracle_gap_closed": bt["share_of_oracle_gap_closed"],
        "silent_trip_rate": bt["silent_trip_rate"],
        "floor_violation_adaptive": bt["floor_violation_adaptive"],
    }


def recommend(crop: str, origin: Dict[str, Any], quantity: float, alpha: float = DEFAULT_ALPHA,
              transport_per_q_km: Optional[float] = None, top: int = 5) -> Dict[str, Any]:
    quantity = max(float(quantity), 0.01)
    try:
        ev = ENGINE.evaluate(crop, (origin["lat"], origin["lon"]), alpha, transport_per_q_km)
    except LookupError as exc:
        return {"status": "UNAVAILABLE", "crop": crop, "reason": str(exc)}
    A = E.n_actions(ev["panel"].M)
    offered = ev["offered"]
    expected = np.where(offered, ev["r_hat"], -np.inf)
    floors = np.where(offered, ev["floor"], -np.inf)
    best = int(np.argmax(expected))
    safest = int(np.argmax(floors))
    order = [int(a) for a in np.argsort(-expected) if offered[a] and a != best][:top]

    rec = _option(ev, best, quantity)
    near = _baseline(ev, "nearest", quantity)
    high = _baseline(ev, "highest_yesterday", quantity)
    gate = _baseline(ev, "farm_gate", quantity)
    meta = ev["meta"]
    e = ev["econ"]
    return {
        "status": "OK", "crop": crop,
        "as_of": str(ev["as_of"].date()), "decision_day": str(ev["decision_day"].date()),
        "origin": {k: origin[k] for k in origin if k in ("lat", "lon", "kind", "label", "label_kn", "label_hi", "nearest_district")},
        "quantity_quintals": quantity, "alpha": alpha, "confidence_pct": round(100 * (1 - alpha)),
        "recommended": rec,
        "safest": _option(ev, safest, quantity) if safest != best else None,
        "alternatives": [_option(ev, a, quantity) for a in order],
        "baselines": {"nearest_today": near, "highest_yesterday": high, "farm_gate": gate},
        "gain": {
            "vs_nearest_per_q": round(rec["expected_net_per_q"] - near["expected_net_per_q"], 0) if near else None,
            "vs_highest_yesterday_per_q": round(rec["expected_net_per_q"] - high["expected_net_per_q"], 0) if high else None,
            "vs_nearest_total": round((rec["expected_net_per_q"] - near["expected_net_per_q"]) * quantity, 0) if near else None,
        },
        "guarantee": {"alpha": alpha, "multiplier": round(float(ev["q"]), 3),
                      "method": "adaptive conformal floor on the recommended action",
                      "backtest_violation": (meta.get("backtest") or {}).get("floor_violation_adaptive", {}).get(f"{alpha:.2f}")},
        "assumptions": {"transport_per_q_km": e.transport_per_q_km, "road_factor": e.road_factor, "market_fee": e.market_fee,
                        "handling_per_trip": e.handling, "spoilage_per_day": e.spoilage_per_day,
                        "silent_price_factor": e.silent_price_factor, "farmgate_factor": e.farmgate_factor,
                        "transport_presets": TRANSPORT_PRESETS},
        "evidence": evidence_for(meta),
        "caveats": _caveats(meta, rec, ev),
        "stale_mandis": [registry.MANDIS[m].name for m, el in zip(ev["panel"].markets, ev["elig"]) if not el],
        "model": {"trained_through": meta["trained_through"], "mandis": meta["n_markets"], "training_days": meta["n_train_days"]},
    }


def _caveats(meta: Dict[str, Any], rec: Dict[str, Any], ev: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    bt = meta.get("backtest", {})
    if bt.get("evidence_level") == "limited" or meta.get("limited_evidence"):
        out.append("limited_evidence")
    if rec.get("is_sunday"):
        out.append("sale_on_sunday")
    if rec.get("kind") == "mandi" and rec.get("chance_open", 1) < 0.6:
        out.append("mandi_may_be_closed")
    if (ev["as_of"].date() + timedelta(days=1)) < (ev["decision_day"].date()):
        out.append("stale_data")
    return out


def matrix(crop: str, origin: Dict[str, Any], alpha: float = DEFAULT_ALPHA, transport_per_q_km: Optional[float] = None) -> Dict[str, Any]:
    """The full action-value grid for the trader desk."""
    try:
        ev = ENGINE.evaluate(crop, (origin["lat"], origin["lon"]), alpha, transport_per_q_km)
    except LookupError as exc:
        return {"status": "UNAVAILABLE", "crop": crop, "reason": str(exc)}
    panel = ev["panel"]
    M = panel.M
    rows = []
    for m in range(M):
        mid = panel.markets[m]
        md = registry.MANDIS[mid]
        base = m * N_HOLD
        rows.append({
            "mandi_id": mid, "mandi_name": md.name, "district": md.district, "offered": bool(ev["elig"][m]),
            "distance_km": round(float(ev["dist"][m]), 1), "last_price": round(float(ev["last_price"][m]), 0),
            "days_since_report": int(ev["stale"][m]),
            "expected_price": [round(float(x), 0) for x in ev["price"][m]],
            "expected_net": [round(float(x), 0) for x in ev["r_hat"][base:base + N_HOLD]],
            "floor": [round(float(x), 0) for x in ev["floor"][base:base + N_HOLD]],
            "chance_open": [round(float(x), 2) for x in ev["prep"][m]],
        })
    offered = ev["offered"]
    best = int(np.argmax(np.where(offered, ev["r_hat"], -np.inf)))
    bm, bk = E.decode(best, M)
    return {
        "status": "OK", "crop": crop, "as_of": str(ev["as_of"].date()), "decision_day": str(ev["decision_day"].date()),
        "alpha": alpha, "origin": {k: origin[k] for k in origin if k in ("lat", "lon", "kind", "label", "nearest_district")},
        "mandis": rows, "farm_gate": {"expected_net": round(float(ev["r_hat"][-1]), 0), "floor": round(float(ev["floor"][-1]), 0)},
        "best": {"mandi_id": panel.markets[bm] if bm is not None else None, "hold_days": int(bk)},
        "assumptions": {"transport_per_q_km": ev["econ"].transport_per_q_km, "spoilage_per_day": ev["econ"].spoilage_per_day,
                        "market_fee": ev["econ"].market_fee, "handling_per_trip": ev["econ"].handling},
        "error_scale": {"multiplier": round(float(ev["q"]), 3)},
    }


def crops_summary() -> Dict[str, Any]:
    out = []
    for crop in ENGINE.crops():
        meta = ENGINE.meta(crop)
        out.append({"crop": crop, "mandis": meta["n_markets"], "trained_through": meta["trained_through"],
                    "limited_evidence": bool(meta.get("limited_evidence") or meta["backtest"].get("evidence_level") == "limited"),
                    "evidence": evidence_for(meta)})
    return {"crops": out, "alphas": list(ALPHAS), "default_alpha": DEFAULT_ALPHA, "origins": [
        {"id": k, "name": registry.DISTRICTS[k].name, "name_kn": registry.DISTRICTS[k].name_kn, "name_hi": registry.DISTRICTS[k].name_hi,
         "lat": v[0], "lon": v[1]} for k, v in ORIGINS.items()], "transport_presets": TRANSPORT_PRESETS}


def calibration(crop: str) -> Dict[str, Any]:
    meta = ENGINE.meta(crop.lower())
    if meta is None:
        return {"status": "UNAVAILABLE", "crop": crop, "reason": f"No market-choice model for '{crop}'."}
    bt = meta["backtest"]
    if bt.get("status") != "OK":
        return {"status": "UNAVAILABLE", "crop": crop, "reason": f"Backtest {bt.get('status')}."}
    return {"status": "OK", "crop": crop, "trained_through": meta["trained_through"], "alphas": meta["alphas"],
            "multiplier_q": meta["q"], "calibration_scores": meta["calibration_scores"], "backtest": bt}


def research_evidence() -> Dict[str, Any]:
    if not EVIDENCE_FILE.exists():
        return {"status": "UNAVAILABLE", "reason": "Research evidence has not been exported."}
    return {"status": "OK", **json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))}


def explain_recommendation(crop: str, origin: Dict[str, Any], quantity: float, alpha: float = DEFAULT_ALPHA,
                           transport_per_q_km: Optional[float] = None, lang: str = "en", use_llm: bool = True,
                           model: Optional[str] = None) -> Dict[str, Any]:
    """The recommendation plus a plain-language "why", in the reader's language.

    The decision is made by `recommend`; the explanation can neither change it nor insert a number of its own
    (see `intelligence/explain.py`).
    """
    from mandisense_ai.intelligence.explain import explain
    from mandisense_ai.shock.service import radar

    rec = recommend(crop, origin, quantity, alpha, transport_per_q_km)
    if rec.get("status") != "OK":
        return rec
    district = origin.get("nearest_district")
    item = None
    try:
        out = radar("farmer", crop, district) if district else {}
        item = (out.get("items") or [None])[0] if out.get("status") == "OK" else None
    except Exception:  # the shock radar enriches the explanation; it must never block it
        item = None
    return {"status": "OK", "crop": crop, "recommended": rec["recommended"], "explanation": explain(rec, item, lang, use_llm, model),
            "shock": item}
