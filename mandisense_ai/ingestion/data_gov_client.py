"""
Thin client for the Government of India's free daily mandi price feed
("Variety-wise Daily Market Prices Data of Commodity", data.gov.in resource
9ef84268-d588-465a-a308-a864a43d0070 — published by the Ministry of
Agriculture & Farmers Welfare via the AGMARKNET portal).

Get your own free key at https://data.gov.in (sign in, then My Account ->
API Keys) and set it as DATA_GOV_API_KEY. Without one, this falls back to
data.gov.in's shared public sample key, which works but is rate-limited
and not meant for anything beyond local development/testing.

Docs: https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Dict, List, Optional

import requests

from mandisense_ai.utils.logger import get_logger

logger = get_logger("data_gov_client")

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
PUBLIC_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571"
REQUEST_TIMEOUT = 12
PAGE_SIZE = 200
MAX_PAGES = 5


def _api_key() -> str:
    return os.getenv("DATA_GOV_API_KEY", PUBLIC_SAMPLE_KEY)


def fetch_commodity_day(commodity: str, on_date: date, state: str = "Karnataka") -> List[Dict[str, object]]:
    """
    Pulls every market row published for `commodity` in `state` on `on_date`.
    Returns [] on any failure or if the government hasn't published that
    date yet (a 1-3 day lag is normal) — callers should treat an empty list
    as "try an earlier date", not as an error.
    """
    records: List[Dict[str, object]] = []
    date_str = on_date.strftime("%d/%m/%Y")

    for page in range(MAX_PAGES):
        params = {
            "api-key": _api_key(),
            "format": "json",
            "limit": PAGE_SIZE,
            "offset": page * PAGE_SIZE,
            "filters[state]": state,
            "filters[commodity]": commodity.title(),
            "filters[arrival_date]": date_str,
        }
        try:
            resp = requests.get(
                BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (MandiSenseAI market-data sync)"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning(f"data.gov.in fetch failed for {commodity}@{state} {date_str}: {exc}")
            break

        page_records = payload.get("records", [])
        if not isinstance(page_records, list):
            break
        records.extend(page_records)

        total = int(payload.get("total", len(records)) or 0)
        if len(page_records) < PAGE_SIZE or len(records) >= total:
            break

    return records


def find_latest_published_day(
    commodity: str, state: str = "Karnataka", max_lookback_days: int = 6
) -> Optional[Dict[str, object]]:
    """
    Government mandi data typically lags 1-3 days behind today. Walk
    backwards from yesterday until a day with published records turns up,
    or give up after `max_lookback_days`.
    """
    for offset in range(1, max_lookback_days + 1):
        probe_date = date.today() - timedelta(days=offset)
        records = fetch_commodity_day(commodity, probe_date, state=state)
        if records:
            return {"date": probe_date, "records": records}
    return None
