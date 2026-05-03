from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher import (
    DEFAULT_CACHE_DIR,
    NewsFetchError,
    fetch_bbc_news,
)


def _build_article(title: str, description: str, published_at: str):
    return {
        "title": title,
        "description": description,
        "publishedAt": published_at,
    }


def test_fetch_bbc_news_parses_and_filters_recent_articles(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).date()
    recent_date = today.isoformat()
    old_date = (today - timedelta(days=10)).isoformat()

    def fake_request(*args, **kwargs):
        return {
            "status": "ok",
            "articles": [
                _build_article("Farm output rises", "Strong harvest expected", recent_date + "T12:00:00Z"),
                _build_article("Farm output rises", "Duplicate headline content", recent_date + "T13:00:00Z"),
                _build_article("Old news", "Should be filtered out", old_date + "T08:00:00Z"),
            ],
        }

    monkeypatch.setattr(
        "mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher._request_bbc_news",
        fake_request,
    )

    result = fetch_bbc_news(
        query="agriculture",
        days_back=2,
        api_key="test-key",
        use_cache=False,
        cache_dir=tmp_path,
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "farm output rises"
    assert result[0]["description"] == "strong harvest expected"
    assert result[0]["published_at"] == recent_date


def test_fetch_bbc_news_raises_without_api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher.config.api_keys",
        {"news_api": "dummy"},
    )

    with pytest.raises(NewsFetchError):
        fetch_bbc_news(query="market", days_back=1, use_cache=False, cache_dir=tmp_path)


def test_fetch_bbc_news_caches_results(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).date().isoformat()
    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        return {
            "status": "ok",
            "articles": [
                {
                    "title": "Market watch",
                    "description": "Prices remain stable.",
                    "publishedAt": today + "T09:00:00Z",
                }
            ],
        }

    monkeypatch.setattr(
        "mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher._request_bbc_news",
        fake_request,
    )
    monkeypatch.setattr(
        "mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher.config.api_keys",
        {"news_api": "test-key"},
    )

    first = fetch_bbc_news(query="market", days_back=1, api_key="test-key", cache_dir=tmp_path)
    second = fetch_bbc_news(query="market", days_back=1, api_key="test-key", cache_dir=tmp_path)

    assert calls["count"] == 1
    assert first == second
    assert first[0]["title"] == "market watch"
    assert any(Path(tmp_path).glob("*.json"))
