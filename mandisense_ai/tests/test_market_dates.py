"""
Regression tests for market date parsing.

These guard a defect that silently destroyed most of the real dataset: passing
``dayfirst=True`` to ``pandas.to_datetime`` for ISO-8601 inputs transposed day
and month for days 1-12 and turned days 13-31 into NaT, which downstream
``dropna`` calls then discarded. The result was a dataset with ~37% of its rows,
all filed under wrong dates.
"""

import pandas as pd
import pytest

from mandisense_ai.utils.dates import parse_market_dates


class TestIsoDates:
    def test_iso_dates_are_not_transposed(self):
        """2019-09-10 is 10 September, never 9 October."""
        parsed = parse_market_dates(pd.Series(["2019-09-10"]))
        assert parsed.iloc[0] == pd.Timestamp("2019-09-10")

    def test_iso_days_above_twelve_survive(self):
        """The bug turned day>12 into NaT; those rows must be retained."""
        values = ["2019-09-13", "2019-09-20", "2019-09-31"]
        parsed = parse_market_dates(pd.Series(values))
        assert parsed.iloc[0] == pd.Timestamp("2019-09-13")
        assert parsed.iloc[1] == pd.Timestamp("2019-09-20")
        assert pd.isna(parsed.iloc[2])  # 31 September does not exist

    def test_full_month_of_iso_dates_parses_completely(self):
        dates = pd.date_range("2019-09-01", "2019-09-30", freq="D")
        raw = pd.Series([d.strftime("%Y-%m-%d") for d in dates])
        parsed = parse_market_dates(raw)
        assert parsed.notna().all()
        assert list(parsed) == list(dates)

    def test_day_of_month_coverage_is_preserved(self):
        """
        The signature of the original defect: only days 1-12 survived, because
        the day field was being read as a month.
        """
        dates = pd.date_range("2019-01-01", "2019-12-31", freq="D")
        raw = pd.Series([d.strftime("%Y-%m-%d") for d in dates])
        parsed = parse_market_dates(raw)
        assert parsed.dt.day.max() == 31
        assert parsed.dt.month.nunique() == 12


class TestOtherFormats:
    def test_unambiguous_dayfirst(self):
        parsed = parse_market_dates(pd.Series(["13-09-2019", "10-09-2019"]))
        assert parsed.iloc[0] == pd.Timestamp("2019-09-13")
        assert parsed.iloc[1] == pd.Timestamp("2019-09-10")

    def test_unambiguous_monthfirst(self):
        parsed = parse_market_dates(pd.Series(["09/13/2019", "09/10/2019"]))
        assert parsed.iloc[0] == pd.Timestamp("2019-09-13")
        assert parsed.iloc[1] == pd.Timestamp("2019-09-10")

    def test_textual_month(self):
        parsed = parse_market_dates(pd.Series(["13-Sep-2019", "06-Jan-2015"]))
        assert parsed.iloc[0] == pd.Timestamp("2019-09-13")
        assert parsed.iloc[1] == pd.Timestamp("2015-01-06")


class TestRobustness:
    def test_unparseable_becomes_nat_not_a_wrong_date(self):
        parsed = parse_market_dates(pd.Series(["2019-09-10", "", "nan", "banana"]))
        assert parsed.iloc[0] == pd.Timestamp("2019-09-10")
        assert parsed.iloc[1:].isna().all()

    def test_empty_series(self):
        parsed = parse_market_dates(pd.Series([], dtype="object"))
        assert len(parsed) == 0

    def test_datetime_input_passes_through(self):
        original = pd.Series(pd.date_range("2020-01-01", periods=3, freq="D"))
        parsed = parse_market_dates(original)
        assert list(parsed) == list(original)

    def test_index_is_preserved(self):
        raw = pd.Series(["2019-09-10", "2019-09-13"], index=[7, 9])
        parsed = parse_market_dates(raw)
        assert list(parsed.index) == [7, 9]

    def test_report_is_populated(self):
        report = []
        parse_market_dates(pd.Series(["2019-09-10", "2019-09-13"]), report=report)
        assert len(report) == 1
        assert report[0].parsed == 2
        assert report[0].failed == 0
        assert report[0].parse_rate == pytest.approx(1.0)


class TestRealDatasetInvariant:
    """
    Guards the specific corruption observed in production data: raw Agmarknet
    dates for onion/Lasalgaon in September 2019 must land on their own dates.
    """

    def test_september_2019_sequence(self):
        raw = pd.Series(
            [
                "2019-09-04", "2019-09-05", "2019-09-06", "2019-09-07",
                "2019-09-09", "2019-09-10", "2019-09-11", "2019-09-13",
                "2019-09-16", "2019-09-17", "2019-09-18", "2019-09-19",
                "2019-09-20",
            ]
        )
        parsed = parse_market_dates(raw)
        assert parsed.notna().all(), "no observation may be dropped"
        assert (parsed.dt.month == 9).all(), "all observations are in September"
        assert list(parsed.dt.day) == [4, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 19, 20]
