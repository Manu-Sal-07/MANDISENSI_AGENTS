"""
Did We Get It Right -- the public track record.

Every other feature asks the farmer to trust a number. This is the one that
checks whether trusting it has paid off, using the same forecast ledger
that `/v1/institutional/metrics` reports system-wide (see
`forecasting/ledger.py`), narrowed here to one series so the answer is
"has this mandi's tomato forecast been reliable" rather than an average
across a hundred series a farmer never asked about.

Inherits the ledger's own honesty gate: below `MIN_SCORED_FOR_RATE` scored
outcomes, no rate is claimed. A brand-new series with zero history behind
it correctly reports "not enough resolved calls yet," not a fabricated
"100% accurate" from an empty sample.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mandisense_ai.forecasting.ledger import ForecastLedger
from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def track_record(
    commodity: str,
    mandi_id: str,
    horizon_days: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()

    try:
        performance = ForecastLedger().live_performance(
            horizon=horizon_days, commodity=resolved_commodity, mandi_id=resolved_mandi
        )
    except Exception as exc:
        logger.error("Track record: ledger read failed: %s", exc)
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "ERROR", "reason": "Could not read the forecast ledger.",
        }

    performance["commodity"] = resolved_commodity
    performance["mandi_id"] = resolved_mandi
    return performance
