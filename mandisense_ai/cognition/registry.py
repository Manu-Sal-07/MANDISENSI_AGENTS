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
VALID_MANDIS = ["kolar_apmc", "bangalore_apmc"]

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
