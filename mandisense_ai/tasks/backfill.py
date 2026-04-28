"""
Background Tasks — Outcome Backfill Pipeline.

Backfills actual 7-day price changes into prediction log records
whose prediction horizon has elapsed.

Usage:
  CLI:    python -m tasks.backfill
  Celery: backfill_outcomes.delay()
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def run_backfill() -> dict:
    """
    Backfill actual outcomes for predictions whose 7-day horizon has passed.

    Reads unfilled records from prediction log, looks up actual prices,
    and computes the realized 7-day percentage change.

    Returns:
        Summary dict with counts of updated records.
    """
    from ensemble.prediction_logger import PredictionLogger

    logger.info("[Backfill] Starting outcome backfill...")

    plogger = PredictionLogger()
    all_records = plogger.read_all()

    # Find unfilled records older than 7 days
    now = datetime.utcnow()
    candidates = [
        r for r in all_records
        if r.get("actual_7d_change") is None
        and _is_older_than(r.get("timestamp", ""), days=7, reference=now)
    ]

    if not candidates:
        logger.info("[Backfill] No records to backfill")
        return {"status": "ok", "updated": 0, "candidates": 0}

    logger.info(f"[Backfill] Found {len(candidates)} unfilled records past 7-day horizon")

    # Attempt to look up actual prices
    updated_total = 0
    for record in candidates:
        commodity = record.get("commodity", "")
        mandi = record.get("mandi", "")
        timestamp = record.get("timestamp", "")

        actual = _lookup_actual_change(commodity, mandi, timestamp)
        if actual is not None:
            count = plogger.backfill_actual(commodity, mandi, timestamp, actual)
            updated_total += count

    result = {
        "status": "ok",
        "candidates": len(candidates),
        "updated": updated_total,
        "timestamp": now.isoformat() + "Z",
    }
    logger.info(f"[Backfill] Complete: {result}")
    return result


def _is_older_than(timestamp_str: str, days: int, reference: datetime) -> bool:
    """Check if a timestamp string is older than N days from reference."""
    try:
        ts = datetime.fromisoformat(timestamp_str.rstrip("Z"))
        return (reference - ts).days >= days
    except (ValueError, TypeError):
        return False


def _lookup_actual_change(commodity: str, mandi: str, prediction_timestamp: str) -> float | None:
    """
    Look up the actual 7-day price change from market data.

    This is a placeholder that should be connected to the actual
    market_prices database table in production.

    Returns:
        Percentage change over 7 days, or None if data unavailable.
    """
    # TODO: Connect to PostgreSQL market_prices table
    # SELECT modal_price FROM market_prices
    # WHERE commodity = ? AND mandi = ?
    # AND price_date IN (prediction_date, prediction_date + 7)
    #
    # actual_change = ((price_t7 - price_t0) / price_t0) * 100.0

    try:
        import pandas as pd
        data_dir = Path("data") / "processed"

        # Try loading from existing processed CSV files
        price_file = data_dir / f"{commodity}_{mandi}_prices.csv"
        if not price_file.exists():
            return None

        df = pd.read_csv(price_file, parse_dates=["date"])
        pred_date = datetime.fromisoformat(prediction_timestamp.rstrip("Z")).date()
        target_date = pred_date + timedelta(days=7)

        # Find prices
        df_pred = df[df["date"].dt.date == pred_date]
        df_target = df[df["date"].dt.date == target_date]

        if df_pred.empty or df_target.empty:
            return None

        p0 = float(df_pred.iloc[0]["modal_price"])
        p7 = float(df_target.iloc[0]["modal_price"])

        if p0 == 0:
            return None

        return ((p7 - p0) / p0) * 100.0

    except Exception:
        return None


# ── CLI Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_backfill()
    print(json.dumps(result, indent=2, default=str))
