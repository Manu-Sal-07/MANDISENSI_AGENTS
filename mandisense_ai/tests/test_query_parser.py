"""
Tests for market query parsing.

The defect these guard against: the UI shipped suggested questions that named
a commodity but no mandi, while the parser hard-required both. Clicking a
suggestion returned "Context missing", so the feature looked broken on its own
example queries. Two failures compounded — unanswerable suggestions, and a
refusal that never said which half was missing.
"""

import pytest

from mandisense_ai.core.orchestrator.query_parser import (
    describe_gap,
    parse_market_query,
    supported_commodities,
    supported_mandis,
)


class TestCompleteQueries:
    @pytest.mark.parametrize(
        "query,commodity,mandi",
        [
            ("Should I sell tomatoes in Kolar today?", "tomato", "kolar_apmc"),
            ("Can I hold my onion stock in Bengaluru?", "onion", "bangalore_yeshwanthpur"),
            ("Best time to sell potatoes in Hoskote?", "potato", "hoskote_apmc"),
            ("garlic prices in Malur", "garlic", "malur_apmc"),
            ("ginger at Ramanagara", "ginger", "ramanagara_apmc"),
        ],
    )
    def test_commodity_and_mandi_are_extracted(self, query, commodity, mandi):
        parsed = parse_market_query(query)
        assert parsed.commodity == commodity
        assert parsed.mandi_id == mandi
        assert parsed.is_complete
        assert parsed.missing == []

    @pytest.mark.parametrize(
        "query,commodity",
        [
            ("aloo ka bhav Hoskote mein?", "potato"),
            ("pyaz in bengaluru", "onion"),
            ("tamatar in Kolar", "tomato"),
            ("lehsun in Malur", "garlic"),
            ("adrak in Anekal", "ginger"),
        ],
    )
    def test_local_language_names_are_understood(self, query, commodity):
        """A mandi product that only understands English is half a product."""
        assert parse_market_query(query).commodity == commodity

    def test_plurals_are_understood(self):
        assert parse_market_query("tomatoes in Kolar").commodity == "tomato"
        assert parse_market_query("onions in Kolar").commodity == "onion"


class TestSuggestionChips:
    """The exact strings the UI offers must be answerable."""

    UI_SUGGESTIONS = [
        "Should I sell tomatoes in Kolar today?",
        "Can I hold my onion stock in Bengaluru?",
        "Best time to sell potatoes in Hoskote?",
    ]

    @pytest.mark.parametrize("query", UI_SUGGESTIONS)
    def test_every_suggested_query_is_complete(self, query):
        parsed = parse_market_query(query)
        assert parsed.is_complete, (
            f"UI suggests {query!r} but the parser cannot answer it "
            f"(missing: {parsed.missing})"
        )


class TestHorizon:
    @pytest.mark.parametrize(
        "query,expected",
        [
            ("tomato in Kolar next 5 days", 5),
            ("tomato in Kolar in 3 days", 3),
            ("tomato in Kolar tomorrow", 1),
            ("tomato in Kolar next week", 7),
            ("tomato in Kolar", None),
        ],
    )
    def test_horizon_extraction(self, query, expected):
        assert parse_market_query(query).horizon_days == expected

    def test_absurd_horizons_are_ignored(self):
        assert parse_market_query("tomato in Kolar next 99 days").horizon_days is None


class TestIncompleteQueries:
    def test_missing_mandi_is_identified(self):
        parsed = parse_market_query("Can I sell 5 tonnes of tomatoes today?")
        assert parsed.commodity == "tomato"
        assert parsed.mandi_id is None
        assert parsed.missing == ["mandi"]

    def test_missing_commodity_is_identified(self):
        parsed = parse_market_query("What is happening in Kolar?")
        assert parsed.mandi_id == "kolar_apmc"
        assert parsed.commodity is None
        assert parsed.missing == ["commodity"]

    def test_empty_query_reports_both(self):
        assert parse_market_query("").missing == ["commodity", "mandi"]
        assert parse_market_query("hello").missing == ["commodity", "mandi"]

    def test_gap_message_names_what_was_understood(self):
        """Generic refusals are what made this look broken."""
        message = describe_gap(parse_market_query("sell tomatoes today"))
        assert "tomato" in message.lower()
        assert "mandi" in message.lower()

    def test_gap_message_for_missing_commodity_lists_options(self):
        message = describe_gap(parse_market_query("what about Kolar"))
        assert "kolar" in message.lower()
        for commodity in ("tomato", "onion", "potato"):
            assert commodity in message.lower()


class TestMatchingPrecision:
    def test_matching_is_word_bounded(self):
        """A name buried inside another word must not register."""
        assert parse_market_query("tomatoxyz in kolarxyz").commodity is None

    def test_similar_mandi_names_do_not_collide(self):
        assert parse_market_query("tomato in Bangarpet").mandi_id == "bangarpet_apmc"
        assert parse_market_query("tomato in Bangalore").mandi_id == "bangalore_yeshwanthpur"

    def test_vocabularies_are_non_empty(self):
        assert len(supported_commodities()) == 5
        assert len(supported_mandis()) >= 15
