from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd

try:
    from mandisense_ai.config.settings import settings
except ImportError:
    from mandisense_ai.config.settings import settings
try:
    from mandisense_ai.core.agents.seasonality.inference import SeasonalityInferencePipeline
    from mandisense_ai.core.agents.seasonality.multi_horizon import (
        HORIZON_LABELS,
        SeasonalityMultiHorizonPipeline,
        _as_2d,
    )
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from mandisense_ai.core.agents.seasonality.inference import SeasonalityInferencePipeline
    from mandisense_ai.core.agents.seasonality.multi_horizon import (
        HORIZON_LABELS,
        SeasonalityMultiHorizonPipeline,
        _as_2d,
    )
    from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def _safe_slug(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("/", "-")


def _bundle_path(commodity: str, mandi: str, models_dir: Optional[str] = None) -> Path:
    root = Path(models_dir or settings.paths.models_dir)
    return root / f"{_safe_slug(commodity)}_{_safe_slug(mandi)}" / "seasonality" / "bundle.pkl"


def _validate_bundle(bundle: Dict[str, Any]) -> None:
    required_keys = {"models", "weights", "feature_columns", "target_columns", "metadata"}
    missing_keys = required_keys - set(bundle.keys())
    if missing_keys:
        raise ValueError(f"Seasonality bundle is missing required keys: {sorted(missing_keys)}")

    if not isinstance(bundle["models"], dict) or not bundle["models"]:
        raise ValueError("Seasonality bundle must contain a non-empty models dictionary")

    if not isinstance(bundle["weights"], dict):
        raise ValueError("Seasonality bundle weights must be a dict")

    if not isinstance(bundle["feature_columns"], list) or not bundle["feature_columns"]:
        raise ValueError("Seasonality bundle feature_columns must be a non-empty list")

    if not isinstance(bundle["metadata"], dict):
        raise ValueError("Seasonality bundle metadata must be a dictionary")


from functools import lru_cache

@lru_cache(maxsize=10)
def load_seasonality_bundle(
    commodity: str,
    mandi: str,
    models_dir: Optional[str] = None,
) -> Dict[str, Any]:
    bundle_path = _bundle_path(commodity, mandi, models_dir=models_dir)
    if not bundle_path.exists():
        logger.warning("Seasonality bundle not found at %s", bundle_path)
        raise FileNotFoundError(f"Seasonality bundle not found at {bundle_path}")

    bundle = joblib.load(bundle_path)
    _validate_bundle(bundle)
    logger.info(
        "Loaded seasonality bundle from %s (%d models)",
        bundle_path,
        len(bundle["models"]),
    )
    return bundle



def align_features(features: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    aligned = features.copy()
    missing_columns = [col for col in feature_columns if col not in aligned.columns]
    for column in missing_columns:
        aligned[column] = 0.0

    aligned = aligned.reindex(columns=feature_columns)
    if aligned.isna().all(axis=1).any():
        raise ValueError("Aligned inference features contain only missing values for one or more rows")

    return aligned


def save_seasonality_bundle(bundle: Dict[str, Any], commodity: str, mandi: str, models_dir: Optional[str] = None) -> Path:
    bundle_path = _bundle_path(commodity, mandi, models_dir=models_dir)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)

    if bundle_path.exists():
        backup_path = bundle_path.with_name(
            f"bundle.pkl.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        )
        bundle_path.replace(backup_path)
        logger.info("Existing seasonality bundle moved to %s", backup_path)

    joblib.dump(bundle, bundle_path)
    logger.info(
        "Saved seasonality bundle to %s (%d models, trained_at=%s)",
        bundle_path,
        len(bundle["models"]),
        bundle["metadata"]["trained_at"],
    )
    return bundle_path


def train_seasonality_models(
    df: pd.DataFrame,
    commodity: str,
    mandi: str,
    models_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Train seasonality models and return the training bundle.

    This function is intentionally separated from the agent runtime so that
    training logic is isolated from inference orchestration.
    """
    pipeline = SeasonalityMultiHorizonPipeline(models_dir=models_dir)
    prepared_data = pipeline.prepare_dataset(df)
    result = pipeline.train(df, commodity=commodity, mandi=mandi)

    trained_at = datetime.utcnow().isoformat() + "Z"
    metadata = {
        "trained_at": trained_at,
        "n_samples": len(prepared_data),
        "cv_scores": result.metrics_per_model,
        "metrics_per_model": result.metrics_per_model,
        "model_names": list(result.models.keys()),
        "best_models_per_horizon": result.best_models_per_horizon,
        "weights_per_horizon": result.weights_per_horizon,
        "feature_columns": result.feature_columns,
        "target_columns": result.target_columns,
        "confidence": result.confidence,
    }

    bundle = {
        "models": result.models,
        "weights": result.weights_per_horizon,
        "feature_columns": result.feature_columns,
        "target_columns": result.target_columns,
        "metadata": metadata,
    }

    save_seasonality_bundle(bundle, commodity, mandi, models_dir=models_dir)
    return bundle


def build_features(df: pd.DataFrame, mandi_name: str = "unknown") -> pd.DataFrame:
    """Build inference-ready seasonality features from the input dataset."""
    inference_pipeline = SeasonalityInferencePipeline()
    return inference_pipeline.build_inference_features(df, mandi_name=mandi_name)


def predict_per_model(bundle: Dict[str, Any], features: pd.DataFrame) -> Dict[str, np.ndarray]:
    """Generate per-model predictions for validated inference features."""
    if features.empty:
        raise ValueError("No inference features could be built from input data.")

    trained_models = bundle["models"]
    valid_predictions: Dict[str, np.ndarray] = {}

    feature_row = features.iloc[[-1]]
    for model_name, model in trained_models.items():
        try:
            raw_output = model.predict(feature_row)
            model_pred = _as_2d(raw_output, n_rows=1)[0]
        except Exception as exc:
            logger.warning(
                "Seasonality model %s failed during predict(): %s",
                model_name,
                exc,
            )
            continue

        if not np.all(np.isfinite(model_pred)):
            logger.warning(
                "Seasonality model %s produced invalid prediction values and will be excluded.",
                model_name,
            )
            continue

        if model_pred.shape[0] != len(HORIZON_LABELS):
            logger.warning(
                "Seasonality model %s returned %d outputs; expected %d. It will be excluded.",
                model_name,
                model_pred.shape[0],
                len(HORIZON_LABELS),
            )
            continue

        valid_predictions[model_name] = model_pred

    if not valid_predictions:
        raise RuntimeError("All seasonality ensemble models failed or returned invalid predictions.")

    return valid_predictions


def _normalize_ensemble_weights(
    model_weights: Any,
    valid_models: set[str],
) -> Dict[str, Dict[str, float]]:
    normalized: Dict[str, Dict[str, float]] = {}

    if isinstance(model_weights, dict) and all(
        isinstance(value, dict) for value in model_weights.values()
    ):
        for label in HORIZON_LABELS:
            label_weights = {
                model_name: float(model_weights.get(label, {}).get(model_name, 0.0))
                for model_name in valid_models
            }
            total = sum(label_weights.values()) or float(len(label_weights) or 1)
            normalized[label] = {
                model_name: weight / total
                for model_name, weight in label_weights.items()
            }
    else:
        uniform = {
            model_name: float(model_weights.get(model_name, 0.0))
            for model_name in valid_models
        }
        total = sum(uniform.values()) or float(len(uniform) or 1)
        normalized = {
            label: {
                model_name: weight / total
                for model_name, weight in uniform.items()
            }
            for label in HORIZON_LABELS
        }

    return normalized


def compute_confidence(
    model_predictions: Dict[str, np.ndarray],
    weights: Dict[str, Dict[str, float]],
    metadata: Dict[str, Any],
    feature_row: pd.Series,
    final_prediction: float,
) -> float:
    """Compute a deterministic confidence score from model agreement, CV reliability, and signal strength."""
    preds_30d = np.array(
        [pred[HORIZON_LABELS.index("30d")] for pred in model_predictions.values()],
        dtype="float64",
    )

    if len(preds_30d) == 1:
        agreement_score = 0.90
    else:
        prediction_std = float(np.std(preds_30d, ddof=0))
        agreement_score = 1.0 - min(prediction_std / 0.08, 1.0)

    cv_scores = metadata.get("cv_scores") or metadata.get("metrics_per_model") or {}
    model_mapes: list[float] = []
    for model_name in model_predictions:
        model_metrics = cv_scores.get(model_name, {})
        if isinstance(model_metrics, dict):
            target_metrics = model_metrics.get("30d") or model_metrics.get("30d", {})
            if isinstance(target_metrics, dict) and "MAPE" in target_metrics:
                model_mapes.append(float(target_metrics["MAPE"]))

    if model_mapes:
        avg_mape = float(np.mean(model_mapes))
        inverse_mape_score = 1.0 / (1.0 + max(avg_mape, 1e-6) * 10.0)
    else:
        inverse_mape_score = 0.60

    signal_strength_score = min(abs(final_prediction) / 0.12, 1.0)
    signal_strength_score = max(signal_strength_score, 0.10)

    volatility = float(feature_row.get("volatility_7d", 0.0) or 0.0)
    volatility_penalty = min(max((volatility - 0.08) / 0.12, 0.0), 0.35)

    confidence = (
        0.40 * agreement_score
        + 0.40 * inverse_mape_score
        + 0.20 * signal_strength_score
        - volatility_penalty
    )
    confidence = float(np.clip(confidence, 0.05, 0.95))
    return confidence


def aggregate_predictions(
    model_predictions: Dict[str, np.ndarray],
    model_weights: Any,
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], Dict[str, Dict[str, Any]]]:
    """Aggregate valid model predictions using stored ensemble weights."""
    valid_models = set(model_predictions.keys())
    normalized_weights = _normalize_ensemble_weights(model_weights, valid_models)

    ensemble_preds: Dict[str, float] = {label: 0.0 for label in HORIZON_LABELS}
    model_breakdown: Dict[str, Dict[str, Any]] = {}

    for model_name, preds in model_predictions.items():
        model_weight_values = [normalized_weights[label].get(model_name, 0.0) for label in HORIZON_LABELS]
        avg_model_weight = float(np.mean(model_weight_values)) if model_weight_values else 0.0
        model_breakdown[model_name] = {
            "prediction": float(preds[HORIZON_LABELS.index("30d")]),
            "weight": round(avg_model_weight, 6),
        }

        for idx, label in enumerate(HORIZON_LABELS):
            ensemble_preds[label] += float(preds[idx]) * normalized_weights[label].get(model_name, 0.0)

    # Fix 6: Remove excessive clamping before final stage
    # ensemble_preds = {
    #     label: float(np.clip(value, -0.15, 0.15))
    #     for label, value in ensemble_preds.items()
    # }

    return ensemble_preds, normalized_weights, model_breakdown


def predict_with_ensemble(bundle: Dict[str, Any], features: pd.DataFrame) -> Dict[str, Any]:
    """Predict seasonality from trained models and a validated feature vector."""
    if features.empty:
        raise ValueError("No inference features could be built from input data.")

    bundle_weights = bundle["weights"]
    bundle_metadata = bundle.get("metadata", {})
    model_predictions = predict_per_model(bundle, features)
    ensemble_preds, normalized_weights, model_breakdown = aggregate_predictions(
        model_predictions,
        bundle_weights,
    )

    stable_prediction = SeasonalityMultiHorizonPipeline().enforce_stability(ensemble_preds)
    final_prediction = float(stable_prediction["30d"])
    confidence = compute_confidence(
        model_predictions=model_predictions,
        weights=normalized_weights,
        metadata=bundle_metadata,
        feature_row=features.iloc[0],
        final_prediction=final_prediction,
    )

    prediction_std = float(np.std(
        [pred[HORIZON_LABELS.index("30d")] for pred in model_predictions.values()],
        ddof=0,
    ))

    return {
        "prediction": final_prediction,
        "confidence": confidence,
        "stable_prediction": stable_prediction,
        "ensemble_prediction": ensemble_preds,
        "model_breakdown": model_breakdown,
        "metadata": {
            "n_models_used": len(model_predictions),
            "prediction_std": prediction_std,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "weights_used": normalized_weights,
        },
    }
