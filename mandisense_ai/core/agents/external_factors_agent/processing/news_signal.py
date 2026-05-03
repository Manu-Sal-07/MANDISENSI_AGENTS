"""
News signal extraction for the External Factors Agent.

Transforms structured BBC news articles into a bounded signal describing
expected commodity price impact.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

RELEVANCE_KEYWORDS = [
    "onion",
    "tomato",
    "vegetable",
    "crop",
    "agriculture",
    "mandi",
    "price",
]

EVENT_MAP: Dict[str, float] = {
    "export ban": -0.8,
    "import duty cut": -0.5,
    "shortage": 0.6,
    "price surge": 0.5,
    "crop damage": 0.7,
    "flood": 0.6,
    "heavy rain": 0.5,
    "drought": 0.7,
    "bumper harvest": -0.6,
    "oversupply": -0.6,
    "price crash": -0.7,
}

WEIGHT_LAMBDA = 0.5
MAX_CONFIDENCE_ARTICLES = 5
INDIA_KEYWORDS = ["india", "indian", "bharat"]


def _normalize_text(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def _is_relevant_article(article: Dict[str, Any], commodity: str) -> bool:
    title = _normalize_text(article.get("title", ""))
    description = _normalize_text(article.get("description", ""))
    combined = f"{title} {description}"

    if commodity.lower() in combined:
        return True
    return any(keyword in combined for keyword in RELEVANCE_KEYWORDS)


def _extract_article_events(text: str) -> List[float]:
    signals: List[float] = []
    for phrase, signal in EVENT_MAP.items():
        if phrase in text:
            signals.append(signal)
    return signals


def _article_weight(published_at: datetime, current_date: datetime, text: str) -> float:
    days_diff = max(0, (current_date.date() - published_at.date()).days)
    weight = math.exp(-WEIGHT_LAMBDA * days_diff)
    if any(keyword in text for keyword in INDIA_KEYWORDS):
        weight *= 1.2
    return min(weight, 1.0)


def _resolve_signal_conflict(raw_signal: float, signal_values: List[float], confidence: float) -> tuple[float, float]:
    if not signal_values:
        return 0.0, 0.0

    positive = any(s > 0 for s in signal_values)
    negative = any(s < 0 for s in signal_values)

    if positive and negative:
        adjusted_signal = raw_signal * 0.75
        adjusted_confidence = confidence * 0.75
        return adjusted_signal, adjusted_confidence

    return raw_signal, confidence


def _bounded_float(value: float) -> float:
    return float(max(-1.0, min(1.0, value)))


def get_news_signal(
    commodity: str,
    mandi: str,
    date: str,
    news_articles: List[Dict[str, Any]],
    *,
    lambda_decay: float = WEIGHT_LAMBDA,
    india_priority: bool = True,
    min_events_required: int = 1,
) -> Dict[str, Any]:
    """Convert raw news articles into a bounded commodity news signal."""
    current_date = _parse_date(date)
    if current_date is None:
        raise ValueError(f"Invalid current_date format: {date}")
    current_date = current_date.astimezone(timezone.utc)

    commodity_key = commodity.lower().strip()
    processed_articles: List[Dict[str, Any]] = []
    events_detected: List[str] = []

    for article in news_articles:
        parsed_date = _parse_date(article.get("published_at") or article.get("date"))
        if parsed_date is None or parsed_date > current_date:
            continue

        if not _is_relevant_article(article, commodity_key):
            continue

        title = _normalize_text(article.get("title", ""))
        description = _normalize_text(article.get("description", ""))
        combined_text = f"{title} {description}".strip()
        if not combined_text:
            continue

        signals = _extract_article_events(combined_text)
        if not signals:
            continue

        raw_signal = sum(signals) / len(signals)
        if abs(raw_signal) < 0.1:
            continue

        days_diff = max(0, (current_date.date() - parsed_date.date()).days)
        weight = math.exp(-lambda_decay * days_diff)
        if india_priority and any(keyword in combined_text for keyword in INDIA_KEYWORDS):
            weight *= 1.2
        weight = min(weight, 1.0)

        processed_articles.append(
            {
                "raw_signal": raw_signal,
                "weight": weight,
                "event_phrases": [phrase for phrase in EVENT_MAP if phrase in combined_text],
                "published_at": parsed_date.date().isoformat(),
            }
        )
        events_detected.extend([phrase for phrase in EVENT_MAP if phrase in combined_text])

    if not processed_articles:
        logger.info(f"News signal: no relevant articles for {commodity}/{mandi} @ {date}")
        return {
            "news_signal": 0.0,
            "confidence": 0.0,
            "num_articles": 0,
            "events_detected": [],
        }

    total_weight = sum(item["weight"] for item in processed_articles)
    if total_weight <= 0:
        return {
            "news_signal": 0.0,
            "confidence": 0.0,
            "num_articles": len(processed_articles),
            "events_detected": sorted(set(events_detected)),
        }

    weighted_sum = sum(item["raw_signal"] * item["weight"] for item in processed_articles)
    raw_news_signal = weighted_sum / total_weight

    noise_penalty = 0.9 if len(processed_articles) < min_events_required else 1.0
    raw_news_signal *= noise_penalty

    base_confidence = min(1.0, len(processed_articles) / MAX_CONFIDENCE_ARTICLES)
    sign_counts = Counter(math.copysign(1, item["raw_signal"]) for item in processed_articles)
    if len(sign_counts) > 1:
        base_confidence *= 0.75
    else:
        base_confidence = min(1.0, base_confidence + 0.1)

    final_signal, final_confidence = _resolve_signal_conflict(
        raw_news_signal,
        [item["raw_signal"] for item in processed_articles],
        base_confidence,
    )
    final_signal = _bounded_float(final_signal)
    final_confidence = float(max(0.0, min(1.0, final_confidence)))

    logger.debug(
        f"News signal computed for {commodity}/{mandi}@{date}: {final_signal} "
        f"confidence={final_confidence} articles={len(processed_articles)}"
    )

    return {
        "news_signal": final_signal,
        "confidence": final_confidence,
        "num_articles": len(processed_articles),
        "events_detected": sorted(set(events_detected)),
    }
