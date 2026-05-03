import asyncio
from typing import Dict, Any
from mandisense_ai.core.orchestrator.inference_orchestrator import InferenceOrchestrator
from mandisense_ai.core.agents.decision_engine import MandiDecisionEngine

class DecisionOrchestrator:
    def __init__(self):
        self.inference_orch = InferenceOrchestrator()
        self.decision_engine = MandiDecisionEngine()

    async def get_actionable_decision(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        """
        Flow: InferenceOrch -> Decision Logic -> Consistency Rules
        """
        # 1. Get Forecasts
        forecast = await self.inference_orch.run_inference(commodity, mandi_id)
        
        if forecast.get("status") == "error":
            return self._fail_safe(commodity, mandi_id, forecast["explanation"])
            
        # 2. Apply Decision Logic
        try:
            # Decision engine is now async
            decision = await self.decision_engine.get_decision(commodity, mandi_id)
            
            # STEP 11 Override: If risk is HIGH, always suggest WAIT
            if forecast["risk_level"] == "HIGH":
                decision["decision"] = "WAIT"
                decision["reasoning"] += " (Overridden due to high market risk)"
                
            return decision
            
        except Exception as e:
            return self._fail_safe(commodity, mandi_id, str(e))

    def _fail_safe(self, commodity, mandi_id, reason):
        return {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "decision": "WAIT",
            "confidence": 0.0,
            "risk_level": "HIGH",
            "signal_strength": "WEAK",
            "price_change_pct": 0.0,
            "reasoning": f"Decision engine unavailable: {reason}"
        }
