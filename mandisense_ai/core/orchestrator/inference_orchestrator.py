"""Single-series inference for the legacy `/predict` route, answered from the validated forecast service."""

from typing import Any, Dict

from mandisense_ai.cognition.forecast_engine import ForecastBackedEngine


class InferenceOrchestrator:
    def __init__(self):
        self.engine = ForecastBackedEngine()

    async def run_inference(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        try:
            prediction = await self.engine.predict(commodity.lower(), mandi_id)
        except Exception as exc:
            return self._fail_safe(commodity, mandi_id, str(exc))
        prediction["is_stale"] = False
        return prediction

    def _fail_safe(self, commodity: str, mandi_id: str, reason: str) -> Dict[str, Any]:
        return {"predicted_price": 0.0, "confidence": 0.0, "trend": "stable", "explanation": f"No validated forecast: {reason}",
                "predicted_arrivals": 0.0, "arrival_signal": "unknown", "is_stale": True, "status": "error", "reason": reason}
