"""
Tests for Track Record, This-Time-Last-Year, Supply Flood Warning and the
seasonal crop-planning comparison.
"""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.farmer.crop_planning import seasonal_crop_comparison
from mandisense_ai.farmer.seasonal_memory import seasonal_reading
from mandisense_ai.farmer.supply_signal import supply_reading
from mandisense_ai.farmer.track_record import track_record
from mandisense_ai.forecasting.ledger import MIN_SCORED_FOR_RATE, ForecastLedger

COLUMNS = [
    "date", "commodity", "mandi_id", "modal_price", "min_price", "max_price",
    "arrivals", "state", "district", "source", "ingested_at",
]


def _write_observations(tmp_path, rows):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "observations.parquet"
    frame.to_parquet(path, index=False)
    return path


@pytest.fixture
def patch_observations(tmp_path, monkeypatch):
    def _apply(rows):
        path = _write_observations(tmp_path, rows)
        monkeypatch.setattr("mandisense_ai.forecasting.store.observations_path", lambda: path)
        return path

    return _apply


# ── track record ────────────────────────────────────────────────────────────


def test_track_record_reports_insufficient_evidence_below_the_minimum(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "mandisense_ai.forecasting.ledger.ledger_path", lambda: tmp_path / "ledger.parquet"
    )
    result = track_record("tomato", "kolar_apmc")
    assert result["status"] == "NO_RECORDS"
    assert result["commodity"] == "tomato"
    assert result["mandi_id"] == "kolar_apmc"


def test_track_record_is_scoped_to_one_series_not_the_whole_system(tmp_path, monkeypatch):
    """The system-wide ledger might have plenty of scored rows for other
    series; a series with none of its own must still say so."""
    ledger_path = tmp_path / "ledger.parquet"
    # `ledger.py` does `from ...config import ledger_path`, which copies the
    # reference at import time -- patching the config module's attribute
    # after that has no effect, so the name has to be patched where it was
    # bound to be observed. `track_record()` constructs its own
    # `ForecastLedger()` with no path, so this is what makes it read the
    # same file this test writes to.
    monkeypatch.setattr("mandisense_ai.forecasting.ledger.ledger_path", lambda: ledger_path)

    ledger = ForecastLedger(path=ledger_path)

    class _FakeStore:
        def __init__(self, forecasts):
            self.forecasts = forecasts

    start = pd.Timestamp("2026-01-01")
    rows = []
    for i in range(MIN_SCORED_FOR_RATE):
        as_of = (start + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        target = (start + pd.Timedelta(days=i + 3)).strftime("%Y-%m-%d")
        rows.append({
            "status": "OK", "as_of_date": as_of, "commodity": "onion",
            "mandi_id": "lasalgaon_apmc", "horizon_days": 3, "target_date": target,
            "last_observed_price": 1000.0, "forecast_price": 950.0,
            "expected_change_pct": -5.0, "direction": "down",
            "interval": {"p05": 900.0, "p25": 930.0, "p75": 970.0, "p95": 1000.0},
            "decision": "SELL", "decision_probability_of_decline": 0.7,
        })
    ledger.record_publication(_FakeStore(rows))
    observations = pd.DataFrame([
        {
            "date": (start + pd.Timedelta(days=i + 3)).strftime("%Y-%m-%d"),
            "commodity": "onion", "mandi_id": "lasalgaon_apmc", "modal_price": 900.0,
        }
        for i in range(MIN_SCORED_FOR_RATE)
    ])
    ledger.score_pending(observations)

    onion_result = track_record("onion", "lasalgaon_apmc")
    assert onion_result["status"] == "OK"

    # The ledger is non-empty (it holds onion's rows), so this is
    # INSUFFICIENT_EVIDENCE (0 scored rows for this series) rather than
    # NO_RECORDS (which only applies to an empty ledger file).
    tomato_result = track_record("tomato", "kolar_apmc")
    assert tomato_result["status"] == "INSUFFICIENT_EVIDENCE"
    assert tomato_result["scored"] == 0


# ── seasonal memory ─────────────────────────────────────────────────────────


def test_seasonal_memory_unavailable_for_untracked_series(patch_observations):
    patch_observations([])
    result = seasonal_reading("tomato", "kolar_apmc")
    assert result["status"] == "UNAVAILABLE"


def test_seasonal_memory_finds_the_closest_anniversary_print(patch_observations):
    rows = [
        ["2025-06-15", "tomato", "kolar_apmc", 1500.0, 1400.0, 1600.0, 100.0, "KA", "X", "t", "2025-06-15"],
        ["2026-06-14", "tomato", "kolar_apmc", 1800.0, 1700.0, 1900.0, 100.0, "KA", "X", "t", "2026-06-14"],
    ]
    patch_observations(rows)
    result = seasonal_reading("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    assert result["last_year"] is not None
    assert result["last_year"]["price"] == pytest.approx(1500.0)
    assert result["last_year"]["change_pct"] == pytest.approx((1800 - 1500) / 1500 * 100)


def test_seasonal_memory_has_no_last_year_entry_with_only_one_years_data(patch_observations):
    rows = [["2026-06-14", "tomato", "kolar_apmc", 1800.0, 1700.0, 1900.0, 100.0, "KA", "X", "t", "2026-06-14"]]
    patch_observations(rows)
    result = seasonal_reading("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    assert result["last_year"] is None


# ── supply signal ───────────────────────────────────────────────────────────


def test_supply_signal_unavailable_without_arrivals(patch_observations):
    rows = [["2026-06-14", "tomato", "kolar_apmc", 1800.0, 1700.0, 1900.0, None, "KA", "X", "t", "2026-06-14"]]
    patch_observations(rows)
    result = supply_reading("tomato", "kolar_apmc")
    assert result["status"] == "UNAVAILABLE"


def test_supply_signal_flags_a_flood_from_elevated_arrivals(patch_observations):
    import datetime

    base = datetime.date(2026, 1, 1)
    rows = []
    for i in range(35):
        d = (base + datetime.timedelta(days=i)).isoformat()
        arrivals = 500.0 if i < 34 else 900.0  # a clear spike on the last day
        rows.append([d, "tomato", "kolar_apmc", 1500.0, 1400.0, 1600.0, arrivals, "KA", "X", "t", d])
    patch_observations(rows)

    result = supply_reading("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    assert result["signal"] == "FLOOD"
    assert result["deviation_pct"] > 30


def test_supply_signal_reports_normal_for_typical_arrivals(patch_observations):
    import datetime

    base = datetime.date(2026, 1, 1)
    rows = []
    for i in range(35):
        d = (base + datetime.timedelta(days=i)).isoformat()
        rows.append([d, "tomato", "kolar_apmc", 1500.0, 1400.0, 1600.0, 500.0, "KA", "X", "t", d])
    patch_observations(rows)

    result = supply_reading("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    assert result["signal"] == "NORMAL"


# ── crop planning ────────────────────────────────────────────────────────────


def test_crop_planning_requires_multi_year_history(patch_observations):
    patch_observations([])
    result = seasonal_crop_comparison("kolar_apmc", target_month=6)
    assert result["status"] == "UNAVAILABLE"


def test_crop_planning_rejects_an_invalid_month():
    result = seasonal_crop_comparison("kolar_apmc", target_month=13)
    assert result["status"] == "ERROR"


def test_crop_planning_labels_itself_as_historical_not_a_forecast(patch_observations):
    import datetime

    rows = []
    for year in (2023, 2024, 2025):
        for month in range(1, 13):
            for day in (5, 15, 25):
                d = datetime.date(year, month, day).isoformat()
                # Tomato is seasonally strong in June (price 1.5x its own
                # yearly mean), flat everywhere else.
                price = 1500.0 if month == 6 else 1000.0
                rows.append([d, "tomato", "kolar_apmc", price, price * 0.9, price * 1.1, 100.0, "KA", "X", "t", d])
    patch_observations(rows)

    result = seasonal_crop_comparison("kolar_apmc", target_month=6)
    assert result["status"] == "OK"
    assert "not a forecast" in result["disclaimer"]
    tomato = next(c for c in result["crops"] if c["commodity"] == "tomato")
    assert tomato["avg_deviation_from_own_yearly_mean_pct"] > 0
