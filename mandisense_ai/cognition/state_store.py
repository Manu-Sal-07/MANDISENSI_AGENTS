import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from mandisense_ai.cognition.ontology import MarketState, MarketRegime, RiskLevel
from mandisense_ai.cognition.temporal import ConfidenceDecayEngine, FreshnessManager

logger = logging.getLogger("MarketMemory")

class MarketMemoryStore:
    """
    Institutional Market Memory.
    Maintains continuity, evolution, and historical trajectories of cognition.
    """
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            self.base_path = Path(__file__).resolve().parent / "storage"
        else:
            self.base_path = base_path
            
        self.snapshots_path = self.base_path / "snapshots"
        self.history_path = self.snapshots_path / "history"
        self.snapshots_path.mkdir(parents=True, exist_ok=True)
        self.history_path.mkdir(parents=True, exist_ok=True)

    def evolve_state(self, new_snapshot: Dict[str, Any]) -> MarketState:
        """
        Takes a raw ML snapshot and evolves it into a continuous MarketState.
        """
        commodity = new_snapshot["commodity"]
        mandi_id = new_snapshot["mandi_id"]
        
        # 1. Retrieve Previous State for Continuity
        prev_data = self.get_latest_state_dict(commodity, mandi_id)
        try:
            prev_state = MarketState(**prev_data) if prev_data else None
        except Exception:
            logger.warning(f"Legacy state detected for {commodity}. Evolution proceeding without continuity.")
            prev_state = None
        
        # 2. Map New Data to Ontology
        # This part bridges the gap between raw ML output and our structured ontology
        
        # Logic to detect regime transitions
        current_regime = self._detect_regime(new_snapshot, prev_state)
        
        state = MarketState(
            commodity=commodity,
            mandi_id=mandi_id,
            timestamp=datetime.now(),
            price_prediction=new_snapshot["forecast"]["price"],
            regime=current_regime,
            risk_level=new_snapshot["regimes"]["risk_level"],
            forecast_arrivals=new_snapshot["forecast"]["arrivals"],
            trend=new_snapshot["forecast"]["trend"],
            volatility={
                "regime": new_snapshot["regimes"]["volatility"],
                "score": 0.5,
                "is_escalating": self._check_escalation(new_snapshot, prev_state),
                "momentum": 0.0
            },
            confidence={
                "score": new_snapshot["confidence"]["overall"],
                "stability": 0.8,
                "decay_rate": 0.01,
                "last_updated": datetime.now()
            },
            integrity_status=new_snapshot.get("integrity_status", "FULL_COGNITION"),
            directives=[{
                "primary_directive": new_snapshot["directives"]["directive"],
                "action_code": new_snapshot["directives"]["action_code"],
                "urgency": new_snapshot["directives"]["urgency"],
                "reasoning": new_snapshot["directives"]["reasoning_summary"],
                "confidence_at_synthesis": new_snapshot["confidence"]["overall"]
            }],
            deliberation={
                "agents": [
                    {
                        "agent_id": s["agent_id"],
                        "signal": s["metadata"].get("trend", "stable"),
                        "confidence": s["confidence"],
                        "weight": s.get("weight", 1.0)
                    } for s in new_snapshot["deliberation"]["signals"]
                ],
                "contradictions": new_snapshot["deliberation"]["contradictions"],
                "dominant_agent_id": new_snapshot["deliberation"]["dominant_agent"],
                "chaos_score": new_snapshot["deliberation"]["chaos_score"]
            },
            freshness={
                "last_computed": datetime.now(),
                "expiration_threshold_minutes": 240
            },
            metadata=new_snapshot.get("meta", {})
        )
        
        # 3. Apply Temporal Evolution (Decay & Freshness)
        state = FreshnessManager.update_integrity(state)
        
        # 4. Persistence
        self.save_state(state)
        return state

    def save_state(self, state: MarketState):
        """
        Persists the evolved state and records the historical trajectory.
        """
        data = state.dict()
        data["last_updated"] = datetime.now().isoformat()
        
        # Save Latest
        latest_file = self.snapshots_path / f"{state.commodity}_{state.mandi_id}_latest.json"
        with open(latest_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
            
        # Save History (Continuity)
        hist_dir = self.history_path / state.commodity / state.mandi_id
        hist_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hist_file = hist_dir / f"{timestamp}.json"
        with open(hist_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
            
        # Rotate History (Phase 5B: Keep last 50)
        hist_files = sorted(list(hist_dir.glob("*.json")), reverse=True)
        if len(hist_files) > 50:
            for old_file in hist_files[50:]:
                try:
                    old_file.unlink()
                except Exception:
                    pass

    def get_latest_state(self, commodity: str, mandi_id: str) -> Optional[MarketState]:
        data = self.get_latest_state_dict(commodity, mandi_id)
        if data:
            try:
                state = MarketState(**data)
                # Apply real-time decay when retrieving
                state = ConfidenceDecayEngine.apply_decay(state)
                state = FreshnessManager.update_integrity(state)
                return state
            except Exception as e:
                logger.warning(f"Failed to validate latest state for {commodity}: {e}. Returning None.")
                return None
        return None

    def get_latest_state_dict(self, commodity: str, mandi_id: str) -> Optional[Dict[str, Any]]:
        latest_file = self.snapshots_path / f"{commodity}_{mandi_id}_latest.json"
        if not latest_file.exists():
            return None
        with open(latest_file, "r") as f:
            return json.load(f)

    def _detect_regime(self, new_data: Dict[str, Any], prev_state: Optional[MarketState]) -> MarketRegime:
        vol = new_data["regimes"]["volatility"]
        risk = new_data["regimes"]["risk_level"]
        
        if vol == "high" and risk in ["HIGH", "CRITICAL"]:
            return MarketRegime.ELEVATED_VOLATILITY
        if vol == "high" and prev_state and prev_state.regime == MarketRegime.STABLE_EXPANSION:
            return MarketRegime.TRANSITIONAL_STRESS
        return MarketRegime.STABLE_EXPANSION

    def _check_escalation(self, new_data: Dict[str, Any], prev_state: Optional[MarketState]) -> bool:
        if not prev_state: return False
        return new_data["forecast"]["price"] > prev_state.price_prediction * 1.05
        
    def list_available_intelligence(self) -> Dict[str, list]:
        intel_map = {}
        for file in self.snapshots_path.glob("*_latest.json"):
            parts = file.stem.replace("_latest", "").split("_")
            if len(parts) >= 2:
                comm = parts[0]
                mandi = "_".join(parts[1:])
                if comm not in intel_map:
                    intel_map[comm] = []
                intel_map[comm].append(mandi)
        return intel_map
