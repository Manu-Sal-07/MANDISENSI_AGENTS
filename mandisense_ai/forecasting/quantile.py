"""
Row-conditional prediction intervals via native multi-quantile regression.

Every interval this system has published before this module shared one shape:
a point forecast from the pooled XGBoost regressor, plus a *fixed* half-width
taken from the quantiles of that model's own residuals on a held-out slice
(see `backtest.py`). That half-width is the same number for every row inside
a given fold — a calm week in Kolar tomato and a supply-shock week in the same
fold get an identical band width, because the width was never a function of
the row at all, only of the fold it happened to fall in. Measured directly:
`coverage_90` in the existing backtest swings from 0.75 to 0.98 across folds
on real archive data, which is exactly what a non-adaptive band produces —
too narrow whenever volatility is above the fold's average, too wide whenever
it is below.

This module trains a second model per horizon whose *objective* is the
quantile loss (`reg:quantileerror`, native since XGBoost 2.0) rather than
squared error, predicting several quantiles of the same log-return target
directly from the same feature row. The band width this produces is a
function of that row's own features — its own recent volatility, its own
seasonal deviation, its own supply-stress signal — not of which fold or which
month happened to contain it. `width_std_pct` in the backtest below is the
metric that makes this concrete: a flat band has essentially zero width
variance within a fold; a row-conditional one does not, and the difference is
the whole point of training it.

This does not replace the point model. The point forecast — and its
walk-forward, baseline-beating promotion gate — is untouched. This is an
additional, independently gated model: promoted only if its own out-of-sample
coverage calibrates at least as well as the existing pooled-residual band, so
a novel method is never served over a working one on faith. Falling short of
that bar falls back to the proven approach rather than degrading it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Same four bands the rest of the system already publishes and calibrates
# against, so a comparison between the two approaches is apples-to-apples.
QUANTILE_LEVELS: Tuple[float, ...] = (0.05, 0.25, 0.75, 0.95)
BAND_90 = ("0.05", "0.95", 0.90)
BAND_50 = ("0.25", "0.75", 0.50)
CALIBRATION_TOLERANCE = 0.05


def _make_quantile_estimator(config: ForecastConfig, levels: Sequence[float] = QUANTILE_LEVELS):
    """
    One model, several quantiles, predicted together in a single call.

    Same regularisation discipline as the point model (`train._make_estimator`)
    and for the same reason: daily spot returns are close to a random walk, and
    an unregularised booster fits noise regardless of which loss it minimises.
    """
    import xgboost as xgb

    return xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=np.asarray(levels, dtype="float64"),
        n_estimators=config.n_estimators,
        learning_rate=config.learning_rate,
        max_depth=config.max_depth,
        subsample=config.subsample,
        colsample_bytree=config.colsample_bytree,
        min_child_weight=config.min_child_weight,
        reg_lambda=config.reg_lambda,
        random_state=config.random_seed,
        n_jobs=4,
    )


def predict_quantiles(
    model: Any,
    X: pd.DataFrame,
    levels: Sequence[float] = QUANTILE_LEVELS,
) -> Dict[str, np.ndarray]:
    """
    Predict every configured quantile for each row.

    Enforces non-crossing defensively: a multi-quantile fit is *usually*
    monotone by construction, but "usually" is not a guarantee worth serving
    on, particularly on thin per-series slices. Sorting each row's predicted
    quantiles is a one-line insurance policy against a p25 that lands above
    its own p75.
    """
    raw = model.predict(X)
    raw = np.atleast_2d(raw)
    if raw.shape[0] != len(X) and raw.shape[1] == len(X):
        raw = raw.T
    sorted_values = np.sort(raw, axis=1)
    return {
        f"{level:g}": sorted_values[:, index]
        for index, level in enumerate(levels)
    }


def _classify_calibration(coverage: Optional[float], nominal: float) -> str:
    if coverage is None:
        return "UNKNOWN"
    delta = coverage - nominal
    if abs(delta) <= CALIBRATION_TOLERANCE:
        return "CALIBRATED"
    return "OVERCONFIDENT" if delta < 0 else "CONSERVATIVE"


@dataclass
class QuantileBacktest:
    """Out-of-sample calibration of the row-conditional band, one horizon."""

    horizon: int
    folds: int = 0
    predictions: int = 0
    coverage_90: Optional[float] = None
    coverage_50: Optional[float] = None
    mean_band_width_pct: Optional[float] = None
    width_std_pct: Optional[float] = None
    """Standard deviation of band width *within* each fold, averaged across
    folds. This is the number that distinguishes a row-conditional band from
    a flat one: a fixed-width band scores ~0 here by construction, because
    every row in a fold shares the same offset from the point prediction."""
    calibration: str = "UNKNOWN"
    fold_reports: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "horizon": self.horizon,
            "folds": self.folds,
            "predictions": self.predictions,
            "coverage_90": self.coverage_90,
            "coverage_50": self.coverage_50,
            "mean_band_width_pct": self.mean_band_width_pct,
            "width_std_pct": self.width_std_pct,
            "calibration": self.calibration,
            "fold_reports": self.fold_reports,
        }


def backtest_quantile_horizon(
    frame: pd.DataFrame,
    features: List[str],
    horizon: int,
    config: ForecastConfig = DEFAULT_CONFIG,
    levels: Sequence[float] = QUANTILE_LEVELS,
) -> QuantileBacktest:
    """
    Out-of-sample coverage of the row-conditional band for one horizon.

    Uses the identical fold boundaries `backtest.backtest_horizon` uses (same
    expanding-window quantile cuts on the same date column), so the two
    reports describe the same evaluation periods and are directly comparable
    rather than each flattering itself on a different split.
    """
    result = QuantileBacktest(horizon=horizon)

    target_column = f"y_h{horizon}"
    usable = frame[frame[target_column].notna()].sort_values("date").reset_index(drop=True)
    if len(usable) < config.min_train_rows * 2:
        return result

    dates = usable["date"]
    edges = np.linspace(0.5, 1.0, config.walk_forward_folds + 1)
    cuts = [dates.quantile(q) for q in edges]

    inside_90: List[np.ndarray] = []
    inside_50: List[np.ndarray] = []
    widths: List[np.ndarray] = []
    fold_width_stds: List[float] = []

    for index in range(config.walk_forward_folds):
        train_end, valid_end = cuts[index], cuts[index + 1]
        train_set = usable[usable["date"] <= train_end]
        valid_set = usable[(usable["date"] > train_end) & (usable["date"] <= valid_end)]

        if len(train_set) < config.min_train_rows or len(valid_set) < 20:
            continue

        model = _make_quantile_estimator(config, levels)
        model.fit(train_set[features], train_set[target_column], verbose=False)

        predicted = predict_quantiles(model, valid_set[features], levels)
        actual = valid_set[target_column].to_numpy()

        lower_90, upper_90 = predicted[f"{levels[0]:g}"], predicted[f"{levels[-1]:g}"]
        lower_50, upper_50 = predicted[f"{levels[1]:g}"], predicted[f"{levels[2]:g}"]

        fold_inside_90 = (actual >= lower_90) & (actual <= upper_90)
        fold_inside_50 = (actual >= lower_50) & (actual <= upper_50)
        fold_width_pct = (np.exp(upper_90) - np.exp(lower_90)) * 100

        inside_90.append(fold_inside_90)
        inside_50.append(fold_inside_50)
        widths.append(fold_width_pct)
        fold_width_stds.append(float(np.std(fold_width_pct)))

        result.fold_reports.append(
            {
                "fold": index + 1,
                "train_rows": int(len(train_set)),
                "valid_rows": int(len(valid_set)),
                "train_end": str(pd.Timestamp(train_end).date()),
                "coverage_90": round(float(np.mean(fold_inside_90)), 4),
                "width_std_pct": round(float(fold_width_stds[-1]), 4),
            }
        )

    if not inside_90:
        return result

    result.folds = len(result.fold_reports)
    result.predictions = int(sum(len(arr) for arr in inside_90))
    result.coverage_90 = round(float(np.concatenate(inside_90).mean()), 4)
    result.coverage_50 = round(float(np.concatenate(inside_50).mean()), 4)
    result.mean_band_width_pct = round(float(np.concatenate(widths).mean()), 2)
    result.width_std_pct = round(float(np.mean(fold_width_stds)), 4)
    result.calibration = _classify_calibration(result.coverage_90, BAND_90[2])

    return result


def run_quantile_backtest(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
    levels: Sequence[float] = QUANTILE_LEVELS,
    prepared: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Backtest every configured horizon's row-conditional band.

    `prepared`: an already-built `(frame, features)` pair — see
    `train.train_bundle`'s docstring for why this exists. Omit to build it
    here, exactly as before.
    """
    from mandisense_ai.forecasting.train import _prepare_training_frame

    frame, features = prepared if prepared is not None else _prepare_training_frame(observations, config)
    if frame.empty:
        raise ValueError("No usable observations for quantile backtesting")

    horizons: Dict[str, Any] = {}
    for horizon in config.horizons:
        logger.info("Backtesting quantile band h=%d…", horizon)
        horizons[str(horizon)] = backtest_quantile_horizon(
            frame, features, horizon, config, levels
        ).as_dict()

    miscalibrated = [
        h for h, r in horizons.items() if r.get("calibration") not in ("CALIBRATED", "UNKNOWN")
    ]

    return {
        "nominal_coverage": {"band_90": BAND_90[2], "band_50": BAND_50[2]},
        "tolerance": CALIBRATION_TOLERANCE,
        "horizons": horizons,
        "miscalibrated_horizons": miscalibrated,
        "verdict": "CALIBRATED" if not miscalibrated else "REVIEW_INTERVALS",
    }


def train_quantile_models(
    frame: pd.DataFrame,
    features: List[str],
    config: ForecastConfig = DEFAULT_CONFIG,
    levels: Sequence[float] = QUANTILE_LEVELS,
) -> Dict[int, Any]:
    """Fit the final, full-data quantile model for every configured horizon."""
    models: Dict[int, Any] = {}
    for horizon in config.horizons:
        target_column = f"y_h{horizon}"
        usable = frame[frame[target_column].notna()]
        if len(usable) < config.min_train_rows:
            continue
        model = _make_quantile_estimator(config, levels)
        model.fit(usable[features], usable[target_column], verbose=False)
        models[horizon] = model
    return models


def quantile_price_interval(
    predicted_quantiles: Dict[str, float],
    base_price: float,
    levels: Sequence[float] = QUANTILE_LEVELS,
) -> Dict[str, Optional[float]]:
    """Convert one row's predicted log-return quantiles into a price interval."""
    values = [predicted_quantiles.get(f"{level:g}") for level in levels]
    if any(v is None for v in values):
        return {"p05": None, "p25": None, "p75": None, "p95": None}

    ordered = sorted(zip(levels, values))
    prices = [round(float(base_price * np.exp(v)), 2) for _, v in ordered]
    return {"p05": prices[0], "p25": prices[1], "p75": prices[2], "p95": prices[3]}
