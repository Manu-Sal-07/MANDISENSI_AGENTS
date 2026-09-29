"""Tests for Where to Sell (net price after transport)."""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.farmer.transport import RUPEES_PER_QUINTAL_PER_KM, compare_mandis

COLUMNS = [
    "date", "commodity", "mandi_id", "modal_price", "min_price", "max_price",
    "arrivals", "state", "district", "source", "ingested_at",
]


def _row(mandi_id, price, date="2026-09-20"):
    return [date, "tomato", mandi_id, price, price * 0.9, price * 1.1, 100.0, "Karnataka", "X", "test", date]


@pytest.fixture
def observations(tmp_path, monkeypatch):
    rows = [
        _row("kolar_apmc", 2000.0),
        _row("bangarpet_apmc", 2300.0),
        _row("bangalore_yeshwanthpur", 1900.0),
    ]
    frame = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "observations.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr("mandisense_ai.forecasting.store.observations_path", lambda: path)
    return frame


def test_ranks_by_net_price_not_gross_price(observations):
    """Bangarpet is a higher gross price than Kolar, but it is also farther
    away; the ranking must account for that, not just sort on the sticker
    price."""
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    assert result["status"] == "OK"
    # Kolar itself has zero transport cost, so its net price equals its gross.
    kolar = next(m for m in result["mandis"] if m["mandi_id"] == "kolar_apmc")
    assert kolar["distance_km"] == 0.0
    assert kolar["net_price_per_quintal"] == pytest.approx(2000.0)


def test_transport_cost_scales_with_distance_and_stated_rate(observations):
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    bangarpet = next(m for m in result["mandis"] if m["mandi_id"] == "bangarpet_apmc")
    expected_cost = round(bangarpet["distance_km"] * RUPEES_PER_QUINTAL_PER_KM, 2)
    assert bangarpet["transport_cost_per_quintal"] == pytest.approx(expected_cost)
    assert bangarpet["net_price_per_quintal"] == pytest.approx(2300.0 - expected_cost)


def test_quantity_scales_the_total(observations):
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc", quantity_quintals=20)
    kolar = next(m for m in result["mandis"] if m["mandi_id"] == "kolar_apmc")
    assert kolar["net_total"] == pytest.approx(kolar["net_price_per_quintal"] * 20)


def test_best_mandi_is_the_top_ranked_one(observations):
    result = compare_mandis("tomato", origin_mandi_id="kolar_apmc")
    assert result["best_mandi_id"] == result["mandis"][0]["mandi_id"]


def test_raw_coordinates_work_without_an_origin_mandi(observations):
    lat, lon = 13.1372, 78.1298  # roughly Kolar's coordinates
    result = compare_mandis("tomato", origin_lat=lat, origin_lon=lon)
    assert result["status"] == "OK"
    assert len(result["mandis"]) >= 1


def test_no_origin_at_all_is_unavailable():
    result = compare_mandis("tomato")
    assert result["status"] == "UNAVAILABLE"


def test_untracked_commodity_is_unavailable(observations):
    result = compare_mandis("onion", origin_mandi_id="kolar_apmc")
    assert result["status"] == "UNAVAILABLE"
