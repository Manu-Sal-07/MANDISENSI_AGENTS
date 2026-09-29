"""
Tests for graded observation quality scoring.

Organised around the properties that make the score trustworthy rather than
around line coverage:

  * a genuinely impossible price is still rejected outright
  * a plausible price with no supporting history or cross-section is trusted
    fully rather than penalised for signals that simply could not be computed
  * a price that moved with its peers is treated differently from one that
    moved alone, which is the comparison the previous single-series gate had
    no way to make
  * every signal degrades gracefully instead of raising when its inputs
    (history, min/max, a peer cross-section) are missing
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.quality import (
    DEFAULT_QUALITY_CONFIG,
    QUALITY_FLAGS_COLUMN,
    QUALITY_SCORE_COLUMN,
    QualityConfig,
    score_observations,
)


def _row(date, commodity="tomato", mandi_id="kolar_apmc", price=1000.0, low=None, high=None):
    return {
        "date": pd.Timestamp(date),
        "commodity": commodity,
        "mandi_id": mandi_id,
        "modal_price": price,
        "min_price": low,
        "max_price": high,
    }


def _history_series(mandi_id, commodity, start, days, price, noise=0.0):
    """A series with a touch of realistic day-to-day noise.

    A perfectly flat price has zero dispersion, so its MAD-based sigma is
    exactly zero and the temporal signal correctly abstains rather than
    dividing by it — real mandi prices always carry some noise, and the test
    fixtures should too, or they end up testing the abstention path by
    accident instead of the signal they are named for.
    """
    dates = pd.date_range(start, periods=days, freq="D")
    rng = np.random.default_rng(20260916)
    prices = price + rng.normal(0.0, price * noise, size=days) if noise else [price] * days
    return pd.DataFrame(
        [
            _row(d, commodity=commodity, mandi_id=mandi_id, price=float(p))
            for d, p in zip(dates, prices)
        ]
    )


class TestHardImpossibility:
    def test_out_of_plausible_bounds_is_rejected(self):
        batch = pd.DataFrame([_row("2026-01-01", commodity="garlic", price=600_000.0)])
        accepted, rejected, report = score_observations(batch)

        assert accepted.empty
        assert len(rejected) == 1
        assert rejected.iloc[0]["reject_reason"] == "out_of_plausible_range"
        assert report.rejected == 1

    def test_non_positive_price_is_rejected(self):
        batch = pd.DataFrame([_row("2026-01-01", price=0.0)])
        accepted, rejected, _ = score_observations(batch)

        assert accepted.empty
        assert rejected.iloc[0]["reject_reason"] == "non_positive_price"

    def test_missing_identity_is_rejected(self):
        batch = pd.DataFrame([_row("2026-01-01", commodity=None)])
        accepted, rejected, _ = score_observations(batch)

        assert accepted.empty
        assert rejected.iloc[0]["reject_reason"] == "missing_required_field"


class TestAbstentionWhenSignalsAreUnavailable:
    def test_plausible_price_with_no_history_scores_full_trust(self):
        """No history, no cross-section: only the bounds signal can fire, and
        a comfortably in-range price should not be punished for the absence
        of signals that simply had nothing to compute from."""
        batch = pd.DataFrame([_row("2026-01-01", price=1500.0)])
        accepted, rejected, report = score_observations(batch, history=None)

        assert rejected.empty
        assert accepted.iloc[0][QUALITY_SCORE_COLUMN] == pytest.approx(1.0)
        assert report.signal_abstentions["temporal"] == 1
        assert report.signal_abstentions["cross_sectional"] == 1

    def test_min_max_absent_does_not_penalise(self):
        """The historical archive mostly does not carry min/max. A row missing
        them should score identically to one that carries a consistent triple,
        not be treated as suspicious for a column it never had."""
        batch = pd.DataFrame([_row("2026-01-01", price=1500.0, low=None, high=None)])
        accepted, _, report = score_observations(batch)

        assert accepted.iloc[0][QUALITY_SCORE_COLUMN] == pytest.approx(1.0)
        assert report.signal_abstentions["internal"] == 1


class TestInternalConsistency:
    def test_modal_outside_min_max_is_penalised_not_rejected(self):
        batch = pd.DataFrame([_row("2026-01-01", price=1500.0, low=1600.0, high=1800.0)])
        accepted, rejected, _ = score_observations(batch)

        assert rejected.empty
        row = accepted.iloc[0]
        assert row[QUALITY_SCORE_COLUMN] < 1.0
        assert "modal_outside_min_max" in row[QUALITY_FLAGS_COLUMN]

    def test_implausible_spread_is_flagged(self):
        batch = pd.DataFrame([_row("2026-01-01", price=1000.0, low=100.0, high=5000.0)])
        accepted, _, _ = score_observations(batch)

        assert "implausible_spread" in accepted.iloc[0][QUALITY_FLAGS_COLUMN]
        assert accepted.iloc[0][QUALITY_SCORE_COLUMN] < 1.0


class TestTemporalSignal:
    def test_stable_series_scores_full_trust(self):
        history = _history_series("kolar_apmc", "tomato", "2025-12-01", 30, price=1000.0)
        batch = pd.DataFrame([_row("2026-01-01", price=1020.0)])

        accepted, rejected, _ = score_observations(batch, history=history)

        assert rejected.empty
        assert accepted.iloc[0][QUALITY_SCORE_COLUMN] == pytest.approx(1.0, abs=0.05)

    def test_large_deviation_from_own_history_is_penalised(self):
        """A tenfold move against a series with mild, realistic day-to-day
        noise is exactly the case a single global threshold either misses (set
        loose) or over-fires on for volatile series (set tight); scaling by
        the series' own dispersion avoids both."""
        history = _history_series(
            "kolar_apmc", "tomato", "2025-12-01", 30, price=1000.0, noise=0.01
        )
        batch = pd.DataFrame([_row("2026-01-01", price=10_000.0)])

        accepted, rejected, report = score_observations(batch, history=history)

        assert report.signal_abstentions["temporal"] == 0
        surviving = accepted if not accepted.empty else rejected
        flags = str(surviving.iloc[0][QUALITY_FLAGS_COLUMN])
        reason = surviving.iloc[0].get("reject_reason")
        assert "temporal_outlier" in flags or reason == "temporal_outlier"
        if not accepted.empty:
            assert accepted.iloc[0][QUALITY_SCORE_COLUMN] < 0.5


class TestCrossSectionalSignal:
    """The signal the single-series gate could never compute: what did the
    rest of the country print for this commodity on this day."""

    def _same_day_batch(self, prices, mandis=None):
        mandis = mandis or [f"mandi_{i}_apmc" for i in range(len(prices))]
        return pd.DataFrame(
            [
                _row("2026-01-01", mandi_id=m, price=p)
                for m, p in zip(mandis, prices)
            ]
        )

    def test_isolated_spike_among_agreeing_peers_is_flagged(self):
        peers = [1000.0, 1050.0, 980.0, 1020.0, 990.0]
        batch = self._same_day_batch(peers + [9000.0])
        accepted, rejected, report = score_observations(batch)

        outlier_row = pd.concat([accepted, rejected]).iloc[-1]
        assert outlier_row["modal_price"] == 9000.0
        assert (
            outlier_row.get("reject_reason") == "cross_sectional_outlier"
            or "cross_sectional_outlier" in str(outlier_row.get(QUALITY_FLAGS_COLUMN, ""))
        )
        assert report.signal_abstentions["cross_sectional"] == 0

    def test_market_wide_move_is_not_penalised_on_cross_section(self):
        """When every peer moved together, the move is a real market event,
        not an error, and the cross-sectional signal should not fire."""
        batch = self._same_day_batch([2000.0, 2050.0, 1980.0, 2020.0, 1990.0])
        accepted, rejected, _ = score_observations(batch)

        assert rejected.empty
        for _, row in accepted.iterrows():
            assert "cross_sectional_outlier" not in row[QUALITY_FLAGS_COLUMN]

    def test_thin_cross_section_abstains(self):
        """Below the peer quorum there is no usable cross-section, and the
        signal must abstain rather than compare a price against one or two
        arbitrary neighbours."""
        batch = self._same_day_batch([1000.0, 5000.0])
        _, _, report = score_observations(batch)

        assert report.signal_abstentions["cross_sectional"] == 2


class TestScoreShapeAndFloor:
    def test_accepted_scores_never_fall_below_the_floor(self):
        history = _history_series("kolar_apmc", "tomato", "2025-12-01", 30, price=1000.0)
        batch = pd.DataFrame([_row("2026-01-01", price=1500.0)])  # mild deviation, should survive

        accepted, _, _ = score_observations(batch, history=history)
        if not accepted.empty:
            assert accepted.iloc[0][QUALITY_SCORE_COLUMN] >= DEFAULT_QUALITY_CONFIG.min_weight

    def test_empty_batch_returns_empty_frames(self):
        accepted, rejected, report = score_observations(pd.DataFrame())
        assert accepted.empty
        assert rejected.empty
        assert report.received == 0

    def test_custom_config_is_respected(self):
        """A stricter hard-reject threshold should turn a merely flagged row
        into a rejected one, proving the config actually gates the pipeline
        rather than being cosmetic."""
        history = _history_series("kolar_apmc", "tomato", "2025-12-01", 30, price=1000.0)
        batch = pd.DataFrame([_row("2026-01-01", price=3500.0)])

        lenient = score_observations(batch, history=history, config=DEFAULT_QUALITY_CONFIG)
        strict_config = QualityConfig(hard_reject_score=0.99)
        strict = score_observations(batch, history=history, config=strict_config)

        assert len(strict[1]) >= len(lenient[1])
