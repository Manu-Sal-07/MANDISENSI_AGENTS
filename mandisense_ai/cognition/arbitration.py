import logging
from typing import List, Dict, Any
from mandisense_ai.cognition.agents.base import AgentSignal
from mandisense_ai.cognition.ontology import MarketState, MarketRegime, RiskLevel

logger = logging.getLogger("ArbitrationEngine")

class SignalArbitrator:
    """
    Institutional Cognition Arbitration Engine.
    Resolves contradictions, weights evidence, and synthesizes operational truth.
    """
    
    def arbitrate(self, signals: List[AgentSignal]) -> Dict[str, Any]:
        """
        Synthesizes multiple agent signals into a unified cognition snapshot.
        """
        # 0. Safety Check (Phase 5B)
        if not signals:
            logger.error("CRITICAL: No signals provided for arbitration.")
            return self.get_empty_result()

        # 1. Signal Sorting by Urgency and Confidence
        sorted_signals = sorted(signals, key=lambda s: (s.urgency, s.confidence), reverse=True)
        
        # 2. Contradiction Detection
        contradictions = self._detect_contradictions(signals)
        if contradictions:
            logger.warning(f"Detected {len(contradictions)} cognitive contradictions.")
            
        # 3. Dynamic Weighting (Initial Version)
        # In institutional systems, some agents dominate in certain regimes
        weights = self._calculate_adaptive_weights(signals)
        
        # 4. Meta-Cognition: Calculate Signal Chaos
        chaos_score = len(contradictions) / len(signals)
        
        # Institutional Doubt check (Phase 5B)
        # If all agents agree with 100% confidence, we inject a small doubt factor
        avg_conf = sum(s.confidence for s in signals) / len(signals)
        if avg_conf > 0.98 and len(contradictions) == 0:
            logger.warning("Institutional Doubt: Perfect consensus detected. Investigating potential echo chamber.")
            chaos_score = 0.05 # Inject tiny chaos to prevent overconfidence
            
        # 5. Synthesis
        # We find the dominant forecast and adjust by other signals
        forecast = next((s for s in signals if s.agent_id == "forecast_agent"), None)
        volatility = next((s for s in signals if s.agent_id == "volatility_agent"), None)
        arrivals = next((s for s in signals if s.agent_id == "arrival_agent"), None)
        
        # Resolve Risk Level
        risk_level = RiskLevel.LOW
        if volatility and volatility.value == "high":
            risk_level = RiskLevel.HIGH
        elif chaos_score > 0.5:
            risk_level = RiskLevel.MEDIUM 
            
        # 6. Narrative Synthesis
        narrative = self._synthesize_narrative(forecast, volatility, arrivals, contradictions)
        
        return {
            "primary_signals": [s.dict() for s in signals],
            "contradictions": contradictions,
            "chaos_score": chaos_score,
            "synthesized_risk": risk_level,
            "narrative": narrative,
            "meta": {
                "consensus": "low" if chaos_score > 0.3 else "high",
                "dominant_agent": sorted_signals[0].agent_id if sorted_signals else "none"
            }
        }

    def get_empty_result(self) -> Dict[str, Any]:
        return {
            "primary_signals": [],
            "contradictions": ["ORCHESTRATION_FAILURE: No intelligence signals received."],
            "chaos_score": 1.0,
            "synthesized_risk": RiskLevel.CRITICAL,
            "narrative": "Cognition collapse: System unable to synthesize market state.",
            "meta": { "consensus": "none", "dominant_agent": "none" }
        }

    def _detect_contradictions(self, signals: List[AgentSignal]) -> List[str]:
        contradictions = []
        forecast = next((s for s in signals if s.agent_id == "forecast_agent"), None)
        arrivals = next((s for s in signals if s.agent_id == "arrival_agent"), None)
        
        if forecast and arrivals:
            # Traditional contradiction: Price rising but supply also rising
            if forecast.metadata.get("trend") == "upward" and arrivals.value == "increasing":
                contradictions.append("Supply-Price Divergence: Price rising despite arrival acceleration.")
                
        return contradictions

    def _calculate_adaptive_weights(self, signals: List[AgentSignal]) -> Dict[str, float]:
        # Placeholder for dynamic weighting logic from Section 4
        return {s.agent_id: 1.0 for s in signals}

    def _synthesize_narrative(self, f, v, a, contradictions) -> str:
        text = "Market state stabilized. "
        if f: text = f.supporting_evidence + " "
        if v and v.value == "high": text += "However, volatility is elevated. "
        if contradictions: text += f"System alert: {contradictions[0]}"
        return text.strip()
