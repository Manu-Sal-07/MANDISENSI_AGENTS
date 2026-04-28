# MandiSense AI — Progress Log

---

## Update: 2026-04-24 — Multi-Model Ensemble Pool (Steps 1–5)

### Overview
Replaced the single-XGBoost model in `ArrivalVolumeAgent` and expanded the
`TieredModelPipeline` for `SeasonalityAgent` to a full 8–9 model ensemble pool.
Both agents now run `TimeSeriesSplit` walk-forward CV on all models, compute
inverse-MAPE weights, and produce a weighted ensemble prediction.  The
`model_contributions` dict in `AgentOutput` reflects real per-model weights.

---

### Step 1 — Seasonality Models Added

| Model | File Path | Notes |
|---|---|---|
| STL + Linear Regression | `mandisense_ai/core/agents/seasonality/models/stl_linear.py` | De-seasonalises with STL; fits LR on residuals; adds seasonal offset at predict |
| RandomForestRegressor | `mandisense_ai/core/agents/seasonality/models/random_forest.py` | 200 trees, depth=10, n_jobs=-1 |
| XGBoostRegressor | `mandisense_ai/core/agents/seasonality/models/xgboost_model.py` | Migrated from inline; stochastic subsampling |
| LightGBMRegressor | `mandisense_ai/core/agents/seasonality/models/lightgbm_model.py` | Leaf-wise growth; faster than XGB on sparse data |
| Ridge Regression | `mandisense_ai/core/agents/seasonality/models/ridge_model.py` | Internal StandardScaler; stable on small mandis |
| Lasso Regression | `mandisense_ai/core/agents/seasonality/models/lasso_model.py` | Sparse feature selection; logs n_selected features |
| Moving Average Baseline | `mandisense_ai/core/agents/seasonality/models/moving_average.py` | Trailing 30-day mean; ensemble quality baseline |
| Lag-based Linear Model | `mandisense_ai/core/agents/seasonality/models/lag_linear.py` | Uses ONLY price_lag_* columns; auto-regressive anchor |
| SARIMA (optional 9th) | `mandisense_ai/core/agents/seasonality/models/sarima_model.py` | Weekly-resampled; graceful fallback if statsmodels fails |

**Registry entry point**: `mandisense_ai/core/agents/seasonality/models/__init__.py`
→ `SEASONALITY_MODEL_REGISTRY` dict imported by `TieredModelPipeline`.

**Base interface**: `mandisense_ai/core/agents/seasonality/models/base.py`
→ `BaseSeasonalityModel(ABC)` with `fit(X, y)` and `predict(X)` abstract methods.

---

### Step 2 — Arrival Models Added

| Model | File Path | Notes |
|---|---|---|
| XGBoostRegressor | `mandisense_ai/core/agents/arrival/models/xgboost_model.py` | Was the single model; now 1-of-8 with fractional weight |
| RandomForestRegressor | `mandisense_ai/core/agents/arrival/models/random_forest.py` | Robust to supply-shock outliers via bagging |
| Elasticity-based Linear | `mandisense_ai/core/agents/arrival/models/elasticity_linear.py` | Full feature set; interpretable coefficient |
| Ridge Regression | `mandisense_ai/core/agents/arrival/models/ridge_model.py` | L2 regularisation; handles collinear arrival features |
| Lasso Regression | `mandisense_ai/core/agents/arrival/models/lasso_model.py` | L1 feature selection; regime-resilient |
| GradientBoostingRegressor | `mandisense_ai/core/agents/arrival/models/gradient_boosting.py` | `loss='huber'`; robust to price-shock outliers |
| Simple Baseline (mean/lag) | `mandisense_ai/core/agents/arrival/models/simple_baseline.py` | Selects best of trailing-mean vs lag-1 at fit time |
| Polynomial Regression | `mandisense_ai/core/agents/arrival/models/polynomial_model.py` | Degree-2 + Ridge; captures non-linear elasticity |

**Registry entry point**: `mandisense_ai/core/agents/arrival/models/__init__.py`
→ `ARRIVAL_MODEL_REGISTRY` dict imported by `ArrivalModelPipeline`.

**Base interface**: `mandisense_ai/core/agents/arrival/models/base.py`
→ `BaseArrivalModel(ABC)` with `fit(X, y)` and `predict(X)` abstract methods.

---

### Step 3 — Feature Consistency

- **All arrival models** receive the same 12-column feature set defined in
  `ArrivalVolumeAgent.train_and_predict()`:
  ```
  arrivals_7d_mean, arrivals_30d_mean, arrival_deviation_pct,
  arrival_yoy_deviation_pct, consecutive_decline_days, supply_momentum_slope,
  arrivals_lag_1, arrivals_lag_7, price_lag_1, price_lag_7,
  rolling_elasticity_30d, is_festival
  ```
- **All seasonality models** receive the same 10-column feature set defined in
  `SeasonalityAgent.execute()` (unchanged from prior implementation).
- `LagLinearModel` (seasonality) deliberately uses only `price_lag_*` columns
  for ensemble diversity — this is intentional, not a bug.
- Feature engineering happens **before** the model pipeline call; no model
  touches raw data directly.

---

### Step 4 — Training Strategy

- **Walk-Forward CV**: `TimeSeriesSplit(n_splits=5)` used in both pipelines.
- **No data leakage**: only lagged features are used as inputs; target is
  always future-facing (`price.shift(-7)` for arrival, `modal_price` future
  rolling mean for seasonality).
- **Full-data refit**: after CV ranking, top models are refitted on the entire
  training set for best prediction at inference time.
- **NaN / Inf guard**: predictions that contain NaN or Inf are replaced with
  `y_train.mean()` per fold to prevent pipeline crashes.
- **Per-fold deepcopy**: each CV fold gets a fresh model instance to prevent
  state leakage across folds.

---

### Files Modified

| File | Change |
|---|---|
| `mandisense_ai/core/agents/seasonality_models.py` | Complete rewrite: now delegates to `SEASONALITY_MODEL_REGISTRY`; uses 5-fold TimeSeriesSplit; adds NaN guards; full-data refit |
| `mandisense_ai/core/agents/arrival_volume_agent.py` | Complete rewrite: replaced `GridSearchCV(XGBRegressor)` with `ArrivalModelPipeline`; `model_contributions` now shows all 8 weights |

### New Files Created

```
mandisense_ai/core/agents/seasonality/
├── __init__.py
└── models/
    ├── __init__.py          ← SEASONALITY_MODEL_REGISTRY
    ├── base.py              ← BaseSeasonalityModel (ABC)
    ├── stl_linear.py
    ├── random_forest.py
    ├── xgboost_model.py
    ├── lightgbm_model.py
    ├── ridge_model.py
    ├── lasso_model.py
    ├── moving_average.py
    ├── lag_linear.py
    └── sarima_model.py      ← optional 9th model

mandisense_ai/core/agents/arrival/
├── __init__.py
└── models/
    ├── __init__.py          ← ARRIVAL_MODEL_REGISTRY
    ├── base.py              ← BaseArrivalModel (ABC)
    ├── xgboost_model.py
    ├── random_forest.py
    ├── elasticity_linear.py
    ├── ridge_model.py
    ├── lasso_model.py
    ├── gradient_boosting.py
    ├── simple_baseline.py
    └── polynomial_model.py  ← optional 8th model
```

---

### Assumptions Made

1. **SARIMA weekly resample**: SARIMA is fitted on weekly-resampled prices to
   keep training time < 30s per commodity.  Daily SARIMA is feasible but
   requires order selection (e.g., auto_arima) which adds > 5 min per run.

2. **PolynomialRegression degree cap**: Capped at degree=2 to prevent
   combinatorial feature explosion (~12 arrival features → 90 poly features at
   degree 2 vs 360 at degree 3).  Ridge regularisation is applied on top.

3. **GradientBoosting Huber loss**: `loss='huber'` is used instead of
   `loss='squared_error'` to handle genuine supply-shock outliers in arrival
   data.  The `alpha` parameter defaults to sklearn's 0.9 (90th-percentile
   threshold).

4. **LagLinearModel feature subset**: Uses only `price_lag_*` columns
   intentionally to provide auto-regressive diversity vs tree-based models.
   If no lag columns exist, it falls back to all columns with a warning.

5. **No new data sources**: All models consume the same processed parquet files
   from `DataRepository.get_processed_data()`.  No new ingestion pipelines were
   added.

6. **Backward compatibility**: `AgentOutput` schema is unchanged.  The only
   visible difference to downstream consumers is that `model_contributions`
   now contains up to 8 entries instead of `{"XGBoost": 1.0}`.

---

### Step 5 & 6 — Internal Ensemble Engine (`AgentEnsemble`) & Logging

- Created `AgentEnsemble` in `ensemble/agent_ensemble.py` as the canonical internal ensemble engine.
- Replaced the duplicate implementations in `TieredModelPipeline` and `ArrivalModelPipeline`.
- **Validation & Weighting**:
  - Automatically performs `TimeSeriesSplit(n_splits=5)` walk-forward cross-validation.
  - Computes `weight_i = (1 / error_i) / Σ (1 / error_j)` based on inverse-MAPE.
  - Removes models with weight < 1% automatically.
- **Agent Integration**:
  - `ArrivalVolumeAgent` directly instantiates `AgentEnsemble` with the `ARRIVAL_MODEL_REGISTRY`.
  - `SeasonalityAgent` continues using `TieredModelPipeline` as a thin backward-compatible wrapper that delegates to `AgentEnsemble`.
- **Logging Injection**:
  - `AgentEnsemble.get_ensemble_log()` packages model predictions, individual weights, CV fold errors, and execution metadata.
  - Both agents now safely inject `ensemble_log` directly into `AgentOutput.metadata`.

### Step 7 — Dynamic Weighting & Regime Detection

- **Storage System (`FeedbackStore`)**:
  - Implemented `ensemble/feedback_store.py` to persist predictions, actuals, and errors in JSONL format.
  - Added method to compute 30-day rolling MAPE per model for dynamic adjustments.
- **Regime Logic (`RegimeDetector`)**:
  - Created `ensemble/regime_detector.py` to identify:
    - High Volatility (using std dev of daily returns).
    - Festival Period (using `is_festival` flag proximity).
    - Supply Shock (using massive deviations from 30-day rolling average arrivals).
- **Dynamic Adjustments (`DynamicWeighter`)**:
  - Created `ensemble/dynamic_weighter.py` to apply EMA smoothing over historical weights (`alpha=0.3`).
  - Added 1.3x weight boosts to specialized models depending on the active regime:
    - `festival` → Boosts `STLLinearRegression`, `SARIMA`, `PolynomialRegression`.
    - `supply_shock` → Boosts `GradientBoosting`, `RandomForest`, `XGBoost`.
- **Integration**:
  - Wired into `SeasonalityAgent` and `ArrivalVolumeAgent` directly prior to making the final ensemble prediction.
  - Agents now automatically serialize predictions and metadata back to `FeedbackStore`.

---

### Step 8 — Output Standardization & Meta-Ensemble Prep

- **Standardized `AgentOutput` Schema**:
  - Simplified the core schema to exactly 5 strictly typed properties (`agent_name`, `prediction`, `confidence`, `metadata`, `model_breakdown`).
  - Purged bloated, agent-specific fields from the root schema.
  - Relocated all domain-specific metrics (e.g. `supply_stress_score`, `P_positive`, `festival_adjustment`) natively into the dynamic `metadata` dictionary.
- **Consistent Model Tracing (`model_breakdown`)**:
  - Built out the `model_breakdown` block capturing per-model predictions and weights dynamically from the `AgentEnsemble.last_predictions`.
- **Integration**:
  - Both `SeasonalityAgent` and `ArrivalVolumeAgent` have been refactored to conform strictly to this unified schema, guaranteeing that the upcoming Meta-Ensemble layer can ingest output payloads uniformly.

---

### Next Steps (Phase 3 — Orchestration & Meta-Ensemble)

- [ ] Connect `FeedbackStore` actuals updating to the daily data ingestion pipeline.
- [ ] Build Layer 2 (Meta-Ensemble) to blend standardized outputs from Seasonality, Arrival, and External Factors agents.
- [ ] Implement CUSUM-based severe regime break detection for emergency re-training.

## 📌 Context Extraction Completed

- Extracted full system architecture
- Documented Seasonality Agent
- Documented Arrival Volume Agent
- Documented External Factors Agent
- Captured model-level and feature-level details
- Mapped codebase structure
- Identified current implementation boundaries

Status: ✅ System context ready for next development phase

## 📌 System Context (Text-Based) Extracted

- Converted full system into readable technical documentation
- Documented all three agents (Seasonality, Arrival, External)
- Captured internal logic in text form
- Defined outputs of each agent
- Explained system flow and current state

Status: ✅ Ready for next development phase

## 📌 System Handoff Documentation Created

- Documented complete multi-agent system
- Explained Seasonality, Arrival, and External agents
- Captured modeling approaches and internal logic
- Explained outputs and system flow

Status: ✅ Ready for next development phase
