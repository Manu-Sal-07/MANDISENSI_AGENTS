import logging
from typing import Dict, Any
from mandisense_ai.cognition.agents.base import CognitiveAgent, AgentSignal
from mandisense_ai.core.agents.inference_engine_v3 import DecisionGradeInferenceEngine

logger = logging.getLogger("CognitiveAgents")

class ForecastAgent(CognitiveAgent):
    """
    Cognitive Agent responsible for short-term price forecasting.
    """
    def __init__(self, engine: DecisionGradeInferenceEngine):
        super().__init__("forecast_agent")
        self.engine = engine

    async def perceive_and_reason(self, commodity: str, mandi_id: str, context: Dict[str, Any]) -> AgentSignal:
        try:
            ml_res = await self.engine.predict(commodity, mandi_id)
            
            return AgentSignal(
                agent_id=self.agent_id,
                commodity=commodity,
                mandi_id=mandi_id,
                signal_type="price_forecast",
                value=ml_res["predicted_price"],
                confidence=ml_res["confidence"],
                urgency=0.6 if ml_res["trend"] != "stable" else 0.2,
                recommendation=f"Expect {ml_res['trend']} price movement.",
                supporting_evidence=ml_res["explanation"],
                metadata={"trend": ml_res["trend"]}
            )
        except Exception as e:
            logger.error(f"ForecastAgent failed: {e}")
            raise

class VolatilityAgent(CognitiveAgent):
    """
    Cognitive Agent responsible for monitoring market turbulence and regime shifts.
    """
    def __init__(self):
        super().__init__("volatility_agent")

    async def perceive_and_reason(self, commodity: str, mandi_id: str, context: Dict[str, Any]) -> AgentSignal:
        # Reasoning logic based on price history in context
        # (Simplified for now, would use real variance analysis)
        vol_score = context.get("volatility_score", 0.3)
        is_high = vol_score > 0.6
        
        return AgentSignal(
            agent_id=self.agent_id,
            commodity=commodity,
            mandi_id=mandi_id,
            signal_type="market_turbulence",
            value="high" if is_high else "low",
            confidence=0.85,
            urgency=0.9 if is_high else 0.1,
            recommendation="Monitor spreads closely" if is_high else "Stable trading conditions.",
            supporting_evidence=f"Variance at {vol_score:.2f} relative to 7-day median.",
            uncertainty_flags=["flash_spike_risk"] if is_high else []
        )

class ArrivalAgent(CognitiveAgent):
    """
    Cognitive Agent responsible for analyzing supply pressure from mandi inflows.
    """
    def __init__(self):
        super().__init__("arrival_agent")

    async def perceive_and_reason(self, commodity: str, mandi_id: str, context: Dict[str, Any]) -> AgentSignal:
        arrival_trend = context.get("arrival_trend", "stable")
        
        return AgentSignal(
            agent_id=self.agent_id,
            commodity=commodity,
            mandi_id=mandi_id,
            signal_type="supply_pressure",
            value=arrival_trend,
            confidence=0.75,
            urgency=0.5 if arrival_trend != "stable" else 0.1,
            recommendation="Supply tightening detected" if arrival_trend == "decreasing" else "Adequate supply.",
            supporting_evidence=f"Arrivals are {arrival_trend} over last 3 updates."
        )
