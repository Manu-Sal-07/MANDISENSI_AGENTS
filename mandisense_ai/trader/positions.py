"""
Position book and risk from the trader's real holdings.

Replaces the Command Center's "₹ Lakhs exposure", which was
`COMMODITY_VOLUMES[commodity] × price × change` — a fixed table (tomato
2,500, onion 5,000, ...) nobody entered, multiplied by a model's expected
move. It described no trader's actual position.

Here the trader records what they actually hold (LONG stock) or owe
(SHORT: committed to deliver), and risk is measured on that.

Method — historical simulation, chosen because it needs no distributional
assumption and keeps cross-position correlation for free:

  1. For every position, take this series' own calendar-true
     `horizon_days` log-returns over the last two years.
  2. Align all positions on the dates they share, so a day when tomato and
     onion both fell contributes a loss to both *on the same day*.
  3. P&L on a date = Σ side × quantity × mark × (e^return − 1).
  4. Report the 5th percentile of that P&L as the "95% worst case" and the
     mean of the worst 5% as the expected shortfall.

When too few dates are shared to trust the joint distribution, the result
falls back to summing each position's own worst case — which assumes every
position loses together, so it can only overstate risk, never understate it
— and says so.

Positions are file-backed (same convention as `farmer/alerts.py`), keyed by
a book id the trader keeps, so no accounts are required.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.trader.data import forward_returns, move_distribution, resolve, series
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

SIDES = ("LONG", "SHORT")
MIN_SHARED_DATES = 60
LOOKBACK_DAYS = 730


def _book_path() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data).parent / "trader" / "positions.json"


def _load() -> List[Dict[str, Any]]:
    path = _book_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Position book unreadable at %s: %s", path, exc)
        return []


def _save(rows: List[Dict[str, Any]]) -> None:
    path = _book_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    temp.replace(path)


def add_position(
    book_id: str,
    commodity: str,
    mandi_id: str,
    quantity_quintals: float,
    avg_cost: Optional[float] = None,
    side: str = "LONG",
) -> Dict[str, Any]:
    if side not in SIDES:
        return {"status": "ERROR", "reason": f"side must be one of {SIDES}"}
    if float(quantity_quintals) <= 0:
        return {"status": "ERROR", "reason": "quantity_quintals must be positive."}
    if avg_cost is not None and float(avg_cost) <= 0:
        return {"status": "ERROR", "reason": "avg_cost must be positive when given."}

    c, m = resolve(commodity, mandi_id)
    if series(c, m).empty:
        return {"status": "ERROR", "reason": f"No price history for {c} at {m}; it cannot be marked to market."}

    position = {
        "id": uuid.uuid4().hex[:12],
        "book_id": str(book_id).strip(),
        "commodity": c,
        "mandi_id": m,
        "quantity_quintals": float(quantity_quintals),
        "avg_cost": float(avg_cost) if avg_cost is not None else None,
        "side": side,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = _load()
    rows.append(position)
    _save(rows)
    return {"status": "OK", "position": position}


def list_positions(book_id: str) -> List[Dict[str, Any]]:
    book_id = str(book_id).strip()
    return [p for p in _load() if p.get("book_id") == book_id]


def delete_position(book_id: str, position_id: str) -> Dict[str, Any]:
    rows = _load()
    kept = [p for p in rows if not (p.get("id") == position_id and p.get("book_id") == str(book_id).strip())]
    if len(kept) == len(rows):
        return {"status": "ERROR", "reason": "Position not found in this book."}
    _save(kept)
    return {"status": "OK"}


def _sign(side: str) -> float:
    return 1.0 if side == "LONG" else -1.0


def assess_book(book_id: str, horizon_days: int = 5) -> Dict[str, Any]:
    positions = list_positions(book_id)
    if not positions:
        return {"status": "EMPTY", "book_id": book_id, "reason": "No positions recorded in this book yet."}

    rows: List[Dict[str, Any]] = []
    pnl_columns: Dict[str, pd.Series] = {}
    used_methods = set()

    for p in positions:
        dist = move_distribution(p["commodity"], p["mandi_id"], horizon_days)
        if dist.get("status") != "OK":
            rows.append({**p, "status": "UNAVAILABLE", "reason": dist.get("reason")})
            continue

        mark = float(dist["base_price"])
        exposure = _sign(p["side"]) * p["quantity_quintals"] * mark
        q = dist["quantiles"]
        # P&L quantiles for this position alone. For a SHORT the tails swap:
        # a price rise is the loss.
        def pnl_at(key: str) -> float:
            return _sign(p["side"]) * p["quantity_quintals"] * mark * (float(np.exp(q[key])) - 1)

        low, high = sorted([pnl_at("p05"), pnl_at("p95")])
        used_methods.add(dist["method"])
        entry = {
            **p,
            "status": "OK",
            "mark_price": round(mark, 2),
            "mark_date": dist["base_date"],
            "price_age_days": dist.get("age_days"),
            "exposure": round(exposure, 2),
            "unrealised_pnl": (
                round(_sign(p["side"]) * p["quantity_quintals"] * (mark - p["avg_cost"]), 2)
                if p.get("avg_cost") else None
            ),
            "pnl_p05": round(low, 2),
            "pnl_p50": round(pnl_at("p50"), 2),
            "pnl_p95": round(high, 2),
            "basis": dist["method"],
            "sample_size": dist.get("sample_size"),
        }
        rows.append(entry)

        # Historical-simulation column for the joint portfolio distribution.
        frame = series(p["commodity"], p["mandi_id"])
        frame = frame[frame["date"] >= frame["date"].max() - pd.Timedelta(days=LOOKBACK_DAYS)].reset_index(drop=True)
        rets = forward_returns(frame, horizon_days)
        col = pd.Series(
            _sign(p["side"]) * p["quantity_quintals"] * mark * (np.exp(rets.to_numpy()) - 1),
            index=pd.DatetimeIndex(frame["date"]),
        ).dropna()
        key = p["id"]
        pnl_columns[key] = col

    ok = [r for r in rows if r.get("status") == "OK"]
    if not ok:
        return {"status": "UNAVAILABLE", "book_id": book_id, "positions": rows,
                "reason": "None of the positions could be priced."}

    joint = None
    if len(pnl_columns) >= 1:
        table = pd.concat(pnl_columns.values(), axis=1, join="inner")
        if len(table) >= MIN_SHARED_DATES:
            joint = table.sum(axis=1)

    if joint is not None:
        var95 = float(np.percentile(joint, 5))
        tail = joint[joint <= var95]
        portfolio = {
            "method": "historical_simulation_joint",
            "shared_dates": int(len(joint)),
            "worst_case_95": round(var95, 2),
            "expected_shortfall_95": round(float(tail.mean()), 2),
            "median_pnl": round(float(np.median(joint)), 2),
            "best_case_95": round(float(np.percentile(joint, 95)), 2),
        }
    else:
        portfolio = {
            "method": "sum_of_individual_worst_cases",
            "shared_dates": int(len(pd.concat(pnl_columns.values(), axis=1, join="inner"))) if pnl_columns else 0,
            "worst_case_95": round(sum(min(r["pnl_p05"], r["pnl_p95"]) for r in ok), 2),
            "expected_shortfall_95": None,
            "median_pnl": round(sum(r["pnl_p50"] for r in ok), 2),
            "best_case_95": round(sum(max(r["pnl_p05"], r["pnl_p95"]) for r in ok), 2),
            "note": (
                "Too few dates are shared across these positions to estimate a joint "
                "distribution. Summing each position's own worst case assumes they all "
                "lose together, so this figure can overstate risk but not understate it."
            ),
        }

    gross = sum(abs(r["exposure"]) for r in ok)
    net = sum(r["exposure"] for r in ok)
    by_commodity: Dict[str, float] = {}
    for r in ok:
        by_commodity[r["commodity"]] = by_commodity.get(r["commodity"], 0.0) + r["exposure"]

    return {
        "status": "OK",
        "book_id": book_id,
        "horizon_days": horizon_days,
        "gross_exposure": round(gross, 2),
        "net_exposure": round(net, 2),
        "by_commodity": {k: round(v, 2) for k, v in by_commodity.items()},
        "portfolio": portfolio,
        "basis": sorted(used_methods),
        "positions": rows,
        "unpriced": [r for r in rows if r.get("status") != "OK"],
    }
