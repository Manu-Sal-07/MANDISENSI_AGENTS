import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("OperationalVerification")

class OutcomeMetric(BaseModel):
    plan_id: str
    commodity: str
    action_type: str
    target_mandi: str
    effectiveness_score: float # -1.0 to 1.0 (Did it work?)
    price_delta_saved: float
    volatility_reduction: float
    timestamp: datetime

class OperationalVerificationEngine:
    """
    Closed-Loop Operational Verification.
    "Learning from real-world consequences."
    """
    def __init__(self):
        self.outcomes: List[OutcomeMetric] = []

    def verify_plan_outcome(self, plan: Any, final_state: Any, baseline_state: Any):
        """
        Compares the expected vs actual outcome of an execution plan.
        """
        # Logic: If plan was 'SWITCH_CORRIDOR', did the target mandi price remain stable?
        # If plan was 'DELAY', did we avoid a price peak?
        
        price_saved = 0.0
        if baseline_state and final_state:
            price_saved = baseline_state.price_prediction - final_state.price_prediction
            
        # Simplified effectiveness calculation
        effectiveness = 0.5 # Default
        if price_saved > 0:
            effectiveness += 0.3
        if final_state.deliberation.chaos_score < (baseline_state.deliberation.chaos_score if baseline_state else 1.0):
            effectiveness += 0.2
            
        outcome = OutcomeMetric(
            plan_id=plan.id,
            commodity=plan.commodity,
            action_type=plan.actions[0].type if plan.actions else "UNKNOWN",
            target_mandi=plan.actions[0].target_mandi if plan.actions else "UNKNOWN",
            effectiveness_score=min(1.0, effectiveness),
            price_delta_saved=price_saved,
            volatility_reduction=(baseline_state.deliberation.chaos_score - final_state.deliberation.chaos_score) if baseline_state else 0.0,
            timestamp=datetime.now()
        )
        
        self.outcomes.append(outcome)
        logger.info(f"Operational Verification Complete: Plan {plan.id} Effectiveness: {outcome.effectiveness_score:.2f}")
        return outcome

    def get_institutional_effectiveness(self) -> Dict[str, Any]:
        if not self.outcomes:
            return {"overall_effectiveness": 1.0, "total_verified_plans": 0}
            
        avg_score = sum(o.effectiveness_score for o in self.outcomes) / len(self.outcomes)
        total_saved = sum(o.price_delta_saved for o in self.outcomes)
        
        return {
            "overall_effectiveness": avg_score,
            "total_verified_plans": len(self.outcomes),
            "total_price_delta_stabilized": total_saved,
            "success_rate": len([o for o in self.outcomes if o.effectiveness_score > 0.6]) / len(self.outcomes)
        }
