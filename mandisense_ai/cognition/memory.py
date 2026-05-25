import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("CognitiveMemory")

class AgentReliabilityTracker:
    """
    Historical Cognitive Trust Engine.
    "The machine should now learn how to trust itself."
    """
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path(__file__).resolve().parent / "storage" / "memory" / "agents.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_memory()

    def _load_memory(self):
        if self.storage_path.exists():
            with open(self.storage_path, "r") as f:
                self.memory = json.load(f)
        else:
            self.memory = {}

    def record_performance(self, agent_id: str, commodity: str, was_accurate: bool, context: Dict[str, Any]):
        """
        Records how an agent performed in a specific market context.
        """
        if agent_id not in self.memory:
            self.memory[agent_id] = {"total_runs": 0, "successes": 0, "regime_performance": {}}
            
        mem = self.memory[agent_id]
        mem["total_runs"] += 1
        if was_accurate:
            mem["successes"] += 1
            
        # Track by regime
        regime = context.get("regime", "UNKNOWN")
        if regime not in mem["regime_performance"]:
            mem["regime_performance"][regime] = {"runs": 0, "successes": 0}
        
        mem["regime_performance"][regime]["runs"] += 1
        if was_accurate:
            mem["regime_performance"][regime]["successes"] += 1
            
        self._save_memory()

    def get_trust_score(self, agent_id: str, regime: str = "UNKNOWN") -> float:
        """
        Returns a trust score (0-1) for an agent, optionally specific to a regime.
        """
        if agent_id not in self.memory:
            return 0.5 # Default trust for new agents
            
        mem = self.memory[agent_id]
        
        # Prefer regime-specific reliability if enough data exists
        regime_data = mem["regime_performance"].get(regime)
        if regime_data and regime_data["runs"] > 5:
            return regime_data["successes"] / regime_data["runs"]
            
        if mem["total_runs"] > 0:
            return mem["successes"] / mem["total_runs"]
            
        return 0.5

    def _save_memory(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.memory, f, indent=2)

class MetaCognitionEngine:
    """
    Machine Self-Awareness.
    Detects when cognition is unstable or signals conflict excessively.
    """
    
    @staticmethod
    def evaluate_stability(arbitration_results: Dict[str, Any], integrity_status: str = "FULL_COGNITION") -> Dict[str, Any]:
        chaos = arbitration_results["chaos_score"]
        consensus = arbitration_results["meta"]["consensus"]
        
        # Institutional Integrity Penalties
        integrity_penalty = 0.0
        if integrity_status == "DEGRADED_COGNITION":
            integrity_penalty = 0.3
        elif integrity_status == "TELEMETRY_DEGRADED":
            integrity_penalty = 0.5
        elif integrity_status == "COGNITION_FAILED":
            integrity_penalty = 0.9
        
        # Aggregate Stability
        final_chaos = min(1.0, chaos + integrity_penalty)
        is_unstable = final_chaos > 0.6 or consensus == "low"
        
        warnings = []
        if integrity_penalty > 0.5:
            warnings.append(f"INTEGRITY ALERT: Confidence collapsed due to {integrity_status}.")
        
        if is_unstable:
            warnings.append("High Cognitive Conflict: Signals are diverging significantly.")
        if arbitration_results["synthesized_risk"] == "CRITICAL":
            warnings.append("Systemic Risk Escalation: Volatility and Contradiction detected.")
            
        return {
            "is_cognition_stable": not is_unstable,
            "warnings": warnings,
            "suppress_directives": final_chaos > 0.8, # Threshold for total suppression
            "anomaly_detected": final_chaos > 0.9,
            "confidence_penalty": integrity_penalty
        }
