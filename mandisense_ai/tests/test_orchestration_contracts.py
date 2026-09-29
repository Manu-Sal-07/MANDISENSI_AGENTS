"""
Tests for the orchestration layer's user-facing contracts.

These three paths had no test coverage at all, and each was returning
something fabricated or malformed to a user:

  * `/v1/predict` filled its `decision` field with a narrative sentence
    rather than an action code, which the farmer UI silently rendered as
    WAIT regardless of the market
  * the discovery feed picked its headline "hot commodity" with
    `random.choice` and reported `arrival_signal` as `random.random() > 0.5`
  * telemetry freshness measured how long the *process* had been running,
    not how old the *data* was — so restarting the server was the fastest
    way to make the health numbers look good
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from api.main import VALID_ACTION_CODES, action_code_from_state
from mandisense_ai.cognition.deployment import RealitySynchronizer


class TestPredictActionCode:
    def test_a_real_action_code_is_passed_through(self):
        for code in VALID_ACTION_CODES:
            state = SimpleNamespace(metadata={"decision": code})
            assert action_code_from_state(state) == code

    def test_a_narrative_sentence_never_leaks_into_the_decision_field(self):
        """The original bug: `primary_directive` prose reaching a field the
        client switches on."""
        state = SimpleNamespace(metadata={
            "decision": "Price is expected to rise in kolar_apmc (LOW risk). Arrivals are..."
        })
        assert action_code_from_state(state) == "WAIT"

    def test_missing_metadata_degrades_to_wait(self):
        assert action_code_from_state(SimpleNamespace(metadata=None)) == "WAIT"
        assert action_code_from_state(SimpleNamespace(metadata={})) == "WAIT"

    def test_state_without_metadata_attribute_does_not_raise(self):
        assert action_code_from_state(SimpleNamespace()) == "WAIT"

    def test_unknown_code_is_not_guessed_into_an_action(self):
        state = SimpleNamespace(metadata={"decision": "EXECUTE"})
        assert action_code_from_state(state) == "WAIT"


class TestDiscoveryRankingIsDeterministic:
    def test_repeated_calls_return_the_same_order(self):
        """`random.choice` meant refreshing the page changed which crop the
        market was supposedly excited about."""
        from backend.app.routes.discovery import _rank_commodities_by_expected_move

        first = _rank_commodities_by_expected_move("kolar_apmc")
        for _ in range(5):
            assert _rank_commodities_by_expected_move("kolar_apmc") == first

    def test_every_commodity_is_still_represented(self):
        from backend.app.routes.discovery import COMMODITIES, _rank_commodities_by_expected_move

        ranked = _rank_commodities_by_expected_move("kolar_apmc")
        assert sorted(ranked) == sorted(COMMODITIES)

    def test_an_unknown_mandi_falls_back_to_a_stable_order_not_a_crash(self):
        from backend.app.routes.discovery import COMMODITIES, _rank_commodities_by_expected_move

        ranked = _rank_commodities_by_expected_move("not_a_real_mandi_apmc")
        assert sorted(ranked) == sorted(COMMODITIES)
        assert ranked == _rank_commodities_by_expected_move("not_a_real_mandi_apmc")


class TestTelemetryMeasuresDataAgeNotUptime:
    @pytest.mark.parametrize(
        "age_days,expected",
        [(0, 1.0), (3, 1.0), (4, 0.8), (7, 0.8), (8, 0.4), (21, 0.4), (22, 0.1), (150, 0.1)],
    )
    def test_freshness_is_graded_against_how_the_feed_actually_behaves(self, age_days, expected):
        assert RealitySynchronizer._freshness_from_age(age_days) == expected

    def test_unknown_age_is_zero_trust_not_full_trust(self):
        """The dangerous direction to fail in: an unmeasurable source must
        not report itself as perfectly fresh."""
        assert RealitySynchronizer._freshness_from_age(None) == 0.0

    def test_freshness_is_independent_of_process_age(self, monkeypatch):
        """Two synchronizers constructed at different times, over identical
        data, must report identical freshness — the old implementation's
        score depended entirely on when the object was created."""
        monkeypatch.setattr(RealitySynchronizer, "_observation_age_days", lambda self: 5.0)
        monkeypatch.setattr(RealitySynchronizer, "_forecast_age_days", lambda self: 5.0)

        young = RealitySynchronizer()
        old = RealitySynchronizer()
        for src in old.sources.values():
            src.last_sync = datetime.now() - timedelta(days=30)

        young_scores = {s.id: s.freshness_score for s in young.get_source_status()}
        old_scores = {s.id: s.freshness_score for s in old.get_source_status()}
        assert young_scores == old_scores

    def test_stale_data_is_reported_stale_even_on_a_fresh_process(self, monkeypatch):
        monkeypatch.setattr(RealitySynchronizer, "_observation_age_days", lambda self: 150.0)
        monkeypatch.setattr(RealitySynchronizer, "_forecast_age_days", lambda self: 150.0)

        statuses = RealitySynchronizer().get_source_status()
        assert all(s.freshness_score == 0.1 for s in statuses)
        assert all(s.status in ("STALE", "DEGRADED") for s in statuses)

    def test_fresh_data_clears_the_integrity_gate(self, monkeypatch):
        """`CognitionEngine.validate_integrity` gates FULL_COGNITION on
        avg_trust >= 0.7; genuinely fresh data has to be able to reach it."""
        monkeypatch.setattr(RealitySynchronizer, "_observation_age_days", lambda self: 1.0)
        monkeypatch.setattr(RealitySynchronizer, "_forecast_age_days", lambda self: 1.0)

        statuses = RealitySynchronizer().get_source_status()
        avg_trust = sum(s.trust_score for s in statuses) / len(statuses)
        assert avg_trust >= 0.7
