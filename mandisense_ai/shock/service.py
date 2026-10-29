"""
Live supply-shock radar.

For every crop and district it reads today's arrivals against the series' own
trailing norm, attaches what the event study found usually follows such a shock
(with its evidence tier), the same-crop gap to neighbouring districts and how
fast such gaps have closed, and, for traders, any cross-crop link that is
currently armed.

Responses are structured fields and codes, never composed sentences; the
frontend and the language model compose the wording. Nothing is fitted here.

Audience rules (one place to change them):
  * farmer  - a price-response claim is shown only if its tier is in
              `FARMER_TIERS`; the facts (how much more is arriving, the
              neighbour price gap) are always shown, because they are
              observations, not model claims. Cross-crop links are not shown.
  * trader  - everything, each with its tier, sample size and the smallest
              effect the sample could have detected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry, world
from mandisense_ai.farmer.transmission import arrival_surprise, neighbour_signal_series
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

STUDY_PATH = Path(__file__).resolve().parents[1] / "models" / "shock" / "shock_study.json"
FARMER_TIERS = {"ROBUST"}
RESPONSE_HORIZON = 7
GLUT_Z, ELEVATED_Z = 1.5, 1.0
MAX_AGE_DAYS = 10            # an arrival print older than this is context, not a live reading
_CACHE: Dict[str, Any] = {}


def study() -> Dict[str, Any]:
    if not STUDY_PATH.exists():
        return {"available": False}
    stamp = STUDY_PATH.stat().st_mtime
    hit = _CACHE.get("study")
    if hit and hit[0] == stamp:
        return hit[1]
    data = {"available": True, **json.loads(STUDY_PATH.read_text(encoding="utf-8"))}
    _CACHE["study"] = (stamp, data)
    return data


def _state(z: Optional[float]) -> Dict[str, Any]:
    if z is None or not np.isfinite(z):
        return {"state": "unknown", "direction": None}
    if z >= GLUT_Z:
        return {"state": "glut", "direction": "glut"}
    if z >= ELEVATED_Z:
        return {"state": "elevated", "direction": "glut"}
    if z <= -GLUT_Z:
        return {"state": "squeeze", "direction": "squeeze"}
    if z <= -ELEVATED_Z:
        return {"state": "low", "direction": "squeeze"}
    return {"state": "normal", "direction": None}


def _response(crop: str, direction: Optional[str], horizon: int = RESPONSE_HORIZON) -> Optional[Dict[str, Any]]:
    s = study()
    if not s.get("available") or direction is None:
        return None
    for r in s["own_crop"]["results"]:
        if r["crop"] == crop and r["direction"] == direction and r["horizon"] == horizon:
            if r["status"] != "OK":
                return {"status": r["status"], "n": r.get("n", 0), "tier": "NONE"}
            return {
                "status": "OK", "direction": direction, "horizon_days": horizon, "n_episodes": r["n"], "tier": r["tier"],
                "effect_pct": round(100 * r["effect"], 1), "ci_pct": [round(100 * r["ci"][0], 1), round(100 * r["ci"][1], 1)],
                "typical_change_pct": round(100 * r["raw_median"], 1), "range_pct": [round(100 * r["p10"], 1), round(100 * r["p90"], 1)],
                "share_price_fell": round(r["share_down"], 2), "min_detectable_pct": round(100 * (r["mde"] or 0), 1),
                "placebo_p": r["placebo_p"], "holm_p": r.get("holm_p"),
            }
    return None


def _gap(obs: pd.DataFrame, crop: str, district: str) -> Optional[Dict[str, Any]]:
    gap = neighbour_signal_series(obs, crop, district)
    if gap is None or gap.empty:
        return None
    s = study()
    half_lives, closing = [], 0
    pairs = (s.get("district_gaps") or {}).get("pairs", []) if s.get("available") else []
    mine = [p for p in pairs if p["crop"] == crop and district in (p["from"], p["to"])]
    for p in mine:
        half_lives.append(p["half_life_weeks"])
        closing += 1 if p.get("closes") else 0
    sig = ((s.get("neighbour_signal") or {}).get(f"{crop}/{district}") or {}) if s.get("available") else {}
    latest = float(gap.iloc[-1])
    return {
        "neighbours_dearer_by_pct": round(100 * (np.exp(latest) - 1), 1),
        "mean_gap_pct_last_8w": round(100 * (np.exp(float(gap.tail(8).mean())) - 1), 1),
        "median_half_life_weeks": round(float(np.median(half_lives)), 1) if half_lives else None,
        "pairs_tested": len(mine), "pairs_closing": closing,
        "predicts_next_week": bool(sig.get("earns_signal")) if sig else None,
        "as_of": str(gap.index[-1].date()),
    }


def _mandi_levels(crop: str, district: str) -> List[Dict[str, Any]]:
    try:
        from mandisense_ai.market_choice.panel import load_long

        long = load_long()
    except Exception:
        return []
    out = []
    for m in registry.mandis_in(district):
        sub = long[(long["crop"] == crop) & (long["mandi_id"] == m.id)].rename(columns={"price": "modal_price"})
        sub = sub.dropna(subset=["arrivals"])
        if len(sub) < 60:
            continue
        z = arrival_surprise(sub[["date", "arrivals"]]).dropna()
        if z.empty:
            continue
        out.append({"mandi_id": m.id, "mandi_name": m.name, "z": round(float(z.iloc[-1]), 2), "as_of": str(z.index[-1].date()),
                    **_state(float(z.iloc[-1]))})
    return out


def _item(obs: pd.DataFrame, crop: str, district: str, end: pd.Timestamp, audience: str) -> Optional[Dict[str, Any]]:
    series = world.district_series(crop, district)
    if series.empty or len(series) < 90:
        return None
    z = arrival_surprise(series).dropna()
    if z.empty:
        return None
    s = series.sort_values("date").set_index("date")
    la = np.log(s["arrivals"].where(s["arrivals"] > 0))
    mu = la.rolling(60, min_periods=30).mean().shift(1)
    last_z = float(z.iloc[-1])
    age = int((end - z.index[-1]).days)
    st = _state(last_z) if age <= MAX_AGE_DAYS else {"state": "stale", "direction": None}
    ratio = float(np.exp(la.loc[z.index[-1]] - mu.loc[z.index[-1]])) if np.isfinite(mu.loc[z.index[-1]]) else None
    price = float(s["modal_price"].iloc[-1])
    week_ago = s["modal_price"].loc[:s.index[-1] - pd.Timedelta(days=7)]
    chg7 = float(np.log(price / week_ago.iloc[-1])) if len(week_ago) else None

    resp = _response(crop, st["direction"])
    allowed = resp is not None and resp.get("status") == "OK" and (audience == "trader" or resp["tier"] in FARMER_TIERS)
    if resp is not None and resp.get("status") == "OK" and not allowed:
        note = "mixed_history"
    elif resp is None:
        note = "no_shock"
    elif resp.get("status") != "OK":
        note = "too_few_episodes"
    else:
        note = "reliable" if resp["tier"] == "ROBUST" else "suggestive"
    return {
        "crop": crop, "district": district, "district_name": registry.DISTRICTS[district].name,
        "arrivals": {"z": round(last_z, 2), "times_normal": round(ratio, 2) if ratio else None, "as_of": str(z.index[-1].date()),
                     "age_days": age, **st},
        "price": {"modal": round(price, 0), "change_7d_pct": round(100 * (np.exp(chg7) - 1), 1) if chg7 is not None else None,
                  "as_of": str(s.index[-1].date())},
        "response": resp if allowed else None, "response_note": note,
        "response_evidence": ({"tier": resp["tier"], "n_episodes": resp.get("n_episodes", resp.get("n")),
                               "min_detectable_pct": resp.get("min_detectable_pct")} if (resp and audience == "trader") else None),
        "gap": _gap(obs, crop, district),
        "mandis": _mandi_levels(crop, district) if audience == "trader" else [],
    }


def _edge_tier(e: Dict[str, Any]) -> str:
    if e.get("published"):
        return "ROBUST"
    if e.get("status") == "OK" and e.get("ci") and (e["ci"][0] > 0 or e["ci"][1] < 0):
        return "SUGGESTIVE"
    return "NONE"


def cross_crop_watch(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cross-crop links the data supports (or does not), and which are armed by today's shocks."""
    s = study()
    if not s.get("available") or not s.get("cross_commodity"):
        return {"status": "UNAVAILABLE"}
    edges = s["cross_commodity"]["edges"]
    state = {(i["crop"], i["district"]): i["arrivals"] for i in items}
    out = []
    for e in edges:
        tier = _edge_tier(e)
        armed = [d for d in e.get("districts", []) if (state.get((e["source"], d)) or {}).get("direction") == e["shock"]]
        out.append({"source": e["source"], "target": e["target"], "shock": e["shock"], "tier": tier, "n_episodes": e.get("n_episodes"),
                    "effect_pct": round(100 * e["effect"], 1) if e.get("effect") is not None else None,
                    "ci_pct": [round(100 * e["ci"][0], 1), round(100 * e["ci"][1], 1)] if e.get("ci") else None,
                    "min_detectable_pct": round(100 * e["min_detectable_effect"], 1) if e.get("min_detectable_effect") else None,
                    "placebo_p": e.get("placebo_p"), "armed_districts": armed, "armed": bool(armed)})
    out.sort(key=lambda x: (x["tier"] != "ROBUST", x["tier"] != "SUGGESTIVE", not x["armed"]))
    return {"status": "OK", "n_tested": len(edges), "n_robust": sum(x["tier"] == "ROBUST" for x in out),
            "n_suggestive": sum(x["tier"] == "SUGGESTIVE" for x in out), "links": out}


def radar(audience: str = "trader", crop: Optional[str] = None, district: Optional[str] = None) -> Dict[str, Any]:
    obs = world.district_observations()
    if obs.empty:
        return {"status": "UNAVAILABLE", "reason": "No district observations; run the farmer build."}
    end = obs["date"].max()
    pairs = sorted({(r.commodity, r.mandi_id) for r in obs[["commodity", "mandi_id"]].drop_duplicates().itertuples()})
    items = []
    for c, d in pairs:
        if (district and d != district) or d not in registry.DISTRICTS:
            continue
        it = _item(obs, c, d, end, audience)
        if it:
            items.append(it)
    # cross-crop links are armed by OTHER crops' shocks, so they are evaluated on every crop before the output is narrowed
    watch = cross_crop_watch(items) if audience == "trader" else None
    if crop:
        items = [i for i in items if i["crop"] == crop]
    s = study()
    out: Dict[str, Any] = {
        "status": "OK", "audience": audience, "as_of": str(end.date()), "items": items,
        "study": {"available": bool(s.get("available")), "generated_at": s.get("generated_at"),
                  "own_crop": {k: s["own_crop"][k] for k in ("n_tested", "n_robust", "n_suggestive", "rules")} if s.get("available") else None,
                  "farmer_tiers": sorted(FARMER_TIERS)},
    }
    if audience == "trader":
        out["cross_crop"] = watch
    return out


def study_table(audience: str = "trader") -> Dict[str, Any]:
    s = study()
    if not s.get("available"):
        return {"status": "UNAVAILABLE", "reason": "The shock study has not been built (scripts/build_shock_study.py)."}
    rows = [r for r in s["own_crop"]["results"] if r["status"] == "OK"]
    if audience == "farmer":
        rows = [r for r in rows if r["tier"] in FARMER_TIERS]
    return {"status": "OK", "generated_at": s["generated_at"], "data": s["data"], "rules": s["own_crop"]["rules"],
            "n_tested": s["own_crop"]["n_tested"], "n_robust": s["own_crop"]["n_robust"], "n_suggestive": s["own_crop"]["n_suggestive"],
            "results": [{"crop": r["crop"], "direction": r["direction"], "horizon_days": r["horizon"], "n_episodes": r["n"], "tier": r["tier"],
                         "effect_pct": round(100 * r["effect"], 1), "ci_pct": [round(100 * r["ci"][0], 1), round(100 * r["ci"][1], 1)],
                         "typical_change_pct": round(100 * r["raw_median"], 1), "share_price_fell": round(r["share_down"], 2),
                         "min_detectable_pct": round(100 * (r["mde"] or 0), 1), "placebo_p": r["placebo_p"], "holm_p": r.get("holm_p")}
                        for r in rows]}
