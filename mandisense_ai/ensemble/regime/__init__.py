"""
MandiSense AI — Regime Detection & Adaptive Weight System (Objective 2).

This package implements the Volatility & Regime Intelligence System:
  - GARCHVolatilityEstimator:   EGARCH(1,1) conditional volatility estimation
  - HMMRegimeClassifier:        4-state Gaussian HMM regime classification
  - AdaptiveWeightCalculator:   Dynamic regime-aware ensemble weight engine
  - VolatilityAlertEngine:      Multi-level statistical alert system
  - RegimeAwareMetaEnsemble:    Master orchestration layer

Public API:
  from ensemble.regime import RegimeAwareMetaEnsemble
"""

from ensemble.regime.garch_estimator import GARCHVolatilityEstimator
from ensemble.regime.hmm_classifier import HMMRegimeClassifier
from ensemble.regime.weight_calculator import AdaptiveWeightCalculator
from ensemble.regime.alert_engine import VolatilityAlertEngine
from ensemble.regime.meta_ensemble import RegimeAwareMetaEnsemble

__all__ = [
    "GARCHVolatilityEstimator",
    "HMMRegimeClassifier",
    "AdaptiveWeightCalculator",
    "VolatilityAlertEngine",
    "RegimeAwareMetaEnsemble",
]
