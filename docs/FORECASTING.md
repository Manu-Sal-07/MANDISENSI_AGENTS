# Scheduled Forecasting

Offline training, offline (batch) inference, O(1) serving. Nothing is trained
or scored inside a request.

```
NIGHTLY (scheduled)                              REQUEST (milliseconds)
┌──────────────────────────────────┐             ┌────────────────────────┐
│ 1. ingest   data.gov.in feed     │             │ GET /v1/forecast/      │
│ 2. store    idempotent upsert    │   publish   │   tomato/hoskote_apmc  │
│ 3. train    weekly cadence only  │  ────────▶  │   ?horizon=5           │
│ 4. forecast every series × h     │             │                        │
│ 5. publish  atomic swap          │             │ → table lookup         │
└──────────────────────────────────┘             └────────────────────────┘
```

## Why this shape

**Offline inference, not on-demand.** The old path loaded a model, rebuilt
features and predicted on every call — against a CSV frozen 137 days earlier,
with nothing in the response saying so. Now the expensive work runs once a
night against a known snapshot where it can be validated before anyone reads
it, and every answer carries its own freshness.

**No online training.** Deliberately excluded. It is expensive, hard to
validate, and buys nothing for a market that prints once a day. Models refit
on a **weekly** cadence; refitting nightly would only churn the artifact and
invite silent regressions.

**Ingestion and training are on different clocks.** Ingestion runs every night
because a day of prices that is not captured is gone — the upstream feed is a
snapshot with no history endpoint. Training runs weekly because one extra day
of data does not change a model.

## Data source

`data.gov.in` resource `9ef84268-…`, *Current Daily Price of Various
Commodities from Various Markets (Mandi)* — the free government feed behind
Agmarknet. Live, updated daily, no registration needed for the sample key;
set `DATAGOV_API_KEY` for production throughput.

Two constraints it imposes, both handled explicitly:

| Constraint | Consequence |
|---|---|
| **Snapshot, not archive** — no date-range query | History must accumulate one night at a time. The `api.agmarknet.gov.in` range endpoint the repo's old CSVs came from now returns `TOKEN_OR_CAPTCHA_REQUIRED`, so this is the only free path. |
| **Price only, no arrival volume** | Features are price-primary. Arrival features are emitted as NaN when unavailable and XGBoost's missing-value handling routes them, rather than zero-filling — a zero reads to a tree as "volume collapsed", which is a different claim than "unknown". |

Coverage is also sparse: on a given day only some markets report a given
commodity. Missing days are normal, never an error, and prices are never
forward-filled into a day the market did not trade.

## Modelling

**Target is log-return, not price level:** `log(price[t+h] / price[t])`,
reconstructed as `price[t] · exp(prediction)`.

A level model is rewarded for echoing yesterday's price — it can post a
flattering 5% MAPE while carrying no information, which is exactly what the
previous 1-day model did. On returns the naive forecast is exactly zero, so
reported skill is skill the model actually has. It is also scale-free, which
lets one model serve garlic at ₹11,000 and potato at ₹500.

**Direct multi-horizon:** one model per horizon (1, 3, 5, 7 days). The
alternative — predicting one day ahead and feeding the prediction back in —
compounds its own error and produces intervals that cannot be trusted past
day two. This is also what makes "next 5 days" answerable at all; the previous
engine only ever predicted `shift(-1)`, one day.

**Walk-forward validation with a promotion gate.** Folds move forward in time,
never shuffled. A horizon is promoted only if it beats the naive
`price[t+h] = price[t]` baseline *and* wins in at least 75% of folds — a small
edge on the mean can be carried by one lucky fold.

### Measured skill

Measured on the full panel — the national benchmark archive plus the 15
Karnataka APMC mandis of the operating region (97,145 training rows):

| Horizon | Skill vs naive | Fold win rate | Promoted |
|---|---|---|---|
| 1 day | +0.178 | 4/4 | yes |
| 3 days | +0.176 | 4/4 | yes |
| 5 days | +0.181 | 4/4 | yes |
| 7 days | +0.180 | 4/4 | yes |

**These numbers are panel-specific, and the honest headline is lower.**
On the national benchmark archive alone the same pipeline scores +0.010 to
+0.028, and the 1-day horizon fails the promotion gate at 2/4 folds. The
Karnataka v4 panel scores an order of magnitude higher, and the reason is
measurable rather than mysterious:

| | Benchmark archive | Karnataka v4 panel |
|---|---|---|
| Lag-1 autocorrelation of daily log-returns | −0.284 | **−0.465** |
| Mean absolute daily log-return | 0.085 | 0.060 |

v4 is a *processed* panel and it mean-reverts considerably harder than the
raw scrapes do. A model that learns mean reversion scores well against a
random-walk baseline on such a series, so the skill is real *on this data*
without being a claim about raw market forecastability.

**Quote 2–3% as the conservative figure for genuine daily spot
forecastability**; quote 18% only as skill on the processed operating-region
panel, with the autocorrelation caveat attached. Daily spot prices are close
to a random walk, and a number dramatically higher than a few percent should
always be interrogated for leakage or smoothing before it is believed.

This is why the **interval**, not the point estimate, is the decision-relevant
output. Intervals are empirical: they come from how wrong the model actually
was on held-out folds, not from a normality assumption that fat-tailed,
skewed mandi returns do not satisfy.

> During development an earlier version reported 0.94–0.97 skill. That was
> target leakage — the log-return targets were named `y_h*` while the column
> filter only excluded `target_h*`, so the answer was sitting in the feature
> set at 86% importance. `features.is_target_column` now matches both prefixes
> and `_prepare_training_frame` asserts the invariant, because a leaked target
> does not fail loudly, it just validates beautifully and is worthless.

## Data quality gates

Ingested rows pass two independent gates before they reach the store. A bad
price is worse than a missing one: a missing day is skipped, a fat-finger
print poisons every lag and rolling feature that touches it for thirty days,
silently.

| Gate | Catches |
|---|---|
| **Absolute plausibility** — per-commodity price envelope | unit errors (per-kg quoted as per-quintal), decimal slips, stuck zeros |
| **Relative spike** — vs the series' own recent median | series-specific anomalies that sit inside the absolute band |

Bounds are derived from this project's archive, not invented, and are
deliberately wide. The spike threshold (12x) sits well beyond measured
behaviour: the 99th percentile of day-over-day absolute log return in the real
archive is 0.58 (a 79% move) and the maximum is 1.70 (~5.5x). Vegetable mandis
genuinely move that hard — a tighter gate would discard the volatility the
model exists to forecast.

Rejected rows are **quarantined with a reason** and reported in the run
record, so a feed that starts misbehaving is visible immediately rather than
surfacing weeks later as unexplained drift.

## Interval calibration

The point estimate carries only 2–3% skill. The interval is the output that
earns trust, so it is measured rather than asserted — and measured *out of
sample*, since deriving a band from residuals and then scoring coverage
against those same residuals is circular and always flatters the model.

`backtest.py` refits both the model and the quantiles strictly before each
evaluation fold:

| Horizon | Realised coverage of the 90% band | 50% band | Mean band width | Verdict |
|---|---|---|---|---|
| 1 day | 86.3% | 50.1% | 21% of price | CALIBRATED |
| 3 days | 86.7% | 50.1% | 22% | CALIBRATED |
| 5 days | 86.6% | 50.2% | 24% | CALIBRATED |
| 7 days | 86.7% | 50.5% | 25% | CALIBRATED |

Bands are narrower than on the benchmark-only panel (21–25% against 34–66%)
for the same reason the skill is higher: the v4 series is less volatile. The
50% band sits almost exactly on nominal, and the 90% band runs ~3.5 points
under — inside the ±5 tolerance, but on the conservative side of it, so the
bands are marginally optimistic rather than marginally wide.

When this system says the 90% band is ₹600–900, the price lands inside it
about 90% of the time. The bands are wide because vegetable prices are
genuinely uncertain at these horizons; that width is the honest answer, not a
defect to tune away.

A backtest runs on **every retrain**, and the verdict plus per-horizon
coverage are attached to the model bundle and exposed at
`GET /v1/forecast/status`. Tolerance is ±5 points in either direction —
a band that always contains the outcome is as useless as one that rarely does.

## Refusal states

A forecast is published only when it can be justified. Otherwise the series is
returned with a reason, never a fabricated number:

| State | Meaning |
|---|---|
| `OK` | Forecast published with interval and skill |
| `INSUFFICIENT_HISTORY` | Fewer than 60 observations — features are not yet stable |
| `DORMANT` | Last traded beyond the 21-day window |
| `DISCONTINUOUS_HISTORY` | Long history and a print today, but the *previous* print was months ago, so every lag on this row spans the gap |
| `NO_PROMOTED_MODEL` | No horizon passed the baseline gate at last training |

`DISCONTINUOUS_HISTORY` exists because of a real failure caught in testing:
the archive ends Feb 2025 and the live feed starts now, so the first live
print for Agra potato produced a **+38% three-day forecast** — the model
mean-reverting against a 19-month-old lag. The row was in distribution for
none of its features. It is now refused.

## Cold start

The observation store is seeded from two bundled archives:

* the national benchmark markets — 11,149 observations, 2016–2025, five
  markets (Kolar, Lasalgaon, Agra, Neemuch, Guntur), carrying the deep
  history the models are trained on; and
* the **Karnataka operating region** — 86,663 observations across 5
  commodities × 15 APMC mandis, 2023–2026, read from the same
  `data/processed/v4` dataset the cognition engine and the candlestick API
  use.

The second exists so the forecast universe is a superset of what the product
can display. Seeded from the benchmark markets alone, the forecasting system
and the rest of the product addressed disjoint sets of markets and every
forecast lookup driven from the UI missed. Only genuine trading days are
admitted from either source; rows the preprocessing pipeline carried forward
to keep the grid dense are excluded so they cannot masquerade as prices the
market actually made.

Live ingestion then adds ~250–400 rows a night across ~500 tracked series.

Most series are new and need ~60 observations before they can be forecast.
That wait is legitimate but would be indistinguishable from a broken pipeline
if it were invisible, so it is measured:

```bash
curl localhost:8000/v1/forecast/readiness
```

returns, per series, observations held, observations still required, last seen
and state. Watch `series_ready` climb as the nightly job runs.

## Usage

```bash
# first run: seed the archive, then ingest + train + forecast
python scripts/run_nightly_job.py --seed-history --force-retrain

# normal nightly run
python scripts/run_nightly_job.py

# re-forecast without hitting the feed
python scripts/run_nightly_job.py --no-ingest

# reproduce a run as of a past date (see below)
python scripts/run_nightly_job.py --no-ingest --as-of 2026-05-02
```

`--as-of` truncates the observation store to that date and judges dormancy
and history gaps against it, so a replay sees exactly what a run that night
would have seen — it is not an exemption from the freshness rules. The date
is recorded in the store and returned on every response as `as_of_date`.

It exists because the bundled Karnataka archive ends 2026-05-02 while the
live feed starts now. Without it those series are correctly refused as
`DISCONTINUOUS_HISTORY`: the system declining to forecast across a 137-day
gap, which is the documented behaviour rather than a fault to work around.

Exit code is 1 if the forecast stage did not publish, so a scheduler can alert
on a real failure rather than on log noise. A failed run leaves the previous
night's store in place — publishing is the last step.

### Scheduling

Windows, nightly at 01:30:

```
schtasks /create /tn "MandiSense Nightly Forecast" /sc daily /st 01:30 ^
  /tr "\"<repo>\ms_env\Scripts\python.exe\" \"<repo>\scripts\run_nightly_job.py\"" /f
```

Linux:

```
30 1 * * *  cd /srv/mandisense && ms_env/bin/python scripts/run_nightly_job.py
```

### Endpoints

| Route | Purpose |
|---|---|
| `GET /v1/forecast/{commodity}/{mandi_id}?horizon=5` | Primary read. Omit `horizon` for the full curve; the nearest published horizon is substituted and stated. |
| `GET /v1/forecast/status` | Freshness, coverage, model version. Never fails. |
| `GET /v1/forecast/readiness` | Per-series progress toward eligibility |
| `GET /v1/forecast/series` | Tracked series and promoted horizons |
| `POST /v1/forecast/reload` | Pick up a new store without restarting |

## Safety properties

- **Train/serve skew is structurally impossible.** `features.build_features`
  is the only place features are built; training and batch inference both call
  it. The previous generation duplicated this logic across
  `training_pipeline_v2.py` and `inference_engine_v3.py`.
- **Ingestion is idempotent.** Keyed on (date, commodity, mandi); re-running a
  night cannot double count. A revised upstream print replaces the earlier read.
- **Every stage degrades rather than aborting.** Feed down → re-forecast from
  stored observations and label the result honestly. No model → refuse, keep
  the last good store.
- **Atomic publishes.** Temp file then replace, for both stores.
- **Locked writes.** Upsert is a read-modify-write; an exclusive lock file
  makes a scheduled run overlapping a manual one a wait rather than silent
  data loss.
- **Bounded inference cost.** Batch scoring trims each series to a lookback
  window instead of rebuilding features across the whole archive. Verified
  bit-identical to the full-history path, so the speedup cannot introduce
  train/serve skew.
- **The service never raises into a request.** Missing, corrupt or
  schema-incompatible store → "unavailable", not a 500.

## Relationship to the existing engine

This runs alongside `/v1/predict` and the cognition layer; nothing was removed.
The older path remains for the snapshot-driven TraderOS views. New work that
needs a price forecast should use `/v1/forecast/*`, which is the one that knows
what day it is.
