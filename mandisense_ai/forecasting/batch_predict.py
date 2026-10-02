"""
Batch inference — the step that makes serving cheap.

Every (commodity, mandi, horizon) cell is scored once per night and written to
the forecast store. A request then costs a dictionary lookup instead of a
model load, a feature build and a prediction. That is the whole point of the
offline-inference design: the expensive work happens on a schedule, against a
known data snapshot, where it can be validated before anyone reads it.

Eligibility is enforced here rather than at request time. A series is only
forecast when it has enough history for its features to be meaningful and has
traded recently enough for those features to still describe the current market.
Series that fail either test are published with an explicit reason, so the API
can answer "not enough history for Hoskote yet" instead of inventing a number.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.forecasting.features import latest_feature_rows
from mandisense_ai.forecasting.store import ForecastStore
from mandisense_ai.forecasting.train import ForecastBundle
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

STATUS_OK = "OK"
STATUS_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
STATUS_DORMANT = "DORMANT"
STATUS_DISCONTINUOUS = "DISCONTINUOUS_HISTORY"
STATUS_REBUILDING = "REBUILDING_HISTORY"
"""A series that has resumed trading but has not yet accumulated enough
contiguous observations for its windowed features to describe the current
market. Distinct from DORMANT (not trading at all) and from
INSUFFICIENT_HISTORY (never traded enough): this market is open and printing
today, and the wait is finite and countable, which is what the reason string
reports."""
STATUS_NO_MODEL = "NO_PROMOTED_MODEL"


def _series_eligibility(
    history_rows: int,
    last_date: pd.Timestamp,
    as_of: pd.Timestamp,
    days_since_prev: Optional[float],
    config: ForecastConfig,
    segment_observations: Optional[int] = None,
) -> Dict[str, Any]:
    """Decide whether a series may be forecast, and say why if not."""
    gap_days = int((as_of - last_date).days)

    if history_rows < config.min_history_days:
        return {
            "eligible": False,
            "status": STATUS_INSUFFICIENT_HISTORY,
            "reason": (
                f"only {history_rows} observations on record; "
                f"{config.min_history_days} required before a forecast is published"
            ),
            "gap_days": gap_days,
        }

    if gap_days > config.max_observation_gap_days:
        return {
            "eligible": False,
            "status": STATUS_DORMANT,
            "reason": (
                f"last traded {gap_days} days ago; beyond the "
                f"{config.max_observation_gap_days}-day freshness window"
            ),
            "gap_days": gap_days,
        }

    # A series can be recent *and* long and still be unforecastable: if it has
    # only just resumed after a dormancy, it has almost no *contiguous* recent
    # history, and the windowed features that carry the signal are legitimately
    # missing (see `use_segment_aware_features`). The model can score such a
    # row -- it has seen the same pattern at every real series start -- but
    # with this little in-segment history it degenerates toward a
    # commodity-level average, which is not worth publishing as a
    # mandi-specific forecast.
    #
    # This replaces a test on `days_since_prev` alone, which refused the first
    # print after a break and then accepted the *second* one, at which point
    # `days_since_prev` is 1 while the 14-day lag and 30-day mean still
    # described the pre-break market.
    if segment_observations is not None and segment_observations < config.min_segment_observations:
        still_needed = config.min_segment_observations - segment_observations
        return {
            "eligible": False,
            "status": STATUS_REBUILDING,
            "reason": (
                f"only {segment_observations} observation(s) since trading "
                f"resumed; {still_needed} more needed before recent-history "
                "features describe the current market"
            ),
            "gap_days": gap_days,
            "segment_observations": segment_observations,
        }

    # Retained for configurations with segment-aware features switched off,
    # where nothing else prevents a window from spanning a break.
    if (
        segment_observations is None
        and days_since_prev is not None
        and days_since_prev > config.max_observation_gap_days
    ):
        return {
            "eligible": False,
            "status": STATUS_DISCONTINUOUS,
            "reason": (
                f"trading resumed after a {int(days_since_prev)}-day break; "
                "recent-history features are not yet meaningful for this series"
            ),
            "gap_days": gap_days,
        }

    return {"eligible": True, "status": STATUS_OK, "reason": None, "gap_days": gap_days}


def _interval_from_residuals(
    predicted_return: float,
    base_price: float,
    quantiles: Dict[str, float],
) -> Dict[str, Optional[float]]:
    """
    Convert stored residual quantiles into a price interval.

    Intervals are empirical: they come from how wrong this model actually was
    on held-out folds, not from a distributional assumption the data does not
    satisfy. Mandi returns are fat-tailed and skewed, so a symmetric
    ±1.96σ band would understate exactly the moves that matter.
    """
    if not quantiles:
        return {"p05": None, "p25": None, "p75": None, "p95": None}

    def price_at(q: str) -> Optional[float]:
        if q not in quantiles:
            return None
        return round(float(base_price * np.exp(predicted_return + quantiles[q])), 2)

    return {
        "p05": price_at("0.05"),
        "p25": price_at("0.25"),
        "p75": price_at("0.75"),
        "p95": price_at("0.95"),
    }


def build_readiness(
    observations: pd.DataFrame,
    as_of: pd.Timestamp,
    config: ForecastConfig,
) -> List[Dict[str, Any]]:
    """
    Per-series progress toward being forecastable.

    Because the upstream feed is a daily snapshot with no history endpoint, a
    newly seen mandi cannot be forecast until the nightly job has observed it
    enough times. That wait is a legitimate state, but an invisible one is
    indistinguishable from a broken pipeline — so it is measured and published:
    how many observations a series has, how many it still needs, and when it
    last traded.

    The verdict comes from `_series_eligibility` — the same function the
    forecast loop itself gates on — rather than being recomputed here. It was
    recomputed here, and the copy had drifted: it tested history length and
    freshness but not discontinuity, so a series whose archive ends in 2025
    and which printed once yesterday was reported READY while the forecaster
    refused it as DISCONTINUOUS_HISTORY. On the present store that is 16
    series whose operator-facing diagnostic says the opposite of what was
    published. A readiness report that disagrees with the gate it reports on
    is worse than no readiness report, because it sends the operator looking
    for a pipeline fault that does not exist.
    """
    if observations.empty:
        return []

    grouped = (
        observations.groupby(["commodity", "mandi_id"])["date"]
        .agg(rows="count", first="min", last="max")
        .reset_index()
    )

    # Gap between each series' last two prints — the input the discontinuity
    # test needs and the grouped aggregate above cannot supply.
    ordered = observations[["commodity", "mandi_id", "date"]].sort_values(
        ["commodity", "mandi_id", "date"]
    )
    ordered["previous_date"] = ordered.groupby(["commodity", "mandi_id"])["date"].shift(1)

    # Observations in each series' *current* continuity segment — the same
    # definition `_series_features` builds its windows on, so readiness and
    # the feature layer cannot disagree about when a resumed series is ready.
    ordered["break"] = (
        (ordered["date"] - ordered["previous_date"]).dt.days
        > config.max_observation_gap_days
    ).fillna(False)
    ordered["segment_id"] = ordered.groupby(["commodity", "mandi_id"])["break"].cumsum()
    segment_rows = (
        ordered.groupby(["commodity", "mandi_id", "segment_id"], as_index=False)
        .size()
        .groupby(["commodity", "mandi_id"], as_index=False)
        .last()
        .rename(columns={"size": "segment_observations"})[
            ["commodity", "mandi_id", "segment_observations"]
        ]
    )

    previous = ordered.groupby(["commodity", "mandi_id"], as_index=False).last()[
        ["commodity", "mandi_id", "previous_date"]
    ]
    grouped = grouped.merge(previous, on=["commodity", "mandi_id"], how="left")
    grouped = grouped.merge(segment_rows, on=["commodity", "mandi_id"], how="left")

    rows: List[Dict[str, Any]] = []
    for _, series in grouped.iterrows():
        history_rows = int(series["rows"])
        last_date = pd.Timestamp(series["last"])
        previous_date = series.get("previous_date")
        days_since_prev = (
            float((last_date - pd.Timestamp(previous_date)).days)
            if previous_date is not None and not pd.isna(previous_date)
            else None
        )

        segment_observations = series.get("segment_observations")
        segment_observations = (
            int(segment_observations)
            if segment_observations is not None and not pd.isna(segment_observations)
            else None
        )

        verdict = _series_eligibility(
            history_rows,
            last_date,
            as_of,
            days_since_prev,
            config,
            segment_observations=(
                segment_observations
                if getattr(config, "use_segment_aware_features", False)
                else None
            ),
        )

        rows.append(
            {
                "commodity": series["commodity"],
                "mandi_id": series["mandi_id"],
                "observations": history_rows,
                "observations_required": config.min_history_days,
                "observations_remaining": max(0, config.min_history_days - history_rows),
                "first_seen": str(pd.Timestamp(series["first"]).date()),
                "last_seen": str(last_date.date()),
                "days_since_last": verdict["gap_days"],
                "days_since_previous": days_since_prev,
                "segment_observations": segment_observations,
                "state": verdict["status"],
                "reason": verdict["reason"],
            }
        )

    return sorted(rows, key=lambda r: (-r["observations"], r["commodity"]))


def generate_forecasts(
    observations: pd.DataFrame,
    bundle: ForecastBundle,
    config: ForecastConfig = DEFAULT_CONFIG,
    as_of: Optional[pd.Timestamp] = None,
) -> ForecastStore:
    """
    Score every eligible series at every promoted horizon.

    Returns a populated :class:`ForecastStore`, not yet written to disk, so the
    caller can inspect or reject a run before publishing it.
    """
    if observations is None or observations.empty:
        raise ValueError("No observations available for batch inference")

    observations = observations.copy()
    observations["date"] = pd.to_datetime(observations["date"])
    as_of = pd.Timestamp(as_of) if as_of is not None else observations["date"].max()

    # Counts drive the history-eligibility test and must be computed on the
    # full store, not the trimmed inference window.
    history_counts = (
        observations.groupby(["commodity", "mandi_id"])["date"]
        .agg(rows="count", last="max")
        .reset_index()
    )

    feature_rows = latest_feature_rows(observations, config)
    if feature_rows.empty:
        raise ValueError("Feature construction produced no rows")

    # `latest_feature_rows` only loads a small trailing window per series
    # (see its own docstring on why), which is essentially never enough to
    # reach a prior calendar year — so its seasonal-deviation columns are
    # almost always NaN. The bundle's climatology table is the multi-year
    # answer computed once at training time; applying it here is an O(1)
    # lookup per row rather than a recomputation.
    if bundle.seasonal_climatology_table:
        try:
            from mandisense_ai.forecasting.seasonal import lookup_batch

            feature_rows = lookup_batch(feature_rows, bundle.seasonal_climatology_table, config)
        except Exception as exc:
            logger.warning("Seasonal climatology lookup failed, serving without it: %s", exc)

    promoted = sorted(bundle.promoted_horizons)
    if not promoted:
        logger.error("No promoted horizons in bundle — nothing can be served")

    rows: List[Dict[str, Any]] = []
    eligible_series = 0
    skipped_series = 0

    for _, feature_row in feature_rows.iterrows():
        commodity = feature_row["commodity"]
        mandi_id = feature_row["mandi_id"]

        stats = history_counts[
            (history_counts["commodity"] == commodity)
            & (history_counts["mandi_id"] == mandi_id)
        ]
        if stats.empty:
            continue

        history_rows = int(stats.iloc[0]["rows"])
        last_date = pd.Timestamp(stats.iloc[0]["last"])
        days_since_prev = feature_row.get("days_since_prev")
        days_since_prev = (
            float(days_since_prev) if pd.notna(days_since_prev) else None
        )
        # `segment_position` is 0-indexed, so the count of observations backing
        # this row's windowed features is one more than it.
        segment_position = feature_row.get("segment_position")
        segment_observations = (
            int(segment_position) + 1 if pd.notna(segment_position) else None
        )
        verdict = _series_eligibility(
            history_rows,
            last_date,
            as_of,
            days_since_prev,
            config,
            segment_observations=segment_observations,
        )

        base_price = float(feature_row["modal_price"])
        common = {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "as_of_date": str(last_date.date()),
            "last_observed_price": round(base_price, 2),
            "history_rows": history_rows,
            "data_lag_days": verdict["gap_days"],
            # How much *contiguous* recent history backs this forecast, as
            # distinct from how much history the series has in total. A
            # reopened mandi can have 2,600 observations and 12 that describe
            # the market it trades in today; publishing only `history_rows`
            # made those two situations indistinguishable downstream.
            "segment_observations": segment_observations,
        }

        if not verdict["eligible"]:
            skipped_series += 1
            rows.append({**common, "horizon_days": None, "status": verdict["status"],
                         "reason": verdict["reason"], "forecast_price": None})
            continue

        if not promoted:
            skipped_series += 1
            rows.append({**common, "horizon_days": None, "status": STATUS_NO_MODEL,
                         "reason": "no horizon passed the baseline gate at last training",
                         "forecast_price": None})
            continue

        eligible_series += 1

        # Model input must be column-aligned with training; any feature the
        # bundle expects but this row lacks is passed as NaN so XGBoost's
        # missing-value handling applies rather than a silent zero.
        design = pd.DataFrame([feature_row])
        for column in bundle.features:
            if column not in design.columns:
                design[column] = np.nan
        if "commodity_code" in bundle.features:
            design["commodity_code"] = bundle.commodity_codes.get(commodity, np.nan)
        design = design[bundle.features].apply(pd.to_numeric, errors="coerce")

        for horizon in promoted:
            model = bundle.models.get(horizon)
            if model is None:
                continue

            predicted_return = float(model.predict(design)[0])
            prediction_source = "xgboost"

            # Blend with the second model where the walk-forward measurement
            # actually showed it helping (a horizon's presence in
            # `blend_models` *is* its promotion state — see `train.py`).
            # Weights came from each fold's own held-out inverse-MAE, not a
            # hand-picked constant, and are re-used exactly as measured.
            blend_model = bundle.blend_models.get(horizon)
            if blend_model is not None and horizon in bundle.blend_weights:
                try:
                    linear_return = float(blend_model.predict(design)[0])
                    weights = bundle.blend_weights[horizon]
                    predicted_return = (
                        weights["xgboost"] * predicted_return
                        + weights["linear"] * linear_return
                    )
                    prediction_source = "xgboost_linear_blend"
                except Exception as exc:
                    logger.warning(
                        "Blend prediction failed for %s/%s h=%d, falling back "
                        "to the single point model: %s",
                        commodity, mandi_id, horizon, exc,
                    )

            forecast_price = float(base_price * np.exp(predicted_return))
            validation = bundle.validation.get(horizon, {})
            quantiles = validation.get("residual_quantiles", {})

            # Row-conditional band where it has earned that trust (measured,
            # out-of-sample, per horizon — see `quantile_promoted_horizons`);
            # the pooled-residual band otherwise. Never both, and never the
            # new one where it has not actually calibrated.
            interval_source = "pooled_residual"
            interval = _interval_from_residuals(predicted_return, base_price, quantiles)
            quantile_model = bundle.quantile_models.get(horizon)
            if horizon in bundle.quantile_promoted_horizons and quantile_model is not None:
                try:
                    from mandisense_ai.forecasting.quantile import (
                        predict_quantiles,
                        quantile_price_interval,
                    )

                    predicted = predict_quantiles(quantile_model, design)
                    row_quantiles = {level: float(values[0]) for level, values in predicted.items()}
                    interval = quantile_price_interval(row_quantiles, base_price)
                    interval_source = "row_conditional_quantile"
                except Exception as exc:
                    logger.warning(
                        "Quantile interval failed for %s/%s h=%d, falling back "
                        "to pooled-residual band: %s",
                        commodity, mandi_id, horizon, exc,
                    )

            # SELL/HOLD/WAIT from the same calibrated band, at the threshold
            # `decision.run_decision_backtest` measured to actually earn its
            # precision for this horizon. A horizon with no chosen threshold
            # (`decision_thresholds` has nothing for it) reports WAIT for
            # every row rather than an unvalidated confident call.
            decision = "WAIT"
            decision_probability_of_decline = None
            threshold = bundle.decision_thresholds.get(horizon)
            if threshold is not None:
                try:
                    from mandisense_ai.forecasting.decision import decide_for_row

                    outcome = decide_for_row(interval, base_price, threshold)
                    decision = outcome["decision"]
                    decision_probability_of_decline = outcome["probability_of_decline"]
                except Exception as exc:
                    logger.warning(
                        "Decision policy failed for %s/%s h=%d, defaulting to WAIT: %s",
                        commodity, mandi_id, horizon, exc,
                    )

            rows.append(
                {
                    **common,
                    "horizon_days": int(horizon),
                    "target_date": str((last_date + pd.Timedelta(days=horizon)).date()),
                    "status": STATUS_OK,
                    "reason": None,
                    "forecast_price": round(forecast_price, 2),
                    "expected_change_pct": round((np.exp(predicted_return) - 1) * 100, 2),
                    "direction": "up" if predicted_return > 0 else "down" if predicted_return < 0 else "flat",
                    "interval": interval,
                    "interval_source": interval_source,
                    "prediction_source": prediction_source,
                    "decision": decision,
                    "decision_probability_of_decline": decision_probability_of_decline,
                    "model_skill": validation.get("skill"),
                    "baseline_price": round(base_price, 2),
                }
            )

    store = ForecastStore(
        generated_at=datetime.now(timezone.utc).isoformat(),
        as_of_date=str(pd.Timestamp(as_of).date()),
        model_version=bundle.version,
        config=config.as_dict(),
        forecasts=rows,
        diagnostics={
            "series_forecast": eligible_series,
            "series_skipped": skipped_series,
            "readiness": build_readiness(observations, pd.Timestamp(as_of), config),
            "promoted_horizons": promoted,
            "model_trained_at": bundle.trained_at,
            "training_rows": bundle.training_rows,
            "interval_calibration": {
                "verdict": bundle.backtest.get("verdict"),
                "coverage_90": {
                    horizon: report.get("coverage_90")
                    for horizon, report in (bundle.backtest.get("horizons") or {}).items()
                },
            },
            "observation_rows": int(len(observations)),
        },
    )

    logger.info(
        "Batch inference complete: %d series forecast, %d skipped, %d rows",
        eligible_series, skipped_series, len(rows),
    )
    return store
