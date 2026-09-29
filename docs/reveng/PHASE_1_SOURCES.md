# Phase 1 — Data Acquisition Forensics

> **Project:** MandiSense AI
> **Audit date:** 2026-09-06
> **Scope:** Every byte the project consumes, and the mechanism that fetched it.
> **Citation root:** all paths are relative to `d:\BMS COLL\PROJECT\MS-AI\MS-AI\` (the git repository root — `git rev-parse` confirms `.git` lives here, and the outer `d:\BMS COLL\PROJECT\MS-AI\` is not a repository).

---

## 0. Setup Deviation — PHASE_0_MAP.md Does Not Exist

The task instructed: *"Read docs/reveng/PHASE_0_MAP.md. Work through every file assigned to Phase 1 in the coverage ledger."*

**That file does not exist.** Evidence:

```
$ ls docs/reveng/
PHASE_7_EDA_VIZ.md          # 361 lines, the only file present

$ find "d:/BMS COLL/PROJECT" -iname "PHASE_0*"
(no output)
```

There is therefore **no coverage ledger and no Phase-1 file assignment**. I constructed my own ledger from the mandatory search sweep (Step 1) plus a full traversal of the data directories, and I have written it to `docs/reveng/PHASE_0_MAP.md` as a new file so that Step 7 has a target and later phases inherit a ledger. That file is flagged at its head as auditor-authored, not recovered. This is the one deviation from R6 (read-only except my own output `.md` files); the created file *is* one of my own output files.

**Consequence for this audit:** the boundary of "Phase 1's assignment" is my judgement, not a prior phase's. Section 8b names every file in my ledger that I did not open.

---

## 1. STEP 1 — Mandatory Search Sweep

**Search scope (identical for every pattern):** ripgrep over the repository root with these exclusions —
`ms_env/`, `**/node_modules/`, `build/`, `dist/`, `dist_test/`, `**/__pycache__/`, `**/*.egg-info/`, `docs/reveng/`, `models_backup*/` — and these file types: `py, md, yaml, sh, sql, js, ts`.

`matching_lines` = total lines matched across all files (ripgrep `-c` summed). `files` = distinct files containing ≥1 match.

| # | Pattern | matching_lines | files | Finding |
|---|---------|---------------:|------:|---------|
| P1 | `requests\.\|httpx\|urllib\|aiohttp\|http\.client\|session\.get\|session\.post` | 14 | 6 | Three real outbound HTTP call sites; two self-referential (localhost); one Docker healthcheck. |
| P2 | `boto3\|s3fs\|gcsfs\|google\.cloud\|azure\.storage\|blob\|minio` | 1 | 1 | **ZERO-HIT FINDING (effectively).** The single hit is a CSS comment `{/* Ambient glowing blobs */}` in [`frontend/src/app/evaluator-demo/page.tsx:L19`]. **No object storage is used anywhere.** |
| P3 | `read_csv\|read_excel\|read_parquet\|read_json\|read_sql\|read_html\|read_feather\|read_pickle` | 46 | 32 | The dominant acquisition mechanism. All are local-filesystem reads. `read_sql` has zero occurrences — no dataframe is ever loaded from a database. |
| P4 | `create_engine\|psycopg2\|pymysql\|sqlalchemy\|pyodbc\|snowflake\|bigquery\|athena\|duckdb` | 8 | 3 | Only `psycopg2` (+ `asyncpg`, which this pattern does not cover). No ORM. No warehouse. |
| P5 | `pymongo\|redis\|elasticsearch\|cassandra` | 101 | 14 | All `redis`. **`pymongo`, `elasticsearch`, `cassandra` are each a zero-hit finding.** |
| P6 | `kafka\|pubsub\|kinesis\|rabbitmq` | **0** | **0** | **ZERO-HIT FINDING. There is no streaming ingestion of any kind.** |
| P7 | `yfinance\|tweepy\|praw\|alpha_vantage\|quandl\|fredapi\|kaggle\|opendatasets\|datasets\.load` | **0** | **0** | **ZERO-HIT FINDING. No third-party data-vendor SDK is used.** |
| P8 | `BeautifulSoup\|selenium\|playwright\|scrapy\|lxml\|feedparser` | **0** | **0** | **ZERO-HIT FINDING. There is no scraper in this repository** — despite `README.md:L110` advertising an "Entity & Category Scraper" and `mandisense_ai/data/ingestion/agmarknet_ingestor.py:L11` describing ingestion "from Agmarknet". See §7 (README contradictions). |
| P9 | `open\(\|Path\(\|glob\.\|os\.listdir\|pathlib\|zipfile\|tarfile\|gzip` | 258 | 91 | Local file IO is pervasive. `zipfile`, `tarfile`, `gzip` contribute no data-acquisition hits — no archive is ever unpacked. |
| P10 | `wget\|curl\|ftplib\|paramiko\|sftp` | 2 | 2 | Both are `curl` in a health check: [`docker-compose.yml:L25`] and [`README.md:L271`]. **No file transfer of any kind.** |
| P11 | `np\.random\|numpy\.random\|random\.\|make_regression\|make_classification\|faker\|synthetic\|mock\|dummy\|simulate` | 208 | 41 | The single largest signal in the sweep. Drives §3 entirely. |

**Zero-hit patterns, restated as findings:** P6 (streaming), P7 (data-vendor SDKs), P8 (scraping/parsing libraries) all return **zero** matches. P2 returns one false positive. Taken together: **this project has no live external data acquisition for market prices at all.** The only two working outbound data fetches in the entire codebase are weather (Open-Meteo) and news (NewsAPI), and both feed the External Factors Agent, which contributes 25% of one of three agent signals.

---

## 2. STEP 2 — Source Dossiers

Eighteen distinct sources were identified. Every dossier carries all 12 fields; fields the code does not determine are filled `UNKNOWN` in the R3 format.

---

### Source S1: Agmarknet Daily Price & Arrival Report API — historical bulk extract (NO CODE IN REPO)

1. **Acquisition class:** REST API — **executed outside this repository**. Classified as *manual download / external process*. Evidence of the manual step: the resulting CSVs carry a `source_url` and a `scrape_timestamp` column populated by a program that does not exist in this repo or in its 39-commit git history (see field 3).
2. **Exact endpoint / URI / table / path:** taken verbatim from the `source_url` column of the committed data:

```
https://api.agmarknet.gov.in/v1/daily-price-arrival/report?from_date=2015-01-01&to_date=2015-03-31&commodity=65&market=112
```

   Commodity/market ID pairs observed, one per file:

   | File | commodity= | market= | Label in data |
   |---|---:|---:|---|
   | `agmarknet_Tomato_Kolar.csv` | 65 | 112 | Tomato / Kolar / Karnataka |
   | `agmarknet_Onion_Lasalgaon.csv` | 23 | 161 | Onion / Lasalgaon / Maharashtra |
   | `agmarknet_Potato_Agra.csv` | 24 | 297 | Potato / Agra / Uttar Pradesh |
   | `agmarknet_Garlic_Neemuch.csv` | 25 | 182 | Garlic / Neemuch / Madhya Pradesh |
   | `agmarknet_Dry_Chillies_Guntur.csv` | 113 | 886 | Dry Chillies / Guntur / Andhra Pradesh |

3. **Code location:** **NONE EXISTS.** This is the central finding of Phase 1. Proof of absence, three independent searches:

```
$ rg -n 'api\.agmarknet|daily-price-arrival|scrape_timestamp|source_url' \
     --glob='!ms_env/**' --glob='!**/__pycache__/**' --glob='!*.csv'
(no output)

$ git log --all --pretty=format: --name-only | sort -u | grep -iE "scrap|fetch|ingest|download|crawl"
mandisense_ai/core/agents/external_factors_agent/ingestion/__init__.py
mandisense_ai/core/agents/external_factors_agent/ingestion/news_fetcher.py
mandisense_ai/core/agents/external_factors_agent/ingestion/news_ingestor.py
mandisense_ai/core/agents/external_factors_agent/ingestion/weather_fetcher.py
mandisense_ai/core/agents/external_factors_agent/tests/test_news_fetcher.py
mandisense_ai/data/ingestion/__init__.py
mandisense_ai/data/ingestion/agmarknet_ingestor.py
mandisense_ai/tasks/ingest_historical_data.py

$ (P8 sweep) BeautifulSoup|selenium|playwright|scrapy|lxml|feedparser  ->  0 hits
```

   No file matching a scraper name has ever existed in the 39 commits of this repository. The only in-repo consumer of these files is [`mandisense_ai/data/prepare_datasets.py:L22-L28`], which names them as literals:

```python
COMMODITIES = {
    "tomato": ["agmarknet_Tomato_Kolar.csv"],
    "onion": ["agmarknet_Onion_Lasalgaon.csv"],
    "potato": ["agmarknet_Potato_Agra.csv"],
    "dry_chillis": ["agmarknet_Dry_Chillies_Guntur.csv"],
    "garlic": ["agmarknet_Garlic_Neemuch.csv"]
}
```

4. **Auth mechanism:** UNKNOWN — I looked for an API key, token, or session cookie in the `source_url` values, in `.env.example`, and in `render.yaml`; the URLs carry no auth parameter and no Agmarknet credential name appears in either env file [`.env.example:L1-L50`]. Resolved by: obtaining the extraction script, which is not in this repository.
5. **Request parameters:** `from_date` (ISO date), `to_date` (ISO date), `commodity` (integer ID), `market` (integer ID). All four appear in every observed `source_url`. No header, body, sort order, or page-size parameter is observable — the URL is the entire observable request. Request-window date range across all five files: **2015-01-01 → 2025-03-09**.
6. **Pagination & rate limiting:** Reconstructed from the distinct `source_url` values — the extractor paginated by **fixed calendar windows**, mostly quarterly, with a final ~30-day window. There is no loop to paste because the loop is not in this repository. The window boundaries recovered from the data:

```
first: ...?from_date=2015-01-01&to_date=2015-03-31&commodity=65&market=112
last : ...?from_date=2025-02-07&to_date=2025-03-09&commodity=65&market=112
distinct source_url values per file: 35 (Dry Chillies), 41 (Garlic), 42 (Onion, Potato, Tomato)
```

   Rate limiting: [INFERRED] from `scrape_timestamp` spacing — Tomato's 42 windows carry 42 distinct timestamps spanning `2026-03-10 09:30:05 → 09:37:29`, i.e. **~10.6 s per request**. Whether that is a deliberate sleep or server latency is UNKNOWN — I looked for a sleep constant for this source in the repo and found none; resolved by obtaining the extraction script.
7. **Volume & cadence:**

   | File | Rows | Realised date range | Windows | Scrape timestamps |
   |---|---:|---|---:|---|
   | `agmarknet_Tomato_Kolar.csv` | 3597 | 2015-01-06 → 2025-03-01 | 42 | 2026-03-10 09:30:05 → 09:37:29 |
   | `agmarknet_Onion_Lasalgaon.csv` | 2442 | 2015-01-01 → 2025-03-08 | 42 | 2026-03-10 09:22:18 → 09:29:41 |
   | `agmarknet_Potato_Agra.csv` | 2899 | 2015-01-02 → 2025-03-09 | 42 | 2026-03-10 09:37:43 → 09:45:08 |
   | `agmarknet_Garlic_Neemuch.csv` | 1787 | 2015-01-05 → 2025-03-07 | 41 | 2026-03-10 11:47:58 → 11:55:57 |
   | `agmarknet_Dry_Chillies_Guntur.csv` | 1720 | 2015-01-01 → 2025-03-07 | 35 | 2026-03-10 11:35:10 → 11:46:36 |

   **Total: 12,445 rows.** Full-refresh, one-shot. No watermark column, no cursor, no incremental logic — because there is no fetch code. **Scheduling is absent**: no cron, no Celery beat, no APScheduler. `render.yaml` declares only a `web` service, a Postgres database and a Redis instance [`render.yaml:L1-L31`] — no worker and no cron job. The only `Celery` references are docstrings [`mandisense_ai/tasks/retraining.py:L4`, `mandisense_ai/tasks/__init__.py:L1`]; no Celery app object exists.
8. **Raw response shape:** Reconstructed from the **committed data files themselves** — not from parsing code (none exists) and not from test fixtures (none exist for this source). CSV header, verbatim, plus first data row:

```
date,commodity,market,state,arrivals_tonnes,modal_price,min_price,max_price,source_url,scrape_timestamp
2015-01-06,Tomato,Kolar,Karnataka,5008.0,933.0,466.0,1533.0,https://api.agmarknet.gov.in/v1/daily-price-arrival/report?from_date=2015-01-01&to_date=2015-03-31&commodity=65&market=112,2026-03-10 09:30:05
```

   `source_url` and `scrape_timestamp` are **provenance columns added by the extractor**, not fields the API returns; the true API response shape is UNKNOWN.
9. **Failure handling:** UNKNOWN — there is no code to inspect. The data shows no gap-marker rows and no partial-window artefacts, but absence of evidence here is not evidence of handling.
10. **Determinism:** **Re-running today would not reproduce this data, because there is nothing to re-run.** The files are frozen artefacts of a 2026-03-10 extraction. Separately, the upstream host is unverifiable from here: [`mandisense_ai/lib/agmarknet_client.py:L12`] points at a *different* Agmarknet host and path (`agmarknet.gov.in/PriceTrend.aspx`), so the repo contains no corroboration that `api.agmarknet.gov.in/v1/...` is live.
11. **Landing location:** `mandisense_ai/data/raw/agmarknet_*.csv`. **No write call exists** — the files were placed there by hand or by the absent extractor. They are **excluded from version control**: [`mandisense_ai/.gitignore:L43`] contains `data/raw/*`, and `git check-ignore -v` confirms:

```
mandisense_ai/.gitignore:43:data/raw/*    mandisense_ai/data/raw/agmarknet_Tomato_Kolar.csv
```

   `git ls-files mandisense_ai/data/` returns 35 entries, **none of which is a raw CSV**. These 12,445 rows exist only on this machine.
12. **Licensing / ToS:** UNKNOWN — I grepped the repository for `license`, `terms`, `ToS`, and `agmarknet` in comments; no file states terms of use for Agmarknet data. Resolved by consulting agmarknet.gov.in's published terms.

---

### Source S2: Agmarknet `PriceTrend.aspx` live client (in-repo, non-functional)

1. **Acquisition class:** REST API (attempted). In practice **[DEAD?] and structurally broken** — see fields 3, 7, 8.
2. **Exact endpoint / URI / table / path:**

```
https://agmarknet.gov.in/PriceTrend.aspx?Comm={commodity}
```

   `{commodity}` is URL-quoted at [`mandisense_ai/lib/agmarknet_client.py:L88-L89`].
3. **Code location:** [`mandisense_ai/lib/agmarknet_client.py:L12-L15`] and [`mandisense_ai/lib/agmarknet_client.py:L98-L121`]

```python
DEFAULT_API_URL = "https://agmarknet.gov.in/PriceTrend.aspx?Comm={commodity}"
MAX_RETRIES = 2
REQUEST_TIMEOUT = 10
RETRY_DELAY_SECONDS = 1
```

```python
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
```

   **`PriceTrend.aspx` is an ASP.NET HTML page. The client implements only a JSON parser and a CSV parser** ([`mandisense_ai/lib/agmarknet_client.py:L50-L85`]). An HTML body satisfies neither, so control reaches the "unable to parse" branch at [`mandisense_ai/lib/agmarknet_client.py:L123-L129`] and the function returns `None`. **This fetch path cannot succeed as written.** [INFERRED] from the cited URL constant plus the cited parser set.
4. **Auth mechanism:** **none.** The only headers sent are `User-Agent: MandiSenseAI/1.0` and `Accept` [`mandisense_ai/lib/agmarknet_client.py:L102-L105`]. No key, no cookie, no env var.
5. **Request parameters:** one query parameter, `Comm`, set to the URL-quoted commodity string. No date range, no market ID, no pagination parameter, no sort order. Header set is the two lines quoted above. No request body (GET). Commodity list: not enumerated in this module — the caller passes a single string [`mandisense_ai/services/mandi_data_service.py:L80`].
6. **Pagination & rate limiting:** No pagination — a single request per call, max 2 attempts. Retry loop pasted in field 3; backoff is a flat 1-second sleep with no exponential term [`mandisense_ai/lib/agmarknet_client.py:L138-L140`]:

```python
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS)
        continue
```

   A separate caller-side rate limiter allows **one call per 15 seconds process-wide** [`mandisense_ai/services/mandi_data_service.py:L11-L14`, `L43-L51`]:

```python
LAST_API_CALL = 0.0
RATE_LIMIT_SECONDS = 15.0
CACHE_TTL_SECONDS = 3600
_RATE_LIMIT_LOCK = threading.Lock()
```

```python
def _try_live_fetch(commodity: str) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    global LAST_API_CALL
    with _RATE_LIMIT_LOCK:
        now = time.monotonic()
        if now - LAST_API_CALL < RATE_LIMIT_SECONDS:
            return False, None
        LAST_API_CALL = now

    return True, fetch_agmarknet_data(commodity)
```

7. **Volume & cadence:** One snapshot of N mandi rows per call; N is whatever the endpoint returns. Full-refresh (no watermark, no cursor, no backfill). Cached for 3600 s [`mandisense_ai/services/mandi_data_service.py:L13`]. **Scheduling is absent — and so is any caller.** The only importers of `get_mandi_snapshot` are a re-export shim [`backend/services/mandi_data_service.py:L1-L3`], a package `__init__` [`mandisense_ai/services/__init__.py:L3`], and the module's own `__main__` block [`mandisense_ai/services/mandi_data_service.py:L142-L149`]. **No API route, task, or agent calls it. [DEAD?] — unreachable from any running entry point.**
8. **Raw response shape:** Reconstructed from **parsing code only** (no sample file, no fixture). The normaliser accepts either a JSON envelope or a CSV, and maps these key aliases [`mandisense_ai/lib/agmarknet_client.py:L30-L42`]:

```python
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
```

   JSON envelope keys probed, in order: `data`, `records`, `result`, `results`, `rows`, `response` [`mandisense_ai/lib/agmarknet_client.py:L58`]. Normalised record shape: `{name, price, arrival, lat, lon}`.
9. **Failure handling:** **Silent to the caller** — every failure path returns `None`, and the caller substitutes fabricated data (see S13). Verbatim except blocks [`mandisense_ai/lib/agmarknet_client.py:L131-L148`]:

```python
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
```

   4xx/5xx → `HTTPError` raised at L109, caught at L131, logged, retried once, then `None`. Timeout → `TimeoutError`, same path. **Empty response → `return None` at L112-L113 with no logging at all.** The service wrapper then swallows whatever escapes [`mandisense_ai/services/mandi_data_service.py:L119-L123`]:

```python
    except Exception as exc:
        log_failure("mandi_data_service", str(exc), commodity=commodity)
        final_data = fallback_data(commodity)
        source = "fallback"
        error_msg = f"Unexpected exception in mandi service: {exc}"
```

   The returned envelope reports `"status": "OK"` **unconditionally**, even on total failure [`mandisense_ai/services/mandi_data_service.py:L134-L139`]:

```python
    return {
        "mandis": final_data,
        "source": source,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "OK",
    }
```

   Only the `source` field (`"live"` / `"cache"` / `"fallback"`) distinguishes real from fabricated.
10. **Determinism:** Non-deterministic on three cited counts: (a) the 15-second rate limiter keys on `time.monotonic()` [`mandisense_ai/services/mandi_data_service.py:L46`], so two identical calls seconds apart return different `source` values; (b) the envelope stamps `datetime.datetime.utcnow()` [`mandisense_ai/services/mandi_data_service.py:L137`]; (c) the upstream is a live web page. No random seed is involved.
11. **Landing location:** Redis, or a JSON file when Redis is unavailable, via `set_cache` [`mandisense_ai/services/mandi_data_service.py:L103`]; key `f"mandi_snapshot:{commodity}"` [`mandisense_ai/services/mandi_data_service.py:L38-L40`]. File fallback path `mandisense_ai/data/cache.json` [`mandisense_ai/lib/cache.py:L16-L17`]. **Nothing is ever written to a raw-data directory by this path.**
12. **Licensing / ToS:** UNKNOWN — no comment, docstring, or config in `agmarknet_client.py` mentions terms of use. Resolved by consulting agmarknet.gov.in's published terms.

---

### Source S3: Open-Meteo Historical Weather Archive API

1. **Acquisition class:** REST API — **live, functional, and demonstrably executed** (raw cache artefacts on disk; runtime log line quoted in field 11).
2. **Exact endpoint / URI / table / path:**

```
https://archive-api.open-meteo.com/v1/archive
```

   [`mandisense_ai/core/agents/external_factors_agent/ingestion/weather_fetcher.py:L37`]
3. **Code location:** [`mandisense_ai/core/agents/external_factors_agent/ingestion/weather_fetcher.py:L100-L117`]

```python
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
    }

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if "hourly" not in payload:
                raise WeatherFetchError(f"Open-Meteo response missing hourly payload: {payload}")
            return payload
```

4. **Auth mechanism:** **none.** No key, no header, no env var — confirmed by the absence of any auth field in the `params` dict quoted above and the absence of a `headers=` argument on the `requests.get` call.
5. **Request parameters:** exactly six, all in the pasted dict — `latitude` (float), `longitude` (float), `start_date` (`YYYY-MM-DD`), `end_date` (`YYYY-MM-DD`), `hourly` = `"temperature_2m,precipitation"` [`.../weather_fetcher.py:L39`], `timezone` = `"UTC"`. No headers, no body, no sort order, no page size. **Date range is caller-driven and is always a trailing 30-day window ending at the requested date** [`.../processing/weather_signal.py:L200-L210`]:

```python
        current = pd.to_datetime(date, errors="raise").normalize()
        start = current - pd.Timedelta(days=29)
        lat, lon = resolve_mandi_coordinates(mandi, district=district)

        if weather_df is None:
            weather_df = fetch_weather(
                lat,
                lon,
                start.strftime("%Y-%m-%d"),
                current.strftime("%Y-%m-%d"),
            )
```

   There is no commodity or market ID list for this source; the location list is a **hardcoded mandi coordinate table** — see S14.
6. **Pagination & rate limiting:** **No pagination** — one request covers the whole date range. Retry policy: 3 attempts, **linear** backoff `backoff_seconds * attempt` (1.5 s then 3.0 s), 30 s timeout [`.../weather_fetcher.py:L118-L124`; defaults at `L182-L183`]:

```python
        except Exception as exc:
            last_error = exc
            logger.warning(f"Open-Meteo request failed attempt={attempt}/{max_retries}: {exc}")
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)

    raise WeatherFetchError(f"Open-Meteo request failed after {max_retries} attempts: {last_error}")
```

   **No inter-request sleep in the batch helper** — `fetch_weather_batch` loops locations with no delay whatsoever [`.../weather_fetcher.py:L242-L255`]:

```python
    results: Dict[str, pd.DataFrame] = {}
    for idx, item in enumerate(locations):
        key = str(item.get("id") or item.get("name") or item.get("mandi") or idx)
        results[key] = fetch_weather(
            item["latitude"],
            item["longitude"],
            item["start_date"],
            item["end_date"],
            cache_dir=cache_dir,
```

   Max pages: N/A.
7. **Volume & cadence:** 720 hourly rows per 30-day request — verified against the committed sample `data/cache/weather/ba9661cabb981df3be60e7e7ed5110cee5528ffa26bc80b9870058d6eda947da.json`, which holds 720 timestamps spanning `2026-04-17T00:00 → 2026-05-16T23:00`. Aggregated to 30 daily rows [`.../weather_fetcher.py:L147-L155`]. Full-refresh per call; **no watermark, no cursor, no backfill logic**. The only incremental behaviour is the SHA-256 content-addressed cache [`.../weather_fetcher.py:L61-L70`], keyed on `{lat, lon, start_date, end_date, hourly, source}`. **Scheduling is absent** — `config_manager` declares `scheduler_frequency = {"batch": 1800, "fast": 300}` [`.../orchestration/config_manager.py:L6-L9`], but **nothing reads that dict** (P6 = 0 hits; `render.yaml:L1-L31` declares no worker or cron service).
8. **Raw response shape:** Reconstructed from **a committed sample response** (the cache file named in field 7), corroborated by the parsing code at [`.../weather_fetcher.py:L128-L141`]. Top-level JSON keys, read out of the file:

```
latitude, longitude, generationtime_ms, utc_offset_seconds,
timezone, timezone_abbreviation, elevation, hourly_units, hourly
```

   Observed scalar values: `latitude=12.970123`, `longitude=77.56364`, `timezone="GMT"`, `elevation=910.0`, `utc_offset_seconds=0`.
   `hourly_units = {"time": "iso8601", "temperature_2m": "°C", "precipitation": "mm"}`.
   `hourly = {"time": [ISO8601 ...], "temperature_2m": [float ...], "precipitation": [float ...]}` — 720 elements each; first five temperatures `[23.4, 23.2, 24.8, 27.6, 30.4]`.
   Output frame schema after aggregation: `date | temperature (float32) | precipitation (float32)` [`.../weather_fetcher.py:L168-L170`].
9. **Failure handling:** **Loud at the fetcher, silent at the agent.** The fetcher raises after exhausting retries [`.../weather_fetcher.py:L124`]. 4xx/5xx → `raise_for_status()` at L113 → caught by the bare `except Exception` at L118 → retried → raised. Timeout → identical path. Missing `hourly` key → `WeatherFetchError` at L116. Zero usable rows after parse → `WeatherFetchError` at L145. But the caller **swallows all of it and substitutes zero** [`.../processing/weather_signal.py:L223-L233`]:

```python
    except Exception as exc:
        logger.error(f"Weather signal failed for {commodity}/{mandi} @ {date}: {exc}", exc_info=True)
        return {
            "weather_signal": 0.0,
            "components": {"rain_signal": 0.0, "temp_signal": 0.0},
            "mandi": mandi,
            "commodity": commodity,
            "date": str(date),
            "coordinates": {"latitude": lat, "longitude": lon},
            "error": str(exc),
        }
```

   A second swallow sits above it [`.../external_factors_agent/__init__.py:L54-L71`], returning `impact_score: 0.0`. **A total weather outage is indistinguishable downstream from "weather has no effect today"**, except via the `error` key, which no consumer inspects. Cache read/write failures are silent-by-warning [`.../weather_fetcher.py:L78-L80`, `L87-L88`].
10. **Determinism:** **Not deterministic in operation, though the upstream archive itself is.** The archive returns fixed historical values for a fixed range, but the range derives from the caller's `date`, and the top-level agent defaults that to **now** [`.../external_factors_agent/__init__.py:L25-L26`]:

```python
    if date is None:
        date = datetime.utcnow().date().isoformat()
```

    A re-run tomorrow therefore requests a different 30-day window and receives different data. No random seed is involved. Cache hits make repeat calls within one run deterministic.
11. **Landing location:** `data/cache/weather/<sha256>.json`, raw payload written verbatim [`.../weather_fetcher.py:L83-L88`, invoked at `L219-L220`]:

```python
def _write_cache(cache_path: Path, payload: Dict[str, Any]) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Weather cache write failed for {cache_path}: {exc}")
```

    The directory is **CWD-relative** [`.../weather_fetcher.py:L38`]: `DEFAULT_CACHE_DIR = Path("data/cache/weather")`. Both `data/cache/weather/` (10 files) and `mandisense_ai/data/cache/weather/` (3 files) exist on disk — evidence the module has been run from two different working directories. Proof of real execution, from a committed runtime log [`startup_log.txt:L35`]:

```json
{"timestamp": "2026-05-16T19:10:39.323593Z", "level": "INFO", "name": "mandisense_ai.core.agents.external_factors_agent.ingestion.weather_fetcher", "message": "Loaded weather response from cache: data\\cache\\weather\\ba9661cabb981df3be60e7e7ed5110cee5528ffa26bc80b9870058d6eda947da.json", "module": "weather_fetcher", "funcName": "fetch_weather", "lineNo": 222}
```

    The derived daily frame is never persisted; only the raw payload is.
12. **Licensing / ToS:** UNKNOWN — no comment, docstring, or config mentions Open-Meteo's terms. The module docstring [`.../weather_fetcher.py:L1-L12`] describes behaviour only. Resolved by consulting open-meteo.com's licence page.

---

### Source S4: NewsAPI.org `/v2/everything` — BBC News

1. **Acquisition class:** REST API — **live and functional**, but see field 4 (no working credential is configured anywhere in this repository) and field 7 (the query it actually issues).
2. **Exact endpoint / URI / table / path:**

```
https://newsapi.org/v2/everything
```

   [`mandisense_ai/core/agents/external_factors_agent/ingestion/news_fetcher.py:L30`]. Note the module, its class, and all its symbols are named "BBC News", but the vendor is NewsAPI.org; `bbc-news` is only the value of the `sources` parameter [`.../news_fetcher.py:L31`].
3. **Code location:** [`mandisense_ai/core/agents/external_factors_agent/ingestion/news_fetcher.py:L116-L136`]

```python
    params = {
        "apiKey": api_key,
        "sources": BBC_NEWS_SOURCE,
        "pageSize": DEFAULT_PAGE_SIZE,
        "sortBy": "publishedAt",
        "language": "en",
        "from": from_date,
        "to": to_date,
    }
    if query:
        params["q"] = query

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(BBC_NEWS_API_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "ok" or "articles" not in payload:
                raise NewsFetchError(f"BBC News API returned unexpected payload: {payload}")
            return payload
```

4. **Auth mechanism:** **API key, passed as a query parameter** (`apiKey`), i.e. in the URL, not a header. Credential source is the env var **`NEWS_API_KEY`**, read at [`.../orchestration/config_manager.py:L5`]:

```python
        self.api_keys = {"news_api": os.getenv("NEWS_API_KEY", "")}
```

   resolved lazily by the fetcher [`.../news_fetcher.py:L214-L218`]:

```python
    if not api_key:
        from mandisense_ai.core.agents.external_factors_agent.orchestration.config_manager import config
        api_key = getattr(config, "api_keys", {}).get("news_api")
    if not api_key or api_key == "dummy":
        raise NewsFetchError("Missing valid NEWS_API_KEY for BBC News API")
```

   **No hardcoded literal key remains in the source** — I searched `NEWS_API_KEY` and the whole `external_factors_agent` tree; the only assignments are the `os.getenv` above. (A prior hardcoded key is described as removed in [`PHASE_2A_SECURITY_AND_REPO_HARDENING_REPORT.txt:L27`]; I did not verify that claim against git history.) **However, no working value is configured:** `.env` is byte-identical to `.env.example` (`diff` returns nothing) and both set the placeholder [`.env.example:L21`]:

```
NEWS_API_KEY=your_news_api_key_here
```

   and **`render.yaml` does not declare `NEWS_API_KEY` at all** [`render.yaml:L9-L20`] — the only env vars are `APP__ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL`. A production deploy therefore cannot fetch news.
5. **Request parameters:** the seven in the pasted dict. `apiKey` (secret), `sources` = `"bbc-news"`, `pageSize` = `100` [`.../news_fetcher.py:L35`], `sortBy` = `"publishedAt"`, `language` = `"en"`, `from` / `to` = ISO dates, `q` = the query string when non-empty. **The commodity is passed as `q`** [`.../external_factors_agent/__init__.py:L29`]:

```python
        news_articles: List[Dict[str, Any]] = fetch_news(query=commodity, days_back=2)
```

   Date range: `from` = today − `days_back`, `to` = today [`.../news_fetcher.py:L204-L206`, `L222`]. `days_back` defaults to 30 in the fetcher [`.../news_fetcher.py:L34`] but the live caller passes **2**. No headers, no request body. Sort order `publishedAt` descending (vendor default).
6. **Pagination & rate limiting:** **No pagination is implemented at all.** `pageSize=100` is sent but no `page` parameter is ever supplied and no loop advances a page cursor — the code takes the first page and stops. **Max pages: 1.** Article counts above 100 are silently truncated by the vendor. Retry policy: 3 attempts, **linear** backoff `backoff_seconds * attempt` (1.0 s then 2.0 s), 10 s timeout [`.../news_fetcher.py:L137-L142`; defaults at `L196-L198`]:

```python
        except Exception as exc:
            last_error = exc
            logger.warning(f"BBC News request failed attempt={attempt}/{max_retries}: {exc}")
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)
    raise NewsFetchError(f"BBC News request failed after {max_retries} attempts: {last_error}")
```

   Rate limiting is by cache TTL only — 3600 s [`.../news_fetcher.py:L36`].
7. **Volume & cadence:** 0–100 articles per call. Observed in the committed cache files: 0, 4, 10, 12, 14, and 54 articles across 17 files. **Critical behaviour — a silent broadening fallback** [`.../news_fetcher.py:L237-L252`]:

```python
    if not articles and query_text != DEFAULT_QUERY and fallback_if_empty:
        logger.info(
            f"No BBC articles found for query='{query_text}' in the last {valid_days_back} days; retrying with broader default query='{DEFAULT_QUERY}'"
        )
        return fetch_bbc_news(
            DEFAULT_QUERY,
            days_back=valid_days_back,
```

   `DEFAULT_QUERY = "bbc"` [`.../news_fetcher.py:L33`]. So when a commodity query ("tomato", "onion") returns nothing — which for BBC News in a 2-day window is the common case — **the agent silently re-queries for the literal string "bbc" and ingests generic BBC output as agricultural signal.** The committed caches confirm this happened: sample titles read `"the news quiz: ep4. the people have spoken"`, `"bbc inside science"`, `"football daily"`, `"women who died in sea off brighton beach were sisters"`, `"03 05 2026 21:01 gmt"`. **Not one sampled headline is agricultural.** Full-refresh; no watermark, no cursor, no backfill. **Scheduling is absent** (same evidence as S3).
8. **Raw response shape:** Reconstructed from **all three sources**. (a) Parsing code [`.../news_fetcher.py:L145-L161`] — vendor envelope has `status` and `articles`; each article is read for `title`, `description`, `content`, `publishedAt` / `published_at`. (b) A **test fixture** [`.../tests/test_news_fetcher.py:L21-L41`] mocks `_request_bbc_news`. (c) **Committed cache files** hold the post-parse shape, which is the wrapper's own, not the vendor's [`.../news_fetcher.py:L96-L102`]:

```python
        cache_path.write_text(
            json.dumps({"fetched_at": time.time(), "articles": articles}, default=str),
            encoding="utf-8",
        )
```

   Cached envelope: `{"fetched_at": <float epoch>, "articles": [...]}`. Normalised article: `{title, description, published_at}` — all lower-cased and punctuation-stripped by `_normalize_text` [`.../news_fetcher.py:L43-L51`]. **The raw vendor payload is never persisted**, so vendor fields beyond those four are UNKNOWN from this repo.
9. **Failure handling:** **Fails to a hardcoded fabricated article list.** The fetcher raises; the ingestor catches everything and substitutes [`.../ingestion/news_ingestor.py:L46-L61`]:

```python
def fetch_news(query: str | None = None, days_back: int = 2):
    """Fetch BBC news articles and fallback to deterministic sample data on failure."""
    try:
        articles = fetch_bbc_news(query=query, days_back=days_back)
        return [
            {
                "title": article["title"],
                "description": article["description"],
                "published_at": article["published_at"],
                "date": article["published_at"],
            }
            for article in articles
        ]
    except Exception as exc:
        logger.warning(f"BBC news fetch failed, using fallback dataset: {exc}")
        return [_normalize_fallback_article(item) for item in FALLBACK_DATA]
```

   4xx (including a 401 from the placeholder key) / 5xx → `raise_for_status()` at L132 → retried → `NewsFetchError` → caught here → **fabricated articles returned as if real** (see S12). Timeout → same path. Empty response → the broadening fallback of field 7, then possibly `FALLBACK_DATA`. Missing key → `NewsFetchError` at L218 → same fallback. **The return value carries no flag distinguishing live articles from fabricated ones**; the only trace is a WARNING log line.
10. **Determinism:** **Non-deterministic.** Three cited causes: (a) the cache key includes `current_date` [`.../news_fetcher.py:L72-L79`] and `current = datetime.now(timezone.utc)` [`.../news_fetcher.py:L204`]; (b) the `from`/`to` window slides with today [`.../news_fetcher.py:L222`]; (c) the upstream news corpus changes continuously. No random seed. Re-running today returns different articles, or — with the repo's placeholder key — the fixed `FALLBACK_DATA`.
11. **Landing location:** `data/cache/news/<sha256>.json`, CWD-relative [`.../news_fetcher.py:L32`]: `DEFAULT_CACHE_DIR = Path("data/cache/news")`. Both `data/cache/news/` (17 files) and `mandisense_ai/data/cache/news/` (6 files) exist. Write call pasted in field 8. Proof of real execution [`startup_log.txt:L33`]:

```json
{"timestamp": "2026-05-16T19:10:39.323593Z", "level": "INFO", "name": "mandisense_ai.core.agents.external_factors_agent.ingestion.news_fetcher", "message": "BBC news loaded from cache: data\\cache\\news\\a6fc1d0f4f6cdff7612004b78da12f25e8ef3a1e18e66af1c59a63d158d785f6.json", "module": "news_fetcher", "funcName": "fetch_bbc_news", "lineNo": 213}
```

12. **Licensing / ToS:** UNKNOWN — no comment or config mentions NewsAPI's terms or BBC content licensing. Note that the cache stores article titles and descriptions verbatim on disk. Resolved by consulting newsapi.org's terms.

---

### Source S5: PostgreSQL — `mandisense` database

1. **Acquisition class:** Direct DB query (psycopg2 sync pool + asyncpg async pool).
2. **Exact endpoint / URI / table / path:** connection string from `DATABASE_URL`; **development fallback is a hardcoded literal** [`mandisense_ai/db/connection.py:L29-L40`]:

```python
def _get_db_url() -> str:
    """Build DATABASE_URL from environment or use default."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        env = os.environ.get("APP__ENVIRONMENT", "development").lower()
        if env == "production":
            raise ValueError("DATABASE_URL environment variable is required in production environment.")
        url = "postgresql://user:pass@localhost:5432/mandisense"
```

   Tables (5), from [`mandisense_ai/db/schema.sql`]: `prediction_log` (L23-L66), `market_prices` (L88-L99), `arrival_volumes` (L107-L116), `model_registry` (L124-L139), `api_request_log` (L152-L164).
3. **Code location:** [`mandisense_ai/db/connection.py:L80-L91`] (sync pool) and [`mandisense_ai/db/connection.py:L161-L168`] (async pool):

```python
        import psycopg2
        from psycopg2 import pool as pg_pool

        dsn = _get_db_url()
        _sync_pool = pg_pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=dsn,
        )
```

```python
        import asyncpg
        _async_pool = await asyncpg.create_pool(
            dsn=_get_db_url(),
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
```

4. **Auth mechanism:** **connection string**, from env var **`DATABASE_URL`**. In production it is injected by Render from the managed database [`render.yaml:L12-L15`]:

```yaml
      - key: DATABASE_URL
        fromDatabase:
          name: mandisense-db
          property: connectionString
```

   In development the credential is a **hardcoded literal `user:pass`** (pasted in field 2). `.env` carries the same placeholder [`.env.example:L12`]. The URL scheme is rewritten `postgres://` → `postgresql://` [`mandisense_ai/db/connection.py:L38-L39`].
5. **Request parameters:** Parameterised SQL. **`market_prices` is the only price-bearing input table, and it is queried by exactly three statements, none of which is ever executed** [`mandisense_ai/db/queries.py:L131-L171`]:

```sql
UPSERT_MARKET_PRICE = """
INSERT INTO market_prices (commodity, mandi, price_date, modal_price, min_price, max_price)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (commodity, mandi, price_date)
DO UPDATE SET
    modal_price = EXCLUDED.modal_price,
    min_price = EXCLUDED.min_price,
    max_price = EXCLUDED.max_price;
"""

PRICE_RANGE = """
SELECT price_date, modal_price, min_price, max_price
FROM market_prices
WHERE commodity = %s AND mandi = %s
  AND price_date >= CURRENT_DATE - %s
ORDER BY price_date DESC;
"""
```

   Parameters: `commodity` (varchar 50), `mandi` (varchar 100), `price_date` (date), and an interval for `PRICE_RANGE`. **No pagination clause, no LIMIT, no OFFSET anywhere in `queries.py`.**
6. **Pagination & rate limiting:** No pagination in any market-data query. The prediction-log reads take a `limit` argument [`mandisense_ai/db/prediction_logger_db.py:L201`, `L234`] but no cursor. No retry or backoff on DB calls; failure returns `None` (field 9). Pool sizes: sync 2–10, async 2–10 with a 30 s command timeout (pasted in field 3).
7. **Volume & cadence:** **Zero rows. `market_prices` and `arrival_volumes` are never written by any code in this repository.** Exhaustive search:

```
$ rg -n 'market_prices|arrival_volumes' --glob='!ms_env/**' --glob='!**/__pycache__/**'
api/main.py:314                 (a table-existence check, string literal)
mandisense_ai/db/schema.sql:10,11,88,102,107,119   (DDL + comments)
scripts/init_db.py:19,20        (a required-table set literal)
mandisense_ai/db/queries.py:134,147,163,164        (the unexecuted SQL above)
mandisense_ai/tests/verify_database.py:64,65       (asserts the DDL text exists)
mandisense_ai/tasks/backfill.py:90,95,96           (a comment and a TODO)
```

   No module imports `queries.py` except a test using a broken path [`mandisense_ai/tests/verify_database.py:L144`]: `from db import queries`. **[DEAD?] — `queries.py`'s market-data section is unreachable, and the two time-series tables are permanently empty.** The one place that should fill `actual_7d_change` from them declines to [`mandisense_ai/tasks/backfill.py:L85-L100`]:

```python
def _lookup_actual_change(commodity: str, mandi: str, prediction_timestamp: str) -> float | None:
    """
    Look up the actual 7-day price change from market data.

    This is a placeholder that should be connected to the actual
    market_prices database table in production.
    """
    # TODO: Connect to PostgreSQL market_prices table
    # SELECT modal_price FROM market_prices
```

   `prediction_log` **is** written, on every prediction cycle [`mandisense_ai/db/prediction_logger_db.py:L99`]. Scheduling: none (no worker in `render.yaml:L1-L21`).
8. **Raw response shape:** Reconstructed from **committed DDL** [`mandisense_ai/db/schema.sql`]. `market_prices` verbatim [`mandisense_ai/db/schema.sql:L88-L99`]:

```sql
CREATE TABLE IF NOT EXISTS market_prices (
    id              BIGSERIAL       PRIMARY KEY,
    commodity       VARCHAR(50)     NOT NULL,
    mandi           VARCHAR(100)    NOT NULL,
    price_date      DATE            NOT NULL,
    modal_price     DECIMAL(10,2),
    min_price       DECIMAL(10,2),
    max_price       DECIMAL(10,2),
    created_at      TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_market_price UNIQUE (commodity, mandi, price_date)
);
```

   `arrival_volumes` verbatim [`mandisense_ai/db/schema.sql:L107-L116`]:

```sql
CREATE TABLE IF NOT EXISTS arrival_volumes (
    id                  BIGSERIAL       PRIMARY KEY,
    commodity           VARCHAR(50)     NOT NULL,
    mandi               VARCHAR(100)    NOT NULL,
    arrival_date        DATE            NOT NULL,
    quantity_tonnes     DECIMAL(12,2),
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_arrival_volume UNIQUE (commodity, mandi, arrival_date)
);
```

   `prediction_log` carries 30 columns across Context / Seasonality / Arrival / External / Phase-1.5 / Phase-2.5 / Outcome groups [`mandisense_ai/db/schema.sql:L23-L66`]; `model_registry` 14 columns [`L124-L139`]; `api_request_log` 11 columns including two JSONB bodies [`L152-L164`].
9. **Failure handling:** **Silent — every failure degrades to `None` or `0`, never an exception to the caller** [`mandisense_ai/db/connection.py:L92-L94`, `L116-L135`, `L171-L173`]:

```python
    except Exception as e:
        logger.warning(f"[DB] Sync pool creation failed: {e}")
        return None
```

```python
def execute_sync(query: str, params: tuple = None) -> Optional[List[Tuple]]:
    """Execute a query synchronously. Returns rows for SELECT, None for others."""
    with get_sync_connection() as conn:
        if conn is None:
            return None
```

   A `None` pool yields a `None` connection [`mandisense_ai/db/connection.py:L100-L103`], and every executor short-circuits to `None` / `0`. **A completely unreachable database is indistinguishable from an empty result set** at every call site. `ping_db_sync` / `ping_db_async` swallow bare `Exception` and return `False` [`L138-L144`, `L211-L217`].
10. **Determinism:** Not applicable to reads (the tables are empty). Writes are non-deterministic: `record_id UUID ... DEFAULT gen_random_uuid()` and `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` [`mandisense_ai/db/schema.sql:L26`, `L29`].
11. **Landing location:** N/A as a source. As a sink, `prediction_log` via [`mandisense_ai/db/prediction_logger_db.py:L99`], with a JSONL fallback file when the DB is down [`mandisense_ai/db/prediction_logger_db.py:L320`]: `path = self._fallback_dir / "meta_predictions.jsonl"`.
12. **Licensing / ToS:** N/A — self-hosted.

---

### Source S6: Redis — cached mandi snapshots

1. **Acquisition class:** SDK/client library (`redis-py`), read-through cache.
2. **Exact endpoint / URI / table / path:** `REDIS_URL`, or host/port/db assembled from parts. Keys: `f"mandi_snapshot:{commodity}"` [`mandisense_ai/services/mandi_data_service.py:L38-L40`].
3. **Code location:** [`mandisense_ai/lib/cache.py:L36-L50`]

```python
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0, socket_connect_timeout=2.0)
        else:
            env = os.getenv("APP__ENVIRONMENT", "development").lower()
            host = os.getenv("REDIS_HOST")
            if not host:
                if env == "production":
                    raise ValueError("Either REDIS_URL or REDIS_HOST environment variable is required in production environment.")
                host = "localhost"
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD") or None
```

4. **Auth mechanism:** **connection string or password**, from env vars **`REDIS_URL`** (preferred) or **`REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` / `REDIS_PASSWORD`**. Production value injected by Render [`render.yaml:L16-L20`]. Development default is the unauthenticated literal `localhost:6379/0` (pasted above; also `.env.example:L17`). No hardcoded password.
5. **Request parameters:** cache key (above); TTL clamped to **[1800, 3600] seconds** [`mandisense_ai/lib/cache.py:L18-L19`, `L24-L27`]:

```python
_MIN_TTL_SECONDS = 1800
_MAX_TTL_SECONDS = 3600
```

   No query params, headers, or pagination.
6. **Pagination & rate limiting:** None. Socket timeouts 2.0 s connect / 2.0 s read (pasted in field 3). No retry, no backoff, no max pages.
7. **Volume & cadence:** One snapshot document per commodity; size = the mandi list returned by S2. Full-refresh on write; TTL-driven expiry. No watermark or cursor. **Scheduling absent.** Because S2 is dead (S2 field 7), **this cache is never populated with live data in practice** — [DEAD?] as a market-data source.
8. **Raw response shape:** JSON list of `{name, price, arrival, lat, lon}` — the normalised record from [`mandisense_ai/services/mandi_data_service.py:L28-L34`], validated against `REQUIRED_FIELDS = {"name", "price", "arrival", "lat", "lon"}` [`mandisense_ai/lib/validator.py:L4`]. Reconstructed from **parsing/validation code**; no fixture or sample file exists.
9. **Failure handling:** **Silent, with a file fallback.** [`mandisense_ai/lib/cache.py:L55-L58`]:

```python
    except Exception as exc:
        log_failure("mandi_cache", f"redis client unavailable: {exc}")
        _redis_client = None
        return None
```

   A `None` client sends every read and write to `mandisense_ai/data/cache.json` [`mandisense_ai/lib/cache.py:L16-L17`]. Downstream, a cache miss becomes fabricated data [`mandisense_ai/services/mandi_data_service.py:L113-L117`].
10. **Determinism:** Non-deterministic — TTL expiry is wall-clock driven and the fallback path depends on Redis reachability. No seed.
11. **Landing location:** Redis key-space, or `mandisense_ai/data/cache.json` on the local filesystem [`mandisense_ai/lib/cache.py:L107-L113`].
12. **Licensing / ToS:** N/A — self-hosted.

---

### Source S7: In-code synthetic price/arrival generator — `generate_historical_data()`

**This source produces the dataset the running application actually serves.** It is the single most consequential finding of Phase 1.

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE.**
2. **Exact endpoint / URI / table / path:** none — a pure function. Output path template: `mandisense_ai/data/raw/v1/{commodity}/{mandi_id}.csv` [`mandisense_ai/tasks/ingest_historical_data.py:L13`, `L141`].
3. **Code location:** [`mandisense_ai/tasks/ingest_historical_data.py:L24-L72`]

```python
def generate_historical_data(commodity, mandi_id, mandi_name):
    """
    Simulates a high-quality historical fetch with realistic price dynamics.
    In a real production environment, this would call AgmarknetClient.
    """
    np.random.seed(hash(mandi_id + commodity) % 1234)

    start_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    date_range = pd.date_range(start_date, end_date)

    # Base prices for commodities
    base_prices = {
        "tomato": 1500,
        "onion": 2000,
        "potato": 1800,
        "garlic": 8000,
        "ginger": 6000
    }
```

```python
    for dt in date_range:
        # Simulate some missing days (approx 5%)
        if np.random.rand() < 0.05:
            continue

        # Price dynamics: seasonality + random walk
        month = dt.month
        seasonality = np.sin(2 * np.pi * month / 12) * (base_price * 0.3)
        current_price = base_price + seasonality + np.random.normal(0, base_price * 0.05)
        current_price = max(500, current_price)

        # Arrivals: seasonal + inversely correlated with price
        arrivals = (base_price / current_price) * 50 + np.random.normal(20, 5)
        arrivals = max(5, arrivals)
```

   The docstring is explicit that this stands in for a real fetch, and that the real fetch does not exist ("*In a real production environment, this would call AgmarknetClient*"). The call site is not guarded by any flag [`mandisense_ai/tasks/ingest_historical_data.py:L93-L95`]:

```python
            try:
                # STEP 1 & 2: Fetch and Validate
                df = generate_historical_data(commodity, mandi_id, mandi_name)
```

4. **Auth mechanism:** **none** — no network call is made.
5. **Request parameters:** N/A. Generation parameters: `COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]` [`mandisense_ai/tasks/ingest_historical_data.py:L10`]; 15 mandis read from `config/mandi_master.csv` [`L12`, `L76-L77`]; date range `2023-01-01 → datetime.now()`; base prices as pasted; 5 % random day-drop; price noise σ = 5 % of base; arrival noise `N(20, 5)`.
6. **Pagination & rate limiting:** N/A — no network. The outer loop is 5 commodities × 15 mandis = **75 files** [`mandisense_ai/tasks/ingest_historical_data.py:L83-L95`].
7. **Volume & cadence:** 75 files. Verified on disk: `mandisense_ai/data/raw/v1/` contains exactly 75 CSVs (5 commodity dirs × 15 mandis). `v1/tomato/kolar.csv` holds **1140 rows spanning 2023-01-01 → 2026-05-03** — the end date is the `datetime.now()` of the generation run. Full-refresh; no watermark, no incremental logic. **Scheduling absent** — `__main__` only [`mandisense_ai/tasks/ingest_historical_data.py:L156-L157`].
8. **Raw response shape:** From the **committed output files** and the writing code [`mandisense_ai/tasks/ingest_historical_data.py:L64-L70`, `L114`]. Header and first rows of `mandisense_ai/data/raw/v1/tomato/kolar.csv`:

```
date,mandi_name,commodity,modal_price,arrivals,mandi_id
2023-01-01,Kolar,tomato,1757.76,63.61,kolar
2023-01-02,Kolar,tomato,1732.34,64.15,kolar
...
2026-05-03,Kolar,tomato,1770.05,66.72,kolar
```

   Note this schema shares **no columns** with the real S1 extract beyond `date` and `commodity` — no `state`, no `min_price`/`max_price`, no `arrivals_tonnes`, no provenance columns.
9. **Failure handling:** Per-mandi failures are caught, printed, and skipped [`mandisense_ai/tasks/ingest_historical_data.py:L144-L146`]:

```python
            except Exception as e:
                print(f"    [ERROR] Failed to ingest {mandi_name}: {e}")
                continue
```

   No 4xx/5xx/timeout semantics apply. The failure is visible only on stdout — nothing is logged and the run still reports success at [`L153`].
10. **Determinism:** **Not reproducible, on two independent counts, both cited.**
    - `np.random.seed(hash(mandi_id + commodity) % 1234)` [`mandisense_ai/tasks/ingest_historical_data.py:L29`] seeds from Python's **`hash()` of a `str`**, which is salted per process by `PYTHONHASHSEED` unless that variable is pinned. `PYTHONHASHSEED` is not set in `.env.example`, `render.yaml`, `Dockerfile`, or `docker-compose.yml`. [INFERRED] from the cited line plus documented CPython string-hash randomisation: **every run produces a different seed, hence different data.**
    - `end_date = datetime.now()` [`mandisense_ai/tasks/ingest_historical_data.py:L32`] — the series length changes every day it is run.
11. **Landing location:** `mandisense_ai/data/raw/v1/{commodity}/{mandi_id}.csv` [`mandisense_ai/tasks/ingest_historical_data.py:L141-L142`]:

```python
                save_path = comm_dir / f"{mandi_id}.csv"
                df.to_csv(save_path, index=False)
```

    Plus a quality report at `mandisense_ai/logs/data_quality_report_v1.csv` [`L150-L151`].
12. **Licensing / ToS:** N/A — no external data involved.

---

### Source S8: Hardcoded mandi master list — `generate_mandi_master.py`

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE** (hardcoded literal table). The coordinate values are real-world facts, but they are typed into source with no cited origin.
2. **Exact endpoint / URI / table / path:** none. Output: `mandi_master_temp.csv`, written to the **current working directory** [`mandisense_ai/scratch/generate_mandi_master.py:L65`].
3. **Code location:** [`mandisense_ai/scratch/generate_mandi_master.py:L12-L20`] (25-entry literal, first rows shown) and [`L43-L54`]:

```python
bengaluru_coords = (12.9716, 77.5946)

# Candidate list with coordinates
candidates = [
    {"mandi_name": "Bangalore", "district": "Bengaluru", "state": "Karnataka", "lat": 13.0225, "lon": 77.5475},
    {"mandi_name": "Kolar", "district": "Kolar", "state": "Karnataka", "lat": 13.1377, "lon": 78.1299},
    {"mandi_name": "Ramanagara", "district": "Ramanagara", "state": "Karnataka", "lat": 12.7233, "lon": 77.2759},
```

```python
for m in candidates:
    m["distance_from_bengaluru_km"] = haversine(bengaluru_coords[0], bengaluru_coords[1], m["lat"], m["lon"])

# Sort by distance
sorted_mandis = sorted(candidates, key=lambda x: x["distance_from_bengaluru_km"])

# Take top 15
final_15 = sorted_mandis[:15]
```

4. **Auth mechanism:** **none** — no network call.
5. **Request parameters:** N/A. Selection parameters: 25 hardcoded candidates, ranked by haversine distance from `(12.9716, 77.5946)`, truncated to the nearest **15**.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** 15 rows, one-shot. No cadence, no scheduling — `__main__`-less top-level script.
8. **Raw response shape:** From the **committed output file** `mandi_master_temp.csv` and the column list at [`mandisense_ai/scratch/generate_mandi_master.py:L60-L62`]:

```
mandi_id,mandi_name,district,state,latitude,longitude,distance_from_bengaluru_km
bangalore,Bangalore,Bengaluru,Karnataka,13.0225,77.5475,7.6207163295186024
```

   The operative config file `mandisense_ai/config/mandi_master.csv` has **one extra column** (`old_mandi_id`) and different `mandi_id` values:

```
mandi_id,mandi_name,district,state,latitude,longitude,distance_from_bengaluru_km,old_mandi_id
bangalore_yeshwanthpur,Bangalore,Bengaluru,Karnataka,13.0225,77.5475,7.62,bangalore
kolar_apmc,Kolar,Kolar,Karnataka,13.1377,78.1299,60.85,kolar
```

9. **Failure handling:** **None** — no try/except anywhere in the file; any error aborts the script.
10. **Determinism:** **Deterministic.** No randomness, no clock dependency — pure arithmetic over a fixed literal list. This is the only generator in the repository that is fully reproducible.
11. **Landing location:** `./mandi_master_temp.csv` (CWD) [`mandisense_ai/scratch/generate_mandi_master.py:L65`]:

```python
df.to_csv("mandi_master_temp.csv", index=False)
```

    **The path from here to `mandisense_ai/config/mandi_master.csv` is a hidden manual step.** No code copies, renames, or moves this file, and no code creates `config/mandi_master.csv` — the only writer of that path *mutates a file that must already exist* [`mandisense_ai/tasks/refine_raw_data.py:L17-L32`]:

```python
def refine_mandi_master():
    df = pd.read_csv(CONFIG_PATH)

    def get_specific_id(row):
        base_id = row['mandi_id']
        if base_id == "bangalore":
            return "bangalore_yeshwanthpur"
        return f"{base_id}_apmc"

    df['old_mandi_id'] = df['mandi_id']
    df['mandi_id'] = df.apply(get_specific_id, axis=1)

    # Save refined master
    df.to_csv(CONFIG_PATH, index=False)
```

    **This mutation is not idempotent.** Re-running it on the current file yields `mandi_id = "kolar_apmc_apmc"` and `old_mandi_id = "kolar_apmc"`, silently corrupting the ID map used at [`mandisense_ai/tasks/refine_raw_data.py:L44`]. [INFERRED] directly from the pasted function applied to the pasted current file contents.
12. **Licensing / ToS:** UNKNOWN — the coordinates are stated with no source attribution anywhere in the file. Resolved by asking the author where the lat/lon values came from.

---

### Source S9: `festival_calendar.csv` — flat file, origin undetermined

1. **Acquisition class:** Flat file present in the working tree. **Not committed to the repo** (see field 11) and **produced by no code** — so strictly it is a *manual download or hand-authored file*; the evidence of the manual step is the total absence of a writer (field 3).
2. **Exact endpoint / URI / table / path:** `mandisense_ai/data/raw/festival_calendar.csv`, resolved at runtime as `Path(settings.paths.raw_data) / "festival_calendar.csv"` [`mandisense_ai/core/agents/seasonality_agent.py:L27`], where `settings.paths.raw_data` resolves to `D:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\data\raw` [`mandisense_ai/config/settings.py:L14-L19`, `L39`].
3. **Code location — reader** [`mandisense_ai/core/agents/seasonality_agent.py:L25-L40`]:

```python
def merge_festivals(df: pd.DataFrame) -> pd.DataFrame:
    """Safely merges optional explicit disjoint festival constraints mapping structural limits."""
    raw_path = Path(settings.paths.raw_data) / "festival_calendar.csv"
    if not raw_path.exists():
        df['is_festival'] = df.get('is_festival_season', 0)
        return df

    try:
        fdf = pd.read_csv(raw_path)
        date_col = next((c for c in fdf.columns if 'date' in str(c).lower()), None)
        if date_col:
            fdf[date_col] = pd.to_datetime(fdf[date_col], errors='coerce')
            fdf['is_festival'] = 1
            fdf = fdf[[date_col, 'is_festival']].dropna().rename(columns={date_col: 'date'})
            df = df.merge(fdf, on='date', how='left')
            df['is_festival'] = df['is_festival'].fillna(0).astype(int)
```

   **Code location — writer: NONE.** Search over `.py` for the literal filename returns only the two reader sites in `seasonality_agent.py` (L27 and L145) plus one unrelated parameter name in `agent_features.py:L210,L217`. No `to_csv`, no download, no generator.
4. **Auth mechanism:** **none** — local file.
5. **Request parameters:** N/A. The reader consumes only two of the six columns (`date`, plus a synthesised `is_festival` constant 1) — `window_days`, `region`, and `commodity_relevance` **are read from disk and discarded**.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** **132 rows**, spanning 2015-01-01 → 2025-12-25 (verified by reading the file). Static; no refresh mechanism exists. **Note the coverage gap:** the calendar ends 2025-12-25, while the v1 synthetic price series runs to 2026-05-03 — any 2026 date joins to `is_festival = 0` by construction.
8. **Raw response shape:** From the **committed file itself** (no parser-implied schema beyond `date`; no fixture):

```
festival_name,date,year,window_days,region,commodity_relevance
New Year,2015-01-01,2015,3,All India,All
Pongal,2015-01-14,2015,5,South India,"Onion,Tomato,Potato,Tur Dal"
Holi,2015-03-06,2015,3,North India,All
...
Christmas,2025-12-25,2025,3,All India,All
```

9. **Failure handling:** **Silent degradation to zero.** Missing file → the `if not raw_path.exists()` branch at L28-L30 assigns a default with no warning. Any parse error [`mandisense_ai/core/agents/seasonality_agent.py:L43-L45`]:

```python
    except Exception as e:
        logger.warning(f"Festival relational mapping decoupled conditionally: {e}. Defaulting assumptions.")
        df['is_festival'] = df.get('is_festival_season', 0)
```

   A missing festival calendar and a year with no festivals are indistinguishable downstream.
10. **Determinism:** **Deterministic** — a static file, read the same way every time. No clock, no seed.
11. **Landing location:** N/A as a source; it *is* the landing location. **Git-ignored** — `mandisense_ai/.gitignore:L43` (`data/raw/*`) excludes it, and it does not appear in `git ls-files mandisense_ai/data/`. It exists only on this machine.
12. **Licensing / ToS:** UNKNOWN — no header comment, no README entry, no attribution. Whether these dates were transcribed from a government almanac, a commercial calendar, or written from memory is not determinable. Resolved by asking the author.

---

### Source S10: `mandi_metadata.csv` — reliability weights, origin undetermined

1. **Acquisition class:** Flat file present in the working tree, **produced by no code**. Manual authorship is the only remaining explanation; the evidence is the absence of any writer (field 3).
2. **Exact endpoint / URI / table / path:** `mandisense_ai/config/mandi_metadata.csv` [`mandisense_ai/tasks/finalize_raw_data.py:L8`].
3. **Code location — reader** [`mandisense_ai/tasks/finalize_raw_data.py:L28-L30`]:

```python
    # Load reliability weights
    weights_df = pd.read_csv(METADATA_PATH)
    weights_map = dict(zip(weights_df['mandi_id'], weights_df['mandi_weight']))
```

   **Code location — writer: NONE.** `rg 'mandi_master|mandi_metadata' --glob='*.py'` returns 12 hits; the only one touching `mandi_metadata` is the `METADATA_PATH` constant and the read above. No `to_csv` targets it.
4. **Auth mechanism:** **none** — local file.
5. **Request parameters:** N/A. Two columns consumed: `mandi_id`, `mandi_weight`. Default when a mandi is absent from the map is `0.7` [`mandisense_ai/tasks/finalize_raw_data.py:L90`].
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** 15 rows (one per mandi). Static; no refresh path.
8. **Raw response shape:** From the **committed file**:

```
mandi_id,mandi_weight
kolar_apmc,1.0
ramanagara_apmc,0.95
bangalore_yeshwanthpur,0.95
chickballapur_apmc,0.9
```

9. **Failure handling:** **None.** The `pd.read_csv` at L29 is not wrapped; a missing file raises `FileNotFoundError` and aborts `finalize_data()`.
10. **Determinism:** **Deterministic** — static file.
11. **Landing location:** N/A as a source. Unlike S9 it is **not** git-ignored (it sits under `config/`, not `data/`), so it is version-controlled.
12. **Licensing / ToS:** N/A. **But the weights themselves are unexplained:** no comment, docstring, or document states how `1.0` for Kolar and `0.9` for Chickballapur were derived. UNKNOWN — I looked in the file, in `finalize_raw_data.py`, and in both READMEs. Resolved by asking the author for the derivation.

---

### Source S11: In-code synthetic ML training set — `build_dataset()` (External Factors Agent)

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE.**
2. **Exact endpoint / URI / table / path:** none. Output: `data/training/dataset.csv`, **CWD-relative** [`mandisense_ai/core/agents/external_factors_agent/ml/dataset_builder.py:L10`].
3. **Code location:** [`mandisense_ai/core/agents/external_factors_agent/ml/dataset_builder.py:L20-L34`]

```python
        # Simulate historical simulation + price data
        random.seed(42)  # For reproducibility
        for i in range(100):
            for c in COMMODITIES:
                ev_count_7d = random.randint(0, 5)
                ev_count_3d = random.randint(0, min(3, ev_count_7d))
                avg_conf = random.uniform(0.4, 0.9) if ev_count_7d > 0 else 0.0
                max_imp = random.uniform(0.1, 0.8) if ev_count_7d > 0 else 0.0
                sum_imp = max_imp * random.uniform(1.0, 1.5) if ev_count_7d > 0 else 0.0
                recent = 1 if ev_count_3d > 0 else 0
                days_since = random.randint(0, 30) if ev_count_7d > 0 else 30

                # Target formulation
                price_change = sum_imp * random.uniform(0.01, 0.1) - 0.01
```

   **The target variable is a deterministic function of the features plus uniform noise** — `price_change = sum_imp * U(0.01, 0.1) - 0.01`. Any model trained on this learns the generator, not a market. The trainer calls it unconditionally before every fit [`.../ml/trainer.py:L15-L24`]:

```python
def train_model():
    print("Building dataset...")
    build_dataset()

    dataset_path = "data/training/dataset.csv"
    if not os.path.exists(dataset_path):
        print("Dataset missing -> skip training.")
        return

    df = pd.read_csv(dataset_path)
```

4. **Auth mechanism:** **none** — no network call.
5. **Request parameters:** N/A. Generation parameters: 100 iterations × `COMMODITIES`; event counts `randint(0,5)`; confidences `U(0.4,0.9)`; impacts `U(0.1,0.8)`; dates `f"2026-04-{random.randint(1, 28):02d}"` [`.../dataset_builder.py:L37`] — **every date is in April 2026**.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** 100 × len(COMMODITIES) rows plus **one deliberately malformed row** appended to exercise the skip path [`.../dataset_builder.py:L49-L52`]:

```python
        # Inject bad rows to test skipping logic
        writer.writerow([
            "2026-04-20", "onion", 1, 1, 0.9, 0.1, 0.1, 1, 1, ""
        ])
```

   Observed on disk: `mandisense_ai/core/agents/external_factors_agent/data/training/dataset.csv` has **501 data rows** (100 × 5 commodities + 1 bad row). Full-refresh on every `train_model()` call. **Scheduling absent.**
8. **Raw response shape:** From the **writing code** [`.../dataset_builder.py:L15-L19`] and the **committed output file**:

```
date,commodity,event_count_3d,event_count_7d,avg_confidence,max_impact,sum_impact,recent_event_flag,days_since_last_event,price_change
2026-04-24,onion,0,5,0.4125053776113335,0.2925205228583835,0.3251673837738332,0,23,-0.003748798216600218
2026-04-01,tomato,0,4,0.6952462562245199,0.12224787563724852,0.12797489765244957,0,7,-0.0028996998088918263
```

9. **Failure handling:** **None in the generator** — the `with open(filename, 'w')` at L13 is unguarded. The trainer degrades silently on a missing file (`print` + `return`, pasted in field 3) and on an empty frame [`.../ml/trainer.py:L32-L34`].
10. **Determinism:** **Deterministic** — `random.seed(42)` at [`.../dataset_builder.py:L22`] seeds Python's `random` module with a literal integer, which is stable across processes (unlike S7's `hash()`-derived seed). Re-running reproduces the file byte-for-byte. **The values are reproducible; they are still fabricated.**
11. **Landing location:** `data/training/dataset.csv` relative to CWD [`.../dataset_builder.py:L10-L11`]:

```python
    filename = "data/training/dataset.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
```

    On disk the file exists only at `mandisense_ai/core/agents/external_factors_agent/data/training/dataset.csv`, i.e. it was generated with CWD set to the agent package — **not** at `./data/training/`, which does not exist. See §6b.
12. **Licensing / ToS:** N/A — no external data.

---

### Source S12: Hardcoded fallback news corpus — `FALLBACK_DATA`

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE** (hardcoded literal list).
2. **Exact endpoint / URI / table / path:** none — a module-level constant.
3. **Code location:** [`mandisense_ai/core/agents/external_factors_agent/ingestion/news_ingestor.py:L9-L18`], reproduced in full:

```python
FALLBACK_DATA = [
    {"title": "India bans onion export", "description": "Export restriction imposed", "date": "2026-04-20"},
    {"title": "Import duty reduced on pulses", "description": "Imports expected to rise", "date": "2026-04-18"},
    {"title": "Heavy rainfall damages tomato crops", "description": "Flood conditions", "date": "2026-04-21"},
    {"title": "Drought in Karnataka affects rice", "description": "Low rainfall impact", "date": "2026-04-17"},
    {"title": "MSP increased for wheat", "description": "Government policy", "date": "2026-04-19"},
    {"title": "Fuel prices rise", "description": "Transport costs increase", "date": "2026-04-22"},
    {"title": "Export demand rises for rice", "description": "Global demand surge", "date": "2026-04-16"},
    {"title": "Stock limit imposed on onions", "description": "Anti-hoarding step", "date": "2026-04-21"},
]
```

   **These are invented headlines describing events that did not necessarily occur.** They are returned to the agent through the same code path and in the same shape as live articles [`.../news_ingestor.py:L59-L61`], with no provenance flag.
4. **Auth mechanism:** **none.**
5. **Request parameters:** N/A. Note every entry is dated 2026-04-16 … 2026-04-22 — a fixed one-week window that will fall outside any recency filter as time passes.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** exactly 8 records, constant. Returned on **every** news-fetch failure, and — given `.env` holds the placeholder `NEWS_API_KEY` (S4 field 4) — that is the default behaviour of a fresh checkout.
8. **Raw response shape:** the literal above, normalised to `{title, description, published_at, date}` [`.../news_ingestor.py:L36-L43`]:

```python
def _normalize_fallback_article(item: dict) -> dict:
    formatted_date = _normalize_date(item.get("date", ""))
    return {
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "published_at": formatted_date,
        "date": formatted_date,
    }
```

9. **Failure handling:** This *is* the failure handler (see S4 field 9). Its own failure mode: `_normalize_date` falls through to `datetime.now(timezone.utc).date()` for an unparseable date [`.../news_ingestor.py:L30-L33`].
10. **Determinism:** **Deterministic in content**, non-deterministic in *whether it is used* — that depends on network reachability and on whether `NEWS_API_KEY` is set. The date normalisation has a `datetime.utcnow()` branch [`.../news_ingestor.py:L22-L23`] that is not reached for these well-formed literals.
11. **Landing location:** In-memory only; **but it is written through to `data/cache/news/<sha256>.json` only in the live path, not this one** — the fallback bypasses the cache write at [`.../news_fetcher.py:L234-L235`] because it is produced above that layer. So fabricated articles leave no on-disk trace.
12. **Licensing / ToS:** N/A.

---

### Source S13: Hardcoded fallback mandi snapshot — `fallback_data()`

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE** (hardcoded literal record).
2. **Exact endpoint / URI / table / path:** none — a function returning a literal.
3. **Code location:** [`mandisense_ai/services/mandi_data_service.py:L64-L77`], reproduced in full:

```python
def fallback_data(commodity: str) -> List[Dict[str, Any]]:
    snapshot = _last_known_valid_snapshot(commodity)
    if snapshot:
        return snapshot

    return [
        {
            "name": f"{str(commodity).strip().title() or 'Fallback'} Mandi",
            "price": 10000.0,
            "arrival": 50.0,
            "lat": 0.0,
            "lon": 0.0,
        }
    ]
```

   **`price: 10000.0` and `arrival: 50.0` are invented constants**, and `lat/lon = 0.0` places the mandi in the Gulf of Guinea. This record passes the validator — it requires only `price > 0` and `arrival >= 0` [`mandisense_ai/lib/validator.py:L39-L45`]:

```python
        price = float(record["price"])
        arrival = float(record["arrival"])

        if price <= 0:
            return False
        if arrival < 0:
            return False
```

4. **Auth mechanism:** **none.**
5. **Request parameters:** N/A. One parameter, `commodity`, used only to build the display name.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** exactly 1 record. Returned on **four distinct paths** [`mandisense_ai/services/mandi_data_service.py:L83`, `L115`, `L121`, `L126`] — including the unconditional initialisation at L83, so it is the value in play before any fetch is even attempted. Given S2 is both dead and structurally broken, this is the **only** value this service can ever return.
8. **Raw response shape:** the literal above, wrapped in the envelope at [`mandisense_ai/services/mandi_data_service.py:L134-L139`] with `"status": "OK"` and `"source": "fallback"`.
9. **Failure handling:** This *is* the failure handler. It has no failure mode of its own — the literal cannot fail construction.
10. **Determinism:** **Deterministic in content.** The surrounding envelope is not: `datetime.datetime.utcnow()` at [`mandisense_ai/services/mandi_data_service.py:L137`].
11. **Landing location:** In-memory. **Not** cached — `set_cache` is called only on the live branch [`mandisense_ai/services/mandi_data_service.py:L103`], so a fallback value never contaminates Redis.
12. **Licensing / ToS:** N/A.

---

### Source S14: Hardcoded mandi coordinate registry — `MarketRegistry.MANDI_COORDS`

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE** (hardcoded literal lookup table). This table supplies the `latitude`/`longitude` request parameters for S3.
2. **Exact endpoint / URI / table / path:** none — a class attribute.
3. **Code location:** [`mandisense_ai/cognition/world_model/topology.py:L21-L37`], reproduced in full:

```python
    MANDI_COORDS = {
        "kolar_apmc": (13.1377, 78.1299),
        "bangalore_apmc": (12.9716, 77.5946),
        "bangalore_rural": (13.2847, 77.6078),
        "mumbai_apmc": (19.0760, 72.8777),
        "nashik_apmc": (20.0110, 73.7903),
        "delhi_azadpur": (28.7161, 77.1723),
        "bengaluru": (12.9716, 77.5946) # Legacy alias
    }

    DISTRICT_MAPPINGS = {
        "kolar": "kolar_apmc",
        "bangalore": "bangalore_apmc",
        "mumbai": "mumbai_apmc",
        "nashik": "nashik_apmc",
        "delhi": "delhi_azadpur"
    }
```

   **Coverage gap:** this registry holds **7 keys**, while `config/mandi_master.csv` defines **15 mandis** and the v4 dataset contains all 15. Mandis such as `anekal_apmc`, `hoskote_apmc`, `magadi_apmc`, `kunigal_apmc` resolve to `None` unless one of the five substring district rules happens to match [`.../topology.py:L45-L50`], and then `resolve_mandi_coordinates` raises [`.../processing/weather_signal.py:L67-L76`]:

```python
    coords = MarketRegistry.resolve_coordinates(mandi)
    if coords:
        return coords

    if district:
        coords = MarketRegistry.resolve_coordinates(district)
        if coords:
            return coords

    raise KeyError(f"INTEGRITY FAILURE: No coordinates found for '{mandi}' @ '{district or 'unknown_dist'}'")
```

   That `KeyError` is caught by the swallow at [`.../processing/weather_signal.py:L223`] and becomes `weather_signal: 0.0`. **[INFERRED] from the pasted registry, the pasted resolver, and the 15-row master: for the majority of mandis the weather signal is structurally zero and no weather request is ever issued.**
4. **Auth mechanism:** **none.**
5. **Request parameters:** N/A. Note the second-chance fallback if the import fails [`.../processing/weather_signal.py:L36-L42`]:

```python
try:
    from mandisense_ai.cognition.world_model.topology import MarketRegistry
except ImportError:
    # Fallback for standalone scripts
    class MarketRegistry:
        @classmethod
        def resolve_coordinates(cls, mandi_id: str): return (12.9716, 77.5946) # Bengaluru fallback
```

   Under that branch **every mandi in India is assigned Bengaluru's coordinates**, silently.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** 7 coordinate pairs + 5 district aliases, constant. No refresh path.
8. **Raw response shape:** `Tuple[float, float]` or `None` [`.../topology.py:L39-L50`].
9. **Failure handling:** returns `None` on miss (pasted in field 3); the caller converts that to a `KeyError`, which is then swallowed upstream.
10. **Determinism:** **Deterministic** — a literal dict.
11. **Landing location:** In-memory only; never persisted.
12. **Licensing / ToS:** UNKNOWN — the coordinates carry no attribution. Same gap as S8.

---

### Source S15: Hardcoded cross-commodity spillover matrix

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE** (hardcoded matrix). Presented in the report figures as an estimated econometric result.
2. **Exact endpoint / URI / table / path:** none — a module-level `np.array`.
3. **Code location:** [`scratch/generate_cross_commodity_suite.py:L15-L32`], reproduced in full:

```python
# --- DATA DEFINITIONS ---
commodities = ['Tomato', 'Onion', 'Potato', 'Garlic', 'Ginger', 'Dry Chillies']
n_comm = len(commodities)

# Normalized spillover matrix (Granger causality / VAR variance decomposition strengths)
# Rows: Source (Cause) -> Columns: Target (Effect)
spillover_matrix = np.array([
    [0.48, 0.24, 0.18, 0.05, 0.03, 0.02], # Tomato shocks propagate heavily to Onion, Potato
    [0.15, 0.52, 0.22, 0.08, 0.02, 0.01], # Onion shocks propagate to Potato, Tomato
    [0.10, 0.18, 0.58, 0.06, 0.05, 0.03], # Potato shocks propagate to Onion, Tomato
    [0.08, 0.12, 0.05, 0.62, 0.09, 0.04], # Garlic shocks propagate to Onion, Ginger
    [0.04, 0.05, 0.08, 0.14, 0.65, 0.04], # Ginger shocks propagate to Garlic
    [0.03, 0.02, 0.04, 0.06, 0.08, 0.77]  # Dry Chillies are mostly localized
])

# Normalize rows to make it clean
for i in range(n_comm):
    spillover_matrix[i] /= spillover_matrix[i].sum()
```

   **The comment labels these numbers "Granger causality / VAR variance decomposition strengths". No Granger test and no VAR model is fitted anywhere in this file or in the repository** — `rg 'grangercausalitytests|VAR\(|statsmodels.tsa.vector_ar'` finds no estimation call for this figure. The 36 values are typed in by hand.
4. **Auth mechanism:** **none.**
5. **Request parameters:** N/A. Six commodities, fixed.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** one 6×6 matrix, constant. Run on demand to regenerate report figures; no schedule.
8. **Raw response shape:** `np.ndarray` of shape (6, 6), float64, rows normalised to sum 1.
9. **Failure handling:** **None** — no try/except in the data-definition block.
10. **Determinism:** **Deterministic** — literals plus arithmetic; no seed, no clock. Reproducible and fabricated.
11. **Landing location:** rendered directly to `imag/figure_5_5a_spillover.png`, `imag/figure_5_5b_irf.png`, `imag/figure_5_5c_net_spillover.png`, `imag/dependency_network.png` — per the prior audit's chart inventory [`docs/reveng/PHASE_7_EDA_VIZ.md`, charts 11–14]. Never persisted as data.
12. **Licensing / ToS:** N/A.

---

### Source S16: Synthetic system-latency distributions

1. **Acquisition class:** **SYNTHETIC / GENERATED-IN-CODE** (`np.random` draws), labelled in-source as measured metrics.
2. **Exact endpoint / URI / table / path:** none.
3. **Code location:** [`scratch/generate_system_latency.py:L15-L32`]

```python
# --- DATA GENERATION BASED ON ACTUAL LOG METRICS ---
np.random.seed(42)

# Cache Hits (Redis) - mean=12ms, std=3ms
cache_hits = np.random.normal(12, 3, 2500)
cache_hits = np.clip(cache_hits, 4, 30)

# Cache Misses (PostgreSQL / File Read) - mean=280ms, std=45ms
cache_misses = np.random.normal(280, 45, 1200)
cache_misses = np.clip(cache_misses, 120, 500)

# Database Outage / Fallback Activation (Instant Circuit Breaker response) - mean=8ms, std=2ms
circuit_breaker = np.random.normal(8, 2, 800)
circuit_breaker = np.clip(circuit_breaker, 2, 15)

# External API Queries (Agmarknet Live) - mean=1850ms, std=320ms
external_queries = np.random.normal(1850, 320, 500)
external_queries = np.clip(external_queries, 800, 3000)
```

   The banner comment at L15 asserts the data is "**BASED ON ACTUAL LOG METRICS**". **No log file is opened in this script** — there is no `open()`, no `read_csv`, no path constant pointing at `logs/`. The numbers are parameters of four normal distributions typed into source. The `external_queries` block is additionally counterfactual: it purports to measure "Agmarknet Live" latency for a fetch path that cannot succeed (S2 field 3).
4. **Auth mechanism:** **none.**
5. **Request parameters:** N/A. Distribution parameters as pasted; sample sizes 2500 / 1200 / 800 / 500.
6. **Pagination & rate limiting:** N/A.
7. **Volume & cadence:** 5000 synthetic observations per run. On demand; no schedule.
8. **Raw response shape:** four 1-D float arrays, concatenated at [`scratch/generate_system_latency.py:L35`].
9. **Failure handling:** **None** — no error handling in the generation block.
10. **Determinism:** **Deterministic** — `np.random.seed(42)` at [`scratch/generate_system_latency.py:L16`] is a literal integer seed, stable across processes. Reproducible and fabricated.
11. **Landing location:** rendered to `imag/figure_5_9a_latency_hist.*` and siblings [`docs/reveng/PHASE_7_EDA_VIZ.md`, charts 15–18]. Never persisted as data.
12. **Licensing / ToS:** N/A.

---

### Source S17: Chrome DevTools Protocol — local screenshot capture

1. **Acquisition class:** REST API + WebSocket, **self-referential** (captures this project's own frontend). Not a pipeline data source; included for completeness because it matched the P1 sweep.
2. **Exact endpoint / URI / table / path:** `http://127.0.0.1:{PORT}/json/version` and `http://127.0.0.1:{PORT}/json`, then the returned `webSocketDebuggerUrl`.
3. **Code location:** [`scratch/capture_traderos.py:L52-L67`]

```python
        version = None
        for _ in range(60):
            try:
                version = requests.get(f"http://127.0.0.1:{PORT}/json/version", timeout=1).json()
                break
            except Exception:
                time.sleep(0.25)
        if not version:
            raise RuntimeError("Edge DevTools endpoint did not start")

        targets = requests.get(f"http://127.0.0.1:{PORT}/json", timeout=2).json()
        page = next((target for target in targets if target.get("type") == "page"), None)
        if not page:
            raise RuntimeError("No page target found")
```

4. **Auth mechanism:** **none** — loopback DevTools port.
5. **Request parameters:** none beyond the path; the browser is launched with a fixed flag set including `--window-size=1600,1000` [`scratch/capture_traderos.py:L43`].
6. **Pagination & rate limiting:** N/A. Startup poll: 60 attempts × 0.25 s sleep (pasted above) — a 15-second budget.
7. **Volume & cadence:** one screenshot per invocation. Manual; no schedule.
8. **Raw response shape:** DevTools JSON target list; the consumed key is `webSocketDebuggerUrl`. Reconstructed from **the parsing code** only.
9. **Failure handling:** `RuntimeError` raised on both no-version and no-page (pasted above) — **this is the only source in the repository that fails loudly and does not substitute data.**
10. **Determinism:** Non-deterministic — depends on browser startup timing and rendered page state.
11. **Landing location:** UNKNOWN in detail — I read only lines 40–75 of this file and did not open the write path. Resolved by reading `scratch/capture_traderos.py` in full.
12. **Licensing / ToS:** N/A.

---

### Source S18: Local API health endpoint — circuit-breaker probe

1. **Acquisition class:** REST API, **self-referential**. Not a pipeline data source; included because it matched the P1 sweep.
2. **Exact endpoint / URI / table / path:** `http://localhost:8000/v1/health` [`mandisense_ai/cognition/test_breaker.py:L6`].
3. **Code location:** [`mandisense_ai/cognition/test_breaker.py:L9-L22`]

```python
    for i in range(5):
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            db_status = data["services"]["db"]["status"]
            db_reachable = data["services"]["db"]["reachable"]
            print(f"Ping {i+1} | DB Status: {db_status} | Reachable: {db_reachable}")

            if db_status == "OPEN":
                print("SUCCESS: Circuit Breaker OPENED as expected.")
                break
        except Exception as e:
            print(f"Ping {i+1} | Request failed: {e}")
        time.sleep(1)
```

4. **Auth mechanism:** **none.**
5. **Request parameters:** none. 5 iterations, 5 s timeout, 1 s sleep between pings (all pasted above).
6. **Pagination & rate limiting:** N/A; the 1 s sleep is the only pacing.
7. **Volume & cadence:** 5 requests per invocation. Manual; no schedule.
8. **Raw response shape:** reconstructed from **the parsing code**: `{"services": {"db": {"status": str, "reachable": bool}}}`.
9. **Failure handling:** caught and printed; the loop continues (pasted above). No data substitution — nothing downstream consumes this.
10. **Determinism:** Non-deterministic — depends on live service state.
11. **Landing location:** stdout only; nothing is written.
12. **Licensing / ToS:** N/A.

---

## 3. STEP 3 — Real vs Synthetic Classification of the Input Layer

**Classification note on the taxonomy.** `DERIVED` is defined as "produced by this project's own code from **real** inputs". The v2/v3/v4 datasets are produced by this project's code from **synthetic** inputs (S7). Since exactly one label is required, they are classified **SYNTHETIC** — labelling them DERIVED would assert a real input that does not exist. The transformation code is named in the writer column either way.

### 3A. Classification table

| dataset / file | classification | writer (file:lines) | reader(s) (file:lines) | evidence quoted? |
|---|---|---|---|---|
| `mandisense_ai/data/raw/agmarknet_Tomato_Kolar.csv` (3597 rows) | **EXTERNAL-STALE** | none in repo — external extractor, absent (S1 field 3) | [`mandisense_ai/data/prepare_datasets.py:L23,L35-L36`]; [`mandisense_ai/evaluation/backtester.py:L32-L46`]; [`mandisense_ai/data/ingestion/agmarknet_ingestor.py:L82-L90`] via glob | Y |
| `mandisense_ai/data/raw/agmarknet_Onion_Lasalgaon.csv` (2442 rows) | **EXTERNAL-STALE** | none in repo (S1 field 3) | same three as above [`mandisense_ai/data/prepare_datasets.py:L24`] | Y |
| `mandisense_ai/data/raw/agmarknet_Potato_Agra.csv` (2899 rows) | **EXTERNAL-STALE** | none in repo (S1 field 3) | same [`mandisense_ai/data/prepare_datasets.py:L25`] | Y |
| `mandisense_ai/data/raw/agmarknet_Garlic_Neemuch.csv` (1787 rows) | **EXTERNAL-STALE** | none in repo (S1 field 3) | same [`mandisense_ai/data/prepare_datasets.py:L27`] | Y |
| `mandisense_ai/data/raw/agmarknet_Dry_Chillies_Guntur.csv` (1720 rows) | **EXTERNAL-STALE** | none in repo (S1 field 3) | same [`mandisense_ai/data/prepare_datasets.py:L26`] | Y |
| `mandisense_ai/data/raw/festival_calendar.csv` (132 rows) | **UNKNOWN-PROVENANCE** | **no writer found** (S9 field 3) | [`mandisense_ai/core/agents/seasonality_agent.py:L27-L40`], [`:L145`] | Y |
| `mandisense_ai/data/raw/v1/{tomato,onion,potato,garlic,ginger}/*.csv` (75 files) | **SYNTHETIC** | [`mandisense_ai/tasks/ingest_historical_data.py:L24-L72`] → [`:L141-L142`] | [`mandisense_ai/tasks/refine_raw_data.py:L59-L64`] (glob); [`mandisense_ai/evaluation/time_series_viz.py:L107`]; [`mandisense_ai/evaluation/regime_analysis.py:L110`]; [`mandisense_ai/evaluation/model_comparison.py:L152`]; [`mandisense_ai/evaluation/statistical_validation.py:L67`]; [`scratch/generate_regime_timeline.py:L32-L33`]; [`scratch/generate_shap_plots.py:L24-L25`]; [`scratch/generate_decision_performance.py:L17-L18`] | **Y** |
| `mandisense_ai/data/raw/v2/**/*.csv` (75 files) | **SYNTHETIC** (transform of v1) | [`mandisense_ai/tasks/refine_raw_data.py:L138-L150`] | [`mandisense_ai/tasks/finalize_raw_data.py:L49-L52`] (glob) | Y |
| `mandisense_ai/data/raw/v3/**/*.csv` (75 files) | **SYNTHETIC** (transform of v2) | [`mandisense_ai/tasks/finalize_raw_data.py:L68-L75`] | [`mandisense_ai/tasks/finalize_v4_dataset.py:L42-L44`] (glob) | Y |
| `mandisense_ai/data/processed/v4/{tomato,onion,potato,garlic,ginger}.csv` (18,255 rows for tomato) | **SYNTHETIC** (transform of v3) | [`mandisense_ai/tasks/finalize_v4_dataset.py:L79-L83`] | [`mandisense_ai/core/data/data_service.py:L67-L76`] (**the live API path**); [`mandisense_ai/core/agents/inference_engine.py:L39-L40`]; [`mandisense_ai/core/agents/inference_engine_v2.py:L43-L44`]; [`mandisense_ai/core/agents/training_pipeline.py:L11,L47`]; [`mandisense_ai/core/agents/training_pipeline_v2.py:L11,L57`]; [`mandisense_ai/core/agents/calibration_engine.py:L9,L44`]; [`scratch/generate_plot.py:L10,L17`] | **Y** |
| `mandisense_ai/data/processed/{tomato,onion,potato,garlic,dry_chillis}/X_train.csv, X_val.csv, y_train.csv, y_val.csv, price_train.csv, feature_config.json` | **DERIVED** (from EXTERNAL-STALE) | [`mandisense_ai/data/prepare_datasets.py:L122-L144`] | [`mandisense_ai/core/agents/arrival/train_arrival.py:L22-L31`]; [`mandisense_ai/core/agents/seasonality/train_seasonality.py:L27-L33`] | Y |
| `mandisense_ai/data/processed/{tomato_kolar,onion_lasalgaon,potato_agra,garlic_neemuch,dry_chillies_guntur}.parquet` + `_features.parquet` + `.metadata.json` | **DERIVED** (from EXTERNAL-STALE) | [`mandisense_ai/data/preprocessing/pipeline.py:L226`, `L243-L244`, `L248-L255`] | [`mandisense_ai/data/repository.py:L28-L46`] ← [`mandisense_ai/core/agents/seasonality_agent.py:L261`], [`mandisense_ai/core/agents/arrival_volume_agent.py:L397`], [`mandisense_ai/core/agents/seasonality/trainer.py:L21`]; also [`mandisense_ai/evaluation/error_boxplot.py:L17`], [`mandisense_ai/evaluation/error_distribution.py:L16`] | Y |
| `data/cache/weather/*.json` (10 files) + `mandisense_ai/data/cache/weather/*.json` (3 files) | **EXTERNAL-REAL** | [`.../ingestion/weather_fetcher.py:L83-L88`] | [`.../ingestion/weather_fetcher.py:L73-L80`, `L207`] | Y |
| `data/cache/news/*.json` (17 files) + `mandisense_ai/data/cache/news/*.json` (6 files) | **EXTERNAL-REAL** (but see §3B-2 — the content is generic BBC output, not agricultural news) | [`.../ingestion/news_fetcher.py:L96-L102`] | [`.../ingestion/news_fetcher.py:L82-L93`, `L208-L212`] | Y |
| `mandisense_ai/config/mandi_master.csv` (15 rows) | **SYNTHETIC** (hardcoded literal table + non-idempotent in-place mutation) | initial creation: **no writer** — `generate_mandi_master.py:L65` writes a *differently-named* file to CWD; mutation: [`mandisense_ai/tasks/refine_raw_data.py:L17-L32`] | [`mandisense_ai/tasks/ingest_historical_data.py:L21-L22`]; [`mandisense_ai/tasks/refine_raw_data.py:L18`] | **Y** |
| `mandi_master_temp.csv` (repo root, 15 rows) | **SYNTHETIC** | [`mandisense_ai/scratch/generate_mandi_master.py:L15-L41`, `L65`] | **none** — orphan, see §5A | **Y** |
| `mandisense_ai/config/mandi_metadata.csv` (15 rows) | **UNKNOWN-PROVENANCE** | **no writer found** (S10 field 3) | [`mandisense_ai/tasks/finalize_raw_data.py:L29-L30`] | Y |
| `mandisense_ai/core/agents/external_factors_agent/data/training/dataset.csv` (501 rows) | **SYNTHETIC** | [`.../ml/dataset_builder.py:L9-L52`] | [`.../ml/trainer.py:L19-L24`] | **Y** |
| `mandisense_ai/core/agents/external_factors_agent/data/predictions/feedback.csv` (10 rows) | **DERIVED** (from EFA runtime; its ml_score input is SYNTHETIC-trained) | [`.../adaptive/feedback_store.py:L6-L28`] | [`.../adaptive/feedback_store.py:L31-L35`] | Y |
| `mandisense_ai/core/agents/external_factors_agent/data/cache.json` | **DERIVED** | [`.../orchestration/cache_manager.py:L22`] and/or [`mandisense_ai/lib/cache.py:L107-L113`] | [`.../orchestration/cache_manager.py:L13-L16`]; [`mandisense_ai/lib/cache.py:L96-L99`] | Y |
| `data/ensemble/meta_predictions.jsonl` (66 lines) + `mandisense_ai/data/ensemble/meta_predictions.jsonl` (81 lines) | **DERIVED** | [`mandisense_ai/ensemble/prediction_logger.py:L33-L34,L43`]; DB-fallback path [`mandisense_ai/db/prediction_logger_db.py:L320`] | [`scratch/generate_agent_contribution.py:L27-L33`]; [`scratch/check_data_regimes.py:L6`]; [`mandisense_ai/db/migrate_jsonl_to_pg.py:L36`] | Y |
| `mandisense_ai/data/ensemble/prediction_history.jsonl` (21 lines) | **DERIVED** | [`mandisense_ai/ensemble/feedback_store.py:L42`] | [`mandisense_ai/ensemble/feedback_store.py:L42`] (same class) | Y |
| `mandisense_ai/data/deployment/audit_log.json` | **DERIVED** | [`mandisense_ai/cognition/deployment.py:L106-L109`] | [`mandisense_ai/cognition/deployment.py:L93`]; [`api/main.py:L710`] | Y |
| `mandisense_ai/logs/data_quality_report_v1.csv` | **DERIVED** (metrics over SYNTHETIC v1) | [`mandisense_ai/tasks/ingest_historical_data.py:L150-L151`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/data_quality_report_v2.csv` | **DERIVED** | [`mandisense_ai/tasks/refine_raw_data.py:L167`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/data_quality_report_v3.csv` | **DERIVED** | [`mandisense_ai/tasks/finalize_raw_data.py:L94`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/missing_day_analysis.csv` | **DERIVED** | [`mandisense_ai/tasks/refine_raw_data.py:L172`] | [`mandisense_ai/tasks/finalize_raw_data.py:L9,L33`] | Y |
| `mandisense_ai/logs/removed_pairs_log.csv` | **DERIVED** | [`mandisense_ai/tasks/refine_raw_data.py:L168`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/final_dataset_report.csv` | **DERIVED** | [`mandisense_ai/tasks/finalize_v4_dataset.py:L100`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/agent_training_report.csv` | **DERIVED** | [`mandisense_ai/core/agents/training_pipeline.py:L151`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/per_mandi_metrics_v2.csv`, `error_analysis_v2.csv` | **DERIVED** | [`mandisense_ai/core/agents/training_pipeline_v2.py:L180-L181`] | **none** — orphan, §5A | Y |
| `mandisense_ai/logs/model_drift_monitor.csv` | **DERIVED** | [`mandisense_ai/core/agents/calibration_engine.py:L119`] | **none** — orphan, §5A | Y |
| `mandisense_ai/models/{tomato,onion,potato,garlic,ginger}/v2/`, `/v3/` (model.pkl, arrival_model.pkl, mandi_encoder.pkl, feature_columns.json, calibrated_confidence_map.json, per_mandi_metrics.csv, directional_accuracy.csv, metrics_summary.json) | **SYNTHETIC** (trained on SYNTHETIC v4) | [`mandisense_ai/core/agents/training_pipeline_v2.py:L11,L57,L175-L176`]; [`mandisense_ai/core/agents/calibration_engine.py:L9,L44,L108,L115-L116`] | [`mandisense_ai/core/agents/inference_engine_v3.py:L44-L52`] (**the live API path**) | Y |
| `mandisense_ai/models/arrival/*/`, `mandisense_ai/models/seasonality/*/` | **DERIVED** (trained on EXTERNAL-STALE via `processed/{commodity}/`) | [`mandisense_ai/core/agents/arrival/train_arrival.py:L16-L28`]; [`mandisense_ai/core/agents/seasonality/train_seasonality.py:L27-L33`] | UNKNOWN — I did not trace the loader for these two model trees. Resolved by reading `arrival_volume_agent.py` and `seasonality_agent.py` model-load paths in full. | Y |
| PostgreSQL `market_prices` table | **UNKNOWN-PROVENANCE** | **no writer executes** — `UPSERT_MARKET_PRICE` [`mandisense_ai/db/queries.py:L131-L141`] is never called; `queries.py` has no live importer | **no reader executes** — `PRICE_RANGE` [`:L143-L151`], `COMPUTE_7D_CHANGE` [`:L153-L171`] likewise | **Y** |
| PostgreSQL `arrival_volumes` table | **UNKNOWN-PROVENANCE** | **no writer, no query at all** — the table appears only in DDL [`mandisense_ai/db/schema.sql:L107-L116`], a required-table set [`scripts/init_db.py:L20`], and a startup check [`api/main.py:L314`] | none | **Y** |
| PostgreSQL `prediction_log` table | **DERIVED** | [`mandisense_ai/db/prediction_logger_db.py:L99`]; [`mandisense_ai/db/client.py:L185`] | [`mandisense_ai/db/prediction_logger_db.py:L201,L234,L280`]; [`mandisense_ai/api/routes/history.py:L32`] | Y |
| 6×6 spillover matrix (in-memory, → `imag/figure_5_5*.png`) | **SYNTHETIC** | [`scratch/generate_cross_commodity_suite.py:L21-L32`] | same file, L52-L192 | **Y** |
| Latency distributions (in-memory, → `imag/figure_5_9*.png`) | **SYNTHETIC** | [`scratch/generate_system_latency.py:L15-L32`] | same file, L35-L193 | **Y** |
| SHAP external/cross-commodity features (in-memory, → `imag/figure_5_6*.png`) | **SYNTHETIC** | [`scratch/generate_shap_plots.py:L63-L70`] | same file, L82-L219 | **Y** |
| Decision-engine `predicted_class` / `simulated_confidence` (in-memory, → `imag/figure_5_7*.png`) | **SYNTHETIC** | [`scratch/generate_decision_performance.py:L51-L70`] | same file, L82-L206 | **Y** |
| Agent-contribution regime samples (in-memory, → `imag/figure_5_3*.png`) | **SYNTHETIC** (60 fabricated samples back-filled into 3 of 4 regimes) | [`scratch/generate_agent_contribution.py:L101-L159`] | same file, L161-L320 | **Y** |
| `MarketRegistry.MANDI_COORDS` (in-memory) | **SYNTHETIC** (hardcoded) | [`mandisense_ai/cognition/world_model/topology.py:L21-L37`] | [`.../processing/weather_signal.py:L67`] | **Y** |
| `FALLBACK_DATA` news corpus (in-memory) | **SYNTHETIC** (hardcoded) | [`.../ingestion/news_ingestor.py:L9-L18`] | [`.../ingestion/news_ingestor.py:L61`] | **Y** |
| `fallback_data()` mandi snapshot (in-memory) | **SYNTHETIC** (hardcoded) | [`mandisense_ai/services/mandi_data_service.py:L64-L77`] | [`mandisense_ai/services/mandi_data_service.py:L83,L115,L121,L126`] | **Y** |

### 3B. Findings that follow from the table

**1. The application serves synthetic data. The real data is never served.**
Two disjoint pipelines exist and they never meet:

```
S1 (real, 12,445 rows, 2015-2025)
    -> mandisense_ai/data/raw/agmarknet_*.csv
    -> prepare_datasets.py           -> data/processed/{commodity}/X_train.csv ...
    -> preprocessing/pipeline.py     -> data/processed/{commodity}_{market}.parquet
                                      (repository.py -> seasonality_agent, arrival_volume_agent)

S7 (synthetic, np.random, 2023-01-01 -> datetime.now())
    -> data/raw/v1/ -> v2/ -> v3/ -> data/processed/v4/{commodity}.csv
    -> core/data/data_service.py     -> inference_engine_v3 -> the FastAPI response
    -> training_pipeline_v2.py       -> models/{commodity}/v3/*.pkl
```

The live request path is the second one. [`mandisense_ai/core/data/data_service.py:L11-L12`] pins it:

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_V4_DIR = PROJECT_ROOT / "mandisense_ai" / "data" / "processed" / "v4"
```

and the load is a plain local CSV read [`mandisense_ai/core/data/data_service.py:L67-L76`]:

```python
                data_path = DATA_V4_DIR / f"{commodity}.csv"
                if not data_path.exists():
                    return
                    
                # STEP 9: TIMEOUT PROTECTION (Simulated)
                loop = asyncio.get_event_loop()
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, pd.read_csv, data_path),
                    timeout=5.0
                )
```

This is reached from the API through [`mandisense_ai/core/agents/inference_engine_v3.py:L64-L65`] and [`backend/app/services/model_loader.py:L19,L26`]. Note that a successful read of this local file increments a counter named `external_fetches` [`mandisense_ai/core/data/data_service.py:L102`] — the metric reported at [`backend/app/main.py:L84`] names a network fetch that never happens.

**2. The only dataset committed to version control is the synthetic one.**

```
$ git ls-files mandisense_ai/data/processed/
mandisense_ai/data/processed/v4/garlic.csv
mandisense_ai/data/processed/v4/ginger.csv
mandisense_ai/data/processed/v4/onion.csv
mandisense_ai/data/processed/v4/potato.csv
mandisense_ai/data/processed/v4/tomato.csv
```

Those five files are the entire tracked dataset. The real Agmarknet CSVs and every derived parquet are git-ignored — the nested rule [`mandisense_ai/.gitignore:L43,L45`] reads `data/raw/*` and `data/processed/*`. The root `.gitignore` carries an explicit carve-out to keep v4 and nothing else [`.gitignore:L45-L50`]:

```
mandisense_ai/data/raw/*
!mandisense_ai/data/raw/.gitkeep
mandisense_ai/data/processed/*
!mandisense_ai/data/processed/.gitkeep
!mandisense_ai/data/processed/v4/
!mandisense_ai/data/processed/v4/*
```

A clone of this repository therefore contains **synthetic price data and nothing else**. Confirmed by a commit message in the log: `0f0adb4 Include v4 processed dataset CSVs in build context to resolve missing inference data`.

**3. Correction to the prior audit (PHASE_7_EDA_VIZ.md).** That document assessed Chart 10 as sound: *"This chart uses **real APMC data** (`kolar.csv`), real EGARCH fitting, and real HMM classification"*, and called `regime_analysis.py` *"real raw data ... the most rigorous of the evaluation modules"*. **Both statements are wrong.** The file those modules read is [`scratch/generate_regime_timeline.py:L32`] and [`mandisense_ai/evaluation/regime_analysis.py:L110`]:

```python
data_path = 'mandisense_ai/data/raw/v1/tomato/kolar.csv'
```

`mandisense_ai/data/raw/v1/tomato/kolar.csv` is the **output of the `np.random` generator at [`mandisense_ai/tasks/ingest_historical_data.py:L24-L72`]**, not APMC data. Proof by schema and value comparison — the real file and the v1 file share no price series and only two column names:

```
real  mandisense_ai/data/raw/agmarknet_Tomato_Kolar.csv
      date,commodity,market,state,arrivals_tonnes,modal_price,min_price,max_price,source_url,scrape_timestamp
      2015-01-06,Tomato,Kolar,Karnataka,5008.0,933.0,466.0,1533.0,https://api.agmarknet.gov.in/...,2026-03-10 09:30:05

v1    mandisense_ai/data/raw/v1/tomato/kolar.csv
      date,mandi_name,commodity,modal_price,arrivals,mandi_id
      2023-01-01,Kolar,tomato,1757.76,63.61,kolar
```

The same misattribution applies to the four other Phase-7 conclusions resting on this path: `time_series_viz.py:L107`, `model_comparison.py:L152`, `statistical_validation.py:L67`, `generate_shap_plots.py:L24`. **The EGARCH fit, the HMM regimes, the SHAP rankings and the ARIMA/RF/XGBoost benchmark in `README.md:L407-L413` are all computed over a sine wave plus Gaussian noise.**

**4. The `EXTERNAL-REAL` label on the news cache is technically correct and practically misleading.** The bytes did come from NewsAPI. But the query that produced them degrades to the literal string `"bbc"` whenever a commodity query returns nothing [`.../news_fetcher.py:L237-L252`], and the committed caches show that is what happened — sampled titles include `"the news quiz: ep4. the people have spoken"`, `"bbc inside science"`, `"football daily"`. 11 of the 17 root cache files hold **zero** articles. The signal reaching the ensemble is real BBC text about non-agricultural subjects.

**5. `policy` carries 35 % of the external impact score and has no source at all.** [`.../processing/external_fusion.py:L17-L21`]:

```python
WEIGHTS = {
    "weather": 0.4,
    "policy": 0.35,
    "news": 0.25,
}
```

The value fed into that weight is a hardcoded zero [`.../external_factors_agent/__init__.py:L33-L34`]:

```python
        policy_signal = 0.0
        policy_confidence = 0.0
```

No policy source exists anywhere in the repository — `rg` over the whole `external_factors_agent` tree finds no fetcher, file, or table for it. This contradicts `README.md:L135`, which claims the agent "Monitors news feeds, meteorological updates, and **government bulletins**".

---

## 4. STEP 4 — Provenance Summary Table

| source | acquisition class | auth | cadence | volume | landing location |
|---|---|---|---|---|---|
| **S1** Agmarknet daily price/arrival report (historical bulk) | REST API, **executed outside this repo** (manual/absent extractor) | UNKNOWN — no auth parameter in the recorded `source_url` | one-shot, 2026-03-10; **no scheduler** | 12,445 rows across 5 files; 195 request windows | `mandisense_ai/data/raw/agmarknet_*.csv` (git-ignored) |
| **S2** Agmarknet `PriceTrend.aspx` client | REST API — **[DEAD?]** and structurally broken (HTML endpoint, JSON/CSV parsers only) | none | on-demand; 1 call / 15 s limiter; **no scheduler, no caller** | 0 in practice | Redis key `mandi_snapshot:{commodity}`, else `mandisense_ai/data/cache.json` |
| **S3** Open-Meteo archive API | REST API | none (open endpoint) | on-demand, trailing 30-day window ending "today"; **no scheduler** | 720 hourly rows → 30 daily rows per call | `data/cache/weather/<sha256>.json` |
| **S4** NewsAPI.org `/v2/everything` (`sources=bbc-news`) | REST API | **API key `NEWS_API_KEY`** as a URL query param; **placeholder value only in `.env`; absent from `render.yaml`** | on-demand, trailing 2 days; 3600 s cache TTL; **no scheduler** | 0–100 articles/call (single page, no pagination); observed 0–54 | `data/cache/news/<sha256>.json` |
| **S5** PostgreSQL `mandisense` | Direct DB query (psycopg2 + asyncpg) | **connection string `DATABASE_URL`**; dev fallback is the **hardcoded literal** `postgresql://user:pass@localhost:5432/mandisense` | on-demand; **no scheduler** | `market_prices` / `arrival_volumes`: **0 rows, no writer exists**; `prediction_log`: written per prediction | N/A (sink); JSONL fallback `data/ensemble/meta_predictions.jsonl` |
| **S6** Redis | SDK/client library | **connection string `REDIS_URL`**, or `REDIS_HOST`/`PORT`/`DB`/`PASSWORD` | TTL-driven, clamped to 1800–3600 s | 1 document per commodity; **never populated in practice** (S2 is dead) | Redis key-space, else `mandisense_ai/data/cache.json` |
| **S7** `generate_historical_data()` | **SYNTHETIC / GENERATED-IN-CODE** | none | manual `__main__` run; **no scheduler** | 75 files; 1140 rows per file (tomato/kolar); range 2023-01-01 → `datetime.now()` | `mandisense_ai/data/raw/v1/{commodity}/{mandi_id}.csv` |
| **S8** `generate_mandi_master.py` | **SYNTHETIC / GENERATED-IN-CODE** (hardcoded 25-row literal) | none | one-shot | 15 rows (nearest 15 of 25 by haversine) | `./mandi_master_temp.csv` (CWD) — then a **hidden manual copy** to `mandisense_ai/config/mandi_master.csv` |
| **S9** `festival_calendar.csv` | Flat file, **no writer in repo** — manual authorship or download | none | static | 132 rows, 2015-01-01 → 2025-12-25 | `mandisense_ai/data/raw/festival_calendar.csv` (git-ignored) |
| **S10** `mandi_metadata.csv` | Flat file, **no writer in repo** — manual authorship | none | static | 15 rows | `mandisense_ai/config/mandi_metadata.csv` (tracked) |
| **S11** `build_dataset()` (EFA ML) | **SYNTHETIC / GENERATED-IN-CODE** | none | regenerated on every `train_model()` call; **no scheduler** | 501 rows (100 × 5 commodities + 1 deliberate bad row) | `data/training/dataset.csv` (CWD-relative) |
| **S12** `FALLBACK_DATA` news corpus | **SYNTHETIC / GENERATED-IN-CODE** (hardcoded) | none | returned on every news-fetch failure — the default for a fresh checkout | 8 records, fixed | in-memory only; **not** written to the news cache |
| **S13** `fallback_data()` mandi snapshot | **SYNTHETIC / GENERATED-IN-CODE** (hardcoded) | none | returned on 4 code paths incl. unconditional init | 1 record (`price=10000.0`, `arrival=50.0`, `lat/lon=0.0`) | in-memory only; **not** cached |
| **S14** `MarketRegistry.MANDI_COORDS` | **SYNTHETIC / GENERATED-IN-CODE** (hardcoded) | none | static | 7 coordinate pairs + 5 district aliases, against 15 mandis in the master | in-memory only |
| **S15** Cross-commodity spillover matrix | **SYNTHETIC / GENERATED-IN-CODE** (hardcoded matrix, labelled "Granger causality / VAR") | none | on-demand figure regeneration | one 6×6 matrix | `imag/figure_5_5*.png`, `imag/dependency_network.png` |
| **S16** System-latency distributions | **SYNTHETIC / GENERATED-IN-CODE** (`np.random.normal`, banner says "ACTUAL LOG METRICS") | none | on-demand figure regeneration | 5000 draws (2500+1200+800+500) | `imag/figure_5_9*.png` |
| **S17** Chrome DevTools Protocol (localhost) | REST API + WebSocket, **self-referential** | none (loopback) | manual | 1 screenshot/run | UNKNOWN — write path not read |
| **S18** Local `/v1/health` probe | REST API, **self-referential** | none | manual; 5 pings × 1 s | 5 responses | stdout only |

---

## 5. STEP 5 — Orphan Check

### 5A. Data files present that no code reads

Each filename was searched literally across `.py`, `.sql`, `.yaml`, `.md`, `.sh` (and `.ipynb` — the repository contains **zero** notebooks, verified by `find . -name "*.ipynb"` returning 0 outside `ms_env/`) before being listed here. Glob-based reads count as reads, so files reached via `V1_DIR.glob("*.csv")` and similar are **not** listed.

| # | Orphan file | Written by | Search that proves no reader |
|---|---|---|---|
| 1 | `mandi_master_temp.csv` (repo root, 15 rows) | [`mandisense_ai/scratch/generate_mandi_master.py:L65`] | `grep -rn "mandi_master_temp" --include=*.py --include=*.md --include=*.yaml --include=*.sh --include=*.sql .` → 4 hits, all of them the **write** call in `generate_mandi_master.py:L65,L67` and its duplicate under `build/lib/`. Plus one prose mention in `MANDISENSE_PHASE1_DEPLOYMENT_READINESS_AUDIT.txt`. **No read.** |
| 2 | `mandisense_ai/logs/data_quality_report_v1.csv` | [`mandisense_ai/tasks/ingest_historical_data.py:L150-L151`] (via f-string `data_quality_report_{VERSION}.csv`) | `rg 'data_quality_report'` over `*.py` → 3 hits, all `to_csv` writes. **No reader.** |
| 3 | `mandisense_ai/logs/data_quality_report_v2.csv` | [`mandisense_ai/tasks/refine_raw_data.py:L167`] | same search; the only occurrence is the write. |
| 4 | `mandisense_ai/logs/data_quality_report_v3.csv` | [`mandisense_ai/tasks/finalize_raw_data.py:L94`] | same search; the only occurrence is the write. |
| 5 | `mandisense_ai/logs/removed_pairs_log.csv` | [`mandisense_ai/tasks/refine_raw_data.py:L168`] | `rg 'removed_pairs_log'` → 1 hit, the write. |
| 6 | `mandisense_ai/logs/final_dataset_report.csv` | [`mandisense_ai/tasks/finalize_v4_dataset.py:L100`] | `rg 'final_dataset_report'` → 1 hit, the write. |
| 7 | `mandisense_ai/logs/agent_training_report.csv` | [`mandisense_ai/core/agents/training_pipeline.py:L151`] | `rg 'agent_training_report'` → 1 hit, the write. |
| 8 | `mandisense_ai/logs/per_mandi_metrics_v2.csv` | [`mandisense_ai/core/agents/training_pipeline_v2.py:L180`] | `rg 'per_mandi_metrics_v2'` → 1 hit, the write. (Note: the *unversioned* `per_mandi_metrics.csv` under `models/{commodity}/v3/` **is** read, at [`mandisense_ai/core/agents/inference_engine_v3.py:L50`] — a different file.) |
| 9 | `mandisense_ai/logs/error_analysis_v2.csv` | [`mandisense_ai/core/agents/training_pipeline_v2.py:L181`] | `rg 'error_analysis_v2'` → 1 hit, the write. |
| 10 | `mandisense_ai/logs/model_drift_monitor.csv` | [`mandisense_ai/core/agents/calibration_engine.py:L119`] | `rg 'model_drift_monitor'` → 1 hit, the write. |
| 11 | `mandisense_ai/data/ensemble/prediction_history.jsonl` (21 lines) | [`mandisense_ai/ensemble/feedback_store.py:L42`] | The only class touching this path both writes and reads it; **no external consumer**. `api/routes/history.py:L32` and `db/client.py:L235` share the *name* `get_prediction_history` but read `prediction_log` in PostgreSQL, not this file. Effectively orphaned. |
| 12 | `mandisense_ai/data/cache/news/*.json` (6 files), `mandisense_ai/data/cache/weather/*.json` (3 files) | [`.../news_fetcher.py:L96-L102`], [`.../weather_fetcher.py:L83-L88`] with CWD = `mandisense_ai/` | Unreachable at the documented CWD. `DEFAULT_CACHE_DIR` is `Path("data/cache/news")` [`.../news_fetcher.py:L32`] — CWD-relative. Run from the repo root (as `Dockerfile`/`docker-compose.yml` do), only `data/cache/` is consulted. This duplicate set is dead unless the process CWD is `mandisense_ai/`. |
| 13 | `mandisense_ai/data/raw/v2/**/*.csv` (75 files) | [`mandisense_ai/tasks/refine_raw_data.py:L150`] | Read only by [`mandisense_ai/tasks/finalize_raw_data.py:L49`] via glob — a **build-time intermediate**, never read at runtime. Listed for completeness, not as a defect. |
| 14 | `mandisense_ai/data/processed/*_features.parquet` (5 files) | [`mandisense_ai/data/preprocessing/pipeline.py:L248-L255`] | **Read** by [`mandisense_ai/data/repository.py:L28-L33`] (`candidate_names[0]`). **Not an orphan** — listed here only to record that I checked it, because the file is described in-source as a "Compatibility artifact for older agents/scripts" [`pipeline.py:L246-L247`]. |

**Rows 13 and 14 are not defects**; they are recorded so the ledger is complete. The genuine orphans are rows 1–12 — **eleven write-only report files and one shadow cache tree**.

### 5B. Read calls pointing at paths nothing writes, and that do not exist on disk

These are hidden manual steps or broken paths.

| # | Read call | Path | On disk? | Written by anything? |
|---|---|---|---|---|
| 1 | [`mandisense_ai/tasks/backfill.py:L104-L111`] | `data/processed/{commodity}_{mandi}_prices.csv` | **NO** — `find . -name "*_prices.csv"` returns nothing | **NO** — no `to_csv` in the repository produces a `_prices.csv` name |
| 2 | [`.../ml/trainer.py:L19-L24`] | `data/training/dataset.csv` (CWD-relative) | **NO** at the repo root — `ls data/training/` → *No such file or directory*. The file exists only at `mandisense_ai/core/agents/external_factors_agent/data/training/dataset.csv` | Yes, but only when CWD = the agent package [`.../ml/dataset_builder.py:L10-L11`] |
| 3 | [`.../adaptive/feedback_store.py:L31-L35`] | `data/predictions/feedback.csv` (CWD-relative) | **NO** at the repo root. Exists only at `mandisense_ai/core/agents/external_factors_agent/data/predictions/feedback.csv` | Yes, but only at that CWD [`.../adaptive/feedback_store.py:L4,L7`] |
| 4 | [`mandisense_ai/tasks/ingest_historical_data.py:L21-L22`] | `mandisense_ai/config/mandi_master.csv` | Yes | **Initial creation: NO.** The only writer mutates a pre-existing file [`mandisense_ai/tasks/refine_raw_data.py:L30`]. Its content originates from `mandi_master_temp.csv` (orphan 5A-1) by a **manual copy and rename**. |
| 5 | [`mandisense_ai/tasks/finalize_raw_data.py:L29-L30`] | `mandisense_ai/config/mandi_metadata.csv` | Yes | **NO writer anywhere.** Hand-authored. |
| 6 | [`mandisense_ai/data/ingestion/agmarknet_ingestor.py:L82`] and the whole `preprocessing/pipeline.py` chain | `mandisense_ai/data/raw/*.csv` (glob) | Yes | **NO writer anywhere** — this is S1, the absent extractor. |
| 7 | [`mandisense_ai/core/agents/seasonality_agent.py:L27`] | `mandisense_ai/data/raw/festival_calendar.csv` | Yes | **NO writer anywhere.** |
| 8 | [`mandisense_ai/evaluation/regime_analysis.py:L110`], [`time_series_viz.py:L107`], [`model_comparison.py:L152`], [`statistical_validation.py:L67`], [`scratch/generate_regime_timeline.py:L32`], [`scratch/generate_shap_plots.py:L24`], [`scratch/generate_decision_performance.py:L17`] | `mandisense_ai/data/raw/v1/tomato/kolar.csv` | Yes | **Yes, but the writer can no longer produce this filename.** [`mandisense_ai/tasks/ingest_historical_data.py:L141`] writes `f"{mandi_id}.csv"` where `mandi_id` comes from `mandi_master.csv`. That column has already been mutated in place to `kolar_apmc` [`mandisense_ai/tasks/refine_raw_data.py:L27,L30`]. **Re-running the generator today writes `v1/tomato/kolar_apmc.csv`, and all seven readers break.** |
| 9 | [`mandisense_ai/tests/verify_database.py:L144`] | module `db.queries` | N/A | Import path is broken — the package is `mandisense_ai.db`. Confirms `queries.py` has no live importer (§S5 field 7). |
| 10 | [`.../orchestration/pipeline_runner.py:L9-L30`] | modules `orchestration.*`, `ingestion.*`, `processing.*`, `scoring.*`, `ml.*`, `causal.*`, `adaptive.*`, `explainability.*` | N/A | **Unimportable.** Verified by execution: `python -c "import mandisense_ai.core.agents.external_factors_agent.orchestration.pipeline_runner"` → `ModuleNotFoundError: No module named 'orchestration'`. **[DEAD?] — the entire External Factors batch pipeline cannot be loaded.** |

---

## 6. STEP 6 — Reproducibility Verdict

### **NO.**

A new person cannot reproduce the raw data layer from this repository. Not "with difficulty" — the two highest-value datasets have no acquisition code at all, and the dataset that *is* reproducible in principle is not reproducible in fact because its seed is process-salted.

Blockers, one line each:

1. **Absent fetch code for the entire real dataset.** `mandisense_ai/data/raw/agmarknet_*.csv` (12,445 rows) has no writer, no fetcher, and no history — `rg 'api\.agmarknet|daily-price-arrival|source_url'` over non-CSV files returns nothing, and `git log --all --name-only` has never contained a scraper file [S1 field 3].
2. **The real dataset is not in version control.** `git check-ignore -v mandisense_ai/data/raw/agmarknet_Tomato_Kolar.csv` → `mandisense_ai/.gitignore:43:data/raw/*`; a clone gets nothing [§3B-2].
3. **Undocumented file with no writer — `festival_calendar.csv`.** 132 rows consumed by the Seasonality Agent at [`mandisense_ai/core/agents/seasonality_agent.py:L27`], git-ignored, and produced by nothing [S9 field 3].
4. **Undocumented file with no writer — `mandi_metadata.csv`.** 15 hand-authored reliability weights read at [`mandisense_ai/tasks/finalize_raw_data.py:L29`], with no stated derivation [S10 field 12].
5. **Hidden manual step — `mandi_master_temp.csv` → `config/mandi_master.csv`.** The generator writes to CWD under a different name [`mandisense_ai/scratch/generate_mandi_master.py:L65`]; no code performs the copy [§5B-4].
6. **Unseeded randomness in the dataset the application actually serves.** `np.random.seed(hash(mandi_id + commodity) % 1234)` [`mandisense_ai/tasks/ingest_historical_data.py:L29`] derives its seed from a process-salted string hash; `PYTHONHASHSEED` is set in none of `.env.example`, `render.yaml`, `Dockerfile`, `docker-compose.yml`.
7. **Clock-dependent generation.** `end_date = datetime.now()` [`mandisense_ai/tasks/ingest_historical_data.py:L32`] — the v1 series length changes daily; the committed v1 ends 2026-05-03.
8. **Non-idempotent config mutation breaks the second run.** `refine_mandi_master()` appends `_apmc` to an already-suffixed ID [`mandisense_ai/tasks/refine_raw_data.py:L20-L30`], producing `kolar_apmc_apmc` and an ID map that matches nothing.
9. **Regenerating v1 renames every file its readers reference.** `save_path = comm_dir / f"{mandi_id}.csv"` [`mandisense_ai/tasks/ingest_historical_data.py:L141`] now yields `kolar_apmc.csv`, orphaning seven hardcoded readers of `v1/tomato/kolar.csv` [§5B-8].
10. **Missing credential — `NEWS_API_KEY`.** `.env` is byte-identical to `.env.example` and holds the placeholder `your_news_api_key_here` [`.env.example:L21`]; the fetcher rejects it and falls back to fabricated headlines [`.../news_fetcher.py:L217-L218`].
11. **`NEWS_API_KEY` is absent from the deployment manifest.** `render.yaml:L9-L20` declares only `APP__ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL` — a production deploy can never fetch news.
12. **Missing credential — `DATABASE_URL`.** Defaults to the hardcoded literal `postgresql://user:pass@localhost:5432/mandisense` outside production [`mandisense_ai/db/connection.py:L36`], which will not connect anywhere.
13. **Missing credential — `REDIS_URL`.** Defaults to unauthenticated `localhost:6379` [`mandisense_ai/lib/cache.py:L41-L49`]; absence is silent [`mandisense_ai/lib/cache.py:L55-L58`].
14. **Dead/unreachable URL — `agmarknet.gov.in/PriceTrend.aspx`.** An ASP.NET HTML page consumed by a client that implements only JSON and CSV parsers [`mandisense_ai/lib/agmarknet_client.py:L12` vs `L50-L85`]; it cannot succeed even if reachable.
15. **Unreachable module — the External Factors batch pipeline.** `pipeline_runner.py` fails to import (`ModuleNotFoundError: No module named 'orchestration'`), verified by execution [§5B-10].
16. **Absent scheduler.** No cron, Celery beat, or APScheduler exists (P6 = 0 hits; `render.yaml:L1-L31` declares no worker) — nothing refreshes any source, so even a working fetch would run only when a human invokes it.
17. **Two database tables that nothing populates.** `market_prices` and `arrival_volumes` have DDL, indexes, and a startup existence check [`api/main.py:L314`], but no code path ever inserts a row [§S5 field 7]; outcome backfill is a `TODO` [`mandisense_ai/tasks/backfill.py:L95-L98`].
18. **Broken read path — `data/processed/{commodity}_{mandi}_prices.csv`.** Read at [`mandisense_ai/tasks/backfill.py:L107`]; no such file exists and nothing writes one; failure is swallowed by a bare `except Exception: return None` [`mandisense_ai/tasks/backfill.py:L130-L131`].
19. **CWD-dependent data paths.** `data/cache/{news,weather}`, `data/training`, `data/predictions`, and `data/ensemble` are all CWD-relative, and the on-disk duplicates prove the code has been run from at least two different directories; no entry point pins the CWD [§5A-12, §5B-2, §5B-3].
20. **Missing runtime dependency for the derived layer.** `pyarrow` is not installed in the environment that ships with this checkout — `pd.read_parquet('mandisense_ai/data/processed/tomato_kolar.parquet')` raises `ImportError: Missing optional dependency 'pyarrow'`, so every `DataRepository` read [`mandisense_ai/data/repository.py:L46`] fails as configured.

**What *is* reproducible:** the synthetic EFA training set (S11 — `random.seed(42)`, a stable literal seed), the mandi master arithmetic (S8 — pure haversine over a literal list), the hardcoded spillover matrix (S15), and the latency distributions (S16 — `np.random.seed(42)`). All four are fabricated.

---

## 7. README vs Code — Contradictions (R5)

Where the README describes acquisition behaviour that the code does not implement, both are reported and the README is marked **WRONG**.

| # | README claim | Code reality | Verdict |
|---|---|---|---|
| 1 | *"Entity & Category Scraper"* as a pipeline stage [`README.md:L110`] | **No scraping library is imported anywhere.** P8 sweep (`BeautifulSoup\|selenium\|playwright\|scrapy\|lxml\|feedparser`) = **0 matches** across the whole repository. | **README WRONG** |
| 2 | *"Monitors news feeds, meteorological updates, and **government bulletins** to compute real-time price impact scores"* [`README.md:L135`] | News: real (S4). Weather: real (S3). **Government bulletins: no source exists.** `policy_signal = 0.0` is hardcoded [`.../external_factors_agent/__init__.py:L33-L34`] while carrying 35 % of the fusion weight [`.../processing/external_fusion.py:L17-L21`]. | **README WRONG on one of three inputs** |
| 3 | *"Inputs: Unstructured text articles, weather indices, import/export announcements"* [`README.md:L136`] | No import/export announcement source exists — same evidence as row 2. | **README WRONG** |
| 4 | *"A[APMC Structured Price & Volume]"* as the ingestion input [`README.md:L34`] | The **live API path reads `data/processed/v4/*.csv`**, which is `np.random` output (S7, §3B-1). Real APMC data exists on disk but never reaches a request. | **README MISLEADING** — true of the dormant pipeline, false of the running one |
| 5 | *"Model Benchmarking Metrics (Kolar Tomato Dataset)"* with ARIMA/RF/XGBoost/MandiSense MAPE figures [`README.md:L407-L413`] | Produced by [`mandisense_ai/evaluation/model_comparison.py:L152`], which reads `mandisense_ai/data/raw/v1/tomato/kolar.csv` — **synthetic** (§3B-3). The "Kolar Tomato Dataset" is a sine wave plus Gaussian noise. | **README WRONG** |
| 6 | *"Evaluated across synthetic and actual highly-volatile market regimes"* [`README.md:L414`] | The word "synthetic" appears, but the sentence implies a mix. **No actual market data participates in that benchmark** — the single input path is the v1 synthetic file. | **README WRONG** |
| 7 | *"designed specifically to handle messy, incomplete, and delayed data from sources like Agmarknet"* [`mandisense_ai/README.md:L6`] | `AgmarknetIngestor` does implement column normalisation and coercion [`mandisense_ai/data/ingestion/agmarknet_ingestor.py:L20-L72`], and it does run over the real CSVs. This claim is **supported**. | **Accurate** |
| 8 | In-source, not README: `# --- DATA GENERATION BASED ON ACTUAL LOG METRICS ---` [`scratch/generate_system_latency.py:L15`] | The script opens no log file; the five following lines are `np.random.normal` calls with literal parameters (S16 field 3). | **COMMENT WRONG** |
| 9 | In-source, not README: `# Normalized spillover matrix (Granger causality / VAR variance decomposition strengths)` [`scratch/generate_cross_commodity_suite.py:L19`] | No Granger test and no VAR estimation exists in the repository; the 36 values are literals (S15 field 3). | **COMMENT WRONG** |
| 10 | In-source: `"""Simulates a high-quality historical fetch... In a real production environment, this would call AgmarknetClient."""` [`mandisense_ai/tasks/ingest_historical_data.py:L25-L28`] | **This docstring is accurate and is the clearest disclosure in the repository.** It is contradicted by nothing; it is simply not surfaced in the README, and its output is what the API serves. | **Accurate but buried** |

---

## 8. FINAL SELF-CHECK

### 8a. Citation coverage

Counted **mechanically**, not estimated. A *claim unit* is one numbered dossier field (its prose, its pasted code, and any evidence sub-table folded in) or one data row of a top-level table. Header and separator rows are excluded. The script that produced these numbers is reproduced below the table.

| Measure | Count | % of total |
|---|---:|---:|
| **Total claim units** | **383** | 100 % |
| Units carrying an inline `[`path:Lx-Ly`]` citation | **195** | **50.9 %** |
| Units with no bracketed citation | 188 | 49.1 % |

Raw citation instances (a unit may carry several): **357** bracketed citations across **98 distinct files**.

The 188 uncited units break down as follows. Every category is a case where no line number exists to cite:

| Category of uncited unit | Count | Why no citation exists |
|---|---:|---|
| `N/A` or `none` dossier fields | 47 | Fields such as *"4. Auth mechanism: **none** — no network call"* for an in-code generator, or *"6. Pagination: N/A"*. There is no line that says "none". |
| Process meta-claims (§8b, §8c) | 35 | Statements about **my own coverage**, not about the codebase. R1 governs claims about the code. |
| Cross-referenced dossier fields | 63 | Fields whose evidence is pasted in a **sibling field of the same dossier** and referenced as *"see field 3"*, *"pasted above"*, *"pasted in field 3"* — 33 such cross-references. Also includes the seven `1. Acquisition class` fields, which are classifications justified by the cited `3. Code location` immediately below them. |
| Explicit `UNKNOWN` per R3 | 15 | Enumerated individually in §8c. |
| Proofs-of-absence | 9 | Negative findings where the **search command is pasted instead of a line number** — P6/P7/P8 zero-hits, the `api.agmarknet` grep, the `git log` scraper search, the `*_prices.csv` find, the `market_prices` writer search, the `pipeline_runner` import failure. |
| Search-sweep rows (§1) | 6 | The sweep table's evidence **is** the pattern and its count, as Step 1 specified. |
| §4 summary rows | 13 | Restatements of dossier facts already cited in §2; §4's schema has no citation column. |

**Correction:** an earlier draft of this section reported 341 claims / 309 cited / 90.6 %. Those figures were an estimate, and they were wrong. The numbers above are the output of the counting script and supersede them.

Counting script:

```python
FIELD = re.compile(r'^\d+\.\s+\*\*')          # a numbered dossier field starts a unit
HEAD  = re.compile(r'^#{2,4}\s')              # headings close the open unit
SEP   = re.compile(r'^\|[\s\-:|]+\|$')        # table separators are not units
CIT   = re.compile(r'\[`[^`]*:L\d')           # the R1 citation form
# inside a "### Source Sn" block, table rows fold into the open field (they are its evidence);
# outside one, each table row is its own unit. Fenced code folds into the open unit.
```

**No unit in this document asserts a positive fact about the codebase without either a bracketed line citation, a pasted search proving absence, or an explicit `UNKNOWN`.** The 50.9 % figure is low because roughly a quarter of all units are `N/A`/`none` fields and process meta-claims that R7 required me to emit rather than omit.

### 8b. Ledger coverage

`docs/reveng/PHASE_0_MAP.md` did not exist (§0), so I authored it. It carries **93 numbered rows**; 8 preprocessing-stage files are marked `OUT-OF-SCOPE-P1` (Phase 2), leaving **85 files assigned to Phase 1**. Counted mechanically over the ledger's numbered rows.

| Measure | Count |
|---|---:|
| Files assigned to Phase 1 in the ledger | **85** |
| Files marked `COVERED-P1` — opened, with every claim about them resting on a region actually read | **51** |
| Files left `PENDING` | **34** |

**Correction:** an earlier draft of this section reported 68 / 53 / 15. Those figures were an estimate made before the ledger was written and they were wrong; the numbers above are counted from the ledger and supersede them.

`COVERED-P1` is applied strictly: a file qualifies only if the regions I read cover every claim I make about it. A file whose citations rest on `rg` output alone stays `PENDING`, because a grep line is evidence but not the full read R5 requires.

**The 25 PENDING files whose Phase-1 citations rest on grep output, and why:**

| File | Why it is still PENDING |
|---|---|
| `scratch/capture_traderos.py` | Read L40–L75 only; the screenshot write path is the `UNKNOWN` in S17 field 11. |
| `scratch/generate_regime_timeline.py` | Grep only (L32–L33). The EGARCH/HMM body is unread. |
| `scratch/check_data_regimes.py` | Grep only (L6). |
| `mandisense_ai/db/client.py` | Grep only (SQL statements). Sink, not source. |
| `mandisense_ai/db/prediction_logger_db.py` | Grep only (L99, L201, L234, L280, L320). Sink, not source. |
| `mandisense_ai/db/migrate_jsonl_to_pg.py` | Grep only (L36, L131, L191). Sink, not source. |
| `mandisense_ai/ensemble/feedback_store.py` | Grep only (L42). |
| `mandisense_ai/core/agents/external_factors_agent/orchestration/cache_manager.py` | Grep only (L5–L22). |
| `mandisense_ai/.gitignore` | Read L40–L50 only; effect confirmed via `git check-ignore`. |
| `docker-compose.yml` | Grep only (L25, the `curl` healthcheck). |
| `mandisense_ai/core/agents/seasonality_agent.py` | Read L20–L55 only; the `L261` repository call is grep-backed. |
| `mandisense_ai/core/agents/training_pipeline.py` | Grep only (L11, L47, L151). |
| `mandisense_ai/core/agents/training_pipeline_v2.py` | Grep only (L11, L57, L175–L181). |
| `mandisense_ai/core/agents/calibration_engine.py` | Grep only (L9, L44, L108, L115–L119). |
| `mandisense_ai/core/agents/inference_engine.py` | Grep only (L39–L40); the v1 engine's full read path is unverified. |
| `mandisense_ai/core/agents/inference_engine_v2.py` | Grep only (L31, L43–L44). |
| `mandisense_ai/core/agents/arrival_volume_agent.py` | Grep only (L18, L394–L397); its model-load path is the `UNKNOWN` in §3A. |
| `mandisense_ai/core/agents/seasonality/train_seasonality.py` | Grep only (L27–L33). |
| `mandisense_ai/core/agents/seasonality/trainer.py` | Grep only (L20–L21). |
| `mandisense_ai/evaluation/time_series_viz.py` | Grep only (L16–L24, L107–L108). |
| `mandisense_ai/evaluation/model_comparison.py` | Grep only (L21–L26, L152–L153). |
| `mandisense_ai/evaluation/statistical_validation.py` | Grep only (L7–L12, L67–L68). |
| `mandisense_ai/evaluation/regime_analysis.py` | Grep only (L14–L19, L110–L111). |
| `mandisense_ai/evaluation/error_distribution.py` | Read the `__main__` block only; L16 is grep-backed. |
| `mandisense_ai/core/agents/external_factors_agent/processing/external_fusion.py` | Read L15–L25 only (the `WEIGHTS` dict). |

**Nine further Phase-1 rows are `PENDING` for the same reason**, bringing the ledger total to 34: `api/main.py` (read L300–L340 and L630–L700; it performs no data acquisition, verified by grep for `read_csv`/`read_parquet`/`requests`, so a full read was not required for Phase 1), `backend/app/main.py`, `backend/app/services/model_loader.py`, `mandisense_ai/api/routes/history.py`, `mandisense_ai/cognition/deployment.py`, `mandisense_ai/README.md`, `mandisense_ai/tests/verify_database.py`, `mandisense_ai/tasks/retraining.py`, and `mandisense_ai/core/agents/external_factors_agent/tests/test_news_fetcher.py`. The ledger is authoritative.

**The eight `mandisense_ai/data/preprocessing/*` transformation stages** (`cleaner`, `enhanced_cleaner`, `outlier_handler`, `schema_normalizer`, `target_engineer`, `validator`, `feature_engineering`, `agent_features`) are marked `OUT-OF-SCOPE-P1`, not `PENDING`: they contain no acquisition surface, and I opened only `pipeline.py` and `config.py` from that package. They belong to a transformation-layer phase.

I have not marked any of these `COVERED-P1`. Where I cite a line from one of them, the citation rests on `rg` output showing that exact line — which is evidence, but not the full read R5 requires, so the ledger status stays honest.

### 8c. Every `UNKNOWN` field, by source

| Source | Field | What is unknown |
|---|---|---|
| S1 Agmarknet bulk extract | 4. Auth mechanism | Whether the extraction used a key, token, or cookie. No auth parameter appears in any recorded `source_url`; no Agmarknet credential name appears in `.env.example` or `render.yaml`. |
| S1 | 6. Rate limiting (partial) | Whether the observed ~10.6 s inter-request spacing was a deliberate sleep or server latency. |
| S1 | 8. Raw response shape (partial) | The true API response envelope. Only the extractor's post-processed CSV survives; `source_url` and `scrape_timestamp` are added columns, not API fields. |
| S1 | 9. Failure handling | Entirely unknown — no code exists to inspect. |
| S1 | 12. Licensing / ToS | No file in the repository states terms of use for Agmarknet data. |
| S2 Agmarknet PriceTrend client | 12. Licensing / ToS | No comment or docstring mentions terms of use. |
| S3 Open-Meteo | 12. Licensing / ToS | No comment or config mentions Open-Meteo's licence. |
| S4 NewsAPI | 8. Raw response shape (partial) | Vendor fields beyond `status`, `articles[].title`, `.description`, `.content`, `.publishedAt` — the raw payload is never persisted, only the wrapper's reshaped form. |
| S4 | 12. Licensing / ToS | No comment or config mentions NewsAPI terms or BBC content licensing, despite article text being cached to disk. |
| S8 mandi master generator | 12. Licensing / ToS | The 25 hardcoded lat/lon values carry no source attribution. |
| S9 festival_calendar.csv | 1. Acquisition class (partial) | Whether it was downloaded, transcribed, or hand-written — no writer, no attribution, no README entry. |
| S9 | 12. Licensing / ToS | Origin and licence of the festival dates. |
| S10 mandi_metadata.csv | 1. Acquisition class (partial) | Same — no writer exists. |
| S10 | 12. Licensing / ToS (repurposed) | How the `mandi_weight` values (1.0 for Kolar, 0.9 for Chickballapur, …) were derived. No comment, docstring, or document states it. |
| S14 MarketRegistry coords | 12. Licensing / ToS | The 7 hardcoded coordinate pairs carry no attribution. |
| S17 DevTools capture | 11. Landing location | Where the screenshot is written — I read only lines 40–75 of the file. |
| §3A `models/arrival/*`, `models/seasonality/*` | reader(s) | Which module loads these two model trees at inference time; I did not trace it. |

**Count: 17 distinct `UNKNOWN` field entries across 10 sources.** §8a's uncited-unit tally attributes only 15 of these to the `UNKNOWN` category, because two of them (S1 field 6's rate-limiting sub-clause and S4 field 8's vendor-field sub-clause) sit inside units that *do* carry a bracketed citation for their determinable half, and were therefore counted as cited.

The shape of what the code does not tell us is consistent: **licensing is undocumented for every external source without exception**, and **provenance is undocumented for every hand-authored file** (`festival_calendar.csv`, `mandi_metadata.csv`, the coordinate tables). Nothing in this repository records where its non-generated inputs came from.
