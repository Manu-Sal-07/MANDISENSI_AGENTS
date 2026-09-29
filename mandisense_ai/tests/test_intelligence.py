"""
Objective 3 — LLM decision intelligence.

The feature's whole claim is that a language model may reason over the
system's numbers but may not invent them. These tests exercise that claim
directly: a deliberately dishonest provider is injected and the suite asserts
that its output is caught, marked and reported rather than served as fact.

Test data is constructed in-process rather than read from the live stores, so
a failure here means the intelligence layer changed, not that tonight's
forecast moved.
"""

from __future__ import annotations

import pytest

from mandisense_ai.intelligence.evidence import EvidenceBundle
from mandisense_ai.intelligence.grounding import verify_grounding
from mandisense_ai.intelligence.providers import (
    BriefProvider,
    DeterministicProvider,
    select_provider,
)
from mandisense_ai.intelligence.schema import (
    ALLOWED_ACTIONS,
    ALLOWED_CONFIDENCE,
    BRIEF_TOOL_SCHEMA,
    brief_from_dict,
)
from mandisense_ai.intelligence.service import DecisionIntelligenceService


@pytest.fixture
def bundle() -> EvidenceBundle:
    """A realistic bundle: forecast, market, cognition, withheld spillover."""
    return EvidenceBundle(
        commodity="tomato",
        mandi_id="hoskote_apmc",
        assembled_at="2026-05-02T00:00:00+00:00",
        facts={
            "forecast.h5.point": 1719.53,
            "forecast.h5.change_pct": 7.33,
            "forecast.h5.direction": "up",
            "forecast.h5.p05": 1523.18,
            "forecast.h5.p95": 1946.26,
            "forecast.h5.model_skill": 0.1806,
            "forecast.last_observed_price": 1602.12,
            "forecast.as_of_date": "2026-05-02",
            "market.current_price": 1602.12,
            "market.month_change_pct": -11.53,
            "cognition.decision": "EXECUTE",
            "cognition.confidence_score": 0.9468,
            "volatility.regime": "low",
            "volatility.score": 0.5,
            "spillover.total_edges": 40,
            "spillover.actionable_edges": 0,
            "spillover.placebo_verdict": "FAIL",
            "spillover.is_validated": False,
        },
        unavailable={},
    )


class _HallucinatingProvider(BriefProvider):
    """States a price that is nowhere in the evidence."""

    name = "hallucinating"

    def generate(self, evidence):
        return {
            "commodity": evidence.commodity,
            "mandi_id": evidence.mandi_id,
            "action": "BUY",
            "confidence": "HIGH",
            "headline": "Prices will reach 2450 within the week.",
            "rationale": "Analysis indicates a move to 2450 from current levels.",
            "factors": [
                {
                    "label": "Momentum",
                    "detail": "Strong upward momentum toward 2450.",
                    "direction": "supports",
                    "evidence_ref": "forecast.h5.change_pct",
                }
            ],
            "risks": [],
            "watch_next": [],
        }


class _BadCitationProvider(BriefProvider):
    """Cites an evidence key that does not exist."""

    name = "bad-citation"

    def generate(self, evidence):
        return {
            "commodity": evidence.commodity,
            "mandi_id": evidence.mandi_id,
            "action": "WAIT",
            "confidence": "MEDIUM",
            "headline": "Hold for now.",
            "rationale": "Conditions are mixed.",
            "factors": [
                {
                    "label": "Satellite imagery",
                    "detail": "Crop stress detected.",
                    "direction": "opposes",
                    "evidence_ref": "satellite.ndvi",
                }
            ],
            "risks": [],
            "watch_next": [],
        }


class _ExplodingProvider(BriefProvider):
    name = "exploding"

    def generate(self, evidence):
        raise RuntimeError("provider is down")


# ─────────────────────────── grounding ────────────────────────────


class TestGrounding:
    """The core guarantee: invented figures are detected."""

    def test_invented_price_is_caught(self, bundle):
        brief = DecisionIntelligenceService(
            provider=_HallucinatingProvider()
        ).build_brief("tomato", "hoskote_apmc", evidence=bundle)

        assert brief.grounded is False
        assert any("2450" in issue for issue in brief.grounding_issues)

    def test_unknown_evidence_key_is_caught(self, bundle):
        brief = DecisionIntelligenceService(
            provider=_BadCitationProvider()
        ).build_brief("tomato", "hoskote_apmc", evidence=bundle)

        assert brief.grounded is False
        assert any("satellite.ndvi" in issue for issue in brief.grounding_issues)

    def test_deterministic_provider_is_always_grounded(self, bundle):
        brief = DecisionIntelligenceService(
            provider=DeterministicProvider()
        ).build_brief("tomato", "hoskote_apmc", evidence=bundle)

        assert brief.grounded is True, brief.grounding_issues
        assert brief.grounding_issues == []

    def test_figures_copied_from_evidence_pass(self, bundle):
        brief = brief_from_dict(
            {
                "commodity": "tomato",
                "mandi_id": "hoskote_apmc",
                "action": "BUY",
                "confidence": "MEDIUM",
                "headline": "Forecast moves to 1719.53.",
                "rationale": "Band runs 1523.18 to 1946.26 from a close of 1602.12.",
                "factors": [],
                "risks": [],
                "watch_next": [],
            }
        )
        grounded, issues = verify_grounding(
            brief, bundle.numeric_values(), list(bundle.facts)
        )
        assert grounded is True, issues

    def test_rounding_in_prose_is_tolerated(self, bundle):
        """1719.53 written as 1720 is a copy, not an invention."""
        brief = brief_from_dict(
            {
                "commodity": "tomato",
                "mandi_id": "hoskote_apmc",
                "action": "BUY",
                "confidence": "MEDIUM",
                "headline": "Forecast near 1720.",
                "rationale": "About 1720.",
                "factors": [],
                "risks": [],
                "watch_next": [],
            }
        )
        grounded, issues = verify_grounding(
            brief, bundle.numeric_values(), list(bundle.facts)
        )
        assert grounded is True, issues

    def test_dates_are_not_treated_as_claims(self, bundle):
        brief = brief_from_dict(
            {
                "commodity": "tomato",
                "mandi_id": "hoskote_apmc",
                "action": "WAIT",
                "confidence": "LOW",
                "headline": "Evidence as of 2026-05-02.",
                "rationale": "Assembled 2026-09-16T13:54:03 with a 90% interval.",
                "factors": [],
                "risks": [],
                "watch_next": [],
            }
        )
        grounded, issues = verify_grounding(
            brief, bundle.numeric_values(), list(bundle.facts)
        )
        assert grounded is True, issues

    def test_small_integers_are_not_claims(self, bundle):
        brief = brief_from_dict(
            {
                "commodity": "tomato",
                "mandi_id": "hoskote_apmc",
                "action": "WAIT",
                "confidence": "LOW",
                "headline": "Two risks over the next 5 days.",
                "rationale": "There are 3 factors and 2 risks.",
                "factors": [],
                "risks": [],
                "watch_next": [],
            }
        )
        grounded, issues = verify_grounding(
            brief, bundle.numeric_values(), list(bundle.facts)
        )
        assert grounded is True, issues


# ─────────────────────────── schema ───────────────────────────────


class TestSchema:
    def test_unknown_action_falls_back_to_wait(self):
        brief = brief_from_dict({"action": "YOLO", "confidence": "HIGH"})
        assert brief.action == "WAIT"

    def test_unknown_confidence_falls_back_to_insufficient(self):
        brief = brief_from_dict({"action": "BUY", "confidence": "CERTAIN"})
        assert brief.confidence == "INSUFFICIENT_EVIDENCE"

    def test_malformed_factor_entries_are_dropped(self):
        brief = brief_from_dict(
            {"action": "BUY", "confidence": "HIGH", "factors": ["nonsense", 42, None]}
        )
        assert brief.factors == []

    def test_tool_schema_is_strict_and_closed(self):
        """Strict + closed object is what makes the model's arguments valid."""
        assert BRIEF_TOOL_SCHEMA["strict"] is True
        schema = BRIEF_TOOL_SCHEMA["input_schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) <= set(schema["properties"])

    def test_schema_enums_match_module_constants(self):
        props = BRIEF_TOOL_SCHEMA["input_schema"]["properties"]
        assert props["action"]["enum"] == list(ALLOWED_ACTIONS)
        assert props["confidence"]["enum"] == list(ALLOWED_CONFIDENCE)

    def test_refusal_is_an_allowed_confidence(self):
        """The model must be able to say the evidence is not enough."""
        assert "INSUFFICIENT_EVIDENCE" in ALLOWED_CONFIDENCE


# ─────────────────────────── service ──────────────────────────────


class TestService:
    def test_provider_failure_falls_back_rather_than_raising(self, bundle):
        brief = DecisionIntelligenceService(
            provider=_ExplodingProvider()
        ).build_brief("tomato", "hoskote_apmc", evidence=bundle)

        assert "fallback" in brief.generated_by
        assert brief.headline

    def test_series_identity_comes_from_the_request(self, bundle):
        """A model cannot reattribute a brief to a different market."""

        class _Liar(BriefProvider):
            name = "liar"

            def generate(self, evidence):
                return {
                    "commodity": "onion",
                    "mandi_id": "lasalgaon_apmc",
                    "action": "BUY",
                    "confidence": "HIGH",
                    "headline": "x",
                    "rationale": "y",
                    "factors": [],
                    "risks": [],
                    "watch_next": [],
                }

        brief = DecisionIntelligenceService(provider=_Liar()).build_brief(
            "tomato", "hoskote_apmc", evidence=bundle
        )
        assert brief.commodity == "tomato"
        assert brief.mandi_id == "hoskote_apmc"

    def test_provenance_is_recorded(self, bundle):
        brief = DecisionIntelligenceService(
            provider=DeterministicProvider()
        ).build_brief("tomato", "hoskote_apmc", evidence=bundle)
        assert brief.generated_by == "deterministic"
        assert brief.evidence_as_of == "2026-05-02"

    def test_default_provider_needs_no_network(self, monkeypatch):
        monkeypatch.delenv("MANDISENSE_LLM_PROVIDER", raising=False)
        assert isinstance(select_provider(), DeterministicProvider)

    def test_claude_without_credentials_degrades_not_fails(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        provider = select_provider(prefer="claude")
        assert provider.name in ("claude", "deterministic")

    def test_status_reports_grounding_is_enforced(self):
        status = DecisionIntelligenceService(
            provider=DeterministicProvider()
        ).status()
        assert status["grounding_enforced"] is True
        assert status["provider"] == "deterministic"


# ─────────────────────────── evidence ─────────────────────────────


class TestEvidence:
    def test_unavailable_sources_are_named_not_omitted(self):
        bundle = EvidenceBundle(
            commodity="tomato",
            mandi_id="nowhere_apmc",
            assembled_at="2026-05-02T00:00:00+00:00",
            facts={},
            unavailable={"forecast": "not a tracked series"},
        )
        rendered = bundle.render()
        assert "UNAVAILABLE" in rendered
        assert "not a tracked series" in rendered

    def test_booleans_are_not_offered_as_numbers(self):
        """A bool must not enter the numeric allow-list.

        In Python `False == 0`, so a naive `isinstance(v, int)` check would
        silently admit every boolean fact as the number zero and licence the
        model to write "0" anywhere. The bundle used here holds only
        booleans, so the allow-list must come back empty — testing this
        against the realistic fixture would pass for the wrong reason, since
        `spillover.actionable_edges` is a genuine zero.
        """
        bools_only = EvidenceBundle(
            commodity="tomato",
            mandi_id="hoskote_apmc",
            assembled_at="2026-05-02T00:00:00+00:00",
            facts={"spillover.is_validated": False, "volatility.is_escalating": True},
        )
        assert bools_only.numeric_values() == []

    def test_genuine_zero_is_still_offered(self, bundle):
        """A measured zero is a real figure the model may state."""
        assert bundle.facts["spillover.actionable_edges"] == 0
        assert 0.0 in bundle.numeric_values()

    def test_rendered_keys_are_citable(self, bundle):
        rendered = bundle.render()
        for key in bundle.facts:
            assert key in rendered

    def test_withheld_spillover_is_explained_not_just_zeroed(self, bundle):
        """An actionable_edges of 0 must not read as 'no risk'."""
        from mandisense_ai.intelligence.evidence import build_evidence

        real = build_evidence("tomato", "hoskote_apmc")
        if real.facts.get("spillover.is_validated") is False:
            assert "spillover.interpretation" in real.facts
            assert "not mean" in real.facts["spillover.interpretation"]
