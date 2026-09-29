"""
Tests for leak-free seasonal climatology.

Organised around the property that makes this safe to drop into a
walk-forward-validated pipeline:

  * a row's seasonal reference is built only from years strictly before its
    own -- adding or changing a *later* year's data must never change an
    earlier row's feature value
  * a row in a bucket's first observed year has no prior year to reference
    and is left NaN, not zero or some other silent default
  * the serving-time table lookup answers the same question a fresh row
    (one dated after all training data) would get from the expanding
    version, without needing that row's own multi-year history
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.config import ForecastConfig
from mandisense_ai.forecasting.seasonal import (
    build_climatology_table,
    expanding_seasonal_features,
    lookup_batch,
    table_from_json,
    table_to_json,
)

CONFIG = ForecastConfig(seasonal_bucket_days=15)


def _series(mandi_id, commodity, year_prices, bucket_day=1):
    """One row per year, all landing in the same ~15-day bucket, at prices
    given by `year_prices` (a dict of year -> price)."""
    records = []
    for year, price in year_prices.items():
        date = pd.Timestamp(year=year, month=1, day=bucket_day)
        records.append(
            {"commodity": commodity, "mandi_id": mandi_id, "date": date, "modal_price": price}
        )
    return pd.DataFrame(records)


class TestLeakFreeExpandingFeature:
    def test_first_year_has_no_reference(self):
        obs = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1100.0, 2022: 1200.0})
        result = expanding_seasonal_features(obs, CONFIG)

        first_year_row = result[result["date"] == pd.Timestamp("2020-01-01")].iloc[0]
        assert pd.isna(first_year_row["seasonal_deviation_pct"])
        assert first_year_row["seasonal_reference_years"] == 0

    def test_second_year_references_only_the_first(self):
        obs = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1300.0})
        result = expanding_seasonal_features(obs, CONFIG)

        row = result[result["date"] == pd.Timestamp("2021-01-01")].iloc[0]
        assert row["seasonal_reference_years"] == 1
        # Reference is 2020's price (1000); 2021 printed 1300 -> +30% deviation.
        assert row["seasonal_deviation_pct"] == pytest.approx(0.30, abs=1e-6)

    def test_later_year_never_affects_an_earlier_rows_feature(self):
        """The property that makes this safe under walk-forward CV: a row's
        feature value must be identical whether or not future years are even
        present in the input frame."""
        without_future = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1200.0})
        with_future = _series(
            "kolar_apmc", "tomato", {2020: 1000.0, 2021: 1200.0, 2022: 5000.0}
        )

        result_a = expanding_seasonal_features(without_future, CONFIG)
        result_b = expanding_seasonal_features(with_future, CONFIG)

        row_a = result_a[result_a["date"] == pd.Timestamp("2021-01-01")].iloc[0]
        row_b = result_b[result_b["date"] == pd.Timestamp("2021-01-01")].iloc[0]

        assert row_a["seasonal_deviation_pct"] == pytest.approx(row_b["seasonal_deviation_pct"])
        assert row_a["seasonal_reference_years"] == row_b["seasonal_reference_years"]

    def test_reference_years_accumulate_across_years(self):
        obs = _series(
            "kolar_apmc", "tomato",
            {2018: 900.0, 2019: 1000.0, 2020: 1100.0, 2021: 1200.0},
        )
        result = expanding_seasonal_features(obs, CONFIG).sort_values("date")

        assert list(result["seasonal_reference_years"]) == [0, 1, 2, 3]

    def test_reference_is_the_median_of_prior_years_not_just_the_last(self):
        """An expanding median rather than 'last year's price' -- one noisy
        year should not single-handedly dominate the reference."""
        obs = _series(
            "kolar_apmc", "tomato",
            {2018: 1000.0, 2019: 1000.0, 2020: 1000.0, 2021: 9000.0, 2022: 1000.0},
        )
        result = expanding_seasonal_features(obs, CONFIG)

        row_2022 = result[result["date"] == pd.Timestamp("2022-01-01")].iloc[0]
        # Prior years are [1000, 1000, 1000, 9000]; median is 1000, not
        # dragged toward the single outlier the way a mean would be.
        assert row_2022["seasonal_deviation_pct"] == pytest.approx(0.0, abs=1e-6)

    def test_different_buckets_do_not_share_a_reference(self):
        """A January price spike must not leak into July's climatology."""
        jan = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1000.0}, bucket_day=1)
        jul = pd.DataFrame(
            [
                {"commodity": "tomato", "mandi_id": "kolar_apmc",
                 "date": pd.Timestamp("2020-07-01"), "modal_price": 5000.0},
                {"commodity": "tomato", "mandi_id": "kolar_apmc",
                 "date": pd.Timestamp("2021-07-01"), "modal_price": 5100.0},
            ]
        )
        obs = pd.concat([jan, jul], ignore_index=True)
        result = expanding_seasonal_features(obs, CONFIG)

        jan_2021 = result[result["date"] == pd.Timestamp("2021-01-01")].iloc[0]
        # Referencing only January 2020 (1000), not July 2020 (5000).
        assert jan_2021["seasonal_deviation_pct"] == pytest.approx(0.0, abs=1e-6)

    def test_empty_input_returns_empty_frame(self):
        result = expanding_seasonal_features(pd.DataFrame(), CONFIG)
        assert result.empty


class TestClimatologyTable:
    def test_table_uses_all_years_including_the_most_recent(self):
        """Unlike the training feature, the serving snapshot legitimately
        includes every year present -- any request it serves happens after
        all of it was observed."""
        obs = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1200.0})
        table = build_climatology_table(obs, CONFIG)

        bucket = 0  # January 1st falls in the first ~15-day bucket
        entry = table[("tomato", "kolar_apmc", bucket)]
        assert entry["reference_years"] == 2
        assert entry["median_price"] == pytest.approx(1100.0)

    def test_empty_input_returns_empty_table(self):
        assert build_climatology_table(pd.DataFrame(), CONFIG) == {}


class TestServingLookup:
    def test_lookup_fills_what_the_trimmed_window_could_not(self):
        obs = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1000.0, 2022: 1000.0})
        table = build_climatology_table(obs, CONFIG)

        serving_row = pd.DataFrame(
            [{"commodity": "tomato", "mandi_id": "kolar_apmc",
              "date": pd.Timestamp("2023-01-01"), "modal_price": 1250.0}]
        )
        enriched = lookup_batch(serving_row, table, CONFIG)

        assert enriched.iloc[0]["seasonal_reference_years"] == 3
        assert enriched.iloc[0]["seasonal_deviation_pct"] == pytest.approx(0.25, abs=1e-6)

    def test_unknown_series_abstains_rather_than_guessing(self):
        table = build_climatology_table(
            _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1000.0}), CONFIG
        )
        serving_row = pd.DataFrame(
            [{"commodity": "onion", "mandi_id": "hoskote_apmc",
              "date": pd.Timestamp("2023-01-01"), "modal_price": 500.0}]
        )
        enriched = lookup_batch(serving_row, table, CONFIG)

        assert pd.isna(enriched.iloc[0]["seasonal_deviation_pct"])
        assert enriched.iloc[0]["seasonal_reference_years"] == 0

    def test_empty_table_leaves_rows_unchanged(self):
        serving_row = pd.DataFrame(
            [{"commodity": "tomato", "mandi_id": "kolar_apmc",
              "date": pd.Timestamp("2023-01-01"), "modal_price": 1000.0}]
        )
        result = lookup_batch(serving_row, {}, CONFIG)
        assert result.equals(serving_row)


class TestJsonRoundTrip:
    def test_table_survives_json_serialisation(self):
        obs = _series("kolar_apmc", "tomato", {2020: 1000.0, 2021: 1200.0})
        table = build_climatology_table(obs, CONFIG)

        restored = table_from_json(table_to_json(table))

        assert restored == table

    def test_empty_and_none_round_trip_to_empty(self):
        assert table_from_json(table_to_json({})) == {}
        assert table_from_json(None) == {}
