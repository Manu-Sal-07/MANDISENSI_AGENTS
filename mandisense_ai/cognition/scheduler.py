import asyncio
import time
import logging
from typing import List, Tuple
from mandisense_ai.cognition.engine import CognitionEngine
from mandisense_ai.cognition.ontology import MarketRegime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AdaptiveScheduler")

class AdaptiveScheduler:
    """
    Intelligence-Aware Cognition Scheduler.
    Allocates compute dynamically based on volatility and confidence decay.
    """
    def __init__(self):
        self.engine = CognitionEngine()
        
    async def run_cycle(self):
        logger.info("Starting Adaptive Cognition Cycle...")
        
        # 1. Identify all active mandis
        available = self.engine.state_store.list_available_intelligence()
        
        # 2. Calculate Urgency for each
        queue = []
        for commodity, mandis in available.items():
            for mandi in mandis:
                urgency = self._calculate_urgency(commodity, mandi)
                queue.append((urgency, commodity, mandi))
        
        # Sort by urgency (highest first)
        queue.sort(key=lambda x: x[0], reverse=True)
        
        # 3. Execute with Priority
        # We can process top N immediately, or all in order
        for urgency, comm, mandi in queue:
            if urgency > 0.5: # Threshold for refresh
                logger.info(f"Priority Refresh: {comm} @ {mandi} (Urgency: {urgency:.2f})")
                await self.engine.generate_cognition(comm, mandi)
            else:
                logger.debug(f"Skipping {comm} @ {mandi} (Low Urgency: {urgency:.2f})")

    def _calculate_urgency(self, commodity: str, mandi_id: str) -> float:
        state = self.engine.state_store.get_latest_state(commodity, mandi_id)
        if not state: return 1.0 # New mandi, highest priority
        
        urgency = 0.0
        
        # Factor 1: Freshness (0.0 to 1.0)
        # If it's stale (4 hours), urgency increases
        age_factor = min(1.0, state.freshness.age_minutes / state.freshness.expiration_threshold_minutes)
        urgency += age_factor * 0.4
        
        # Factor 2: Volatility & Regime
        if state.regime == MarketRegime.ELEVATED_VOLATILITY:
            urgency += 0.5 # Force frequent updates
        elif state.regime == MarketRegime.TRANSITIONAL_STRESS:
            urgency += 0.3
            
        # Factor 3: Confidence Collapse
        if state.confidence.score < 0.5:
            urgency += 0.2
            
        return min(1.0, urgency)

async def main():
    scheduler = AdaptiveScheduler()
    logger.info("MandiSense Adaptive Scheduler Started.")
    
    while True:
        try:
            await scheduler.run_cycle()
            # Adaptive sleep: shorter cycles if market is volatile
            await asyncio.sleep(600) # Every 10 mins
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
