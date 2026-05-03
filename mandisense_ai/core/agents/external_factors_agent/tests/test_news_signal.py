from datetime import datetime, timedelta, timezone

import pytest

from mandisense_ai.core.agents.external_factors_agent.processing.news_signal import get_news_signal


def test_get_news_signal_returns_zero_for_irrelevant_articles():
    articles = [
        {"title": "Sports update", "description": "Football scores", "published_at": "2026-04-27"}
    ]

    result = get_news_signal("onion", "kolar", "2026-04-28", articles)

    assert result["news_signal"] == 0.0
    assert result["confidence"] == 0.0
    assert result["num_articles"] == 0
    assert result["events_detected"] == []


def test_get_news_signal_detects_event_and_scales_confidence():
    articles = [
        {
            "title": "Onion shortage hits mandi",
            "description": "Shortage pushes prices up",
            "published_at": "2026-04-28",
        }
    ]

    result = get_news_signal("onion", "kolar", "2026-04-28", articles)

    assert pytest.approx(result["news_signal"], rel=1e-3) == 0.6
    assert pytest.approx(result["confidence"], rel=1e-3) == 0.3
    assert result["num_articles"] == 1
    assert result["events_detected"] == ["shortage"]


def test_get_news_signal_handles_conflicting_signals():
    articles = [
        {
            "title": "Price surge expected for tomato",
            "description": "Demand is strong",
            "published_at": "2026-04-28",
        },
        {
            "title": "Export ban for onions",
            "description": "Supply constrained",
            "published_at": "2026-04-28",
        },
    ]

    result = get_news_signal("tomato", "kolar", "2026-04-28", articles)

    assert result["num_articles"] == 2
    assert "price surge" in result["events_detected"]
    assert "export ban" in result["events_detected"]
    assert result["news_signal"] != 0.0
    assert result["confidence"] < 0.5


def test_get_news_signal_ignores_future_articles():
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    articles = [
        {
            "title": "Onion shortage spills into future",
            "description": "Ahead of time signal",
            "published_at": tomorrow,
        }
    ]

    result = get_news_signal("onion", "kolar", "2026-04-28", articles)
    assert result["news_signal"] == 0.0
    assert result["confidence"] == 0.0
    assert result["num_articles"] == 0
