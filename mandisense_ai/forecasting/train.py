"""
Offline multi-horizon training.

Design decisions that matter more than the hyperparameters
----------------------------------------------------------

**Predict log-return, not price level.** The target for horizon *h* is
``log(price[t+h] / price[t])``, and the forecast is reconstructed as
``price[t] * exp(prediction)``. Three reasons:

1. *Scale-free.* Garlic trades near ₹7,000 and potato near ₹960. A single
   pooled model on raw levels spends its capacity learning which commodity it
   is looking at; on returns, every series is on the same scale.
2. *Honest evaluation.* A level model is rewarded for echoing yesterday's
   price — it can post a flattering 5% MAPE while carrying no information.
   On returns the naive forecast is exactly zero, so any skill the model
   reports is skill it actually has.
3. *Stationarity.* Levels drift and trend; returns do not, so a model fit on
   2016-2024 is still applicable in 2026.

**Direct multi-horizon.** One model per horizon, each mapping today's features
to the h-day-ahead return. The alternative — predicting one day ahead and
feeding the prediction back in — compounds its own error and produces
intervals that cannot be trusted past day two.

**Walk-forward validation with a baseline gate.** Folds move forward in time,
never shuffled, because shuffling a time series leaks the future into the
training set. A model is only promoted if it beats the naive
``price[t+h] = price[t]`` baseline by a real margin on held-out folds.
Anything that cannot clear that bar is not worth serving.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig, model_registry_dir
from mandisense_ai.forecasting.features import (
    build_features,
    feature_columns,
    is_target_column,
)
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

BUNDLE_VERSION = "1.1.0"

# Residual quantiles retained per horizon to build prediction intervals.
INTERVAL_QUANTILES = (0.05, 0.25, 0.75, 0.95)

# Features that exist only because the archive carried arrival volume. The live
# feed does not publish it, so these are the columns that will disappear at
# serve time and the ones dropout has to teach the model to live without.
ARRIVAL_FEATURES = (
    "arrivals",
    "arrivals_lag_1",
    "arrivals_lag_7",
    "arrivals_mean_7",
    "arrivals_dev",
    "price_arrival_elasticity",
)
ARRIVAL_PRESENCE_FLAG = "has_arrivals"


def _mask_arrivals(
    frame: pd.DataFrame,
    features: List[str],
    rows: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """
    Blank the arrival columns, as the live feed will.

    NaN rather than zero: XGBoost routes missing values down a learned default
    branch, whereas a zero reads as "volume collapsed to nothing", which is a
    strong and completely false signal.
    """
    masked = frame.copy()
    index = masked.index if rows is None else masked.index[rows]

    for column in ARRIVAL_FEATURES:
        if column in features and column in masked.columns:
            masked.loc[index, column] = np.nan
    if ARRIVAL_PRESENCE_FLAG in features and ARRIVAL_PRESENCE_FLAG in masked.columns:
        masked.loc[index, ARRIVAL_PRESENCE_FLAG] = 0

    return masked


def _apply_arrival_dropout(
    frame: pd.DataFrame,
    features: List[str],
    config: ForecastConfig,
    seed: int,
) -> pd.DataFrame:
    """Mask arrivals on a random share of training rows."""
    rate = float(getattr(config, "arrival_dropout_rate", 0.0) or 0.0)
    if rate <= 0.0 or frame.empty:
        return frame

    rng = np.random.default_rng(seed)
    selected = rng.random(len(frame)) < rate
    if not selected.any():
        return frame
    return _mask_arrivals(frame, features, rows=selected)


def _sample_weights(frame: pd.DataFrame, config: ForecastConfig) -> Optional[np.ndarray]:
    """Per-row fit weights taken from the ingest-time quality score."""
    if not getattr(config, "use_quality_weights", False):
        return None
    if "quality_score" not in frame.columns:
        return None

    weights = pd.to_numeric(frame["quality_score"], errors="coerce").fillna(1.0)
    return weights.clip(0.0, 1.0).to_numpy(dtype="float64")


def _make_estimator(config: ForecastConfig):
    """
    Build the estimator used for *both* cross-validation and the final fit.

    Kept in one place deliberately: if validation scores a different model
    than the one that ships, the reported skill describes something that was
    never deployed.
    """
    import xgboost as xgb

    return xgb.XGBRegressor(
        n_estimators=config.n_estimators,
        learning_rate=config.learning_rate,
        max_depth=config.max_depth,
        subsample=config.subsample,
        colsample_bytree=config.colsample_bytree,
        min_child_weight=config.min_child_weight,
        reg_lambda=config.reg_lambda,
        random_state=config.random_seed,
        objective="reg:squarederror",
        n_jobs=4,
    )


def _make_linear_estimator(config: ForecastConfig):
    """
    A second, structurally different model for the same target: linear
    rather than tree-based, so its errors are not correlated with the point
    model's in the way two different tunings of the same booster would be —
    which is what makes blending the two potentially reduce variance rather
    than just averaging two views of the same mistake.

    Imputation is not optional here the way it is for XGBoost. The booster
    routes a missing value down a learned default branch; a linear model has
    no such mechanism and `StandardScaler`/`ElasticNet` will raise on the
    first NaN they see — and this feature set has real NaNs by design
    (arrivals absent, no prior-year seasonal reference yet). Median
    imputation, then standardisation, then elastic-net regularisation: the
    same shrinkage discipline the point model's own hyperparameters apply,
    for the same reason — this project's returns are close to a random walk,
    and an unregularised fit of either family will fit the noise.
    """
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import ElasticNet
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", ElasticNet(
            alpha=0.01,
            l1_ratio=0.5,
            max_iter=5000,
            random_state=config.random_seed,
        )),
    ])


def _fit_model(model: Any, X: pd.DataFrame, y: pd.Series, weights: Optional[np.ndarray]) -> Any:
    """
    Fit either estimator family with the same sample weights.

    A bare `sample_weight=` kwarg is accepted by XGBoost's own `.fit()` but
    rejected outright by `sklearn.pipeline.Pipeline.fit()` — a `Pipeline`
    only forwards fit parameters that are explicitly step-prefixed
    (`model__sample_weight`). Silently swallowing that with a broad
    `except` would mean quality weighting quietly stopped applying to the
    linear model specifically; routing on type here keeps both paths correct
    and explicit instead.
    """
    from sklearn.pipeline import Pipeline

    if isinstance(model, Pipeline):
        if weights is not None:
            model.fit(X, y, model__sample_weight=weights)
        else:
            model.fit(X, y)
    else:
        model.fit(X, y, sample_weight=weights, verbose=False)
    return model


def _prepare_training_frame(
    observations: pd.DataFrame,
    config: ForecastConfig,
) -> Tuple[pd.DataFrame, List[str]]:
    """Build features, attach log-return targets and a commodity code."""
    frame = build_features(observations, config, with_targets=True)
    if frame.empty:
        return frame, []

    for horizon in config.horizons:
        target = pd.to_numeric(frame[f"target_h{horizon}"], errors="coerce")
        base = pd.to_numeric(frame["modal_price"], errors="coerce")
        valid = (target > 0) & (base > 0)
        frame[f"y_h{horizon}"] = np.where(valid, np.log(target / base), np.nan)

    # Pooled model needs to know which commodity a row belongs to; a stable
    # sorted code keeps the mapping reproducible across runs.
    commodities = sorted(frame["commodity"].unique())
    code_map = {name: index for index, name in enumerate(commodities)}
    frame["commodity_code"] = frame["commodity"].map(code_map)

    features = feature_columns(frame)
    if "commodity_code" not in features:
        features.append("commodity_code")

    # Hard guard against target leakage. A leaked target does not raise, it
    # just produces implausibly good validation scores, so the only reliable
    # defence is to assert the invariant at the boundary rather than trust the
    # column filter to have caught every naming variant.
    leaked = [name for name in features if is_target_column(name)]
    if leaked:
        raise ValueError(
            f"Target columns leaked into the feature set: {leaked}. "
            "Features must never contain a realised future value."
        )

    return frame, features


def _walk_forward_scores(
    frame: pd.DataFrame,
    features: List[str],
    horizon: int,
    config: ForecastConfig,
) -> Dict[str, Any]:
    """
    Expanding-window validation for one horizon.

    Returns model skill against the naive baseline plus the pooled residuals,
    which become the prediction intervals.

    Each fold is also scored a second time with arrival features masked on the
    validation rows (`skill_arrival_masked`), because the live feed will serve
    every future row that way. Reporting only the unmasked skill would state a
    number the deployed model can never actually achieve once the archive's
    arrival column runs out.
    """
    target_column = f"y_h{horizon}"
    usable = frame[frame[target_column].notna()].sort_values("date").reset_index(drop=True)

    if len(usable) < config.min_train_rows * 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "rows": int(len(usable)),
            "folds": 0,
        }

    dates = usable["date"]
    # Fold boundaries are time-based so each fold validates on a genuinely
    # later period than it trained on.
    quantile_edges = np.linspace(0.5, 1.0, config.walk_forward_folds + 1)
    cut_dates = [dates.quantile(q) for q in quantile_edges]

    fold_reports: List[Dict[str, Any]] = []
    residuals: List[np.ndarray] = []
    masked_maes: List[float] = []
    rows_excluded_low_quality = 0
    use_blend = bool(getattr(config, "use_model_blend", False))
    linear_maes: List[float] = []
    blend_maes: List[float] = []
    fold_blend_weights: List[float] = []

    for index in range(config.walk_forward_folds):
        train_end = cut_dates[index]
        valid_end = cut_dates[index + 1]

        train_mask = usable["date"] <= train_end
        valid_mask = (usable["date"] > train_end) & (usable["date"] <= valid_end)

        train_set = usable[train_mask]
        valid_set = usable[valid_mask]

        if len(train_set) < config.min_train_rows or len(valid_set) < 20:
            continue

        train_fit = train_set
        if "quality_score" in train_fit.columns and config.min_quality_for_training > 0:
            keep = train_fit["quality_score"] >= config.min_quality_for_training
            rows_excluded_low_quality += int((~keep).sum())
            train_fit = train_fit[keep]
            if len(train_fit) < config.min_train_rows:
                continue

        train_fit = _apply_arrival_dropout(
            train_fit, features, config, seed=config.random_seed + horizon * 100 + index
        )
        weights = _sample_weights(train_fit, config)

        model = _make_estimator(config)
        model.fit(train_fit[features], train_fit[target_column], sample_weight=weights, verbose=False)

        predicted = model.predict(valid_set[features])
        actual = valid_set[target_column].to_numpy()

        model_mae = float(np.mean(np.abs(actual - predicted)))
        # Naive forecast: price is unchanged over the horizon -> return of 0.
        baseline_mae = float(np.mean(np.abs(actual)))

        # Same fold, arrivals blanked on the validation rows — the condition
        # every served prediction will actually face.
        masked_valid = _mask_arrivals(valid_set, features)
        masked_predicted = model.predict(masked_valid[features])
        masked_mae = float(np.mean(np.abs(actual - masked_predicted)))
        masked_maes.append(masked_mae)

        residuals.append(actual - predicted)
        fold_report = {
            "fold": index + 1,
            "train_rows": int(len(train_fit)),
            "valid_rows": int(len(valid_set)),
            "train_end": str(pd.Timestamp(train_end).date()),
            "model_mae": round(model_mae, 6),
            "baseline_mae": round(baseline_mae, 6),
            "skill": round(1 - (model_mae / baseline_mae), 4) if baseline_mae > 0 else 0.0,
            "arrival_masked_mae": round(masked_mae, 6),
            "skill_arrival_masked": (
                round(1 - (masked_mae / baseline_mae), 4) if baseline_mae > 0 else 0.0
            ),
        }

        # Second, structurally different model on the identical fold split —
        # so any measured blend advantage is attributable to the models
        # actually making different kinds of errors, not to a more generous
        # slice of data.
        if use_blend:
            try:
                linear_model = _make_linear_estimator(config)
                _fit_model(linear_model, train_fit[features], train_fit[target_column], weights)
                linear_predicted = linear_model.predict(valid_set[features])
                linear_mae = float(np.mean(np.abs(actual - linear_predicted)))

                inv_xgb = 1.0 / (model_mae + 1e-9)
                inv_linear = 1.0 / (linear_mae + 1e-9)
                fold_w_xgb = inv_xgb / (inv_xgb + inv_linear)
                blended = fold_w_xgb * predicted + (1.0 - fold_w_xgb) * linear_predicted
                blend_mae = float(np.mean(np.abs(actual - blended)))

                linear_maes.append(linear_mae)
                blend_maes.append(blend_mae)
                fold_blend_weights.append(fold_w_xgb)

                fold_report["linear_mae"] = round(linear_mae, 6)
                fold_report["blend_mae"] = round(blend_mae, 6)
                fold_report["blend_weight_xgboost"] = round(fold_w_xgb, 4)
            except Exception as exc:
                logger.warning(
                    "Horizon %d fold %d: linear/blend evaluation failed: %s",
                    horizon, index + 1, exc,
                )

        fold_reports.append(fold_report)

    if not fold_reports:
        return {"status": "NO_VALID_FOLDS", "rows": int(len(usable)), "folds": 0}

    mean_model_mae = float(np.mean([f["model_mae"] for f in fold_reports]))
    mean_baseline_mae = float(np.mean([f["baseline_mae"] for f in fold_reports]))
    skill = 1 - (mean_model_mae / mean_baseline_mae) if mean_baseline_mae > 0 else 0.0

    mean_masked_mae = float(np.mean(masked_maes)) if masked_maes else None
    skill_arrival_masked = (
        1 - (mean_masked_mae / mean_baseline_mae)
        if mean_masked_mae is not None and mean_baseline_mae > 0
        else None
    )

    pooled = np.concatenate(residuals) if residuals else np.array([])
    quantiles = {
        str(q): float(np.quantile(pooled, q)) for q in INTERVAL_QUANTILES
    } if pooled.size else {}

    # Mean skill alone can be carried by one favourable fold, so promotion also
    # requires the win to repeat across folds.
    fold_wins = sum(1 for f in fold_reports if f["skill"] > 0)
    fold_win_rate = fold_wins / len(fold_reports)
    beats_baseline = (
        skill >= config.baseline_improvement_margin
        and fold_win_rate >= config.min_fold_win_rate
    )

    result: Dict[str, Any] = {
        "status": "OK",
        "rows": int(len(usable)),
        "folds": len(fold_reports),
        "fold_reports": fold_reports,
        "model_mae": round(mean_model_mae, 6),
        "baseline_mae": round(mean_baseline_mae, 6),
        "skill": round(float(skill), 4),
        "skill_arrival_masked": (
            round(float(skill_arrival_masked), 4) if skill_arrival_masked is not None else None
        ),
        "fold_win_rate": round(float(fold_win_rate), 3),
        "beats_baseline": bool(beats_baseline),
        "residual_quantiles": quantiles,
        "residual_std": float(np.std(pooled)) if pooled.size else None,
        "rows_excluded_low_quality": int(rows_excluded_low_quality),
        "arrival_dropout_rate": float(config.arrival_dropout_rate),
    }

    if blend_maes:
        mean_linear_mae = float(np.mean(linear_maes))
        mean_blend_mae = float(np.mean(blend_maes))
        # Same relative-improvement shape as `beats_baseline` above: a mean
        # improvement over the single point model, repeated across most
        # folds rather than carried by one — the bar a blend must clear is
        # smaller (`blend_improvement_margin` vs `baseline_improvement_margin`)
        # because beating an already-validated model is inherently harder
        # than beating a naive one.
        blend_vs_single_skill = (
            1 - (mean_blend_mae / mean_model_mae) if mean_model_mae > 0 else 0.0
        )
        blend_fold_wins = sum(
            1 for f in fold_reports
            if "blend_mae" in f and f["blend_mae"] < f["model_mae"]
        )
        blend_fold_win_rate = blend_fold_wins / len(blend_maes)
        blend_beats_single = (
            blend_vs_single_skill >= config.blend_improvement_margin
            and blend_fold_win_rate >= config.min_fold_win_rate
        )

        result.update({
            "linear_mae": round(mean_linear_mae, 6),
            "blend_mae": round(mean_blend_mae, 6),
            "blend_vs_single_skill": round(float(blend_vs_single_skill), 4),
            "blend_fold_win_rate": round(float(blend_fold_win_rate), 3),
            "blend_weight_xgboost": round(float(np.mean(fold_blend_weights)), 4),
            "blend_beats_single": bool(blend_beats_single),
        })

    return result


@dataclass
class HorizonModel:
    horizon: int
    model: Any
    validation: Dict[str, Any]
    promoted: bool


@dataclass
class ForecastBundle:
    """Trained artifact for all horizons plus the metadata to audit it."""

    models: Dict[int, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    commodity_codes: Dict[str, int] = field(default_factory=dict)
    validation: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    promoted_horizons: List[int] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    trained_at: str = ""
    version: str = BUNDLE_VERSION
    training_rows: int = 0
    training_span: Dict[str, str] = field(default_factory=dict)
    feature_importance: Dict[int, Dict[str, float]] = field(default_factory=dict)
    """Top drivers per horizon. Recorded so a retrain that suddenly leans on a
    different feature is visible in a diff rather than discovered later as
    unexplained drift."""
    backtest: Dict[str, Any] = field(default_factory=dict)
    """Out-of-sample interval calibration, attached at build time so a
    published band can always be traced to a measured coverage figure."""
    lineage_hash: str = ""
    """Content hash of the exact observation set this bundle was fit on (see
    `ObservationStore.lineage_hash`). Lets any published forecast be traced
    back to a byte-identical input rather than to "the data as it was that
    night", which nobody can reproduce after the fact."""
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    absence_summary: Dict[str, Any] = field(default_factory=dict)
    seasonal_climatology_table: Dict[Tuple[str, str, int], Dict[str, float]] = field(default_factory=dict)
    """The freshest seasonal-norm snapshot (see `seasonal.build_climatology_table`),
    persisted as a model artifact rather than an audit note because serving
    reads it on every forecast: `latest_feature_rows` only loads a small
    trailing window per series, nowhere near enough to see a prior year, so
    this table is the only way a served row gets a genuine multi-year
    seasonal reference."""
    quantile_models: Dict[int, Any] = field(default_factory=dict)
    """Per-horizon multi-quantile regressor (see `quantile.py`), predicting a
    row-conditional prediction interval directly from that row's own features
    rather than adding a fold-fixed offset to the point forecast."""
    quantile_backtest: Dict[str, Any] = field(default_factory=dict)
    """Out-of-sample calibration of the row-conditional band, measured on the
    identical walk-forward folds `backtest` uses so the two are comparable."""
    quantile_promoted_horizons: List[int] = field(default_factory=list)
    """Horizons where the row-conditional band's out-of-sample coverage
    actually calibrates. `batch_predict` only serves it here; elsewhere it
    falls back to the pooled-residual band that `backtest` already validates,
    so a novel interval method is never served ahead of a working one on
    faith alone."""
    blend_models: Dict[int, Any] = field(default_factory=dict)
    """Per-horizon regularised-linear model, fit alongside the point model —
    present only where `_walk_forward_scores` measured an inverse-error blend
    of the two beating the point model alone, out of sample. A horizon's
    presence in this dict *is* its promotion state; there is no separate
    'promoted' list to drift out of sync with it."""
    blend_weights: Dict[int, Dict[str, float]] = field(default_factory=dict)
    """Per-horizon `{"xgboost": w, "linear": 1-w}`, averaged from each fold's
    own held-out inverse-MAE weighting — never a hand-picked constant."""
    decision_backtest: Dict[str, Any] = field(default_factory=dict)
    """Out-of-sample precision of the SELL/HOLD/WAIT policy at every
    candidate threshold, per horizon (see `decision.py`). Kept in full,
    not just the chosen threshold, so a reviewer can see exactly what was
    rejected and why."""
    decision_thresholds: Dict[int, float] = field(default_factory=dict)
    """Per-horizon decision threshold, present only where its measured
    combined precision (SELL and HOLD calls together) cleared
    `decision.MIN_ACCEPTABLE_PRECISION` on held-out folds. A horizon's
    absence here means the honest answer was 'no threshold earned the right
    to make a confident call' — `batch_predict` reports WAIT for every row
    at that horizon rather than serve an unvalidated one."""

    def metadata(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "trained_at": self.trained_at,
            "training_rows": self.training_rows,
            "training_span": self.training_span,
            "features": self.features,
            "commodity_codes": self.commodity_codes,
            "promoted_horizons": self.promoted_horizons,
            "validation": {str(k): v for k, v in self.validation.items()},
            "feature_importance": {str(k): v for k, v in self.feature_importance.items()},
            "backtest": self.backtest,
            "config": self.config,
            "lineage_hash": self.lineage_hash,
            "quality_summary": self.quality_summary,
            "absence_summary": self.absence_summary,
            # The table itself lives in bundle.pkl (it's read at serve time,
            # not just for audit); metadata.json keeps only its size so a
            # human skimming the run record can see it was actually built.
            "seasonal_climatology_table_size": len(self.seasonal_climatology_table),
            "quantile_backtest": self.quantile_backtest,
            "quantile_promoted_horizons": self.quantile_promoted_horizons,
            "blend_weights": {str(k): v for k, v in self.blend_weights.items()},
            "blend_promoted_horizons": sorted(self.blend_models.keys()),
            "decision_backtest": self.decision_backtest,
            "decision_thresholds": {str(k): v for k, v in self.decision_thresholds.items()},
        }

    def save(self, directory: Optional[Path] = None) -> Path:
        import joblib
        from mandisense_ai.forecasting.seasonal import table_to_json

        target = Path(directory) if directory else model_registry_dir()
        target.mkdir(parents=True, exist_ok=True)

        joblib.dump(
            {
                "models": self.models,
                "quantile_models": self.quantile_models,
                "blend_models": self.blend_models,
                "blend_weights": self.blend_weights,
                "seasonal_climatology_table": table_to_json(self.seasonal_climatology_table),
                "features": self.features,
                "commodity_codes": self.commodity_codes,
                "promoted_horizons": self.promoted_horizons,
                "quantile_promoted_horizons": self.quantile_promoted_horizons,
                "decision_thresholds": self.decision_thresholds,
                "version": self.version,
            },
            target / "bundle.pkl",
        )
        (target / "metadata.json").write_text(
            json.dumps(self.metadata(), indent=2, default=str), encoding="utf-8"
        )
        logger.info("Forecast bundle saved to %s", target)
        return target

    @staticmethod
    def load(directory: Optional[Path] = None) -> "ForecastBundle":
        import joblib
        from mandisense_ai.forecasting.seasonal import table_from_json

        target = Path(directory) if directory else model_registry_dir()
        payload = joblib.load(target / "bundle.pkl")
        metadata: Dict[str, Any] = {}
        metadata_path = target / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        return ForecastBundle(
            models=payload["models"],
            quantile_models=payload.get("quantile_models", {}),
            blend_models=payload.get("blend_models", {}),
            blend_weights=payload.get("blend_weights", {}),
            features=payload["features"],
            commodity_codes=payload.get("commodity_codes", {}),
            promoted_horizons=payload.get("promoted_horizons", []),
            quantile_promoted_horizons=payload.get("quantile_promoted_horizons", []),
            decision_thresholds={
                int(k): v for k, v in (payload.get("decision_thresholds") or {}).items()
            },
            validation={int(k): v for k, v in (metadata.get("validation") or {}).items()},
            config=metadata.get("config", {}),
            trained_at=metadata.get("trained_at", ""),
            version=payload.get("version", BUNDLE_VERSION),
            training_rows=metadata.get("training_rows", 0),
            training_span=metadata.get("training_span", {}),
            feature_importance={
                int(k): v for k, v in (metadata.get("feature_importance") or {}).items()
            },
            backtest=metadata.get("backtest", {}),
            lineage_hash=metadata.get("lineage_hash", ""),
            quality_summary=metadata.get("quality_summary", {}),
            absence_summary=metadata.get("absence_summary", {}),
            seasonal_climatology_table=table_from_json(payload.get("seasonal_climatology_table")),
            quantile_backtest=metadata.get("quantile_backtest", {}),
            decision_backtest=metadata.get("decision_backtest", {}),
        )


def train_bundle(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
    prepared: Optional[Tuple[pd.DataFrame, List[str]]] = None,
) -> ForecastBundle:
    """
    Train one model per horizon and return the bundle.

    Horizons that fail the baseline gate are still fitted and recorded, but are
    left out of `promoted_horizons` so batch inference will not serve them.
    Failing loudly in the metadata is more useful than silently shipping a
    model with no skill.

    `prepared`: an already-built `(frame, features)` pair, for callers that
    also need the point-model backtest and the quantile backtest in the same
    run. Building it is a full feature pass over the archive (absence
    classification, seasonal climatology, ~14s measured on this project's
    data) — cheap once, wasteful paid three times over for what is otherwise
    identical work. Left as an internal call when omitted, so every existing
    caller and test is unaffected.
    """
    frame, features = prepared if prepared is not None else _prepare_training_frame(observations, config)
    if frame.empty:
        raise ValueError("No usable observations for training")

    code_map = (
        frame[["commodity", "commodity_code"]]
        .drop_duplicates()
        .set_index("commodity")["commodity_code"]
        .to_dict()
    )

    quality_summary: Dict[str, Any] = {}
    if "quality_score" in observations.columns:
        scores = pd.to_numeric(observations["quality_score"], errors="coerce").dropna()
        if not scores.empty:
            quality_summary = {
                "mean": round(float(scores.mean()), 4),
                "p05": round(float(scores.quantile(0.05)), 4),
                "min": round(float(scores.min()), 4),
                "below_training_threshold": int(
                    (scores < config.min_quality_for_training).sum()
                ),
            }

    absence_summary: Dict[str, Any] = {}
    for column in ("no_trade_30", "mandi_silent_30"):
        if column in frame.columns:
            absence_summary[f"{column}_mean"] = round(float(frame[column].mean()), 4)
    if "report_rate_90" in frame.columns:
        absence_summary["report_rate_90_mean"] = round(float(frame["report_rate_90"].mean()), 4)

    try:
        from mandisense_ai.forecasting.store import ObservationStore

        lineage = ObservationStore().lineage_hash(observations)
    except Exception as exc:
        logger.warning("Lineage hash unavailable: %s", exc)
        lineage = ""

    climatology_table: Dict[Any, Any] = {}
    if getattr(config, "use_seasonal_climatology", False):
        try:
            from mandisense_ai.forecasting.seasonal import build_climatology_table

            climatology_table = build_climatology_table(observations, config)
        except Exception as exc:
            logger.warning("Seasonal climatology table unavailable: %s", exc)

    bundle = ForecastBundle(
        features=features,
        commodity_codes={k: int(v) for k, v in code_map.items()},
        config=config.as_dict(),
        seasonal_climatology_table=climatology_table,
        trained_at=datetime.now(timezone.utc).isoformat(),
        training_rows=int(len(frame)),
        training_span={
            "start": str(frame["date"].min().date()),
            "end": str(frame["date"].max().date()),
        },
        lineage_hash=lineage,
        quality_summary=quality_summary,
        absence_summary=absence_summary,
    )

    for horizon in config.horizons:
        logger.info("Training horizon h=%d…", horizon)
        validation = _walk_forward_scores(frame, features, horizon, config)
        bundle.validation[horizon] = validation

        target_column = f"y_h{horizon}"
        usable = frame[frame[target_column].notna()]
        if len(usable) < config.min_train_rows:
            logger.warning("Horizon %d: not enough rows to fit (%d)", horizon, len(usable))
            continue

        if "quality_score" in usable.columns and config.min_quality_for_training > 0:
            keep = usable["quality_score"] >= config.min_quality_for_training
            if keep.sum() >= config.min_train_rows:
                usable = usable[keep]
            else:
                logger.warning(
                    "Horizon %d: quality filter would leave only %d rows, fitting on all instead",
                    horizon, int(keep.sum()),
                )

        usable = _apply_arrival_dropout(
            usable, features, config, seed=config.random_seed + horizon
        )
        weights = _sample_weights(usable, config)

        model = _make_estimator(config)
        model.fit(usable[features], usable[target_column], sample_weight=weights, verbose=False)
        bundle.models[horizon] = model

        # Row-conditional quantile model, fit on the identical rows/weights the
        # point model just used — same quality filter, same arrival-dropout
        # exposure — so the two models see the same training distribution and
        # only differ in what they were asked to predict.
        try:
            from mandisense_ai.forecasting.quantile import _make_quantile_estimator

            quantile_model = _make_quantile_estimator(config)
            quantile_model.fit(
                usable[features], usable[target_column], sample_weight=weights, verbose=False
            )
            bundle.quantile_models[horizon] = quantile_model
        except Exception as exc:
            logger.warning("Horizon %d: quantile model training failed: %s", horizon, exc)

        # Second model for the blend, fit only where the walk-forward pass
        # above (`_walk_forward_scores`, computed as `validation` a few lines
        # up) actually measured the blend beating the single point model out
        # of sample. Fitting the final linear model when it was never going
        # to be served would be wasted work; the honest check happens once,
        # on held-out folds, not by fitting first and hoping.
        if validation.get("blend_beats_single"):
            try:
                linear_model = _make_linear_estimator(config)
                _fit_model(linear_model, usable[features], usable[target_column], weights)
                bundle.blend_models[horizon] = linear_model
                bundle.blend_weights[horizon] = {
                    "xgboost": validation["blend_weight_xgboost"],
                    "linear": round(1.0 - validation["blend_weight_xgboost"], 4),
                }
                logger.info(
                    "Horizon %d: blend PROMOTED (blend_vs_single_skill=%.4f, "
                    "w_xgboost=%.3f)",
                    horizon, validation.get("blend_vs_single_skill", 0.0),
                    validation["blend_weight_xgboost"],
                )
            except Exception as exc:
                logger.warning("Horizon %d: blend model training failed: %s", horizon, exc)

        ranked = sorted(
            zip(features, model.feature_importances_), key=lambda pair: -pair[1]
        )
        bundle.feature_importance[horizon] = {
            name: round(float(score), 5) for name, score in ranked[:12]
        }

        promote = (not config.require_beat_baseline) or bool(validation.get("beats_baseline"))
        if promote:
            bundle.promoted_horizons.append(horizon)
            logger.info(
                "Horizon %d PROMOTED (skill=%.3f vs baseline)",
                horizon, validation.get("skill", 0.0),
            )
        else:
            logger.warning(
                "Horizon %d NOT promoted (skill=%.3f below margin %.3f)",
                horizon, validation.get("skill", 0.0), config.baseline_improvement_margin,
            )

    return bundle
