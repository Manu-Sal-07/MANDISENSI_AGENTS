"""
Calibrated decision policy for published forecasts.

Every decision rule elsewhere in this codebase (`core/agents/decision_engine.py`'s
`MandiDecisionEngine`, `core/decision_engine.py`'s `generate_decision`) works
the same way: hand-picked thresholds on a point prediction — `dir_conf > 0.7`,
`abs_change > 0.05`, `risk_score < 0.3` — chosen because they looked
reasonable, never checked against what actually happened afterward. Checked
directly against this project's own per-mandi directional-accuracy table
(`mandisense_ai/models/*/v3/directional_accuracy.csv`), several mandis'
measured accuracy — 0.65 to 0.76 — never clears the 0.7 bar a SELL call
requires there. The threshold is not conservative for those series; it is
unreachable dead code, silently.

This module differs in two ways, both following the same discipline already
applied to intervals (`quantile.py`) and the point model itself (`train.py`'s
`beats_baseline` gate):

**Uses the calibrated distribution, not just the point forecast.** The
row-conditional quantile band already answers "how much could this specific
row's price plausibly move, and in which direction" — `implied_probability_of_decline`
reads that shape (has the band mostly cleared zero, or does it straddle it)
rather than discarding everything except the median.

**The threshold is measured, not invented.** `backtest_decision_policy` walks
the same expanding-window folds as `backtest.py` and `quantile.py`, replays
what the policy would have called using only information available at the
time, and reports the realised precision of SELL and HOLD calls at each
candidate threshold. A threshold is only published once its historical
precision has actually been checked. Where none clears even a modest bar
over a coin flip, the policy honestly returns WAIT for every row rather than
publish a confident-sounding call nobody validated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

DECISION_LEVELS: Tuple[float, ...] = (0.05, 0.25, 0.75, 0.95)

# Candidate probability-of-decline thresholds. Used symmetrically: a
# threshold of 0.65 means "call SELL when P(decline) >= 0.65" and "call HOLD
# when P(rise) >= 0.65" — the same bar in both directions, since neither
# call should be easier to earn than the other.
CANDIDATE_THRESHOLDS: Tuple[float, ...] = (0.55, 0.60, 0.65, 0.70, 0.75, 0.80)

# A threshold is only worth publishing if it beats a coin flip by a real
# margin. 0.55 is deliberately modest — this is a near-random-walk market
# where the point model itself only beats naive by ~18-21% MAE — but it is
# still a real, checked floor, not zero.
MIN_ACCEPTABLE_PRECISION = 0.55

# A threshold that only ever fires on a handful of rows can post a flattering
# precision by luck; require it to actually make a call often enough for
# that number to mean something.
MIN_ACCEPTABLE_COVERAGE = 0.05


def implied_probability_of_decline(
    q05: float, q25: float, q75: float, q95: float
) -> float:
    """
    Where zero return falls within the calibrated quantile band, as a
    probability of decline.

    Piecewise-linear interpolation across the four calibrated points, exactly
    the shape `quantile.py`'s own band already validated coverage for (0.90
    and 0.95 measured, not assumed) — this is the same distribution the
    published interval represents, just read as a probability rather than a
    price range. Extrapolated conservatively past the outer points: if even
    the 5th percentile return is positive, the implied decline probability is
    reported as slightly less than 0.05 rather than a confident zero, since
    the calibration was only ever measured *between* the 5th and 95th
    percentiles, not beyond them.
    """
    points = sorted([(0.05, q05), (0.25, q25), (0.75, q75), (0.95, q95)], key=lambda p: p[1])
    levels = [p[0] for p in points]
    values = [p[1] for p in points]

    if values[0] >= 0:
        return 0.03
    if values[-1] <= 0:
        return 0.97

    for i in range(len(values) - 1):
        lo, hi = values[i], values[i + 1]
        if lo <= 0 <= hi:
            if hi == lo:
                return float(levels[i])
            frac = (0.0 - lo) / (hi - lo)
            return float(levels[i] + frac * (levels[i + 1] - levels[i]))

    return 0.5  # unreachable given the sorted bracketing above; safe default


def decide(probability_of_decline: float, threshold: float) -> str:
    """SELL/HOLD/WAIT from a decline probability and a single symmetric bar."""
    if probability_of_decline >= threshold:
        return "SELL"
    if (1.0 - probability_of_decline) >= threshold:
        return "HOLD"
    return "WAIT"


@dataclass
class ThresholdEvaluation:
    threshold: float
    sell_calls: int = 0
    sell_correct: int = 0
    hold_calls: int = 0
    hold_correct: int = 0
    total_rows: int = 0

    @property
    def precision_sell(self) -> Optional[float]:
        return self.sell_correct / self.sell_calls if self.sell_calls else None

    @property
    def precision_hold(self) -> Optional[float]:
        return self.hold_correct / self.hold_calls if self.hold_calls else None

    @property
    def coverage(self) -> float:
        return (self.sell_calls + self.hold_calls) / self.total_rows if self.total_rows else 0.0

    @property
    def combined_precision(self) -> Optional[float]:
        correct = self.sell_correct + self.hold_correct
        calls = self.sell_calls + self.hold_calls
        return correct / calls if calls else None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "threshold": self.threshold,
            "sell_calls": self.sell_calls,
            "precision_sell": round(self.precision_sell, 4) if self.precision_sell is not None else None,
            "hold_calls": self.hold_calls,
            "precision_hold": round(self.precision_hold, 4) if self.precision_hold is not None else None,
            "combined_precision": round(self.combined_precision, 4) if self.combined_precision is not None else None,
            "coverage": round(self.coverage, 4),
        }


def backtest_decision_policy(
    frame: pd.DataFrame,
    features: List[str],
    horizon: int,
    config: ForecastConfig = DEFAULT_CONFIG,
    candidate_thresholds: Sequence[float] = CANDIDATE_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Out-of-sample precision of the decision policy at each candidate
    threshold, for one horizon.

    Same fold boundaries as `backtest.backtest_horizon` and
    `quantile.backtest_quantile_horizon`, so all three describe the same
    evaluation periods. Each fold fits both the point model and the quantile
    model fresh on data strictly before it, exactly as production training
    does, then reads the decline probability for every held-out row and
    checks it against what actually happened.
    """
    from mandisense_ai.forecasting.quantile import _make_quantile_estimator, predict_quantiles
    from mandisense_ai.forecasting.train import _make_estimator

    target_column = f"y_h{horizon}"
    usable = frame[frame[target_column].notna()].sort_values("date").reset_index(drop=True)

    result: Dict[str, Any] = {"horizon": horizon, "status": "INSUFFICIENT_DATA", "folds": 0}
    if len(usable) < config.min_train_rows * 2:
        return result

    dates = usable["date"]
    edges = np.linspace(0.5, 1.0, config.walk_forward_folds + 1)
    cuts = [dates.quantile(q) for q in edges]

    evaluations = {t: ThresholdEvaluation(threshold=t) for t in candidate_thresholds}
    folds_run = 0

    for index in range(config.walk_forward_folds):
        train_end, valid_end = cuts[index], cuts[index + 1]
        train_set = usable[usable["date"] <= train_end]
        valid_set = usable[(usable["date"] > train_end) & (usable["date"] <= valid_end)]

        if len(train_set) < config.min_train_rows or len(valid_set) < 20:
            continue

        try:
            quantile_model = _make_quantile_estimator(config)
            quantile_model.fit(train_set[features], train_set[target_column], verbose=False)
            predicted_quantiles = predict_quantiles(quantile_model, valid_set[features])
        except Exception as exc:
            logger.warning("Horizon %d fold %d: decision policy backtest failed: %s", horizon, index + 1, exc)
            continue

        actual = valid_set[target_column].to_numpy()
        q05, q25, q75, q95 = (
            predicted_quantiles["0.05"], predicted_quantiles["0.25"],
            predicted_quantiles["0.75"], predicted_quantiles["0.95"],
        )
        p_decline = np.array([
            implied_probability_of_decline(q05[i], q25[i], q75[i], q95[i])
            for i in range(len(actual))
        ])
        actual_declined = actual < 0

        folds_run += 1
        for threshold, evaluation in evaluations.items():
            evaluation.total_rows += len(actual)
            for i in range(len(actual)):
                call = decide(float(p_decline[i]), threshold)
                if call == "SELL":
                    evaluation.sell_calls += 1
                    if actual_declined[i]:
                        evaluation.sell_correct += 1
                elif call == "HOLD":
                    evaluation.hold_calls += 1
                    if not actual_declined[i]:
                        evaluation.hold_correct += 1

    if folds_run == 0:
        return result

    threshold_reports = [evaluations[t].as_dict() for t in candidate_thresholds]

    # Choose the most decisive (lowest) threshold that clears both the
    # precision and coverage floors — the least conservative policy that has
    # actually earned the right to make a confident call. If none clears the
    # bar, the honest answer is that no threshold here is worth serving.
    chosen = None
    for t in sorted(candidate_thresholds):
        evaluation = evaluations[t]
        precision = evaluation.combined_precision
        if (
            precision is not None
            and precision >= MIN_ACCEPTABLE_PRECISION
            and evaluation.coverage >= MIN_ACCEPTABLE_COVERAGE
        ):
            chosen = t
            break

    result.update({
        "status": "OK",
        "folds": folds_run,
        "thresholds": threshold_reports,
        "chosen_threshold": chosen,
        "verdict": "CALIBRATED" if chosen is not None else "NO_THRESHOLD_CLEARS_BAR",
    })
    return result


def run_decision_backtest(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
    prepared: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Backtest the decision policy for every configured horizon.

    `prepared`: an already-built `(frame, features)` pair — see
    `train.train_bundle`'s docstring for why this exists.
    """
    from mandisense_ai.forecasting.train import _prepare_training_frame

    frame, features = prepared if prepared is not None else _prepare_training_frame(observations, config)
    if frame.empty:
        raise ValueError("No usable observations for decision-policy backtesting")

    horizons: Dict[str, Any] = {}
    for horizon in config.horizons:
        logger.info("Backtesting decision policy h=%d…", horizon)
        horizons[str(horizon)] = backtest_decision_policy(frame, features, horizon, config)

    chosen_thresholds = {
        h: r.get("chosen_threshold") for h, r in horizons.items() if r.get("chosen_threshold") is not None
    }

    return {
        "horizons": horizons,
        "chosen_thresholds": chosen_thresholds,
        "verdict": "OK" if chosen_thresholds else "NO_HORIZON_CALIBRATED",
    }


def decide_for_row(
    interval: Dict[str, Optional[float]],
    base_price: float,
    threshold: float,
) -> Dict[str, Any]:
    """
    Decision for one already-computed price interval (as `batch_predict.py`
    produces it), given the threshold `run_decision_backtest` measured for
    this horizon.
    """
    p05, p25, p75, p95 = interval.get("p05"), interval.get("p25"), interval.get("p75"), interval.get("p95")
    if None in (p05, p25, p75, p95) or base_price <= 0:
        return {"decision": "WAIT", "probability_of_decline": None}

    # Prices, not returns -- convert back to log-return space so the
    # zero-crossing means "no change" regardless of the base price.
    q05 = float(np.log(p05 / base_price))
    q25 = float(np.log(p25 / base_price))
    q75 = float(np.log(p75 / base_price))
    q95 = float(np.log(p95 / base_price))

    p_decline = implied_probability_of_decline(q05, q25, q75, q95)
    return {
        "decision": decide(p_decline, threshold),
        "probability_of_decline": round(p_decline, 4),
    }
