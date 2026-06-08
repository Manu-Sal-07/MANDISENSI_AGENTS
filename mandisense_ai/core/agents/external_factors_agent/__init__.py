from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from mandisense_ai.utils.logger import get_logger
except Exception:
    from mandisense_ai.utils.logger import get_logger

from .ingestion.news_ingestor import fetch_news
from .processing.external_fusion import compute_external_impact
from .processing.news_signal import get_news_signal
from .processing.weather_signal import get_weather_signal

logger = get_logger(__name__)


def run_external_factors_agent(
    commodity: str,
    mandi: str,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the External Factors Agent and return an ensemble-ready signal."""
    if date is None:
        date = datetime.utcnow().date().isoformat()

    try:
        news_articles: List[Dict[str, Any]] = fetch_news(query=commodity, days_back=2)
        news_result = get_news_signal(commodity, mandi, date, news_articles)
        weather_result = get_weather_signal(mandi, commodity, date)

        policy_signal = 0.0
        policy_confidence = 0.0

        external_output = compute_external_impact(
            weather_signal=weather_result.get("weather_signal", 0.0),
            news_signal=news_result.get("news_signal", 0.0),
            policy_signal=policy_signal,
            weather_conf=weather_result.get("confidence", 0.0),
            news_conf=news_result.get("confidence", 0.0),
            policy_conf=policy_confidence,
        )

        return {
            "impact_score": float(external_output["impact_score"]),
            "confidence": float(external_output["confidence"]),
            "weather_result": weather_result,
            "news_result": news_result,
            "policy_signal": policy_signal,
            "policy_confidence": policy_confidence,
            "external_output": external_output,
        }
    except Exception as exc:
        logger.error(
            f"External Factors Agent failed for {commodity}/{mandi} @ {date}: {exc}",
            exc_info=True,
        )
        return {
            "impact_score": 0.0,
            "confidence": 0.0,
            "weather_result": {},
            "news_result": {},
            "policy_signal": 0.0,
            "policy_confidence": 0.0,
            "external_output": {
                "impact_score": 0.0,
                "confidence": 0.0,
                "components": {"weather": 0.0, "policy": 0.0, "news": 0.0},
            },
        }
