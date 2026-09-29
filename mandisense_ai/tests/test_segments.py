"""
Tests for segment-aware feature construction.

A *continuity segment* is a maximal run of observations with no break longer
than the freshness window. Every windowed feature is computed within the
current segment, which fixes a live defect: lags and rolling windows were
positional, so a mandi that stopped trading in 2024 and resumed in 2026 was
refused on its first print (`days_since_prev` was huge) and accepted on its
*second*, at which point `days_since_prev` was 1 while `price_lag_14` and
`roll_mean_30` still described the 2024 market. The model was handed a 3x
"spike" that was really just the new price level.

The properties pinned here:

  * no windowed feature takes a value from before a break
  * the features the model is *given* are invariant to how much history the
    caller passes in -- inference trims to a lookback window, so anything
    that counts rows since a break cannot be a model input
  * a missing rolling statistic propagates as missing, never as 0.0, which
    would assert "today sits exactly on its 30-day mean" for a market we have
    no recent history of
  * the eligibility gate counts contiguous observations, and says how many
    more are needed rather than refusing indefinitely
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.batch_predict import (
    STATUS_OK,
    STATUS_REBUILDING,
    _series_eligibility,
)
from mandisense_ai.forecasting.config import ForecastConfig
from mandisense_ai.forecasting.features import (
    build_features,
    feature_columns,
    latest_feature_rows,
)


PRE_BREAK_PRICE = 1000.0
POST_BREAK_PRICE = 3000.0


def _config(**overrides):
    base = dict(horizons=(1, 3), min_history_days=30, max_observation_gap_days=21)
    base.update(overrides)
    return ForecastConfig(**base)


def _span(start, periods, price, commodity="tomato", mandi="agra_apmc"):
    return pd.DataFrame(
        {
            "date": pd.date_range(start, periods=periods, freq="D"),
            "commodity": commodity,
            "mandi_id": mandi,
            "modal_price": float(price),
            "arrivals": 100.0,
            "source": "test",
        }
    )


def _resumed(days_after_break, periods_before=200):
    """An archive ending in 2024, then `days_after_break` prints in 2026."""
    return pd.concat(
        [
            _span("2024-01-01", periods_before, PRE_BREAK_PRICE),
            _span("2026-01-01", days_after_break, POST_BREAK_PRICE),
        ],
        ignore_index=True,
    )


# -- the defect itself -----------------------------------------------------


@pytest.mark.parametrize("days_after", [1, 2, 3, 5, 12, 40])
def test_no_windowed_feature_carries_a_pre_break_value(days_after):
    """
    The core property. Every windowed feature on the latest row is either
    missing or describes the post-break market -- never the 2024 one.
    """
    built = build_features(_resumed(days_after), _config(), with_targets=False)
    row = built.iloc[-1]

    windowed = [
        c
        for c in built.columns
        if c.startswith(("price_lag_", "roll_mean_", "roll_min_", "roll_max_"))
    ]
    assert windowed, "expected windowed feature columns to exist"

    for column in windowed:
        value = row[column]
        if pd.isna(value):
            continue
        assert value == pytest.approx(POST_BREAK_PRICE), (
            f"{column} = {value} on day {days_after} after the break; "
            f"pre-break price was {PRE_BREAK_PRICE}"
        )


def test_the_second_print_after_a_break_is_not_silently_accepted():
    """
    The exact regression: on day 2 the old gate passed the series because
    `days_since_prev` was 1, while its 14-day lag still held a 2024 price.
    """
    config = _config()
    row = build_features(_resumed(2), config, with_targets=False).iloc[-1]

    assert pd.isna(row["price_lag_14"])
    assert pd.isna(row["roll_mean_30"])

    verdict = _series_eligibility(
        history_rows=202,
        last_date=pd.Timestamp(row["date"]),
        as_of=pd.Timestamp(row["date"]),
        days_since_prev=float(row["days_since_prev"]),
        config=config,
        segment_observations=int(row["segment_position"]) + 1,
    )
    assert verdict["eligible"] is False
    assert verdict["status"] == STATUS_REBUILDING


def test_a_rebuilt_series_becomes_eligible_again():
    config = _config(min_segment_observations=10)
    row = build_features(_resumed(40), config, with_targets=False).iloc[-1]

    verdict = _series_eligibility(
        history_rows=240,
        last_date=pd.Timestamp(row["date"]),
        as_of=pd.Timestamp(row["date"]),
        days_since_prev=1.0,
        config=config,
        segment_observations=int(row["segment_position"]) + 1,
    )
    assert verdict["eligible"] is True
    assert verdict["status"] == STATUS_OK


def test_the_refusal_says_how_many_more_prints_are_needed():
    config = _config(min_segment_observations=10)
    verdict = _series_eligibility(
        history_rows=500,
        last_date=pd.Timestamp("2026-01-04"),
        as_of=pd.Timestamp("2026-01-04"),
        days_since_prev=1.0,
        config=config,
        segment_observations=4,
    )
    assert verdict["status"] == STATUS_REBUILDING
    assert "6 more needed" in verdict["reason"]
    assert verdict["segment_observations"] == 4


# -- train/serve invariance ------------------------------------------------


def test_segment_support_is_invariant_to_how_much_history_is_passed():
    """
    Inference trims to a lookback window. Any feature counting rows since a
    break would be larger at fit time than at serve time for the same row.
    """
    config = _config()
    observations = _span("2022-01-01", 900, PRE_BREAK_PRICE)

    full = (
        build_features(observations, config, with_targets=False)
        .sort_values("date")
        .groupby(["commodity", "mandi_id"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    windowed = latest_feature_rows(observations, config)

    assert full["segment_position"].iloc[0] != windowed["segment_position"].iloc[0]
    assert full["segment_support"].iloc[0] == windowed["segment_support"].iloc[0]
    assert full["segment_support"].iloc[0] == max(config.rolling_windows)


def test_raw_segment_counters_are_not_model_inputs():
    built = build_features(_resumed(40), _config(), with_targets=False)
    features = feature_columns(built)

    for leaked in (
        "segment_id",
        "segment_position",
        "segment_age_days",
        "is_resumed_segment",
    ):
        assert leaked not in features, f"{leaked} must not be a model input"
    assert "segment_support" in features


# -- missingness propagation -----------------------------------------------


def test_missing_rolling_statistics_propagate_as_missing_not_zero():
    """
    A literal 0.0 here reads as "today sits exactly on its 30-day mean" --
    a confident claim about a market with no recent history.
    """
    row = build_features(_resumed(2), _config(), with_targets=False).iloc[-1]

    assert pd.isna(row["roll_mean_30"])
    for derived in (
        "dev_from_mean_30",
        "volatility_30",
        "momentum_7",
        "price_position_30",
    ):
        assert pd.isna(row[derived]), f"{derived} fabricated a value from a missing input"


def test_a_genuinely_flat_window_still_reports_a_real_zero():
    """Absence and a measured zero must stay distinguishable."""
    row = build_features(_span("2026-01-01", 60, PRE_BREAK_PRICE), _config()).iloc[-1]

    assert row["roll_mean_30"] == pytest.approx(PRE_BREAK_PRICE)
    assert row["dev_from_mean_30"] == pytest.approx(0.0)
    assert row["volatility_30"] == pytest.approx(0.0)


# -- opt-out ---------------------------------------------------------------


def test_disabling_segmentation_restores_positional_windows():
    """
    The switch is real: with it off, the pre-break value comes back. Pinned so
    the flag cannot quietly become a no-op.
    """
    off = build_features(
        _resumed(5), _config(use_segment_aware_features=False), with_targets=False
    ).iloc[-1]
    on = build_features(
        _resumed(5), _config(use_segment_aware_features=True), with_targets=False
    ).iloc[-1]

    assert off["price_lag_14"] == pytest.approx(PRE_BREAK_PRICE)
    assert pd.isna(on["price_lag_14"])


def test_an_unbroken_series_is_unaffected_by_segmentation():
    """Segmenting must be a no-op where there is nothing to segment."""
    observations = _span("2024-01-01", 300, PRE_BREAK_PRICE)

    on = build_features(
        observations, _config(use_segment_aware_features=True), with_targets=False
    )
    off = build_features(
        observations, _config(use_segment_aware_features=False), with_targets=False
    )

    shared = [
        c
        for c in feature_columns(on)
        if c in feature_columns(off) and c != "segment_support"
    ]
    np.testing.assert_allclose(
        on[shared].to_numpy(float),
        off[shared].to_numpy(float),
        rtol=1e-9,
        equal_nan=True,
    )


def test_a_target_is_never_resolved_across_a_break():
    """
    The forward-looking counterpart. Targets are resolved on the calendar with
    a tolerance of at most a week, so the last row before a break must have no
    target rather than borrowing the post-break price as its "future".
    """
    config = _config(horizons=(1, 3))
    built = build_features(_resumed(5), config, with_targets=True)

    last_before_break = built[built["date"] == pd.Timestamp("2024-07-18")]
    assert len(last_before_break) == 1
    row = last_before_break.iloc[0]

    for horizon in config.horizons:
        assert pd.isna(row[f"target_h{horizon}"]), (
            f"target_h{horizon} reached across an 18-month break"
        )
