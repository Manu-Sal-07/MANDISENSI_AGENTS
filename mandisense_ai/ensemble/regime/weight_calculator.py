"""
Adaptive Weight Calculator — Dynamic regime-aware ensemble weight engine.

Adjusts agent weights based on: recent prediction accuracy, current market
regime, agent confidence scores, and recency-weighted performance.

Weight formula:
  w_i(t) = base_weight_i × regime_multiplier_i × recency_factor_i × confidence_i

Constraints:
  - Minimum weight: 0.10 (no agent completely ignored)
  - Maximum weight: 0.70 (prevent over-reliance)
  - Weights always sum to 1.0 (±1e-6)
  - Smooth transitions when regime confidence < 0.7

Performance: <20ms per weight update, <10MB memory.
"""

from __future__ import annotations
from collections import deque
from typing import Dict, Optional
import numpy as np
try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)

REGIME_NAMES = {1: "Stable", 2: "Medium Volatility", 3: "High Volatility", 4: "Crisis"}


class AdaptiveWeightCalculator:
    """Dynamic ensemble weight calculator with regime awareness."""

    def __init__(self):
        self.error_tracker: Dict[str, deque] = {
            "seasonality": deque(maxlen=30),
            "arrival": deque(maxlen=30),
            "external": deque(maxlen=30),
        }
        # Regime-specific multipliers (tuned via backtesting)
        self.regime_multipliers: Dict[int, Dict[str, float]] = {
            1: {"seasonality": 1.2, "arrival": 0.8, "external": 0.5},  # Stable
            2: {"seasonality": 1.0, "arrival": 1.2, "external": 0.8},  # Medium
            3: {"seasonality": 0.6, "arrival": 1.5, "external": 1.2},  # Volatile
            4: {"seasonality": 0.3, "arrival": 0.9, "external": 2.0},  # Crisis
        }
        # Previous weights for transition smoothing
        self.prev_weights: Dict[str, float] = {
            "seasonality": 0.33, "arrival": 0.33, "external": 0.34,
        }

    def update_error(self, agent_name: str, prediction: float, actual: float) -> None:
        """Track prediction error for an agent."""
        if agent_name not in self.error_tracker:
            raise ValueError(f"Unknown agent: {agent_name}")
        error = abs(prediction - actual)
        self.error_tracker[agent_name].append(error)

    def compute_weights(
        self,
        agent_outputs: Dict[str, Dict],
        current_regime: int,
        transition_prob: float,
    ) -> Dict[str, float]:
        """
        Compute optimal ensemble weights for the current regime.

        Args:
            agent_outputs: {agent_name: {prediction, confidence, metadata}}
            current_regime: Current regime state (1-4)
            transition_prob: Confidence in regime classification

        Returns:
            Normalized weights {agent_name: weight} summing to 1.0
        """
        # Step 1: Base weights from inverse recent error
        base_weights = self._compute_base_weights(window=14)

        # Step 2: Apply regime multipliers
        regime_adjusted = self._apply_regime_multipliers(base_weights, current_regime)

        # Step 3: Apply recency factor (exponential decay)
        recency_adjusted = self._apply_recency_factor(regime_adjusted)

        # Step 4: Normalize
        normalized = self._normalize_weights(recency_adjusted)

        # Step 5: Confidence damping
        confidence_adjusted = self._apply_confidence_damping(normalized, agent_outputs)

        # Step 6: Re-normalize
        final_normalized = self._normalize_weights(confidence_adjusted)

        # Step 7: Apply constraints (min/max bounds)
        constrained = self._apply_constraints(final_normalized)

        # Step 8: Smooth transition if low confidence in regime
        smoothed = self._smooth_transition(constrained, self.prev_weights, transition_prob)

        # Final: re-apply constraints to guarantee bounds are honoured
        # even after blending.  _apply_constraints already normalises internally.
        smoothed = self._apply_constraints(smoothed)

        # Update previous weights for next iteration
        self.prev_weights = smoothed.copy()

        logger.debug(
            f"[WeightCalc] Regime={current_regime}, trans_prob={transition_prob:.3f}, "
            f"weights={{{', '.join(f'{a}={w:.3f}' for a, w in smoothed.items())}}}"
        )

        return smoothed

    def _compute_base_weights(self, window: int = 14) -> Dict[str, float]:
        """Inverse recent MAE weighting."""
        weights = {}
        for agent, errors in self.error_tracker.items():
            recent = list(errors)[-window:]
            if not recent:
                weights[agent] = 1.0
            else:
                mae = np.mean(recent)
                weights[agent] = 1.0 / (mae + 1e-6)
        return weights

    def _apply_regime_multipliers(self, weights: Dict[str, float], regime: int) -> Dict[str, float]:
        """Apply regime-specific boosts/penalties."""
        multipliers = self.regime_multipliers.get(regime, self.regime_multipliers[1])
        return {agent: w * multipliers[agent] for agent, w in weights.items()}

    def _apply_recency_factor(self, weights: Dict[str, float], decay: float = 0.95) -> Dict[str, float]:
        """Exponentially weight recent errors more heavily."""
        recency_weights = {}
        for agent, errors in self.error_tracker.items():
            errors_list = list(errors)[-14:]
            if not errors_list:
                recency_weights[agent] = 1.0
            else:
                weighted_errors = [
                    err * (decay ** (len(errors_list) - i - 1))
                    for i, err in enumerate(errors_list)
                ]
                recency_mae = np.mean(weighted_errors)
                recency_weights[agent] = 1.0 / (recency_mae + 1e-6)
        return {agent: weights[agent] * recency_weights[agent] for agent in weights}

    def _apply_confidence_damping(
        self, weights: Dict[str, float], agent_outputs: Dict[str, Dict]
    ) -> Dict[str, float]:
        """Scale weights by agent confidence scores."""
        return {
            agent: w * agent_outputs[agent].get("confidence", 0.5)
            for agent, w in weights.items()
        }

    @staticmethod
    def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
        """Normalize weights to sum to 1.0."""
        total = sum(weights.values())
        if total == 0:
            return {a: 1.0 / len(weights) for a in weights}
        return {a: w / total for a, w in weights.items()}

    @staticmethod
    def _apply_constraints(
        weights: Dict[str, float], min_w: float = 0.1, max_w: float = 0.7
    ) -> Dict[str, float]:
        """Clip weights to [min_w, max_w] and re-normalize iteratively.

        A single clip-then-normalize pass can push weights back outside bounds,
        so we iterate until all weights are within tolerance.
        """
        w = dict(weights)
        for _ in range(50):  # Increased iterations for strict 1e-6 tolerance
            w = {a: float(np.clip(v, min_w, max_w)) for a, v in w.items()}
            total = sum(w.values())
            if total == 0:
                return {a: 1.0 / len(w) for a in w}
            w = {a: v / total for a, v in w.items()}
            if all(min_w - 1e-9 <= v <= max_w + 1e-9 for v in w.values()):
                break
        return w

    @staticmethod
    def _smooth_transition(
        new_weights: Dict[str, float],
        prev_weights: Dict[str, float],
        transition_prob: float,
    ) -> Dict[str, float]:
        """Blend new weights with previous when regime confidence is low."""
        if transition_prob < 0.7:
            alpha = transition_prob
            return {
                agent: alpha * new_weights[agent] + (1 - alpha) * prev_weights.get(agent, 1 / 3)
                for agent in new_weights
            }
        return new_weights

    def get_weight_explanation(self, weights: Dict[str, float], regime: int) -> Dict:
        """Generate human-readable explanation of weight assignment."""
        dominant_agent = max(weights, key=weights.get)

        regime_reasoning = {
            1: "Market is stable — seasonal patterns are most reliable",
            2: "Medium volatility — supply dynamics becoming important",
            3: "High volatility — supply shocks dominating price movements",
            4: "Crisis regime — external events overriding normal patterns",
        }
        agent_reasoning = {
            "seasonality": "Long-term cyclical patterns showing strong predictive power",
            "arrival": "Supply-demand balance is primary price driver",
            "external": "External shocks (policy/weather) causing major disruptions",
        }

        return {
            "regime": REGIME_NAMES.get(regime, f"State {regime}"),
            "dominant_agent": dominant_agent,
            "dominant_weight": weights[dominant_agent],
            "reasoning": f"{regime_reasoning.get(regime, '')}. {agent_reasoning.get(dominant_agent, '')}.",
            "weight_distribution": weights,
        }

    def __repr__(self) -> str:
        n_tracked = {a: len(e) for a, e in self.error_tracker.items()}
        return f"<AdaptiveWeightCalculator tracked={n_tracked}>"
