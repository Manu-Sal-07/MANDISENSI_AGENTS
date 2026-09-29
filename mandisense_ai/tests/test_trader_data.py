"""
Tests for the trader package's shared data layer (`trader/data.py`).

The properties that matter: duplicate same-day prints collapse rather than
letting whichever row sorts last win silently; forward returns resolve on
the calendar, not by row position, so a gappy series doesn't quietly borrow
tomorrow's print as "3 days out"; and the cross-mandi snapshot refuses to
compare a fresh print against a four-month-old one just because both exist
somewhere in the archive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.trader import data as trader_data

COLUMNS = [
    "date", "commodity", "mandi_id", "modal_price", "min_price", "max_price",
    "arrivals", "state", "district", "source", "ingested_at",
]


def _row(date, commodity, mandi_id, price, arrivals=100.0):
    return [date, commodity, mandi_id, price, price * 0.9, price * 1.1, arrivals, "KA", "X", "t", date]


def _write(tmp_path, rows, monkeypatch):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "observations.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr("mandisense_ai.forecasting.store.observations_path", lambda: path)
    trader_data._cache["frame"] = None
    trader_data._cache["mtime"] = None
    return path


def test_duplicate_same_day_prints_collapse_to_their_median(tmp_path, monkeypatch):
    _write(tmp_path, [
        _row("2026-01-01", "tomato", "kolar_apmc", 1000.0),
        _row("2026-01-01", "tomato", "kolar_apmc", 1200.0),
    ], monkeypatch)
    out = trader_data.series("tomato", "kolar_apmc")
    assert len(out) == 1
    assert out["price"].iloc[0] == pytest.approx(1100.0)


def test_forward_returns_resolve_on_the_calendar_not_row_position(tmp_path, monkeypatch):
    # A gap: day 1, then nothing until day 10. A positional shift(-1) would
    # treat day 10's price as "1 day out"; the calendar-correct answer is NaN.
    _write(tmp_path, [
        _row("2026-01-01", "tomato", "kolar_apmc", 1000.0),
        _row("2026-01-10", "tomato", "kolar_apmc", 1500.0),
    ], monkeypatch)
    frame = trader_data.series("tomato", "kolar_apmc")
    fwd = trader_data.forward_returns(frame, horizon_days=1)
    assert pd.isna(fwd.iloc[0])


def test_forward_returns_finds_the_print_within_tolerance(tmp_path, monkeypatch):
    _write(tmp_path, [
        _row("2026-01-01", "tomato", "kolar_apmc", 1000.0),
        _row("2026-01-04", "tomato", "kolar_apmc", 1100.0),
    ], monkeypatch)
    frame = trader_data.series("tomato", "kolar_apmc")
    fwd = trader_data.forward_returns(frame, horizon_days=3)
    assert fwd.iloc[0] == pytest.approx(np.log(1100 / 1000))


def test_snapshot_anchors_on_a_date_most_mandis_can_reach(tmp_path, monkeypatch):
    # Three mandis print through 2026-01-05; a fourth's only print is months
    # earlier. The anchor should be 2026-01-05, and the stale mandi excluded.
    rows = []
    for d in ("2026-01-01", "2026-01-03", "2026-01-05"):
        for mandi in ("kolar_apmc", "bangarpet_apmc", "hoskote_apmc"):
            rows.append(_row(d, "tomato", mandi, 1000.0))
    rows.append(_row("2025-06-01", "tomato", "anekal_apmc", 500.0))
    _write(tmp_path, rows, monkeypatch)

    snap = trader_data.snapshot("tomato", window_days=7)
    assert snap["as_of"] == "2026-01-05"
    assert set(snap["prices"]) == {"kolar_apmc", "bangarpet_apmc", "hoskote_apmc"}
    assert snap["stale"] == ["anekal_apmc"]


def test_snapshot_universe_restricts_candidates(tmp_path, monkeypatch):
    """Without a universe, a single-day nationwide ingest of hundreds of
    mandis can out-vote the handful actually tracked for arbitrage."""
    rows = [_row("2026-01-05", "tomato", "kolar_apmc", 1000.0)]
    for i in range(20):
        rows.append(_row("2026-01-05", "tomato", f"other_mandi_{i}", 900.0))
    _write(tmp_path, rows, monkeypatch)

    restricted = trader_data.snapshot("tomato", universe=["kolar_apmc"])
    assert list(restricted["prices"]) == ["kolar_apmc"]


def test_snapshot_with_no_data_reports_none_not_a_crash(tmp_path, monkeypatch):
    _write(tmp_path, [], monkeypatch)
    snap = trader_data.snapshot("tomato")
    assert snap["as_of"] is None
    assert snap["prices"] == {}


def test_move_distribution_falls_back_to_historical_returns_without_a_forecast(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "mandisense_ai.forecasting.service.get_forecast_service",
        lambda: type("S", (), {"is_available": False})(),
    )
    start = pd.Timestamp("2024-01-01")
    rows = [
        _row((start + pd.Timedelta(days=i)).strftime("%Y-%m-%d"), "tomato", "kolar_apmc",
             1000.0 * (1 + 0.001 * np.sin(i / 5)))
        for i in range(400)
    ]
    _write(tmp_path, rows, monkeypatch)

    result = trader_data.move_distribution("tomato", "kolar_apmc", horizon_days=3)
    assert result["status"] == "OK"
    assert result["method"] == "historical_returns"
    assert result["sample_size"] and result["sample_size"] > 60
    assert set(result["quantiles"]) == {"p05", "p25", "p50", "p75", "p95"}


def test_move_distribution_prefers_the_calibrated_forecast_when_available(tmp_path, monkeypatch):
    _write(tmp_path, [_row("2026-01-01", "tomato", "kolar_apmc", 1000.0)], monkeypatch)

    class _Service:
        is_available = True

        def nearest_horizon(self, commodity, mandi_id, horizon):
            return {
                "status": "OK", "horizon_days": 3, "as_of_date": "2026-01-01",
                "data_lag_days": 0, "last_observed_price": 1000.0, "forecast_price": 1020.0,
                "interval": {"p05": 900.0, "p25": 950.0, "p75": 1080.0, "p95": 1150.0},
            }

    monkeypatch.setattr("mandisense_ai.forecasting.service.get_forecast_service", lambda: _Service())
    result = trader_data.move_distribution("tomato", "kolar_apmc", horizon_days=3)
    assert result["status"] == "OK"
    assert result["method"] == "calibrated_forecast"
    assert result["sample_size"] is None
