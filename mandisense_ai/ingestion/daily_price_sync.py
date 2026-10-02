"""
Keeps the v4 processed commodity datasets current by pulling the most
recently published day's mandi prices from data.gov.in (see
data_gov_client.py) and appending them if that date isn't already present.

This only touches the daily price/volume history the chart feature reads
(mandisense_ai/data/processed/v4/*.csv). It never writes into the
cognition engine's snapshot store and never runs the ML forecasting
pipeline — it is strictly "keep the chart's history one day fresher",
nothing else.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from mandisense_ai.ingestion.data_gov_client import find_latest_published_day
from mandisense_ai.services import candle_data_service
from mandisense_ai.utils.logger import get_logger

logger = get_logger("daily_price_sync")

_V4_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "v4"
_COMMODITIES = candle_data_service.VALID_COMMODITIES

# Government market names -> our canonical mandi_id (matches the ids
# already used inside mandisense_ai/data/processed/v4/*.csv).
_MARKET_ALIASES = {
    "kolar": "kolar_apmc",
    "bangalore": "bangalore_yeshwanthpur",
    "bengaluru": "bangalore_yeshwanthpur",
    "yeshwanthpur": "bangalore_yeshwanthpur",
    "ramanagara": "ramanagara_apmc",
    "chickballapur": "chickballapur_apmc",
    "hoskote": "hoskote_apmc",
    "nelamangala": "nelamangala_apmc",
    "anekal": "anekal_apmc",
    "doddaballapur": "doddaballapur_apmc",
    "malur": "malur_apmc",
    "magadi": "magadi_apmc",
    "kanakapura": "kanakapura_apmc",
    "sidlaghatta": "sidlaghatta_apmc",
    "channapatna": "channapatna_apmc",
    "kunigal": "kunigal_apmc",
    "bangarpet": "bangarpet_apmc",
}


def _resolve_mandi_id(market_name: str) -> Optional[str]:
    key = str(market_name).strip().lower()
    for alias, mandi_id in _MARKET_ALIASES.items():
        if alias in key:
            return mandi_id
    return None


def _safe_float(value) -> Optional[float]:
    try:
        parsed = float(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def sync_commodity(commodity: str) -> Dict[str, object]:
    csv_path = _V4_DIR / f"{commodity}.csv"
    if not csv_path.exists():
        return {"commodity": commodity, "status": "skipped", "reason": "no base dataset"}

    found = find_latest_published_day(commodity)
    if not found:
        return {"commodity": commodity, "status": "no_new_data"}

    published_date: date = found["date"]  # type: ignore[assignment]
    date_key = published_date.strftime("%Y-%m-%d")

    existing_dates = pd.read_csv(csv_path, usecols=["date"])["date"]
    if date_key in set(existing_dates):
        return {"commodity": commodity, "status": "already_current", "date": date_key}

    new_rows: List[Dict[str, object]] = []
    for record in found["records"]:  # type: ignore[union-attr]
        mandi_id = _resolve_mandi_id(record.get("market", ""))
        if not mandi_id:
            continue
        price = _safe_float(record.get("modal_price"))
        if price is None:
            continue
        new_rows.append({
            "date": date_key,
            "mandi_id": mandi_id,
            "commodity": commodity,
            "price": price,
            # This API does not publish arrival volume, so it's left blank
            # rather than guessed — the chart's volume bar just shows a gap
            # for live-only days instead of a fabricated number.
            "arrivals": None,
            "arrivals_log": None,
            "is_missing": 0,
            "is_unstable": 0,
            "is_valid_training": 0,
            "split": "live",
        })

    if not new_rows:
        return {"commodity": commodity, "status": "no_matching_mandis", "date": date_key}

    full = pd.read_csv(csv_path)
    updated = pd.concat([full, pd.DataFrame(new_rows)], ignore_index=True)
    updated.to_csv(csv_path, index=False)
    candle_data_service.invalidate_cache(commodity)

    logger.info(f"Synced {len(new_rows)} live rows for {commodity} on {date_key}")
    return {"commodity": commodity, "status": "synced", "date": date_key, "rows_added": len(new_rows)}


def sync_all() -> List[Dict[str, object]]:
    results = []
    for commodity in _COMMODITIES:
        try:
            results.append(sync_commodity(commodity))
        except Exception as exc:  # one bad commodity must never block the rest
            logger.error(f"Live sync failed for {commodity}: {exc}")
            results.append({"commodity": commodity, "status": "error", "error": str(exc)})
    return results
