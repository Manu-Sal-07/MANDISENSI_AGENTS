import asyncio
import logging
from typing import Dict, Any
from mandisense_ai.cognition.engine import CognitionEngine
from mandisense_ai.cognition.ontology import RiskLevel

logger = logging.getLogger("ShockHandler")

class MarketShockHandler:
    """
    Event-Triggered Cognition Evolution.
    Handles external shocks (Weather, Policy, Infrastructure) and propagates them to market state.
    """
    def __init__(self):
        self.engine = CognitionEngine()

    async def trigger_shock(self, event_type: str, severity: float, affected_regions: list, description: str):
        """
        Propagates an external shock through the market memory.
        """
        logger.warning(f"MARKET SHOCK DETECTED: {event_type} (Severity: {severity})")
        logger.warning(f"Impact: {description}")
        
        # Identify affected commodities/mandis
        # For this foundation, we'll refresh all active mandis in the regions
        available = self.engine.state_store.list_available_intelligence()
        
        tasks = []
        for commodity, mandis in available.items():
            for mandi in mandis:
                # In a real system, we'd filter by region
                tasks.append(self._apply_shock_to_mandi(commodity, mandi, event_type, severity, description))
                
        await asyncio.gather(*tasks)

    async def _apply_shock_to_mandi(self, commodity: str, mandi_id: str, event_type: str, severity: float, description: str):
        # 1. Immediate Recomputation
        logger.info(f"Force-refreshing {commodity} @ {mandi_id} due to {event_type} shock.")
        state = await self.engine.generate_cognition(commodity, mandi_id)
        
        # 2. Mutate State based on Shock
        # We manually escalate risk and collapse confidence if severity is high
        if severity > 0.7:
            state.risk_level = RiskLevel.CRITICAL
            state.confidence.score *= (1.0 - severity)
            state.metadata["shock_event"] = {
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "description": description
            }
            
            # 3. Persistence of the Shock-Aware State
            self.engine.state_store.save_state(state)
            logger.info(f"Escalated {mandi_id} to CRITICAL risk due to external shock.")

if __name__ == "__main__":
    from datetime import datetime
    handler = MarketShockHandler()
    
    async def demo():
        await handler.trigger_shock(
            event_type="UNSEASONAL_RAINFALL",
            severity=0.85,
            affected_regions=["kolar", "bengaluru"],
            description="Flash floods in Kolar region disrupting supply chains."
        )
        
    asyncio.run(demo())
