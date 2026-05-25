import logging
from typing import Optional
from datetime import datetime, timedelta
from mandisense_ai.cognition.ontology import MarketState, MarketRegime

logger = logging.getLogger("TemporalCognition")

class ConfidenceDecayEngine:
    """
    Handles the temporal degradation of intelligence trust.
    Institutional systems admit that old intelligence is less reliable.
    """
    
    @staticmethod
    def apply_decay(state: MarketState) -> MarketState:
        """
        Mutates the state to reflect confidence decay.
        """
        # High volatility accelerates decay
        base_decay = state.confidence.decay_rate
        if state.regime == MarketRegime.ELEVATED_VOLATILITY:
            base_decay *= 2.5
        elif state.regime == MarketRegime.TRANSITIONAL_STRESS:
            base_decay *= 1.5
            
        hours_passed = (datetime.now() - state.confidence.last_updated).total_seconds() / 3600
        total_decay = hours_passed * base_decay
        
        old_score = state.confidence.score
        state.confidence.score = max(0.1, state.confidence.score - total_decay)
        
        if state.confidence.score < old_score:
            logger.debug(f"Decayed confidence for {state.commodity}_{state.mandi_id}: {old_score:.2f} -> {state.confidence.score:.2f}")
            
        return state

class FreshnessManager:
    """
    Calculates integrity scores and manages intelligence expiration.
    """
    
    @staticmethod
    def update_integrity(state: MarketState) -> MarketState:
        """
        Calculates a 0-1 integrity score based on age and market conditions.
        """
        age = state.freshness.age_minutes
        threshold = state.freshness.expiration_threshold_minutes
        
        # Linear decay of integrity towards threshold
        integrity = max(0.0, 1.0 - (age / threshold))
        
        # Penalize integrity if confidence is low
        if state.confidence.score < 0.4:
            integrity *= 0.8
            
        state.freshness.integrity_score = round(integrity, 3)
        return state

class StabilityEngine:
    """
    Detects contradictions and shocks that should collapse confidence.
    """
    @staticmethod
    def detect_instability(current_state: MarketState, previous_state: Optional[MarketState]) -> float:
        if not previous_state:
            return 1.0 # Initial stability
            
        # Contradiction: Price trend reversed suddenly
        if current_state.trend != previous_state.trend:
            return 0.5
            
        # Volatility Spike
        if current_state.volatility.score > previous_state.volatility.score * 1.5:
            return 0.4
            
        return 1.0
