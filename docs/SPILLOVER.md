# Cross-Commodity Spillover

Estimates how a supply shock in one commodity transmits to the prices of others.

The engine is offline. It builds a versioned artifact; the API only reads it.
Nothing in a request path estimates anything.

## Current status: built, validated, and reporting no transmission

The engine runs end to end and its own validation says the present dataset
cannot support publishable edges. That is the intended behaviour, not a defect.

```
total edges         40
actionable edges     0
placebo verdict   FAIL  (observed 1 vs chance mean 2.97, p = 0.81)
```

A permutation placebo re-runs the whole pipeline with the shock dates
randomised. Under randomised dates no real transmission can exist, so any edge
the pipeline still calls significant is a false positive. On this panel the
real dates produce *fewer* significant edges than random ones. Every edge is
therefore withheld from serving, and `/v1/spillover/impacts/{commodity}`
returns `evidence_state: NOT_VALIDATED` with an explanation.

The full 40-edge table stays queryable via `/v1/spillover/matrix` for
inspection. It is evidence, not advice.

### Why the data cannot support it yet

| Constraint | Value | Effect |
|---|---|---|
| Commodities | 5 | Mechanical residual correlation of about -1/(k-1) = -0.25 |
| Markets | 5 different states | Transmission is confounded with regional effects |
| Weekly observations | 298 jointly observed | ~9 years, but shocks are rare |
| Independent shock episodes | 2-29 per pair | Potato has 2; the floor is 8 |
| Simultaneous hypotheses | 40 | ~4 spurious "discoveries" expected at a nominal 10% |

The binding constraint is episodes, not rows. Widening the panel — especially
**several commodities observed in the same market**, which holds geography
fixed — is what would change the result. That is a scraping task; the raw
Agmarknet extracts already show the API shape (`?commodity=65&market=112`).

## How it works

```
processed parquets
  -> weekly panel, trading days only          panel.py
  -> leave-one-out common factor removed      common_factor.py
  -> regime-based shock episodes, clustered   events.py
  -> forward-window event study + bootstrap    estimator.py
  -> Benjamini-Hochberg across all tests       build.py
  -> permutation placebo                       validate.py
  -> versioned artifact                        matrix.py
```

Five design decisions carry the weight:

1. **Common-factor removal.** Monsoon, diesel and festival demand move every
   commodity at once. Raw co-movement is mostly that. The factor for commodity
   *j* is estimated from the other *k-1* commodities so *j*'s own noise never
   enters the factor used to clean it.

2. **Episodes, not weeks.** A single onion squeeze holds the regime flag for
   many consecutive weeks. Counting each week would inflate the sample roughly
   tenfold and shrink intervals to nothing. Only clustered onsets count: 114
   onion squeeze weeks become 29 independent episodes.

3. **Block bootstrap over episodes.** Shock windows overlap and rows within an
   episode are dependent, so row-level standard errors understate uncertainty
   by about an order of magnitude.

4. **FDR over the full family.** Every tested edge enters the
   Benjamini-Hochberg correction, not just those that already cleared their
   interval — correcting only within prior winners is circular. This step alone
   cut 15 apparent discoveries to 9.

5. **Permutation placebo.** The final gate, and the one that decides whether
   anything ships.

## Usage

```bash
# rebuild after the preprocessing pipeline regenerates processed data
python scripts/build_spillover_matrix.py --placebo 100

# inspect without writing
python scripts/build_spillover_matrix.py --dry-run --no-holdout
```

The API picks up a new artifact via `POST /v1/spillover/reload`, or on restart.

### Endpoints

| Route | Purpose |
|---|---|
| `GET /v1/spillover/status` | Availability, provenance, placebo verdict. Never fails. |
| `GET /v1/spillover/commodities` | Commodities and shock types in the artifact |
| `GET /v1/spillover/impacts/{commodity}?shock_type=SQUEEZE\|GLUT` | Primary read: what a shock implies for other commodities |
| `GET /v1/spillover/edge/{source}/{target}` | One edge with its full horizon profile |
| `GET /v1/spillover/matrix` | Everything, with diagnostics |
| `POST /v1/spillover/reload` | Hot-reload after a rebuild |

Three outcomes are deliberately distinguished, so that absence of evidence is
never rendered as evidence of absence:

- `503` — artifact not built
- `200` + `INSUFFICIENT_EVIDENCE` — tested, could not tell
- `200` + actionable edges — tested, transmission found

## Safety properties

The feature is an enrichment and must never be able to degrade the system.

- `SpilloverService` returns empty results rather than raising, for a missing
  artifact, corrupt JSON, schema mismatch, or malformed arguments.
- `MarketTopology` falls back to its declared edges if anything goes wrong, and
  only adopts learned edges from an artifact whose placebo passed.
- Artifact writes are atomic (temp file then replace), so a concurrent reader
  can never observe a half-written matrix.
- `SCHEMA_VERSION` is checked on load; an incompatible artifact is refused
  rather than misread.
- Rebuilds are byte-identical on unchanged data (fixed seed), so a diff in the
  artifact always means a real change in the inputs.

## Prerequisite fixed along the way

The processed datasets had day and month transposed. `dayfirst=True` was being
applied to ISO-8601 dates in `schema_normalizer.py` and `agmarknet_ingestor.py`,
which mapped `2019-09-10` to 9 October and turned days 13-31 into `NaT` that
downstream `dropna` calls discarded. Roughly 63% of real observations were
being dropped and the survivors were filed under wrong dates.

Since spillover is entirely a lag-based measurement, no estimate was meaningful
until this was corrected. `mandisense_ai/utils/dates.py` now parses ISO first
and infers day/month order only from evidence. Trading-day counts roughly
doubled (onion 894 → 2177; tomato 1277 → 3219) and weekly volatility fell from
an implausible 40-93% to a realistic 13-32%.

Regression tests live in `mandisense_ai/tests/test_market_dates.py`.

## Reading the numbers when edges do publish

An elasticity is a *cumulative residual* move over the window after shock
onset, not a price forecast. `+8% at h=3` means: in the three weeks following
an onset, the target historically moved about 8% more than its own baseline,
after the common market factor was removed.

Treat it as a lead indicator for pre-positioning. It is deliberately a
different product from the 1-day price model.
