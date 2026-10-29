"""
Read side of the agent council: what each specialist forecasts for a series, the fused forecast, and the evidence for trusting it.

The council is trained and evaluated offline (`scripts/eval_agent_council.py`); this module only reads its artifacts. It never
decides what the product serves: that is the promotion rule in `council.promote`, whose verdict is carried in every response.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Optional

from mandisense_ai.forecasting.council import OUT_DIR
from mandisense_ai.forecasting.naming import forecast_market


@lru_cache(maxsize=4)
def _load(name: str, mtime: float) -> Dict[str, Any]:
    return json.loads((OUT_DIR / name).read_text(encoding="utf-8"))


def _artifact(name: str) -> Optional[Dict[str, Any]]:
    path = OUT_DIR / name
    return _load(name, path.stat().st_mtime) if path.exists() else None


def evaluation() -> Dict[str, Any]:
    ev = _artifact("evaluation.json")
    if ev is None:
        return {"status": "UNAVAILABLE", "reason": "The council has not been evaluated; run scripts/eval_agent_council.py."}
    return {"status": "OK", **ev}


def view(commodity: str, mandi_id: str) -> Dict[str, Any]:
    """Per-agent and fused forecasts for one series at every evaluated horizon, with each horizon's promotion verdict."""
    data, ev = _artifact("forecasts.json"), _artifact("evaluation.json")
    if data is None or ev is None:
        return {"status": "UNAVAILABLE", "reason": "The council has not been built; run scripts/eval_agent_council.py."}
    row = data["series"].get(f"{commodity.lower()}|{forecast_market(mandi_id)}")
    if row is None:
        return {"status": "UNAVAILABLE", "reason": f"No council forecast for {commodity} at {mandi_id}: the series has too little history."}
    horizons = {}
    for h, v in row["horizons"].items():
        e = ev["horizons"].get(h, {})
        horizons[h] = {**v, "evidence": {
            "single_skill": e.get("methods", {}).get("single", {}).get("skill"), "council_skill": e.get("methods", {}).get("council", {}).get("skill"),
            "difference_ci": (e.get("council_vs_single") or {}).get("ci"), "folds_council_beats_single": e.get("folds_council_beats_single"),
            "folds": e.get("folds"), "agent_skill": {k: e["methods"][k]["skill"] for k in ev["agents"] if k in e.get("methods", {})}}}
    return {"status": "OK", "commodity": row["commodity"], "mandi_id": row["mandi_id"], "as_of": row["as_of"], "last_price": row["last_price"],
            "horizons": horizons, "agents": list(ev["agents"]), "generated_at": data["generated_at"],
            "served": "single model unless a horizon is promoted",
            "external_factors": "shown as live context only; no historical panel exists to validate a weight against"}
