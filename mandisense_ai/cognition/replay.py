import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from mandisense_ai.cognition.ontology import MarketState

logger = logging.getLogger("CognitionReplay")

class AnalogEngine:
    """
    Historical Cognition Replay & Analog Similarity.
    "Current Tomato Compression resembles Aug-2023 Kolar instability."
    """
    def __init__(self, history_root: Path | None = None):
        self.history_root = history_root or Path(__file__).resolve().parent / "storage" / "snapshots" / "history"

    def find_analogs(self, current_state: MarketState, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Searches historical trajectories for similar market states.
        """
        commodity = current_state.commodity
        mandi_id = current_state.mandi_id
        
        history_path = self.history_root / commodity / mandi_id
        if not history_path.exists():
            return []
            
        analogs = []
        
        # In a real system, we would use vector embeddings of states.
        # For this foundation, we'll use heuristic similarity on regimes and trends.
        
        for hist_file in history_path.glob("*.json"):
            # Don't compare with very recent states (e.g. last 24h)
            # For simplicity in this demo, we'll just check all
            with open(hist_file, "r") as f:
                hist_data = json.load(f)
                
            similarity_score = self._calculate_similarity(current_state, hist_data)
            
            if similarity_score > 0.7:
                analogs.append({
                    "timestamp": hist_data["freshness"]["last_computed"],
                    "similarity": round(similarity_score, 3),
                    "regime": hist_data["regime"],
                    "directive": self._get_directive(hist_data)
                })
        
        # Sort by similarity and return top N
        return sorted(analogs, key=lambda x: x["similarity"], reverse=True)[:limit]

    def _calculate_similarity(self, current: MarketState, historical: Dict[str, Any]) -> float:
        score = 0.0
        
        # Regime Match
        if current.regime == historical["regime"]:
            score += 0.4
            
        # Trend Match
        if current.trend == historical["trend"]:
            score += 0.3
            
        # Price Proximity (within 10%)
        historical_price = historical.get("price_prediction", historical.get("forecast_price", 0.0))
        price_diff = abs(current.price_prediction - historical_price)
        if price_diff / (current.price_prediction + 1e-6) < 0.1:
            score += 0.3
            
        return score

    @staticmethod
    def _get_directive(state: Dict[str, Any]) -> str:
        directives = state.get("directives", [])
        if isinstance(directives, list) and directives:
            return directives[0].get("primary_directive", "HOLD")
        if isinstance(directives, dict):
            return directives.get("primary_directive", "HOLD")
        return "HOLD"

class TrajectoryAnalyzer:
    """
    Analyzes how market truth has evolved over a period.
    """
    def get_trajectory(self, commodity: str, mandi_id: str, depth: int = 10) -> List[Dict[str, Any]]:
        # Implementation to fetch last N states and analyze transitions
        pass
