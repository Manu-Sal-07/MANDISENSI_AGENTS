import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from mandisense_ai.cognition.world_model.topology import MarketTopology

logger = logging.getLogger("WorldModelSimulation")

class ShockPropagationSimulator:
    """
    Institutional Shock Propagation Engine.
    Simulates how market stress evolves through structural corridors.
    """
    def __init__(self, topology: MarketTopology):
        self.topology = topology

    def simulate_shock(self, source_node: str, initial_magnitude: float) -> List[Dict[str, Any]]:
        """
        Calculates the secondary and tertiary impacts of a shock.
        Returns a list of propagation events.
        """
        propagation_chain = []
        
        # Initial Shock
        propagation_chain.append({
            "target": source_node,
            "magnitude": initial_magnitude,
            "latency_hours": 0,
            "depth": 0
        })
        
        # Level 1 Propagation
        downstream = self.topology.get_downstream_impacts(source_node)
        for edge in downstream:
            impact_mag = initial_magnitude * edge.weight
            propagation_chain.append({
                "target": edge.target,
                "magnitude": round(impact_mag, 3),
                "latency_hours": edge.latency_hours,
                "depth": 1,
                "driver": source_node
            })
            
            # Level 2 Propagation (Simplified)
            level2 = self.topology.get_downstream_impacts(edge.target)
            for e2 in level2:
                i2 = impact_mag * e2.weight
                propagation_chain.append({
                    "target": e2.target,
                    "magnitude": round(i2, 3),
                    "latency_hours": edge.latency_hours + e2.latency_hours,
                    "depth": 2,
                    "driver": edge.target
                })
                
        return propagation_chain

class CounterfactualEngine:
    """
    Scenario Simulation Infrastructure.
    "What-if" reasoning for procurement strategy.
    """
    def __init__(self, simulator: ShockPropagationSimulator):
        self.simulator = simulator

    def run_scenario(self, scenario_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Example scenarios: "RAIN_IN_KOLAR", "TRANSPORT_STRIKE_NASHIK"
        """
        if scenario_type == "RAIN_IN_KOLAR":
            impacts = self.simulator.simulate_shock("kolar_apmc", 0.8)
            return {
                "scenario": scenario_type,
                "primary_impact": "Severe arrival delay in Kolar production hub.",
                "downstream_cascades": impacts,
                "procurement_advice": "Shift sourcing to Nashik/Pune corridors immediately."
            }
        
        return {"error": "Unknown scenario type"}
