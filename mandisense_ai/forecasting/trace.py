"""
A traced run of the agent council for one commodity at one mandi, step by step.

Used by `/v1/trace-run`, the `/ws/visualizer` WebSocket and the command line (`python -m mandisense_ai.forecasting.trace tomato kolar`).
Every number comes from the council artifacts (`scripts/eval_agent_council.py`) or the live external-factors reader; nothing is
simulated. The trace says plainly whether the council is trusted over the single model at each horizon.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, List, Optional

from mandisense_ai.forecasting import council_service
from mandisense_ai.forecasting.naming import canonical_market
from mandisense_ai.utils.event_bus import event_bus
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

Emit = Callable[[str, Optional[Dict[str, Any]]], None]


def _external(commodity: str, mandi: str) -> Dict[str, Any]:
    """Live weather/news context. It carries no forecast weight; a failure here must not stop the trace."""
    try:
        from mandisense_ai.core.agents.external_factors_agent import run_external_factors_agent

        return run_external_factors_agent(commodity, mandi)
    except Exception as exc:
        logger.warning("External factors unavailable: %s", exc)
        return {"status": "UNAVAILABLE", "reason": str(exc)[:160]}


def run_trace(commodity: str, mandi: str, emit: Emit) -> Dict[str, Any]:
    commodity = commodity.strip().lower()
    mandi_id = canonical_market(mandi) or mandi
    emit("query_received", {"commodity": commodity, "mandi": mandi_id})

    view = council_service.view(commodity, mandi_id)
    if view["status"] != "OK":
        emit("error", {"message": view["reason"]})
        return {"status": "error", "message": view["reason"]}

    for agent in view["agents"]:
        emit("agent_completed", {"agent": agent, "forecast_pct": {h: v["agents"][agent] for h, v in view["horizons"].items()},
                                 "skill_vs_no_change": {h: v["evidence"]["agent_skill"].get(agent) for h, v in view["horizons"].items()}})

    emit("external_started", None)
    external = _external(commodity, mandi_id)
    emit("external_completed", external)

    emit("ensemble_weights_computed", {h: v["weights"] for h, v in view["horizons"].items()})
    fused = {h: {"council_pct": v["council_pct"], "single_pct": v["single_pct"], "council_price": v["council_price"],
                 "council_trusted_over_single": v["promoted"], "evidence": v["evidence"]} for h, v in view["horizons"].items()}
    emit("meta_ensemble_completed", fused)

    result = {"status": "success", "commodity": commodity, "mandi": mandi_id, "as_of": view["as_of"], "last_price": view["last_price"],
              "agents": {a: {h: v["agents"][a] for h, v in view["horizons"].items()} for a in view["agents"]},
              "meta_ensemble": fused, "external_factors": external, "served": view["served"]}
    emit("final_output", result)
    return result


def run_pipeline(commodity: str, mandi: str) -> Dict[str, Any]:
    """Synchronous entry point; steps are published on the process-wide event bus for any subscribed visualiser."""
    def emit(step: str, data: Optional[Dict[str, Any]] = None) -> None:
        event_bus.sync_emit(step, data=data)

    try:
        return run_trace(commodity, mandi, emit)
    except Exception as exc:
        logger.error("Trace failed: %s", exc, exc_info=True)
        event_bus.sync_emit("error", data={"message": str(exc)})
        return {"status": "error", "message": str(exc)}


def collect(commodity: str, mandi: str) -> List[Dict[str, Any]]:
    """The trace as an ordered list of events, for transports (WebSocket) that stream them with their own pacing."""
    events: List[Dict[str, Any]] = []
    run_trace(commodity, mandi, lambda step, data=None: events.append({"step": step, "data": data}))
    return events


if __name__ == "__main__":
    result = run_pipeline(*(sys.argv[1:3] or ["tomato", "kolar"]))
    print(json.dumps(result, indent=2, default=str))
    raise SystemExit(0 if result["status"] == "success" else 1)
