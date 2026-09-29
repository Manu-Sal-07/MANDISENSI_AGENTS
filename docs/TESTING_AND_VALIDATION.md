# Testing, Validation & Result Analysis

MandiSense AI. Prepared for the Phase 2 project review.

How the four stated objectives are tested, which metrics are used and why
those metrics, what the results are, and what they mean.

---

## 1. How to reproduce everything in this document

```bash
# Objective-traceable suite: runs the tests grouped by objective,
# reads the measured metrics, and interprets both.
python scripts/run_validation_suite.py

# Flat run with coverage
python -m pytest mandisense_ai/tests -q --cov=mandisense_ai --cov-report=term

# Phase 1 -> Phase 2 integration, against a running API
python scripts/verify_phase2_integration.py
```

`run_validation_suite.py` exits non-zero if any objective's tests fail, so it
works as a gate and not only as a report. `--markdown docs/VALIDATION_REPORT.md`
regenerates the machine-produced report alongside this hand-written one.

---

## 2. Headline result

```
310 tests, 310 passed, 0 failed
Objective 1  Multi-agent ensemble        82 passed   PASS
Objective 2  Cross-commodity spillover   61 passed   PASS
Objective 3  LLM decision intelligence   52 passed   PASS
Objective 4  Volatility feedback         44 passed   PASS
Supporting   Scheduled forecasting       71 passed   PASS
```

Statement coverage over the four objective packages is **65%**, up from 53%
at the start of this review cycle. The modules that carry each objective's
central claim are covered far higher than the average — the figures are in
§7 — because coverage was raised where a silent failure would be costly
rather than uniformly.

---

## 3. Why the tests are grouped by objective

A flat "310 tests passed" is not evidence that the spillover objective was
met. It is evidence that 310 assertions hold.

So the suite is organised around the four claims rather than around the
module tree. Every test file belongs to exactly one objective, every
objective states its claim in one sentence, and the metrics reported under
it are interpreted against that sentence. A gap then shows up as an
objective with thin coverage rather than as an absence nobody counted.

This is also what caught the largest defect in this cycle: grouping by
objective made it obvious that Objective 2's `validate.py` — the permutation
placebo that decides whether *anything* ships — had **0% coverage**, while
the estimator around it was covered at 97%.

---

## 4. Test design principles

**Fixtures, not live state.** Tests construct their own data in-process.
A suite that reads the live forecast store fails when tonight's forecast
moves, which trains everyone to ignore it.

**Adversarial inputs where the claim is about honesty.** Objective 3 claims
the system will not state a figure it cannot support. That is tested by
injecting a provider that deliberately invents one and asserting it is
caught — not by checking that the honest path works.

**Properties, not golden outputs.** `test_market_normalisation_is_idempotent`
asserts `f(f(x)) == f(x)` across the alias table rather than pinning one
expected string, so it catches the whole class of bug.

**Regression tests name the bug.** Each one carries a docstring explaining
the failure it prevents, so a future reader can tell whether it still
matters.

---

## 5. Results by objective

### Objective 1 — Multi-agent ensemble system

**Claim.** Independent agents are fused into one prediction whose weights are
earned from measured out-of-sample error, not fixed.

| Metric | Value | Why this metric |
|---|---|---|
| Agents fused | 3 | Seasonality, arrival volume, external factors |
| Meta-ensemble coverage | 94% | The fusion layer is the claim |
| Prediction cycles logged | 147 | The substrate the learned ensemble trains on |
| Cycles with realised outcomes | 0 | Only these are training-eligible |
| Tests | 82 passed | |

**Interpretation.** Fusion is deterministic and fully covered: given the same
agent outputs it produces the same prediction, with attribution and risk
flags. Walk-forward CV with `TimeSeriesSplit` ranks the model pool and
inverse-MAPE weights it.

147 cycles are on record; none yet carry a backfilled outcome, so the
learned ensemble is still blending at its Phase-1 floor (rule-based
contributes ≥30% by construction). That is the documented cold-start
behaviour rather than a regression, and it is visible precisely because the
leakage boundary is enforced — a record without an outcome cannot enter
training. `test_prediction_logger.py::test_pending_records_are_not_training_eligible`
is the test that holds that line.

### Objective 2 — Cross-commodity spillover

**Claim.** Transmission is estimated, and published only when it survives
multiple-testing correction and a permutation placebo.

| Metric | Value | Why this metric |
|---|---|---|
| Edges estimated | 40 | 5 commodities × shock types × directions |
| Edges served | **0** | What actually reaches a user |
| Placebo verdict | **FAIL** | The gate that decides |
| Empirical p-value | 0.81 | Observed 1 vs chance mean 2.97 |
| Tests | 61 passed | |

**Interpretation — read this one carefully.** The engine estimated 40 edges
and served none. Under randomised shock dates the pipeline produced *more*
"significant" edges (mean 2.97) than the real dates did (1), so the real
result is indistinguishable from chance and every edge was withheld.

**This is the objective being met, not missed.** The objective was to
estimate transmission *and establish whether it is real*. The gate answered
that question, and on this panel the answer is no. A version that published
40 unvalidated edges would have failed the objective while looking more
impressive.

The binding constraint is independent shock episodes — 2 to 29 per pair
against a floor of 8 — across five commodities in five *different* states,
where transmission is confounded with regional effects. Widening the panel
to several commodities observed in the same market is what would change it.

The full 40-edge table stays queryable at `/v1/spillover/matrix` as evidence,
and `/v1/spillover/impacts/{commodity}` returns `NOT_VALIDATED` with an
explanation, so absence of evidence is never rendered as evidence of absence.

### Objective 3 — LLM decision intelligence

**Claim.** A language model reasons over the system's evidence to produce a
structured brief, and every figure it states is verified against that
evidence before the brief is served.

| Metric | Value | Why this metric |
|---|---|---|
| Grounding enforced | true | The central guarantee |
| Probe: true figure accepted | true | The verifier is not simply rejecting everything |
| Probe: invented figure rejected | true | The verifier actually works |
| Evidence sources fused | 4 | cognition, forecast, spillover, market |
| Active provider | deterministic | Default; Claude enabled by env var |
| Tests | 52 passed | |

**Interpretation.** The layer built in this cycle assembles a flat, keyed
evidence bundle from all four engines, hands it to a provider, and then
**verifies the result against that same bundle** before returning it. Every
figure in the brief must appear in the evidence; every factor must cite an
evidence key that exists.

The verification is adversarially tested. `_HallucinatingProvider` states a
price of 2450 that is nowhere in the evidence, and the suite asserts it is
caught. `_BadCitationProvider` cites `satellite.ndvi`, a source that does not
exist, and the suite asserts that is caught too. The verifier is also
tested for false positives — rounding 1719.53 to 1720 in prose, quoting the
as-of date, and saying "the 90% band" must all pass, or the check would be
noise nobody reads.

A failing brief is **served with `grounded: false` and the issues listed**,
not discarded. A caller that can see the problem can act on it; one that
receives a 500 cannot.

Two provider implementations sit behind one interface. The deterministic one
is the default and composes the brief from the evidence with explicit rules,
so a procurement recommendation never depends on a network call and the demo
never depends on a third party. Setting `ANTHROPIC_API_KEY` and
`MANDISENSE_LLM_PROVIDER=claude` switches to Claude, which fills the same
schema through a strict tool call. Both are verified identically — the
deterministic provider is not exempt just because it cannot hallucinate.

### Objective 4 — Volatility feedback system

**Claim.** Realised error and the detected volatility regime feed back into
model weights, so the ensemble adapts rather than staying fixed.

| Metric | Value | Why this metric |
|---|---|---|
| Weights respond to error | **true** | The loop is closed |
| Weight shift, 1% vs 40% error model | 0.5/0.5 → **0.965/0.035** | Magnitude of response |
| Weights respond to regime | **true** | Volatility reaches the weighting |
| Regime boost on shock-robust model | 0.5 → **0.5652** | |
| Store path deterministic | true | Regression cover, see below |
| Tests | 44 passed | |

**Interpretation.** The loop is measurably closed. Given one model at 1%
realised error and another at 40% over the same series, the weights move from
an even split to 0.965 / 0.035. Declaring a supply-shock regime raises the
shock-robust model's weight from 0.5 to 0.5652. Both are measured live by the
validation suite at report time, not asserted from documentation.

The EMA smoothing factor is tested for effect, not just for presence:
`test_alpha_controls_responsiveness` asserts that a higher alpha reacts
harder to recent error, which is the difference between a tunable parameter
and a decorative one.

**A real defect was found and fixed here.** Both `FeedbackStore` and
`PredictionLogger` resolved their storage directory *relative to the process
working directory* — and `FeedbackStore` additionally read
`settings.paths.data`, a field that does not exist, with the resulting
`AttributeError` swallowed by a bare `except`. The history had therefore
split across two directories: 81 records in one, 66 in the other. The rolling
error driving the weighting was being computed from 55% of the available
history, and nothing reported it. Both now resolve to one absolute path, the
66 orphaned records were merged back, and `TestStorageLocation` keeps it
fixed.

### Supporting — Scheduled forecasting

Not one of the four objectives, but it underpins objectives 2–4, so it is
reported separately rather than folded in.

| Horizon | Skill vs naive | Fold win rate | 90% coverage | 50% coverage | Verdict |
|---|---|---|---|---|---|
| 1 day | 0.1781 | 4/4 | 86.3% | 50.1% | CALIBRATED |
| 3 days | 0.1764 | 4/4 | 86.7% | 50.2% | CALIBRATED |
| 5 days | 0.1806 | 4/4 | 86.6% | 50.2% | CALIBRATED |
| 7 days | 0.1800 | 4/4 | 86.7% | 50.5% | CALIBRATED |

**Why these metrics.** Skill is measured against a naive `price[t+h] =
price[t]` baseline because a level model is rewarded for echoing yesterday's
price and can post a flattering MAPE while carrying no information. Coverage
is measured **out of sample** — both the model and the quantiles are refit
strictly before each evaluation fold — because deriving a band from residuals
and then scoring it against those same residuals is circular.

**The honest reading of the skill figure.** 0.18 is panel-specific. The same
pipeline scores 0.010–0.028 on the raw national benchmark archive. The cause
is measurable: lag-1 autocorrelation of daily log-returns is **−0.465** in the
processed Karnataka panel against **−0.284** in the raw archive, and mean
absolute daily log-return is 0.060 against 0.085. The processed panel
mean-reverts considerably harder, and a model that learns mean reversion
beats a random-walk baseline easily on such a series.

**Quote 2–3% as the conservative claim about genuine daily spot
forecastability.** Quote 18% only as skill on the processed operating-region
panel, with the autocorrelation caveat attached.

---

## 6. Defects found and fixed during this validation cycle

Testing that finds nothing has not been performed. These are the defects the
work surfaced, each now covered by a regression test.

| # | Defect | Impact | Fix |
|---|---|---|---|
| 1 | 17 files pinned absolute `d:/BMS COLL/...` paths, including `models/registry.py` on the inference path | Nothing ran on another machine, in Docker, or on Render | All anchored on the installed package |
| 2 | `FeedbackStore` read `settings.paths.data` — a nonexistent field — behind a bare `except` | Configured path never used; fell back to a CWD-relative literal | Reads `data_dir`, resolved absolute |
| 3 | Feedback history split across two directories | Rolling error computed from 55% of history, silently | Paths unified; 66 orphaned records merged |
| 4 | `canonical_market()` was not idempotent | `bangalore_yeshwanthpur` gained `_apmc` on a second pass, splitting a series | Canonical ids returned unchanged |
| 5 | Spillover `validate.py` at 0% coverage | The placebo gate, untested | 93% coverage, incl. reproducibility |
| 6 | No LLM decision intelligence existed | Objective 3 unimplemented | Built with enforced grounding |

---

## 7. Coverage

Overall statement coverage across the four objective packages: **65%**
(was 53%).

| Module | Before | After | Objective |
|---|---|---|---|
| `spillover/validate.py` | 0% | **93%** | 2 |
| `spillover/panel.py` | 0% | **91%** | 2 |
| `ensemble/dynamic_weighter.py` | 24% | **90%** | 4 |
| `ensemble/regime_detector.py` | 22% | **88%** | 4 |
| `ensemble/feedback_store.py` | 25% | **87%** | 4 |
| `ensemble/prediction_logger.py` | 23% | **88%** | 4 |
| `intelligence/schema.py` | — | **96%** | 3 |
| `intelligence/service.py` | — | **91%** | 3 |
| `intelligence/grounding.py` | — | **90%** | 3 |
| `ensemble/meta_ensemble.py` | 94% | 94% | 1 |
| `spillover/estimator.py` | 97% | 98% | 2 |

Coverage is a floor, not a target. `meta_ensemble.py` at 94% and
`estimator.py` at 98% were already well covered and were left alone;
the effort went where a silent failure would be expensive.

**Known remaining gaps, stated rather than hidden:** `learned_ensemble.py`
(19%) and `agent_ensemble.py` (18%) are the deepest untested modules. Both
are exercised end-to-end through the meta-ensemble path but lack unit
coverage. They are the next thing to test, and they are listed here because
an unstated gap is worse than a stated one.

---

## 8. What a reviewer can check live

| Check | Command | Expected |
|---|---|---|
| Every objective validated | `python scripts/run_validation_suite.py` | 310 passed, exit 0 |
| Grounding rejects an invented figure | in the suite output, Objective 3 | `grounding_probe_rejects_invented_figure: True` |
| Weights respond to error | in the suite output, Objective 4 | `0.5/0.5 → 0.965/0.035` |
| Placebo gate withholds unvalidated edges | `curl localhost:8000/v1/spillover/status` | `placebo_verdict: FAIL`, `actionable_edges: 0` |
| A brief is grounded | `curl localhost:8000/v1/intelligence/brief/tomato/bangalore_apmc` | `grounded: true`, 4 cited factors |
| The evidence behind a brief | `curl localhost:8000/v1/intelligence/evidence/tomato/bangalore_apmc` | the exact bundle the provider saw |
| Phase 1 → Phase 2 integration | `python scripts/verify_phase2_integration.py` | 75/75 |
