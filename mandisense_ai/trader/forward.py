"""
Fair forward price: the number a trader and a farmer can both accept.

A trader agrees today to buy a farmer's crop for delivery in `h` days at a
fixed price F. The farmer gets certainty; the trader gets guaranteed
supply. Both sides need a price they can defend, and this is the one place
the farmer and trader halves of the product meet: it reads the same price
distribution and the same crop shelf-life table as the farmer tools.

The two sides' limits are computed separately, and a deal exists only when
they overlap:

  Farmer's floor  — what selling today would have paid, grossed up for the
      spoilage the crop suffers while it waits to be delivered:
          F_min = P_today / (1 − daily_loss)^h
      Below this the farmer is better off selling now.

  Trader's ceiling — the expected price at delivery, less a risk premium for
      the downside the trader is taking on:
          F_max = median_h × (1 − 0.25 × (median_h − p05_h) / median_h)
      A quarter of the distance to the 5th-percentile outcome is the price
      of carrying the tail. Above this the trader expects to lose money for
      bearing the risk.

  Fair price — the midpoint of [F_min, F_max] when it is non-empty (an equal
      split of the surplus), and both sides' surplus is shown so neither has
      to take the number on trust. When F_min > F_max there is no deal, and
      the result says which side rules it out.

The price distribution is the calibrated forecast band when a live forecast
exists, else the series' own historical returns (`trader/data.py`
`move_distribution`) — and which was used is stated in the result. On the
historical basis the quantity is an *expected* price with no conditioning on
today's signals, so the result is labelled accordingly.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from mandisense_ai.farmer.reference import shelf_profile
from mandisense_ai.trader.data import move_distribution, resolve

RISK_PREMIUM_FRACTION = 0.25
MAX_HORIZON_DAYS = 14


def fair_forward_price(
    commodity: str,
    mandi_id: str,
    horizon_days: int = 7,
    quantity_quintals: float = 10.0,
) -> Dict[str, Any]:
    c, m = resolve(commodity, mandi_id)
    if not (1 <= int(horizon_days) <= MAX_HORIZON_DAYS):
        return {"status": "ERROR", "reason": f"horizon_days must be between 1 and {MAX_HORIZON_DAYS}."}

    dist = move_distribution(c, m, int(horizon_days))
    if dist.get("status") != "OK":
        return {"status": "UNAVAILABLE", "commodity": c, "mandi_id": m, "reason": dist.get("reason")}

    profile = shelf_profile(c)
    if horizon_days > profile.shelf_life_days:
        return {
            "status": "UNSUITABLE",
            "commodity": c,
            "mandi_id": m,
            "reason": (
                f"{c} keeps about {profile.shelf_life_days} day(s) in ordinary storage; "
                f"a {horizon_days}-day forward contract would deliver a crop that has "
                "already spoiled. Use a shorter horizon."
            ),
        }

    base = float(dist["base_price"])
    q = dist["quantiles"]
    median_h = base * float(np.exp(q["p50"]))
    p05_h = base * float(np.exp(q["p05"]))
    p95_h = base * float(np.exp(q["p95"]))

    surviving = (1 - profile.daily_loss_pct / 100.0) ** int(horizon_days)
    farmer_floor = base / surviving
    risk_premium = RISK_PREMIUM_FRACTION * max(0.0, median_h - p05_h)
    trader_ceiling = median_h - risk_premium

    qty = float(quantity_quintals)
    overlap = farmer_floor <= trader_ceiling
    fair = (farmer_floor + trader_ceiling) / 2 if overlap else None

    result: Dict[str, Any] = {
        "status": "OK",
        "commodity": c,
        "mandi_id": m,
        "horizon_days": int(horizon_days),
        "quantity_quintals": qty,
        "basis": dist["method"],
        "basis_sample_size": dist.get("sample_size"),
        "base_price": round(base, 2),
        "base_date": dist["base_date"],
        "price_age_days": dist.get("age_days"),
        "expected_price_at_delivery": round(median_h, 2),
        "delivery_price_range_90": [round(p05_h, 2), round(p95_h, 2)],
        "farmer_floor": round(farmer_floor, 2),
        "trader_ceiling": round(trader_ceiling, 2),
        "risk_premium_per_quintal": round(risk_premium, 2),
        "spoilage_over_horizon_pct": round((1 - surviving) * 100, 2),
        "deal_possible": bool(overlap),
    }

    if overlap:
        result.update({
            "fair_price": round(fair, 2),
            "farmer_surplus_per_quintal": round(fair - farmer_floor, 2),
            "trader_surplus_per_quintal": round(trader_ceiling - fair, 2),
            "farmer_surplus_total": round((fair - farmer_floor) * qty, 2),
            "trader_surplus_total": round((trader_ceiling - fair) * qty, 2),
            "contract_value": round(fair * qty, 2),
        })
    else:
        gap = farmer_floor - trader_ceiling
        result["reason"] = (
            f"No overlap: the farmer needs at least ₹{farmer_floor:,.0f}/quintal to beat selling "
            f"today, but the trader's risk-adjusted ceiling is ₹{trader_ceiling:,.0f} "
            f"(₹{gap:,.0f} short). "
            + ("Spoilage while waiting is what pushes the farmer's floor up."
               if surviving < 0.97 else "The expected move is too small to cover the trader's risk.")
        )

    if dist["method"] == "historical_returns":
        result["caveat"] = (
            "No live forecast exists for this series, so the expected price and range come "
            "from its own two-year history of moves this long, not from today's conditions."
        )
    return result
