"""
BBC News fetcher for the External Factors Agent.

Fetches BBC news articles, normalizes text, filters by recency, removes duplicates,
and caches results to reduce repeated API calls.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

try:
    from mandisense_ai.utils.logger import get_logger
except Exception:  # pragma: no cover - fallback for direct script use
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
else:
    logger = get_logger(__name__)

from mandisense_ai.core.agents.external_factors_agent.orchestration.config_manager import config

BBC_NEWS_API_URL = "https://newsapi.org/v2/everything"
BBC_NEWS_SOURCE = "bbc-news"
DEFAULT_CACHE_DIR = Path("data/cache/news")
DEFAULT_QUERY = "bbc"
DEFAULT_DAYS_BACK = 30
DEFAULT_PAGE_SIZE = 100
DEFAULT_CACHE_TTL_SECONDS = 3600


class NewsFetchError(RuntimeError):
    """Raised when BBC news cannot be fetched or parsed."""


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip().lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"[^a-z0-9 .,;:\-_'&]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_published_date(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        published = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(published)
        return dt.date().isoformat()
    except ValueError:
        return None


def _validate_inputs(query: Optional[str], days_back: int) -> tuple[str, int]:
    query_text = query.strip() if isinstance(query, str) and query.strip() else DEFAULT_QUERY
    if not isinstance(days_back, int) or days_back < 0:
        raise ValueError("days_back must be a non-negative integer")
    return query_text, days_back


def _cache_key(query: str, days_back: int, current_date: str) -> str:
    payload = {
        "query": query,
        "days_back": days_back,
        "current_date": current_date,
        "source": "bbc_news",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _read_cache(cache_path: Path, ttl_seconds: int) -> Optional[List[Dict[str, Any]]]:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        fetched_at = float(payload.get("fetched_at", 0))
        if time.time() - fetched_at > ttl_seconds:
            return None
        return payload.get("articles")
    except Exception as exc:
        logger.warning(f"BBC news cache read failed {cache_path}: {exc}")
        return None


def _write_cache(cache_path: Path, articles: List[Dict[str, Any]]) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"fetched_at": time.time(), "articles": articles}, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning(f"BBC news cache write failed {cache_path}: {exc}")


def _request_bbc_news(
    query: str,
    from_date: str,
    to_date: str,
    api_key: str,
    timeout: int,
    max_retries: int,
    backoff_seconds: float,
) -> Dict[str, Any]:
    params = {
        "apiKey": api_key,
        "sources": BBC_NEWS_SOURCE,
        "pageSize": DEFAULT_PAGE_SIZE,
        "sortBy": "publishedAt",
        "language": "en",
        "from": from_date,
        "to": to_date,
    }
    if query:
        params["q"] = query

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(BBC_NEWS_API_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "ok" or "articles" not in payload:
                raise NewsFetchError(f"BBC News API returned unexpected payload: {payload}")
            return payload
        except Exception as exc:
            last_error = exc
            logger.warning(f"BBC News request failed attempt={attempt}/{max_retries}: {exc}")
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)
    raise NewsFetchError(f"BBC News request failed after {max_retries} attempts: {last_error}")


def _extract_articles(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    articles = []
    for item in payload.get("articles", []):
        title = _normalize_text(item.get("title"))
        description = _normalize_text(item.get("description") or item.get("content") or "")
        published_at = _parse_published_date(item.get("publishedAt") or item.get("published_at"))

        if not title or not description or not published_at:
            continue
        articles.append(
            {
                "title": title,
                "description": description,
                "published_at": published_at,
            }
        )
    return articles


def _filter_recent_articles(articles: List[Dict[str, Any]], days_back: int, current_date: datetime) -> List[Dict[str, Any]]:
    cutoff = (current_date - timedelta(days=days_back)).date()
    filtered: List[Dict[str, Any]] = []
    for article in articles:
        try:
            published = datetime.fromisoformat(article["published_at"]).date()
        except Exception:
            continue
        if published >= cutoff:
            filtered.append(article)
    return filtered


def _deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_titles = set()
    deduped: List[Dict[str, Any]] = []
    for article in articles:
        title = article["title"].strip()
        if title in seen_titles:
            continue
        seen_titles.add(title)
        deduped.append(article)
    return deduped


def fetch_bbc_news(
    query: Optional[str] = None,
    days_back: int = DEFAULT_DAYS_BACK,
    *,
    api_key: Optional[str] = None,
    cache_dir: Union[str, Path] = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
    timeout: int = 10,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    fallback_if_empty: bool = True,
) -> List[Dict[str, Any]]:
    """Fetch and return cleaned BBC news articles for the last `days_back` days."""
    query_text, valid_days_back = _validate_inputs(query, days_back)
    current = datetime.now(timezone.utc)
    current_date = current.date().isoformat()
    cache_path = Path(cache_dir) / f"{_cache_key(query_text, valid_days_back, current_date)}.json"

    if use_cache:
        cached = _read_cache(cache_path, cache_ttl_seconds)
        if cached is not None:
            logger.info(f"BBC news loaded from cache: {cache_path}")
            return cached

    api_key = api_key or getattr(config, "api_keys", {}).get("news_api")
    if not api_key or api_key == "dummy":
        raise NewsFetchError("Missing valid NEWS_API_KEY for BBC News API")

    payload = _request_bbc_news(
        query_text,
        (current - timedelta(days=valid_days_back)).date().isoformat(),
        current_date,
        api_key,
        timeout,
        max_retries,
        backoff_seconds,
    )

    articles = _extract_articles(payload)
    articles = _filter_recent_articles(articles, valid_days_back, current)
    articles = _deduplicate_articles(articles)

    if use_cache:
        _write_cache(cache_path, articles)

    if not articles and query_text != DEFAULT_QUERY and fallback_if_empty:
        logger.info(
            f"No BBC articles found for query='{query_text}' in the last {valid_days_back} days; retrying with broader default query='{DEFAULT_QUERY}'"
        )
        return fetch_bbc_news(
            DEFAULT_QUERY,
            days_back=valid_days_back,
            api_key=api_key,
            cache_dir=cache_dir,
            use_cache=use_cache,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            fallback_if_empty=False,
        )

    return articles
