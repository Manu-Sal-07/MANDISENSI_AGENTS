"""
Supply Flood Warning.

A sudden jump in how much of a crop is arriving at a mandi usually shows up
in price a few days later, before any forecast model reacts to it -- this is
the same economic relationship `features.py` already encodes as
`price_arrival_elasticity`, read here directly off recent arrivals rather
than through a trained model, so it can be checked and explained in one
sentence: "arrivals are unusually high; in this series' own history, that
has usually been followed by a price drop within a few days."

Stated honestly rather than silently degraded: the free live data.gov.in feed
this system ingests from does not publish arrival volume at all (see
`forecasting/config.py`, `arrival_dropout_rate`) -- only the historical
archive carries it. Until a volume-carrying feed is wired in, this reads the
archive's last available arrival print and says its age plainly, rather than
implying a live reading it does not have.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.forecasting.store import ObservationStore
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

FLOOD_THRESHOLD = 0.30
"""Arrivals this far above their own trailing mean are flagged as a flood."""
DROUGHT_THRESHOLD = -0.30

ARRIVAL_STALE_DAYS = 14
"""Beyond this the last arrival print is reported as historical context,
not a live reading -- the live feed carries no arrivals at all (see module
docstring), so this will very often be older than the price data next to it."""


def supply_reading(commodity: str, mandi_id: str) -> Dict[str, Any]:
    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()

    try:
        series = ObservationStore().read_series(resolved_commodity, resolved_mandi)
    except Exception as exc:
        logger.error("Supply signal: observation read failed: %s", exc)
        series = pd.DataFrame()

    if series.empty or "arrivals" not in series.columns:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "No arrival volume data for this series.",
        }

    series = series.copy()
    series["date"] = pd.to_datetime(series["date"])
    series["arrivals"] = pd.to_numeric(series["arrivals"], errors="coerce")
    carrying = series[series["arrivals"].notna() & (series["arrivals"] > 0)]

    if carrying.empty:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "UNAVAILABLE", "reason": "No recorded arrival volumes for this series.",
        }

    latest = carrying.iloc[-1]
    latest_date = pd.Timestamp(latest["date"])
    age_days = (pd.Timestamp.now(tz=None).normalize() - latest_date).days

    trailing = carrying[carrying["date"] < latest_date].tail(30)
    if len(trailing) < 5:
        return {
            "commodity": resolved_commodity, "mandi_id": resolved_mandi,
            "status": "INSUFFICIENT_HISTORY",
            "reason": "Not enough prior arrival prints to judge what is normal.",
        }

    baseline = float(trailing["arrivals"].mean())
    latest_arrivals = float(latest["arrivals"])
    deviation = (latest_arrivals - baseline) / baseline if baseline > 0 else 0.0

    if deviation >= FLOOD_THRESHOLD:
        signal = "FLOOD"
    elif deviation <= DROUGHT_THRESHOLD:
        signal = "DROUGHT"
    else:
        signal = "NORMAL"

    # A simple, checkable historical correlation: of past days where arrivals
    # were similarly elevated (or depressed), what fraction saw price fall
    # (or rise) within the next 3 days. Computed on this series' own history,
    # never asserted from a general rule.
    historical_note = None
    if signal != "NORMAL" and len(carrying) > 20:
        carrying = carrying.reset_index(drop=True)
        carrying["baseline_arrivals"] = carrying["arrivals"].rolling(30, min_periods=5).mean().shift(1)
        carrying["deviation"] = (carrying["arrivals"] - carrying["baseline_arrivals"]) / carrying["baseline_arrivals"]
        carrying["future_price"] = carrying["modal_price"].shift(-3)
        carrying["price_change_pct"] = (carrying["future_price"] - carrying["modal_price"]) / carrying["modal_price"]

        if signal == "FLOOD":
            matches = carrying[carrying["deviation"] >= FLOOD_THRESHOLD].dropna(subset=["price_change_pct"])
            direction_word = "fell"
            hit = matches[matches["price_change_pct"] < 0]
        else:
            matches = carrying[carrying["deviation"] <= DROUGHT_THRESHOLD].dropna(subset=["price_change_pct"])
            direction_word = "rose"
            hit = matches[matches["price_change_pct"] > 0]

        if len(matches) >= 5:
            rate = len(hit) / len(matches)
            historical_note = (
                f"In {len(matches)} similar past episode(s) at this mandi, price "
                f"{direction_word} within 3 days {rate * 100:.0f}% of the time."
            )

    return {
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "status": "OK",
        "signal": signal,
        "latest_arrivals": round(latest_arrivals, 1),
        "baseline_arrivals": round(baseline, 1),
        "deviation_pct": round(deviation * 100, 1),
        "as_of_date": str(latest_date.date()),
        "data_age_days": age_days,
        "is_live_reading": age_days <= ARRIVAL_STALE_DAYS,
        "historical_note": historical_note,
    }
