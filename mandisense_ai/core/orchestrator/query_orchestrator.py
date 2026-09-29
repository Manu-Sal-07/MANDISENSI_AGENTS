from typing import Any, Dict

from mandisense_ai.core.orchestrator.decision_orchestrator import DecisionOrchestrator
from mandisense_ai.core.orchestrator.query_parser import (
    describe_gap,
    parse_market_query,
    supported_commodities,
    supported_mandis,
)

SUMMARIES = {
    "SELL": "Prices are likely to fall soon, selling now is advised.",
    "HOLD": "A positive price trend is expected, holding is recommended.",
    "WAIT": "Market signals are mixed; staying cautious is best.",
}


class QueryOrchestrator:
    """Turns a free-text market question into an actionable decision."""

    def __init__(self):
        self.decision_orch = DecisionOrchestrator()

    async def handle_user_query(self, query_text: str) -> Dict[str, Any]:
        """
        Flow: parse -> decision -> response.

        An incomplete question is answered with the specific missing piece
        rather than a generic refusal, and the response carries `needs` so the
        UI can prompt for exactly that.
        """
        parsed = parse_market_query(query_text)

        if not parsed.is_complete:
            return {
                "decision": "WAIT",
                "summary": "I need a little more detail",
                "reasoning": describe_gap(parsed),
                "market_insight": "Incomplete query",
                "metadata": {
                    "commodity": parsed.commodity,
                    "mandi_id": parsed.mandi_id,
                    "confidence": 0.0,
                    "needs": parsed.missing,
                    "supported_commodities": supported_commodities(),
                    "supported_mandis": supported_mandis(),
                },
            }

        # The parsed horizon is passed through rather than discarded. It used
        # to be extracted correctly and then only interpolated into a display
        # string, so "should I sell tomorrow" and "what about in 15 days"
        # produced byte-identical answers.
        decision = await self.decision_orch.get_actionable_decision(
            parsed.commodity, parsed.mandi_id, horizon_days=parsed.horizon_days
        )

        served_horizon = decision.get("horizon_days")
        market_insight = f"Price change: {decision.get('price_change_pct', 0)}%"
        if served_horizon:
            market_insight += f" over {served_horizon} day(s)"
        if parsed.horizon_days and served_horizon and int(parsed.horizon_days) != int(served_horizon):
            market_insight += f" · nearest published horizon to the {parsed.horizon_days} you asked about"

        action = decision.get("decision", "WAIT")
        status = decision.get("status")
        summary = (
            SUMMARIES.get(action, "Stay cautious.")
            if status == "OK"
            else "No forecast is available for this market yet."
        )

        return {
            "decision": action,
            "summary": summary,
            "reasoning": decision.get("reasoning", ""),
            "market_insight": market_insight,
            "metadata": {
                "commodity": parsed.commodity,
                "mandi_id": parsed.mandi_id,
                "confidence": decision.get("confidence", 0.0),
                "horizon_days": parsed.horizon_days,
                "served_horizon_days": served_horizon,
                "status": status,
                "interval": decision.get("interval"),
                "probability_of_decline": decision.get("probability_of_decline"),
                "as_of_date": decision.get("as_of_date"),
                "freshness": decision.get("freshness"),
                "needs": [],
            },
        }
