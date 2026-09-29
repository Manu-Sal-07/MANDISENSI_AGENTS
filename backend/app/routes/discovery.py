from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from backend.app.services import model_loader
from mandisense_ai.core.orchestrator.decision_orchestrator import (
    CALL_UNAVAILABLE,
    DecisionOrchestrator,
)
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Constructed here rather than reached for through `model_loader.engines`.
#
# That global is populated by a *background* warmup task with a 15-second
# timeout whose failures are logged and swallowed, so `engines` is routinely
# still None when the first request lands -- and these routes dereferenced it
# unguarded. Every discovery endpoint then raised AttributeError, which the
# per-item `except: continue` turned into an empty list, which the farmer
# screen rendered as "Today's calls are not in yet. Mandi records usually
# arrive by the afternoon." That message blames the mandi for a warmup race.
#
# Since the orchestrator was rewritten to read the published forecast store
# and run no models at request time, it has no warmup to wait for: it is a
# store lookup, and constructing one is free.
_ORCHESTRATOR = DecisionOrchestrator()


def _decision_orchestrator():
    """The warmed-up orchestrator when there is one, else a direct reader.

    Prefers `model_loader`'s instance so anything that warmup attaches is not
    bypassed, but never depends on it having happened.
    """
    engines = getattr(model_loader, "engines", None)
    return getattr(engines, "decision_orch", None) or _ORCHESTRATOR

# Mock location to mandi mapping (Bengaluru area)
LOCATION_MANDI_MAP = {
    "bengaluru": ["bangalore_yeshwanthpur", "hoskote_apmc", "anekal_apmc"],
    "kolar": ["kolar_apmc", "bangarpet_apmc"],
    "ramanagara": ["ramanagara_apmc", "channapatna_apmc"],
    "chickballapur": ["chickballapur_apmc", "sidlaghatta_apmc"]
}

COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]


def _rank_commodities_by_expected_move(mandi_id: str) -> List[str]:
    """
    Commodities for a mandi, most-moving first.

    This used to be `random.choice(COMMODITIES)`: the "hot commodity" on the
    farmer home screen was drawn from a hat on every request, so refreshing
    the page changed which crop the market was supposedly excited about. The
    published forecast store already knows which series it expects to move
    furthest, so rank by that and fall back to a stable declared order when
    no forecast is available — never to a random pick, which is indis-
    tinguishable from evidence to whoever is reading it.
    """
    try:
        from mandisense_ai.forecasting.naming import canonical_market
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
        if not service.is_available:
            return list(COMMODITIES)

        resolved_mandi = canonical_market(mandi_id) or mandi_id
        scored: List[tuple] = []
        for commodity in COMMODITIES:
            curve = service.get_curve(commodity, resolved_mandi)
            best = 0.0
            for row in curve:
                if row.get("status") != "OK":
                    continue
                change = row.get("expected_change_pct")
                if change is not None:
                    best = max(best, abs(float(change)))
            scored.append((best, commodity))

        # Stable tie-break on the declared order, so commodities with no
        # forecast keep a deterministic position instead of shuffling.
        scored.sort(key=lambda pair: (-pair[0], COMMODITIES.index(pair[1])))
        return [commodity for _, commodity in scored]
    except Exception:
        return list(COMMODITIES)


@router.get("/feed")
@router.get("/mandi-feed")
async def get_mandi_feed(location: str = "bengaluru"):
    location = location.lower()
    mandi_ids = LOCATION_MANDI_MAP.get(location, ["bengaluru_apmc", "kolar_apmc"])

    feed = []
    for m_id in mandi_ids:
        hot_comm = _rank_commodities_by_expected_move(m_id)[0]
        try:
            # Use bracket notation [] for dictionary access
            decision = await _decision_orchestrator().get_actionable_decision(hot_comm, m_id)

            feed.append({
                "id": m_id,
                "mandi_name": m_id.replace("_apmc", "").replace("_", " ").title(),
                "hot_commodity": hot_comm.replace("_", " ").title(),
                "decision": decision.get("decision", "WAIT"),
                "call_type": decision.get("call_type", CALL_UNAVAILABLE),
                "abstention_reason": decision.get("abstention_reason"),
                "status": decision.get("status"),
                "reasoning": decision.get("reasoning", "Market unclear today"),
                "price_change_pct": decision.get("price_change_pct", 0.0),
                "confidence": decision.get("confidence", 0.0),
                # Defaulting an unknown risk to "HIGH" is still a claim. Where
                # the orchestrator reports UNKNOWN, that is what travels.
                "risk_level": decision.get("risk_level", "UNKNOWN")
            })
        except Exception as e:
            print(f"DEBUG: Feed error for {m_id}: {str(e)}")
            continue

    return feed

@router.get("/details")
@router.get("/mandi/{mandi_id}")
async def get_mandi_details(mandi_id: str):
    details = {
        "mandi_id": mandi_id,
        "mandi_name": mandi_id.replace("_apmc", "").replace("_", " ").title(),
        "commodities": []
    }
    
    for comm in COMMODITIES:
        try:
            decision = await _decision_orchestrator().get_actionable_decision(comm, mandi_id)
            
            # Extract price safely from raw_inference if available
            raw_inf = decision.get("raw_inference", {})
            pred_price = raw_inf.get("predicted_price", 0)
            
            details["commodities"].append({
                "name": comm.replace("_", " ").title(),
                "price": pred_price,
                "decision": decision.get("decision", "WAIT"),
                "call_type": decision.get("call_type", CALL_UNAVAILABLE),
                "abstention_reason": decision.get("abstention_reason"),
                "status": decision.get("status"),
                "reason": decision.get("reason"),
                "reasoning": decision.get("reasoning", ""),
                "confidence": decision.get("confidence", 0.0),
                "risk": decision.get("risk_level", "UNKNOWN"),
                "price_change": decision.get("price_change_pct", 0.0),
                # Was `random.random() > 0.5`. The inference result already
                # carries a real arrival signal derived from observed volumes;
                # where it is absent the honest answer is that we do not know,
                # not a coin flip presented to a farmer as supply intelligence.
                "arrival_signal": (raw_inf.get("arrival_signal") or "unavailable").title(),
                # "not HIGH" is not the same as "Low": an UNKNOWN risk level
                # was being published to a farmer as low volatility.
                "volatility": {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}.get(
                    decision.get("risk_level"), "Unknown"
                ),
            })
        except Exception as e:
            print(f"DEBUG: Detail error for {comm}: {str(e)}")
            continue
            
    details["transport_suggestion"] = "Evening transport recommended for freshness."
    return details

@router.get("/quick-decisions")
async def get_quick_decisions(location: str = "bengaluru"):
    location = location.lower()
    mandi_ids = LOCATION_MANDI_MAP.get(location, ["bengaluru_apmc"])
    m_id = mandi_ids[0]
    
    quick_list = []
    for comm in COMMODITIES:
        label = comm.replace("_", " ").title()
        try:
            decision = await _decision_orchestrator().get_actionable_decision(comm, m_id)
            # `call_type` travels with the verb. Forwarding `decision` alone
            # made "the policy says hold" and "there is no forecast for this
            # crop" arrive at the UI as the same string, and the UI rendered
            # both as a confident call with a 0.0% move beside it.
            quick_list.append({
                "commodity": label,
                "decision": decision.get("decision", "WAIT"),
                "call_type": decision.get("call_type", CALL_UNAVAILABLE),
                "abstention_reason": decision.get("abstention_reason"),
                "status": decision.get("status"),
                "reason": decision.get("reason"),
                "confidence": decision.get("confidence", 0.0),
                "price_change_pct": decision.get("price_change_pct", 0.0),
            })
        except Exception as exc:
            # Previously `continue`, which silently shortened the list: a
            # farmer saw four crops where five were asked for, with nothing
            # to say the fifth had failed rather than not existing.
            logger.warning("Quick decision failed for %s/%s: %s", comm, m_id, exc)
            quick_list.append({
                "commodity": label,
                "decision": "WAIT",
                "call_type": CALL_UNAVAILABLE,
                "abstention_reason": None,
                "status": "ERROR",
                "reason": "This crop could not be read from the forecast service.",
                "confidence": 0.0,
                "price_change_pct": 0.0,
            })

    return {
        "location": location.title(),
        "decisions": quick_list
    }
