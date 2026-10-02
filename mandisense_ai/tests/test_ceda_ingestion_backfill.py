"""
Tests for `pipeline._backfill_arrivals_from_ceda` -- the ingestion-time
wiring that lets CEDA fill in arrival volumes the free data.gov.in feed
never carries, without ever touching the prices that feed already supplies.

No key exists yet: every test drives `ceda.fetch_daily_prices_and_arrivals`
through a monkeypatch, exactly as `test_ceda_source.py` drives the client
itself through a fake transport. What matters here is the *merge* logic --
arrivals only, never overwriting, never raising into the caller.
"""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.forecasting.pipeline import _backfill_arrivals_from_ceda
from mandisense_ai.forecasting.sources import ceda


def _fetched(rows):
    return pd.DataFrame(rows, columns=["date", "commodity", "mandi_id", "modal_price", "arrivals"])


def test_is_a_no_op_when_ceda_is_not_configured(monkeypatch):
    monkeypatch.delenv("CEDA_API_KEY", raising=False)
    fetched = _fetched([["2026-01-01", "tomato", "kolar_apmc", 1000.0, None]])

    result = _backfill_arrivals_from_ceda(fetched)

    assert result["status"] == "NOT_CONFIGURED"
    assert fetched["arrivals"].isna().all()  # untouched


def test_fills_a_missing_arrival_from_ceda(monkeypatch):
    monkeypatch.setenv("CEDA_API_KEY", "x")
    fetched = _fetched([["2026-01-01", "tomato", "kolar_apmc", 1000.0, None]])

    ceda_frame = pd.DataFrame([{
        "date": pd.Timestamp("2026-01-01"), "commodity": "tomato",
        "mandi_id": "kolar_apmc", "arrivals": 250.0,
    }])
    monkeypatch.setattr(
        ceda, "fetch_daily_prices_and_arrivals", lambda *a, **k: ceda_frame
    )

    result = _backfill_arrivals_from_ceda(fetched)

    assert result == {"status": "OK", "matched": 1}
    assert fetched["arrivals"].iloc[0] == 250.0


def test_never_overwrites_an_arrival_the_price_feed_already_had(monkeypatch):
    """Guards a real future risk: if the free feed ever starts publishing
    arrivals itself, CEDA must not silently override an established number."""
    monkeypatch.setenv("CEDA_API_KEY", "x")
    fetched = _fetched([["2026-01-01", "tomato", "kolar_apmc", 1000.0, 999.0]])

    ceda_frame = pd.DataFrame([{
        "date": pd.Timestamp("2026-01-01"), "commodity": "tomato",
        "mandi_id": "kolar_apmc", "arrivals": 250.0,
    }])
    monkeypatch.setattr(
        ceda, "fetch_daily_prices_and_arrivals", lambda *a, **k: ceda_frame
    )

    result = _backfill_arrivals_from_ceda(fetched)

    assert result == {"status": "OK", "matched": 0}
    assert fetched["arrivals"].iloc[0] == 999.0


def test_a_row_with_no_matching_ceda_date_stays_missing(monkeypatch):
    monkeypatch.setenv("CEDA_API_KEY", "x")
    fetched = _fetched([["2026-01-01", "tomato", "kolar_apmc", 1000.0, None]])
    monkeypatch.setattr(
        ceda, "fetch_daily_prices_and_arrivals", lambda *a, **k: pd.DataFrame()
    )

    result = _backfill_arrivals_from_ceda(fetched)

    assert result == {"status": "OK", "matched": 0}
    assert fetched["arrivals"].isna().all()


def test_a_ceda_failure_is_caught_and_never_raised(monkeypatch):
    """A CEDA outage or a bad key must never take down the price ingestion
    this system already depends on."""
    monkeypatch.setenv("CEDA_API_KEY", "x")
    fetched = _fetched([["2026-01-01", "tomato", "kolar_apmc", 1000.0, None]])

    def boom(*a, **k):
        raise ceda.CedaFetchError("down")

    monkeypatch.setattr(ceda, "fetch_daily_prices_and_arrivals", boom)

    result = _backfill_arrivals_from_ceda(fetched)  # must not raise
    assert result["status"] == "ERROR"
    assert fetched["arrivals"].isna().all()
