"""
data.gov.in Agmarknet daily price client.

Fetches the government's "Current Daily Price of Various Commodities from
Various Markets (Mandi)" resource — the free, officially published feed that
underpins Agmarknet.

Two properties of this feed drive the design of everything downstream:

1. **It is a snapshot, not an archive.** Each call returns what markets
   reported for the current day. There is no historical range query. History
   therefore has to be *accumulated* by a job that runs every day — which is
   exactly why ingestion is scheduled rather than on-demand.

2. **Coverage is sparse and irregular.** On a given day only a subset of
   markets report a given commodity; a mandi that printed yesterday may be
   absent today. Downstream code must treat missing days as normal, never as
   an error, and must never forward-fill a price into a day the market did
   not actually trade.

The client returns price fields only. The free resource does not publish
arrival volume, so `arrivals` is emitted as None and the feature layer treats
arrival-derived inputs as optional.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from mandisense_ai.forecasting.config import (
    DATAGOV_BASE_URL,
    DATAGOV_RESOURCE_ID,
    TARGET_COMMODITIES,
    TARGET_STATES,
    get_api_key,
)
from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

PAGE_SIZE = 1000
MAX_PAGES = 25
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

SOURCE_NAME = "datagov_agmarknet"


class DataGovFetchError(RuntimeError):
    """Raised when the upstream feed cannot be read after retries."""


def _build_url(
    *,
    state: Optional[str],
    commodity: Optional[str],
    offset: int,
    limit: int,
) -> str:
    params: Dict[str, Any] = {
        "api-key": get_api_key(),
        "format": "json",
        "limit": limit,
        "offset": offset,
    }
    if state:
        # The `.keyword` suffix selects the exact-match analyzer; without it
        # multi-word states match loosely and pull in neighbouring records.
        params["filters[state.keyword]"] = state
    if commodity:
        params["filters[commodity]"] = commodity

    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"{DATAGOV_BASE_URL}/{DATAGOV_RESOURCE_ID}?{query}"


def _request(url: str) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MandiSense/1.0"})
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # network, decode, HTTP - all retryable here
            last_error = exc
            if attempt < MAX_RETRIES:
                delay = RETRY_BACKOFF_SECONDS * attempt
                logger.warning(
                    "data.gov.in request failed (attempt %d/%d): %s — retrying in %ds",
                    attempt, MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
    raise DataGovFetchError(f"data.gov.in unreachable after {MAX_RETRIES} attempts: {last_error}")


def _parse_date(value: Any) -> Optional[pd.Timestamp]:
    """
    Parse the feed's arrival_date.

    The feed writes DD/MM/YYYY. This is parsed with an explicit format rather
    than letting pandas infer, because inference on day<=12 silently produces
    a month/day transposition — the exact defect that corrupted this project's
    historical archive before.
    """
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt))
        except ValueError:
            continue
    logger.debug("Unparseable arrival_date from feed: %r", value)
    return None


def _to_records(raw_records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    ingested_at = datetime.utcnow().isoformat() + "Z"

    for raw in raw_records:
        commodity = canonical_commodity(raw.get("commodity", ""))
        mandi_id = canonical_market(raw.get("market", ""))
        date = _parse_date(raw.get("arrival_date"))

        if not commodity or not mandi_id or date is None:
            continue
        if commodity not in TARGET_COMMODITIES:
            continue

        rows.append(
            {
                "date": date,
                "commodity": commodity,
                "mandi_id": mandi_id,
                "modal_price": raw.get("modal_price"),
                "min_price": raw.get("min_price"),
                "max_price": raw.get("max_price"),
                # The free daily-price resource does not publish volume.
                "arrivals": None,
                "state": raw.get("state"),
                "district": raw.get("district"),
                "source": SOURCE_NAME,
                "ingested_at": ingested_at,
            }
        )

    return rows


def fetch_daily_prices(
    states: Iterable[str] = TARGET_STATES,
    commodities: Iterable[str] = TARGET_COMMODITIES,
) -> pd.DataFrame:
    """
    Pull the current day's prices for the configured states and commodities.

    Returns a frame conforming to the observation store schema. Partial
    failures are tolerated: if one (state, commodity) slice fails, the rest of
    the run still produces data and the failure is logged. A run only raises
    if *every* slice failed, which is the signal that the feed itself is down.
    """
    collected: List[Dict[str, Any]] = []
    attempted = 0
    failed = 0

    for state in states:
        for commodity in commodities:
            attempted += 1
            # Feed commodity names are title-cased ("Tomato"); canonical ids
            # are lowercase slugs.
            upstream_commodity = commodity.replace("_", " ").title()
            try:
                offset = 0
                for _ in range(MAX_PAGES):
                    url = _build_url(
                        state=state,
                        commodity=upstream_commodity,
                        offset=offset,
                        limit=PAGE_SIZE,
                    )
                    payload = _request(url)
                    records = payload.get("records", []) or []
                    collected.extend(_to_records(records))

                    total = int(payload.get("total", 0) or 0)
                    offset += len(records)
                    if not records or offset >= total:
                        break
            except DataGovFetchError as exc:
                failed += 1
                logger.error("Fetch failed for %s/%s: %s", state, upstream_commodity, exc)

    if attempted and failed == attempted:
        raise DataGovFetchError("All upstream slices failed; treating feed as unavailable")

    frame = pd.DataFrame(collected)
    logger.info(
        "data.gov.in fetch complete: %d rows across %d slices (%d failed)",
        len(frame), attempted, failed,
    )
    return frame
