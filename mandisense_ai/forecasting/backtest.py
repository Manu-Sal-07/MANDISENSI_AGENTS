"""
End-to-end backtest and interval calibration.

Walk-forward cross-validation in `train.py` answers "is the model better than
naive". It does not answer the question a trader actually cares about: **when
this system says the 90% band is 600-900, is the price inside that band 90% of
the time?**

That question cannot be answered from the training residuals, because the
published quantiles are derived from those same residuals — measuring coverage
against them is circular and always flatters the model. So this module refits
the whole thing out of sample:

    for each fold:
        fit model on data strictly before the fold
        derive residual quantiles on data strictly before the fold
        predict the fold, and check how often reality landed inside the band

A band that contains the outcome far less than 90% of the time is overconfident
and will get someone hurt. One that contains it far more is so wide it says
nothing. Both are reported rather than tuned away, because the honest width of
a vegetable-price forecast is a finding, not a defect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.forecasting.train import _make_estimator, _prepare_training_frame
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Nominal coverage of each published band.
BAND_90 = ("0.05", "0.95", 0.90)
BAND_50 = ("0.25", "0.75", 0.50)

# A band whose realised coverage misses nominal by more than this is flagged,
# in either direction. Five percentage points rather than ten: against a 90%
# nominal a ten-point tolerance can never flag an over-wide band, since even
# 100% coverage would sit inside it — and a band that always contains the
# outcome is as useless as one that rarely does.
CALIBRATION_TOLERANCE = 0.05


@dataclass
class HorizonBacktest:
    horizon: int
    folds: int = 0
    predictions: int = 0
    mae: Optional[float] = None
    baseline_mae: Optional[float] = None
    skill: Optional[float] = None
    coverage_90: Optional[float] = None
    coverage_50: Optional[float] = None
    mean_band_width_pct: Optional[float] = None
    calibration: str = "UNKNOWN"
    fold_reports: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "horizon": self.horizon,
            "folds": self.folds,
            "predictions": self.predictions,
            "mae": self.mae,
            "baseline_mae": self.baseline_mae,
            "skill": self.skill,
            "coverage_90": self.coverage_90,
            "coverage_50": self.coverage_50,
            "mean_band_width_pct": self.mean_band_width_pct,
            "calibration": self.calibration,
            "fold_reports": self.fold_reports,
        }


def _classify_calibration(coverage: Optional[float], nominal: float) -> str:
    if coverage is None:
        return "UNKNOWN"
    delta = coverage - nominal
    if abs(delta) <= CALIBRATION_TOLERANCE:
        return "CALIBRATED"
    return "OVERCONFIDENT" if delta < 0 else "CONSERVATIVE"


def backtest_horizon(
    frame: pd.DataFrame,
    features: List[str],
    horizon: int,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> HorizonBacktest:
    """
    Out-of-sample backtest for one horizon.

    Both the model *and* the interval quantiles are fit on data strictly
    before each evaluation fold, so reported coverage is genuinely out of
    sample.
    """
    result = HorizonBacktest(horizon=horizon)

    target_column = f"y_h{horizon}"
    usable = frame[frame[target_column].notna()].sort_values("date").reset_index(drop=True)
    if len(usable) < config.min_train_rows * 2:
        return result

    dates = usable["date"]
    edges = np.linspace(0.5, 1.0, config.walk_forward_folds + 1)
    cuts = [dates.quantile(q) for q in edges]

    errors: List[np.ndarray] = []
    baseline_errors: List[np.ndarray] = []
    inside_90: List[np.ndarray] = []
    inside_50: List[np.ndarray] = []
    widths: List[np.ndarray] = []

    for index in range(config.walk_forward_folds):
        train_end, valid_end = cuts[index], cuts[index + 1]
        train_set = usable[usable["date"] <= train_end]
        valid_set = usable[(usable["date"] > train_end) & (usable["date"] <= valid_end)]

        if len(train_set) < config.min_train_rows or len(valid_set) < 20:
            continue

        # Inner split: the tail of the training window derives the quantiles,
        # so the band is never fit on the rows it is later scored against.
        inner_cut = train_set["date"].quantile(0.8)
        inner_fit = train_set[train_set["date"] <= inner_cut]
        inner_cal = train_set[train_set["date"] > inner_cut]
        if len(inner_fit) < config.min_train_rows // 2 or len(inner_cal) < 20:
            inner_fit, inner_cal = train_set, train_set

        calibrator = _make_estimator(config)
        calibrator.fit(inner_fit[features], inner_fit[target_column], verbose=False)
        calibration_residuals = (
            inner_cal[target_column].to_numpy() - calibrator.predict(inner_cal[features])
        )
        q_low_90 = float(np.quantile(calibration_residuals, 0.05))
        q_high_90 = float(np.quantile(calibration_residuals, 0.95))
        q_low_50 = float(np.quantile(calibration_residuals, 0.25))
        q_high_50 = float(np.quantile(calibration_residuals, 0.75))

        model = _make_estimator(config)
        model.fit(train_set[features], train_set[target_column], verbose=False)

        predicted = model.predict(valid_set[features])
        actual = valid_set[target_column].to_numpy()

        errors.append(np.abs(actual - predicted))
        baseline_errors.append(np.abs(actual))

        # Bands live in log-return space; coverage is scale-free there and
        # identical to checking the reconstructed price band.
        lower_90, upper_90 = predicted + q_low_90, predicted + q_high_90
        lower_50, upper_50 = predicted + q_low_50, predicted + q_high_50
        inside_90.append((actual >= lower_90) & (actual <= upper_90))
        inside_50.append((actual >= lower_50) & (actual <= upper_50))
        widths.append(np.exp(upper_90) - np.exp(lower_90))

        result.fold_reports.append(
            {
                "fold": index + 1,
                "train_rows": int(len(train_set)),
                "valid_rows": int(len(valid_set)),
                "train_end": str(pd.Timestamp(train_end).date()),
                "mae": round(float(np.mean(errors[-1])), 6),
                "coverage_90": round(float(np.mean(inside_90[-1])), 4),
            }
        )

    if not errors:
        return result

    all_errors = np.concatenate(errors)
    all_baseline = np.concatenate(baseline_errors)

    result.folds = len(result.fold_reports)
    result.predictions = int(all_errors.size)
    result.mae = round(float(all_errors.mean()), 6)
    result.baseline_mae = round(float(all_baseline.mean()), 6)
    result.skill = (
        round(float(1 - all_errors.mean() / all_baseline.mean()), 4)
        if all_baseline.mean() > 0
        else None
    )
    result.coverage_90 = round(float(np.concatenate(inside_90).mean()), 4)
    result.coverage_50 = round(float(np.concatenate(inside_50).mean()), 4)
    result.mean_band_width_pct = round(float(np.concatenate(widths).mean() * 100), 2)
    result.calibration = _classify_calibration(result.coverage_90, BAND_90[2])

    return result


def run_backtest(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
    prepared: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Backtest every configured horizon and summarise calibration.

    Returns a report suitable for storing alongside the model bundle, so the
    published intervals can always be traced to a measured coverage figure.

    `prepared`: an already-built `(frame, features)` pair — see
    `train_bundle`'s docstring for why this exists. Omit to build it here,
    exactly as before.
    """
    frame, features = prepared if prepared is not None else _prepare_training_frame(observations, config)
    if frame.empty:
        raise ValueError("No usable observations for backtesting")

    horizons: Dict[str, Any] = {}
    for horizon in config.horizons:
        logger.info("Backtesting horizon h=%d…", horizon)
        horizons[str(horizon)] = backtest_horizon(frame, features, horizon, config).as_dict()

    miscalibrated = [
        h for h, r in horizons.items() if r.get("calibration") not in ("CALIBRATED", "UNKNOWN")
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(frame)),
        "nominal_coverage": {"band_90": BAND_90[2], "band_50": BAND_50[2]},
        "tolerance": CALIBRATION_TOLERANCE,
        "horizons": horizons,
        "miscalibrated_horizons": miscalibrated,
        "verdict": "CALIBRATED" if not miscalibrated else "REVIEW_INTERVALS",
        "note": (
            "Model and interval quantiles are both fit strictly before each "
            "evaluation fold, so coverage is out of sample rather than measured "
            "against the residuals the band was derived from."
        ),
    }
