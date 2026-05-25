from typing import Dict, Any

class DirectiveSynthesizer:
    """
    Converts raw forecasts and market states into actionable procurement directives.
    This is the "Monetizable Cognition Layer".
    """
    
    def synthesize(self, ml_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw ML output and returns a directive snapshot.
        """
        trend = ml_output.get("trend", "stable")
        confidence = ml_output.get("confidence", 0.5)
        risk_level = ml_output.get("risk_level", "MEDIUM")
        volatility = ml_output.get("volatility", "low")
        arrival_signal = ml_output.get("arrival_signal", "stable")
        
        directive = "Monitor Market"
        urgency = "NORMAL"
        action_code = "MONITOR"
        reasoning = ml_output.get("explanation", "")

        # Logic for Directive Synthesis
        if trend == "upward":
            if confidence > 0.75:
                directive = "Accelerate Procurement"
                urgency = "HIGH"
                action_code = "ACCELERATE"
            else:
                directive = "Watch for Entry Point"
                urgency = "MEDIUM"
                action_code = "WATCH"
        
        elif trend == "downward":
            if risk_level == "LOW" or confidence > 0.7:
                directive = "Delay Procurement"
                urgency = "LOW"
                action_code = "DELAY"
            else:
                directive = "Wait for Bottom"
                urgency = "MEDIUM"
                action_code = "WAIT"

        if volatility == "high":
            directive = f"{directive} (Cautious Execution)"
            action_code = f"{action_code}_CAUTION"

        # Special Case: Supply Pressure
        if arrival_signal == "decreasing" and trend == "upward":
            directive = "Immediate Procurement Required"
            urgency = "CRITICAL"
            action_code = "IMMEDIATE"

        return {
            "directive": directive,
            "urgency": urgency,
            "action_code": action_code,
            "confidence_score": confidence,
            "primary_driver": "price_trend" if trend != "stable" else "arrival_pressure",
            "reasoning_summary": reasoning
        }
