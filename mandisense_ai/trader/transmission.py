"""
Transmission analytics for the trader surface, built on the farmer data
world's real district data (mandisense_ai/farmer/transmission.py).

This is a separate, additional view of the same statistically-tested
results the farmer screens read -- it does not touch, read or modify
mandisense_ai/spillover/ or mandisense_ai/trader/arbitrage.py, which keep
running on their own existing pipeline and data exactly as before.

Two products, because a trader's two questions are different from a
farmer's one:

  cross_commodity_matrix()  "does a shock in one crop move another crop?"
                            every one of the 40 tested edges, shown with its
                            full evidence (effect, interval, FDR, placebo,
                            stability) -- not just the edges that passed,
                            because a trader deciding whether to act on a
                            pattern needs to see how strong the filter was.

  gap_arbitrage()           "is there a same-crop price gap between two
                            districts worth hauling for, and how fast does
                            it usually close?" -- the quantitative sibling of
                            the farmer-facing gap_note() in
                            mandisense_ai/farmer/dashboard.py, projected
                            forward over an actual trip time instead of
                            reported as a plain-language nudge.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from mandisense_ai.farmer import registry, world
from mandisense_ai.farmer.transmission import _weekly_log_price

TRANSPORT_RATE_PER_QUINTAL_PER_KM = 3.5


def cross_commodity_matrix() -> Dict[str, Any]:
    """Every tested cross-commodity edge, with its full evidence trail."""
    matrix = world.transmission_matrix()
    if not matrix.get("available"):
        return {"status": "UNAVAILABLE", "reason": "Transmission analysis has not been built yet."}
    a = matrix["test_a_cross_commodity"]
    edges = []
    for e in a["edges"]:
        if e["status"] != "OK":
            edges.append({**e, "tier": "INSUFFICIENT_EVIDENCE"})
            continue
        if e["published"]:
            tier = "ROBUST"
        elif e.get("fdr_pass") and abs(e["pre_trend_t"]) < 2:
            tier = "SUGGESTIVE"
        else:
            tier = "NOT_SIGNIFICANT"
        edges.append({**e, "tier": tier})
    return {
        "status": "OK",
        "generated_at": matrix.get("generated_at"),
        "data_from": matrix["data"]["from"],
        "data_to": matrix["data"]["to"],
        "n_tested": a["n_tested"],
        "n_robust": a["n_published"],
        "edges": edges,
    }


def _current_gap(crop: str, from_district: str, to_district: str) -> Optional[float]:
    obs = world.district_observations()
    a = _weekly_log_price(obs, crop, from_district)
    b = _weekly_log_price(obs, crop, to_district)
    if a.empty or b.empty:
        return None
    joint = a.dropna().align(b.dropna(), join="inner")
    if joint[0].empty:
        return None
    return float(joint[1].iloc[-1] - joint[0].iloc[-1])


def gap_arbitrage(crop: str, quantity_quintals: float = 20.0, trip_days: int = 3) -> Dict[str, Any]:
    """Every district pair for `crop` whose gap is shown to close (Test B),
    with today's live gap projected forward to the trip's arrival date using
    the pair's own measured speed of closure, and the net value of hauling
    after transport.

    The structural mean gap is approximated by the pair's historical mean
    log gap (the same approximation the farmer-facing summary uses), not the
    OLS intercept ratio -a/kappa; stated here so the simplification is never
    silently assumed to be exact.
    """
    matrix = world.transmission_matrix()
    if not matrix.get("available"):
        return {"status": "UNAVAILABLE", "reason": "Transmission analysis has not been built yet."}
    crop = str(crop).strip().lower()
    pairs = [p for p in matrix["test_b_spatial_gaps"]["pairs"] if p["crop"] == crop and p["closes"]]
    if not pairs:
        return {"status": "UNAVAILABLE", "reason": f"No district pair for {crop} has a measured closing gap."}

    seen = set()
    rows: List[Dict[str, Any]] = []
    k_weeks = trip_days / 7.0
    for p in pairs:
        key = frozenset((p["from"], p["to"]))
        if key in seen:
            continue
        seen.add(key)
        gap_now = _current_gap(crop, p["from"], p["to"])
        if gap_now is None:
            continue
        mu = float(np.log1p(p["mean_gap_pct"] / 100.0))
        kappa = p["kappa"]
        projected = mu + (gap_now - mu) * (1 + kappa) ** k_weeks
        cheaper, dearer = (p["from"], p["to"]) if gap_now >= 0 else (p["to"], p["from"])
        gross_gap_pct = round((np.exp(abs(projected)) - 1) * 100, 2)
        dm_a, dm_b = registry.DISTRICTS.get(cheaper), registry.DISTRICTS.get(dearer)
        distance_km = round(registry.haversine_km((dm_a.lat, dm_a.lon), (dm_b.lat, dm_b.lon)), 1) if dm_a and dm_b else None
        transport_pct = None
        if distance_km is not None:
            anchor_price = world.district_series(crop, cheaper)
            if not anchor_price.empty:
                last_price = float(anchor_price.iloc[-1]["modal_price"])
                transport_cost = distance_km * TRANSPORT_RATE_PER_QUINTAL_PER_KM
                transport_pct = round(transport_cost / last_price * 100, 2) if last_price > 0 else None
        net_pct = round(gross_gap_pct - (transport_pct or 0.0), 2)
        rows.append({
            "cheaper_district": cheaper, "dearer_district": dearer,
            "current_gap_pct": round((np.exp(abs(gap_now)) - 1) * 100, 2),
            "projected_gap_pct_on_arrival": gross_gap_pct,
            "structural_mean_gap_pct": p["mean_gap_pct"],
            "half_life_weeks": p["half_life_weeks"], "kappa": kappa,
            "distance_km": distance_km, "transport_pct": transport_pct,
            "net_gross_margin_pct": net_pct, "worth_hauling": bool(net_pct > 0 and gross_gap_pct > 1.0),
            "trip_days": trip_days, "quantity_quintals": quantity_quintals,
        })

    rows.sort(key=lambda r: -r["net_gross_margin_pct"])
    return {"status": "OK", "crop": crop, "trip_days": trip_days, "pairs": rows,
            "assumption": "Structural mean gap approximated by the pair's historical mean log gap; "
                          f"transport at Rs.{TRANSPORT_RATE_PER_QUINTAL_PER_KM}/quintal/km."}
