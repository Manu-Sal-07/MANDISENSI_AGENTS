import json
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from mandisense_ai.cognition.state_store import MarketMemoryStore
from mandisense_ai.cognition.replay import AnalogEngine

router = APIRouter()
memory_store = MarketMemoryStore()
analog_engine = AnalogEngine()

@router.get("/state/{commodity}/{mandi_id}")
async def get_market_state(commodity: str, mandi_id: str):
    """
    Institutional endpoint for Evolving Market State.
    Includes freshness, confidence decay, and historical analogs.
    """
    state = memory_store.get_latest_state(commodity, mandi_id)
    if not state:
        raise HTTPException(
            status_code=404, 
            detail=f"Cognition not yet evolved for {commodity} @ {mandi_id}."
        )
        
    # Convert to dict for response
    state_dict = state.dict()
    
    # ── Institutional Intelligence Extension ──────────────────────────
    # We enrich the response with historical analogs
    analogs = analog_engine.find_analogs(state)
    state_dict["historical_analogs"] = analogs
    
    return state_dict

@router.get("/history/{commodity}/{mandi_id}")
async def get_market_history(commodity: str, mandi_id: str, limit: int = 50):
    """
    Retrieves the latest historical cognition snapshots for a specific commodity/mandi.
    """
    history_dir = memory_store.history_path / commodity / mandi_id
    if not history_dir.exists():
        raise HTTPException(status_code=404, detail=f"No historical market history found for {commodity} @ {mandi_id}.")

    history_files = sorted(history_dir.glob("*.json"))
    if not history_files:
        raise HTTPException(status_code=404, detail=f"No history files available for {commodity} @ {mandi_id}.")

    if limit < 1:
        limit = 1

    history_files = history_files[-limit:]
    history = []
    for hist_file in history_files:
        with open(hist_file, "r") as f:
            data = json.load(f)
        history.append(data)

    return {
        "commodity": commodity,
        "mandi_id": mandi_id,
        "history": history,
    }

@router.get("/directives")
async def get_all_directives():
    """
    Institutional summary of all evolving directives.
    """
    available = memory_store.list_available_intelligence()
    active_directives = []
    
    for commodity, mandis in available.items():
        for mandi in mandis:
            state = memory_store.get_latest_state(commodity, mandi)
            if state:
                active_directives.append({
                    "commodity": commodity,
                    "mandi_id": mandi,
                    "regime": state.regime,
                    "directive": state.directives.primary_directive,
                    "urgency": state.directives.urgency,
                    "confidence": round(state.confidence.score, 3),
                    "integrity": state.freshness.integrity_score,
                    "last_updated": state.freshness.last_computed
                })
                
    return {
        "count": len(active_directives),
        "directives": sorted(active_directives, key=lambda x: x["integrity"], reverse=True)
    }

@router.get("/available")
async def list_intelligence():
    return memory_store.list_available_intelligence()
