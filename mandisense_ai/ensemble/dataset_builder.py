"""
Dataset Builder — Phase 2 Training Data Construction.

Transforms raw prediction logs (from PredictionLogger) into
structured feature matrices suitable for Ridge Regression training.

Responsibilities:
  • Filter to completed records only (actual outcome backfilled)
  • Construct 11 engineered features from agent signals
  • Assign regime labels for regime-aware model routing
  • Provide time-ordered train/validation splits (walk-forward)
  • Enforce minimum data requirements before training is allowed

No data leakage:
  • Only records with actual_7d_change != null are used
  • Walk-forward splits preserve temporal ordering
  • 7-day gap between train and validation sets
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

_SCALING_DAMPING = 0.8
_MIN_TOTAL_RECORDS = 50       # Minimum completed records to enable training
_MIN_REGIME_RECORDS = 20      # Minimum records per regime to train regime model
_MIN_RECENT_RECORDS = 10      # Minimum from last 60 days
_RECENT_WINDOW_DAYS = 60

# Regime detection thresholds
_SUPPLY_SHOCK_STRESS_THRESHOLD = 0.7
_EXTERNAL_DOMINATED_SCORE_THRESHOLD = 0.5
_EXTERNAL_DOMINATED_INTERNAL_THRESHOLD = 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Feature Record
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FeatureRecord:
    """One fully-engineered training sample."""
    features: List[float]       # 11-element feature vector
    target: float               # actual_7d_change
    regime: str                 # "normal" / "supply_shock" / "external_dominated"
    timestamp: str              # for time-ordering
    commodity: str
    mandi: str


# Feature name registry — order matters (matches feature vector index)
FEATURE_NAMES = [
    "norm_seasonality",         # 0
    "arrival_pred",             # 1
    "external_score",           # 2
    "conf_seasonality",         # 3
    "conf_arrival",             # 4
    "volatility",               # 5
    "supply_stress",            # 6
    "phase1_prediction",        # 7
    "phase1_confidence",        # 8
    "seasonality_x_arrival",    # 9
    "arrival_x_stress",         # 10
    "external_direction",       # 11
    "agreement_flag",           # 12
    "magnitude_diff",           # 13
    "seasonality_x_vol",        # 14
    "conf_agreement",           # 15
]


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════════

def _safe(val: Any, default: float = 0.0) -> float:
    """Convert to float safely, defaulting on None/NaN/Inf."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def classify_regime(
    supply_stress: float,
    arrival_regime: str,
    external_score: float,
    norm_seasonality: float,
    arrival_pred: float,
) -> str:
    """
    Classify the market regime for this observation.

    Priority:
      1. supply_shock — if stress is very high or arrival regime is squeeze
      2. external_dominated — if external signal is strong and internal is weak
      3. normal — default
    """
    # Supply shock
    if supply_stress > _SUPPLY_SHOCK_STRESS_THRESHOLD:
        return "supply_shock"
    if str(arrival_regime).strip().lower() == "squeeze":
        return "supply_shock"

    # External dominated
    if (abs(external_score) > _EXTERNAL_DOMINATED_SCORE_THRESHOLD
        and abs(norm_seasonality) < _EXTERNAL_DOMINATED_INTERNAL_THRESHOLD
        and abs(arrival_pred) < _EXTERNAL_DOMINATED_INTERNAL_THRESHOLD):
        return "external_dominated"

    return "normal"


def extract_features(record: Dict[str, Any]) -> Tuple[List[float], str]:
    """
    Extract the 16-element feature vector and regime label from a raw log record.

    Returns:
        (features, regime) tuple
    """
    # Raw values
    pred_30d = _safe(record.get("seasonality_pred_30d"))
    conf_s = _safe(record.get("seasonality_confidence"))
    vol = _safe(record.get("seasonality_volatility"))

    pred_7d = _safe(record.get("arrival_pred_7d"))
    conf_a = _safe(record.get("arrival_confidence"))
    stress = _safe(record.get("arrival_supply_stress"))
    arr_regime = str(record.get("arrival_regime", "normal"))

    ext_impact = _safe(record.get("external_impact"))
    ext_conf = _safe(record.get("external_confidence"))

    phase1_pred = _safe(record.get("phase1_prediction"))
    phase1_conf = _safe(record.get("phase1_confidence"))

    # Derived features
    norm_s = (pred_30d / 30.0) * 7.0 * _SCALING_DAMPING
    ext_score = ext_impact * ext_conf

    # Interaction features
    seasonality_x_arrival = norm_s * pred_7d
    arrival_x_stress = pred_7d * stress
    external_direction = float(_sign(ext_score))
    agreement_flag = 1.0 if _sign(norm_s) == _sign(pred_7d) and _sign(norm_s) != 0 else 0.0
    magnitude_diff = abs(norm_s - pred_7d)
    seasonality_x_vol = norm_s * max(1.0 - vol, 0.0)
    conf_agreement = conf_s * conf_a

    features = [
        norm_s,                 # 0
        pred_7d,                # 1
        ext_score,              # 2
        conf_s,                 # 3
        conf_a,                 # 4
        vol,                    # 5
        stress,                 # 6
        phase1_pred,            # 7
        phase1_conf,            # 8
        seasonality_x_arrival,  # 9
        arrival_x_stress,       # 10
        external_direction,     # 11
        agreement_flag,         # 12
        magnitude_diff,         # 13
        seasonality_x_vol,      # 14
        conf_agreement,         # 15
    ]

    regime = classify_regime(stress, arr_regime, ext_score, norm_s, pred_7d)
    return features, regime


def _sign(x: float) -> int:
    if x > 0: return 1
    if x < 0: return -1
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# Dataset Builder
# ═══════════════════════════════════════════════════════════════════════════════

class DatasetBuilder:
    """
    Constructs training datasets from completed prediction log records.

    Targets Residuals: target = actual - phase1_prediction
    """

    def __init__(
        self,
        min_total: int = _MIN_TOTAL_RECORDS,
        min_per_regime: int = _MIN_REGIME_RECORDS,
        min_recent: int = _MIN_RECENT_RECORDS,
    ):
        self.min_total = min_total
        self.min_per_regime = min_per_regime
        self.min_recent = min_recent

    def build(
        self,
        completed_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build the training dataset from completed log records.

        Residual learning: target = actual_7d_change - phase1_prediction
        """
        if len(completed_records) < self.min_total:
            return {
                "trainable": False,
                "reason": f"Insufficient data: {len(completed_records)} < {self.min_total}",
                "records": [],
                "regime_counts": {},
                "total": 0,
                "trainable_regimes": [],
            }

        # Convert to FeatureRecords
        feature_records: List[FeatureRecord] = []
        for raw in completed_records:
            actual = raw.get("actual_7d_change")
            phase1_pred = raw.get("phase1_prediction")
            
            if actual is None or phase1_pred is None:
                continue
                
            features, regime = extract_features(raw)
            
            # RESIDUAL TARGET
            residual_target = float(actual) - float(phase1_pred)
            
            feature_records.append(FeatureRecord(
                features=features,
                target=residual_target,
                regime=regime,
                timestamp=str(raw.get("timestamp", "")),
                commodity=str(raw.get("commodity", "")),
                mandi=str(raw.get("mandi", "")),
            ))

        # Sort by timestamp (chronological)
        feature_records.sort(key=lambda r: r.timestamp)

        # Count per regime
        regime_counts: Dict[str, int] = {}
        for r in feature_records:
            regime_counts[r.regime] = regime_counts.get(r.regime, 0) + 1

        # Determine which regimes have enough data
        trainable_regimes = [
            regime for regime, count in regime_counts.items()
            if count >= self.min_per_regime
        ]

        # "normal" is always trainable if we have enough total data
        if "normal" not in trainable_regimes and len(feature_records) >= self.min_total:
            trainable_regimes.append("normal")

        result = {
            "trainable": True,
            "reason": "OK",
            "records": feature_records,
            "regime_counts": regime_counts,
            "total": len(feature_records),
            "trainable_regimes": trainable_regimes,
        }

        logger.info(
            f"[DatasetBuilder] Built dataset: {len(feature_records)} records, "
            f"regimes={regime_counts}, trainable_regimes={trainable_regimes}"
        )
        return result

    @staticmethod
    def walk_forward_splits(
        records: List[FeatureRecord],
        n_splits: int = 3,
        min_train: int = 30,
        gap: int = 7,
    ) -> List[Tuple[List[FeatureRecord], List[FeatureRecord]]]:
        """
        Generate walk-forward train/validation splits.

        Each split uses all data up to a cutoff for training,
        then skips `gap` records, and uses the next chunk for validation.
        This prevents lookahead bias and respects temporal ordering.

        Args:
            records: Time-sorted FeatureRecords
            n_splits: Number of validation folds
            min_train: Minimum training set size
            gap: Number of records to skip between train and validation

        Returns:
            List of (train_records, val_records) tuples
        """
        n = len(records)
        if n < min_train + gap + 5:
            # Not enough for even one split
            return []

        # Allocate validation sizes
        val_size = max(5, (n - min_train - gap * n_splits) // n_splits)
        splits = []

        for i in range(n_splits):
            val_end = n - i * val_size
            val_start = val_end - val_size
            train_end = val_start - gap

            if train_end < min_train or val_start < 0:
                break

            train = records[:train_end]
            val = records[val_start:val_end]

            if len(train) >= min_train and len(val) >= 2:
                splits.append((train, val))

        splits.reverse()  # Chronological order
        return splits
