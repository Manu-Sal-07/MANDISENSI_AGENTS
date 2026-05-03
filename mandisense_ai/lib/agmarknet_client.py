import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from io import StringIO
from typing import Any, Dict, List, Optional

from mandisense_ai.lib.logger import log_failure

DEFAULT_API_URL = "https://agmarknet.gov.in/PriceTrend.aspx?Comm={commodity}"
MAX_RETRIES = 2
REQUEST_TIMEOUT = 10
RETRY_DELAY_SECONDS = 1


def _extract_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(record, dict):
        return None

    normalized = {
        "name": None,
        "price": None,
        "arrival": None,
        "lat": 0.0,
        "lon": 0.0,
    }

    for raw_key, raw_value in record.items():
        key = str(raw_key).strip().lower()
        if key in {"market", "mandi", "market_name", "name"}:
            normalized["name"] = raw_value
        elif key in {"modal_price", "price", "min_price", "max_price"}:
            if normalized["price"] is None:
                normalized["price"] = raw_value
        elif key in {"arrivals_tonnes", "arrival", "arrivals", "total_arrivals"}:
            normalized["arrival"] = raw_value
        elif key in {"latitude", "lat"}:
            normalized["lat"] = raw_value
        elif key in {"longitude", "lon"}:
            normalized["lon"] = raw_value

    if normalized["name"] is None or normalized["price"] is None or normalized["arrival"] is None:
        return None

    return normalized


def _parse_json_payload(payload: str) -> Optional[List[Dict[str, Any]]]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError:
        return None

    candidates = []
    if isinstance(raw, dict):
        for key in ("data", "records", "result", "results", "rows", "response"):
            if key in raw and isinstance(raw[key], list):
                candidates = raw[key]
                break
        if not candidates and isinstance(raw, list):
            candidates = raw
    elif isinstance(raw, list):
        candidates = raw
    else:
        return None

    sanitized = []
    for row in candidates:
        extracted = _extract_record(row)
        if extracted is not None:
            sanitized.append(extracted)

    return sanitized if sanitized else None


def _parse_csv_payload(payload: str) -> Optional[List[Dict[str, Any]]]:
    reader = csv.DictReader(StringIO(payload))
    records = []
    for row in reader:
        extracted = _extract_record(row)
        if extracted is not None:
            records.append(extracted)
    return records if records else None


def _build_url(commodity: str) -> str:
    return DEFAULT_API_URL.format(commodity=urllib.parse.quote(str(commodity).strip()))


def fetch_agmarknet_data(commodity: str) -> Optional[List[Dict[str, Any]]]:
    if not commodity or not isinstance(commodity, str):
        return None

    url = _build_url(commodity)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "MandiSenseAI/1.0",
                    "Accept": "application/json, text/csv, */*",
                },
            )
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(url, response.status, response.reason, response.headers, None)

                raw_text = response.read().decode(response.headers.get_content_charset("utf-8"), errors="replace")
                if not raw_text.strip():
                    return None

                parsed = _parse_json_payload(raw_text)
                if parsed is not None:
                    return parsed

                parsed = _parse_csv_payload(raw_text)
                if parsed is not None:
                    return parsed

                log_failure(
                    "agmarknet_client",
                    "unable to parse Agmarknet response",
                    commodity=commodity,
                    metadata={"attempt": attempt},
                )
                return None

        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, ValueError, TimeoutError) as exc:
            log_failure(
                "agmarknet_client",
                str(exc),
                commodity=commodity,
                metadata={"attempt": attempt, "max_attempts": MAX_RETRIES},
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
            continue
        except Exception as exc:
            log_failure(
                "agmarknet_client",
                f"unexpected Agmarknet client failure: {exc}",
                commodity=commodity,
                metadata={"attempt": attempt, "max_attempts": MAX_RETRIES},
            )
            break

    return None
