"""
Decision Intelligence Engine for MandiSense AI.
Transforms raw ML predictions into actionable insights for farmers and traders.
"""

from typing import Dict, Any, Optional

def generate_decision(
    prediction: float, 
    confidence: float, 
    metadata: Dict[str, Any], 
    status: str = "success"
) -> Dict[str, Any]:
    """
    Translates ML metrics into a human-readable decision structure.
    Refined for better actionability and clarity.
    """
    
    # ── 1. Fallback Handling ──────────────────────────────────────────
    if status == "fallback":
        return {
            "decision": "WAIT",
            "risk_level": "HIGH",
            "action_strength": "WEAK",
            "direction": "STABLE",
            "confidence_label": "LOW",
            "summary": "System uncertainty — unable to generate reliable prediction",
            "reasoning": "Prediction unavailable due to timeout or internal error. Market signals are currently opaque.",
            "signals": {
                "trend": "STABLE",
                "supply": "NORMAL",
                "volatility": "HIGH",
                "conflict": True
            }
        }

    # ── 2. Safe Extraction ────────────────────────────────────────────
    volatility = metadata.get("volatility", metadata.get("volatility_7d", metadata.get("return_std", 0.3)))
    supply_stress = metadata.get("supply_stress_score", metadata.get("supply_stress", 0.5))
    
    if volatility > 1.0: volatility = volatility / 100.0

    # ── 3. Signal Logic ───────────────────────────────────────────────
    # Trend
    if prediction > 1.0: trend = "UP"
    elif prediction < -1.0: trend = "DOWN"
    else: trend = "STABLE"
    
    # Supply
    if supply_stress > 0.7: supply = "TIGHT"
    elif supply_stress < 0.3: supply = "HIGH"
    else: supply = "NORMAL"
    
    # Volatility
    if volatility > 0.6: vol_label = "HIGH"
    elif volatility > 0.3: vol_label = "MEDIUM"
    else: vol_label = "LOW"
    
    # Conflict detection (e.g., price UP but supply HIGH)
    is_conflict = (trend == "UP" and supply == "HIGH") or (trend == "DOWN" and supply == "TIGHT")

    # ── 4. Action Strength ───────────────────────────────────────────
    abs_pred = abs(prediction)
    if abs_pred > 3.0 and confidence >= 0.7:
        action_strength = "STRONG"
    elif abs_pred >= 1.5 and confidence >= 0.5:
        action_strength = "MODERATE"
    else:
        action_strength = "WEAK"

    # ── 5. Decision & Risk ────────────────────────────────────────────
    # Reduced WAIT usage
    if confidence < 0.4 or (volatility > 0.7 and is_conflict):
        decision = "WAIT"
    elif prediction < -1.5:
        decision = "SELL"
    elif prediction > 1.5:
        decision = "HOLD"
    else:
        # Lean SELL or HOLD even on weak signals
        decision = "SELL" if prediction < 0 else "HOLD"

    # Risk Level
    if volatility > 0.6 or confidence < 0.4:
        risk_level = "HIGH"
    elif confidence >= 0.7 and volatility < 0.4:
        risk_level = "LOW"
    else:
        risk_level = "MEDIUM"

    # ── 6. Summary & Reasoning ───────────────────────────────────────
    conf_word = "high" if confidence >= 0.7 else "moderate" if confidence >= 0.4 else "low"
    strength_word = "strong" if abs_pred > 3.0 else "steady" if abs_pred > 1.5 else "slight"
    
    # Temporal Clarity in Summary
    if trend == "UP":
        summary = f"Prices likely to increase by ~{prediction:.1f}% over the next 7 days (short-term outlook)"
    elif trend == "DOWN":
        summary = f"Prices expected to fall by ~{abs(prediction):.1f}% over the next 7 days (short-term outlook)"
    else:
        summary = "Prices expected to remain relatively stable over the next 7 days"

    # Confidence-Aware Reasoning
    reason_parts = [f"Prices are expected to {trend.lower()} with {conf_word} confidence."]
    
    if supply == "TIGHT":
        reason_parts.append("Reduced arrivals are causing a supply squeeze.")
    elif supply == "HIGH":
        reason_parts.append("High arrival volumes are putting pressure on prices.")
    
    if is_conflict:
        reason_parts.append("Note: Market signals are currently conflicting, increasing overall risk.")
    
    if vol_label == "HIGH":
        reason_parts.append("Significant price volatility detected.")

    return {
        "decision": decision,
        "risk_level": risk_level,
        "action_strength": action_strength,
        "direction": trend,
        "confidence_label": conf_word.upper(),
        "summary": summary,
        "reasoning": " ".join(reason_parts),
        "signals": {
            "trend": trend,
            "supply": supply,
            "volatility": vol_label,
            "conflict": is_conflict
        }
    }

