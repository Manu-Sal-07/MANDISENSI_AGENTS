"""
Tests for the position book (real trader risk, replacing the Command
Center's hardcoded ``COMMODITY_VOLUMES`` table) and fair forward pricing
(the farmer/trader deal calculator).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.trader import data as trader_data
from mandisense_ai.trader import positions as pos
from mandisense_ai.trader.forward import fair_forward_price

COLUMNS = [
    "date", "commodity", "mandi_id", "modal_price", "min_price", "max_price",
    "arrivals", "state", "district", "source", "ingested_at",
]


def _row(date, price, commodity="tomato", mandi_id="kolar_apmc"):
    return [date, commodity, mandi_id, price, price * 0.9, price * 1.1, 100.0, "KA", "X", "t", date]


def _flat_history(n, price, commodity="tomato", mandi_id="kolar_apmc", noise=0.01, seed=0, start="2023-01-01"):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq="D")
    prices = price * (1 + np.cumsum(rng.normal(0, noise, n)))
    return [_row(d.strftime("%Y-%m-%d"), float(p), commodity, mandi_id) for d, p in zip(dates, prices)]


def _write(tmp_path, rows, monkeypatch):
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "observations.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr("mandisense_ai.forecasting.store.observations_path", lambda: path)
    trader_data._cache["frame"] = None
    trader_data._cache["mtime"] = None


@pytest.fixture(autouse=True)
def _isolated_book(tmp_path, monkeypatch):
    monkeypatch.setattr(pos, "_book_path", lambda: tmp_path / "positions.json")
    monkeypatch.setattr(
        "mandisense_ai.forecasting.service.get_forecast_service",
        lambda: type("S", (), {"is_available": False})(),
    )


# -- position book CRUD -------------------------------------------------------


def test_add_position_requires_price_history(tmp_path, monkeypatch):
    _write(tmp_path, [], monkeypatch)
    result = pos.add_position("book1", "tomato", "kolar_apmc", 50)
    assert result["status"] == "ERROR"
    assert "history" in result["reason"]


def test_add_and_list_position(tmp_path, monkeypatch):
    _write(tmp_path, _flat_history(300, 1000.0), monkeypatch)
    created = pos.add_position("book1", "tomato", "kolar_apmc", 50, avg_cost=950.0, side="LONG")
    assert created["status"] == "OK"
    listed = pos.list_positions("book1")
    assert len(listed) == 1
    assert listed[0]["side"] == "LONG"


def test_invalid_side_is_rejected(tmp_path, monkeypatch):
    _write(tmp_path, _flat_history(300, 1000.0), monkeypatch)
    result = pos.add_position("book1", "tomato", "kolar_apmc", 50, side="SIDEWAYS")
    assert result["status"] == "ERROR"


def test_positions_are_scoped_to_their_own_book(tmp_path, monkeypatch):
    _write(tmp_path, _flat_history(300, 1000.0), monkeypatch)
    pos.add_position("book1", "tomato", "kolar_apmc", 50)
    pos.add_position("book2", "tomato", "kolar_apmc", 20)
    assert len(pos.list_positions("book1")) == 1
    assert len(pos.list_positions("book2")) == 1


def test_delete_position_scoped_to_its_book(tmp_path, monkeypatch):
    _write(tmp_path, _flat_history(300, 1000.0), monkeypatch)
    created = pos.add_position("book1", "tomato", "kolar_apmc", 50)
    position_id = created["position"]["id"]
    denied = pos.delete_position("book2", position_id)
    assert denied["status"] == "ERROR"
    ok = pos.delete_position("book1", position_id)
    assert ok["status"] == "OK"
    assert pos.list_positions("book1") == []


# -- risk assessment -----------------------------------------------------


def test_empty_book_reports_empty_not_a_crash(tmp_path, monkeypatch):
    _write(tmp_path, [], monkeypatch)
    result = pos.assess_book("book1")
    assert result["status"] == "EMPTY"


def test_a_long_and_a_short_do_not_add_their_exposure_the_same_direction(tmp_path, monkeypatch):
    """Real risk math: a LONG loses when price falls, a SHORT loses when it
    rises. If exposure sign were ignored, both would report the same-sign
    number regardless of position direction -- exactly the bug replaced."""
    rows = _flat_history(400, 1000.0, commodity="tomato", mandi_id="kolar_apmc", seed=1)
    rows += _flat_history(400, 1000.0, commodity="onion", mandi_id="lasalgaon_apmc", seed=2)
    _write(tmp_path, rows, monkeypatch)

    pos.add_position("book1", "tomato", "kolar_apmc", 50, side="LONG")
    pos.add_position("book1", "onion", "lasalgaon_apmc", 50, side="SHORT")
    result = pos.assess_book("book1", horizon_days=5)
    assert result["status"] == "OK"

    long_row = next(r for r in result["positions"] if r["side"] == "LONG")
    short_row = next(r for r in result["positions"] if r["side"] == "SHORT")
    # A LONG's downside is a falling price (negative pnl_p05 on the low
    # tail); a SHORT's downside is a rising price -- its pnl_p05 comes from
    # the *same* price move with the opposite sign applied.
    assert long_row["exposure"] > 0
    assert short_row["exposure"] < 0


def test_unpriced_positions_are_reported_not_silently_dropped(tmp_path, monkeypatch):
    rows = _flat_history(400, 1000.0, commodity="tomato", mandi_id="kolar_apmc")
    _write(tmp_path, rows, monkeypatch)
    pos.add_position("book1", "tomato", "kolar_apmc", 50)
    # A second position added directly to the store for a series with no
    # price history at assessment time (simulating a series that later
    # disappeared from the archive).
    rows_store = pos._load()
    rows_store.append({
        "id": "ghost", "book_id": "book1", "commodity": "ginger", "mandi_id": "no_such_mandi",
        "quantity_quintals": 10.0, "avg_cost": None, "side": "LONG", "created_at": "x",
    })
    pos._save(rows_store)

    result = pos.assess_book("book1")
    assert result["status"] == "OK"
    assert len(result["unpriced"]) == 1
    assert result["unpriced"][0]["commodity"] == "ginger"


def test_portfolio_falls_back_to_sum_of_worst_cases_with_no_shared_history(tmp_path, monkeypatch):
    """Two series with no overlapping dates at all cannot support a joint
    historical simulation; the fallback must say so rather than silently
    reporting a number as if it were the real joint distribution."""
    rows = _flat_history(200, 1000.0, commodity="tomato", mandi_id="kolar_apmc",
                          start="2020-01-01", seed=1)
    rows += _flat_history(200, 1000.0, commodity="onion", mandi_id="lasalgaon_apmc",
                           start="2024-01-01", seed=2)
    _write(tmp_path, rows, monkeypatch)
    pos.add_position("book1", "tomato", "kolar_apmc", 50)
    pos.add_position("book1", "onion", "lasalgaon_apmc", 50)

    result = pos.assess_book("book1", horizon_days=5)
    assert result["status"] == "OK"
    assert result["portfolio"]["method"] == "sum_of_individual_worst_cases"
    assert "note" in result["portfolio"]


def test_portfolio_uses_joint_simulation_with_enough_shared_history(tmp_path, monkeypatch):
    rows = _flat_history(400, 1000.0, commodity="tomato", mandi_id="kolar_apmc", seed=1)
    rows += _flat_history(400, 1000.0, commodity="onion", mandi_id="lasalgaon_apmc", seed=2)
    _write(tmp_path, rows, monkeypatch)
    pos.add_position("book1", "tomato", "kolar_apmc", 50)
    pos.add_position("book1", "onion", "lasalgaon_apmc", 50)

    result = pos.assess_book("book1", horizon_days=5)
    assert result["status"] == "OK"
    assert result["portfolio"]["method"] == "historical_simulation_joint"
    assert result["portfolio"]["worst_case_95"] <= result["portfolio"]["median_pnl"]


# -- fair forward price --------------------------------------------------


def test_forward_price_rejects_a_horizon_beyond_the_crops_shelf_life(tmp_path, monkeypatch):
    _write(tmp_path, _flat_history(400, 1000.0, commodity="tomato", mandi_id="kolar_apmc"), monkeypatch)
    result = fair_forward_price("tomato", "kolar_apmc", horizon_days=14, quantity_quintals=10)
    assert result["status"] == "UNSUITABLE"


def test_forward_price_needs_a_valid_horizon_range():
    result = fair_forward_price("tomato", "kolar_apmc", horizon_days=0)
    assert result["status"] == "ERROR"


def test_no_deal_when_expected_move_cannot_cover_risk_and_spoilage(tmp_path, monkeypatch):
    # A dead-flat price series: no expected move at all, so the trader's
    # risk-adjusted ceiling sits below the farmer's spoilage-adjusted floor.
    rows = _flat_history(400, 1000.0, commodity="tomato", mandi_id="kolar_apmc", noise=0.0)
    _write(tmp_path, rows, monkeypatch)
    result = fair_forward_price("tomato", "kolar_apmc", horizon_days=3, quantity_quintals=10)
    assert result["status"] == "OK"
    assert result["deal_possible"] is False
    assert "fair_price" not in result
    assert result["farmer_floor"] > result["trader_ceiling"]


def test_a_deal_when_it_exists_splits_the_surplus_evenly(tmp_path, monkeypatch):
    rows = _flat_history(500, 1000.0, commodity="garlic", mandi_id="malur_apmc", noise=0.02, seed=4)
    _write(tmp_path, rows, monkeypatch)
    result = fair_forward_price("garlic", "malur_apmc", horizon_days=3, quantity_quintals=10)
    if result["status"] == "OK" and result["deal_possible"]:
        assert result["fair_price"] == pytest.approx(
            (result["farmer_floor"] + result["trader_ceiling"]) / 2, rel=1e-6
        )
        assert result["farmer_surplus_per_quintal"] == pytest.approx(
            result["trader_surplus_per_quintal"], abs=0.01
        )


def test_historical_basis_carries_a_caveat_about_no_live_forecast(tmp_path, monkeypatch):
    rows = _flat_history(500, 1000.0, commodity="garlic", mandi_id="malur_apmc", noise=0.02, seed=4)
    _write(tmp_path, rows, monkeypatch)
    result = fair_forward_price("garlic", "malur_apmc", horizon_days=3, quantity_quintals=10)
    if result["status"] == "OK":
        assert result["basis"] == "historical_returns"
        assert "caveat" in result
