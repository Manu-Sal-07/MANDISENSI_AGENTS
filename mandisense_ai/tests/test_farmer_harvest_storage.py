"""
Tests for the Harvest Planner and Hold-or-Rot -- both convert the published
forecast curve into rupee decisions for one farmer's actual quantity.
"""

from __future__ import annotations

import pytest

from mandisense_ai.farmer.harvest import plan_harvest
from mandisense_ai.farmer.storage import hold_or_sell


class _FakeService:
    def __init__(self, curve, available=True):
        self._curve = curve
        self.is_available = available

    def get_curve(self, commodity, mandi_id):
        return self._curve


def _curve(base_price=2000.0, points=None):
    """A curve with `last_observed_price` on every row (as the real store
    publishes it) and one OK row per (horizon, forecast_price) pair given."""
    points = points or [(1, 2050.0), (3, 2100.0), (5, 1950.0), (7, 1800.0)]
    rows = []
    for horizon, price in points:
        rows.append({
            "status": "OK",
            "horizon_days": horizon,
            "target_date": f"2026-09-{20 + horizon}",
            "as_of_date": "2026-09-20",
            "last_observed_price": base_price,
            "forecast_price": price,
            "interval": {"p05": price * 0.9, "p25": price * 0.95, "p75": price * 1.05, "p95": price * 1.1},
            "decision": "SELL" if price < base_price else "HOLD",
            "decision_probability_of_decline": 0.7 if price < base_price else 0.3,
            "interval_source": "row_conditional_quantile",
        })
    return rows


def _patch_service(monkeypatch, curve, available=True):
    monkeypatch.setattr(
        "mandisense_ai.farmer.world.forecast_service",
        lambda: _FakeService(curve, available),
    )


# ── harvest planner ─────────────────────────────────────────────────────────


def test_harvest_converts_price_to_rupees_for_the_given_quantity(monkeypatch):
    _patch_service(monkeypatch, _curve())
    result = plan_harvest("tomato", "kolar_apmc", quantity_quintals=10)

    assert result["status"] == "OK"
    day1 = next(d for d in result["days"] if d["horizon_days"] == 1)
    assert day1["expected_total"] == pytest.approx(2050.0 * 10)
    assert day1["range_low"] == pytest.approx(2050.0 * 0.9 * 10)
    assert day1["range_high"] == pytest.approx(2050.0 * 1.1 * 10)


def test_harvest_includes_today_as_the_zero_day_baseline(monkeypatch):
    _patch_service(monkeypatch, _curve(base_price=2000.0))
    result = plan_harvest("tomato", "kolar_apmc", quantity_quintals=5)
    today = next(d for d in result["days"] if d["horizon_days"] == 0)
    assert today["expected_total"] == pytest.approx(2000.0 * 5)


def test_best_day_picks_the_highest_expected_rupee_value(monkeypatch):
    _patch_service(monkeypatch, _curve(points=[(1, 1900.0), (3, 2500.0), (5, 2100.0)]))
    result = plan_harvest("tomato", "kolar_apmc", quantity_quintals=1)
    assert result["best_day_horizon"] == 3


def test_refused_horizons_are_passed_through_not_silently_dropped(monkeypatch):
    curve = _curve(points=[(1, 2050.0)])
    curve.append({
        "status": "INSUFFICIENT_HISTORY", "horizon_days": 3, "reason": "not enough data",
        "as_of_date": "2026-09-20",
    })
    _patch_service(monkeypatch, curve)
    result = plan_harvest("tomato", "kolar_apmc", quantity_quintals=1)
    refused = next(d for d in result["days"] if d["horizon_days"] == 3)
    assert refused["status"] == "INSUFFICIENT_HISTORY"
    assert refused["expected_total"] is None


def test_untracked_series_is_unavailable(monkeypatch):
    _patch_service(monkeypatch, [], available=False)
    result = plan_harvest("onion", "lasalgaon_apmc", quantity_quintals=1)
    assert result["status"] == "UNAVAILABLE"


# ── hold or rot ─────────────────────────────────────────────────────────────


def test_perishable_crop_charges_compounding_spoilage(monkeypatch):
    """Tomato loses 8%/day: over 5 days that is 1 - 0.92**5 ~= 34%, not the
    naive 40% simple-subtraction a linear model would produce."""
    _patch_service(monkeypatch, _curve(base_price=2000.0, points=[(5, 2200.0)]))
    result = hold_or_sell("tomato", "kolar_apmc", quantity_quintals=1)

    option = result["options"][0]
    expected_surviving_fraction = (1 - 0.08) ** 5
    assert option["net_value"] == pytest.approx(2200.0 * expected_surviving_fraction, rel=1e-3)
    assert option["spoilage_cost"] == pytest.approx(2200.0 * (1 - expected_surviving_fraction), rel=1e-3)


def test_a_gain_too_small_to_beat_spoilage_recommends_sell(monkeypatch):
    """A 3% expected rise cannot survive 8%/day tomato spoilage even one day out."""
    _patch_service(monkeypatch, _curve(base_price=2000.0, points=[(1, 2060.0)]))
    result = hold_or_sell("tomato", "kolar_apmc", quantity_quintals=1)
    assert result["recommendation"] == "SELL"


def test_a_storable_crop_can_recommend_hold_for_the_same_gain(monkeypatch):
    """The same 3% expected rise over onion's 0.3%/day loss easily clears it --
    same forecast shape, opposite advice, purely from the crop's own shelf life."""
    _patch_service(monkeypatch, _curve(base_price=2000.0, points=[(1, 2060.0)]))
    result = hold_or_sell("onion", "lasalgaon_apmc", quantity_quintals=1)
    assert result["recommendation"] == "HOLD"


def test_horizons_beyond_shelf_life_are_excluded(monkeypatch):
    """Tomato has a 5-day shelf life; a 7-day horizon must not appear as an
    option, since the crop cannot survive to be sold on that day at all."""
    _patch_service(monkeypatch, _curve(base_price=2000.0, points=[(7, 2500.0)]))
    result = hold_or_sell("tomato", "kolar_apmc", quantity_quintals=1)
    assert result["options"] == []
    assert result["recommendation"] == "SELL"


def test_untracked_series_reports_shelf_profile_even_when_unavailable(monkeypatch):
    _patch_service(monkeypatch, [], available=False)
    result = hold_or_sell("tomato", "kolar_apmc")
    assert result["status"] == "UNAVAILABLE"
    assert result["shelf_profile"]["category"] == "highly_perishable"
