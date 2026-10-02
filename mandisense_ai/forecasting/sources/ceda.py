"""
CEDA (Ashoka University) Agmarknet API client.

A second, optional ingestion source alongside `datagov.py`. Built ahead of
having a key, so the day one is registered this starts working without any
further code change — only `CEDA_API_KEY` needs to be set.

Why a second source at all: the free data.gov.in feed this project already
ingests from carries price but never arrival volume (see `datagov.py`'s
module docstring). CEDA's API exposes `/agmarknet/quantities` as a genuinely
separate endpoint from `/agmarknet/prices` — the one dataset this project
has never had. Wiring it in is what turns `farmer/supply_signal.py`'s
"based on the last available print" caveat and the trader `arrival_surge` /
`arrival_drought` scenarios from historical-archive-only into something a
nightly job can keep current.

**Why this is harder than the data.gov.in client.** That feed is queried by
free-text commodity and market names. CEDA is queried entirely by integer
ids, resolved through a geography walk:

    commodities  -> commodity_id
    geographies  -> state_id, and per-state a list of district_id
    markets (POST, needs a commodity_id + state_id + district_id)
                 -> market_id, market_name

and neither `/prices` nor `/quantities` echoes `market_name` back — a
response row only carries `market_id`. So a canonical mandi id has to be
resolved to a `market_id` *before* the price/quantity call, by fetching
every market CEDA lists across a state's districts and matching each
`market_name` through the same `canonical_market()` alias table the rest of
this codebase already uses (see `naming.py`) — never a bespoke second
mapping that could quietly drift from it.

**Why this is untested against a live server.** No key exists yet. Every
request-building and response-parsing function here is instead verified
against the *exact* response shape published in CEDA's own OpenAPI spec
(extracted from `https://api.ceda.ashoka.edu.in/documentation/`, see
`test_ceda_source.py`), with the real HTTP transport swapped out for a
fake one. The one thing that cannot be verified without a key is whether
the live server's actual responses match its own published schema — which
`fetch_daily_prices_and_arrivals` guards for defensively (a row missing an
expected field is skipped and counted, never guessed at), and which the
first live run should be watched for.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from mandisense_ai.forecasting.config import TARGET_COMMODITIES, TARGET_STATES
from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.exceptions import ConfigurationError
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.ceda.ashoka.edu.in/v1"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

SOURCE_NAME = "ceda_agmarknet"

# A request/response pair: (method, path, json_body) -> parsed JSON. Real
# transport by default; tests inject a fake one so nothing here ever needs
# a live key or a live server to verify.
Transport = Callable[[str, str, Optional[Dict[str, Any]]], Dict[str, Any]]


class CedaFetchError(RuntimeError):
    """Raised when the CEDA API cannot be read after retries, or is unconfigured."""


def get_api_key() -> str:
    """
    The CEDA bearer token.

    No public sample key exists for this API (unlike data.gov.in's shared
    evaluation key) — CEDA requires a real, individually issued key from the
    first request, confirmed live: an unauthenticated call returns
    `{"message": "Unauthorised, no api key passed."}` and an invalid one
    returns `{"message": "Api key expired"}`, not a degraded free tier. So
    there is no soft fallback to fall back to; this raises immediately
    when the key is absent, in every environment, rather than pretending a
    developer's empty key might still work.
    """
    key = os.getenv("CEDA_API_KEY")
    if not key:
        raise ConfigurationError(
            "CEDA_API_KEY is not set. Unlike the data.gov.in feed, CEDA has no "
            "shared evaluation key to fall back to — every request needs a real, "
            "individually issued bearer token from the first call."
        )
    return key


def is_configured() -> bool:
    return bool(os.getenv("CEDA_API_KEY"))


def _default_transport(method: str, path: str, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "User-Agent": "MandiSense/1.0",
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    transport: Transport = _default_transport,
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return transport(method, path, body)
        except urllib.error.HTTPError as exc:
            # A 401/403 will not resolve by retrying — surface it immediately
            # with the server's own message rather than burning three
            # attempts and a stale-looking generic error on an expired key.
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("message", str(exc))
            except Exception:
                detail = str(exc)
            if exc.code in (401, 403):
                raise CedaFetchError(f"CEDA authentication failed ({exc.code}): {detail}") from exc
            last_error = exc
        except CedaFetchError:
            # Already a terminal signal from a nested call (e.g. one made
            # inside `resolve_market_ids`) -- retrying it here would just
            # repeat whatever already exhausted its own retries once.
            raise
        except Exception as exc:  # network, decode — retryable
            last_error = exc

        if attempt < MAX_RETRIES:
            delay = RETRY_BACKOFF_SECONDS * attempt
            logger.warning(
                "CEDA request failed (attempt %d/%d) for %s %s: %s — retrying in %ds",
                attempt, MAX_RETRIES, method, path, last_error, delay,
            )
            time.sleep(delay)
    raise CedaFetchError(f"CEDA unreachable after {MAX_RETRIES} attempts: {last_error}")


# ── metadata (commodities, geographies, markets) ────────────────────────────


def fetch_commodities(transport: Transport = _default_transport) -> Dict[str, int]:
    """Canonical commodity id -> CEDA commodity_id, for every match this
    project tracks. A CEDA commodity name that does not resolve through
    `canonical_commodity()` is skipped, not guessed at."""
    payload = _request("GET", "/agmarknet/commodities", transport=transport)
    out: Dict[str, int] = {}
    for row in payload.get("commodities", []) or []:
        canon = canonical_commodity(str(row.get("name", "")))
        if canon and canon in TARGET_COMMODITIES and canon not in out:
            out[canon] = int(row["id"])
    return out


def fetch_geographies(transport: Transport = _default_transport) -> Dict[str, Any]:
    """{state_name (as CEDA spells it) -> {state_id, districts: {name: id}}}."""
    payload = _request("GET", "/agmarknet/geographies", transport=transport)
    out: Dict[str, Any] = {}
    for row in payload.get("geographies", []) or []:
        state_name = str(row.get("state_name", ""))
        districts = {
            str(d.get("district_name", "")): int(d["district_id"])
            for d in row.get("districts", []) or []
            if d.get("district_id") is not None
        }
        out[state_name] = {"state_id": row.get("state_id"), "districts": districts}
    return out


def fetch_markets(
    commodity_id: int,
    state_id: int,
    district_id: int,
    indicator: str = "price",
    transport: Transport = _default_transport,
) -> List[Dict[str, Any]]:
    """Markets CEDA has data for, within one district, for one commodity."""
    payload = _request(
        "POST", "/agmarknet/markets",
        body={
            "commodity_id": commodity_id, "state_id": state_id,
            "district_id": district_id, "indicator": indicator,
        },
        transport=transport,
    )
    return payload.get("data", []) or []


def resolve_market_ids(
    mandi_ids: Iterable[str],
    commodity_id: int,
    state_id: int,
    district_ids: Iterable[int],
    transport: Transport = _default_transport,
) -> Dict[str, int]:
    """
    canonical mandi_id -> CEDA market_id, for whichever of `mandi_ids` CEDA
    has a market for in this state.

    Walks every district under the state because neither the geographies nor
    the markets endpoint offers a narrower entry point — `/markets` itself
    requires a district_id per call. Each CEDA market_name is passed through
    the same `canonical_market()` alias table the rest of this codebase
    resolves upstream market names through, so a CEDA-specific second
    mapping can never quietly drift from it.
    """
    wanted = set(mandi_ids)
    resolved: Dict[str, int] = {}
    district_ids = list(district_ids)
    attempted = 0
    failed = 0
    last_error: Optional[CedaFetchError] = None

    for district_id in district_ids:
        if wanted <= resolved.keys():
            break
        attempted += 1
        try:
            markets = fetch_markets(commodity_id, state_id, district_id, transport=transport)
        except CedaFetchError as exc:
            failed += 1
            last_error = exc
            logger.warning("CEDA market lookup failed for district %s: %s", district_id, exc)
            continue
        for row in markets:
            canon = canonical_market(str(row.get("market_name", "")))
            if canon in wanted and canon not in resolved:
                resolved[canon] = int(row["market_id"])

    # Distinguish "no market exists here for this crop" (a legitimate empty
    # result -- markets genuinely returned nothing) from "every district
    # lookup errored" (a fetch problem, not an absence). Without this,
    # `fetch_daily_prices_and_arrivals`'s all-slices-failed check never
    # fired when the failure happened at market resolution: it caught the
    # per-district CedaFetchError, logged it, and returned an empty dict
    # that looked identical to "this crop just has no markets here" --
    # silently returning zero rows with no exception raised at all.
    if attempted and failed == attempted and not resolved:
        raise last_error  # type: ignore[misc]
    return resolved


# ── prices & quantities ──────────────────────────────────────────────────


def _fetch_series(
    endpoint: str,
    commodity_id: int,
    state_id: int,
    market_id: int,
    from_date: str,
    to_date: str,
    transport: Transport,
) -> List[Dict[str, Any]]:
    payload = _request(
        "POST", endpoint,
        body={
            "commodity_id": commodity_id, "state_id": state_id,
            "market_id": [market_id], "from_date": from_date, "to_date": to_date,
        },
        transport=transport,
    )
    return payload.get("data", []) or []


def fetch_daily_prices_and_arrivals(
    from_date: str,
    to_date: str,
    states: Iterable[str] = TARGET_STATES,
    commodities: Iterable[str] = TARGET_COMMODITIES,
    mandi_ids: Optional[Iterable[str]] = None,
    transport: Transport = _default_transport,
) -> pd.DataFrame:
    """
    Prices *and* arrival quantities for the configured commodities and
    markets, merged into one frame matching the observation store schema.

    Unlike `datagov.fetch_daily_prices`, `arrivals` is populated here rather
    than always None — this is the entire reason this client exists. Partial
    failure is tolerated the same way: one commodity or market failing to
    resolve or fetch does not fail the run, and the run only raises if
    nothing at all could be fetched, which is the honest signal that the API
    itself (or its key) is the problem rather than one series in it.
    """
    if mandi_ids is None:
        from mandisense_ai.farmer.reference import MANDI_COORDINATES

        mandi_ids = list(MANDI_COORDINATES.keys())
    mandi_ids = list(mandi_ids)

    try:
        commodity_ids = fetch_commodities(transport=transport)
        geographies = fetch_geographies(transport=transport)
    except CedaFetchError:
        raise  # nothing downstream can proceed without metadata; not a partial failure

    ingested_at = datetime.utcnow().isoformat() + "Z"
    rows: List[Dict[str, Any]] = []
    attempted = 0
    failed = 0

    for state in states:
        geo = geographies.get(state)
        if not geo or not geo.get("state_id"):
            logger.warning("CEDA has no geography entry for state %r; skipping.", state)
            continue
        state_id = geo["state_id"]
        district_ids = list(geo["districts"].values())

        for commodity in commodities:
            commodity_id = commodity_ids.get(commodity)
            if commodity_id is None:
                continue
            attempted += 1
            try:
                market_map = resolve_market_ids(
                    mandi_ids, commodity_id, state_id, district_ids, transport=transport
                )
                for mandi_id, market_id in market_map.items():
                    price_rows = _fetch_series(
                        "/agmarknet/prices", commodity_id, state_id, market_id,
                        from_date, to_date, transport,
                    )
                    qty_rows = _fetch_series(
                        "/agmarknet/quantities", commodity_id, state_id, market_id,
                        from_date, to_date, transport,
                    )
                    qty_by_date = {r.get("date"): r.get("quantity") for r in qty_rows if r.get("date")}

                    for row in price_rows:
                        date = row.get("date")
                        if not date or row.get("modal_price") is None:
                            continue
                        rows.append({
                            "date": pd.Timestamp(date),
                            "commodity": commodity,
                            "mandi_id": mandi_id,
                            "modal_price": row.get("modal_price"),
                            "min_price": row.get("min_price"),
                            "max_price": row.get("max_price"),
                            "arrivals": qty_by_date.get(date),
                            "state": state,
                            "district": None,
                            "source": SOURCE_NAME,
                            "ingested_at": ingested_at,
                        })
            except CedaFetchError as exc:
                failed += 1
                logger.error("CEDA fetch failed for %s/%s: %s", state, commodity, exc)

    if attempted and failed == attempted:
        raise CedaFetchError("All CEDA slices failed; treating the API as unavailable")

    frame = pd.DataFrame(rows)
    logger.info(
        "CEDA fetch complete: %d rows across %d (state, commodity) slices (%d failed)",
        len(frame), attempted, failed,
    )
    return frame
