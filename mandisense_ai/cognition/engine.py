import asyncio
import logging
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from mandisense_ai.core.agents.inference_engine_v3 import DecisionGradeInferenceEngine
from mandisense_ai.cognition.state_store import MarketMemoryStore
from mandisense_ai.cognition.ontology import MarketState, MarketRegime, CognitionStatus
from mandisense_ai.cognition.agents.base import AgentRegistry, AgentSignal
from mandisense_ai.cognition.agents.implementations import ForecastAgent, VolatilityAgent, ArrivalAgent
from mandisense_ai.cognition.arbitration import SignalArbitrator
from mandisense_ai.cognition.memory import MetaCognitionEngine

# World Model & Institutional Layers
from mandisense_ai.cognition.world_model.topology import MarketTopology
from mandisense_ai.cognition.world_model.simulation import ShockPropagationSimulator
from mandisense_ai.cognition.world_model.corridors import ProcurementCorridorEngine
from mandisense_ai.cognition.memory_engine import InstitutionalMemoryEngine, StrategicMemory
from mandisense_ai.cognition.orchestration import OrchestrationEngine
from mandisense_ai.cognition.enterprise import EnterpriseCognitionHub
from mandisense_ai.cognition.verification import OperationalVerificationEngine

# Deployment & Reality Synchronizer (New in Phase 5)
from mandisense_ai.cognition.deployment import DeploymentManager, RealitySynchronizer


# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CognitionOrchestrator")

class CognitionEngine:
    """
    Unified Institutional Cognition Organism.
    "Operationally dependable enterprise infrastructure."
    """
    _instance = None
    _start_time = time.time()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CognitionEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        
        # 1. Reliability Governance (Must be initialized FIRST for health reporting)
        self.cycle_count = 0
        self.total_cycle_time = 0.0
        self._refresh_lock = asyncio.Lock()
        
        # 2. Core Services
        try:
            self.inference_engine = DecisionGradeInferenceEngine()
            self.state_store = MarketMemoryStore()
            self.arbitrator = SignalArbitrator()
            self.meta_cognition = MetaCognitionEngine()
            
            # 3. Institutional Brain
            self.memory_engine = InstitutionalMemoryEngine()
            self.orchestration_engine = OrchestrationEngine()
            self.enterprise_hub = EnterpriseCognitionHub()
            self.verification_engine = OperationalVerificationEngine()
            
            # 4. Deployment & Reality Sync (Phase 5)
            self.deployment_manager = DeploymentManager()
            self.reality_sync = RealitySynchronizer()
            
            # 5. Topology & Agent Ecosystem
            self.topology = MarketTopology()
            self.corridor_engine = ProcurementCorridorEngine(self.topology)
            self.registry = AgentRegistry()
            self._initialize_agents()
            
            self._initialized = True
            logger.info("CognitionEngine Phase 5B: Institutional Reliability Active.")
        except Exception as e:
            logger.error(f"CognitionEngine Initialization FAILED: {e}", exc_info=True)
            # We don't set _initialized=True so it can retry, but the counters now exist.
            raise

    def _initialize_agents(self):
        self.registry.register(ForecastAgent(self.inference_engine))
        self.registry.register(VolatilityAgent())
        self.registry.register(ArrivalAgent())

    def get_health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time
        return {
            "status": "HEALTHY",
            "uptime_seconds": int(uptime),
            "timestamp": datetime.now().isoformat(),
            "telemetry": [t.dict() for t in self.reality_sync.get_source_status()],
            "verification": self.verification_engine.get_institutional_effectiveness()
        }

    def validate_integrity(self, commodity: str, mandi_id: str) -> CognitionStatus:
        """
        Institutional Truth Verification Layer.
        Checks if cognition is valid before orchestration.
        """
        # 1. Telemetry Health
        telemetry = self.reality_sync.get_source_status()
        avg_trust = sum(t.trust_score for t in telemetry) / len(telemetry)
        
        # 2. Institutional Artifact Validation
        package_root = Path(__file__).resolve().parents[1]
        model_path = package_root / "models" / commodity / "v3"
        if not model_path.exists():
            logger.warning(f"INTEGRITY FAILURE: Institutional artifacts missing for {commodity}.")
            return CognitionStatus.MODEL_UNAVAILABLE
            
        # 3. Data Availability Check
        # (This would check for latest parquet files in production)
        
        if avg_trust < 0.4:
            return CognitionStatus.TELEMETRY_DEGRADED
        elif avg_trust < 0.7:
            return CognitionStatus.DEGRADED_COGNITION
            
        return CognitionStatus.FULL_COGNITION

    async def generate_cognition(self, commodity: str, mandi_id: str):
        """
        Orchestrates cognition and logs action lineage.
        """
        logger.info(f"Generating cognition for {commodity} @ {mandi_id}...")
        
        try:
            # 1. Integrity Validation (Truth Engineering)
            integrity = self.validate_integrity(commodity, mandi_id)
            logger.info(f"Integrity check for {commodity}: {integrity}")

            # 2. Reality Check (Telemetry trust scoring)
            telemetry = self.reality_sync.get_source_status()
            avg_trust = sum(t.trust_score for t in telemetry) / len(telemetry)
            
            # 2. Context & Council Execution
            prev_state = self.state_store.get_latest_state(commodity, mandi_id)
            context = { "prev_state": prev_state, "telemetry_trust": avg_trust }
            
            # 3. Agent Execution (Bypass if artifacts missing)
            if integrity == CognitionStatus.MODEL_UNAVAILABLE:
                logger.error(f"BYPASSING AGENTS: No valid artifacts for {commodity}")
                signals = []
                arbitration_res = self.arbitrator.get_empty_result()
                meta_res = {"confidence_penalty": 1.0, "stability_score": 0.0, "chaos_score": 1.0}
            else:
                agent_ids = self.registry.list_agents()
                tasks = [self.registry.get_agent(aid).perceive_and_reason(commodity, mandi_id, context) for aid in agent_ids]
                signals = await asyncio.gather(*tasks)
                arbitration_res = self.arbitrator.arbitrate(signals)
                meta_res = self.meta_cognition.evaluate_stability(arbitration_res, integrity)
            
            # 4. Evolve State
            snapshot = self._map_to_snapshot(commodity, mandi_id, arbitration_res, meta_res)
            snapshot["meta"]["telemetry_trust"] = avg_trust
            snapshot["integrity_status"] = integrity
            
            evolved_state = self.state_store.evolve_state(snapshot)
            evolved_state.integrity_status = integrity
            
            # 5. Orchestration Synthesis (With Safety Gates)
            if integrity in [CognitionStatus.COGNITION_FAILED, CognitionStatus.ORCHESTRATION_UNSAFE, CognitionStatus.MODEL_UNAVAILABLE]:
                logger.warning(f"ORCHESTRATION FROZEN: Cognition integrity is {integrity}")
                execution_plan = self.orchestration_engine.get_empty_plan("Safety Restraint")
            else:
                execution_plan = self.orchestration_engine.synthesize_response(evolved_state)
            
            evolved_state.metadata["active_execution_plan"] = execution_plan.dict()
            
            # Audit Logging (New in Phase 5)
            self.deployment_manager.log_action(
                org_id="org_default",
                actor="SYSTEM",
                action="SYNTHESIZE_PLAN",
                plan_id=execution_plan.id,
                details=f"Synthesized response sequence for {commodity} with {int(avg_trust*100)}% telemetry trust."
            )
            
            # Verification
            if prev_state:
                self.verification_engine.verify_plan_outcome(execution_plan, evolved_state, prev_state)
            
            # 6. Final Persistence
            self.state_store.save_state(evolved_state)
            try:
                from api.cognition_streaming import stream_manager
                await stream_manager.broadcast_state_update(commodity, mandi_id)
            except Exception as se:
                logger.warning(f"Could not broadcast state update: {se}")
            
            return evolved_state
            
        except Exception as e:
            logger.error(f"Critical failure: {e}")
            raise

    def approve_orchestration(self, plan_id: str, action_id: str, operator_id: str = "OPERATOR_01"):
        """
        Operator-driven approval with audit lineage.
        """
        self.orchestration_engine.approve_action(plan_id, action_id)
        self.deployment_manager.log_action(
            org_id="org_default",
            actor=operator_id,
            action="APPROVE_EXECUTION",
            plan_id=plan_id,
            details=f"Action {action_id} authorized for execution."
        )

    async def simulate_future(self, commodity: str, mandi_id: str, scenario: Dict[str, Any]):
        """
        Runs a counterfactual cognition cycle under scenario pressure.
        """
        logger.info(f"Simulating {scenario['type']} for {commodity}@{mandi_id}...")
        try:
            # 1. Mutated Context
            context = { "scenario": scenario, "is_simulation": True }
            
            # 2. Run Council
            agent_ids = self.registry.list_agents()
            tasks = [self.registry.get_agent(aid).perceive_and_reason(commodity, mandi_id, context) for aid in agent_ids]
            signals = await asyncio.gather(*tasks)
            
            # 3. Arbitration & Meta
            arb = self.arbitrator.arbitrate(signals)
            meta = self.meta_cognition.evaluate_stability(arb)
            
            # 4. Map to Memory
            snapshot = self._map_to_snapshot(commodity, mandi_id, arb, meta)
            sim_state = MarketState(**snapshot)
            
            # 5. Record Memory & Broadcast
            self.memory_engine.record_simulation(commodity, mandi_id, scenario["type"], sim_state)
            try:
                from api.cognition_streaming import stream_manager
                await stream_manager.broadcast_simulation_evolved(commodity, mandi_id, sim_state, scenario["type"])
            except Exception as se:
                logger.warning(f"Could not broadcast simulation evolved: {se}")
            
            self.deployment_manager.log_action(
                org_id="org_default",
                actor="SYSTEM",
                action="SIMULATION_COMPLETE",
                details=f"Simulation of {scenario['type']} complete. Strategic memory recorded."
            )
            return sim_state
        except Exception as e:
            logger.error(f"Simulation failed: {e}")

    async def run_full_refresh(self):
        """
        Triggers a full portfolio cognition refresh with lock governance.
        Refactored in Phase 5B for Canonical Namespace Integrity.
        """
        from mandisense_ai.cognition.registry import CognitionRegistry
        
        if self._refresh_lock.locked():
            logger.warning("Cognition cycle already in progress. Skipping redundant request.")
            return

        async with self._refresh_lock:
            start_time = time.time()
            
            # Phase 5B: Enforce Canonical Namespace Iteration
            commodities = CognitionRegistry.get_canonical_commodities()
            mandis = CognitionRegistry.get_canonical_mandis()
            
            tasks = []
            for commodity in commodities:
                for mandi in mandis:
                    tasks.append(self.generate_cognition(commodity, mandi))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            valid_states = [r for r in results if isinstance(r, MarketState)]
            self.enterprise_hub.update_portfolio_cognition(valid_states)
            valid_states = [r for r in results if isinstance(r, MarketState)]
            self.enterprise_hub.update_portfolio_cognition(valid_states)
            
            # Update Reliability Telemetry
            duration = time.time() - start_time
            self.cycle_count += 1
            self.total_cycle_time += duration
            logger.info(f"Full cognition refresh complete in {duration:.2f}s. Cycle #{self.cycle_count}")

    def _map_to_snapshot(self, commodity, mandi_id, arb, meta) -> Dict[str, Any]:
        primary_signals = arb.get("primary_signals", [])
        normalized_signals = []
        for signal in primary_signals:
            if isinstance(signal, dict):
                normalized_signals.append(signal)
            elif hasattr(signal, "model_dump"):
                normalized_signals.append(signal.model_dump())
            elif hasattr(signal, "dict"):
                normalized_signals.append(signal.dict())
            else:
                normalized_signals.append(vars(signal))

        forecast = next(
            (signal for signal in normalized_signals if signal.get("agent_id") == "forecast_agent"),
            None,
        )
        if forecast is None and normalized_signals:
            forecast = normalized_signals[0]

        dominant = arb.get("meta", {}).get("dominant_agent", "forecast_agent")
        risk_val = arb.get("synthesized_risk", "MEDIUM")
        risk_str = risk_val.value if hasattr(risk_val, 'value') else str(risk_val)

        forecast_price = forecast["value"] if forecast else 0.0
        forecast_arrivals = forecast.get("metadata", {}).get("predicted_arrivals", 0.0) if forecast else 0.0
        forecast_trend = forecast.get("metadata", {}).get("trend", "stable") if forecast else "stable"

        return {
            "commodity": commodity, "mandi_id": mandi_id,
            "regime": "SUPPLY_COMPRESSION" if risk_str == "CRITICAL" else "STABLE_EXPANSION",
            "forecast": { "price": forecast_price, "arrivals": forecast_arrivals, "trend": forecast_trend },
            "regimes": { "volatility": "high" if risk_str in ["HIGH", "CRITICAL"] else "low", "risk_level": risk_str },
            "confidence": {
                "overall": max(0.0, (forecast["confidence"] if forecast else 0.5) - meta.get("confidence_penalty", 0.0))
            },
            "directives": { "directive": arb["narrative"], "action_code": "EXECUTE", "urgency": "NORMAL", "reasoning_summary": arb["narrative"] },
            "meta": { "chaos_score": arb["chaos_score"] },
            "deliberation": { "signals": normalized_signals, "contradictions": arb["contradictions"], "dominant_agent": dominant, "chaos_score": arb["chaos_score"] }
        }
