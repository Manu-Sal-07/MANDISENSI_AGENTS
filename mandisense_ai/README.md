# `mandisense_ai`: the Python package

The repository [README](../README.md) explains what the system does and how to run it; [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) shows how
the pieces connect. This file is a map of the modules.

| Module | Responsibility | Entry points |
|---|---|---|
| `farmer/` | The data world: registry of districts and mandis, the district, mandi and market panels built from Agmarknet exports, sell plans, transmission tests, farmer-facing readings | `world.py`, `registry.py`, `transmission.py` |
| `forecasting/` | The served forecaster: causal features, walk-forward training, conformal bands, forecast store, scheduler; the agent council and its traced run | `train.py`, `features.py`, `service.py`, `council.py`, `trace.py`, `naming.py` (one id per mandi) |
| `market_choice/` | Where-and-when-to-sell: realised-outcome labels, economics, conformal floor, backtest, service | `engine.py`, `econ.py`, `conformal.py`, `service.py` |
| `shock/` | Arrival-shock event study and the radar both audiences read | `study.py`, `service.py` |
| `spillover/` | Weekly cross-commodity spillover matrix (evidence for the AI Brief) | `build.py`, `service.py` |
| `cognition/` | Per-series market state from a council of agents, arbitration, state store, orchestration | `engine.py`, `forecast_engine.py`, `state_store.py` |
| `intelligence/` | AI Brief and the explanation layer (code-written sentences, paraphrase, independent judge) | `explain.py`, `service.py`, `providers.py` |
| `chat/` | Farmer and trader assistants with tool calling; the tools wrap the same functions the API serves | `engine.py`, `tools.py`, `providers.py` |
| `trader/` | Spreads, gap arbitrage, volatility regime, analogues, scenarios, forward price, position risk | one module per tool |
| `core/` | Query/decision orchestrators and the external-factors (weather, news) reader | `orchestrator/`, `agents/external_factors_agent/` |
| `services/` | Read-side data services for charts and candles over the market panel | `candle_data_service.py` |
| `lib/`, `utils/`, `config/`, `db/` | Caching, logging, settings, optional Postgres access | |
| `data/`, `models/` | Panels, source exports and trained artefacts (produced by `scripts/`, not edited by hand) | |
| `tests/` | Application tests (no network or API key needed) | `python -m pytest mandisense_ai -q` |
