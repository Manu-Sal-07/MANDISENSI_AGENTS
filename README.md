# MandiSense AI

Decision support for small farmers and traders in the Bengaluru–Kolar belt of Karnataka, built on real Agmarknet mandi prices
and arrivals (January 2021 – October 2026). It answers two questions with evidence attached:

* **Farmers:** *Where and on which day should I sell this load, and what is the least I can count on?* The answer is the
  market and holding period with the best expected **net** revenue after transport, fees and spoilage, with a revenue floor that
  held in past tests, the chance each mandi is open that day, and plain-language reasons in English, Kannada and Hindi.
* **Traders:** *Where is supply unusual, which links between crops have evidence, and how far can this forecast be trusted?* Thirteen
  desk tools show spreads, the full market-choice grid, supply shocks, volatility regimes, historical analogues, scenarios,
  forward pricing, position risk and an audit of the forecasting methods, each with its evidence tier and limits.

The project's position is that a recommendation is only as good as the evidence behind it, so every number the application shows
traces to a held-out test, and claims that did not survive testing are reported as such (see [What did not work](#what-did-not-work)).

## Results in brief

All figures are out of sample (nested walk-forward blocks); full tables, intervals and protocol are in
[`research/docs/RESULTS.md`](research/docs/RESULTS.md) and [`research/docs/METHODOLOGY.md`](research/docs/METHODOLOGY.md).

| Question | Finding |
|---|---|
| Does training on what a farmer **actually received** (including a wasted trip to a silent mandi) beat training on observed prices? | **Yes.** About Rs 123 per quintal less regret on the same network (95% CI −165 to −87, Holm p < 0.0001); the gain appears in every outer fold and for every farmer origin. |
| Is the revenue floor honest? | **Yes.** The adaptive conformal floor was violated 4.6 / 10.6 / 23.3% of the time at stated levels of 5 / 10 / 20%; a naive Gaussian floor was violated 27–35% against a 10% target. |
| Do published decompose-then-forecast hybrids (STL, VMD) hold up? | **No.** They show +17 to +70% skill over a random walk under the published protocol and −15 to 0% once the decomposition may not see the future, a gap of 30–72 points. |
| How accurate are price forecasts? | **Barely better than "no change"**: +0.6 to +0.8% mean-absolute-error skill on mandi-level series at 3–7 days and +3 to 4% on district-level series. They are used for risk bands and direction, not as price promises. |

## What did not work

Reported in full in the documents named, because a negative result bounds what the data can support:

* The SPO+ decision loss, a reporting-probability head and tuning on decision regret did not beat the plain loss (`research/docs/RESULTS.md` §2).
* A mandi's neighbours' silence adds no information beyond its own reporting history (RESULTS §3).
* The supply-shock event study found no reliable own-crop price response: of 30 tests, 0 robust and 5 suggestive; of 40 cross-commodity
  links, 0 robust and 6 suggestive. The farmer app therefore makes no claim that arrivals will move a price ([`docs/SHOCK_STUDY.md`](docs/SHOCK_STUDY.md)).
* A four-agent specialist council, fused by weights learned inside each fold, is not significantly better than the single served
  model, so it is shown but not promoted ([`docs/AGENT_COUNCIL.md`](docs/AGENT_COUNCIL.md)).

## Quick start

Requirements: Python 3.11+ (tests were run on 3.12), Node 20+ (22 recommended), and optionally Chrome for the UI smoke test.

```bash
# 1. Backend
python -m venv ms_env
ms_env\Scripts\activate            # Windows;  source ms_env/bin/activate  on Linux/macOS
pip install -r requirements.lock   # the exact versions the tests ran on  (or: pip install -e .)
copy .env.example .env             # Linux/macOS: cp .env.example .env   (every key is optional)
python -m uvicorn api.main:app --port 8000        # http://localhost:8000/docs

# 2. Frontend (second terminal)
cd frontend
npm ci
npm run dev                        # http://localhost:3000
```

The trained artefacts and the data panels are in the repository, so the application runs immediately. The cognition states
(`/v1/cognition/*`) are seeded automatically at start-up from the validated forecasts.

### Rebuild everything from the raw exports

```bash
python scripts/pipeline.py --list          # the stages, and what each reads and writes
python scripts/pipeline.py                 # data -> forecasts -> market choice -> shocks -> spillover -> council -> evidence -> tests
python scripts/pipeline.py --only shock    # one stage
python scripts/pipeline.py --with-research # also re-run the full research experiments (hours)
```

### Check that it works

```bash
python -m pytest mandisense_ai -q          # 640+ application tests, no network or API key needed
cd frontend && npm test && npx tsc --noEmit && npx eslint . --quiet
python scripts/smoke_ui.py                 # with both servers running: 25 endpoints and 27 pages, in headless Chrome
cd research && python -m pytest            # 57 tests for the research package (its own requirements)
```

## Layout

```
api/                  FastAPI app (api/main.py) and its routers: market-choice, shock, council, cognition, chat, ...
mandisense_ai/
  farmer/             the farmer data world: registry, district and mandi panels, transmission, sell plans
  forecasting/        the served forecaster (features, walk-forward training, conformal bands, store) and the agent council
  market_choice/      where-and-when-to-sell engine: realised-outcome labels, revenue floor, backtest
  shock/              arrival-shock event study and the radar served to both audiences
  spillover/          weekly cross-commodity matrix used as AI Brief evidence
  cognition/          per-series state, specialist agents' council and arbitration, built on the forecasts
  intelligence/       AI Brief and the explanation layer (constrained paraphrase + independent judge)
  chat/               farmer and trader assistants with tool calling
  trader/             spreads, volatility, analogues, scenarios, forward price, positions
  core/               orchestrators and the external-factors (weather, news) reader
  models/             trained artefacts and the published forecast store
  data/               panels (parquet) and the Agmarknet source exports
  tests/              application tests
frontend/             Next.js app: farmer surface (/, /sell-plan, /tools, ...) and trader surface (/trader-tools/*, /terminal, ...)
research/             the paper's code: leakage audit, realised-label learning, conformal floor, statistics; its tests and results
papers/               IEEE Access, CICPS and KSCST sources
datasets/year_data/   the raw Agmarknet exports the research package reads
scripts/              pipeline.py, build_*.py, eval_*.py, run_nightly_job.py, smoke_ui.py
docs/                 architecture, tool choices, evaluations, deployment notes
```

## Data and provenance

Prices and arrivals are public Agmarknet reports (agmarknet.gov.in) for Bengaluru, Bengaluru Rural, Bengaluru South, Chikkaballapur and
Kolar districts: a district-level history from January 2021 and per-mandi daily reports. Nothing is imputed: a mandi that did not
report on a day has no row, and the models are trained on that fact. Synthetic data was removed from the project; the history of this
is in the commit log. Raw exports are in `datasets/year_data/` and `mandisense_ai/data/farmer/source/`.

## Documentation

| Document | What it covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Data flow, components, how an answer is produced, where the evidence enters |
| [`docs/TOOL_CHOICES.md`](docs/TOOL_CHOICES.md) | Every framework, library and method choice, against the alternatives considered |
| [`docs/SHOCK_STUDY.md`](docs/SHOCK_STUDY.md) | Every supply-shock test, with intervals, placebo and Holm p-values, and detectable effect sizes |
| [`docs/AGENT_COUNCIL.md`](docs/AGENT_COUNCIL.md) | The specialist-agent ensemble and why it is not promoted |
| [`docs/LLM_EVALUATION.md`](docs/LLM_EVALUATION.md) | Measured faithfulness of the language-model explanations |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Workflow, conventions, and the contribution record |
| [`docs/LANGUAGE_REVIEW.md`](docs/LANGUAGE_REVIEW.md) | The Kannada and Hindi strings awaiting native-speaker review |
| [`research/README.md`](research/README.md) | The research package |

## Limits

* Forecast skill is small; price forecasts are intervals and directions, not promises.
* The revenue floor is a statement about past tests of the method, not a guarantee on any single sale.
* The data covers five crops in one region; results are not claimed elsewhere.
* The model-written wording of explanations is checked for meaning by a second model; Kannada and Hindi copy has not yet had a native-speaker review.
* The language-model layer is optional. With no key every explanation is written by rules from the same facts.
