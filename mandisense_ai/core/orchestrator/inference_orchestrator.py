import asyncio
from typing import Dict, Any
from mandisense_ai.core.data.data_service import MandiDataService
from mandisense_ai.core.agents.inference_engine_v3 import DecisionGradeInferenceEngine

class InferenceOrchestrator:
    def __init__(self):
        self.data_service = MandiDataService.get_instance()
        self.engine = DecisionGradeInferenceEngine()

    async def run_inference(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        """
        Flow: DataService -> Input Prep -> Engine -> Response
        """
        # 1. Fetch Data
        data_input = await self.data_service.prepare_inference_input(commodity, mandi_id)
        
        if data_input["status"] == "error":
            return self._fail_safe(commodity, mandi_id, data_input["reason"])
            
        # 2. Run Model Inference (Engine v3)
        try:
            # Engine v3 is now async
            prediction = await self.engine.predict(commodity, mandi_id)
            
            # 3. Enrich with Metadata
            prediction["is_stale"] = data_input["is_stale"]
            prediction["data_version"] = data_input["metadata"].get("version_id")
            
            # STEP 6: STALENESS HANDLING
            if data_input["is_stale"]:
                prediction["confidence"] *= 0.7 # Reduce confidence for stale data
                prediction["explanation"] += " (Warning: Data is stale, confidence reduced)"
                
            return prediction
            
        except Exception as e:
            return self._fail_safe(commodity, mandi_id, str(e))

    def _fail_safe(self, commodity, mandi_id, reason):
        return {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "predicted_price": 0.0,
            "predicted_arrivals": 0.0,
            "confidence": 0.0,
            "risk_level": "HIGH",
            "trend": "stable",
            "explanation": f"Inference failed: {reason}",
            "status": "error"
        }
