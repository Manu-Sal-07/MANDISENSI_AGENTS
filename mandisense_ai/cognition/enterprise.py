import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("EnterpriseCognition")

class SystemicExposure(BaseModel):
    commodity: str
    concentration_score: float # 0.0 to 1.0
    regional_dependency: str
    volatility_contribution: float
    fragility_index: float

class EnterpriseResilience(BaseModel):
    overall_score: float
    sourcing_resilience: float
    volatility_tolerance: float
    inventory_stability: float
    recovery_probability: float
    last_updated: datetime

class EnterpriseCognitionHub:
    """
    Enterprise Portfolio Resilience Infrastructure.
    "The institutional nervous system of the organization."
    """
    def __init__(self):
        self.market_states: Dict[str, Any] = {}
        self.exposure_topology: List[SystemicExposure] = []
        self.current_resilience: Optional[EnterpriseResilience] = None

    def update_portfolio_cognition(self, all_market_states: List[Any]):
        """
        Aggregates individual market states into enterprise-wide exposure intelligence.
        """
        self.market_states = {f"{s.commodity}_{s.mandi_id}": s for s in all_market_states}
        
        # 1. Synthesize Exposure Topology
        self.exposure_topology = self._calculate_exposure_topology()
        
        # 2. Estimate Enterprise Resilience
        self.current_resilience = self._calculate_resilience()
        
        logger.info(f"Enterprise cognition updated. Resilience Score: {self.current_resilience.overall_score:.2f}")

    def get_strategic_posture(self) -> Dict[str, Any]:
        """
        Returns the enterprise-scale strategic posture.
        """
        if not self.current_resilience:
            return {"status": "initializing"}
            
        return {
            "resilience": self.current_resilience.dict(),
            "exposure": [e.dict() for e in self.exposure_topology],
            "systemic_threats": self._identify_systemic_threats(),
            "rebalancing_recommendations": self._generate_rebalancing_plan()
        }

    def _calculate_exposure_topology(self) -> List[SystemicExposure]:
        topology = []
        commodities = set(s.commodity for s in self.market_states.values())
        
        for comm in commodities:
            comm_states = [s for s in self.market_states.values() if s.commodity == comm]
            avg_risk = sum(1.0 if s.risk_level in ["HIGH", "CRITICAL"] else 0.0 for s in comm_states) / len(comm_states)
            avg_chaos = sum(s.deliberation.chaos_score for s in comm_states) / len(comm_states)
            
            topology.append(SystemicExposure(
                commodity=comm,
                concentration_score=len(comm_states) / 10.0, # Dummy scaling
                regional_dependency="SOUTH_CORRIDOR" if "bangalore" in str(comm_states[0].mandi_id) else "NORTH_CORRIDOR",
                volatility_contribution=avg_chaos,
                fragility_index=avg_risk * avg_chaos
            ))
        return topology

    def _calculate_resilience(self) -> EnterpriseResilience:
        if not self.exposure_topology:
            return EnterpriseResilience(overall_score=1.0, sourcing_resilience=1.0, volatility_tolerance=1.0, inventory_stability=1.0, recovery_probability=1.0, last_updated=datetime.now())
            
        avg_fragility = sum(e.fragility_index for e in self.exposure_topology) / len(self.exposure_topology)
        resilience_score = max(0.1, 1.0 - avg_fragility)
        
        return EnterpriseResilience(
            overall_score=resilience_score,
            sourcing_resilience=resilience_score * 0.9,
            volatility_tolerance=1.0 - (sum(e.volatility_contribution for e in self.exposure_topology) / len(self.exposure_topology)),
            inventory_stability=0.85, # Logic for inventory stability would go here
            recovery_probability=resilience_score * 1.1,
            last_updated=datetime.now()
        )

    def _identify_systemic_threats(self) -> List[str]:
        threats = []
        critical_exposures = [e for e in self.exposure_topology if e.fragility_index > 0.6]
        if len(critical_exposures) > 1:
            threats.append("Cross-Commodity Contagion Risk: Multiple critical fragilities detected.")
        if any(e.volatility_contribution > 0.8 for e in self.exposure_topology):
            threats.append("Systemic Volatility Saturation: High chaos score in primary sourcing hubs.")
        return threats

    def _generate_rebalancing_plan(self) -> List[Dict[str, Any]]:
        plan = []
        for e in self.exposure_topology:
            if e.fragility_index > 0.5:
                plan.append({
                    "target": e.commodity,
                    "action": "DIVERSIFY_SOURCING",
                    "reason": f"High fragility index ({e.fragility_index:.2f}) in primary corridor."
                })
        return plan
