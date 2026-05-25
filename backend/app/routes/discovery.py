from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.app.services import model_loader
import random

router = APIRouter()

# Mock location to mandi mapping (Bengaluru area)
LOCATION_MANDI_MAP = {
    "bengaluru": ["bangalore_yeshwanthpur", "hoskote_apmc", "anekal_apmc"],
    "kolar": ["kolar_apmc", "bangarpet_apmc"],
    "ramanagara": ["ramanagara_apmc", "channapatna_apmc"],
    "chickballapur": ["chickballapur_apmc", "sidlaghatta_apmc"]
}

COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]

@router.get("/feed")
@router.get("/mandi-feed")
async def get_mandi_feed(location: str = "bengaluru"):
    location = location.lower()
    mandi_ids = LOCATION_MANDI_MAP.get(location, ["bengaluru_apmc", "kolar_apmc"])
    
    feed = []
    for m_id in mandi_ids:
        hot_comm = random.choice(COMMODITIES)
        try:
            # Use bracket notation [] for dictionary access
            decision = await model_loader.engines.decision_orch.get_actionable_decision(hot_comm, m_id)
            
            feed.append({
                "id": m_id,
                "mandi_name": m_id.replace("_apmc", "").replace("_", " ").title(),
                "hot_commodity": hot_comm.replace("_", " ").title(),
                "decision": decision.get("decision", "WAIT"),
                "reasoning": decision.get("reasoning", "Market unclear today"),
                "price_change_pct": decision.get("price_change_pct", 0.0),
                "confidence": decision.get("confidence", 0.0),
                "risk_level": decision.get("risk_level", "HIGH")
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
            decision = await model_loader.engines.decision_orch.get_actionable_decision(comm, mandi_id)
            
            # Extract price safely from raw_inference if available
            raw_inf = decision.get("raw_inference", {})
            pred_price = raw_inf.get("predicted_price", 0)
            
            details["commodities"].append({
                "name": comm.replace("_", " ").title(),
                "price": pred_price,
                "decision": decision.get("decision", "WAIT"),
                "reasoning": decision.get("reasoning", ""),
                "confidence": decision.get("confidence", 0.0),
                "risk": decision.get("risk_level", "HIGH"),
                "price_change": decision.get("price_change_pct", 0.0),
                "arrival_signal": "Increasing" if random.random() > 0.5 else "Stable",
                "volatility": "High" if decision.get("risk_level") == "HIGH" else "Low"
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
        try:
            decision = await model_loader.engines.decision_orch.get_actionable_decision(comm, m_id)
            quick_list.append({
                "commodity": comm.replace("_", " ").title(),
                "decision": decision.get("decision", "WAIT"),
                "price_change_pct": decision.get("price_change_pct", 0.0)
            })
        except Exception:
            continue
            
    return {
        "location": location.title(),
        "decisions": quick_list
    }
