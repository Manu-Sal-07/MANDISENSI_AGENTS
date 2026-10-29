"""The data layers behind the trader surfaces run on the real Agmarknet panel and validated forecasts (no v3/v4 artifacts)."""

import asyncio
import json

import pytest

from mandisense_ai.cognition.forecast_engine import ForecastBackedEngine
from mandisense_ai.cognition.state_store import MarketMemoryStore
from mandisense_ai.forecasting.naming import forecast_market, world_market
from mandisense_ai.services import candle_data_service as cds
from mandisense_ai.trader.scenarios import run_scenario


def test_one_bengaluru_market_has_one_identity():
    for legacy in ("bangalore_apmc", "bangalore_yeshwanthpur", "bengaluru_apmc"):
        assert world_market(legacy) == "bengaluru_apmc"
        assert forecast_market(legacy) == "bangalore_yeshwanthpur"
    assert world_market("kolar_apmc") == forecast_market("kolar_apmc") == "kolar_apmc"


def test_charts_read_real_reported_prices():
    markets = cds.list_available_markets()
    assert all(markets[c] for c in cds.VALID_COMMODITIES)
    series = cds.get_daily_series("tomato", "kolar_apmc")
    assert len(series) > 1000 and series["price"].notna().all() and series.index.is_monotonic_increasing
    # the old spelling resolves to the same series
    assert cds.get_summary("onion", "bangalore_yeshwanthpur")["current_price"] == cds.get_summary("onion", "bengaluru_apmc")["current_price"]
    with pytest.raises(ValueError):
        cds.get_daily_series("tomato", "no_such_apmc")


def test_candles_are_ordered_and_consistent():
    for c in cds.resample_candles("tomato", "kolar_apmc", "month"):
        assert c["low"] <= min(c["open"], c["close"]) and c["high"] >= max(c["open"], c["close"])


def test_council_price_signal_comes_from_the_forecast_service():
    engine = ForecastBackedEngine()
    assert engine.has_series("tomato", "kolar_apmc") and not engine.has_series("tomato", "no_such_apmc")
    out = asyncio.run(engine.predict("tomato", "kolar_apmc"))
    assert out["predicted_price"] > 0 and 0.5 <= out["confidence"] <= 1.0 and out["trend"] in {"up", "down", "stable"}
    assert engine.last_price("tomato", "kolar_apmc") > 0
    assert engine.decision("tomato", "kolar_apmc")["decision"] in {"SELL", "WAIT", "HOLD", "BUY"}


def test_series_without_a_forecast_is_refused_not_zero_filled():
    with pytest.raises(ValueError):
        asyncio.run(ForecastBackedEngine().predict("tomato", "no_such_apmc"))


def test_prune_removes_collapsed_and_orphaned_snapshots(tmp_path):
    store = MarketMemoryStore(base_path=tmp_path)
    def write(name, integrity):
        (store.snapshots_path / f"{name}_latest.json").write_text(json.dumps({"integrity_status": integrity}), encoding="utf-8")
    write("tomato_kolar_apmc", "FULL_COGNITION")
    write("tomato_bangalore_apmc", "FULL_COGNITION")      # orphan: not a current pair
    write("onion_kolar_apmc", "MODEL_UNAVAILABLE")        # collapsed: no model when it was written
    removed = store.prune([("tomato", "kolar_apmc"), ("onion", "kolar_apmc")])
    assert removed == 2
    assert set(store.list_available_intelligence()) == {"tomato"}


def test_scenario_edge_has_an_interval_not_a_sticky_median():
    s = run_scenario("tomato", "kolar_apmc", "price_slump", 5)
    assert s["status"] == "OK"
    lo, hi = s["edge_ci_pct"]
    assert lo <= s["edge_vs_baseline_pct"] <= hi
    assert "mean_pct" in s["outcome"] and "mean_pct" in s["baseline"]
