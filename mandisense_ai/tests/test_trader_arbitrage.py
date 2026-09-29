"""
Tests for the mandi-to-mandi spread scanner.

The property that separates this from a sticker-price diff: a gap that
history says closes before the truck arrives must rank below one that
doesn't, and the vehicle choice must actually scale with load rather than
using a flat per-quintal rate regardless of how much is being moved.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.trader.arbitrage import (
    expected_spread_after,
    fit_ar1,
    scan_spreads,
    transport_plan,
)
from mandisense_ai.trader import data as trader_data

COLUMNS = [
    "date", "commodity", "mandi_id", "modal_price", "min_price", "max_price",
    "arrivals", "state", "district", "source", "ingested_at",
]


def _row(date, commodity, mandi_id, price):
    return [date, commodity, mandi_id, price, price * 0.9, price * 1.1, 100.0, "KA", "X", "t", date]


def _write(tmp_path, rows, monkeypatch):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "observations.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr("mandisense_ai.forecasting.store.observations_path", lambda: path)
    trader_data._cache["frame"] = None
    trader_data._cache["mtime"] = None


# -- transport plan ----------------------------------------------------------


def test_transport_plan_picks_the_cheapest_vehicle_for_a_small_load():
    plan = transport_plan(distance_km=60, quantity_quintals=2)
    assert plan["vehicle"] == "small tempo"
    assert plan["vehicles_needed"] == 1


def test_transport_plan_scales_to_a_full_truck_for_a_large_load():
    plan = transport_plan(distance_km=60, quantity_quintals=100)
    assert plan["vehicle"] == "10-tonne truck"


def test_per_quintal_cost_falls_as_load_grows():
    small = transport_plan(60, 2)
    large = transport_plan(60, 300)
    assert large["per_quintal"] < small["per_quintal"]


def test_multiple_trucks_needed_beyond_one_vehicles_capacity():
    plan = transport_plan(distance_km=60, quantity_quintals=350)
    assert plan["vehicles_needed"] == 4  # ceil(350/100)


# -- AR(1) fit and expected spread --------------------------------------------


def test_fit_ar1_recovers_a_known_mean_reverting_process():
    rng = np.random.default_rng(0)
    mu, b = 0.05, -0.3
    s = [mu]
    for _ in range(500):
        s.append(s[-1] + b * (s[-1] - mu) + rng.normal(0, 0.01))
    fit = fit_ar1(pd.Series(s))
    assert fit is not None
    fitted_b, fitted_mu = fit
    assert fitted_mu == pytest.approx(mu, abs=0.02)
    assert fitted_b < 0


def test_fit_ar1_returns_none_for_a_pure_random_walk():
    rng = np.random.default_rng(1)
    s = pd.Series(np.cumsum(rng.normal(0, 0.02, 300)))
    fit = fit_ar1(s)
    assert fit is None


def test_expected_spread_with_no_fit_is_a_random_walk():
    assert expected_spread_after(current=0.1, fit=None, steps=5) == 0.1


def test_expected_spread_reverts_toward_mu_with_more_steps():
    fit = (-0.3, 0.0)
    near = expected_spread_after(current=0.5, fit=fit, steps=1)
    far = expected_spread_after(current=0.5, fit=fit, steps=10)
    assert abs(far) < abs(near) < 0.5


# -- scan_spreads end to end ---------------------------------------------------


def test_scan_spreads_needs_at_least_two_mandis(tmp_path, monkeypatch):
    _write(tmp_path, [_row("2026-01-01", "tomato", "kolar_apmc", 1000.0)], monkeypatch)
    result = scan_spreads("tomato")
    assert result["status"] == "UNAVAILABLE"


def test_scan_spreads_reports_assumptions_with_every_result(tmp_path, monkeypatch):
    rows = [
        _row("2026-01-01", "tomato", "kolar_apmc", 1000.0),
        _row("2026-01-01", "tomato", "bangarpet_apmc", 2000.0),
    ]
    _write(tmp_path, rows, monkeypatch)
    result = scan_spreads("tomato", quantity_quintals=20)
    assert result["status"] == "OK"
    assert "vehicles" in result["assumptions"]
    assert result["assumptions"]["transport_model"].startswith("cheapest vehicle")


def test_scan_spreads_honours_a_trader_supplied_transport_rate(tmp_path, monkeypatch):
    rows = [
        _row("2026-01-01", "tomato", "kolar_apmc", 1000.0),
        _row("2026-01-01", "tomato", "bangarpet_apmc", 3000.0),
    ]
    _write(tmp_path, rows, monkeypatch)
    result = scan_spreads("tomato", transport_rate_override=1.0)
    assert result["status"] == "OK"
    assert "trader-supplied" in result["assumptions"]["transport_model"]
    op = result["opportunities"][0]
    assert op["vehicle"] == "trader-supplied rate"
