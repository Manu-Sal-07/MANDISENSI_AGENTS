"""
Feature engineering — the single source of truth.

This module is deliberately the *only* place features are built. Training and
batch inference both call `build_features`, so a feature can never be computed
one way at fit time and another way at score time. The previous generation of
this system duplicated the logic across `training_pipeline_v2.py` and
`inference_engine_v3.py`, which is the classic setup for train/serve skew:
the model looks excellent offline and quietly degrades in production.

Two properties matter more than the specific feature list:

**No look-ahead.** Every feature at time *t* is computed from observations at
or before *t*. Lags and rolling windows are taken per series after sorting by
date, and targets are built by looking strictly forward.

**Gap awareness.** Mandis do not trade every day, and the upstream feed is
sparse — a market may print Monday, Thursday, then not again for a week.
Positional lags alone would silently treat a 1-day gap and a 10-day gap as
the same thing, so `days_since_prev` is carried as an explicit feature and
targets are resolved on the *calendar*, not on row position. A 5-day forecast
means five calendar days, which is what a trader actually asked for.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Columns that are identifiers/targets rather than model inputs.
NON_FEATURE_COLUMNS = {
    "date",
    "commodity",
    "mandi_id",
    "state",
    "district",
    "source",
    "ingested_at",
    "min_price",
    "max_price",
    # Ingest-time trust in the row, not a market signal. It is consumed
    # directly as a training sample weight (see `train.py`); if it were left
    # in the feature set the model would be conditioning its forecast on how
    # much the pipeline trusted the price, which no future query can supply.
    "quality_score",
    "quality_flags",
    # Which continuity segment a row belongs to. Bookkeeping for building the
    # windowed features and for the eligibility gate, never a signal: it is an
    # arbitrary ordinal that would let a tree split on "this mandi's third
    # trading era" and carry that split into a series where the number means
    # something entirely different. What is genuinely informative about a
    # segment is published separately as `segment_position`,
    # `segment_age_days` and `is_resumed_segment`.
    "segment_id",
    # Bookkeeping and diagnostics, not model inputs: each of these takes a
    # different value depending on how much history the caller happened to
    # pass in, and inference deliberately passes only a trailing window. The
    # window-invariant form the model is actually given is `segment_support`.
    "segment_position",
    "segment_age_days",
    "is_resumed_segment",
}

# Any column carrying a realised future value. `target_h*` is the raw future
# price and `y_h*` its log-return form; both are answers, not inputs. This is
# enforced by prefix rather than by an explicit list because a target that
# leaks into the feature set does not fail loudly — it produces a model that
# validates near-perfectly and is worthless in production.
TARGET_PREFIXES = ("target_h", "y_h")


def is_target_column(name: str) -> bool:
    return name.startswith(TARGET_PREFIXES)


def _series_features(
    frame: pd.DataFrame,
    config: ForecastConfig,
) -> pd.DataFrame:
    """Build features for a single (commodity, mandi) series sorted by date."""
    out = frame.sort_values("date").copy().reset_index(drop=True)
    price = out["modal_price"]

    # --- gap structure -----------------------------------------------------
    gap = out["date"].diff().dt.days
    out["days_since_prev"] = gap.fillna(1.0)

    # A *continuity segment* is a maximal run of observations with no break
    # longer than the freshness window. Every windowed feature below is
    # computed within the current segment, so none of them can reach across a
    # break into a market that no longer exists. See
    # `ForecastConfig.use_segment_aware_features` for what went wrong without
    # this. When disabled, a single constant segment reproduces the original
    # positional behaviour exactly.
    if getattr(config, "use_segment_aware_features", False):
        segment = (gap > config.max_observation_gap_days).fillna(False).cumsum()
    else:
        segment = pd.Series(0, index=out.index)
    out["segment_id"] = segment

    # How much contiguous history actually backs this row.
    #
    # Only `segment_support` is a model input, and it is capped at the longest
    # rolling window on purpose. Inference trims each series to a lookback
    # window, so any raw count of in-segment rows is larger at fit time than at
    # serve time for the same row -- textbook train/serve skew. Past
    # `max(rolling_windows)` observations every window is fully supported and
    # additional history changes no feature value, so clamping there costs
    # nothing and makes the feature identical whether it is computed on the
    # full archive or on the trailing window. The same argument rules out
    # `segment_position`, `segment_age_days` and `is_resumed_segment` as
    # inputs: a break that falls outside the lookback window is invisible at
    # serve time, so the model would be trained on a distinction serving
    # cannot reproduce. They are kept as diagnostics only (see
    # NON_FEATURE_COLUMNS).
    position = out.groupby(segment).cumcount()
    out["segment_position"] = position
    out["segment_support"] = position.clip(upper=max(config.rolling_windows)).astype(float)
    out["segment_age_days"] = (
        out["date"] - out.groupby(segment)["date"].transform("min")
    ).dt.days.astype(float)
    out["is_resumed_segment"] = (segment > 0).astype(int)

    by_segment = price.groupby(segment)

    # --- price level and lags ---------------------------------------------
    for lag in config.price_lags:
        out[f"price_lag_{lag}"] = by_segment.shift(lag)

    # --- returns -----------------------------------------------------------
    for period in (1, 3, 7):
        previous = by_segment.shift(period)
        out[f"return_{period}"] = (price - previous) / previous.where(previous > 0)

    # --- rolling statistics (shifted by 1 so the current row is excluded) ---
    shifted = by_segment.shift(1)
    for window in config.rolling_windows:
        roll = shifted.groupby(segment).rolling(
            window=window, min_periods=max(2, window // 3)
        )
        for name, values in (
            ("mean", roll.mean()),
            ("std", roll.std()),
            ("min", roll.min()),
            ("max", roll.max()),
        ):
            out[f"roll_{name}_{window}"] = values.reset_index(level=0, drop=True)

    # The derived ratios below all divide by a rolling statistic. Where that
    # statistic is missing the result is missing too — not zero. A literal 0.0
    # reads to the model as "today sits exactly on its 30-day mean", which is
    # a confident claim about a market we have no recent history for, and it
    # is precisely the rows early in a segment where that lie is most costly.
    # A real zero is still emitted for the genuinely degenerate case of a flat
    # window, which is information rather than absence.
    def _ratio(numerator, denominator, degenerate):
        return np.where(
            denominator.isna(),
            np.nan,
            np.where(denominator > 0, numerator / denominator.where(denominator > 0), degenerate),
        )

    # Position within the recent range — a cheap, robust regime proxy.
    span = out["roll_max_30"] - out["roll_min_30"]
    out["price_position_30"] = _ratio(price - out["roll_min_30"], span, 0.5)

    # Deviation from trend: how stretched is today versus its own recent mean.
    out["dev_from_mean_7"] = _ratio(price - out["roll_mean_7"], out["roll_mean_7"], 0.0)
    out["dev_from_mean_30"] = _ratio(price - out["roll_mean_30"], out["roll_mean_30"], 0.0)

    # Normalised volatility — comparable across commodities at different levels.
    out["volatility_7"] = _ratio(out["roll_std_7"], out["roll_mean_7"], 0.0)
    out["volatility_30"] = _ratio(out["roll_std_30"], out["roll_mean_30"], 0.0)

    # --- momentum ----------------------------------------------------------
    out["momentum_7"] = _ratio(
        out["roll_mean_7"] - out["roll_mean_30"], out["roll_mean_7"], 0.0
    )

    # --- arrivals (optional) ----------------------------------------------
    # The free daily feed carries price but not volume. Rather than fabricate
    # zeros — which reads to a tree model as "volume collapsed to nothing" —
    # arrival features are emitted as NaN when unavailable and XGBoost's
    # native missing-value handling routes them.
    if config.use_arrivals and "arrivals" in out.columns:
        arrivals = pd.to_numeric(out["arrivals"], errors="coerce")
        by_arrivals = arrivals.groupby(segment)
        out["arrivals_lag_1"] = by_arrivals.shift(1)
        out["arrivals_lag_7"] = by_arrivals.shift(7)
        arrivals_mean_7 = (
            by_arrivals.shift(1)
            .groupby(segment)
            .rolling(7, min_periods=2)
            .mean()
            .reset_index(level=0, drop=True)
        )
        out["arrivals_mean_7"] = arrivals_mean_7
        out["arrivals_dev"] = _ratio(arrivals - arrivals_mean_7, arrivals_mean_7, np.nan)
        out["has_arrivals"] = arrivals.notna().astype(int)

        # Rolling log-log price/arrival elasticity — how much a given change in
        # supply has recently moved price for this series. Stack A's arrival
        # agent computes the same economic quantity, but as a per-row
        # LinearRegression fit inside a Python loop over the whole history —
        # O(n * window). The closed-form slope of a simple regression is
        # cov(x, y) / var(x), and pandas computes rolling covariance and
        # variance natively, so the identical number falls out of two vectorised
        # calls instead of one fit per row. Includes the current row's own
        # price/arrivals, which is not a look-ahead: at serve time "today" is
        # always known when forecasting forward from it (see module docstring).
        window = config.price_arrival_elasticity_window
        with np.errstate(divide="ignore", invalid="ignore"):
            log_price = np.log(price.where(price > 0))
            log_arrivals = np.log(arrivals.where(arrivals > 0))
        # Computed segment by segment explicitly: a paired `rolling().cov(other)`
        # inside a groupby returns a doubled index rather than one value per
        # row, so the vectorised form used for the unpaired statistics above
        # cannot be reused here.
        cov = pd.Series(np.nan, index=out.index, dtype=float)
        var = pd.Series(np.nan, index=out.index, dtype=float)
        for _, position in out.groupby(segment).groups.items():
            arrivals_slice = log_arrivals.loc[position]
            rolling = arrivals_slice.rolling(window, min_periods=10)
            cov.loc[position] = rolling.cov(log_price.loc[position])
            var.loc[position] = rolling.var()
        out["price_arrival_elasticity"] = np.where(var > 0, cov / var, np.nan)
    else:
        for column in (
            "arrivals_lag_1", "arrivals_lag_7", "arrivals_mean_7", "arrivals_dev",
            "price_arrival_elasticity",
        ):
            out[column] = np.nan
        out["has_arrivals"] = 0

    # --- calendar ----------------------------------------------------------
    out["month"] = out["date"].dt.month
    out["day_of_week"] = out["date"].dt.dayofweek
    out["day_of_year"] = out["date"].dt.dayofyear
    out["week_of_year"] = out["date"].dt.isocalendar().week.astype(int)

    # Cyclical encodings so December sits next to January rather than 11 units
    # away, which a tree can only approximate with extra splits.
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)
    out["doy_sin"] = np.sin(2 * np.pi * out["day_of_year"] / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * out["day_of_year"] / 365.25)

    return out


def _add_horizon_targets(
    frame: pd.DataFrame,
    horizons: Tuple[int, ...],
) -> pd.DataFrame:
    """
    Attach a target per horizon, resolved on the calendar.

    For horizon h, the target is the modal price of the first observation on or
    after (date + h days), looked up with a backward-searching as-of join from
    the target date. Rows with no qualifying future observation are left NaN
    and dropped at fit time.
    """
    out = frame.sort_values("date").reset_index(drop=True)
    lookup = out[["date", "modal_price"]].rename(
        columns={"date": "obs_date", "modal_price": "future_price"}
    )

    for horizon in horizons:
        probe = pd.DataFrame({"target_date": out["date"] + pd.Timedelta(days=horizon)})
        # Slack scales with the horizon: a sparse mandi rarely prints exactly h
        # days out, so some tolerance is needed or most targets are lost. It
        # stays proportional because a fixed week of slack would let a "1-day"
        # forecast be scored against a print eight days later — a different
        # question wearing the same label.
        slack = max(3, horizon)
        merged = pd.merge_asof(
            probe.sort_values("target_date"),
            lookup.sort_values("obs_date"),
            left_on="target_date",
            right_on="obs_date",
            direction="forward",
            tolerance=pd.Timedelta(days=slack),
        )
        out[f"target_h{horizon}"] = merged["future_price"].to_numpy()

    return out


def build_features(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
    with_targets: bool = False,
) -> pd.DataFrame:
    """
    Build the modelling frame from raw observations.

    Args:
        observations: long frame with date, commodity, mandi_id, modal_price
            and optionally arrivals.
        config: feature configuration.
        with_targets: attach per-horizon targets (training) or not (inference).

    Returns:
        One row per input observation, with features appended. Series shorter
        than a usable history are still returned — filtering on history length
        is the caller's decision, and is made explicit in the pipeline.
    """
    if observations is None or observations.empty:
        return pd.DataFrame()

    frame = observations.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
    frame = frame[frame["modal_price"].notna() & (frame["modal_price"] > 0)]

    if frame.empty:
        return pd.DataFrame()

    built: List[pd.DataFrame] = []
    for (commodity, mandi_id), group in frame.groupby(["commodity", "mandi_id"], sort=True):
        if len(group) < 2:
            continue
        featured = _series_features(group, config)
        if with_targets:
            featured = _add_horizon_targets(featured, config.horizons)
        featured["commodity"] = commodity
        featured["mandi_id"] = mandi_id
        built.append(featured)

    if not built:
        return pd.DataFrame()

    result = pd.concat(built, ignore_index=True)

    # Absence features are derived from the whole panel rather than per series,
    # because the thing that distinguishes "nobody brought tomatoes" from "the
    # report never arrived" is what the *other* series printed that day.
    if getattr(config, "use_absence_features", False):
        try:
            from mandisense_ai.forecasting.absence import build_absence_features

            result = build_absence_features(result)
        except Exception as exc:
            logger.warning("Absence features unavailable, continuing without: %s", exc)

    # Seasonal climatology needs each row's own calendar year plus every prior
    # year in the same series, which per-series feature building above does
    # not carry forward — attached here from the original (un-trimmed by the
    # per-series loop) observations instead.
    if getattr(config, "use_seasonal_climatology", False):
        try:
            from mandisense_ai.forecasting.seasonal import attach_seasonal_features

            result = attach_seasonal_features(result, frame, config)
        except Exception as exc:
            logger.warning("Seasonal climatology features unavailable, continuing without: %s", exc)

    return result.sort_values(["commodity", "mandi_id", "date"]).reset_index(drop=True)


def feature_columns(frame: pd.DataFrame) -> List[str]:
    """
    The model input columns present in a built frame.

    Derived from the frame itself rather than a hardcoded list, so training and
    inference cannot drift apart as features are added or removed. Targets and
    identifiers are excluded.
    """
    return [
        column
        for column in frame.columns
        if column not in NON_FEATURE_COLUMNS
        and not is_target_column(column)
        and pd.api.types.is_numeric_dtype(frame[column])
    ]


def latest_feature_rows(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """
    The most recent feature row per series — the inference input.

    This is the scoring counterpart to `build_features(with_targets=True)` and
    shares its implementation exactly, which is the point.

    Only the trailing `lookback_window` observations of each series are used.
    The longest feature is a 30-period rolling window, so older rows cannot
    influence the final row's values — building features across a decade of
    history to produce one row per series is pure waste, and it is waste that
    grows every night the job runs.
    """
    if observations is None or observations.empty:
        return pd.DataFrame()

    frame = observations.copy()
    frame["date"] = pd.to_datetime(frame["date"])

    window = max(config.lookback_window, max(config.rolling_windows) + max(config.price_lags) + 5)
    trimmed = (
        frame.sort_values("date")
        .groupby(["commodity", "mandi_id"], as_index=False, group_keys=False)
        .tail(window)
    )

    built = build_features(trimmed, config, with_targets=False)
    if built.empty:
        return built
    return (
        built.sort_values("date")
        .groupby(["commodity", "mandi_id"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
