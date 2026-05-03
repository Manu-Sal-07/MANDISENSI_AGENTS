import json
import re
from mandisense_ai.core.agents.decision_engine import MandiDecisionEngine

class QueryIntelligence:
    def __init__(self):
        self.decision_engine = MandiDecisionEngine()
        
        # Mappings for simple extraction
        self.MANDI_MAP = {
            "kolar": "kolar_apmc",
            "ramanagara": "ramanagara_apmc",
            "bangalore": "bangalore_yeshwanthpur",
            "chickballapur": "chickballapur_apmc",
            "hoskote": "hoskote_apmc",
            "nelamangala": "nelamangala_apmc",
            "anekal": "anekal_apmc",
            "doddaballapur": "doddaballapur_apmc",
            "malur": "malur_apmc",
            "magadi": "magadi_apmc",
            "kanakapura": "kanakapura_apmc",
            "sidlaghatta": "sidlaghatta_apmc",
            "channapatna": "channapatna_apmc",
            "kunigal": "kunigal_apmc",
            "bangarpet": "bangarpet_apmc"
        }
        
        self.COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]

    def process_query(self, query):
        # STEP 1: EXTRACT CONTEXT
        query_lower = query.lower()
        
        commodity = None
        for c in self.COMMODITIES:
            if c in query_lower:
                commodity = c
                break
                
        mandi_id = None
        for m_key, m_val in self.MANDI_MAP.items():
            if m_key in query_lower:
                mandi_id = m_val
                break
                
        if not commodity or not mandi_id:
            return self._error_response("I couldn't identify the commodity or mandi. Please ask like: 'Should I sell tomatoes in Kolar today?'")
            
        # STEP 2 & 3: CALL DECISION ENGINE
        result = self.decision_engine.get_decision(commodity, mandi_id)
        
        if result.get("decision") == "WAIT" and "error" in result.get("reasoning", "").lower():
             return self._error_response(result["reasoning"])
             
        # STEP 5: GENERATE RESPONSE
        return self._format_response(result)

    def _format_response(self, res):
        decision = res["decision"]
        inf = res["raw_inference"]
        
        # Summary mapping
        summaries = {
            "SELL": "Prices are likely to fall soon, selling now is advised to maximize profit.",
            "HOLD": "A positive price trend is expected, holding may yield better returns.",
            "WAIT": "Market signals are mixed or risky; staying cautious is the best strategy today."
        }
        
        # Market Insight
        pred_price = inf["predicted_price"]
        pct = res["price_change_pct"]
        gain_loss = pred_price * (abs(pct)/100)
        
        insight = f"Prices are currently at a stable level. "
        if pct > 0:
            insight += f"There is a potential gain of Rs.{gain_loss:.2f} per quintal if the trend continues."
        else:
            insight += f"Selling now helps avoid a potential loss of Rs.{gain_loss:.2f} per quintal."

        response = f"""
### FINAL RESPONSE

**Decision:** {decision}

**Summary:**
{summaries.get(decision, "Please stay cautious.")}

**Reasoning:**
{res["reasoning"]}

**Market Insight:**
{insight}
"""
        return response

    def _error_response(self, msg):
        return f"""
### SORRY
{msg}
"""

if __name__ == "__main__":
    qi = QueryIntelligence()
    
    print("--- MANDISENSE ADVISOR SIMULATION ---")
    
    queries = [
        "Should I sell tomatoes in Kolar today?",
        "Is it a good time to sell onions in Ramanagara?",
        "What should I do with potato stock in Bangalore mandi?"
    ]
    
    for q in queries:
        print(f"\nUser Query: {q}")
        print(qi.process_query(q))
