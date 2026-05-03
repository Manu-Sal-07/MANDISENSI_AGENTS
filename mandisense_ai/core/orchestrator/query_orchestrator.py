import asyncio
from typing import Dict, Any
from mandisense_ai.core.orchestrator.decision_orchestrator import DecisionOrchestrator
from mandisense_ai.orchestrator.query_intelligence import QueryIntelligence

class QueryOrchestrator:
    def __init__(self):
        self.decision_orch = DecisionOrchestrator()
        self.query_intel = QueryIntelligence()

    async def handle_user_query(self, query_text: str) -> Dict[str, Any]:
        """
        Flow: QueryIntel (Parse) -> DecisionOrch -> Response
        """
        # 1. Parse Context
        # (Reusing the parser from QueryIntelligence)
        query_lower = query_text.lower()
        
        commodity = None
        for c in self.query_intel.COMMODITIES:
            if c in query_lower:
                commodity = c
                break
                
        mandi_id = None
        for m_key, m_val in self.query_intel.MANDI_MAP.items():
            if m_key in query_lower:
                mandi_id = m_val
                break
                
        if not commodity or not mandi_id:
            return {
                "decision": "WAIT",
                "summary": "Context missing",
                "reasoning": "Please specify both a commodity and a mandi (e.g., 'tomatoes in Kolar').",
                "market_insight": "Incomplete query"
            }
            
        # 2. Get Decision
        decision = await self.decision_orch.get_actionable_decision(commodity, mandi_id)
        
        # 3. Format Response
        # (Reusing formatting logic)
        summaries = {
            "SELL": "Prices are likely to fall soon, selling now is advised.",
            "HOLD": "A positive price trend is expected, holding is recommended.",
            "WAIT": "Market signals are mixed; staying cautious is best."
        }
        
        return {
            "decision": decision["decision"],
            "summary": summaries.get(decision["decision"], "Stay cautious."),
            "reasoning": decision["reasoning"],
            "market_insight": f"Price change: {decision['price_change_pct']}%",
            "metadata": {
                "commodity": commodity,
                "mandi_id": mandi_id,
                "confidence": decision["confidence"]
            }
        }
