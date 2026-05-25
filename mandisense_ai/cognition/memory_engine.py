import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("InstitutionalMemory")

class StrategicMemory(BaseModel):
    """
    A persistent record of an operational event or simulation.
    The building block of institutional memory.
    """
    id: str
    timestamp: datetime
    type: str # "LIVE_CRISIS", "SIMULATION", "DOCTRINE_VALIDATION"
    commodity: str
    mandi_id: str
    scenario_type: Optional[str] = None
    initial_state: Dict[str, Any]
    evolved_state: Dict[str, Any]
    propagation_path: List[Dict[str, Any]]
    operator_strategy: Optional[str] = None
    outcome_delta: float = 0.0 # Change in risk/price/savings

class AnalogMatch(BaseModel):
    memory_id: str
    similarity_score: float
    context: str
    key_similarities: List[str]

class InstitutionalMemoryEngine:
    """
    Strategic Replay & Analog Intelligence Infrastructure.
    "The institutional brain of MandiSense."
    """
    def __init__(self, storage_path: str | Path | None = None):
        self.storage_path = Path(storage_path) if storage_path else Path(__file__).resolve().parents[1] / "memory" / "archives"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.doctrines_path = self.storage_path.parent / "doctrines.json"

    def archive_memory(self, memory: StrategicMemory):
        """
        Persists a strategic memory to the institutional archive.
        """
        file_path = self.storage_path / f"{memory.id}.json"
        with open(file_path, 'w') as f:
            f.write(memory.json())
        logger.info(f"Strategic memory archived: {memory.id}")
        
        # Trigger doctrine synthesis periodically (simulated here)
        self._evolve_doctrines(memory)

    def find_analogs(self, current_state: Dict[str, Any], limit: int = 3) -> List[AnalogMatch]:
        """
        Identifies historical analogs for the current market state.
        "Recognition-primed institutional reasoning."
        """
        analogs = []
        for file in self.storage_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    memory_data = json.load(f)
                
                similarity = self._calculate_similarity(current_state, memory_data["evolved_state"])
                if similarity > 0.7:
                    analogs.append(AnalogMatch(
                        memory_id=memory_data["id"],
                        similarity_score=similarity,
                        context=memory_data.get("scenario_type") or "Market Anomaly",
                        key_similarities=self._extract_key_similarities(current_state, memory_data)
                    ))
            except Exception as e:
                logger.error(f"Failed to read memory file {file}: {e}")

        return sorted(analogs, key=lambda x: x.similarity_score, reverse=True)[:limit]

    def get_playbook(self, regime: str, risk: str) -> List[Dict[str, Any]]:
        """
        Retrieves strategic playbooks based on institutional doctrine.
        """
        if not self.doctrines_path.exists():
            return self._get_default_doctrines(regime)
        
        with open(self.doctrines_path, 'r') as f:
            doctrines = json.load(f)
        
        return doctrines.get(f"{regime}_{risk}", self._get_default_doctrines(regime))

    def _calculate_similarity(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> float:
        """
        Multi-dimensional similarity scoring for institutional analogs.
        """
        score = 0.0
        # 1. Regime Match
        if state_a.get("regime") == state_b.get("regime"): score += 0.4
        
        # 2. Risk Level Match
        if state_a.get("risk_level") == state_b.get("risk_level"): score += 0.3
        
        # 3. Chaos/Volatility Score proximity
        chaos_a = state_a.get("deliberation", {}).get("chaos_score", 0.5)
        chaos_b = state_b.get("deliberation", {}).get("chaos_score", 0.5)
        if abs(chaos_a - chaos_b) < 0.1: score += 0.3
        
        return min(1.0, score)

    def _extract_key_similarities(self, current: Dict[str, Any], historical: Dict[str, Any]) -> List[str]:
        keys = []
        if current.get("regime") == historical["evolved_state"].get("regime"):
            keys.append("Regime Alignment")
        if current.get("deliberation", {}).get("dominant_agent") == historical["evolved_state"].get("deliberation", {}).get("dominant_agent"):
            keys.append("Agent Dominance Pattern")
        return keys

    def _evolve_doctrines(self, new_memory: StrategicMemory):
        """
        Evolves institutional doctrine based on new strategic outcomes.
        """
        # Logic to update doctrines.json based on successful/failed outcome_delta
        pass

    def _get_default_doctrines(self, regime: str) -> List[Dict[str, Any]]:
        default_map = {
            "SUPPLY_COMPRESSION": [
                {"title": "Immediate Accumulation", "action": "Secure 48h inventory ahead of arrival collapse."},
                {"title": "Corridor Diversification", "action": "Activate secondary sourcing from non-shocked regions."}
            ],
            "TRANSITIONAL_STRESS": [
                {"title": "Wait & Watch", "action": "Allow volatility to peak before committing bulk orders."},
                {"title": "Logistics Buffering", "action": "Increase transport lead-time margins by 20%."}
            ]
        }
        return default_map.get(regime, [{"title": "Baseline Protocol", "action": "Continue nominal procurement cycle."}])
