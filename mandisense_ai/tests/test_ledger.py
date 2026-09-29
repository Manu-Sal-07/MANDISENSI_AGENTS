"""
Tests for the closed-loop forecast outcome ledger.

Everything else in this system validates itself on history at fit time. The
ledger is the only component that checks those validations against what
happened *after* promotion, which makes its own honesty the property under
test here:

  * a republished forecast is the same claim, not a second one -- otherwise
    a nightly job re-run before new data arrives inflates every rate
  * an outcome is scored once; a later run cannot revise a past result
  * WAIT is not a directional claim, so it is left unscored rather than
    counted as a free win
  * rates are withheld below a sample size that could support them, and the
    withholding says so instead of returning a plausible-looking number
  * drift is measured against the backtest's *own* fold spread, not a
    tolerance invented at monitoring time
"""

from __future__ import annotations

import pandas as pd
import pytest

from mandisense_ai.forecasting.ledger import (
    MIN_SCORED_FOR_RATE,
    ForecastLedger,
    detect_drift,
)


# ── helpers ────────────────────────────────────────────────────────────────


class _FakeStore:
    """Stands in for a published forecast store: only `.forecasts` is read."""

    def __init__(self, forecasts):
        self.forecasts = forecasts


class _FakeBundle:
    def __init__(self, promoted_horizons, backtest, decision_thresholds=None):
        self.promoted_horizons = promoted_horizons
        self.backtest = backtest
        self.decision_thresholds = decision_thresholds or {}


def _forecast_row(
    *,
    as_of="2026-01-01",
    commodity="tomato",
    mandi_id="bangalore_yeshwanthpur",
    horizon=3,
    target="2026-01-04",
    base=2000.0,
    point=1900.0,
    decision="SELL",
    p05=1700.0,
    p95=2100.0,
    status="OK",
):
    return {
        "status": status,
        "as_of_date": as_of,
        "commodity": commodity,
        "mandi_id": mandi_id,
        "horizon_days": horizon,
        "target_date": target,
        "last_observed_price": base,
        "forecast_price": point,
        "expected_change_pct": (point - base) / base * 100.0,
        "direction": "down" if point < base else "up",
        "interval": {"p05": p05, "p25": p05 + 50, "p75": p95 - 50, "p95": p95},
        "interval_source": "quantile",
        "prediction_source": "point_model",
        "decision": decision,
        "decision_probability_of_decline": 0.7,
        "model_skill": 0.03,
    }


def _observation(date, price, commodity="tomato", mandi_id="bangalore_yeshwanthpur"):
    return {
        "date": date,
        "commodity": commodity,
        "mandi_id": mandi_id,
        "modal_price": price,
    }


@pytest.fixture
def ledger(tmp_path):
    return ForecastLedger(path=tmp_path / "forecast_ledger.parquet")


# ── recording ──────────────────────────────────────────────────────────────


def test_missing_file_reads_as_empty_not_error(ledger):
    frame = ledger.read()
    assert frame.empty
    assert "actual_price" in frame.columns


def test_records_only_serveable_rows(ledger):
    store = _FakeStore([
        _forecast_row(horizon=1),
        _forecast_row(horizon=3, status="INSUFFICIENT_HISTORY"),
        _forecast_row(horizon=5, target=None),
    ])
    result = ledger.record_publication(store)
    assert result["inserted"] == 1
    assert list(ledger.read()["horizon_days"]) == [1]


def test_republishing_the_same_claim_does_not_double_count(ledger):
    store = _FakeStore([_forecast_row()])
    first = ledger.record_publication(store)
    second = ledger.record_publication(store)

    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["duplicate"] == 1
    assert len(ledger.read()) == 1


def test_a_new_as_of_date_is_a_new_claim(ledger):
    ledger.record_publication(_FakeStore([_forecast_row(as_of="2026-01-01")]))
    ledger.record_publication(_FakeStore([_forecast_row(as_of="2026-01-02")]))
    assert len(ledger.read()) == 2


def test_empty_store_is_a_no_op(ledger):
    result = ledger.record_publication(_FakeStore([]))
    assert result == {"received": 0, "inserted": 0, "duplicate": 0}
    assert ledger.read().empty


# ── scoring ────────────────────────────────────────────────────────────────


def test_scores_a_resolved_claim(ledger):
    ledger.record_publication(_FakeStore([_forecast_row(base=2000.0, point=1900.0)]))
    observations = pd.DataFrame([_observation("2026-01-04", 1800.0)])

    result = ledger.score_pending(observations)
    assert result["scored"] == 1

    row = ledger.read().iloc[0]
    assert row["actual_price"] == 1800.0
    assert row["actual_change_pct"] == pytest.approx(-10.0)
    # Predicted down, realised down.
    assert bool(row["direction_correct"]) is True
    # 1800 sits inside [1700, 2100].
    assert bool(row["inside_90"]) is True
    # SELL is correct when the price declined.
    assert bool(row["decision_correct"]) is True


def test_unresolved_claim_stays_pending(ledger):
    ledger.record_publication(_FakeStore([_forecast_row(target="2026-01-04")]))
    # Only an observation from before the target date exists.
    observations = pd.DataFrame([_observation("2026-01-02", 1950.0)])

    assert ledger.score_pending(observations)["scored"] == 0
    assert pd.isna(ledger.read().iloc[0]["actual_price"])


def test_observation_beyond_tolerance_does_not_resolve(ledger):
    ledger.record_publication(_FakeStore([_forecast_row(target="2026-01-04")]))
    # 10 days late is a different market, not this claim's outcome.
    observations = pd.DataFrame([_observation("2026-01-14", 1800.0)])
    assert ledger.score_pending(observations)["scored"] == 0


def test_a_scored_row_is_never_rescored(ledger):
    ledger.record_publication(_FakeStore([_forecast_row()]))
    ledger.score_pending(pd.DataFrame([_observation("2026-01-04", 1800.0)]))

    # A later run sees a different price on the same date (a correction, or a
    # second print). History must not move.
    ledger.score_pending(pd.DataFrame([_observation("2026-01-04", 2500.0)]))
    assert ledger.read().iloc[0]["actual_price"] == 1800.0


def test_wait_is_left_unscored_rather_than_counted(ledger):
    ledger.record_publication(_FakeStore([_forecast_row(decision="WAIT")]))
    ledger.score_pending(pd.DataFrame([_observation("2026-01-04", 1800.0)]))

    row = ledger.read().iloc[0]
    # The outcome is still recorded -- only the decision verdict is withheld.
    assert row["actual_price"] == 1800.0
    assert pd.isna(row["decision_correct"])


def test_hold_is_correct_when_price_did_not_decline(ledger):
    ledger.record_publication(_FakeStore([_forecast_row(decision="HOLD")]))
    ledger.score_pending(pd.DataFrame([_observation("2026-01-04", 2200.0)]))
    assert bool(ledger.read().iloc[0]["decision_correct"]) is True


def test_actual_outside_the_band_is_recorded_as_a_miss(ledger):
    ledger.record_publication(
        _FakeStore([_forecast_row(p05=1700.0, p95=2100.0)])
    )
    ledger.score_pending(pd.DataFrame([_observation("2026-01-04", 2500.0)]))
    assert bool(ledger.read().iloc[0]["inside_90"]) is False


def test_scoring_an_empty_ledger_is_safe(ledger):
    assert ledger.score_pending(pd.DataFrame([_observation("2026-01-04", 1800.0)])) == {
        "pending": 0,
        "scored": 0,
    }


# ── reporting ──────────────────────────────────────────────────────────────


def _fill(ledger, n, *, correct=True, horizon=3):
    """Publish and resolve `n` claims, `correct` controlling the outcome."""
    rows, observations = [], []
    start = pd.Timestamp("2026-01-01")
    for i in range(n):
        as_of = (start + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        target = (start + pd.Timedelta(days=i + horizon)).strftime("%Y-%m-%d")
        rows.append(
            _forecast_row(as_of=as_of, target=target, horizon=horizon, point=1900.0)
        )
        observations.append(_observation(target, 1800.0 if correct else 2200.0))
    ledger.record_publication(_FakeStore(rows))
    ledger.score_pending(pd.DataFrame(observations))


def test_rates_are_withheld_below_the_minimum_sample(ledger):
    _fill(ledger, 5)
    report = ledger.live_performance()
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["scored"] == 5
    assert report["required"] == MIN_SCORED_FOR_RATE
    assert "directional_accuracy" not in report


def test_no_records_is_reported_as_such(ledger):
    assert ledger.live_performance()["status"] == "NO_RECORDS"


def test_rates_are_reported_once_the_sample_supports_them(ledger):
    _fill(ledger, MIN_SCORED_FOR_RATE)
    report = ledger.live_performance()
    assert report["status"] == "OK"
    assert report["scored"] == MIN_SCORED_FOR_RATE
    assert report["directional_accuracy"] == 1.0
    assert report["decision_precision"] == 1.0
    assert report["decision_coverage"] == 1.0


def test_a_horizon_filter_narrows_the_sample(ledger):
    _fill(ledger, MIN_SCORED_FOR_RATE, horizon=3)
    assert ledger.live_performance(horizon=3)["status"] == "OK"
    assert ledger.live_performance(horizon=7)["status"] == "INSUFFICIENT_EVIDENCE"


# ── drift ──────────────────────────────────────────────────────────────────


def _backtest(coverages):
    return {
        "horizons": {
            "3": {"fold_reports": [{"coverage_90": c} for c in coverages]}
        }
    }


def test_drift_needs_evidence_before_it_will_claim_anything(ledger):
    bundle = _FakeBundle([3], _backtest([0.88, 0.92]))
    report = detect_drift(bundle, ledger)
    assert report["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert report["horizons"]["3"]["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_live_coverage_inside_the_fold_range_is_not_drift(ledger):
    _fill(ledger, MIN_SCORED_FOR_RATE, correct=True)  # coverage_90 == 1.0
    bundle = _FakeBundle([3], _backtest([0.90, 1.00]), {3: 0.55})

    report = detect_drift(bundle, ledger)
    assert report["verdict"] == "OK"
    assert report["demotions"] == []
    assert report["horizons"]["3"]["checks"]["coverage_90"]["within"] is True


def test_coverage_below_the_fold_range_demotes_the_interval(ledger):
    # Realised price lands outside every published band.
    _fill(ledger, MIN_SCORED_FOR_RATE, correct=False)
    bundle = _FakeBundle([3], _backtest([0.90, 1.00]), {3: 0.55})

    report = detect_drift(bundle, ledger)
    assert report["verdict"] == "DRIFT_DETECTED"
    assert "3" in report["drifted_horizons"]
    actions = {d["action"] for d in report["demotions"]}
    assert "DEMOTE_INTERVAL_TO_POOLED" in actions


def test_precision_below_its_promotion_floor_demotes_the_decision(ledger):
    # Every SELL call was wrong: the price rose.
    _fill(ledger, MIN_SCORED_FOR_RATE, correct=False)
    bundle = _FakeBundle([3], _backtest([0.90, 1.00]), {3: 0.55})

    report = detect_drift(bundle, ledger)
    actions = {d["action"] for d in report["demotions"]}
    assert "DEMOTE_DECISION_TO_WAIT" in actions


def test_string_keyed_thresholds_are_found_too(ledger):
    """A bundle round-tripped through JSON keys horizons as strings."""
    _fill(ledger, MIN_SCORED_FOR_RATE, correct=False)
    bundle = _FakeBundle([3], _backtest([0.90, 1.00]), {"3": 0.55})

    report = detect_drift(bundle, ledger)
    assert "decision_precision" in report["horizons"]["3"]["checks"]


def test_a_single_fold_gives_no_usable_range(ledger):
    """One fold is a point, not a spread; no coverage verdict is claimed."""
    _fill(ledger, MIN_SCORED_FOR_RATE, correct=False)
    bundle = _FakeBundle([3], _backtest([0.95]), {})

    report = detect_drift(bundle, ledger)
    assert "coverage_90" not in report["horizons"]["3"]["checks"]


def test_unpromoted_horizons_are_not_monitored(ledger):
    _fill(ledger, MIN_SCORED_FOR_RATE)
    bundle = _FakeBundle([], _backtest([0.90, 1.00]))
    report = detect_drift(bundle, ledger)
    assert report["horizons"] == {}
    assert report["verdict"] == "INSUFFICIENT_EVIDENCE"
