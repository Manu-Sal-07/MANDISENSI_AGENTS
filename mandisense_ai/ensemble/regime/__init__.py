"""
MandiSense AI — Regime Detection & Adaptive Weight System (Objective 2).

This package implements the Volatility & Regime Intelligence System:
  - GARCHVolatilityEstimator:   EGARCH(1,1) conditional volatility estimation
  - HMMRegimeClassifier:        4-state Gaussian HMM regime classification
  - AdaptiveWeightCalculator:   Dynamic regime-aware ensemble weight engine
  - VolatilityAlertEngine:      Multi-level statistical alert system
  - RegimeAwareMetaEnsemble:    Master orchestration layer

Public API:
  from mandisense_ai.ensemble.regime import RegimeAwareMetaEnsemble
"""

from .garch_estimator import GARCHVolatilityEstimator
from .hmm_classifier import HMMRegimeClassifier
from .weight_calculator import AdaptiveWeightCalculator
from .alert_engine import VolatilityAlertEngine
from .meta_ensemble import RegimeAwareMetaEnsemble

__all__ = [
    "GARCHVolatilityEstimator",
    "HMMRegimeClassifier",
    "AdaptiveWeightCalculator",
    "VolatilityAlertEngine",
    "RegimeAwareMetaEnsemble",
]
