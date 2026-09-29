"""
Ingest-time data quality gates.

A bad price is worse than a missing one. A missing day is simply skipped; a
fat-finger print enters the store and then poisons every lag, rolling mean and
volatility feature that touches it for the next thirty days — and it does so
silently, because a number is a number.

Two independent gates, because they catch different failures:

**Absolute plausibility.** A per-commodity price envelope, derived from the
project's own archive rather than invented. This catches unit errors (a price
quoted per kilogram rather than per quintal), decimal slips and stuck-zero
fields. The bands are deliberately wide — roughly a third of the observed
minimum to several times the observed maximum — so they only ever fire on
values that are not prices of this commodity at all.

**Relative spike.** A value compared against its own series' recent median.
This is calibrated against measured behaviour, not intuition: in the real
archive the 99th percentile of day-over-day absolute log return is 0.58 (a
79% move) and the observed maximum is 1.70 (about 5.5x). Vegetable mandis
genuinely move that hard, so the threshold sits well beyond it. A tighter
gate would quietly discard the volatility the model exists to forecast.

Rejected rows are quarantined with a reason rather than dropped, so a feed
that starts misbehaving is visible in the run record instead of showing up
weeks later as unexplained model drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Per-commodity plausible price envelope in Rs/quintal, derived from the
# observed archive range and widened so only non-prices are rejected.
#   (observed min .. observed max)  ->  (floor, ceiling)
PRICE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "tomato": (100.0, 25_000.0),        # observed  300 ..  5,847
    "onion": (100.0, 30_000.0),         # observed  351 ..  7,800
    "potato": (100.0, 15_000.0),        # observed  320 ..  2,850
    "garlic": (200.0, 90_000.0),        # observed  683 .. 25,438
    "ginger": (300.0, 80_000.0),        # observed 2,000 .. 20,000
    "dry_chillies": (300.0, 60_000.0),  # observed 1,000 .. 15,800
}

# Fallback for a commodity with no declared envelope: reject only values that
# cannot be a per-quintal price in any Indian mandi.
DEFAULT_BOUNDS: Tuple[float, float] = (50.0, 200_000.0)

# |log(price / recent_median)| above this is treated as an error, not a move.
# exp(2.5) ~ 12x, against a measured historical maximum of ~5.5x.
SPIKE_LOG_THRESHOLD = 2.5

# Recent observations used to compute the comparison median.
SPIKE_REFERENCE_WINDOW = 15

# Below this many prior observations there is no reliable reference, so the
# relative gate abstains rather than guessing.
SPIKE_MIN_HISTORY = 5

REASON_OUT_OF_BOUNDS = "price_out_of_plausible_range"
REASON_SPIKE = "price_spike_vs_recent_median"
REASON_MISSING_FIELD = "missing_required_field"
REASON_NON_POSITIVE = "non_positive_price"


@dataclass
class ValidationReport:
    """What a validation pass accepted, rejected and why."""

    received: int = 0
    accepted: int = 0
    rejected: int = 0
    reasons: Dict[str, int] = field(default_factory=dict)
    samples: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        return (self.rejected / self.received) if self.received else 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "received": self.received,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "rejection_rate": round(self.rejection_rate, 4),
            "reasons": dict(self.reasons),
            # A handful of examples makes a misbehaving feed diagnosable from
            # the run record alone.
            "samples": self.samples[:10],
        }


def price_bounds(commodity: str) -> Tuple[float, float]:
    return PRICE_BOUNDS.get(str(commodity).lower(), DEFAULT_BOUNDS)


def _reference_medians(history: pd.DataFrame) -> Dict[Tuple[str, str], float]:
    """Recent median price per series, used as the spike comparison point."""
    if history is None or history.empty:
        return {}

    frame = history.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date")

    medians: Dict[Tuple[str, str], float] = {}
    for key, group in frame.groupby(["commodity", "mandi_id"], sort=False):
        if len(group) < SPIKE_MIN_HISTORY:
            continue
        recent = group["modal_price"].tail(SPIKE_REFERENCE_WINDOW)
        median = float(recent.median())
        if median > 0:
            medians[key] = median
    return medians


def validate_observations(
    records: pd.DataFrame,
    history: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, ValidationReport]:
    """
    Split incoming observations into accepted rows and quarantined rows.

    Args:
        records: candidate observations, already conformed to the store schema.
        history: existing observations, used to build the spike reference. When
            absent the relative gate abstains and only absolute bounds apply.

    Returns:
        ``(accepted, report)``. The caller stores `accepted` and logs `report`.
    """
    report = ValidationReport()

    if records is None or records.empty:
        return pd.DataFrame(columns=getattr(records, "columns", None)), report

    frame = records.copy()
    report.received = len(frame)

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")

    medians = _reference_medians(history) if history is not None else {}

    reasons: List[Optional[str]] = []
    for row in frame.itertuples(index=False):
        commodity = getattr(row, "commodity", None)
        mandi_id = getattr(row, "mandi_id", None)
        price = getattr(row, "modal_price", None)
        date = getattr(row, "date", None)

        if not commodity or not mandi_id or pd.isna(date):
            reasons.append(REASON_MISSING_FIELD)
            continue

        if price is None or pd.isna(price) or price <= 0:
            reasons.append(REASON_NON_POSITIVE)
            continue

        floor, ceiling = price_bounds(commodity)
        if not (floor <= float(price) <= ceiling):
            reasons.append(REASON_OUT_OF_BOUNDS)
            continue

        reference = medians.get((commodity, mandi_id))
        if reference:
            deviation = abs(float(np.log(float(price) / reference)))
            if deviation > SPIKE_LOG_THRESHOLD:
                reasons.append(REASON_SPIKE)
                continue

        reasons.append(None)

    frame["reject_reason"] = reasons
    rejected = frame[frame["reject_reason"].notna()]
    accepted = frame[frame["reject_reason"].isna()].drop(columns=["reject_reason"])

    report.accepted = int(len(accepted))
    report.rejected = int(len(rejected))
    for reason, count in rejected["reject_reason"].value_counts().items():
        report.reasons[str(reason)] = int(count)

    for row in rejected.head(10).itertuples(index=False):
        report.samples.append(
            {
                "date": str(getattr(row, "date", ""))[:10],
                "commodity": getattr(row, "commodity", None),
                "mandi_id": getattr(row, "mandi_id", None),
                "modal_price": getattr(row, "modal_price", None),
                "reason": getattr(row, "reject_reason", None),
            }
        )

    if report.rejected:
        logger.warning(
            "Ingest validation quarantined %d/%d rows: %s",
            report.rejected, report.received, report.reasons,
        )
    else:
        logger.info("Ingest validation passed all %d rows", report.received)

    return accepted, report
