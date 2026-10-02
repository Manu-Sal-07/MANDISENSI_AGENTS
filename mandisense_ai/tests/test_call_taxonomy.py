"""
Tests for the three-way call taxonomy carried to the presentation layer.

Three epistemically different outcomes used to arrive at the UI as the same
string, "WAIT", and were rendered as the same confident tile:

  * the calibrated policy called HOLD -- a real recommendation
  * the calibrated policy ran and declined to call this row
  * there is no forecast for this series at all

A farmer reading "Tomato - WAIT - 0.0%" cannot tell which of those produced
it. That is the last-mile failure this taxonomy exists to close, so these
tests assert the three stay distinguishable all the way out, and that a
refusal never arrives wearing the costume of a decision.
"""

from __future__ import annotations

import asyncio

import pytest

from mandisense_ai.core.orchestrator.decision_orchestrator import (
    ABSTAIN_NO_THRESHOLD,
    ABSTAIN_UNCERTAIN,
    CALL_ABSTAINED,
    CALL_ADVISED,
    CALL_UNAVAILABLE,
    DecisionOrchestrator,
    _unavailable,
)


class _FakeService:
    """Stands in for the published forecast store."""

    def __init__(self, row=None, available=True, curve=None):
        self._row = row
        self._available = available
        self._curve = curve

    @property
    def is_available(self):
        return self._available

    def status(self):
        return {"available": self._available, "reason": "no store on disk"}

    def get_curve(self, commodity, mandi_id):
        if self._curve is not None:
            return self._curve
        return [self._row] if self._row else []

    def freshness(self):
        return "FRESH"


def _row(decision, probability=0.72, status="OK"):
    return {
        "status": status,
        "horizon_days": 3,
        "target_date": "2026-10-02",
        "commodity": "tomato",
        "mandi_id": "kolar_apmc",
        "forecast_price": 1900.0,
        "last_observed_price": 2000.0,
        "expected_change_pct": -5.0,
        "direction": "down",
        "interval": {"p05": 1700.0, "p25": 1820.0, "p75": 1980.0, "p95": 2100.0},
        "interval_source": "row_conditional_quantile",
        "prediction_source": "xgboost",
        "decision": decision,
        "decision_probability_of_decline": probability,
        "model_skill": 0.2,
        "as_of_date": "2026-09-29",
        "data_lag_days": 0,
    }


def _decide(monkeypatch, service):
    monkeypatch.setattr(
        "mandisense_ai.forecasting.service.get_forecast_service", lambda: service
    )
    orchestrator = DecisionOrchestrator()
    return asyncio.run(orchestrator.get_actionable_decision("tomato", "kolar_apmc"))


# -- the three states ------------------------------------------------------


@pytest.mark.parametrize("decision", ["SELL", "HOLD"])
def test_a_directional_call_is_advised(monkeypatch, decision):
    result = _decide(monkeypatch, _FakeService(_row(decision)))

    assert result["decision"] == decision
    assert result["call_type"] == CALL_ADVISED
    assert result["abstention_reason"] is None
    assert result["confidence"] > 0.0


def test_a_calibrated_policy_declining_this_row_is_an_abstention(monkeypatch):
    result = _decide(monkeypatch, _FakeService(_row("WAIT", probability=0.52)))

    assert result["decision"] == "WAIT"
    assert result["call_type"] == CALL_ABSTAINED
    assert result["abstention_reason"] == ABSTAIN_UNCERTAIN
    assert result["status"] == "OK"


def test_an_uncalibrated_horizon_abstains_for_a_different_reason(monkeypatch):
    """
    "This row was too close to call" and "this horizon never earned a
    threshold, so no row of it will ever be called" are different facts.
    """
    result = _decide(monkeypatch, _FakeService(_row(None)))

    assert result["call_type"] == CALL_ABSTAINED
    assert result["abstention_reason"] == ABSTAIN_NO_THRESHOLD


def test_a_refused_series_is_unavailable_not_an_abstention(monkeypatch):
    """The critical distinction: nothing was decided, so nothing is implied."""
    refused = {
        "status": "REBUILDING_HISTORY",
        "horizon_days": 3,
        "reason": "only 2 observation(s) since trading resumed",
    }
    result = _decide(monkeypatch, _FakeService(curve=[refused]))

    assert result["call_type"] == CALL_UNAVAILABLE
    assert result["abstention_reason"] is None
    assert result["confidence"] == 0.0
    assert result["status"] == "REBUILDING_HISTORY"


def test_an_untracked_series_is_unavailable(monkeypatch):
    result = _decide(monkeypatch, _FakeService(curve=[]))
    assert result["call_type"] == CALL_UNAVAILABLE


def test_no_published_store_is_unavailable(monkeypatch):
    result = _decide(monkeypatch, _FakeService(available=False))
    assert result["call_type"] == CALL_UNAVAILABLE
    assert result["status"] == "FORECAST_UNAVAILABLE"


def test_every_refusal_helper_declares_itself_unavailable():
    result = _unavailable("tomato", "kolar_apmc", "DORMANT", "last traded 137 days ago")
    assert result["call_type"] == CALL_UNAVAILABLE
    assert result["decision"] == "WAIT"
    assert result["confidence"] == 0.0


# -- the property that matters ---------------------------------------------


def test_wait_alone_never_distinguishes_the_three(monkeypatch):
    """
    All three can carry decision == "WAIT". Only `call_type` separates them,
    which is exactly why it has to travel with the verb rather than be
    re-derived per screen.
    """
    abstained = _decide(monkeypatch, _FakeService(_row("WAIT", probability=0.52)))
    unavailable = _decide(
        monkeypatch,
        _FakeService(curve=[{"status": "DORMANT", "horizon_days": 3, "reason": "x"}]),
    )

    assert abstained["decision"] == unavailable["decision"] == "WAIT"
    assert abstained["call_type"] != unavailable["call_type"]


def test_an_unavailable_call_never_carries_a_confident_number(monkeypatch):
    """
    A 0.0% move rendered beside a verb reads as "flat market", not "unknown".
    Nothing downstream may present an UNAVAILABLE call as a measurement, so
    confidence is zero and the reason is populated.
    """
    result = _decide(
        monkeypatch,
        _FakeService(curve=[{"status": "DORMANT", "horizon_days": 3, "reason": "x"}]),
    )

    assert result["confidence"] == 0.0
    assert result["risk_level"] == "UNKNOWN"
    assert result["signal_strength"] == "UNKNOWN"
    assert result["reason"]


# -- the discovery routes must not depend on a background warmup -----------


class TestDiscoveryWorksWithoutWarmup:
    """
    `model_loader.engines` is populated by a background task with a 15-second
    timeout whose failures are logged and swallowed, so it is routinely still
    None when the first request lands. The discovery routes dereferenced it
    unguarded, raised AttributeError for every crop, and the per-item
    `except: continue` turned that into an empty list -- which the farmer
    screen rendered as "Today's calls are not in yet. Mandi records usually
    arrive by the afternoon", blaming the mandi for a warmup race.
    """

    def test_orchestrator_is_resolved_without_engines(self, monkeypatch):
        from backend.app.routes import discovery

        monkeypatch.setattr(discovery.model_loader, "engines", None, raising=False)
        assert discovery._decision_orchestrator() is discovery._ORCHESTRATOR

    def test_a_warmed_up_orchestrator_is_preferred(self, monkeypatch):
        from backend.app.routes import discovery

        sentinel = object()

        class _Engines:
            decision_orch = sentinel

        monkeypatch.setattr(discovery.model_loader, "engines", _Engines(), raising=False)
        assert discovery._decision_orchestrator() is sentinel

    def test_quick_decisions_returns_every_crop_even_with_no_engines(self, monkeypatch):
        """
        A shortened list is itself a lie: the farmer asked about five crops
        and silently got four, with nothing to say the fifth had failed.
        """
        from backend.app.routes import discovery

        monkeypatch.setattr(discovery.model_loader, "engines", None, raising=False)
        result = asyncio.run(discovery.get_quick_decisions("bengaluru"))

        assert len(result["decisions"]) == len(discovery.COMMODITIES)
        for entry in result["decisions"]:
            assert entry["call_type"] in {CALL_ADVISED, CALL_ABSTAINED, CALL_UNAVAILABLE}
            assert "confidence" in entry
