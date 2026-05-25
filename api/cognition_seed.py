"""
Cognition Seed Endpoint
Triggers immediate cognition generation for all canonical commodities/mandis.
Called on startup or on-demand to populate the market state store.
"""
import asyncio
import logging
from fastapi import APIRouter
from typing import Dict, Any, List

logger = logging.getLogger("CognitionSeed")
router = APIRouter()


@router.post("/v1/cognition/seed")
async def seed_cognition():
    """
    Seeds initial cognition for all canonical commodities and mandis.
    Populates the MarketMemoryStore with fresh states.
    """
    from mandisense_ai.cognition.engine import CognitionEngine
    from mandisense_ai.cognition.registry import CognitionRegistry

    commodities = CognitionRegistry.get_canonical_commodities()
    mandis = CognitionRegistry.get_canonical_mandis()

    engine = CognitionEngine()
    results = []
    errors = []

    for commodity in commodities:
        for mandi in mandis:
            try:
                state = await engine.generate_cognition(commodity, mandi)
                results.append({
                    "commodity": commodity,
                    "mandi": mandi,
                    "status": "seeded",
                    "directive": state.directives[0].primary_directive if state.directives else "HOLD",
                    "confidence": round(state.confidence.score, 3)
                })
            except Exception as e:
                logger.error(f"Seed failed for {commodity}@{mandi}: {e}")
                errors.append({"commodity": commodity, "mandi": mandi, "error": str(e)})

    return {
        "status": "complete",
        "seeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.get("/v1/cognition/directives/all")
async def get_all_agent_outputs():
    """
    Returns all available market states with full agent deliberation details.
    Used by the Live Cognition Terminal center panel.
    """
    from mandisense_ai.cognition.state_store import MarketMemoryStore
    from mandisense_ai.cognition.registry import CognitionRegistry

    store = MarketMemoryStore()
    commodities = CognitionRegistry.get_canonical_commodities()
    mandis = CognitionRegistry.get_canonical_mandis()

    all_states = []
    for commodity in commodities:
        for mandi in mandis:
            state = store.get_latest_state(commodity, mandi)
            if state:
                state_dict = state.model_dump() if hasattr(state, 'model_dump') else state.dict()
                all_states.append(state_dict)

    return {
        "count": len(all_states),
        "states": all_states,
        "commodities_tracked": commodities,
        "mandis_tracked": mandis
    }


@router.get("/v1/cognition/quick-health")
async def quick_health():
    """
    Returns a lightweight health snapshot for the terminal HUD.
    Does not require CognitionEngine instantiation.
    """
    from mandisense_ai.cognition.state_store import MarketMemoryStore
    from mandisense_ai.cognition.registry import CognitionRegistry

    store = MarketMemoryStore()
    available = store.list_available_intelligence()

    total_states = sum(len(v) for v in available.values())

    return {
        "intelligence_available": total_states > 0,
        "commodities_with_intelligence": list(available.keys()),
        "total_states": total_states,
        "coverage_map": available
    }
