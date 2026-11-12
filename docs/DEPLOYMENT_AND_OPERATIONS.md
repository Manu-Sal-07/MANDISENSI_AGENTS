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
 GitHub Actions (daily, 19:00 IST) ── pulls data.gov.in prices, re-scores forecasts, commits to main ──► Render auto-redeploys
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
| GitHub Actions daily refresh | ₹0 | public repository; the job takes about 4 minutes |
| Data (data.gov.in, Agmarknet) | ₹0 | public feeds |
| Language model (explanations only) | ₹0 with no key | with a key: one writer call and one judge call per explanation, median 6.7 s ([LLM_EVALUATION](LLM_EVALUATION.md)) |

**Measured on 2026-11-12:** the API process holds **313 MB** (peak 317 MB) after the heaviest endpoints are warmed, about 60% of the free
plan's 512 MB. That is enough for one worker and not enough to run a second.

**Scaling assumptions (not measured under load):** a request is small arithmetic over in-memory tables (0.1–1 s warm, measured), so one
small instance should serve tens of concurrent farmers. The first thing to break is memory, not CPU: moving to a paid instance with
1–2 GB is the first step, and it is a plan change, not a code change. The hosted language model is the real ceiling: the free tier of the
provider rate-limits tokens per minute, so explanations degrade to rule-based wording under load (by design, see section 4).

## 3. Measured behaviour (live, 2026-11-12)

| Request | Latency |
|---|---|
| `/v1/health` (warm) | 0.19 s |
| `/v1/market-choice/recommend/tomato` (warm) | 1.0 s |
| `/v1/trader/spreads/tomato`, `/v1/council/evaluation` (warm) | 0.12 s |
| first `/v1/market-choice/crops` after deploy | 14.6 s |
| first `/v1/shock/radar` after deploy | 7.2 s |
| push to `main` until the new version answers | about 2.5 minutes |

Cold-start from sleep on the free plan has **not** been measured separately; expect tens of seconds. Open the site a few minutes before a
demonstration, or put an uptime monitor on `/v1/health`.

## 4. Failure modes

| Failure | What the user sees | How it is detected | Recovery |
|---|---|---|---|
| Language-model provider down or rate-limited | the same recommendation, explained in rule-based wording | `/v1/intelligence/status`; model errors counted in the evaluation | automatic: every figure is written by code, the model only paraphrases, so the answer is identical with or without it (24/24 cases in [LLM_EVALUATION](LLM_EVALUATION.md)) |
| data.gov.in unreachable or rate-limited | prices and forecasts keep their last date, flagged "stale" past 30 hours | daily job exits 1; `/v1/health` shows `freshness` | rerun the workflow; register `DATAGOV_API_KEY` to avoid the shared sample key's limit |
| A mandi does not report | no row, never an invented price; its chance of being open is shown | by design: absence is data | none needed; 62% of mandi-days in the panel are silent (section 6) |
| Forecast skill is close to nil | direction and risk bands, not price promises | published in [RESULTS](RESULTS.md) | the decision layer, not the forecast, carries the value |
| Free instance sleeps | first request takes longer | uptime monitor | wake-up pinger or a paid plan |
| Out of memory on the 512 MB plan | restart loop | Render events and logs | move up one plan |
| Database configured but unreachable | none: degraded mode, answers unchanged | `/v1/health` `postgres: down` | fix or remove `DATABASE_URL`; `DB_REQUIRED=1` makes it fatal on purpose |
| Bad nightly run | previous store stays published | job exits 1; the smoke tests in the workflow fail before commit | revert the data commit with `git revert` |
| Source format changes (Agmarknet / data.gov.in) | stale banner | rows rejected into `rejected_observations`; job fails if every slice fails | adapt `sources/datagov.py`; schema is validated at ingest |

### Incident, 2026-10 to 2026-11 (kept as evidence, not hidden)

A free Render Postgres was suspended by the host after about a month. `scripts/init_db.py` ran before the API and exited 1 on the
unresolvable host, and the API itself called `sys.exit(1)` on a failed database check in production, so the service crash-looped for about
two weeks and every request timed out. Nothing the user sees depended on that database. The fix (commit `1adc12f`) makes the database
optional (warn and continue; `DB_REQUIRED=1` restores fail-fast) with regression tests in `mandisense_ai/tests/test_optional_database.py`.
Lesson: an optional dependency must be optional at every layer, and a deployment needs an external check that notices when it is down.

## 5. Keeping the data current

| Data | Source | Refresh | Status |
|---|---|---|---|
| Forecast store and market observations | data.gov.in "current daily price" feed (prices, no arrivals), Karnataka | **daily GitHub Actions job**, then commit and redeploy | automated; was stale since 2026-10-26 before this, refreshed to 2026-11-12 |
| Farmer panels (price and arrivals per mandi, 2021 to 2026-10-26) used by market choice, the shock radar and the insight panels | Agmarknet exports in `datasets/year_data/`, built by `scripts/build_farmer_world.py` | **manual re-export, then `scripts/pipeline.py`** | **not automated**; the farmer advice is trained through 2026-10-26 |
| Model retraining | forecasting models | weekly cadence inside the nightly job; `--force-retrain` on demand | automated |

Why the daily job is a git commit and not an in-process scheduler: a free instance sleeps and its disk is wiped on restart, so anything it
ingested was lost, and in production the scheduler refuses the shared sample key, so it failed every cycle. A commit is durable, reviewable
and reversible. The in-process scheduler is switched off in production (`FORECAST_SCHEDULER=off`) and remains the default for local use.

**Drift monitoring that exists:** the nightly run scores interval coverage (90% interval coverage 0.899 to 0.906 at horizons 1 to 7 on the
latest calibration), tracks live forecast outcomes in a ledger, and flags drifted horizons for demotion. With under 30 scored live outcomes
it reports `INSUFFICIENT_EVIDENCE` instead of a hit rate, which is the honest state of a system a few weeks into live scoring.

**Known gap, stated plainly:** the farmer-facing market-choice panels are not yet fed by the daily job, because the free feed carries no
arrivals. The honest next step is to append the daily price snapshots to the panel and treat arrivals as missing for those days, then
re-validate; until then the app states the data date ("to 2026-10-26") on its charts.

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
* Dependencies are pinned in `requirements.lock`; CI runs the backend tests (675 passing on 2026-11-12), the frontend type-check, lint,
  unit tests and production build.

## 8. Integration and maintenance

* **Today:** web app (farmer and trader), public REST API (`/docs`), and a Telegram digest bot that is run as a script
  (`scripts/telegram_bot.py`, `scripts/send_daily_digest.py`); it is **not** part of the Render deployment, and its subscriber file would
  not survive a free-tier restart, so a hosted bot needs a persistent store first.
* **Path to existing systems:** the same recommendations can feed an FPO's WhatsApp or SMS broadcast, or an e-NAM-adjacent dashboard,
  because the API returns plain JSON with its evidence attached. None of these integrations is built.
* **Maintenance load:** one daily automated job; a manual Agmarknet export for the farmer panels; Kannada and Hindi copy awaiting
  native-speaker review ([LANGUAGE_REVIEW](LANGUAGE_REVIEW.md)); dependency updates against `requirements.lock`.
* **Rollback:** every deployment is a git commit; Render redeploys on push to `main`.
