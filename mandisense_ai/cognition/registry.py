from typing import List, Dict, Set
from enum import Enum

class EntityType(str, Enum):
    COMMODITY = "COMMODITY"
    AGENT = "AGENT"
    MANDI = "MANDI"
    DATASET = "DATASET"
    ARTIFACT = "ARTIFACT"

# --- CANONICAL COMMODITY REGISTRY ---
# Phase 5B: Unified source of truth for market cognition targets.
VALID_COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]

# --- MANDI REGISTRY ---
# Real Agmarknet mandis of the Bengaluru-Kolar belt (the ids of the farmer world). `bangalore_apmc` and
# `bangalore_yeshwanthpur` are older spellings of `bengaluru_apmc`; see forecasting.naming.world_market.
VALID_MANDIS = ["bagepalli_apmc", "bangarpet_apmc", "bengaluru_apmc", "binny_mill_apmc", "channapatna_apmc", "chikkaballapura_apmc",
                "chintamani_apmc", "doddaballapur_apmc", "gauribidanur_apmc", "hoskote_apmc", "kanakapura_apmc", "kolar_apmc",
                "malur_apmc", "mulbagal_apmc", "ramanagara_apmc", "srinivasapur_apmc"]

# --- NAMESPACE SEGREGATION ---
# These are explicitly NOT commodities.
AGENT_ENTITIES = {
    "ForecastAgent", "ArrivalAgent", "SeasonalityAgent", 
    "VolatilityAgent", "ExternalFactorsAgent",
    "arrival", "seasonality", "volatility", "external_factors"
}

ARTIFACT_ENTITIES = {
    "tomato_kolar", "processed", "v3", "v4", "experiments", "datasets"
}

class CognitionRegistry:
    @staticmethod
    def is_valid_commodity(name: str) -> bool:
        return name in VALID_COMMODITIES

    @staticmethod
    def is_agent(name: str) -> bool:
        return name in AGENT_ENTITIES

    @staticmethod
    def is_mandi(name: str) -> bool:
        return name in VALID_MANDIS

    @staticmethod
    def get_canonical_commodities() -> List[str]:
        return VALID_COMMODITIES

    @staticmethod
    def get_canonical_mandis() -> List[str]:
        return VALID_MANDIS

    @staticmethod
    def get_forecastable_pairs() -> List[tuple]:
        """(commodity, mandi) pairs the forecast service has a validated forecast for, keyed by the world id."""
        from mandisense_ai.forecasting.naming import world_market
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
        if not service.is_available:
            return []
        pairs = {(s["commodity"], world_market(s["mandi_id"])) for s in service.available_series() if s["commodity"] in VALID_COMMODITIES}
        return sorted(p for p in pairs if any(r.get("status") == "OK" for r in service.get_curve(p[0], __import__("mandisense_ai.forecasting.naming", fromlist=["x"]).forecast_market(p[1])) or []))
