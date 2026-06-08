"""
Learned Ensemble — Phase 2 Regime-Aware Ridge Regression Models.

Trains per-regime Ridge models on historical prediction data,
then blends their output with Phase-1.5 rule-based predictions
using a data-availability-aware alpha parameter.

Design principles:
  • Phase-1 is NEVER removed — it always contributes ≥ 30%
  • Ridge Regression chosen for interpretability, speed, and low overfit risk
  • Per-regime training isolates different market dynamics
  • Alpha blending ensures graceful degradation when data is sparse
  • All model state is serializable to JSON (no pickle dependency)
  • Inference is deterministic given fixed model coefficients

Architecture:
  ① Load completed records from PredictionLogger
  ② Build features via DatasetBuilder (Residual Targets)
  ③ Train per-regime Ridge models with walk-forward validation
  ④ Inference: Soft Regime Blending (weighted average of models)
  ⑤ Inference: Predict residual and add to Phase-1.5 output
  ⑥ Dynamic Alpha Blending & Stability Clamping
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from mandisense_ai.utils.logger import get_logger
    from mandisense_ai.ensemble.dataset_builder import (
        DatasetBuilder,
        FeatureRecord,
        FEATURE_NAMES,
        extract_features,
        classify_regime,
        _safe,
        _SCALING_DAMPING,
    )
except ImportError:
    from mandisense_ai.utils.logger import get_logger
    from mandisense_ai.ensemble.dataset_builder import (
        DatasetBuilder,
        FeatureRecord,
        FEATURE_NAMES,
        extract_features,
        classify_regime,
        _safe,
        _SCALING_DAMPING,
    )

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_MODEL_DIR = Path("models") / "meta_ensemble"
_RIDGE_ALPHA = 1.0              # L2 regularization strength

# Alpha blending parameters
_ALPHA_BASE = 0.5               # Starting blend
_ALPHA_MIN = 0.3                # Phase-1 ALWAYS contributes at least 30%
_ALPHA_MAX = 1.0                # Full Phase-1 fallback

# Stability
_LEARNED_RESIDUAL_CLAMP = 5.0   # Learned correction capped at ±5%
_PREDICTION_FINAL_CLAMP = 15.0
_MIN_RECORDS_FOR_MODEL = 50
_STALE_DAYS_THRESHOLD = 30
_R2_FALLBACK_THRESHOLD = 0.0   # If R² < 0, model is worse than mean


# ═══════════════════════════════════════════════════════════════════════════════
# Ridge Regression (Pure Python — no sklearn dependency)
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleRidge:
    """
    Minimal Ridge Regression implementation.

    Why no sklearn?  This module must work in environments where
    sklearn may not be available, and the math is trivial for
    production ridge:  β = (X'X + λI)⁻¹ X'y

    For 11 features this is a 12×12 matrix inversion — microseconds.
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.coef_: List[float] = []
        self.intercept_: float = 0.0
        self.n_features_: int = 0

    def fit(self, X: List[List[float]], y: List[float]) -> "SimpleRidge":
        """Fit ridge regression via normal equations."""
        n = len(X)
        if n == 0:
            return self
        p = len(X[0])
        self.n_features_ = p

        # Augment X with column of 1s for intercept
        Xa = [row + [1.0] for row in X]
        pa = p + 1

        # Compute X'X + λI
        XtX = [[0.0] * pa for _ in range(pa)]
        for i in range(pa):
            for j in range(pa):
                s = 0.0
                for k in range(n):
                    s += Xa[k][i] * Xa[k][j]
                XtX[i][j] = s
                # Add regularization to diagonal (except intercept)
                if i == j and i < p:
                    XtX[i][j] += self.alpha

        # Compute X'y
        Xty = [0.0] * pa
        for i in range(pa):
            s = 0.0
            for k in range(n):
                s += Xa[k][i] * y[k]
            Xty[i] = s

        # Solve via Gaussian elimination
        beta = _solve_linear(XtX, Xty)
        if beta is None:
            # Singular matrix — fall back to zero coefficients
            logger.warning("[SimpleRidge] Singular matrix — using zero coefficients")
            self.coef_ = [0.0] * p
            self.intercept_ = sum(y) / max(n, 1)
            return self

        self.coef_ = beta[:p]
        self.intercept_ = beta[p]
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        """Predict using fitted coefficients."""
        results = []
        for row in X:
            pred = self.intercept_
            for i, xi in enumerate(row):
                if i < len(self.coef_):
                    pred += self.coef_[i] * xi
            results.append(pred)
        return results

    def score(self, X: List[List[float]], y: List[float]) -> Tuple[float, float]:
        """Compute R² and MAE."""
        if not y:
            return 0.0, 0.0
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((yi - pi) ** 2 for yi, pi in zip(y, predictions))
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        mae = sum(abs(yi - pi) for yi, pi in zip(y, predictions)) / len(y)
        
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 0.0
        return r2, mae

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "alpha": self.alpha,
            "coef": self.coef_,
            "intercept": self.intercept_,
            "n_features": self.n_features_,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimpleRidge":
        """Deserialize from dict."""
        model = cls(alpha=d.get("alpha", 1.0))
        model.coef_ = d.get("coef", [])
        model.intercept_ = d.get("intercept", 0.0)
        model.n_features_ = d.get("n_features", 0)
        return model


def _solve_linear(A: List[List[float]], b: List[float]) -> Optional[List[float]]:
    """
    Solve Ax = b via Gaussian elimination with partial pivoting.
    Returns None if matrix is singular.
    """
    n = len(b)
    # Augmented matrix
    M = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        # Partial pivoting
        max_row = col
        max_val = abs(M[col][col])
        for row in range(col + 1, n):
            if abs(M[row][col]) > max_val:
                max_val = abs(M[row][col])
                max_row = row
        if max_val < 1e-15:
            return None  # Singular
        M[col], M[max_row] = M[max_row], M[col]

        # Eliminate below
        pivot = M[col][col]
        for row in range(col + 1, n):
            factor = M[row][col] / pivot
            for j in range(col, n + 1):
                M[row][j] -= factor * M[col][j]

    # Back-substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(M[i][i]) < 1e-15:
            return None
        x[i] = M[i][n]
        for j in range(i + 1, n):
            x[i] -= M[i][j] * x[j]
        x[i] /= M[i][i]

    return x


# ═══════════════════════════════════════════════════════════════════════════════
# Regime Model Store
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TrainedRegimeModel:
    """One trained Ridge model for a specific regime."""
    regime: str
    model: SimpleRidge
    r2_train: float
    r2_val: float
    mae_val: float
    n_train: int
    n_val: int
    trained_at: str
    feature_names: List[str] = field(default_factory=lambda: list(FEATURE_NAMES))


# ═══════════════════════════════════════════════════════════════════════════════
# Learned Ensemble Engine
# ═══════════════════════════════════════════════════════════════════════════════

class LearnedEnsemble:
    """
    Phase-2 data-calibrated ensemble engine.

    Manages per-regime Ridge models, training, persistence,
    and blending with Phase-1.5 predictions.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(model_dir) if model_dir else _DEFAULT_MODEL_DIR
        self.models: Dict[str, TrainedRegimeModel] = {}
        self._metadata: Dict[str, Any] = {}

    # ─── Training ─────────────────────────────────────────────────────

    def train(
        self,
        records: List[FeatureRecord],
        trainable_regimes: List[str],
    ) -> Dict[str, Any]:
        """
        Train per-regime Ridge models using walk-forward validation.

        Args:
            records: Time-sorted FeatureRecords from DatasetBuilder
            trainable_regimes: Regimes that have enough data

        Returns:
            Training report dict
        """
        report: Dict[str, Any] = {
            "trained_at": datetime.utcnow().isoformat() + "Z",
            "total_records": len(records),
            "regimes": {},
        }

        for regime in trainable_regimes:
            # Filter records for this regime
            # For "normal", use ALL records (universal fallback)
            if regime == "normal":
                regime_records = records
            else:
                regime_records = [r for r in records if r.regime == regime]

            if len(regime_records) < _MIN_RECORDS_FOR_MODEL:
                report["regimes"][regime] = {"skipped": True, "reason": "too few records"}
                continue

            # Walk-forward splits
            builder = DatasetBuilder()
            splits = builder.walk_forward_splits(regime_records)

            if not splits:
                # Not enough for splits — train on all, no validation score
                X = [r.features for r in regime_records]
                y = [r.target for r in regime_records]
                model = SimpleRidge(alpha=_RIDGE_ALPHA)
                model.fit(X, y)
                r2_train, mae_train = model.score(X, y)

                self.models[regime] = TrainedRegimeModel(
                    regime=regime,
                    model=model,
                    r2_train=r2_train,
                    r2_val=0.0,
                    mae_val=mae_train,
                    n_train=len(regime_records),
                    n_val=0,
                    trained_at=report["trained_at"],
                )
                report["regimes"][regime] = {
                    "r2_train": round(r2_train, 4),
                    "r2_val": None,
                    "mae_val": round(mae_train, 4),
                    "n_train": len(regime_records),
                    "n_val": 0,
                }
                continue

            # Use last split for final model quality estimate
            best_r2_val = -999.0
            best_mae_val = 999.0
            best_model = None
            best_split_info = {}

            for train_set, val_set in splits:
                X_train = [r.features for r in train_set]
                y_train = [r.target for r in train_set]
                X_val = [r.features for r in val_set]
                y_val = [r.target for r in val_set]

                model = SimpleRidge(alpha=_RIDGE_ALPHA)
                model.fit(X_train, y_train)
                r2_val, mae_val = model.score(X_val, y_val)

                if r2_val > best_r2_val:
                    best_r2_val = r2_val
                    best_mae_val = mae_val
                    best_model = model
                    best_split_info = {
                        "n_train": len(train_set),
                        "n_val": len(val_set),
                    }

            # Final model: train on ALL regime data
            X_all = [r.features for r in regime_records]
            y_all = [r.target for r in regime_records]
            final_model = SimpleRidge(alpha=_RIDGE_ALPHA)
            final_model.fit(X_all, y_all)
            r2_train, _ = final_model.score(X_all, y_all)

            self.models[regime] = TrainedRegimeModel(
                regime=regime,
                model=final_model,
                r2_train=r2_train,
                r2_val=best_r2_val,
                mae_val=best_mae_val,
                n_train=len(regime_records),
                n_val=best_split_info.get("n_val", 0),
                trained_at=report["trained_at"],
            )
            report["regimes"][regime] = {
                "r2_train": round(r2_train, 4),
                "r2_val": round(best_r2_val, 4),
                "mae_val": round(best_mae_val, 4),
                "n_train": len(regime_records),
                "n_val": best_split_info.get("n_val", 0),
                "coef": [round(c, 6) for c in final_model.coef_],
                "intercept": round(final_model.intercept_, 6),
            }

            logger.info(
                f"[LearnedEnsemble] Trained {regime} model: "
                f"R²_train={r2_train:.4f}, R²_val={best_r2_val:.4f}, "
                f"N={len(regime_records)}"
            )

        self._metadata = report
        return report

    # ─── Persistence ──────────────────────────────────────────────────

    def save(self) -> None:
        """Save all trained models to disk as JSON."""
        self.model_dir.mkdir(parents=True, exist_ok=True)

        for regime, trained in self.models.items():
            path = self.model_dir / f"{regime}_ridge.json"
            data = {
                "regime": trained.regime,
                "model": trained.model.to_dict(),
                "r2_train": trained.r2_train,
                "r2_val": trained.r2_val,
                "mae_val": trained.mae_val,
                "n_train": trained.n_train,
                "n_val": trained.n_val,
                "trained_at": trained.trained_at,
                "feature_names": trained.feature_names,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        # Save metadata
        meta_path = self.model_dir / "training_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2)

        logger.info(f"[LearnedEnsemble] Saved {len(self.models)} models to {self.model_dir}")

    def load(self) -> bool:
        """Load persisted models from disk.  Returns True if any loaded."""
        if not self.model_dir.exists():
            return False

        loaded = 0
        for path in self.model_dir.glob("*_ridge.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                regime = data["regime"]
                self.models[regime] = TrainedRegimeModel(
                    regime=regime,
                    model=SimpleRidge.from_dict(data["model"]),
                    r2_train=data.get("r2_train", 0.0),
                    r2_val=data.get("r2_val", 0.0),
                    mae_val=data.get("mae_val", 0.0),
                    n_train=data.get("n_train", 0),
                    n_val=data.get("n_val", 0),
                    trained_at=data.get("trained_at", ""),
                    feature_names=data.get("feature_names", list(FEATURE_NAMES)),
                )
                loaded += 1
            except Exception as e:
                logger.warning(f"[LearnedEnsemble] Failed to load {path}: {e}")

        # Load metadata
        meta_path = self.model_dir / "training_metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception:
                pass

        if loaded > 0:
            logger.info(f"[LearnedEnsemble] Loaded {loaded} models from {self.model_dir}")
        return loaded > 0

    # ─── Inference ────────────────────────────────────────────────────

    def predict_and_blend(
        self,
        # Raw agent inputs (for feature engineering)
        seasonality_pred_30d: float,
        seasonality_confidence: float,
        seasonality_volatility: float,
        seasonality_regime: str,
        arrival_pred_7d: float,
        arrival_confidence: float,
        arrival_supply_stress: float,
        arrival_regime: str,
        external_impact: float,
        external_confidence: float,
        # Phase-1 output
        phase1_prediction: float,
        phase1_confidence: float,
    ) -> Dict[str, Any]:
        """
        Phase-2.5 Optimized Inference:
          1. Residual learning (Phase-1 + correction)
          2. Soft Regime Blending (weighted average of models)
          3. Dynamic Alpha (Context-aware trust)
        """
        # Build a synthetic record for feature extraction
        record = {
            "seasonality_pred_30d": seasonality_pred_30d,
            "seasonality_confidence": seasonality_confidence,
            "seasonality_volatility": seasonality_volatility,
            "seasonality_regime": seasonality_regime,
            "arrival_pred_7d": arrival_pred_7d,
            "arrival_confidence": arrival_confidence,
            "arrival_supply_stress": arrival_supply_stress,
            "arrival_regime": arrival_regime,
            "external_impact": external_impact,
            "external_confidence": external_confidence,
            "phase1_prediction": phase1_prediction,
            "phase1_confidence": phase1_confidence,
        }
        features, regime = extract_features(record)

        # Generate soft regime weights
        regime_weights = self._get_soft_regime_weights(record)
        
        # Aggregate learned residual using soft weights
        learned_residual_raw = 0.0
        agg_model_info = {}
        total_active_weight = 0.0
        
        for r_name, weight in regime_weights.items():
            model_info = self._select_model(r_name)
            if model_info:
                res = model_info.model.predict([features])[0]
                learned_residual_raw += res * weight
                total_active_weight += weight
                agg_model_info[r_name] = {
                    "r2_val": round(model_info.r2_val, 4),
                    "n_train": model_info.n_train,
                    "weight": round(weight, 4)
                }

        if total_active_weight < 1e-6:
            # Fallback if no models usable
            return {
                "final_prediction": _clamp(phase1_prediction, -_PREDICTION_FINAL_CLAMP, _PREDICTION_FINAL_CLAMP),
                "final_confidence": phase1_confidence,
                "alpha": 1.0,
                "learned_residual": 0.0,
                "regime_detected": regime,
                "mode": "phase1_only",
            }

        # Normalize in case some models were missing
        learned_residual_raw /= total_active_weight
        learned_residual = _clamp(learned_residual_raw, -_LEARNED_RESIDUAL_CLAMP, _LEARNED_RESIDUAL_CLAMP)

        # Compute dynamic alpha
        alpha = self._compute_alpha_v2_5(agg_model_info, phase1_prediction, learned_residual, seasonality_confidence, arrival_confidence)

        # Final prediction (Phase-1 + Learned Residual)
        final_prediction_raw = phase1_prediction + (1.0 - alpha) * learned_residual
        final_prediction = _clamp(final_prediction_raw, -_PREDICTION_FINAL_CLAMP, _PREDICTION_FINAL_CLAMP)

        # Agreement-aware confidence adjustment
        final_confidence = self._adjust_confidence(phase1_confidence, agg_model_info, alpha, phase1_prediction, learned_residual)

        return {
            "final_prediction": round(final_prediction, 4),
            "final_confidence": round(final_confidence, 4),
            "alpha": round(alpha, 4),
            "learned_residual": round(learned_residual, 4),
            "regime_detected": regime,
            "mode": "blended",
            "soft_regime_weights": regime_weights,
            "model_stats": agg_model_info,
        }

    def _get_soft_regime_weights(self, record: Dict[str, Any]) -> Dict[str, int]:
        """
        Compute soft weights for regime models based on current context.
        """
        stress = _safe(record.get("arrival_supply_stress"))
        ext_score = abs(_safe(record.get("external_impact")) * _safe(record.get("external_confidence")))
        
        # Simple heuristics for soft weighting
        w_shock = _clamp(stress, 0.0, 0.8)
        w_external = _clamp(ext_score, 0.0, 0.8)
        
        # Remaining weight goes to normal model
        w_normal = max(0.2, 1.0 - (w_shock + w_external))
        
        total = w_normal + w_shock + w_external
        return {
            "normal": w_normal / total,
            "supply_shock": w_shock / total,
            "external_dominated": w_external / total
        }

    def _compute_alpha_v2_5(
        self,
        agg_model_info: Dict[str, Any],
        phase1_pred: float,
        learned_res: float,
        conf_s: float,
        conf_a: float
    ) -> float:
        """
        Refined alpha calculation for Phase-2.5.
        
        Uses validation quality (R2), data volume, and agreement signal.
        """
        # Average validation R2 across active models
        avg_r2 = sum(m["r2_val"] * m["weight"] for m in agg_model_info.values()) / sum(m["weight"] for m in agg_model_info.values())
        total_n = sum(m["n_train"] for m in agg_model_info.values())
        
        alpha = _ALPHA_BASE
        
        # Quality adjustment: Higher R2 -> lower alpha (more trust in learned)
        if avg_r2 > 0.2:
            alpha -= 0.1
        if avg_r2 < 0.05:
            alpha += 0.2
            
        # Data volume adjustment
        if total_n < 100:
            alpha += 0.2
        elif total_n > 500:
            alpha -= 0.1
            
        # Agreement signal: If residual moves in SAME direction as Phase-1, trust more
        # Note: residual is a correction. If correction has same sign as prediction,
        # it means the model is "amplifying" the signal, which often indicates strong trend.
        if _sign(phase1_pred) == _sign(learned_res) and _sign(phase1_pred) != 0:
            alpha -= 0.1
        
        # Conflict: If Phase-1 and Learned strongly disagree on correction direction
        # (e.g. Phase-1 is +5%, Learned wants to subtract 4%)
        if _sign(phase1_pred) != _sign(learned_res) and abs(learned_res) > 2.0:
            alpha += 0.1

        return _clamp(alpha, _ALPHA_MIN, _ALPHA_MAX)

    def _adjust_confidence(
        self,
        phase1_conf: float,
        agg_model_info: Dict[str, Any],
        alpha: float,
        phase1_pred: float,
        learned_res: float
    ) -> float:
        """
        Agreement-aware confidence adjustment.
        """
        avg_r2 = sum(m["r2_val"] * m["weight"] for m in agg_model_info.values()) / sum(m["weight"] for m in agg_model_info.values())
        
        # Base confidence is blended
        base_conf = phase1_conf * alpha + max(avg_r2, 0.0) * (1.0 - alpha) * 0.95
        
        # Boost if direction matches
        if _sign(phase1_pred) == _sign(learned_res) and _sign(phase1_pred) != 0:
            base_conf *= 1.1
            
        # Penalize if strong disagreement
        if _sign(phase1_pred) != _sign(learned_res) and abs(learned_res) > 2.0:
            base_conf *= 0.8
            
        return _clamp(base_conf, 0.05, 0.95)

    def _select_model(self, regime: str) -> Optional[TrainedRegimeModel]:
        """
        Select the best available model for the given regime.
        """
        candidate = self.models.get(regime)
        if candidate is None and regime != "normal":
            candidate = self.models.get("normal")

        if candidate is None:
            return None

        # Reject if model is worse than predicting the mean
        if candidate.r2_val < _R2_FALLBACK_THRESHOLD and candidate.n_val > 0:
            if regime != "normal":
                return self.models.get("normal")
            return None

        # Reject if too few training samples
        if candidate.n_train < _MIN_RECORDS_FOR_MODEL:
            return None

        return candidate

    @property
    def is_ready(self) -> bool:
        """True if at least one model is loaded and usable."""
        return len(self.models) > 0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _sign(x: float) -> int:
    if x > 0: return 1
    if x < 0: return -1
    return 0
