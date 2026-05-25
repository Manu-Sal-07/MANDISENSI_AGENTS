"""
MandiSense AI — Ensemble Package.

Public exports:
  AgentEnsemble : canonical internal ensemble engine used by both
                  SeasonalityAgent and ArrivalVolumeAgent.

  Regime Detection & Adaptive Weight System (Objective 2):
    GARCHVolatilityEstimator  — EGARCH(1,1) volatility estimation
    HMMRegimeClassifier       — 4-state Gaussian HMM regime detection
    AdaptiveWeightCalculator  — Dynamic regime-aware weight engine
    VolatilityAlertEngine     — Multi-level statistical alerts
    RegimeAwareMetaEnsemble   — Master orchestration layer

  Phase-1/1.5 Meta-Ensemble (Objective 3):
    fuse                      — Core stateless fusion function
    run_meta_ensemble         — Convenience wrapper accepting AgentOutputs
    SeasonalityInput          — Immutable input dataclass for Seasonality
    ArrivalInput              — Immutable input dataclass for Arrival
    ExternalInput             — Immutable input dataclass for External
    MetaEnsembleOutput        — Fusion result with attribution & risk flags

  Phase-2 Learned Ensemble (Objective 4):
    PredictionLogger          — Append-only prediction logging
    DatasetBuilder            — Feature engineering & dataset construction
    LearnedEnsemble           — Regime-aware Ridge models + blending
"""

from .agent_ensemble import AgentEnsemble
from .feedback_store import FeedbackStore
from .regime_detector import RegimeDetector
from .dynamic_weighter import DynamicWeighter

from .regime import (
    GARCHVolatilityEstimator,
    HMMRegimeClassifier,
    AdaptiveWeightCalculator,
    VolatilityAlertEngine,
    RegimeAwareMetaEnsemble,
)

from .meta_ensemble import (
    fuse as meta_ensemble_fuse,
    run_meta_ensemble,
    SeasonalityInput,
    ArrivalInput,
    ExternalInput,
    MetaEnsembleOutput,
)

from .prediction_logger import PredictionLogger
from .dataset_builder import DatasetBuilder
from .learned_ensemble import LearnedEnsemble

__all__ = [
    # Existing
    "AgentEnsemble",
    "FeedbackStore",
    "RegimeDetector",
    "DynamicWeighter",
    # Objective 2 — Regime Intelligence
    "GARCHVolatilityEstimator",
    "HMMRegimeClassifier",
    "AdaptiveWeightCalculator",
    "VolatilityAlertEngine",
    "RegimeAwareMetaEnsemble",
    # Objective 3 — Phase-1 Meta-Ensemble
    "meta_ensemble_fuse",
    "run_meta_ensemble",
    "SeasonalityInput",
    "ArrivalInput",
    "ExternalInput",
    "MetaEnsembleOutput",
    # Objective 4 — Phase-2 Learned Ensemble
    "PredictionLogger",
    "DatasetBuilder",
    "LearnedEnsemble",
]

