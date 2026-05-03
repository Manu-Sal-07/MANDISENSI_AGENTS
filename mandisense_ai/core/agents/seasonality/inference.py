from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from config.settings import settings
from utils.logger import get_logger
from core.agents.seasonality.multi_horizon import FEATURE_COLS, HORIZON_LABELS, SeasonalityMultiHorizonPipeline, _as_2d

logger = get_logger(__name__)

BUNDLE_SUMMARY_FILENAME = "ensemble_summary.json"
MODEL_FILENAME = "trained_model.pkl"

MANDI_MAP = {
    "kolar": 0,
    "lasalgaon": 1,
    "agra": 2,
    "guntur": 3,
    "neemuch": 4,
    "bangalore": 5,
    "unknown": 99
}


@dataclass
class SeasonalityInferenceResult:
    stable_prediction: Dict[str, float]
    ensemble_prediction: Dict[str, float]
    weights_per_horizon: Dict[str, Dict[str, float]]
    best_models_per_horizon: Dict[str, str]
    confidence: float
    model_artifact_dir: Path
    feature_columns: List[str]
    target_columns: List[str]
    metrics_per_model: Dict[str, Dict[str, Dict[str, float]]]
    training_timestamp: str
    training_mean: np.ndarray
    model_names: List[str]
    model_breakdown: Dict[str, Dict[str, float]]


class SeasonalityModelBundle:
    def __init__(
        self,
        root: Path,
        models: Dict[str, Any],
        weights_per_horizon: Dict[str, Dict[str, float]],
        best_models_per_horizon: Dict[str, str],
        confidence: float,
        ensemble_prediction: Dict[str, float],
        stable_prediction: Dict[str, float],
        feature_columns: List[str],
        target_columns: List[str],
        metrics_per_model: Dict[str, Dict[str, Dict[str, float]]],
        training_timestamp: str,
        training_mean: np.ndarray,
    ):
        self.root = root
        self.models = models
        self.weights_per_horizon = weights_per_horizon
        self.best_models_per_horizon = best_models_per_horizon
        self.confidence = confidence
        self.ensemble_prediction = ensemble_prediction
        self.stable_prediction = stable_prediction
        self.feature_columns = feature_columns
        self.target_columns = target_columns
        self.metrics_per_model = metrics_per_model
        self.training_timestamp = training_timestamp
        self.training_mean = training_mean

    @staticmethod
    def _safe_load_pickle(path: Path) -> Any:
        with path.open("rb") as fh:
            return pickle.load(fh)

    @classmethod
    def _bundle_root(cls, commodity: str, mandi: str, models_dir: Optional[str] = None) -> Path:
        root = Path(models_dir or settings.paths.models_dir)
        if root.name != "seasonality":
            root = root / "seasonality"
        # Transitioning to commodity-level bundles for mandi-aware architecture
        return root / commodity.strip().lower().replace(" ", "_")

    @classmethod
    def load(cls, commodity: str, mandi: str, models_dir: Optional[str] = None) -> "SeasonalityModelBundle":
        root = cls._bundle_root(commodity, mandi, models_dir)
        summary_path = root / BUNDLE_SUMMARY_FILENAME
        if not summary_path.exists():
            raise FileNotFoundError(f"Seasonality model bundle not found at {summary_path}")

        manifest = json.loads(summary_path.read_text(encoding="utf-8"))
        model_names = set()
        weights_per_horizon = manifest.get("weights_per_horizon", {})
        for weights in weights_per_horizon.values():
            model_names.update(weights.keys())

        models: Dict[str, Any] = {}
        for model_name in model_names:
            model_path = root / model_name / MODEL_FILENAME
            if model_path.exists():
                try:
                    models[model_name] = cls._safe_load_pickle(model_path)
                except Exception as exc:
                    logger.warning(f"Failed to load seasonality model {model_name}: {exc}")
            else:
                logger.warning(f"Missing seasonality model artifact: {model_path}")

        if not models:
            raise FileNotFoundError(f"No seasonality models could be loaded from {root}")

        training_mean = np.asarray(manifest.get("training_mean", [0.0] * len(HORIZON_LABELS)), dtype="float64")
        if training_mean.shape != (len(HORIZON_LABELS),):
            training_mean = np.zeros(len(HORIZON_LABELS), dtype="float64")

        return cls(
            root=root,
            models=models,
            weights_per_horizon=weights_per_horizon,
            best_models_per_horizon=manifest.get("best_models_per_horizon", {}),
            confidence=float(manifest.get("confidence", 0.0)),
            ensemble_prediction={k: float(v) for k, v in manifest.get("ensemble_prediction", {}).items()},
            stable_prediction={k: float(v) for k, v in manifest.get("stable_prediction", {}).items()},
            feature_columns=list(manifest.get("feature_columns", FEATURE_COLS)),
            target_columns=list(manifest.get("target_columns", [])),
            metrics_per_model=manifest.get("metrics_per_model", {}),
            training_timestamp=str(manifest.get("training_timestamp", "")),
            training_mean=training_mean,
        )

    def _normalize_weights(self) -> Dict[str, Dict[str, float]]:
        normalized: Dict[str, Dict[str, float]] = {}
        for horizon, weights in self.weights_per_horizon.items():
            active = {name: weight for name, weight in weights.items() if name in self.models}
            if not active:
                active = {name: 1.0 for name in self.models}
            total = sum(active.values()) or 1.0
            normalized[horizon] = {name: float(weight / total) for name, weight in active.items()}
        return normalized

    def _safe_predict(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        fallback = np.tile(self.training_mean.reshape(1, -1), (len(X), 1))
        try:
            pred = _as_2d(model.predict(X), len(X))
            pred = np.where(np.isfinite(pred), pred, fallback)
            return np.clip(pred, -0.50, 0.50)
        except Exception as exc:
            logger.warning(f"Seasonality model prediction failed for {model}: {exc}")
            return fallback

    def predict(self, X: pd.DataFrame) -> Dict[str, Any]:
        if X.empty:
            raise ValueError("Inference feature dataframe is empty")

        weights = self._normalize_weights()
        raw_preds = {label: 0.0 for label in HORIZON_LABELS}
        model_breakdown: Dict[str, Dict[str, float]] = {}

        for model_name, model in self.models.items():
            pred = self._safe_predict(model, X)[0]
            avg_weight = float(np.mean([weights[label].get(model_name, 0.0) for label in HORIZON_LABELS]))
            model_breakdown[model_name] = {
                "prediction": round(float(pred[HORIZON_LABELS.index("30d")]) * 100.0, 6),
                "weight": round(avg_weight, 6),
            }

            for idx, label in enumerate(HORIZON_LABELS):
                raw_preds[label] += float(pred[idx]) * weights[label].get(model_name, 0.0)

        stable_preds = SeasonalityMultiHorizonPipeline().enforce_stability(raw_preds)
        return {
            "stable_prediction": stable_preds,
            "ensemble_prediction": raw_preds,
            "weights_per_horizon": weights,
            "model_breakdown": model_breakdown,
        }


class SeasonalityInferencePipeline:
    """Runtime seasonality inference using pretrained model bundles."""

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir or settings.paths.models_dir)

    @staticmethod
    def _stl_period(window_len: int) -> int:
        if window_len < 8:
            raise ValueError("Insufficient history to compute STL decomposition (need at least 8 observations)")
        return min(365, max(3, window_len // 2))

    @staticmethod
    def _compute_stl_components(series: pd.Series) -> Dict[str, float]:
        values = series.astype(float).dropna().to_numpy()
        if len(values) < 8:
            raise ValueError("Insufficient history to compute STL decomposition (need at least 8 observations)")

        period = SeasonalityInferencePipeline._stl_period(len(values))
        stl = STL(values, period=period, seasonal=21, robust=True)
        result = stl.fit()

        return {
            "trend": float(result.trend[-1]),
            "seasonal": float(result.seasonal[-1]),
            "residual": float(result.resid[-1]),
        }

    def build_inference_features(
        self,
        df: pd.DataFrame,
        mandi_name: str,
        timestamp: Optional[datetime] = None,
        feature_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        data = df.copy()
        data["date"] = pd.to_datetime(data["date"])
        data = data.sort_values("date")

        if timestamp is None:
            timestamp = data["date"].max()

        data = data[data["date"] <= timestamp]
        if data.empty:
            raise ValueError(f"No historical data is available on or before {timestamp}")

        feature_columns = feature_columns or FEATURE_COLS
        historical_window = data[data["date"] >= timestamp - pd.Timedelta(days=365)].copy()

        if historical_window.empty:
            raise ValueError(
                "Insufficient historical history for inference: no data found within the last 365 days before the requested timestamp"
            )

        historical_window["price_lag_1"] = historical_window["modal_price"].shift(1)
        historical_window["price_lag_7"] = historical_window["modal_price"].shift(7)
        historical_window["price_lag_14"] = historical_window["modal_price"].shift(14)
        historical_window["price_mean_7"] = historical_window["modal_price"].shift(1).rolling(7, min_periods=4).mean()
        historical_window["price_std_7"] = historical_window["modal_price"].shift(1).rolling(7, min_periods=4).std()
        historical_window["price_mean_30"] = historical_window["modal_price"].shift(1).rolling(30, min_periods=10).mean()
        historical_window["price_std_30"] = historical_window["modal_price"].shift(1).rolling(30, min_periods=10).std()
        historical_window["returns"] = historical_window["modal_price"].pct_change().fillna(0.0)
        historical_window["momentum_7d"] = (
            historical_window["modal_price"] / historical_window["price_lag_7"].replace(0, np.nan) - 1.0
        )
        historical_window["log_returns"] = np.log(
            historical_window["modal_price"] / historical_window["modal_price"].shift(1).replace(0, np.nan)
        )
        historical_window["volatility_7d"] = historical_window["log_returns"].rolling(7, min_periods=4).std().fillna(0.0)
        historical_window["month"] = float(timestamp.month)
        historical_window["day_of_week"] = float(timestamp.weekday())
        historical_window["mandi_id"] = float(MANDI_MAP.get(mandi_name.lower(), MANDI_MAP['unknown']))

        if any(col in feature_columns for col in ("trend", "seasonal", "residual")):
            stl_features = self._compute_stl_components(historical_window["modal_price"])
        else:
            stl_features = {}

        latest = historical_window.iloc[[-1]].copy()
        if latest.empty:
            raise ValueError("Unable to derive the latest inference row from historical data")

        features = latest[FEATURE_COLS].copy()
        for name, value in stl_features.items():
            features[name] = value

        features = features.reindex(columns=feature_columns, fill_value=0.0)
        features = features.replace([np.inf, -np.inf], np.nan)

        if features.isna().any(axis=None):
            missing = features.columns[features.isna().any()].tolist()
            raise ValueError(f"Inference feature construction returned missing values for columns: {missing}")

        if not np.isfinite(features.to_numpy()).all():
            raise ValueError("Inference feature construction returned non-finite values")

        return features

    def infer(self, df: pd.DataFrame, commodity: str, mandi: str) -> SeasonalityInferenceResult:
        if df.empty:
            raise ValueError("Processed data is empty; cannot perform seasonality inference")

        features = self.build_inference_features(df, mandi_name=mandi)
        if features.empty or features.iloc[-1].isna().any():
            raise ValueError("Insufficient historical data to construct seasonality inference features")

        bundle = SeasonalityModelBundle.load(commodity, mandi, self.models_dir.as_posix())
        prediction_result = bundle.predict(features.iloc[[-1]])

        return SeasonalityInferenceResult(
            stable_prediction=prediction_result["stable_prediction"],
            ensemble_prediction=prediction_result["ensemble_prediction"],
            weights_per_horizon=bundle.weights_per_horizon,
            best_models_per_horizon=bundle.best_models_per_horizon,
            confidence=bundle.confidence,
            model_artifact_dir=bundle.root,
            feature_columns=bundle.feature_columns,
            target_columns=bundle.target_columns,
            metrics_per_model=bundle.metrics_per_model,
            training_timestamp=bundle.training_timestamp,
            training_mean=bundle.training_mean,
            model_names=list(bundle.models.keys()),
            model_breakdown=prediction_result["model_breakdown"],
        )

    def inference_payload(
        self,
        df: pd.DataFrame,
        commodity: str,
        mandi: str,
        result: SeasonalityInferenceResult,
    ) -> Dict[str, Any]:
        current_price = float(df.sort_values("date")["modal_price"].iloc[-1])
        forecasts = {
            label: {
                "pct": round(float(result.stable_prediction[label]) * 100.0, 4),
                "price": round(current_price * (1.0 + float(result.stable_prediction[label])), 2),
            }
            for label in HORIZON_LABELS
        }
        return {
            "commodity": commodity,
            "mandi": mandi,
            "seasonality_agent": {
                "forecasts": forecasts,
                "weights_per_horizon": result.weights_per_horizon,
                "best_models_per_horizon": result.best_models_per_horizon,
                "confidence": result.confidence,
                "model_artifact_dir": str(result.model_artifact_dir),
                "feature_columns": result.feature_columns,
                "target_columns": result.target_columns,
                "training_timestamp": result.training_timestamp,
                "metrics_per_model": result.metrics_per_model,
                "model_breakdown": result.model_breakdown,
            },
        }
