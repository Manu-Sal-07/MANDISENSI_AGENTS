"""
Tests for the cross-commodity / cross-district transmission engine
(mandisense_ai/farmer/transmission.py) and its trader-facing presentation
(mandisense_ai/trader/transmission.py).

Where the ground truth is known (a synthetic mean-reverting gap, a synthetic
shock with no real effect), the test checks the engine recovers it -- not
just that it runs.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.farmer import transmission as tr


def _district_frame(rows):
    df = pd.DataFrame(rows, columns=["date", "commodity", "mandi_id", "district", "min_price", "modal_price", "max_price", "arrivals"])
    df["date"] = pd.to_datetime(df["date"])
    return df


# ── onset detection ─────────────────────────────────────────────────────────


def test_a_single_arrival_spike_is_one_onset_not_several_days_of_them():
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    arrivals = np.full(120, 100.0)
    arrivals[60:63] = 400.0  # a 3-day glut, should cluster into one onset
    series = pd.DataFrame({"date": dates, "arrivals": arrivals})
    z = tr.arrival_surprise(series)
    onsets = tr.onsets(z, "glut")
    assert len(onsets) == 1
    assert onsets[0] == dates[60]


def test_two_spikes_within_the_minimum_gap_count_once():
    dates = pd.date_range("2024-01-01", periods=150, freq="D")
    arrivals = np.full(150, 100.0)
    arrivals[80] = 400.0
    arrivals[83] = 400.0  # 3 days later, inside MIN_GAP_DAYS=7
    arrivals[100] = 400.0  # well clear, a genuine second episode
    series = pd.DataFrame({"date": dates, "arrivals": arrivals})
    onsets = tr.onsets(tr.arrival_surprise(series), "glut")
    assert len(onsets) == 2


def test_arrival_surprise_only_uses_information_up_to_the_previous_day():
    """A spike on day t must not inflate its own z-score (which would make
    the spike see itself in its own trailing window)."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    arrivals = np.full(100, 100.0)
    arrivals[70] = 1000.0
    series = pd.DataFrame({"date": dates, "arrivals": arrivals})
    z = tr.arrival_surprise(series)
    assert z.iloc[70] > 5  # the spike itself still reads as extreme...
    # ...but the day right after should not, because yesterday's spike is a
    # single point against 69 days of trailing history at a lagged window.
    assert abs(z.iloc[71]) < 5


# ── nearest-print price matching (used by both the real and placebo paths) ──


def test_nearest_lookup_matches_within_tolerance_and_refuses_beyond_it():
    dates = pd.to_datetime(["2024-01-01", "2024-01-10", "2024-01-20"])
    prices = pd.Series([100.0, 110.0, 120.0], index=dates)
    lookup = tr.NearestLookup(prices, tol=3)
    assert lookup.at(pd.Timestamp("2024-01-02")) == pytest.approx(np.log(100.0))
    assert lookup.at(pd.Timestamp("2024-01-15")) is None  # 5 days from both sides, beyond tol=3


def test_price_change_is_log_difference_of_matched_prints():
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    prices = pd.Series(100.0 * 1.01 ** np.arange(30), index=dates)
    change = tr._price_change(prices, dates[0], 14)
    assert change == pytest.approx(np.log(prices.iloc[14] / prices.iloc[0]), abs=1e-6)


# ── Test B: error-correction recovers a known mean-reversion speed ──────────


def test_run_test_b_recovers_a_known_mean_reverting_gap():
    """Build two synthetic district price series whose log-gap is a known
    AR(1) process around a known mean, and check the fitted kappa and
    half-life land close to the generating values."""
    rng = np.random.default_rng(0)
    n = 300
    true_kappa = -0.3
    mu = 0.08
    gap = np.empty(n)
    gap[0] = mu
    for i in range(1, n):
        gap[i] = gap[i - 1] + true_kappa * (gap[i - 1] - mu) + rng.normal(0, 0.01)
    base = 100 * np.cumprod(1 + rng.normal(0, 0.005, n))
    dates = pd.date_range("2020-01-05", periods=n, freq="W")
    rows = []
    for i, d in enumerate(dates):
        rows.append([d, "tomato", "a", "a", base[i] * 0.9, base[i], base[i] * 1.1, 50.0])
        price_b = base[i] * np.exp(gap[i])
        rows.append([d, "tomato", "b", "b", price_b * 0.9, price_b, price_b * 1.1, 50.0])
    obs = _district_frame(rows)

    out = tr.run_test_b(obs, ["tomato"])
    pair = next(p for p in out["pairs"] if p["from"] == "a" and p["to"] == "b")
    assert pair["kappa"] == pytest.approx(true_kappa, abs=0.08)
    assert pair["closes"] is True
    expected_half_life = np.log(0.5) / np.log(1 + true_kappa)
    assert pair["half_life_weeks"] == pytest.approx(expected_half_life, rel=0.3)
    assert pair["mean_gap_pct"] == pytest.approx((np.exp(mu) - 1) * 100, abs=3.0)


def test_run_test_b_does_not_claim_closure_for_a_pure_random_walk_gap():
    rng = np.random.default_rng(1)
    n = 250
    gap = np.cumsum(rng.normal(0, 0.02, n))  # a genuine random walk: kappa = 0
    base = 100 * np.cumprod(1 + rng.normal(0, 0.005, n))
    dates = pd.date_range("2020-01-05", periods=n, freq="W")
    rows = []
    for i, d in enumerate(dates):
        rows.append([d, "onion", "a", "a", base[i] * 0.9, base[i], base[i] * 1.1, 50.0])
        price_b = base[i] * np.exp(gap[i])
        rows.append([d, "onion", "b", "b", price_b * 0.9, price_b, price_b * 1.1, 50.0])
    obs = _district_frame(rows)
    out = tr.run_test_b(obs, ["onion"])
    pair = next(p for p in out["pairs"] if p["from"] == "a" and p["to"] == "b")
    assert pair["closes"] is False


# ── Test A: a shock with no true effect should not be published ────────────


def test_run_test_a_does_not_publish_an_edge_with_no_true_effect():
    """Two crops whose arrivals and prices are independent noise: the engine
    must not publish a spillover edge between them."""
    rng = np.random.default_rng(2)
    n = 400
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    rows = []
    for district in ("a", "b"):
        for crop in ("tomato", "onion"):
            price = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
            arrivals = np.abs(rng.normal(100, 15, n))
            for i, d in enumerate(dates):
                rows.append([d, crop, district, district, price[i] * 0.9, price[i], price[i] * 1.1, arrivals[i]])
    obs = _district_frame(rows)
    out = tr.run_test_a(obs, ["tomato", "onion"])
    assert out["n_published"] == 0


# ── neighbour signal: honesty of the gating ─────────────────────────────────


def test_evaluate_neighbour_signal_returns_none_on_too_little_history():
    rng = np.random.default_rng(3)
    n = 50  # below the 150-week minimum the function requires
    dates = pd.date_range("2020-01-05", periods=n, freq="W")
    rows = []
    for district in ("a", "b"):
        price = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
        for i, d in enumerate(dates):
            rows.append([d, "tomato", district, district, price[i] * 0.9, price[i], price[i] * 1.1, 50.0])
    obs = _district_frame(rows)
    assert tr.evaluate_neighbour_signal(obs, "tomato", "a") is None


# ── trader-facing presentation: tiers and arithmetic ────────────────────────


def _fake_matrix(tmp_path, monkeypatch):
    from mandisense_ai.farmer import world

    matrix = {
        "generated_at": "2026-10-01T00:00:00Z",
        "data": {"from": "2021-01-01", "to": "2026-09-28"},
        "test_a_cross_commodity": {
            "n_tested": 2, "n_published": 1,
            "edges": [
                {"source": "tomato", "target": "onion", "shock": "glut", "status": "OK", "n_episodes": 50,
                 "effect": 0.05, "ci": [0.02, 0.08], "placebo_p": 0.01, "pre_trend_t": 0.5,
                 "stability": {"stable": True, "districts": 4, "agree": 4}, "fdr_pass": True, "published": True},
                {"source": "onion", "target": "tomato", "shock": "glut", "status": "OK", "n_episodes": 40,
                 "effect": 0.02, "ci": [-0.01, 0.05], "placebo_p": 0.4, "pre_trend_t": 0.2,
                 "stability": {"stable": False, "districts": 2, "agree": 1}, "fdr_pass": False, "published": False},
            ],
        },
        "test_b_spatial_gaps": {
            "pairs": [
                {"crop": "ginger", "from": "a", "to": "b", "kappa": -0.3, "half_life_weeks": 1.9,
                 "mean_gap_pct": 10.0, "closes": True, "p_holm": 0.001},
            ],
        },
        "neighbour_signal": {},
    }
    path = tmp_path / "transmission_matrix.json"
    path.write_text(json.dumps(matrix), encoding="utf-8")
    monkeypatch.setattr(world, "TRANSMISSION_MATRIX", path)


def test_cross_commodity_matrix_tiers_edges_by_their_evidence(tmp_path, monkeypatch):
    _fake_matrix(tmp_path, monkeypatch)
    from mandisense_ai.trader.transmission import cross_commodity_matrix

    result = cross_commodity_matrix()
    tiers = {(e["source"], e["target"]): e["tier"] for e in result["edges"]}
    assert tiers[("tomato", "onion")] == "ROBUST"
    assert tiers[("onion", "tomato")] == "NOT_SIGNIFICANT"


def test_gap_arbitrage_nets_off_transport_and_orders_by_margin(tmp_path, monkeypatch):
    _fake_matrix(tmp_path, monkeypatch)
    from mandisense_ai.farmer import registry, world

    rows = []
    dates = pd.date_range("2026-08-01", periods=6, freq="D")
    for i, d in enumerate(dates):
        rows.append([d, "ginger", "a", registry.MANDIS.get("kolar_apmc").district if registry.MANDIS.get("kolar_apmc") else "a",
                     900, 1000, 1100, 50.0])
        rows.append([d, "ginger", "b", "b", 1350, 1500, 1650, 50.0])
    obs = _district_frame(rows)
    monkeypatch.setattr(world, "district_observations", lambda: obs)
    monkeypatch.setattr(world, "district_series",
                        lambda crop, district: obs[(obs.commodity == crop) & (obs.mandi_id == district)].sort_values("date"))

    from mandisense_ai.trader.transmission import gap_arbitrage

    result = gap_arbitrage("ginger", quantity_quintals=20, trip_days=3)
    assert result["status"] == "OK"
    row = result["pairs"][0]
    assert row["cheaper_district"] == "a" and row["dearer_district"] == "b"
    assert row["net_gross_margin_pct"] == pytest.approx(row["projected_gap_pct_on_arrival"] - (row["transport_pct"] or 0), abs=0.01)
