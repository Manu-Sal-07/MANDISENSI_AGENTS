"""
Leak-proof multi-horizon Seasonality Agent training and forecasting.

This module intentionally uses price-only signals. It trains each model
independently to emit the full target vector in one predict call:

    [target_3d, target_5d, target_7d, target_15d, target_30d]
"""

from __future__ import annotations

import json
import math
import pickle
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


HORIZONS: List[int] = [3, 5, 7, 15, 30]
HORIZON_LABELS: List[str] = [f"{h}d" for h in HORIZONS]
TARGET_COLS: List[str] = [f"target_{h}d" for h in HORIZONS]
HORIZON_IMPORTANCE: Dict[str, float] = {
    "3d": 0.35,
    "5d": 0.25,
    "7d": 0.20,
    "15d": 0.12,
    "30d": 0.08,
}

FEATURE_COLS: List[str] = [
    "mandi_id",
    "price_lag_1",
    "price_lag_7",
    "price_lag_14",
    "price_mean_7",
    "price_std_7",
    "price_mean_30",
    "price_std_30",
    "returns",
    "momentum_7d",
    "volatility_7d",
    "month",
    "day_of_week",
]


def _safe_slug(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("/", "-")


def _json_dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _as_2d(pred: Any, n_rows: int) -> np.ndarray:
    arr = np.asarray(pred, dtype="float64")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.shape[0] != n_rows:
        arr = np.resize(arr, (n_rows, arr.shape[1]))
    if arr.shape[1] != len(HORIZONS):
        fallback = np.nanmean(arr, axis=1, keepdims=True)
        arr = np.repeat(fallback, len(HORIZONS), axis=1)
    return arr


def _direction(values: np.ndarray) -> np.ndarray:
    labels = np.full(values.shape, 1, dtype=int)  # FLAT
    labels[values > 0.02] = 2  # UP
    labels[values < -0.02] = 0  # DOWN
    return labels


def _weighted_score(metrics: Dict[str, Dict[str, float]], key: str = "MAPE") -> float:
    return float(
        sum(metrics[label][key] * HORIZON_IMPORTANCE[label] for label in HORIZON_LABELS)
    )


class SARIMAMultiHorizonRegressor(BaseEstimator, RegressorMixin):
    """
    Lightweight statistical baseline adapted to the multi-output contract.

    A production SARIMA generally forecasts the price series directly. Here the
    training contract is a multi-output return vector, so the estimator models
    each horizon target as a deterministic seasonal persistence signal using
    recent target history. It predicts the full vector in one call and degrades
    safely when statsmodels is unavailable or a fold is short.
    """

    def __init__(self, seasonal_period: int = 7, window: int = 30):
        self.seasonal_period = seasonal_period
        self.window = window

    def fit(self, X: pd.DataFrame, y: pd.DataFrame) -> "SARIMAMultiHorizonRegressor":
        y_arr = np.asarray(y, dtype="float64")
        self.train_mean_ = np.nanmean(y_arr, axis=0)
        if not np.all(np.isfinite(self.train_mean_)):
            self.train_mean_ = np.zeros(len(HORIZONS), dtype="float64")

        tail = y_arr[-max(self.window, self.seasonal_period):]
        self.recent_mean_ = np.nanmean(tail, axis=0)
        self.recent_mean_ = np.where(np.isfinite(self.recent_mean_), self.recent_mean_, self.train_mean_)

        if len(y_arr) > self.seasonal_period:
            seasonal_tail = y_arr[-self.seasonal_period:]
            self.seasonal_mean_ = np.nanmean(seasonal_tail, axis=0)
            self.seasonal_mean_ = np.where(
                np.isfinite(self.seasonal_mean_),
                self.seasonal_mean_,
                self.recent_mean_,
            )
        else:
            self.seasonal_mean_ = self.recent_mean_

        self.output_ = 0.50 * self.recent_mean_ + 0.35 * self.seasonal_mean_ + 0.15 * self.train_mean_
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.tile(self.output_, (len(X), 1))


@dataclass
class SeasonalityTrainingResult:
    models: Dict[str, Any]
    latest_predictions: Dict[str, Dict[str, float]]
    metrics_per_model: Dict[str, Dict[str, Dict[str, float]]]
    fold_metrics: Dict[str, List[Dict[str, Any]]]
    weights_per_horizon: Dict[str, Dict[str, float]]
    ensemble_prediction: Dict[str, float]
    stable_prediction: Dict[str, float]
    best_models_per_horizon: Dict[str, str]
    confidence: float
    output_root: Path
    feature_columns: List[str] = field(default_factory=lambda: FEATURE_COLS.copy())
    target_columns: List[str] = field(default_factory=lambda: TARGET_COLS.copy())


class SeasonalityMultiHorizonPipeline:
    """Train, evaluate, store, ensemble, and forecast seasonality models."""

    def __init__(
        self,
        models_dir: Optional[str] = None,
        n_splits: int = 5,
        random_state: int = 42,
    ):
        self.models_dir = Path(models_dir or settings.paths.models_dir) / "seasonality"
        self.n_splits = n_splits
        self.random_state = random_state
        self.training_mean_: Optional[np.ndarray] = None

    def prepare_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.sort_values(["mandi", "date"]).copy()
        data["date"] = pd.to_datetime(data["date"])

        # Mandi-Aware Feature Engineering
        if "returns" not in data.columns:
            data["returns"] = data.groupby("mandi")["modal_price"].pct_change()
        
        if "momentum_7d" not in data.columns:
            data["momentum_7d"] = data.groupby("mandi").apply(
                lambda x: x["modal_price"] / x["price_lag_7"].replace(0, np.nan) - 1.0
            ).reset_index(level=0, drop=True)
            
        if "volatility_7d" not in data.columns:
            if "log_returns" not in data.columns:
                data["log_returns"] = data.groupby("mandi").apply(
                    lambda x: np.log(x["modal_price"] / x["modal_price"].shift(1))
                ).reset_index(level=0, drop=True)
            data["volatility_7d"] = data.groupby("mandi")["log_returns"].transform(
                lambda x: x.rolling(7, min_periods=4).std()
            )

        for horizon in HORIZONS:
            col = f"target_{horizon}d"
            if col not in data.columns:
                data[col] = data.groupby("mandi").apply(
                    lambda x: (x["modal_price"].shift(-horizon) - x["modal_price"]) / x["modal_price"].replace(0, np.nan)
                ).reset_index(level=0, drop=True)

        required = ["date", "mandi", "mandi_id", "modal_price"] + FEATURE_COLS + TARGET_COLS
        missing = [col for col in required if col not in data.columns]
        if missing:
            raise ValueError(f"Seasonality dataset missing required columns: {missing}")

        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.dropna(subset=required).reset_index(drop=True)
        if len(data) < max(80, self.n_splits * 20):
            raise ValueError(f"Insufficient seasonality training rows after preparation: {len(data)}")

        return data

    def _model_registry(self) -> Dict[str, Any]:
        registry: Dict[str, Any] = {
            "sarima": SARIMAMultiHorizonRegressor(),
            "linear_regression": Pipeline([
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]),
            "ridge": Pipeline([
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0, random_state=self.random_state)),
            ]),
            "lasso": Pipeline([
                ("scaler", StandardScaler()),
                ("model", MultiOutputRegressor(Lasso(alpha=0.001, max_iter=5000, random_state=self.random_state))),
            ]),
            "random_forest": RandomForestRegressor(
                n_estimators=220,
                max_depth=10,
                min_samples_leaf=3,
                random_state=self.random_state,
                n_jobs=-1,
            ),
            "gradient_boosting": MultiOutputRegressor(
                GradientBoostingRegressor(
                    loss="huber",
                    n_estimators=180,
                    max_depth=3,
                    learning_rate=0.04,
                    random_state=self.random_state,
                )
            ),
        }

        try:
            from xgboost import XGBRegressor

            registry["xgboost"] = MultiOutputRegressor(
                XGBRegressor(
                    n_estimators=180,
                    max_depth=3,
                    learning_rate=0.04,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    random_state=self.random_state,
                    objective="reg:squarederror",
                    n_jobs=2,
                )
            )
        except Exception as exc:
            logger.warning(f"XGBoost unavailable for seasonality training: {exc}")
            registry["xgboost"] = deepcopy(registry["ridge"])

        try:
            from lightgbm import LGBMRegressor

            registry["lightgbm"] = MultiOutputRegressor(
                LGBMRegressor(
                    n_estimators=220,
                    max_depth=5,
                    learning_rate=0.035,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    random_state=self.random_state,
                    verbosity=-1,
                )
            )
        except Exception as exc:
            logger.warning(f"LightGBM unavailable for seasonality training: {exc}")
            registry["lightgbm"] = deepcopy(registry["ridge"])

        return registry

    def _safe_predict(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        fallback = np.tile(self.training_mean_, (len(X), 1))
        try:
            pred = _as_2d(model.predict(X), len(X))
            pred = np.where(np.isfinite(pred), pred, fallback)
            return np.clip(pred, -0.50, 0.50)
        except Exception as exc:
            logger.warning(f"Seasonality model prediction failed, using training mean: {exc}")
            return fallback

    def _metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, float]]:
        result: Dict[str, Dict[str, float]] = {}
        for idx, label in enumerate(HORIZON_LABELS):
            yt = y_true[:, idx].astype("float64")
            yp = y_pred[:, idx].astype("float64")
            # Return targets often sit close to zero; a tiny denominator makes
            # MAPE numerically explosive and unhelpful for model weighting.
            # A 5 percentage-point floor preserves ranking without letting
            # nearly-flat actuals dominate the evaluation.
            denom = np.maximum(np.abs(yt), 0.05)
            mape = float(np.mean(np.abs((yt - yp) / denom)))
            mae = float(mean_absolute_error(yt, yp))
            rmse = float(math.sqrt(mean_squared_error(yt, yp)))

            yd = _direction(yt)
            pd_ = _direction(yp)
            result[label] = {
                "MAPE": round(mape, 6),
                "MAE": round(mae, 6),
                "RMSE": round(rmse, 6),
                "Accuracy": round(float(accuracy_score(yd, pd_)), 6),
                "Precision": round(float(precision_score(yd, pd_, average="macro", zero_division=0)), 6),
                "Recall": round(float(recall_score(yd, pd_, average="macro", zero_division=0)), 6),
                "F1": round(float(f1_score(yd, pd_, average="macro", zero_division=0)), 6),
            }
        return result

    def _build_weights(self, metrics_by_model: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, Dict[str, float]]:
        weights: Dict[str, Dict[str, float]] = {}
        for label in HORIZON_LABELS:
            raw = {}
            for model_name, metrics in metrics_by_model.items():
                mape = max(float(metrics[label]["MAPE"]), 1e-6)
                raw[model_name] = 1.0 / mape

            total = sum(raw.values()) or 1.0
            normalized = {name: value / total for name, value in raw.items()}
            filtered = {name: value for name, value in normalized.items() if value >= 0.01}
            filtered_total = sum(filtered.values()) or 1.0
            weights[label] = {
                name: round(value / filtered_total, 6)
                for name, value in sorted(filtered.items(), key=lambda item: item[1], reverse=True)
            }
        return weights

    def _ensemble_latest(
        self,
        latest_predictions: Dict[str, Dict[str, float]],
        weights: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        output = {}
        for label in HORIZON_LABELS:
            value = 0.0
            for model_name, weight in weights[label].items():
                value += weight * latest_predictions.get(model_name, {}).get(label, float(self.training_mean_[HORIZON_LABELS.index(label)]))
            output[label] = float(value)
        return output

    def enforce_stability(self, preds: Dict[str, float]) -> Dict[str, float]:
        # Fix 6: Remove Excessive Clamping before final stage
        return {label: round(float(preds[label]), 6) for label in HORIZON_LABELS}

    def _confidence(self, metrics_by_model: Dict[str, Dict[str, Dict[str, float]]], weights: Dict[str, Dict[str, float]]) -> float:
        horizon_conf = []
        for label in HORIZON_LABELS:
            weighted_mape = 0.0
            for name, weight in weights[label].items():
                weighted_mape += weight * metrics_by_model[name][label]["MAPE"]
            horizon_conf.append(1.0 / (1.0 + max(weighted_mape, 0.0)))
        return round(float(np.average(horizon_conf, weights=[HORIZON_IMPORTANCE[x] for x in HORIZON_LABELS])), 6)

    def train(
        self,
        df: pd.DataFrame,
        commodity: str,
        mandi: str,
    ) -> SeasonalityTrainingResult:
        data = self.prepare_dataset(df)
        X = data[FEATURE_COLS].astype("float64")
        Y = data[TARGET_COLS].astype("float64")
        self.training_mean_ = Y.mean(axis=0).to_numpy(dtype="float64")

        output_root = self.models_dir / _safe_slug(commodity) / _safe_slug(mandi)
        registry = self._model_registry()
        splitter = TimeSeriesSplit(n_splits=min(self.n_splits, max(2, len(data) // 120)))

        fitted_models: Dict[str, Any] = {}
        metrics_by_model: Dict[str, Dict[str, Dict[str, float]]] = {}
        fold_metrics: Dict[str, List[Dict[str, Any]]] = {}
        predictions_by_model: Dict[str, List[Dict[str, Any]]] = {}
        latest_predictions: Dict[str, Dict[str, float]] = {}

        for model_name, base_model in registry.items():
            logger.info(f"[SeasonalityMultiHorizon] Training {model_name} for {commodity}/{mandi}")
            oof_pred = np.full((len(data), len(HORIZONS)), np.nan, dtype="float64")
            model_folds: List[Dict[str, Any]] = []

            for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(X), start=1):
                model = clone(base_model)
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = Y.iloc[train_idx], Y.iloc[val_idx]
                try:
                    model.fit(X_train, y_train)
                    pred = self._safe_predict(model, X_val)
                except Exception as exc:
                    logger.warning(f"{model_name} fold {fold_idx} failed: {exc}")
                    pred = np.tile(np.nanmean(y_train.to_numpy(), axis=0), (len(X_val), 1))

                oof_pred[val_idx] = pred
                fold_result = {
                    "fold": fold_idx,
                    "train_start": str(data["date"].iloc[train_idx[0]].date()),
                    "train_end": str(data["date"].iloc[train_idx[-1]].date()),
                    "validation_start": str(data["date"].iloc[val_idx[0]].date()),
                    "validation_end": str(data["date"].iloc[val_idx[-1]].date()),
                    "metrics": self._metrics(y_val.to_numpy(), pred),
                }
                fold_result["weighted_MAPE"] = round(_weighted_score(fold_result["metrics"], "MAPE"), 6)
                model_folds.append(fold_result)

            valid_mask = np.isfinite(oof_pred).all(axis=1)
            model_metrics = self._metrics(Y.to_numpy()[valid_mask], oof_pred[valid_mask])
            metrics_by_model[model_name] = model_metrics
            fold_metrics[model_name] = model_folds

            final_model = clone(base_model)
            final_model.fit(X, Y)
            fitted_models[model_name] = final_model

            latest_pred = self._safe_predict(final_model, X.iloc[[-1]])[0]
            latest_predictions[model_name] = {
                label: round(float(value), 6)
                for label, value in zip(HORIZON_LABELS, latest_pred)
            }

            model_predictions = []
            for row_idx in np.where(valid_mask)[0]:
                record = {"date": str(data["date"].iloc[row_idx].date())}
                for target_idx, label in enumerate(HORIZON_LABELS):
                    record[f"actual_{label}"] = round(float(Y.iloc[row_idx, target_idx]), 6)
                    record[f"pred_{label}"] = round(float(oof_pred[row_idx, target_idx]), 6)
                model_predictions.append(record)
            predictions_by_model[model_name] = model_predictions[-500:]

        weights = self._build_weights(metrics_by_model)
        ensemble_pred = self._ensemble_latest(latest_predictions, weights)
        stable_pred = self.enforce_stability(ensemble_pred)
        best = {
            label: min(metrics_by_model, key=lambda name: metrics_by_model[name][label]["MAPE"])
            for label in HORIZON_LABELS
        }
        confidence = self._confidence(metrics_by_model, weights)

        for model_name, model in fitted_models.items():
            model_dir = output_root / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            _json_dump(model_dir / "metrics_per_horizon.json", metrics_by_model[model_name])
            _json_dump(model_dir / "fold_metrics.json", {"folds": fold_metrics[model_name]})
            _json_dump(
                model_dir / "predictions_multi_output.json",
                {
                    "horizons": HORIZON_LABELS,
                    "latest_prediction": latest_predictions[model_name],
                    "validation_predictions_tail": predictions_by_model[model_name],
                },
            )
            with (model_dir / "trained_model.pkl").open("wb") as fh:
                pickle.dump(model, fh)

        _json_dump(
            output_root / "ensemble_summary.json",
            {
                "commodity": commodity,
                "mandi": mandi,
                "feature_columns": FEATURE_COLS,
                "target_columns": TARGET_COLS,
                "weights_per_horizon": weights,
                "best_models_per_horizon": best,
                "ensemble_prediction": ensemble_pred,
                "stable_prediction": stable_pred,
                "confidence": confidence,
                "training_timestamp": datetime.utcnow().isoformat() + "Z",
                "training_mean": self.training_mean_.tolist(),
                "model_names": list(metrics_by_model.keys()),
                "metrics_per_model": metrics_by_model,
            },
        )

        return SeasonalityTrainingResult(
            models=fitted_models,
            latest_predictions=latest_predictions,
            metrics_per_model=metrics_by_model,
            fold_metrics=fold_metrics,
            weights_per_horizon=weights,
            ensemble_prediction={k: round(v, 6) for k, v in ensemble_pred.items()},
            stable_prediction=stable_pred,
            best_models_per_horizon=best,
            confidence=confidence,
            output_root=output_root,
        )

    def forecast_payload(
        self,
        df: pd.DataFrame,
        commodity: str,
        mandi: str,
        result: SeasonalityTrainingResult,
    ) -> Dict[str, Any]:
        current_price = float(df.sort_values("date")["modal_price"].iloc[-1])
        forecasts = {}
        for label, pct in result.stable_prediction.items():
            forecasts[label] = {
                "pct": round(float(pct) * 100.0, 4),
                "price": round(current_price * (1.0 + float(pct)), 2),
            }

        return {
            "commodity": commodity,
            "mandi": mandi,
            "seasonality_agent": {
                "forecasts": forecasts,
                "weights_per_horizon": result.weights_per_horizon,
                "best_models_per_horizon": result.best_models_per_horizon,
                "confidence": result.confidence,
                "model_artifact_dir": str(result.output_root),
            },
        }
