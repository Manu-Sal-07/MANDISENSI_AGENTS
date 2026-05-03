import pandas as pd
import numpy as np
import json
from pathlib import Path
from mandisense_ai.core.agents.inference_engine_v3 import DecisionGradeInferenceEngine

class MandiDecisionEngine:
    def __init__(self):
        self.inference_engine = DecisionGradeInferenceEngine()
        
    async def get_decision(self, commodity, mandi_id):
        try:
            # Run Inference
            inf_res = await self.inference_engine.predict(commodity, mandi_id)
            
            # Fetch last price from data service (already async)
            from mandisense_ai.core.data.data_service import MandiDataService
            ds = MandiDataService.get_instance()
            series, _, _ = await ds.get_mandi_series(commodity, mandi_id, window=1)
            last_price = series['price'].iloc[-1]
            
            # STEP 1: DERIVE CORE SIGNALS
            pred_price = inf_res['predicted_price']
            price_change_pct = (pred_price - last_price) / last_price
            abs_change = abs(price_change_pct)
            
            if abs_change > 0.05: signal_strength = "STRONG"
            elif abs_change > 0.02: signal_strength = "MODERATE"
            else: signal_strength = "WEAK"
            
            # STEP 2: ECONOMIC CONSISTENCY CHECK
            conflict_flag = False
            arrival_signal = inf_res['arrival_signal']
            trend = inf_res['trend']
            
            if (arrival_signal == "increasing" and trend == "upward") or \
               (arrival_signal == "decreasing" and trend == "downward"):
                conflict_flag = True
                
            # STEP 3 & 4: DECISION LOGIC & RISK ADJUSTMENT
            risk_level = inf_res['risk_level']
            conf = inf_res['confidence']
            dir_conf = inf_res['direction_confidence']
            volatility = inf_res['volatility']
            
            decision = "WAIT" # Default
            
            # SELL Logic
            if trend == "downward" and dir_conf > 0.7 and risk_level != "HIGH" and signal_strength != "WEAK":
                decision = "SELL"
            elif trend == "upward" and signal_strength == "WEAK" and risk_level == "HIGH":
                decision = "SELL" # Exit before reversal
                
            # HOLD Logic
            elif trend == "upward" and dir_conf > 0.65 and risk_level == "LOW" and arrival_signal != "increasing":
                decision = "HOLD"
                
            # WAIT Logic (Overrides)
            if risk_level == "HIGH" or conf < 0.6 or conflict_flag:
                decision = "WAIT"
            
            if volatility == "high" and decision != "SELL":
                decision = "WAIT" # Risk-off in high volatility
                
            # STEP 6: NATURAL LANGUAGE REASONING
            reasoning = self._build_reasoning(commodity, mandi_id, inf_res, price_change_pct, decision, conflict_flag)
            
            return {
                "commodity": commodity,
                "mandi_id": mandi_id,
                "decision": decision,
                "confidence": conf,
                "risk_level": risk_level,
                "signal_strength": signal_strength,
                "price_change_pct": float(round(price_change_pct * 100, 2)),
                "reasoning": reasoning,
                "raw_inference": inf_res
            }
            
        except Exception as e:
            return {
                "decision": "WAIT",
                "reasoning": f"System encountered an error while processing the request: {str(e)}",
                "risk_level": "HIGH"
            }

    def _build_reasoning(self, commodity, mandi_id, inf, pct_change, decision, conflict):
        trend = inf['trend']
        arr_sig = inf['arrival_signal']
        risk = inf['risk_level']
        
        text = f"In {mandi_id}, {commodity} prices are expected to {trend} by approximately {abs(pct_change)*100:.1f}%. "
        
        if arr_sig == "increasing":
            text += "Arrivals are increasing, which typically puts downward pressure on prices. "
        else:
            text += "Declining arrivals suggest tightening supply, which supports price levels. "
            
        if conflict:
            text += "However, there is a conflict between supply signals and price trends. "
            
        if decision == "HOLD":
            text += f"Given the low risk and upward trend, we recommend holding for a better price."
        elif decision == "SELL":
            text += f"Expected downward pressure suggests selling now to lock in current rates."
        else:
            text += f"Due to {risk.lower()} risk and market uncertainty, it is safer to wait for clearer signals."
            
        return text

if __name__ == "__main__":
    import asyncio
    async def test():
        engine = MandiDecisionEngine()
        print("--- MANDISENSE DECISION TEST ---")
        res = await engine.get_decision("tomato", "kolar_apmc")
        print(json.dumps(res, indent=2))
    asyncio.run(test())
