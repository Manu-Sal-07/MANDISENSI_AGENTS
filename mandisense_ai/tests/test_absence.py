"""
Tests for panel-based informative-missingness classification.

Organised around the property the module exists for: a single series cannot
tell why a day is missing, but the panel can, because three distinct events
produce an identical hole in one series and different signatures across it.

  * the mandi transacted other commodities that day -> the absence is a real
    supply signal (NO_TRADE), not a data problem
  * the mandi printed nothing while peer mandis reported the same commodity
    -> the silence is local to that market (MANDI_SILENT)
  * almost nothing printed anywhere -> the day itself is a calendar/feed
    artifact (MARKET_WIDE), carrying no market information
  * absence features never use information from the day being described or
    after it
"""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.forecasting.absence import (
    ABSENCE_MANDI_SILENT,
    ABSENCE_MARKET_WIDE,
    ABSENCE_NO_TRADE,
    AbsenceConfig,
    build_absence_features,
    classify_absences,
    summarise,
)


def _rows(date, commodity, mandis):
    return [{"date": pd.Timestamp(date), "commodity": commodity, "mandi_id": m} for m in mandis]


def _panel(days, commodities, mandis, skip=()):
    """
    A dense daily panel over `days` for every (commodity, mandi), except the
    (date, commodity, mandi) triples listed in `skip`.
    """
    records = []
    for day in pd.date_range("2026-01-01", periods=days, freq="D"):
        for commodity in commodities:
            for mandi in mandis:
                if (day, commodity, mandi) in skip:
                    continue
                records.extend(_rows(day, commodity, [mandi]))
    return pd.DataFrame(records)


CONFIG = AbsenceConfig(peer_quorum=2, market_wide_fraction=0.5, min_series_rows=10)


class TestNoTrade:
    def test_commodity_absent_while_mandi_otherwise_open_is_no_trade(self):
        """Mandi A prints onion on day 20 but not tomato; it clearly opened
        that day, so the tomato gap is a real supply event, not a reporting
        gap."""
        target_day = pd.Timestamp("2026-01-20")
        panel = _panel(
            days=40,
            commodities=["tomato", "onion"],
            mandis=["a_apmc", "b_apmc", "c_apmc"],
            skip={(target_day, "tomato", "a_apmc")},
        )

        absences = classify_absences(panel, config=CONFIG)
        row = absences[
            (absences["mandi_id"] == "a_apmc")
            & (absences["commodity"] == "tomato")
            & (absences["date"] == target_day)
        ]

        assert len(row) == 1
        assert row.iloc[0]["absence_type"] == ABSENCE_NO_TRADE


class TestMandiSilent:
    def test_mandi_closed_while_peers_report_same_commodity_is_mandi_silent(self):
        """Mandi A reports nothing at all on day 20, while B and C both print
        tomato as usual. The silence is specific to A, not the market."""
        target_day = pd.Timestamp("2026-01-20")
        mandis = ["a_apmc", "b_apmc", "c_apmc", "d_apmc", "e_apmc"]
        skip = {(target_day, commodity, "a_apmc") for commodity in ("tomato", "onion")}

        panel = _panel(days=40, commodities=["tomato", "onion"], mandis=mandis, skip=skip)

        absences = classify_absences(panel, config=CONFIG)
        row = absences[
            (absences["mandi_id"] == "a_apmc")
            & (absences["commodity"] == "tomato")
            & (absences["date"] == target_day)
        ]

        assert len(row) == 1
        assert row.iloc[0]["absence_type"] == ABSENCE_MANDI_SILENT


class TestMarketWide:
    def test_day_wide_outage_is_market_wide_not_attributed_to_any_series(self):
        """Almost nothing prints anywhere on day 20 (a holiday, a feed
        outage) -- every series' gap that day is the same calendar artifact,
        not an independent market event, and should be labelled as such."""
        target_day = pd.Timestamp("2026-01-20")
        commodities = ["tomato", "onion"]
        mandis = ["a_apmc", "b_apmc", "c_apmc", "d_apmc", "e_apmc"]
        skip = {(target_day, c, m) for c in commodities for m in mandis}

        panel = _panel(days=40, commodities=commodities, mandis=mandis, skip=skip)

        absences = classify_absences(panel, config=CONFIG)
        day_rows = absences[absences["date"] == target_day]

        assert len(day_rows) == len(commodities) * len(mandis)
        assert set(day_rows["absence_type"]) == {ABSENCE_MARKET_WIDE}

    def test_short_series_is_not_classified(self):
        """A series with fewer than `min_series_rows` observations has no
        stable notion of an expected trading day; classifying its gaps would
        be a guess dressed up as a finding."""
        config = AbsenceConfig(peer_quorum=2, market_wide_fraction=0.5, min_series_rows=100)
        panel = _panel(days=15, commodities=["tomato"], mandis=["a_apmc", "b_apmc"])
        # Introduce one gap so there is something that *would* be classified
        # if the series passed the length gate.
        panel = panel[~((panel["date"] == pd.Timestamp("2026-01-05")) & (panel["mandi_id"] == "a_apmc"))]

        absences = classify_absences(panel, config=config)
        assert absences.empty


class TestSummary:
    def test_summary_counts_match_classification(self):
        target_day = pd.Timestamp("2026-01-20")
        panel = _panel(
            days=40,
            commodities=["tomato"],
            mandis=["a_apmc", "b_apmc", "c_apmc"],
            skip={(target_day, "tomato", "a_apmc")},
        )
        absences = classify_absences(panel, config=CONFIG)
        summary = summarise(absences)

        assert summary["total"] == len(absences)
        assert sum(summary["by_type"].values()) == len(absences)

    def test_empty_panel_summarises_to_zero(self):
        summary = summarise(pd.DataFrame(columns=["commodity", "mandi_id", "date", "absence_type"]))
        assert summary == {"total": 0, "by_type": {}}


class TestFeaturesAreNotLookingAhead:
    def test_no_trade_count_excludes_the_current_row(self):
        """The window for `no_trade_30` ends the day *before* the row it is
        attached to -- an absence on the row's own date must never count
        towards its own feature."""
        commodities = ["tomato", "onion"]
        mandis = ["a_apmc", "b_apmc", "c_apmc"]
        target_day = pd.Timestamp("2026-01-25")
        # Tomato is absent at mandi A exactly on `target_day`, and observed
        # every other day, including the day the feature is read for.
        skip = {(target_day, "tomato", "a_apmc")}
        panel = _panel(days=40, commodities=commodities, mandis=mandis, skip=skip)

        featured = build_absence_features(panel, config=CONFIG)
        next_day_row = featured[
            (featured["commodity"] == "tomato")
            & (featured["mandi_id"] == "a_apmc")
            & (featured["date"] == target_day + pd.Timedelta(days=1))
        ]

        assert len(next_day_row) == 1
        # The absence on `target_day` happened strictly before this row's
        # date, so it must be counted in the trailing window...
        assert next_day_row.iloc[0]["no_trade_30"] >= 1.0

        same_day_row = featured[
            (featured["commodity"] == "tomato")
            & (featured["mandi_id"] == "a_apmc")
            & (featured["date"] == target_day - pd.Timedelta(days=1))
        ]
        # ...but a row dated strictly before the absence cannot have seen it.
        assert len(same_day_row) == 1
        assert same_day_row.iloc[0]["no_trade_30"] == 0.0

    def test_first_observation_of_a_series_has_no_prior_absence_to_report(self):
        panel = _panel(days=40, commodities=["tomato"], mandis=["a_apmc", "b_apmc", "c_apmc"])
        featured = build_absence_features(panel, config=CONFIG)

        first_row = featured[featured["mandi_id"] == "a_apmc"].sort_values("date").iloc[0]
        assert first_row["no_trade_30"] == 0.0
        assert first_row["prev_gap_no_trade"] == 0.0

    def test_dense_series_has_full_report_rate(self):
        panel = _panel(days=40, commodities=["tomato"], mandis=["a_apmc", "b_apmc", "c_apmc"])
        featured = build_absence_features(panel, config=CONFIG)

        assert (featured["report_rate_90"] == 1.0).all()

    def test_all_feature_columns_are_attached(self):
        panel = _panel(days=40, commodities=["tomato"], mandis=["a_apmc", "b_apmc", "c_apmc"])
        featured = build_absence_features(panel, config=CONFIG)

        for column in ("no_trade_30", "mandi_silent_30", "prev_gap_no_trade", "report_rate_90"):
            assert column in featured.columns
        assert len(featured) == len(panel)
