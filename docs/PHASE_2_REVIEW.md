# Phase 2 Review — Objective Achievement & Implementation Progress

MandiSense AI. Prepared for the Phase 2 project review.

This document states what Phase 2 set out to add on top of the Phase 1
baseline, what is actually running, how each claim can be verified live in
front of the panel, and — explicitly — what is not yet true.

---

## 1. Where Phase 1 ended

The Phase 1 baseline delivered a working multi-agent decision system:

| Capability | Where it lives |
|---|---|
| Multi-agent cognition engine (seasonality, arrival volume, regime, spillover agents) | `mandisense_ai/cognition/`, `mandisense_ai/core/agents/` |
| Ensemble model pool with walk-forward CV and inverse-MAPE weighting | `mandisense_ai/ensemble/`, `mandisense_ai/core/agents/*/models/` |
| Decision directives (BUY / SELL / WAIT) with confidence and reasoning | `/v1/cognition/*`, `/v1/decision/` |
| TraderOS front end — terminal, market explorer, mandi detail | `frontend/src/app/` |
| Containerised deployment, health checks, circuit breakers | `Dockerfile`, `render.yaml`, `/v1/health` |

Phase 1's answer to "what will the price be?" was a single next-day point
estimate produced **inside the request**, against a CSV snapshot, with no
statement of how stale that snapshot was and no interval.

That limitation defined Phase 2.

---

## 2. What Phase 2 committed to, and its status

| # | Phase 2 milestone | Status | Evidence |
|---|---|---|---|
| 1 | Replace on-request inference with a **scheduled offline pipeline** (ingest → train → batch forecast → publish) | **Done** | `scripts/run_nightly_job.py`, `mandisense_ai/forecasting/pipeline.py` |
| 2 | **Multi-horizon** forecasting (1/3/5/7 days) replacing single next-day | **Done** | 4 horizons promoted, `/v1/forecast/{c}/{m}` |
| 3 | **Honest uncertainty** — empirical, out-of-sample calibrated intervals | **Done** | `backtest.py`; coverage 86.3–86.7% on a nominal 90% band |
| 4 | **Promotion gate** — no horizon ships unless it beats the naive baseline | **Done** | `validation.py`; 4/4 fold win rate at every horizon |
| 5 | **Refusal states** instead of fabricated numbers | **Done** | `INSUFFICIENT_HISTORY`, `DORMANT`, `DISCONTINUOUS_HISTORY`, `NO_PROMOTED_MODEL` |
| 6 | **Live data ingestion** from the public data.gov.in Agmarknet feed | **Done** | `forecasting/sources/datagov.py`; ~443 rows ingested to date |
| 7 | **Data quality gates** with quarantine and reasons | **Done** | `validation.py`; absolute envelope + relative spike |
| 8 | **Cross-commodity spillover** estimation, offline and validated | **Done** | `mandisense_ai/spillover/`, `/v1/spillover/*` |
| 9 | Spillover **statistical honesty** — FDR correction and a permutation placebo gate | **Done** | Placebo FAIL → 0 edges served (see §5) |
| 10 | **Integration with the Phase 1 baseline** — the two halves address the same markets | **Done in this review cycle** | 75/75 coverage (see §4) |
| 11 | **Unified health** across Phase 1 and Phase 2 subsystems | **Done in this review cycle** | `/v1/health` |

---

## 3. End-to-end workflow — how to run it live

Two processes. Both start clean from the repository.

```bash
# 1. Offline pipeline: ingest -> train -> batch forecast -> publish
python scripts/run_nightly_job.py --seed-history --force-retrain --as-of 2026-05-02

# 2. API
ms_env/Scripts/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 3. Front end
cd frontend && npm run dev          # http://localhost:3000/market-explorer
```

The pipeline exits non-zero if the forecast stage did not publish, so the
scheduler alerts on a genuine failure rather than on log noise. Publishing is
the last step, so a failed run leaves the previous night's store in place.

### Verification, in one call

```bash
curl localhost:8000/v1/health
```

```json
{
  "status": "healthy",
  "probe_duration_ms": 4.0,
  "components": {
    "cognition":   { "phase": 1, "status": "up", "cycle_count": 1 },
    "forecasting": { "phase": 2, "status": "up", "series_published": 79,
                     "freshness": "FRESH", "as_of_date": "2026-05-02" },
    "spillover":   { "phase": 2, "status": "up", "total_edges": 40,
                     "placebo_verdict": "FAIL", "actionable_edges": 0 },
    "postgres":    { "required": false, "reachability": "not_configured" },
    "redis":       { "required": false, "reachability": "not_configured" }
  }
}
```

One request shows the Phase 1 baseline and both Phase 2 engines live in the
same process.

### Demo path through the UI

1. `http://localhost:3000/market-explorer`
2. Select **TOMATO · KOLAR** (the default).
3. **Forecast** tab — four horizons, each with a point, a 90% interval and
   measured skill, plus the as-of date.
4. Switch commodity/mandi — the panel refetches; any series the system will
   not forecast shows its refusal reason instead of a number.

---

## 4. Integration with the Phase 1 baseline

This was the one milestone genuinely at risk, and it is the one worth
presenting in detail, because fixing it is what makes the two phases a single
system rather than two projects in one repository.

**The problem.** The Phase 2 observation store was seeded only from the five
*national benchmark* markets in the historical archive — Kolar, Lasalgaon,
Agra, Neemuch, Guntur. The Phase 1 cognition layer and every TraderOS view
address the **15 Karnataka APMC mandis** in `data/processed/v4`. The overlap
was one market. Measured against the universe the product can actually
display:

```
Phase 1 displayable universe : 75 commodity x mandi pairs
Forecast coverage BEFORE     :  0 / 75     every UI-driven lookup 404'd
Forecast coverage AFTER      : 75 / 75     all publishing live forecasts
```

**Three defects were behind it**, each fixed:

1. **The backfill never read the Karnataka dataset.**
   `sources/backfill.py` globbed `data/processed/*.parquet` only.
   `load_v4_karnataka_history()` now seeds from the same canonical v4 CSVs the
   cognition engine and the candlestick API read — 86,663 observations across
   75 series. Only genuine trading days are admitted; rows the preprocessing
   pipeline carried forward to keep the grid dense are excluded so they cannot
   masquerade as prices the market actually made.

2. **`canonical_market()` was not idempotent.**
   `bangalore_yeshwanthpur` is a canonical id that does not end in a
   market-type word, so a second normalisation pass appended `_apmc` and
   produced `bangalore_yeshwanthpur_apmc` — a *different* series from the one
   the rest of the product keys on, silently splitting its history. Any id the
   function emits is now returned unchanged. Regression tests assert
   `canonical_market(canonical_market(x)) == canonical_market(x)` across the
   alias table.

3. **The forecast router did not resolve aliases.**
   It lower-cased the path parameter and looked it up directly, so
   `bangalore_apmc` — the id the cognition layer uses — never reached
   `bangalore_yeshwanthpur` in the store. It now resolves through the same
   canonical mapping ingestion and backfill use, so there is exactly one
   definition of a mandi id across the system.

**Consequences beyond the 404s.** Training rows went from 11,149 to 97,145.
The 1-day horizon, previously withheld for failing the promotion gate, now
passes it, and fold win rate at every horizon is 4/4 rather than 2–3/4.

---

## 5. Measured results

### Forecast skill and calibration

Walk-forward, 4 folds, never shuffled. Skill is versus the naive
`price[t+h] = price[t]` baseline. Coverage is out-of-sample: both the model
and the quantiles are refit strictly before each evaluation fold.

| Horizon | Skill vs naive | Fold win rate | 90% band coverage | 50% band | Band width | Verdict |
|---|---|---|---|---|---|---|
| 1 day | 0.178 | 4/4 | 86.3% | 50.1% | 20.8% | CALIBRATED |
| 3 days | 0.176 | 4/4 | 86.7% | 50.1% | 22.4% | CALIBRATED |
| 5 days | 0.181 | 4/4 | 86.6% | 50.2% | 23.9% | CALIBRATED |
| 7 days | 0.180 | 4/4 | 86.7% | 50.5% | 25.1% | CALIBRATED |

Published store: 304 records across 79 series, 300 `OK`, 4 `DORMANT`.

### Spillover: the engine runs and reports no transmission

40 edges estimated, **0 served**. A permutation placebo — the whole pipeline
re-run with shock dates randomised — produced *more* significant edges by
chance (mean 2.97) than the real dates did (1), p = 0.81. Every edge is
therefore withheld and `/v1/spillover/impacts/{commodity}` returns
`NOT_VALIDATED` with an explanation.

**This is the engine working, not failing.** The binding constraint is
independent shock episodes (2–29 per pair against a floor of 8) across 5
commodities in 5 different states, where transmission is confounded with
regional effects. The full 40-edge table stays queryable at
`/v1/spillover/matrix` as evidence. Widening the panel to several commodities
observed in the *same* market is what would change the result.

---

## 6. Stated honestly — limitations

These are volunteered because a reviewer will find them, and because each one
is a consequence of a deliberate choice rather than an oversight.

**The demonstration replays as of 2026-05-02.** The bundled Karnataka archive
ends 2026-05-02; the live data.gov.in feed starts now. `--as-of` truncates the
observation store to that date so the run sees exactly what a run that night
would have seen. Without it the archive series are correctly refused as
`DISCONTINUOUS_HISTORY` — the system declining to forecast across a 137-day
gap. The as-of date is recorded in the store and returned on every response;
nothing is hidden by it.

**The 0.18 skill figure is dataset-specific, and lower on raw data.** The
national benchmark archive alone yields 0.02–0.03 skill. The Karnataka v4
panel yields 0.18. The cause is measurable: lag-1 autocorrelation of daily
log-returns is **−0.465** in the v4 panel against **−0.284** in the raw
archive, and mean absolute daily log-return is 0.060 against 0.085. The v4
data is a *processed* panel, and it mean-reverts considerably harder than the
raw scrapes do. A model that learns mean reversion scores well against a
random-walk baseline on such a series.

The conservative claim about genuine market forecastability is therefore the
**2–3%** figure, not 18%. The higher number should be presented as skill on
the processed operating-region panel, with the caveat attached.

**Live coverage is still accumulating.** 511 series are tracked from the live
feed; most hold a single observation and need ~60 before they are eligible.
`/v1/forecast/readiness` reports per-series progress so the wait is visible
rather than indistinguishable from a broken pipeline.

**Postgres and Redis are not provisioned locally.** Both are accelerators.
The cognition engine, the forecast store and the spillover matrix all read
local artifacts and serve correctly without them, which is why health reports
them as `not_configured` rather than as a fault.

**Spillover serves nothing today.** By design — see §5.

---

## 7. Anticipated questions

**"Why is the interval so wide?"**
Because vegetable prices at these horizons are genuinely that uncertain. The
band is measured from held-out error, not asserted from a normality
assumption that fat-tailed mandi returns do not satisfy. A narrower band would
be a less honest one. The point estimate carries a few percent of skill; the
interval is the decision-relevant output.

**"Why refuse the 1-day horizon earlier and publish it now?"**
The promotion gate requires beating the naive baseline in at least 75% of
folds. On the benchmark-only data the 1-day model won 2 of 4. With the
Karnataka panel included it wins 4 of 4. The gate did its job in both cases.

**"Isn't 18% skill too good for daily spot prices?"**
Yes, for raw prices — and that is why §6 states the −0.465 autocorrelation
measurement rather than claiming the number at face value.

**"How do you know there is no target leakage?"**
An earlier version reported 0.94–0.97 skill. The log-return targets were named
`y_h*` while the column filter only excluded `target_h*`, so the answer sat in
the feature set at 86% importance. `features.is_target_column` now matches
both prefixes, `_prepare_training_frame` asserts the invariant, and
`TestTargetLeakage` covers it. A leaked target does not fail loudly — it
validates beautifully and is worthless.

**"What stops training and serving diverging?"**
`features.build_features` is the single place features are built; training and
batch inference both call it. The previous generation duplicated this logic
across two files.

---

## 8. Verification summary

| Check | Result |
|---|---|
| Test suite | **228 passed**, 0 failed |
| Frontend type check (`tsc --noEmit`) | clean |
| Frontend production build | clean, 10 routes |
| API module imports | all routers import |
| `/v1/health` | `healthy`, 4 ms |
| Phase 1 → Phase 2 forecast coverage | **75 / 75** |
| End-to-end pipeline run | `status: OK`, 300 forecasts published |
