"""
Tests for volatility regimes, historical analogs, and evidence-based
scenarios -- the three modules replacing panels that were previously either
permanently empty (analogs, regime timeline) or hand-written formulas
(counterfactual scenarios) in the trader frontend.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mandisense_ai.trader import data as trader_data
from mandisense_ai.trader.analogs import find_analogs
from mandisense_ai.trader.scenarios import SCENARIOS, run_scenario
from mandisense_ai.trader.volatility import volatility_profile

COLUMNS = [
    "date", "commodity", "mandi_id", "modal_price", "min_price", "max_price",
    "arrivals", "state", "district", "source", "ingested_at",
]


def _row(date, price, arrivals=100.0, commodity="tomato", mandi_id="kolar_apmc"):
    return [date, commodity, mandi_id, price, price * 0.9, price * 1.1, arrivals, "KA", "X", "t", date]


def _write(tmp_path, rows, monkeypatch):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "observations.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr("mandisense_ai.forecasting.store.observations_path", lambda: path)
    trader_data._cache["frame"] = None
    trader_data._cache["mtime"] = None


def _flat_series(n, start="2023-01-01", price=1000.0, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq="D")
    prices = price * (1 + np.cumsum(rng.normal(0, noise, n))) if noise else np.full(n, price)
    return [_row(d.strftime("%Y-%m-%d"), float(p)) for d, p in zip(dates, prices)]


# -- volatility --------------------------------------------------------------


def test_volatility_needs_a_minimum_history(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(30), monkeypatch)
    result = volatility_profile("tomato", "kolar_apmc")
    assert result["status"] == "INSUFFICIENT_HISTORY"


def test_a_flat_series_is_calm_not_turbulent(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(400, noise=0.0), monkeypatch)
    result = volatility_profile("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    # A perfectly flat series has zero volatility throughout; nothing should
    # register as an elevated regime relative to its own (zero) history.
    assert result["regime_share"]["TURBULENT"] == 0.0


def test_a_short_spike_against_a_long_calm_history_reads_as_turbulent(tmp_path, monkeypatch):
    """A brief spike is exceptional against a long calm baseline and must
    be flagged -- the case a fixed threshold or a short lookback would miss
    if it under- or over-fit to recent noise."""
    rng = np.random.default_rng(3)
    calm = 1000 * (1 + np.cumsum(rng.normal(0, 0.002, 900)))
    spike = calm[-1] * (1 + np.cumsum(rng.normal(0, 0.05, 20)))
    prices = np.concatenate([calm, spike])
    dates = pd.date_range("2022-01-01", periods=len(prices), freq="D")
    rows = [_row(d.strftime("%Y-%m-%d"), float(p)) for d, p in zip(dates, prices)]
    _write(tmp_path, rows, monkeypatch)

    result = volatility_profile("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    assert result["current_regime"] == "TURBULENT"


def test_regime_is_expanding_so_a_long_sustained_turbulence_stops_looking_exceptional(tmp_path, monkeypatch):
    """The flip side of the property above, and why this is an *expanding*
    percentile rather than a fixed threshold: once an elevated-volatility
    regime has persisted long enough to dominate its own history, later days
    within it are no longer exceptional *relative to that history* -- the
    turbulence has become the new normal for this series. A fixed
    volatility cutoff would keep flagging it forever; this should not."""
    rng = np.random.default_rng(3)
    calm = 1000 * (1 + np.cumsum(rng.normal(0, 0.002, 300)))
    sustained = calm[-1] * (1 + np.cumsum(rng.normal(0, 0.05, 100)))
    prices = np.concatenate([calm, sustained])
    dates = pd.date_range("2023-01-01", periods=len(prices), freq="D")
    rows = [_row(d.strftime("%Y-%m-%d"), float(p)) for d, p in zip(dates, prices)]
    _write(tmp_path, rows, monkeypatch)

    result = volatility_profile("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    assert result["current_regime"] != "TURBULENT"


def test_windows_report_where_current_volatility_sits_in_its_own_history(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(400, noise=0.02, seed=5), monkeypatch)
    result = volatility_profile("tomato", "kolar_apmc")
    assert result["status"] == "OK"
    for w in ("10", "20", "60"):
        assert result["windows"][w]["current_daily_pct"] is not None
        assert 0 <= result["windows"][w]["percentile"] <= 100


# -- analogs -------------------------------------------------------------


def test_analogs_need_enough_history(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(50), monkeypatch)
    result = find_analogs("tomato", "kolar_apmc")
    assert result["status"] == "INSUFFICIENT_HISTORY"


def test_analogs_are_not_drawn_from_overlapping_windows(tmp_path, monkeypatch):
    rng = np.random.default_rng(7)
    n = 900
    prices = 1000 * (1 + np.cumsum(rng.normal(0, 0.01, n)))
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    rows = [_row(d.strftime("%Y-%m-%d"), float(p)) for d, p in zip(dates, prices)]
    _write(tmp_path, rows, monkeypatch)

    result = find_analogs("tomato", "kolar_apmc", window=30, horizon_days=5, top_k=15)
    if result["status"] == "OK":
        ends = sorted(
            pd.Timestamp(a["end"]) for a in result["analogs"]
        )
        gaps = [(b - a).days for a, b in zip(ends, ends[1:])]
        assert all(g >= 15 for g in gaps), "analog windows must not overlap each other"


def test_analogs_report_a_baseline_alongside_the_outcome(tmp_path, monkeypatch):
    rng = np.random.default_rng(9)
    n = 900
    prices = 1000 * (1 + np.cumsum(rng.normal(0, 0.01, n)))
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    rows = [_row(d.strftime("%Y-%m-%d"), float(p)) for d, p in zip(dates, prices)]
    _write(tmp_path, rows, monkeypatch)

    result = find_analogs("tomato", "kolar_apmc")
    if result["status"] == "OK":
        assert "baseline" in result
        assert result["baseline"]["n"] > result["outcome"]["n"]


# -- scenarios -------------------------------------------------------------


def test_scenario_requires_a_valid_name(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(300), monkeypatch)
    result = run_scenario("tomato", "kolar_apmc", "not_a_real_scenario")
    assert result["status"] == "ERROR"


def test_arrivals_scenario_is_unavailable_without_arrival_data(tmp_path, monkeypatch):
    rows = _flat_series(300)
    for r in rows:
        r[6] = None  # arrivals column
    _write(tmp_path, rows, monkeypatch)
    result = run_scenario("tomato", "kolar_apmc", "arrival_surge")
    assert result["status"] == "UNAVAILABLE"


def test_price_rally_finds_episodes_when_price_actually_rallies(tmp_path, monkeypatch):
    # A base series with periodic sharp 5-day rallies of >10%.
    n = 600
    prices = [1000.0]
    for i in range(1, n):
        if i % 40 in (0, 1, 2, 3, 4):
            prices.append(prices[-1] * 1.03)
        else:
            prices.append(prices[-1] * 0.999)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    rows = [_row(d.strftime("%Y-%m-%d"), p) for d, p in zip(dates, prices)]
    _write(tmp_path, rows, monkeypatch)

    result = run_scenario("tomato", "kolar_apmc", "price_rally", horizon_days=5)
    assert result["status"] in ("OK", "INSUFFICIENT_EVIDENCE")
    if result["status"] == "OK":
        assert result["episodes"] >= 8


def test_scenario_result_always_carries_the_disclaimer(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(300), monkeypatch)
    result = run_scenario("tomato", "kolar_apmc", "price_slump")
    assert "not a forecast" in result["disclaimer"]


def test_every_declared_scenario_key_is_runnable(tmp_path, monkeypatch):
    _write(tmp_path, _flat_series(300, noise=0.02, seed=11), monkeypatch)
    for key in SCENARIOS:
        result = run_scenario("tomato", "kolar_apmc", key)
        assert result["status"] in ("OK", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE")
