"""Tests for Where to Sell (net price after transport) on the per-mandi prices."""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.farmer import dashboard, registry
from mandisense_ai.farmer.transport import RUPEES_PER_QUINTAL_PER_KM, compare_mandis

COLUMNS = ["date", "commodity", "mandi_id", "district", "min_price", "modal_price", "max_price", "arrivals"]


def _rows(mandi_id, price, arrivals=20.0, crop="tomato", dates=("2026-09-28", "2026-09-29", "2026-09-30")):
    district = registry.MANDIS[mandi_id].district
    return [[d, crop, mandi_id, district, price * 0.8, price, price * 1.2, arrivals] for d in dates]


@pytest.fixture
def prices(tmp_path, monkeypatch):
    def _apply(*groups):
        frame = pd.DataFrame([row for g in groups for row in g], columns=COLUMNS)
        frame["date"] = pd.to_datetime(frame["date"])
        path = tmp_path / "mandi_prices.parquet"
        frame.to_parquet(path, index=False)
        monkeypatch.setattr("mandisense_ai.farmer.world.MANDI_PRICES", path)

    return _apply


def test_ranks_by_net_price_not_gross_price(prices):
    """Bangarpet prints more than Kolar but is 25 km away; the ranking must
    take the haul off, not sort on the sticker price."""
    prices(_rows("kolar_apmc", 2000.0), _rows("bangarpet_apmc", 2080.0), _rows("malur_apmc", 1900.0))
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    assert result["status"] == "OK"
    by_id = {m["mandi_id"]: m for m in result["mandis"]}
    assert by_id["kolar_apmc"]["transport_cost_per_quintal"] == 0.0
    assert by_id["kolar_apmc"]["net_price_per_quintal"] == pytest.approx(by_id["kolar_apmc"]["gross_price_per_quintal"])
    assert by_id["bangarpet_apmc"]["net_price_per_quintal"] < by_id["bangarpet_apmc"]["gross_price_per_quintal"]
    assert result["mandis"][0]["net_price_per_quintal"] >= result["mandis"][-1]["net_price_per_quintal"]


def test_transport_cost_scales_with_distance_and_stated_rate(prices):
    prices(_rows("kolar_apmc", 2000.0), _rows("bangarpet_apmc", 2000.0))
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    row = next(m for m in result["mandis"] if m["mandi_id"] == "bangarpet_apmc")
    assert row["transport_cost_per_quintal"] == pytest.approx(row["distance_km"] * RUPEES_PER_QUINTAL_PER_KM, abs=0.01)
    assert result["transport_rate_per_quintal_per_km"] == RUPEES_PER_QUINTAL_PER_KM


def test_one_thin_day_cannot_rank_a_market_first(prices):
    """Three prints are averaged by arrivals: a last-day spike on a few crates
    must not outweigh two ordinary days."""
    spike = [["2026-09-28", "tomato", "bangarpet_apmc", "kolar", 1600.0, 2000.0, 2400.0, 20.0],
             ["2026-09-29", "tomato", "bangarpet_apmc", "kolar", 1600.0, 2000.0, 2400.0, 20.0],
             ["2026-09-30", "tomato", "bangarpet_apmc", "kolar", 2800.0, 3600.0, 4000.0, 0.4]]
    prices(_rows("kolar_apmc", 2000.0), spike)
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    row = next(m for m in result["mandis"] if m["mandi_id"] == "bangarpet_apmc")
    assert row["latest_price_per_quintal"] == 3600.0
    assert row["gross_price_per_quintal"] < 2100.0


def test_a_price_far_from_its_neighbours_is_flagged_not_recommended(prices):
    prices(_rows("kolar_apmc", 1500.0), _rows("bangarpet_apmc", 1450.0), _rows("malur_apmc", 1550.0),
           _rows("mulbagal_apmc", 3900.0))
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    flags = {m["mandi_id"]: m["outlier"] for m in result["mandis"]}
    assert flags["mulbagal_apmc"] is True
    assert flags["kolar_apmc"] is False
    assert result["best_mandi_id"] != "mulbagal_apmc"


def test_a_mandi_too_small_for_the_load_is_marked_thin(prices):
    prices(_rows("kolar_apmc", 2000.0), _rows("malur_apmc", 2400.0, arrivals=0.5))
    small = compare_mandis("tomato", origin_mandi_id="kolar_apmc", quantity_quintals=20)
    assert next(m for m in small["mandis"] if m["mandi_id"] == "malur_apmc")["thin_for_load"] is True
    tiny_load = compare_mandis("tomato", origin_mandi_id="kolar_apmc", quantity_quintals=2)
    assert next(m for m in tiny_load["mandis"] if m["mandi_id"] == "malur_apmc")["thin_for_load"] is False


def test_sell_plan_never_carries_a_load_to_a_market_that_cannot_take_it(prices, monkeypatch):
    monkeypatch.setattr(dashboard, "_forecast_rows", lambda *a: [])
    prices(_rows("kolar_apmc", 2000.0), _rows("malur_apmc", 2600.0, arrivals=0.5))
    plan = dashboard.sell_plan("tomato", "kolar_apmc", 20)
    assert plan["status"] == "OK"
    assert plan["best"] == "sell_today"
    assert [o["choice"] for o in plan["options"]] == ["sell_today"]


def test_sell_plan_limits_the_haul_for_a_crop_that_spoils_fast(prices, monkeypatch):
    """Tomato loses ~8% a day: a market 100 km away is not offered however
    good its price looks. The same haul is fine for a storable crop."""
    monkeypatch.setattr(dashboard, "_forecast_rows", lambda *a: [])
    far = _rows("kanakapura_apmc", 2600.0)
    prices(_rows("kolar_apmc", 2000.0), far, _rows("kolar_apmc", 2000.0, crop="onion"),
           _rows("kanakapura_apmc", 2600.0, crop="onion"))
    assert dashboard.sell_plan("tomato", "kolar_apmc", 10)["best"] == "sell_today"
    assert dashboard.sell_plan("onion", "kolar_apmc", 10)["best"] == "travel"


def test_untracked_commodity_is_unavailable(prices):
    prices(_rows("kolar_apmc", 2000.0))
    assert compare_mandis("saffron", origin_mandi_id="kolar_apmc")["status"] == "UNAVAILABLE"


def test_no_origin_is_unavailable(prices):
    prices(_rows("kolar_apmc", 2000.0))
    assert compare_mandis("tomato")["status"] == "UNAVAILABLE"
