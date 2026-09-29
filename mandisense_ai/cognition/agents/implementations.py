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
                metadata={
                    "trend": ml_res["trend"],
                    "predicted_arrivals": ml_res["predicted_arrivals"],
                    "arrival_signal": ml_res["arrival_signal"]
                }
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
        # `volatility_score` is supplied by `CognitionEngine.generate_cognition`
        # from the published forecast's calibrated 90% band width relative to
        # price — a measured quantity. This used to read a key the engine
        # never passed, so the `0.3` default resolved on every call and this
        # agent reported "low" volatility at 0.85 confidence for every
        # commodity, at every mandi, on every run. That constant is why all
        # ten live snapshots report LOW risk. Where the measurement is
        # genuinely unavailable it now abstains rather than inventing calm.
        vol_score = context.get("volatility_score")

        if vol_score is None:
            return AgentSignal(
                agent_id=self.agent_id,
                commodity=commodity,
                mandi_id=mandi_id,
                signal_type="market_turbulence",
                value="unknown",
                confidence=0.0,
                urgency=0.0,
                recommendation="Volatility could not be measured for this series.",
                supporting_evidence="No published forecast band for this series.",
                uncertainty_flags=["volatility_unmeasured"],
            )

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
            supporting_evidence=(
                f"Calibrated 90% forecast band spans {vol_score * 100:.0f}% of price."
            ),
            uncertainty_flags=["flash_spike_risk"] if is_high else []
        )

class ArrivalAgent(CognitiveAgent):
    """
    Cognitive Agent responsible for analyzing supply pressure from mandi inflows.
    """
    def __init__(self):
        super().__init__("arrival_agent")

    async def perceive_and_reason(self, commodity: str, mandi_id: str, context: Dict[str, Any]) -> AgentSignal:
        # Same defect as the volatility agent: this read a key the engine
        # never set, so every call returned "stable" at 0.75 confidence
        # regardless of what arrivals were doing. Measured from the
        # observation store now, and absent data is reported as absent
        # rather than as adequate supply.
        arrival_trend = context.get("arrival_trend")

        if arrival_trend is None:
            return AgentSignal(
                agent_id=self.agent_id,
                commodity=commodity,
                mandi_id=mandi_id,
                signal_type="supply_pressure",
                value="unknown",
                confidence=0.0,
                urgency=0.0,
                recommendation="Arrival volumes are not available for this series.",
                supporting_evidence=(
                    "The free daily feed publishes price but not arrival volume, "
                    "and no archived arrivals cover this series recently."
                ),
                uncertainty_flags=["arrivals_unmeasured"],
            )

        return AgentSignal(
            agent_id=self.agent_id,
            commodity=commodity,
            mandi_id=mandi_id,
            signal_type="supply_pressure",
            value=arrival_trend,
            confidence=0.75,
            urgency=0.5 if arrival_trend != "stable" else 0.1,
            recommendation="Supply tightening detected" if arrival_trend == "decreasing" else "Adequate supply.",
            supporting_evidence=(
                f"Arrivals are {arrival_trend} versus their trailing 30-day average."
            )
        )
