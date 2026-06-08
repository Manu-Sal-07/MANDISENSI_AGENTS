"""
Leak-proof multi-horizon Arrival Volume Agent training and forecasting.

The feature contract is strictly supply-response focused: arrival dynamics,
supply stress, price-response lags, elasticity, and festival/event context.
Every model predicts [3d, 5d, 7d, 15d, 30d] in one forward pass.
"""

from __future__ import annotations

import json
import math
import pickle
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

try:
    from mandisense_ai.config.settings import settings
except ImportError:
    from mandisense_ai.config.settings import settings
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


HORIZONS: List[int] = [3, 5, 7, 15, 30]
HORIZON_LABELS: List[str] = [f"{h}d" for h in HORIZONS]
TARGET_COLS: List[str] = [f"target_{h}d" for h in HORIZONS]
HORIZON_IMPORTANCE: Dict[str, float] = {
    "3d": 0.38,
    "5d": 0.27,
    "7d": 0.20,
    "15d": 0.10,
    "30d": 0.05,
}

FEATURE_COLS: List[str] = [
    "arrivals_lag_1",
    "arrivals_lag_7",
    "arrivals_7d_mean",
    "arrivals_30d_mean",
    "arrival_deviation_pct",
    "arrival_yoy_deviation_pct",
    "supply_momentum",
    "consecutive_decline_days",
    "price_lag_1",
    "price_lag_7",
    "log_price",
    "log_arrivals",
    "rolling_elasticity_30d",
    "is_festival",
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
    return float(sum(metrics[label][key] * HORIZON_IMPORTANCE[label] for label in HORIZON_LABELS))


class SimpleArrivalBaseline(BaseEstimator, RegressorMixin):
    """Mean/lag baseline that emits the full multi-horizon target vector."""

    def __init__(self, window: int = 30):
        self.window = window

    def fit(self, X: pd.DataFrame, y: pd.DataFrame) -> "SimpleArrivalBaseline":
        y_arr = np.asarray(y, dtype="float64")
        self.global_mean_ = np.nanmean(y_arr, axis=0)
        recent = y_arr[-self.window:] if len(y_arr) else y_arr
        self.recent_mean_ = np.nanmean(recent, axis=0)
        self.output_ = np.where(np.isfinite(self.recent_mean_), self.recent_mean_, self.global_mean_)
        self.output_ = np.where(np.isfinite(self.output_), self.output_, 0.0)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.tile(self.output_, (len(X), 1))


class ElasticityLinearMultiOutput(BaseEstimator, RegressorMixin):
    """
    Linear multi-output model with supply-response interpretation.

    It receives the same full feature matrix as all other models, but the
    linear coefficients remain inspectable, especially around
    rolling_elasticity_30d, log_arrivals, and arrival_deviation_pct.
    """

    def __init__(self):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ])

    def fit(self, X: pd.DataFrame, y: pd.DataFrame) -> "ElasticityLinearMultiOutput":
        self.feature_columns_ = list(X.columns)
        self.pipeline.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return _as_2d(self.pipeline.predict(X), len(X))


@dataclass
class ArrivalTrainingResult:
    models: Dict[str, Any]
    latest_predictions: Dict[str, Dict[str, float]]
    metrics_per_model: Dict[str, Dict[str, Dict[str, float]]]
    fold_metrics: Dict[str, List[Dict[str, Any]]]
    weights_per_horizon: Dict[str, Dict[str, float]]
    ensemble_prediction: Dict[str, float]
    stable_prediction: Dict[str, float]
    best_models_per_horizon: Dict[str, str]
    confidence: float
    supply_stress_score: float
    output_root: Path
    feature_columns: List[str] = field(default_factory=lambda: FEATURE_COLS.copy())
    target_columns: List[str] = field(default_factory=lambda: TARGET_COLS.copy())


class ArrivalMultiHorizonPipeline:
    """Train, evaluate, store, ensemble, and forecast arrival models."""

    def __init__(
        self,
        models_dir: Optional[str] = None,
        n_splits: int = 5,
        random_state: int = 42,
    ):
        self.models_dir = Path(models_dir or settings.paths.models_dir) / "arrival"
        self.n_splits = n_splits
        self.random_state = random_state
        self.training_mean_: Optional[np.ndarray] = None

    def prepare_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.sort_values("date").copy()
        data["date"] = pd.to_datetime(data["date"])

        if "is_festival" not in data.columns:
            data["is_festival"] = 0

        data["arrivals_7d_mean"] = data.get(
            "arrivals_7d_mean",
            data.get("arrivals_mean_7", data["arrivals_tonnes"].rolling(7, min_periods=4).mean()),
        )
        data["arrivals_30d_mean"] = data.get(
            "arrivals_30d_mean",
            data.get("arrivals_mean_30", data["arrivals_tonnes"].rolling(30, min_periods=15).mean()),
        )
        data["arrival_deviation_pct"] = data.get(
            "arrival_deviation_pct",
            (data["arrivals_tonnes"] - data["arrivals_30d_mean"]) / data["arrivals_30d_mean"].replace(0, np.nan),
        )

        if "arrival_yoy_deviation_pct" not in data.columns:
            if "arrivals_yoy_deviation" in data.columns:
                data["arrival_yoy_deviation_pct"] = data["arrivals_yoy_deviation"]
            else:
                yoy = data["arrivals_tonnes"].shift(365)
                data["arrival_yoy_deviation_pct"] = (data["arrivals_tonnes"] - yoy) / yoy.replace(0, np.nan)

        if "supply_momentum" not in data.columns:
            data["supply_momentum"] = data["arrivals_tonnes"].rolling(7, min_periods=4).apply(
                lambda x: float(np.polyfit(np.arange(len(x)), x, 1)[0]) if len(x) >= 2 else 0.0,
                raw=False,
            )

        if "consecutive_decline_days" not in data.columns:
            decline = (data["arrivals_tonnes"].diff() < 0).astype(int)
            data["consecutive_decline_days"] = decline * decline.groupby((decline == 0).cumsum()).cumsum()

        data["log_price"] = np.log(data["modal_price"].replace(0, np.nan))
        data["log_arrivals"] = np.log(data["arrivals_tonnes"].replace(0, np.nan))

        if "rolling_elasticity_30d" not in data.columns:
            if "rolling_elasticity" in data.columns:
                data["rolling_elasticity_30d"] = data["rolling_elasticity"]
            else:
                data["rolling_elasticity_30d"] = (
                    data["log_price"].rolling(30, min_periods=15).corr(data["log_arrivals"])
                )

        for lag in [1, 7]:
            if f"arrivals_lag_{lag}" not in data.columns:
                data[f"arrivals_lag_{lag}"] = data["arrivals_tonnes"].shift(lag)
            if f"price_lag_{lag}" not in data.columns:
                data[f"price_lag_{lag}"] = data["modal_price"].shift(lag)

        for horizon in HORIZONS:
            col = f"target_{horizon}d"
            if col not in data.columns:
                future = data["modal_price"].shift(-horizon)
                data[col] = (future - data["modal_price"]) / data["modal_price"].replace(0, np.nan)

        required = ["date", "modal_price", "arrivals_tonnes"] + FEATURE_COLS + TARGET_COLS
        missing = [col for col in required if col not in data.columns]
        if missing:
            raise ValueError(f"Arrival dataset missing required columns: {missing}")

        data = data.replace([np.inf, -np.inf], np.nan)
        data[["rolling_elasticity_30d"]] = data[["rolling_elasticity_30d"]].fillna(0.0)
        data = data.dropna(subset=required).reset_index(drop=True)
        if len(data) < max(80, self.n_splits * 20):
            raise ValueError(f"Insufficient arrival training rows after preparation: {len(data)}")
        return data

    def _model_registry(self) -> Dict[str, Any]:
        registry: Dict[str, Any] = {
            "elasticity_linear": ElasticityLinearMultiOutput(),
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
            "polynomial_regression": Pipeline([
                ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=2.0, random_state=self.random_state)),
            ]),
            "simple_baseline": SimpleArrivalBaseline(window=30),
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
            logger.warning(f"XGBoost unavailable for arrival training: {exc}")
            registry["xgboost"] = deepcopy(registry["ridge"])

        return {
            "xgboost": registry["xgboost"],
            "random_forest": registry["random_forest"],
            "elasticity_linear": registry["elasticity_linear"],
            "ridge": registry["ridge"],
            "lasso": registry["lasso"],
            "gradient_boosting": registry["gradient_boosting"],
            "polynomial_regression": registry["polynomial_regression"],
            "simple_baseline": registry["simple_baseline"],
        }

    def _safe_predict(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        fallback = np.tile(self.training_mean_, (len(X), 1))
        try:
            pred = _as_2d(model.predict(X), len(X))
            pred = np.where(np.isfinite(pred), pred, fallback)
            return np.clip(pred, -0.60, 0.60)
        except Exception as exc:
            logger.warning(f"Arrival model prediction failed, using training mean: {exc}")
            return fallback

    def _metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, float]]:
        result: Dict[str, Dict[str, float]] = {}
        for idx, label in enumerate(HORIZON_LABELS):
            yt = y_true[:, idx].astype("float64")
            yp = y_pred[:, idx].astype("float64")
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
            raw = {
                model_name: 1.0 / max(float(metrics[label]["MAPE"]), 1e-6)
                for model_name, metrics in metrics_by_model.items()
            }
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
        for idx, label in enumerate(HORIZON_LABELS):
            value = 0.0
            for model_name, weight in weights[label].items():
                value += weight * latest_predictions.get(model_name, {}).get(label, float(self.training_mean_[idx]))
            output[label] = float(value)
        return output

    def _supply_stress(self, row: pd.Series) -> float:
        deviation = abs(float(row.get("arrival_deviation_pct", 0.0)))
        yoy = abs(float(row.get("arrival_yoy_deviation_pct", 0.0)))
        momentum = abs(float(row.get("supply_momentum", 0.0))) / (abs(float(row.get("arrivals_30d_mean", 0.0))) + 1e-9)
        decline = min(float(row.get("consecutive_decline_days", 0.0)) / 30.0, 1.0)
        shock = 1.0 if deviation > 0.50 or yoy > 0.75 else 0.0
        return float(np.clip(0.35 * np.tanh(deviation) + 0.25 * np.tanh(yoy) + 0.20 * np.tanh(momentum) + 0.10 * decline + 0.10 * shock, 0.0, 1.0))

    def enforce_stability(self, preds: Dict[str, float], supply_stress_score: float) -> Dict[str, float]:
        values = np.array([preds[label] for label in HORIZON_LABELS], dtype="float64")
        values = np.nan_to_num(values, nan=0.0, posinf=0.20, neginf=-0.20)
        values = np.clip(values, -0.20, 0.20)

        # Arrival shocks are allowed to move 3-7d quickly, then decay.
        shock_boost = 1.0 + min(max(supply_stress_score, 0.0), 1.0) * 0.35
        values[:3] = np.clip(values[:3] * shock_boost, -0.20, 0.20)

        max_steps = np.array([0.055, 0.045, 0.065, 0.055], dtype="float64")
        for idx in range(1, len(values)):
            delta = values[idx] - values[idx - 1]
            values[idx] = values[idx - 1] + float(np.clip(delta, -max_steps[idx - 1], max_steps[idx - 1]))

        # Medium/long-term supply effects should decay toward neutral, not grow.
        if abs(values[3]) > abs(values[2]) and np.sign(values[3]) == np.sign(values[2]):
            values[3] = values[2] * 0.85
        if abs(values[4]) > abs(values[3]) and np.sign(values[4]) == np.sign(values[3]):
            values[4] = values[3] * 0.75

        for idx in range(1, len(values)):
            if values[idx - 1] * values[idx] < 0 and max(abs(values[idx - 1]), abs(values[idx])) > 0.025:
                values[idx] = 0.5 * values[idx - 1]

        values = np.clip(values, -0.20, 0.20)
        return {label: round(float(value), 6) for label, value in zip(HORIZON_LABELS, values)}

    def _confidence(self, metrics_by_model: Dict[str, Dict[str, Dict[str, float]]], weights: Dict[str, Dict[str, float]]) -> float:
        horizon_conf = []
        for label in HORIZON_LABELS:
            weighted_mape = sum(
                weight * metrics_by_model[name][label]["MAPE"]
                for name, weight in weights[label].items()
            )
            horizon_conf.append(1.0 / (1.0 + max(weighted_mape, 0.0)))
        return round(float(np.average(horizon_conf, weights=[HORIZON_IMPORTANCE[x] for x in HORIZON_LABELS])), 6)

    def train(self, df: pd.DataFrame, commodity: str, mandi: str) -> ArrivalTrainingResult:
        data = self.prepare_dataset(df)
        X = data[FEATURE_COLS].astype("float64")
        Y = data[TARGET_COLS].astype("float64")
        self.training_mean_ = Y.mean(axis=0).to_numpy(dtype="float64")

        output_root = self.models_dir / f"{_safe_slug(commodity)}_{_safe_slug(mandi)}"
        registry = self._model_registry()
        splitter = TimeSeriesSplit(n_splits=min(self.n_splits, max(2, len(data) // 120)))

        fitted_models: Dict[str, Any] = {}
        metrics_by_model: Dict[str, Dict[str, Dict[str, float]]] = {}
        fold_metrics: Dict[str, List[Dict[str, Any]]] = {}
        predictions_by_model: Dict[str, List[Dict[str, Any]]] = {}
        latest_predictions: Dict[str, Dict[str, float]] = {}

        for model_name, base_model in registry.items():
            logger.info(f"[ArrivalMultiHorizon] Training {model_name} for {commodity}/{mandi}")
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

            records = []
            for row_idx in np.where(valid_mask)[0]:
                record = {"date": str(data["date"].iloc[row_idx].date())}
                for target_idx, label in enumerate(HORIZON_LABELS):
                    record[f"actual_{label}"] = round(float(Y.iloc[row_idx, target_idx]), 6)
                    record[f"pred_{label}"] = round(float(oof_pred[row_idx, target_idx]), 6)
                records.append(record)
            predictions_by_model[model_name] = records[-500:]

        weights = self._build_weights(metrics_by_model)
        ensemble_pred = self._ensemble_latest(latest_predictions, weights)
        supply_stress_score = self._supply_stress(data.iloc[-1])
        stable_pred = self.enforce_stability(ensemble_pred, supply_stress_score=supply_stress_score)
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
                "supply_stress_score": supply_stress_score,
            },
        )

        return ArrivalTrainingResult(
            models=fitted_models,
            latest_predictions=latest_predictions,
            metrics_per_model=metrics_by_model,
            fold_metrics=fold_metrics,
            weights_per_horizon=weights,
            ensemble_prediction={k: round(v, 6) for k, v in ensemble_pred.items()},
            stable_prediction=stable_pred,
            best_models_per_horizon=best,
            confidence=confidence,
            supply_stress_score=round(supply_stress_score, 6),
            output_root=output_root,
        )

    def forecast_payload(
        self,
        df: pd.DataFrame,
        commodity: str,
        mandi: str,
        result: ArrivalTrainingResult,
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
            "arrival_agent": {
                "forecasts": forecasts,
                "weights_per_horizon": result.weights_per_horizon,
                "best_models_per_horizon": result.best_models_per_horizon,
                "confidence": result.confidence,
                "supply_stress_score": result.supply_stress_score,
                "model_artifact_dir": str(result.output_root),
            },
        }
