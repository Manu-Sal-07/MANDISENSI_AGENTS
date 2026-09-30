"""
Tests for Fair Price Check.

The property that matters: an offer is judged against what actually printed
today (or a forecast band, when one exists), never fabricated when neither
exists.
"""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.farmer.fair_price import _verdict_bucket, check_offer

COLUMNS = ["date", "commodity", "mandi_id", "district", "min_price", "modal_price", "max_price", "arrivals"]


def _write_observations(tmp_path, rows):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame["date"] = pd.to_datetime(frame["date"])
    path = tmp_path / "mandi_prices.parquet"
    frame.to_parquet(path, index=False)
    return path


def _row(date, price, low=None, high=None):
    return [
        date, "tomato", "kolar_apmc", "kolar",
        low if low is not None else price * 0.9, price,
        high if high is not None else price * 1.1, 100.0,
    ]


@pytest.fixture(autouse=True)
def _patch_observation_store(tmp_path, monkeypatch):
    path = _write_observations(tmp_path, [_row("2026-09-20", 2000.0, 1800.0, 2200.0)])
    monkeypatch.setattr("mandisense_ai.farmer.world.MANDI_PRICES", path)
    # No forecast service configured in these tests unless explicitly patched.
    monkeypatch.setattr(
        "mandisense_ai.farmer.world.forecast_service",
        lambda: _NoForecastService(),
    )


class _NoForecastService:
    is_available = False


# ── verdict bucketing (pure function) ──────────────────────────────────────


def test_offer_at_the_low_edge_reads_as_a_little_below():
    """Exactly at the day's printed minimum is not mid-range -- it is the
    worst real trade of the day, so it should read as below, not fair."""
    assert _verdict_bucket(1800.0, 1800.0, 2200.0) == "below"


def test_offer_well_below_range_is_flagged():
    assert _verdict_bucket(1200.0, 1800.0, 2200.0) == "well_below"


def test_offer_well_above_range_is_flagged():
    assert _verdict_bucket(2800.0, 1800.0, 2200.0) == "well_above"


def test_offer_in_the_middle_is_fair():
    assert _verdict_bucket(2000.0, 1800.0, 2200.0) == "fair"


def test_degenerate_zero_width_range_never_crashes():
    assert _verdict_bucket(2000.0, 2000.0, 2000.0) == "fair"


# ── end-to-end check_offer ─────────────────────────────────────────────────


def test_offer_below_todays_range_is_flagged_low():
    result = check_offer("tomato", "kolar_apmc", 1000.0)
    assert result["status"] == "OK"
    assert result["verdict"] in ("well_below", "below")
    assert result["observed"]["range_low"] == pytest.approx(1800.0)
    assert result["observed"]["range_high"] == pytest.approx(2200.0)


def test_offer_within_range_is_fair():
    result = check_offer("tomato", "kolar_apmc", 2000.0)
    assert result["verdict"] == "fair"


def test_quantity_computes_total_difference():
    result = check_offer("tomato", "kolar_apmc", 1900.0, quantity_quintals=10)
    assert result["quantity_quintals"] == 10
    assert result["offered_total"] == pytest.approx(19000.0)
    assert result["typical_total"] == pytest.approx(20000.0)
    assert result["difference"] == pytest.approx(-1000.0)


def test_unknown_series_is_unavailable_not_fabricated():
    result = check_offer("onion", "lasalgaon_apmc", 1500.0)
    assert result["status"] == "UNAVAILABLE"
    assert "reason" in result


def test_no_forecast_service_still_returns_observed_reading():
    """Fair Price Check must work even when nothing is forecastable yet --
    that is the whole point of grounding it in observed trades first."""
    result = check_offer("tomato", "kolar_apmc", 2000.0)
    assert result["status"] == "OK"
    assert result["forecast"] is None
    assert result["observed"] is not None
