"""
Leak-free seasonal climatology.

Every named "seasonality" signal in this codebase before this module was one
of: a raw `month` integer, a cyclical `month_sin`/`month_cos`/`doy_sin`/`doy_cos`
encoding, or — in the agent literally named `SeasonalityAgent` — a mock
regressor (`SARIMAMultiHorizonRegressor`) that returns a constant, and several
hundred lines of STL/drift/festival-premium code that the agent's own
`execute()` never calls. None of that is seasonality; it is calendar position,
which a tree model can only turn into seasonality by re-deriving the pattern
from scratch, one split at a time, from whatever years happen to fall in its
training fold.

This module computes the thing directly: how far today's price sits from the
historical norm for this time of year, where "historical norm" means the
median price this series has printed in the same ~15-day window of the
calendar, in years strictly before the one the current row belongs to.

Two properties make this safe to drop into a walk-forward-validated pipeline
without re-opening the leakage question the rest of this codebase is careful
about:

**Expanding, not global.** The reference for a row in 2021 is built only from
2016-2020; the reference for a 2019 row never sees 2020 or 2021 data, even
though all three rows might sit in the same training fold. A global "median
price in this calendar window across all years" would leak exactly that —
every row's feature would carry information from every other year, including
years that come after it, which is invisible in an offline table but would
quietly inflate every walk-forward skill number computed on top of it.

**Table snapshot for serving.** Training computes the expanding version above
for every row. Serving asks a different question — "what is the seasonal norm
right now" — which does not need the expanding history at all, only the
freshest snapshot, exactly the way `ForecastBundle.commodity_codes` is a
snapshot rather than something recomputed per request. `build_climatology_table`
produces that snapshot at training time from the full archive; `lookup_batch`
answers it at serve time in O(1) per row. This also sidesteps a real
constraint: `latest_feature_rows` deliberately loads only a small trailing
window per series (a decade of history to produce one inference row is
"waste that grows every night the job runs", per its own docstring), which is
nowhere near enough to see a prior year directly. The table is how a 120-day
serving window still gets a genuine multi-year answer.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

SEASONAL_FEATURE_COLUMNS = ("seasonal_deviation_pct", "seasonal_reference_years")

ClimatologyTable = Dict[Tuple[str, str, int], Dict[str, float]]


def _bucket_of_year(dates: pd.Series, bucket_days: int) -> pd.Series:
    """Which ~`bucket_days`-wide slice of the calendar year a date falls in.

    Forced to int64 explicitly rather than the bare Python `int`: on Windows,
    `.astype(int)` produces int32 (native C `long`), while `.dt.year` and
    other pandas integer columns are int64. A later merge on a mismatched
    int32/int64 key raises a low-level buffer dtype error rather than
    quietly upcasting, so the platform-independent width has to be explicit.
    """
    day_of_year = dates.dt.dayofyear
    return ((day_of_year - 1) // bucket_days).astype("int64")


def _bucket_year_medians(
    observations: pd.DataFrame, bucket_days: int
) -> pd.DataFrame:
    """One row per (commodity, mandi_id, bucket, year): that cell's median price."""
    frame = observations[["commodity", "mandi_id", "date", "modal_price"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
    frame = frame.dropna(subset=["date", "modal_price"])
    frame = frame[frame["modal_price"] > 0]

    frame["year"] = frame["date"].dt.year
    frame["bucket"] = _bucket_of_year(frame["date"], bucket_days)

    grouped = (
        frame.groupby(["commodity", "mandi_id", "bucket", "year"])["modal_price"]
        .median()
        .reset_index()
        .sort_values(["commodity", "mandi_id", "bucket", "year"])
        .reset_index(drop=True)
    )
    return grouped


def expanding_seasonal_features(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """
    Row-level, leak-free seasonal deviation for training and walk-forward CV.

    Returns a frame keyed on ``(commodity, mandi_id, date)`` with
    ``seasonal_deviation_pct`` and ``seasonal_reference_years``, meant to be
    merged onto the built feature frame. A row in a bucket's first observed
    year has no prior year to compare against and gets NaN — a fact about the
    series' history, not a computation error, and left for the model's native
    missing-value handling exactly like an absent arrivals column.
    """
    if observations is None or observations.empty:
        return pd.DataFrame(
            columns=["commodity", "mandi_id", "date", *SEASONAL_FEATURE_COLUMNS]
        )

    bucket_days = config.seasonal_bucket_days
    bucket_year = _bucket_year_medians(observations, bucket_days)
    if bucket_year.empty:
        return pd.DataFrame(
            columns=["commodity", "mandi_id", "date", *SEASONAL_FEATURE_COLUMNS]
        )

    group = bucket_year.groupby(["commodity", "mandi_id", "bucket"])["modal_price"]
    # Shifted before expanding so the current year's own bucket-median is
    # excluded from its own reference — the entire leak-free property lives
    # in this one shift.
    bucket_year["prior_median"] = group.apply(
        lambda s: s.shift(1).expanding().median()
    ).reset_index(level=[0, 1, 2], drop=True)
    bucket_year["prior_reference_years"] = group.cumcount()

    frame = observations[["commodity", "mandi_id", "date", "modal_price"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
    frame["year"] = frame["date"].dt.year
    frame["bucket"] = _bucket_of_year(frame["date"], bucket_days)

    merged = frame.merge(
        bucket_year[["commodity", "mandi_id", "bucket", "year", "prior_median", "prior_reference_years"]],
        on=["commodity", "mandi_id", "bucket", "year"],
        how="left",
    )

    merged["seasonal_deviation_pct"] = np.where(
        merged["prior_median"] > 0,
        (merged["modal_price"] - merged["prior_median"]) / merged["prior_median"],
        np.nan,
    )
    merged["seasonal_reference_years"] = merged["prior_reference_years"].fillna(0).astype(int)

    return merged[["commodity", "mandi_id", "date", *SEASONAL_FEATURE_COLUMNS]]


def attach_seasonal_features(
    result: pd.DataFrame,
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Merge the expanding seasonal features onto an already-built feature frame."""
    seasonal = expanding_seasonal_features(observations, config)
    if seasonal.empty:
        for column in SEASONAL_FEATURE_COLUMNS:
            result[column] = np.nan
        return result

    merged = result.merge(seasonal, on=["commodity", "mandi_id", "date"], how="left")
    return merged


def build_climatology_table(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> ClimatologyTable:
    """
    The freshest seasonal-norm snapshot, for serving.

    Unlike the expanding training feature, this uses *every* year present,
    including the most recent one — legitimately, because any request this
    table serves happens strictly after all of this data was observed. Keyed
    by ``(commodity, mandi_id, bucket)`` for an O(1) lookup per forecast row.
    """
    if observations is None or observations.empty:
        return {}

    bucket_days = config.seasonal_bucket_days
    bucket_year = _bucket_year_medians(observations, bucket_days)
    if bucket_year.empty:
        return {}

    group = bucket_year.groupby(["commodity", "mandi_id", "bucket"])["modal_price"]
    bucket_year["cumulative_median"] = group.apply(
        lambda s: s.expanding().median()
    ).reset_index(level=[0, 1, 2], drop=True)
    bucket_year["cumulative_years"] = group.cumcount() + 1

    latest = (
        bucket_year.sort_values(["commodity", "mandi_id", "bucket", "year"])
        .groupby(["commodity", "mandi_id", "bucket"], as_index=False)
        .tail(1)
    )

    table: ClimatologyTable = {}
    for row in latest.itertuples(index=False):
        key = (row.commodity, row.mandi_id, int(row.bucket))
        table[key] = {
            "median_price": float(row.cumulative_median),
            "reference_years": int(row.cumulative_years),
        }
    return table


def lookup_batch(
    rows: pd.DataFrame,
    table: ClimatologyTable,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """
    Apply a persisted climatology table to a small serving-time frame.

    `rows` must carry `commodity`, `mandi_id`, `date`, `modal_price`. Returns
    `rows` with `seasonal_deviation_pct` / `seasonal_reference_years`
    overwritten from the table — replacing whatever `latest_feature_rows`
    computed internally, which is almost always NaN, because a serving
    window a few months wide essentially never reaches back to a prior year.
    """
    if rows.empty or not table:
        return rows

    out = rows.copy()
    buckets = _bucket_of_year(pd.to_datetime(out["date"]), config.seasonal_bucket_days)

    deviations = []
    reference_years = []
    for commodity, mandi_id, bucket, price in zip(
        out["commodity"], out["mandi_id"], buckets, out["modal_price"]
    ):
        entry = table.get((commodity, mandi_id, int(bucket)))
        if entry is None or entry["median_price"] <= 0:
            deviations.append(np.nan)
            reference_years.append(0)
            continue
        deviations.append((float(price) - entry["median_price"]) / entry["median_price"])
        reference_years.append(entry["reference_years"])

    out["seasonal_deviation_pct"] = deviations
    out["seasonal_reference_years"] = reference_years
    return out


def table_to_json(table: ClimatologyTable) -> Dict[str, Dict[str, float]]:
    """JSON has no tuple keys; flatten to a `"commodity::mandi_id::bucket"` string."""
    return {
        f"{commodity}::{mandi_id}::{bucket}": values
        for (commodity, mandi_id, bucket), values in table.items()
    }


def table_from_json(payload: Optional[Dict[str, Dict[str, float]]]) -> ClimatologyTable:
    if not payload:
        return {}
    table: ClimatologyTable = {}
    for flat_key, values in payload.items():
        commodity, mandi_id, bucket = flat_key.split("::")
        table[(commodity, mandi_id, int(bucket))] = {
            "median_price": float(values["median_price"]),
            "reference_years": int(values["reference_years"]),
        }
    return table
