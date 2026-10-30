"""
Insights built on the market-choice engine.

    breakdown        why the advice is what it is: price, fee, spoilage, transport and handling for the recommended
                     action against the usual alternatives
    simulate         what-if costs and the exact cost at which the advice changes
    crowd            what happens when many farmers follow the same advice, and an allocation that avoids it
    reporting_value  what silent mandis cost a farmer who travels to them
    track_record     how the advice has actually done on days it did not see

Everything is computed from the served engine and the ingested panel. Nothing here fits a model at request time.
Assumptions the user can change are returned with the answer; assumptions that are scenarios (price impact) say so.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry
from mandisense_ai.market_choice import econ as E
from mandisense_ai.market_choice.config import ARTIFACT_DIR, DEFAULT_ALPHA, K_MAX, N_HOLD, economics_for
from mandisense_ai.market_choice.engine import ENGINE
from mandisense_ai.market_choice.service import WEEKDAYS, _option

NEG = -1e12
TRANSPORT_GRID = [round(0.1 * i, 2) for i in range(1, 31)]          # Rs per quintal-km, 0.1 .. 3.0
SPOILAGE_GRID = [round(0.005 * i, 3) for i in range(0, 17)]         # per day, 0 .. 8%
PRICE_FLEXIBILITY = 0.115      # d log price / d log arrivals, within mandi and month (tomato panel; see `crowd`)
CLOSED_DAY_SHARE = 0.9       # a weekday on which a mandi is silent at least this often is treated as a closed day
MIN_YARD_QUINTALS = 10.0       # a yard is never treated as smaller than this when scaling price impact
QUINTALS_PER_TONNE = 10.0


# ───────────────────────────────────────────────────────────────────────── helpers
def _evaluate(crop: str, origin: Dict[str, Any], alpha: float, transport: Optional[float]) -> Optional[Dict[str, Any]]:
    try:
        return ENGINE.evaluate(crop, (origin["lat"], origin["lon"]), alpha, transport)
    except LookupError:
        return None


def _unavailable(crop: str, why: str = "No market-choice engine for this crop.") -> Dict[str, Any]:
    return {"status": "UNAVAILABLE", "crop": crop, "reason": why}


def _baseline_actions(ev: Dict[str, Any]) -> Dict[str, int]:
    """Action indices of the recommendation and the three alternatives a farmer would otherwise use."""
    elig, A = ev["elig"], E.n_actions(ev["panel"].M)
    offered = ev["offered"]
    best = int(np.argmax(np.where(offered, ev["r_hat"], -np.inf)))
    near = int(np.argmin(np.where(elig, ev["dist"], np.inf))) * N_HOLD
    high = int(np.argmax(np.where(elig, ev["last_price"], -np.inf))) * N_HOLD
    return {"recommended": best, "nearest_today": near, "highest_yesterday": high, "farm_gate": A - 1}


def _components(ev: Dict[str, Any], a: int, e) -> Dict[str, Any]:
    """Per-quintal arithmetic of one action: expected price, minus fee, spoilage, transport and handling."""
    m, k = E.decode(a, ev["panel"].M)
    if m is None:
        price = float(ev["gate_price"])
        discount = (1.0 - e.farmgate_factor) * price
        parts = [("price", price), ("farm_gate_discount", -discount)]
        net = price - discount
    else:
        price = float(ev["price"][m, k])
        fee = e.market_fee * price
        spoil = (1.0 - e.market_fee) * price * (1.0 - (1.0 - e.spoilage_per_day) ** k)
        transport = float(e.transport_per_q_km * e.road_factor * ev["dist"][m])
        parts = [("price", price), ("fee", -fee), ("spoilage", -spoil), ("transport", -transport), ("handling", -e.handling)]
        net = price - fee - spoil - transport - e.handling
    return {"parts": [{"key": k_, "value": round(v, 1)} for k_, v in parts], "net": round(net, 1)}


# ───────────────────────────────────────────────────────────────────────── 1. why this mandi
def breakdown(crop: str, origin: Dict[str, Any], quantity: float = 10.0, alpha: float = DEFAULT_ALPHA,
              transport: Optional[float] = None) -> Dict[str, Any]:
    """The arithmetic behind the advice, for the recommended action and the three usual alternatives."""
    ev = _evaluate(crop, origin, alpha, transport)
    if ev is None:
        return _unavailable(crop)
    e = ev["econ"]
    acts = _baseline_actions(ev)
    out = {}
    for name, a in acts.items():
        opt = _option(ev, a, quantity)
        comp = _components(ev, a, e)
        assert abs(comp["net"] - float(ev["r_hat"][a])) < 1.5, "breakdown must reproduce the served net revenue"
        out[name] = {"option": opt, **comp}
    rec, near = out["recommended"], out["nearest_today"]
    delta = {p["key"]: round(p["value"] - next((q["value"] for q in near["parts"] if q["key"] == p["key"]), 0.0), 1) for p in rec["parts"]}
    return {"status": "OK", "crop": crop, "as_of": str(ev["as_of"].date()), "quantity_quintals": quantity,
            "assumptions": {"transport_per_q_km": e.transport_per_q_km, "road_factor": e.road_factor, "market_fee": e.market_fee,
                            "handling_per_trip": e.handling, "spoilage_per_day": e.spoilage_per_day, "farmgate_factor": e.farmgate_factor},
            "note": "The expected price already includes the chance that the mandi reports no price, because the model is trained on what a farmer actually received.",
            "options": out, "recommended_vs_nearest": delta}


# ───────────────────────────────────────────────────────────────────────── 2. what-if
def _scenario(ev: Dict[str, Any], e, max_hold: int) -> Dict[str, Any]:
    price, dist = ev["price"], ev["dist"]
    r = E.revenue_from_prices(price[None], np.array([ev["gate_price"]]), dist, e)[0]
    a_all = np.arange(len(r))
    mi = a_all // N_HOLD
    hold = np.where(a_all < ev["panel"].M * N_HOLD, a_all % N_HOLD, 0)
    allowed = ev["offered"] & (hold <= max_hold)
    best = int(np.argmax(np.where(allowed, r, -np.inf)))
    return {"r_hat": r, "floor": r - ev["q"] * ev["sigma"], "best": best, "allowed": allowed, "mi": mi}


def _label(ev: Dict[str, Any], a: int, lang: str = "en") -> Dict[str, Any]:
    m, k = E.decode(a, ev["panel"].M)
    if m is None:
        return {"kind": "farm_gate", "mandi_id": None, "name": "Farm gate", "name_kn": "ಜಮೀನಿನಲ್ಲೇ ಮಾರಾಟ", "name_hi": "खेत पर बिक्री", "hold_days": 0}
    md = registry.MANDIS[ev["panel"].markets[m]]
    return {"kind": "mandi", "mandi_id": md.id, "name": md.name, "name_kn": md.name_kn, "name_hi": md.name_hi, "hold_days": int(k)}


def simulate(crop: str, origin: Dict[str, Any], quantity: float = 10.0, alpha: float = DEFAULT_ALPHA,
             transport: Optional[float] = None, spoilage: Optional[float] = None, market_fee: Optional[float] = None,
             handling: Optional[float] = None, max_hold: int = K_MAX) -> Dict[str, Any]:
    """Re-price every action under the farmer's own costs and say where the advice changes.

    Prices and the chance a mandi reports come from the served model and do not depend on the farmer's costs, so the
    answer is exact for the stated costs. The floor keeps the error scale calibrated at the default costs: it is
    indicative once the costs move far from the defaults.
    """
    ev = _evaluate(crop, origin, alpha, None)
    if ev is None:
        return _unavailable(crop)
    max_hold = int(np.clip(max_hold, 0, K_MAX))
    base_e = economics_for(crop)
    over = {k: v for k, v in dict(transport_per_q_km=transport, spoilage_per_day=spoilage, market_fee=market_fee, handling=handling).items() if v is not None}
    e = base_e.but(**over)
    base = _scenario(ev, base_e, K_MAX)
    now = _scenario(ev, e, max_hold)

    def pack(sc, econ):
        ev2 = {**ev, "r_hat": sc["r_hat"], "floor": sc["floor"], "econ": econ}
        return _option(ev2, sc["best"], quantity)

    def sweep(param: str, grid: List[float]) -> Dict[str, Any]:
        pts, flips, prev = [], [], None
        for x in grid:
            sc = _scenario(ev, e.but(**{param: x}), max_hold)
            lab = _label(ev, sc["best"])
            pts.append({"x": x, "mandi_id": lab["mandi_id"], "name": lab["name"], "hold_days": lab["hold_days"], "net": round(float(sc["r_hat"][sc["best"]]), 0)})
            if prev is not None and sc["best"] != prev[1]:
                flips.append({"at": x, "from": {k: prev[2][k] for k in ("mandi_id", "name", "name_kn", "name_hi", "hold_days")},
                              "to": {k: lab[k] for k in ("mandi_id", "name", "name_kn", "name_hi", "hold_days")}})
            prev = (x, sc["best"], lab)
        return {"param": param, "points": pts, "flips": flips}

    changed = now["best"] != base["best"]
    return {"status": "OK", "crop": crop, "as_of": str(ev["as_of"].date()), "quantity_quintals": quantity,
            "scenario": {"transport_per_q_km": e.transport_per_q_km, "spoilage_per_day": e.spoilage_per_day, "market_fee": e.market_fee,
                         "handling_per_trip": e.handling, "max_hold_days": max_hold},
            "defaults": {"transport_per_q_km": base_e.transport_per_q_km, "spoilage_per_day": base_e.spoilage_per_day,
                         "market_fee": base_e.market_fee, "handling_per_trip": base_e.handling},
            "recommended": pack(now, e), "default_recommended": pack(base, base_e), "changed": changed,
            "sweeps": {"transport": sweep("transport_per_q_km", TRANSPORT_GRID), "spoilage": sweep("spoilage_per_day", SPOILAGE_GRID)},
            "note": "Prices come from the served model. The guaranteed floor keeps the default-cost error scale, so it is indicative when costs differ a lot."}


# ───────────────────────────────────────────────────────────────────────── 3. crowds
def _daily_arrivals(crop: str, markets: List[str]) -> Dict[str, float]:
    from mandisense_ai.farmer import world

    p = pd.read_parquet(world.MARKET_PANEL)
    p["date"] = pd.to_datetime(p["date"])
    p = p[(p["crop"] == crop) & p["mandi_id"].isin(markets) & (p["arrivals"] > 0)]
    p = p[p["date"] >= p["date"].max() - pd.Timedelta(days=365)]
    return {m: float(g["arrivals"].median()) * QUINTALS_PER_TONNE for m, g in p.groupby("mandi_id")}


def crowd(crop: str, origin: Dict[str, Any], farmers: int = 200, quantity: float = 10.0, alpha: float = DEFAULT_ALPHA,
          flexibility: float = PRICE_FLEXIBILITY) -> Dict[str, Any]:
    """What if `farmers` farmers, each with `quantity` quintals, all take the advice?

    A yard's price falls when it receives more than it usually does: P(x) = P (1 + x / A)^(-b), where A is the yard's
    median daily arrivals over the last year and b is the price flexibility. b = 0.115 is the within-yard, within-month
    association of log price with log arrivals in the tomato panel (standard error 0.023); it is an association, not a
    causal estimate, so it is a scenario and the response lets the caller change it. Three policies are compared: everyone
    takes the single best action; everyone goes to the nearest yard; and a coordinated split that maximises the group's
    total revenue (greedy on marginal revenue), which is also returned as the probability with which each farmer is advised
    each action.
    """
    ev = _evaluate(crop, origin, alpha, None)
    if ev is None:
        return _unavailable(crop)
    farmers = int(np.clip(farmers, 1, 20000))
    flexibility = float(np.clip(flexibility, 0.0, 1.0))
    panel, e = ev["panel"], ev["econ"]
    M, A_n = panel.M, E.n_actions(panel.M)
    arr = _daily_arrivals(crop, list(panel.markets))
    cap = np.array([max(arr.get(m, 0.0), MIN_YARD_QUINTALS) for m in panel.markets])
    disc = E.hold_discount(e)
    trip = E.trip_cost(ev["dist"], e)
    price = ev["price"]

    def net(a: int, load: float) -> float:
        m, k = E.decode(a, M)
        if m is None:
            return float(e.farmgate_factor * ev["gate_price"])
        return float(price[m, k] * (1.0 + load / cap[m]) ** (-flexibility) * disc[k] - trip[m])

    total_q = farmers * quantity
    allowed = [a for a in range(A_n) if ev["offered"][a]]

    def revenue(loads: Dict[int, float]) -> float:
        return sum(x * net(a, x) for a, x in loads.items() if x > 0)

    acts = _baseline_actions(ev)
    all_best = {acts["recommended"]: total_q}
    all_near = {acts["nearest_today"]: total_q}
    # coordinated split: hand out the quantity in steps, each to the action with the best marginal revenue
    steps = int(min(2000, max(20, farmers)))
    step = total_q / steps
    loads: Dict[int, float] = {a: 0.0 for a in allowed}
    for _ in range(steps):
        gains = {a: (loads[a] + step) * net(a, loads[a] + step) - loads[a] * net(a, loads[a]) for a in allowed}
        loads[max(gains, key=gains.get)] += step
    shares = {a: x / total_q for a, x in loads.items() if x / total_q >= 0.005}
    norm = sum(shares.values())

    def per_farmer(loads_: Dict[int, float]) -> float:
        return revenue(loads_) / total_q

    single = float(ev["r_hat"][acts["recommended"]])
    m_best = E.decode(acts["recommended"], M)[0]
    drop_best = (1.0 + total_q / cap[m_best]) ** (-flexibility) if m_best is not None else 1.0
    split = sorted(({"label": _label(ev, a), "share": round(s / norm, 3), "quintals": round(s / norm * total_q, 0),
                     "net_per_q": round(net(a, loads[a]), 0), "price_drop_pct": round(100 * (1 - (1.0 + loads[a] / cap[E.decode(a, M)[0]]) ** (-flexibility)), 1) if E.decode(a, M)[0] is not None else 0.0}
                    for a, s in shares.items()), key=lambda r: -r["share"])
    return {"status": "OK", "crop": crop, "as_of": str(ev["as_of"].date()), "farmers": farmers, "quantity_per_farmer": quantity, "total_quintals": total_q,
            "price_flexibility": flexibility, "flexibility_note": "Scenario: association of price with arrivals within a mandi and month in the panel; not a causal estimate.",
            "recommended": _label(ev, acts["recommended"]),
            "recommended_yard_daily_arrivals_q": round(float(cap[m_best]), 0) if m_best is not None else None,
            "alone": {"net_per_q": round(single, 0)},
            "everyone_follows_best": {"net_per_q": round(per_farmer(all_best), 0), "price_drop_pct": round(100 * (1 - drop_best), 1)},
            "everyone_goes_nearest": {"net_per_q": round(per_farmer(all_near), 0)},
            "coordinated": {"net_per_q": round(per_farmer(loads), 0), "split": split},
            "gain_coordinated_vs_everyone_best_per_q": round(per_farmer(loads) - per_farmer(all_best), 0),
            "gain_total_rs": round((per_farmer(loads) - per_farmer(all_best)) * total_q, 0)}


# ───────────────────────────────────────────────────────────────────────── 4. silence tax
def reporting_value(crop: str, window_days: int = 365) -> Dict[str, Any]:
    """What a silent mandi costs a farmer who travels to it.

    A farmer who goes to mandi m gets its price if it reports and, if it is silent, the silent-price fraction of the day's
    mean price at the mandis that did report (the same assumption the engine is trained on). The expected loss per quintal
    from m's silence is P(silent) x (mean price when it reports - silent fraction x mean day price). It is computed from the
    last `window_days` of the ingested panel, per mandi and per weekday. "Silent" means no price was reported, which may or
    may not mean the mandi was closed.
    """
    from mandisense_ai.farmer import world

    p = pd.read_parquet(world.MARKET_PANEL)
    p["date"] = pd.to_datetime(p["date"])
    p = p[p["crop"] == crop]
    if p.empty:
        return _unavailable(crop, "No prices for this crop.")
    end = p["date"].max()
    start = end - pd.Timedelta(days=window_days)
    p = p[p["date"] >= start]
    counts = p.groupby("mandi_id")["date"].nunique()
    markets = [m for m, n in counts.items() if n >= 60]
    cal = pd.date_range(start, end)
    day_mean = p.groupby("date")["price"].mean().reindex(cal)
    phi = economics_for(crop).silent_price_factor
    rows = []
    for m in markets:
        g = p[p["mandi_id"] == m].drop_duplicates("date").set_index("date")["price"]
        rep = pd.Series(cal.isin(g.index), index=cal)
        wd = [1.0 - float(rep[cal.dayofweek == d].mean()) for d in range(7)]
        closed = [d for d in range(7) if wd[d] >= CLOSED_DAY_SHARE]          # structurally closed: farmers know these days
        open_mask = ~np.isin(cal.dayofweek, closed)
        silent_open = 1.0 - float(rep[open_mask].mean()) if open_mask.any() else 0.0   # surprise silence on the other days
        mean_rep = float(g.mean())
        fb_days = rep.values & open_mask
        fallback = float(phi * day_mean[fb_days].mean()) if fb_days.any() else None
        loss = silent_open * max(mean_rep - fallback, 0.0) if fallback is not None else None
        md = registry.MANDIS.get(m)
        open_wd = [d for d in range(7) if d not in closed]
        worst = max(open_wd, key=lambda d: wd[d]) if open_wd else int(np.argmax(wd))
        rows.append({"mandi_id": m, "name": md.name if md else m, "name_kn": md.name_kn if md else m, "name_hi": md.name_hi if md else m,
                     "district": md.district if md else None, "reported_share": round(float(rep.mean()), 3),
                     "silent_share_open_days": round(silent_open, 3), "closed_weekdays": [WEEKDAYS[d] for d in closed],
                     "silent_by_weekday": [round(x, 2) for x in wd], "worst_open_weekday": WEEKDAYS[worst], "worst_open_weekday_silent": round(wd[worst], 2),
                     "mean_price": round(mean_rep, 0), "expected_loss_per_q": round(loss, 0) if loss is not None else None,
                     "expected_loss_pct": round(100 * loss / mean_rep, 1) if loss is not None and mean_rep else None})
    rows.sort(key=lambda r: -(r["expected_loss_per_q"] or 0))
    served = sum(r["reported_share"] for r in rows) / max(len(rows), 1)
    total_loss = sum(r["expected_loss_per_q"] or 0 for r in rows) / max(len(rows), 1)
    return {"status": "OK", "crop": crop, "window": [str(start.date()), str(end.date())], "silent_price_factor": phi,
            "mandis": rows, "mean_reported_share": round(served, 3), "mean_expected_loss_per_q": round(total_loss, 0),
            "note": "A day with no reported price is called silent; it may be a closed mandi or a missed upload. Weekdays silent on 90% or more of days are treated as closed days that farmers already know, so the loss counts only surprise silence on the other days. Losses use the engine's assumption that a silent mandi pays the silent-price fraction of the day's mean price."}


# ───────────────────────────────────────────────────────────────────────── 5. track record
def track_record(crop: str) -> Dict[str, Any]:
    path = ARTIFACT_DIR / crop / "track_record.json"
    if not path.exists():
        return _unavailable(crop, "No track record has been built for this crop (scripts/build_track_record.py).")
    rec = json.loads(path.read_text(encoding="utf-8"))
    meta = ENGINE.meta(crop) or {}
    return {"status": "OK", **rec, "evidence_level": (meta.get("backtest") or {}).get("evidence_level")}
