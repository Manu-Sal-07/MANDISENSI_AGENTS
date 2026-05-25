import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("OrchestrationEngine")

class OperationalAction(BaseModel):
    id: str
    type: str # "PROCURE", "DELAY", "SWITCH_CORRIDOR", "STABILIZE_INVENTORY", "ESCALATE"
    target_mandi: str
    urgency: str # "CRITICAL", "NORMAL", "LOW"
    status: str = "PENDING" # "PENDING", "APPROVED", "EXECUTED", "OVERRIDDEN"
    reasoning: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionPlan(BaseModel):
    id: str
    commodity: str
    created_at: datetime
    actions: List[OperationalAction]
    overall_status: str = "PROPOSED" # "PROPOSED", "ACTIVE", "COMPLETED", "ABORTED"
    risk_level: str

class OrchestrationEngine:
    """
    Industrial Execution Orchestration Infrastructure.
    Transforms strategic cognition into operational action sequences.
    """
    def __init__(self):
        self.active_plans: Dict[str, ExecutionPlan] = {}

    def get_empty_plan(self, reason: str = "Safety Restraint") -> ExecutionPlan:
        """
        Returns a safety-restrained empty plan.
        """
        return ExecutionPlan(
            id=f"plan_SAFE_{datetime.now().timestamp()}",
            commodity="UNKNOWN",
            created_at=datetime.now(),
            actions=[OperationalAction(
                id="act_safety_freeze",
                type="SAFETY_FREEZE",
                target_mandi="SYSTEM",
                urgency="CRITICAL",
                reasoning=f"Institutional Safety Gate Triggered: {reason}. No automated orchestration permitted."
            )],
            risk_level="CRITICAL",
            overall_status="ABORTED"
        )

    def synthesize_response(self, market_state: Any) -> ExecutionPlan:
        """
        Dynamically generates an execution plan based on market state cognition.
        "Orchestrating the organizational response."
        """
        commodity = market_state.commodity
        mandi_id = market_state.mandi_id
        risk = market_state.risk_level
        chaos = market_state.deliberation.chaos_score
        integrity = getattr(market_state, "integrity_status", "FULL_COGNITION")
        
        # 0. Safety Gate (Phase 5A)
        if integrity in ["COGNITION_FAILED", "ORCHESTRATION_UNSAFE"]:
            return self.get_empty_plan(f"Cognition Integrity Failure ({integrity})")
        
        actions = []
        plan_risk = risk
        
        # 1. Logic for Orchestration Sequencing
        if risk == "CRITICAL" or chaos > 0.7:
            actions.append(OperationalAction(
                id=f"act_{datetime.now().timestamp()}_1",
                type="ESCALATE",
                target_mandi=mandi_id,
                urgency="CRITICAL",
                reasoning="Structural instability or high cognitive chaos detected. Human intervention required."
            ))
            actions.append(OperationalAction(
                id=f"act_{datetime.now().timestamp()}_2",
                type="SWITCH_CORRIDOR",
                target_mandi=mandi_id,
                urgency="HIGH",
                reasoning="Current corridor showing signs of collapse. Activating fallback routing.",
                metadata={"fallback_mandi": "bangalore_apmc"}
            ))
            actions.append(OperationalAction(
                id=f"act_{datetime.now().timestamp()}_3",
                type="STABILIZE_INVENTORY",
                target_mandi="LOCAL_HUB",
                urgency="NORMAL",
                reasoning="Mitigating supply compression by freezing outward allocation."
            ))
        elif risk == "HIGH":
            actions.append(OperationalAction(
                id=f"act_{datetime.now().timestamp()}_1",
                type="DELAY",
                target_mandi=mandi_id,
                urgency="NORMAL",
                reasoning="Wait for volatility peak before committing bulk orders.",
                metadata={"delay_hours": 24}
            ))
            actions.append(OperationalAction(
                id=f"act_{datetime.now().timestamp()}_2",
                type="PROCURE",
                target_mandi=mandi_id,
                urgency="NORMAL",
                reasoning="Execution scheduled post-peak stabilization.",
                status="PENDING"
            ))
        else:
            actions.append(OperationalAction(
                id=f"act_{datetime.now().timestamp()}_1",
                type="PROCURE",
                target_mandi=mandi_id,
                urgency="NORMAL",
                reasoning="Standard procurement cycle execution."
            ))

        plan = ExecutionPlan(
            id=f"plan_{commodity}_{datetime.now().timestamp()}",
            commodity=commodity,
            created_at=datetime.now(),
            actions=actions,
            risk_level=plan_risk
        )
        
        self.active_plans[plan.id] = plan
        return plan

    def approve_action(self, plan_id: str, action_id: str):
        if plan_id in self.active_plans:
            plan = self.active_plans[plan_id]
            for action in plan.actions:
                if action.id == action_id:
                    action.status = "APPROVED"
                    logger.info(f"Action {action_id} approved for plan {plan_id}")
                    # In a real system, this would trigger actual logistics API calls
                    break

    def get_active_plans(self, commodity: Optional[str] = None) -> List[ExecutionPlan]:
        plans = list(self.active_plans.values())
        if commodity:
            plans = [p for p in plans if p.commodity == commodity]
        return sorted(plans, key=lambda x: x.created_at, reverse=True)
