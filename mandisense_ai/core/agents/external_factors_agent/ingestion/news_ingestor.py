from datetime import datetime, timezone

from mandisense_ai.utils.logger import get_logger
from mandisense_ai.core.agents.external_factors_agent.utils.text_utils import normalize_text
from mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher import fetch_bbc_news

logger = get_logger(__name__)

FALLBACK_DATA = [
    {"title": "India bans onion export", "description": "Export restriction imposed", "date": "2026-04-20"},
    {"title": "Import duty reduced on pulses", "description": "Imports expected to rise", "date": "2026-04-18"},
    {"title": "Heavy rainfall damages tomato crops", "description": "Flood conditions", "date": "2026-04-21"},
    {"title": "Drought in Karnataka affects rice", "description": "Low rainfall impact", "date": "2026-04-17"},
    {"title": "MSP increased for wheat", "description": "Government policy", "date": "2026-04-19"},
    {"title": "Fuel prices rise", "description": "Transport costs increase", "date": "2026-04-22"},
    {"title": "Export demand rises for rice", "description": "Global demand surge", "date": "2026-04-16"},
    {"title": "Stock limit imposed on onions", "description": "Anti-hoarding step", "date": "2026-04-21"},
]


def _normalize_date(value: str) -> str:
    if not isinstance(value, str):
        return datetime.utcnow().date().isoformat()
    date_str = value.replace("/", "-").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str).date().isoformat()
    except ValueError:
        return datetime.now(timezone.utc).date().isoformat()


def _normalize_fallback_article(item: dict) -> dict:
    formatted_date = _normalize_date(item.get("date", ""))
    return {
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "published_at": formatted_date,
        "date": formatted_date,
    }


def fetch_news(query: str | None = None, days_back: int = 2):
    """Fetch BBC news articles and fallback to deterministic sample data on failure."""
    try:
        articles = fetch_bbc_news(query=query, days_back=days_back)
        return [
            {
                "title": article["title"],
                "description": article["description"],
                "published_at": article["published_at"],
                "date": article["published_at"],
            }
            for article in articles
        ]
    except Exception as exc:
        logger.warning(f"BBC news fetch failed, using fallback dataset: {exc}")
        return [_normalize_fallback_article(item) for item in FALLBACK_DATA]
