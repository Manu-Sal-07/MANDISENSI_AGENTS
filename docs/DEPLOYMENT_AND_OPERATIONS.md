# Deployment and operations

What it takes to run MandiSense AI for real users: how it is deployed, what it costs, how it fails, how its data stays current, and what
is still not solved. Every number is either measured (with the date) or labelled an assumption.

Live: frontend <https://mandisensi-agents.vercel.app>, API <https://mandisense-api.onrender.com/v1/health>.

## 1. How it is deployed

```
 Browser / Telegram
        │
 Vercel (Next.js frontend, free tier)  ── NEXT_PUBLIC_API_URL ──►  Render web service (Docker, free tier, Singapore)
                                                                     FastAPI + forecast store, panels and trained models in the image
 Developer machine, by hand: scripts/refresh_and_publish.py --push ── pulls data.gov.in prices, re-scores forecasts, commits to main ──► Render auto-redeploys
 (a GitHub Actions workflow exists but is manual only: its runners cannot reach data.gov.in, section 5)
```

* **No database or cache is needed.** Every answer is computed from artefacts that ship in the image (forecast store, price panels,
  trained models). `/v1/health` reports Postgres and Redis as `not_configured` and the service as `healthy`.
* **Why not a database:** the data is small (about 9 MB of panels, 22 MB of models), read-only per request and versioned in git, so a
  database would add a failure mode and a cost without adding capability. Section 5 records the incident that proved the point.
* **One worker**, because the cognition stream keeps in-memory WebSocket state (see the Dockerfile).
* **Configuration** is by environment variables; secrets (`GROQ_API_KEY`, `NEWS_API_KEY`, the Telegram token) live only in the host's
  secret store. `.env` is git-ignored. `DB_REQUIRED=1` makes a database mandatory for a deployment that adds one.

## 2. What it costs

| Item | Today | Note |
|---|---|---|
| Render web service | ₹0 (free plan, 512 MB) | sleeps when idle; see section 4 |
| Vercel | ₹0 (free tier) | |
| Data refresh | ₹0 | run from a developer machine with `scripts/refresh_and_publish.py` (about 4 minutes); GitHub Actions cannot reach the feed, see section 5 |
| Data (data.gov.in, Agmarknet) | ₹0 | public feeds |
| Language model (explanations only) | ₹0 with no key | with a key: one writer call and one judge call per explanation, median 6.7 s ([LLM_EVALUATION](LLM_EVALUATION.md)) |

**Measured on 2026-11-12:** the API process holds **313 MB** (peak 317 MB) after the heaviest endpoints are warmed, about 60% of the free
plan's 512 MB. That is enough for one worker and not enough to run a second.

**Measured under load (`scripts/load_test.py`, 2026-11-13).** A mix of the endpoints a farmer and a trader use, from concurrent clients:

| Target | Clients | Throughput | p50 / p95 latency | Failures |
|---|---|---|---|---|
| **Live, free Render plan** | 1 | 1.6 req/s | 0.66 s / 1.50 s | 0 of 100 |
| | 5 | 1.5 req/s | 3.6 s / 4.7 s | 0 of 100 |
| | 10 | no gain; p50 about 6.8 s on the requests that succeeded | | 13 of 40 (503 and 429) |
| | 25 | | | all rejected within 0.4 s (429) |
| Same code on a laptop | 1 / 5 / 10 / 25 | 22 to 28 req/s at every level | 0.01 s to 0.9 s | 0 of 400 |

How to read it:

* **One free instance sustains about 1.5 heavy requests per second**, however many clients are waiting: more clients only add latency.
  That is roughly **five simultaneous users at acceptable speed**. My earlier estimate of "tens of concurrent farmers" was wrong and is
  withdrawn.
* **The limit is the plan's CPU, not the code.** The same code on an ordinary machine handles about 25 req/s (about 15 times more), and
  adding an in-process response cache changed nothing measurable there, so it was not shipped. A plan with a full CPU is the first and
  cheapest remedy; that is a plan change, not a code change. I have not tested a paid plan, so the improvement there is unmeasured.
* **The failures above 5 clients are partly a property of the test.** The 429 responses were a Cloudflare "Just a moment" challenge
  returned by the host's edge to a single IP sending a burst, and the 503 responses carried `x-render-routing: hibernate-wake-error`.
  Whether the instance restarted under load (for example out of memory at 512 MB) is **not confirmed**; the host's logs would settle it.
  The edge throttle cleared within about a minute. Real farmers come from many addresses, but a single FPO office or a shared mobile
  gateway could look like one.
* The application's own rate limiter (60 requests per second per client, health checks exempt) was never the cause.
* The hosted language model is a second ceiling: its free tier rate-limits tokens per minute, so explanations degrade to rule-based wording
  under load (by design, section 4).

## 3. Measured behaviour (live, 2026-11-12)

| Request | Latency |
|---|---|
| `/v1/health` (warm) | 0.07 to 0.19 s |
| `/v1/market-choice/recommend/tomato` (warm, one client) | 0.5 to 1.0 s |
| `/v1/trader/spreads/tomato` (warm) | 0.1 to 1.4 s |
| first `/v1/market-choice/crops` after deploy | 14.6 s |
| first `/v1/shock/radar` after deploy | 7.2 s |
| push to `main` until the new version answers | about 2.5 minutes |

**Cold start from sleep, measured 2026-11-13: about five minutes.** After several idle hours the API did not answer for roughly five minutes
(health went from no response to `healthy` at the first successful request), then served normally (first heavy request 12 s, then about
1 s). My earlier estimate of "tens of seconds" was wrong. Until it wakes, every page of the frontend is empty, which looks like a broken
site. Two mitigations are in place or needed:

* **In the app:** a banner (`frontend/src/components/ApiWakeBanner.tsx`) says the server is waking, keeps retrying, and reloads the page when the
  server answers; it stays hidden when the API responds within a few seconds (both cases checked in headless Chrome).
* **Operationally (needed):** an external monitor that requests `/v1/health` every 5 minutes keeps the free instance awake, and doubles as the
  alert that would have caught the two-week outage. A paid plan removes sleeping altogether. Before any demonstration, request
  `/v1/health` and wait for HTTP 200; do not rely on the banner on stage.

## 4. Failure modes

| Failure | What the user sees | How it is detected | Recovery |
|---|---|---|---|
| Language-model provider down or rate-limited | the same recommendation, explained in rule-based wording | `/v1/intelligence/status`; model errors counted in the evaluation | automatic: every figure is written by code, the model only paraphrases, so the answer is identical with or without it (24/24 cases in [LLM_EVALUATION](LLM_EVALUATION.md)) |
| data.gov.in unreachable or rate-limited | prices and forecasts keep their last date, flagged "stale" past 30 hours | daily job exits 1; `/v1/health` shows `freshness` | rerun the workflow; register `DATAGOV_API_KEY` to avoid the shared sample key's limit |
| A mandi does not report | no row, never an invented price; its chance of being open is shown | by design: absence is data | none needed; 62% of mandi-days in the panel are silent (section 6) |
| Forecast skill is close to nil | direction and risk bands, not price promises | published in [RESULTS](RESULTS.md) | the decision layer, not the forecast, carries the value |
| Free instance sleeps | **empty pages for about five minutes** (measured), now explained by a banner | uptime monitor | keep-alive pings every 5 minutes, or a paid plan |
| Burst of traffic from one address | Cloudflare challenge page (429) or a 503 while the instance wakes; clears within about a minute | load test, 2026-11-13 | spread load; a paid plan with a full CPU; not yet tested |
| Image missing a data file | a tool answers `UNAVAILABLE` / "0 prints on record" while local tests pass | strict smoke test and `test_deployment_contract.py` | fixed 2026-11-13 (see below) |
| Out of memory on the 512 MB plan | restart loop | Render events and logs | move up one plan |
| Database configured but unreachable | none: degraded mode, answers unchanged | `/v1/health` `postgres: down` | fix or remove `DATABASE_URL`; `DB_REQUIRED=1` makes it fatal on purpose |
| Bad nightly run | previous store stays published | job exits 1; the smoke tests in the workflow fail before commit | revert the data commit with `git revert` |
| Source format changes (Agmarknet / data.gov.in) | stale banner | rows rejected into `rejected_observations`; job fails if every slice fails | adapt `sources/datagov.py`; schema is validated at ingest |

### Second defect found by the live smoke test, 2026-11-13

The first full smoke test against the public site passed, yet four trader endpoints returned `UNAVAILABLE` or `INSUFFICIENT_HISTORY`: the
Docker image had never contained `data/observations/market_observations.parquet` (`.dockerignore` excluded `data/` and the Dockerfile did
not copy it), so spreads, volatility, analogs and forward price had no prices on the live site, although everything passed locally. The
smoke test had counted those statuses as a pass. Fixed in commit `1bd9852`: the image now carries that one file, the smoke test treats those
statuses as failures, and `test_deployment_contract.py` pins the contract without needing Docker. After the redeploy all 29 endpoints
answered `OK` and all 29 pages rendered on the live URLs. Lesson: test the deployed artefact, not only the source tree, and never let a
degraded status count as success.

### Incident, 2026-10 to 2026-11 (kept as evidence, not hidden)

A free Render Postgres was suspended by the host after about a month. `scripts/init_db.py` ran before the API and exited 1 on the
unresolvable host, and the API itself called `sys.exit(1)` on a failed database check in production, so the service crash-looped for about
two weeks and every request timed out. Nothing the user sees depended on that database. The fix (commit `1adc12f`) makes the database
optional (warn and continue; `DB_REQUIRED=1` restores fail-fast) with regression tests in `mandisense_ai/tests/test_optional_database.py`.
Lesson: an optional dependency must be optional at every layer, and a deployment needs an external check that notices when it is down.

## 5. Keeping the data current

| Data | Source | Refresh | Status |
|---|---|---|---|
| Forecast store and market observations | data.gov.in "current daily price" feed (prices, no arrivals), Karnataka | **`python scripts/refresh_and_publish.py --push`** from a machine that can reach the feed: ingest, re-score, test, commit, push, Render redeploys | **manual, one command**; refreshed to 2026-11-12 on 2026-11-12 and not since |
| Farmer district series (arrivals-weighted price per district, crop and day) used by the district forecaster, hold-or-sell, seasonal memory, supply signal, transmission and the shock radar | Agmarknet "All Type of Report" exports in `datasets/year_data/historical_data/`, built by `scripts/build_farmer_world.py` | **manual re-export; a newer, shorter export is layered on with `--add-history <file>`, then `scripts/pipeline.py --only transmission,shock`** | **not automated**; 2021-01-01 to **2026-11-11** (district-level export of 2026-11-13 layered on 2026-11-13; the later export wins on overlapping days) |
| Farmer market panel (price and arrivals per mandi, 2021 to 2026-10-26) used by market choice, the track record, spillover and the council | the same exports, **market-level layout only** (with a Market column) | as above; a district-level export cannot extend it, because a district has 2 to 5 mandis | **not automated**; through 2026-10-26 until a market-level export for 27 Oct onward is added |
| Model retraining | forecasting models | weekly cadence inside the nightly job; `--force-retrain` on demand | automatic **when the job runs**; the job itself is run by hand (above) |

Why a git commit and not an in-process scheduler: a free instance sleeps and its disk is wiped on restart, so anything it ingested was
lost, and in production the scheduler refuses the shared sample key, so it failed every cycle. A commit is durable, reviewable and
reversible. The in-process scheduler is switched off in production (`FORECAST_SCHEDULER=off`) and remains the default for local use.

**What did not work, and what it taught (2026-11-12 and 13).** The intended design was a scheduled GitHub Actions job. Two runs showed that
GitHub's runners cannot reach `api.data.gov.in`: the first sat in the ingest step for 27 minutes on connection timeouts until the job
limit cancelled it, and the second, with a connectivity probe, reported `curl: (7) Failed to connect to api.data.gov.in port 443`. The
same feed is reachable from a normal connection (from where this was developed), so the likely cause is that the feed's host refuses
cloud addresses; that is an inference, not something the host confirmed. Three defects surfaced and were fixed:

* an unreachable feed made the ingest step crawl for up to ~48 minutes (30 slices x 3 retries x 30 s); it now aborts after the first 3
  slices if none has ever succeeded;
* worse, the job then **exited 0** and the workflow committed a store whose only change was a fresh `generated_at` timestamp. Freshness is
  judged from that timestamp, so ageing data would have read as fresh. The job now exits 2 when the feed is unavailable, and the workflow
  commits only when the observation file actually changed (`test_nightly_job_exit.py`);
* the schedule was removed, since it could only fail daily. The workflow remains as a manual option for if the feed ever becomes reachable.

One no-op commit of that kind (`generated_at` only, 2026-11-13) reached `main` before this was caught. It changed no data. The freshness
the health endpoint reports therefore means "when the forecasts were generated"; read `as_of_date` for the date of the newest data.

**Drift monitoring that exists:** the nightly run scores interval coverage (90% interval coverage 0.899 to 0.906 at horizons 1 to 7 on the
latest calibration), tracks live forecast outcomes in a ledger, and flags drifted horizons for demotion. With under 30 scored live outcomes
it reports `INSUFFICIENT_EVIDENCE` instead of a hit rate, which is the honest state of a system a few weeks into live scoring.

**Known gap, stated plainly:** the farmer-facing market-choice panels are not fed by this refresh at all, because the free feed carries no
arrivals. The honest next step is to append the daily price snapshots to the panel and treat arrivals as missing for those days, then
re-validate; until then the app states the data date ("to 2026-10-26") on its charts. The district series are fresher (to 2026-11-11)
because a district-level export was layered on; the research loader (`research/gfmc/data/loader.py`) skips district-level exports and
reads the newest market-level one by its export time.

## 6. Data quality

From `mandisense_ai/data/farmer/market_daily.parquet` (measured 2026-11-12): 16 mandis, 5 crops, 54 crop-mandi series, 2021-01-01 to
2026-10-26. **62% of mandi-days have no report**; the median series reports on 26% of days (range 0.1% to 93%). Nothing is imputed, and
the models are trained on the fact that a mandi was silent, which is the source of the largest measured gain (RESULTS section 2). Series with too
little history are refused rather than served (garlic is refused by the decision engine).

## 7. Security and privacy

* There are no user accounts and the web app collects nothing about the user. The Telegram digest bot keeps, per subscriber, only the
  chat id, first name, language, district and crops (`mandisense_ai/notify/store.py`), enough to send the digest and nothing else.
  The subscriber file is runtime state and must not be committed; deleting a subscriber (`/stop`) removes them from sending.
* Secrets only in the host secret store; rotate any key that has been pasted anywhere. A rate limiter (60 requests per second per client,
  configurable) is on the API; CORS allows only the frontend origin and local development.
* Dependencies are pinned in `requirements.lock`; CI runs the backend tests (686 passing), the frontend type-check, lint,
  unit tests and production build. The live site was smoke-tested end to end on 2026-11-13: 29 of 29 API endpoints `OK` and 29 of 29
  pages rendered in headless Chrome (`scripts/smoke_ui.py --web … --api …`).

## 8. Integration and maintenance

* **Today:** web app (farmer and trader), public REST API (`/docs`), and a Telegram digest bot that is run as a script
  (`scripts/telegram_bot.py`, `scripts/send_daily_digest.py`); it is **not** part of the Render deployment, and its subscriber file would
  not survive a free-tier restart, so a hosted bot needs a persistent store first.
* **Path to existing systems:** the same recommendations can feed an FPO's WhatsApp or SMS broadcast, or an e-NAM-adjacent dashboard,
  because the API returns plain JSON with its evidence attached. None of these integrations is built.
* **Maintenance load:** one data-refresh command run by hand (no scheduled job; section 5); a manual Agmarknet export for the farmer panels; Kannada and Hindi copy awaiting
  native-speaker review ([LANGUAGE_REVIEW](LANGUAGE_REVIEW.md)); dependency updates against `requirements.lock`.
* **Rollback:** every deployment is a git commit; Render redeploys on push to `main`.
