import mandisense_ai.core.agents.external_factors_agent as external_agent
from mandisense_ai.core.agents.external_factors_agent import run_external_factors_agent


def test_run_external_factors_agent_returns_external_signal(monkeypatch):
    sample_news = [
        {
            "title": "Heavy rain damages tomato crop",
            "description": "Flooding leads to shortages",
            "published_at": "2026-04-27T12:00:00Z",
        }
    ]

    sample_news_result = {
        "news_signal": 0.6,
        "confidence": 0.8,
        "num_articles": 1,
        "events_detected": ["heavy rain"],
    }
    sample_weather_result = {
        "weather_signal": -0.4,
        "confidence": 0.9,
        "components": {"rain_signal": 0.5, "temp_signal": -0.1},
    }
    sample_external_output = {"impact_score": 0.01, "confidence": 0.75}

    monkeypatch.setattr(
        external_agent,
        "fetch_news",
        lambda query, days_back: sample_news,
    )
    monkeypatch.setattr(
        external_agent,
        "get_news_signal",
        lambda commodity, mandi, date, news_articles: sample_news_result,
    )
    monkeypatch.setattr(
        external_agent,
        "get_weather_signal",
        lambda mandi, commodity, date: sample_weather_result,
    )
    monkeypatch.setattr(
        external_agent,
        "compute_external_impact",
        lambda weather_signal, news_signal, policy_signal, weather_conf, news_conf, policy_conf: sample_external_output,
    )

    result = run_external_factors_agent("tomato", "kolar", "2026-04-28")

    assert result["impact_score"] == 0.01
    assert result["confidence"] == 0.75
    assert result["news_result"] == sample_news_result
    assert result["weather_result"] == sample_weather_result
    assert result["policy_signal"] == 0.0
    assert result["policy_confidence"] == 0.0
