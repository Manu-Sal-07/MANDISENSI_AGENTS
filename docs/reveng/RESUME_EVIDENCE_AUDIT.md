# MandiSense AI — Resume Evidence Audit

Compiled from three independent forensic sub-audits (metrics/production, dataset/features, model architecture/ensemble) run against `D:\BMS COLL\PROJECT\MS-AI`. Rules followed: no invented/estimated/extrapolated numbers; proposal/README/comment claims are never treated as achieved results; every number is traced to file/function/line; disagreements between sub-audits are reported, not resolved.

**Structural fact that governs the whole audit:** the codebase contains **3–4 parallel implementations** of almost every component (seasonality training, arrival training, dataset versions v1–v4, two evaluation-metric conventions). The "live" path for each agent was identified by tracing actual call graphs from `PredictionController.predict()`; everything else is flagged **implemented-but-not-wired**.

---

## A. FORECASTING PERFORMANCE

| # | Metric | Value | Model/ensemble | Dataset | Methodology | Evidence | File | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | MAPE (per commodity, single split) | garlic 5.32%, ginger 5.32%, onion 5.41%, potato 5.22%, tomato 5.37% | XGBoost, per-commodity, **1-day-ahead** price target | `data/processed/v4/*.csv` (5 commodities × 15 Karnataka mandis, 2023-01-02→2026-05-02) | Single chronological train/val split (`is_valid_training==1` vs `split=='val'`) | `agent_training_report.csv` | `mandisense_ai/logs/agent_training_report.csv`; script `core/agents/training_pipeline.py` L58-109 | **MEASURED** |
| 2 | MAPE (per commodity×mandi, 75 rows) | Model 4.00–5.14%; lag-1 baseline 5.23–7.23% | XGBoost, per commodity×mandi | Same v4 dataset | **Walk-forward CV**, 3 windows (`WF_WINDOWS`: 2024-06-30→2024-12-31, 2024-12-31→2025-06-30, 2025-06-30→2026-01-31), 1-day-ahead target | `per_mandi_metrics_v2.csv` (75 rows) | `mandisense_ai/logs/per_mandi_metrics_v2.csv`; script `training_pipeline_v2.py` | **MEASURED** |
| 3 | RMSE (per commodity×mandi) | e.g. garlic/anekal 431.57, tomato/kanakapura 79.73 (units = raw price, not %) | Same as #2 | Same | Same | Same file | Same | **MEASURED** |
| 4 | Improvement vs lag-1 baseline | 21.2%–34.5% per pair (`improvement_pct` column, e.g. 30.65%, 32.71%, 23.4% sampled) | XGBoost vs lag-1 naive | Same | Same split, same horizon — directly comparable | Same file | Same | **MEASURED** (see Section B) |
| 5 | Trend-direction accuracy | 53.3% (`trend_accuracy: 0.533`) | `CognitionBacktester` rule engine, not the ML ensemble | tomato/kolar_apmc only, 15 days, 2024-01-01→2024-01-15 | Historical replay, ±2% trend band | `tomato_kolar_apmc_replay.json` | `mandisense_ai/evaluation/results/tomato_kolar_apmc_replay.json` | **MEASURED**, single mandi/15 days only |
| 6 | `avg_confidence` = 0.95 alongside #5 | 0.95 | same | same | — | same file — every one of 15 records has identical confidence=0.95 | same | **Flag: constant, not computed** |
| 7 | `directive_reliability` = 0.587 | 0.587 | same | same | `round(accuracy * 1.1, 3)` — inline comment "Heuristic for now" | `backtester.py` L99 | `mandisense_ai/evaluation/backtester.py:99` | **NOT a measured metric** — fixed multiplier on #5 |
| 8 | Ensemble CV score, "MAPE" regime | avg_MAPE up to ~1.3e18 (nonsensical) | AgentEnsemble, all 8 arrival models | Arrival training data | TimeSeriesSplit, 5 folds | Log lines 2026-05-02T18:26–19:20 | `mandisense_ai/logs/mandisense.log` | **MEASURED but broken** — near-zero-denominator MAPE explosion; collapsed ensemble weight to 100% SimpleBaseline |
| 9 | Ensemble CV score, "MAE" regime (post-fix) | XGBoost 127.19, RandomForest 151.69, GradientBoosting 157.03, Ridge 179.34, Lasso 179.39, ElasticityLinear 179.72, SimpleBaseline 63.40, PolynomialRegression 462.21 | AgentEnsemble, 8 arrival models | Same | TimeSeriesSplit, 5 folds, **MAE substituted for MAPE** (explicit code comment explaining why) | Log lines from 2026-05-02T19:23 onward | `mandisense_ai/logs/mandisense.log`; `ensemble/agent_ensemble.py:158-161` | **MEASURED** — units not documented (not a %) |
| 10 | Final blended ensemble weights | XGBoost 14.73%, RandomForest 14.53%, GradientBoosting 14.37%, SimpleBaseline 14.31%, Lasso 11.87%, Ridge 11.71%, ElasticityLinear 11.71%, PolynomialRegression 6.76% | Arrival AgentEnsemble, inverse-MAE weighting | Same | — | `"[AgentEnsemble] Final weights (8 models): ..."` | `mandisense_ai/logs/mandisense.log` (repeated 2026-05-02T19:23 → 2026-05-03T07:25) | **MEASURED** |
| 11 | External Factors per-agent metric | **NOT FOUND** as a real evaluated metric | — | — | `performance_tracker.py::calculate_metrics()` exists but is never called anywhere in the codebase | grep found zero call sites | `external_factors_agent/adaptive/performance_tracker.py` | **IMPLEMENTED, never run — NOT FOUND** |
| 12 | External Factors live values | `external_impact` mostly 0.0–0.0008, `external_confidence` mostly 0.0–0.075 | — | 81/66-record prediction logs | — | `meta_predictions.jsonl` records | `mandisense_ai/data/ensemble/meta_predictions.jsonl` | Confirms External Factors contributes **near-zero/neutral** signal in the great majority of logged predictions — do not treat as a real evaluated external-factor performance number |
| 13 | Seasonality/Arrival final ensemble metric | **NOT FOUND as a single reported number** — no artifact found stating "final ensemble MAPE = X%" for the production meta-ensemble (Phase 1 fuse) as a whole | — | — | — | — | — | **NOT FOUND** |
| 14 | Number of predictions evaluated (with realized outcome) | **1** (out of 21 in `prediction_history.jsonl`); **0** (out of 81, and separately 0 of 66, in `meta_predictions.jsonl`) | — | — | — | Exact record: Onion/Lasalgaon, ArrivalVolume, XGBoost, prediction 1200.0, actual 1250.0, error 0.04 | `mandisense_ai/data/ensemble/prediction_history.jsonl` | **MEASURED** (n=1) |
| 15 | Regime timeline (GARCH/HMM) | State 1 "Stable" 190 days, mean vol 5.439%; State 4 "Crisis" 363 days, mean vol 9.952%; 1,140 total trading days; 30 warning alerts (2σ), 0 critical (3σ) | `GARCHVolatilityEstimator` + `HMMRegimeClassifier` | tomato/kolar only (`data/raw/v1/tomato/kolar.csv`) | Real model fit, not synthetic | `regime_timeline_stats.tex` traced to `scratch/generate_regime_timeline.py` | `artifacts/evaluation/regime_timeline_stats.tex` | **MEASURED**, single commodity/mandi, and produced by an offline script outside the production pipeline |

**Disagreement flagged between sub-audits:** the model-architecture audit's summary table states the 8-model seasonality multi-horizon ensemble was "evaluated (TimeSeriesSplit MAPE/MAE/RMSE/F1 per horizon, saved to `fold_metrics.json`/`metrics_per_horizon.json`)." The metrics/production audit found **no such per-horizon (3d/5d/7d/15d/30d) evaluation file in the live model tree** and states the 30-day/7-day horizons are implemented but not evaluated. Reconciling the raw evidence: `fold_metrics.json` files **do exist**, but only inside `models_backup_20260503_1905\{arrival,seasonality}\...\` — the **stale, superseded backup tree**, one generation older than the currently-loaded `mandisense_ai\models\` tree. So: **per-horizon fold metrics were computed at least once (2026-05-03), but that evidence lives in a backup directory that is not the one currently read by `settings.paths.models_dir`, and no equivalent file was found in the live model tree.** Treat multi-horizon (3/5/7/15/30-day) evaluation as **CONFIGURED/historically MEASURED-in-a-superseded-run**, not as a currently-reproducible measured result.

### Fabricated/synthetic "evaluation" artifacts (do not cite as measured results)

| File | Generator | Why it's not real evaluation evidence |
|---|---|---|
| `artifacts/evaluation/system_latency_stats.tex` | `scratch/generate_system_latency.py` | Latencies drawn from `np.random.normal(...)`; the four headline latency numbers are hardcoded strings in an f-string, not computed at all; "50% cache hit ratio" is `2500/5000` from the chosen sample sizes, not a measured Redis stat |
| `artifacts/evaluation/decision_performance_stats.tex` | `scratch/generate_decision_performance.py` | Predicted labels are set equal to ground truth, then 18% are randomly flipped (`np.random.seed(42)`); confidence scores are drawn from `np.random.uniform(...)`, not from any model. Precision/recall/F1/Cohen's κ = 0.5533 describe this synthetic noise injection, not MandiSense's decision engine |
| `artifacts/evaluation/agent_contribution_stats.tex` | `scratch/generate_agent_contribution.py` | Starts from real `meta_predictions.jsonl` (66/81 records) but explicitly injects synthetic rows (`np.random.seed(42/43/44)`) to "populate insufficient regimes" — mixed real+fabricated, not a clean measurement |
| `artifacts/evaluation/model_comparison.tex` | `mandisense_ai/evaluation/model_comparison.py` | "MandiSense AI (Ensemble)" column is a fixed hand-weighted blend (`0.2*ARIMA + 0.4*RF + 0.4*XGB`), **not** the production `agent_ensemble.py`/`learned_ensemble.py`; all MAPE values >100% (same denominator-explosion bug as row 8 above); MandiSense's own MAE/RMSE (7.64/10.00) is actually *worse* than plain ARIMA (7.42/9.56) in this table |
| `artifacts/evaluation/statistical_validation.tex` | `mandisense_ai/evaluation/statistical_validation.py` | Real paired t-test, but "MandiSense AI approximation" = a plain `Ridge(alpha=1.0)`, not the production system. Baseline MAE 12.00% vs Ridge MAE 7.31%, improvement 39.0%, p=2.45e-85 — **MEASURED, but for a stand-in model**, single commodity/mandi (`v1/tomato/kolar.csv`) |
| `artifacts/evaluation/cross_commodity_stats.tex`, `shap_stats.tex` | Not located | Generator scripts producing these exact numbers were not found/verified — **provenance unconfirmed**, do not cite |

---

## B. BASELINE COMPARISON

The only baseline comparison that is (a) explicitly measured, (b) on the same dataset, (c) same horizon, and (d) same methodology as the model it's compared to:

| Baseline | Baseline metric | Model metric | Absolute improvement | % improvement | Methodology | Dataset/period |
|---|---|---|---|---|---|---|
| Lag-1 naive forecast (`baseline_pred = price_lag_1`) | MAPE 5.23%–7.23% (75 commodity×mandi rows) | XGBoost MAPE 4.00%–5.14% | Row-dependent (e.g. 6.9481% → 4.4387% for garlic/kolar_apmc = 2.51pp) | **21.2%–34.5%** (per-row `improvement_pct` column; individual examples: 30.65%, 32.71%, 23.4%) | Walk-forward CV, 3 windows, 1-day-ahead target, computed on same validation slice | `data/processed/v4/*.csv`, 5 commodities × 15 Karnataka mandis, 2023-01-02→2026-05-02 |

Formula used by the codebase itself (matches the audit's prescribed formula): `improvement_pct = ((baseline_MAPE − model_MAPE) / baseline_MAPE) × 100`, verified consistent with the file's own `improvement_pct` column values, e.g. `(6.9481−4.4387)/6.9481×100 = 36.1%` — **note this doesn't exactly match the file's own reported 32.71% for that row**, a discrepancy in the source file itself, not something this audit introduces. Because the full 75-row file wasn't quoted verbatim by the sub-audit, only 3 sample rows plus the stated aggregate range (21.2–34.5%) are available — **do not cite an average percentage improvement; only the range is evidenced.**

Other baseline-shaped comparisons found, **not usable for a clean improvement calculation**:
- `statistical_validation.tex`: persistence baseline 12.00% MAE vs Ridge stand-in 7.31% MAE (39.0% improvement, p=2.45e-85) — real t-test, but the "model" is a plain Ridge regression stand-in, not the production ensemble, and it's single-mandi (tomato/kolar) only. **Do not present as "MandiSense ensemble beats baseline by 39%."**
- `model_comparison.tex`: shows the (illustrative, non-production) MandiSense blend performing *worse* than ARIMA on MAE/RMSE — contradicts a "we beat baselines" narrative and should not be cited either way given the MAPE-explosion bug affecting all values in that table.
- No moving-average, trailing-mean, or seasonal-naive baseline comparison was found anywhere with a matching methodology to a production metric.

---

## C. FORECAST HORIZONS

| Horizon | Target variable | Implemented? | Actually evaluated? | Evidence | Status |
|---|---|---|---|---|---|
| 1-day | `target_price = groupby(mandi).price.shift(-1)` | Yes | **Yes** — this is the only horizon with clean, reproducible, live-tree MEASURED metrics (Section A rows 1–4) | `training_pipeline.py:58`, `training_pipeline_v2.py:64`; `agent_training_report.csv`, `per_mandi_metrics_v2.csv` | **MEASURED** |
| 3-day | `target_3d = shift(-3)` pct change | Yes, in `multi_horizon.py` | Only in the **stale backup tree** (`models_backup_20260503_1905`, `fold_metrics.json`), not the live model tree | `seasonality/multi_horizon.py` L255-260 | **CONFIGURED / historically measured in a superseded run** |
| 5-day | same pattern | Yes | Same caveat as 3-day | same file | **CONFIGURED / historically measured in a superseded run** |
| 7-day | `target_7d_pct` (arrival) / `target_7d` (seasonality parquet) | Yes — this is also the Phase-2 meta-ensemble's nominal horizon (`meta_predictions.jsonl` field `actual_7d_change`) | **No live-tree evaluation found**; 0 of 81/66 `meta_predictions.jsonl` records have `actual_7d_change` populated, so the 7-day meta-ensemble horizon has never been scored against a realized outcome | `arrival/training/train_arrival_models.py:66`; `meta_predictions.jsonl` | **IMPLEMENTED, NOT evaluated in production** |
| 15-day | `target_15d` | Yes, in `multi_horizon.py` | Backup-tree-only, as above | same | **CONFIGURED / historically measured in a superseded run** |
| 30-day | `target_30d`; also `seasonality_pred_30d` field logged in `meta_predictions.jsonl` | Yes | Backup-tree-only for fold metrics; live predictions are logged but have no realized-outcome comparison | same | **CONFIGURED / IMPLEMENTED, NOT evaluated in production** |

---

## D. DATASET SCALE

### Configured/support capacity vs. actually evaluated

| Dataset tree | Rows | Commodities | Mandis | Date range | Role |
|---|---|---|---|---|---|
| `mandisense_ai/data/raw/*.csv` (Agmarknet single-mandi scrape) | 12,445 data rows total (1,720+1,787+2,442+2,899+3,597) | dry_chillies (Guntur), garlic (Neemuch), onion (Lasalgaon), potato (Agra), tomato (Kolar) — 5 real commodity×mandi pairs, 1 mandi each | Guntur (AP), Neemuch (MP), Lasalgaon (MH), Agra (UP), Kolar (KA) | 2015-01-01 → 2025-03-09 (~10.2 years) | **Actually evaluated** — feeds `data/processed/{commodity}/` splits |
| `festival_calendar.csv` | 132 data rows | all | — | 2015-01-01 → 2025-12-25 | Real festival-window reference data |
| `data/raw/v1/{commodity}/{mandi}.csv` | 86,806 total (non-uniform, 17,322–17,420/commodity) | garlic, ginger, onion, potato, tomato | 15 Karnataka APMCs (anekal, bangalore, bangarpet, channapatna, chickballapur, doddaballapur, hoskote, kanakapura, kolar, kunigal, magadi, malur, nelamangala, ramanagara, sidlaghatta) | 2023-01-01 → 2026-05-03 | Superseded by v2/v3 |
| `data/raw/v2/`, `v3/` | 91,275 each (18,255 uniform rows/commodity × 5) | same 5 | same 15 (with `_apmc`/`_yeshwanthpur` suffixes) | 2023-01-02 → 2026-05-02 | v3 adds `is_missing`/`split`/`is_unstable` flags |
| `data/processed/v4/*.csv` | 91,275 (18,255/commodity) | same 5 | same 15 | 2023-01-02 → 2026-05-02 | **Actually evaluated** — this is the exact input to the MEASURED Section A #1/#2 results |

**Flag — likely synthetic/augmented data:** all 15 "mandi" names reused across v1–v4 are Karnataka-region APMCs, applied uniformly to garlic/ginger/onion/potato/tomato regardless of each commodity's real geography (e.g., the real Agmarknet scrape places garlic's actual market in Neemuch, Madhya Pradesh — over 1,500 km from any of the 15 Karnataka mandis used in v1–v4). This is evidence the v1–v4 multi-mandi dataset is a **generated/augmented dataset**, not 15 additional real per-commodity market scrapes. The Section A #1/#2 MEASURED metrics (the strongest numbers in this audit) are computed on this augmented dataset, not on the raw real Agmarknet scrape.

### Train/validation split (`data/processed/{commodity}/`, built from the *real* single-mandi raw CSVs via 80/20 temporal split, `prepare_datasets.py:96-99`)

| Commodity | Train rows | Val rows | Source (two sub-audits, minor ±1 row discrepancy — not resolved) |
|---|---|---|---|
| dry_chillis | 2,940 or 2,941 | 735 or 736 | Discrepancy between sub-audits, likely a header-row counting convention difference |
| garlic | 2,936 or 2,937 | 735 or 736 | same |
| onion | 2,940 or 2,941 | 736 or 737 | same |
| potato | 2,940 or 2,941 | 736 or 737 | same |
| tomato | 2,931 or 2,932 | 733 or 734 | same |

Split ratio confirmed exactly 80.0%/20.0% by index (`split_idx = int(len(df)*0.8)`), not random.

Test set: **NOT FOUND** as a separate third split — only train/val exists in `prepare_datasets.py`; `training_pipeline_v2.py`'s walk-forward windows serve as the closest thing to a held-out evaluation.

### Also present, not used in any traced `.fit()` call

`data/processed/{name}.parquet` + `_features.parquet` (per single-mandi commodity), 88 engineered columns, self-reported row counts 3,563–3,594 per `.metadata.json` sidecars (not independently re-counted — no parquet reader available in the audit environment). **No code path was found loading these particular parquet files into a model training call** — flag as generated-but-unused artifacts.

---

## E. FEATURE ENGINEERING

### Seasonality Agent — 3 parallel implementations, only one reaches the live `.fit()` call

**Live/production (`core/agents/seasonality/multi_horizon.py::SeasonalityMultiHorizonPipeline`), 13 features, traced to `.fit()` at line 434/458/482:**
```
mandi_id, price_lag_1, price_lag_7, price_lag_14, price_mean_7, price_std_7,
price_mean_30, price_std_30, returns, momentum_7d, volatility_7d, month, day_of_week
```
- Lag features: `price_lag_1/7/14`. Rolling stats: `price_mean_7/30`, `price_std_7/30`. Momentum: `momentum_7d`. Volatility: `volatility_7d`. Calendar: `month`, `day_of_week`.
- **Festival/calendar-event features: NOT present.** **Trend/STL-decomposition features: NOT present** in this feature list.
- Scaling: `StandardScaler` inside a `Pipeline`, but only for the linear/ridge/lasso model variants; tree-based models (RF/GB/XGB/LightGBM) get unscaled features. No PCA/dimensionality reduction anywhere in the codebase.

**Secondary implementation (`core/agents/seasonality/train_seasonality.py`):** uses a generic 8-feature set (`mandi_id, lag_1, lag_3, lag_7, lag_14, rolling_mean_7d, rolling_std_7d, arrival_dev_7d`). **STL decomposition is computed (`STL(...).fit()`) but its trend/seasonal/residual outputs are stored only as bundle metadata and never merged into the feature matrix passed to `.fit()`** — a clean "computed but unused" case.

**Third implementation (`core/agents/seasonality_agent.py`):** has a real, working `merge_festivals()` that loads `festival_calendar.csv` and computes genuine festival-window flags/price deltas — but this function is imported by the **Arrival** agent, not called by either seasonality `.fit()` path above. The only Seasonality code with real festival awareness is not wired into seasonality model training.

**Feature count summary:** 13 features (live path, no festival/trend features) / 8 features (secondary path, STL unused) / festival logic exists but orphaned from both.

### Arrival Volume Agent — 3 parallel implementations

**Live/production (`core/agents/arrival/training/train_arrival_models.py` + `arrival_volume_agent.py::build_arrival_features`), 13 features, traced to `.fit()` via `AgentEnsemble.fit()`:**
```
mandi_id, arrivals_7d_mean, arrivals_30d_mean, arrival_deviation_pct, arrival_yoy_deviation_pct,
consecutive_decline_days, supply_momentum_slope, arrivals_lag_1, arrivals_lag_7, price_lag_1,
price_lag_7, rolling_elasticity_30d, is_festival
```
`is_festival` **is genuinely computed** here — `arrival_volume_agent.py` imports and calls `merge_festivals()` (the seasonality-agent function above) before feature construction, so this specific pipeline's festival flag is a real signal.

**Alternate implementation (`core/agents/arrival/multi_horizon.py::ArrivalMultiHorizonPipeline`), 14 features:**
```
arrivals_lag_1, arrivals_lag_7, arrivals_7d_mean, arrivals_30d_mean, arrival_deviation_pct,
arrival_yoy_deviation_pct, supply_momentum, consecutive_decline_days, price_lag_1, price_lag_7,
log_price, log_arrivals, rolling_elasticity_30d, is_festival
```
In **this** implementation `is_festival` is **hardcoded to 0** whenever missing (`if "is_festival" not in data.columns: data["is_festival"] = 0`) with no festival merge performed — **flagged as mock/placeholder** in this specific (backup-tree-associated) path, in direct contrast to the live path above.

**Generic implementation (`core/agents/arrival/train_arrival.py`):** same 8-generic-feature set as Seasonality's secondary implementation, no arrival-specific/elasticity/festival features at all.

- Price-elasticity: `rolling_elasticity_30d` (30-day rolling correlation of log price vs log arrivals) — present in both the live and alternate implementations.
- Supply-stress: `arrival_deviation_pct`, `arrival_yoy_deviation_pct`, `supply_momentum`/`supply_momentum_slope`, `consecutive_decline_days`.
- Scaling: `StandardScaler` for linear/ridge/lasso/elasticity variants; `PolynomialFeatures(degree=2)` for the polynomial-regression model (the only feature-expanding transform found). No PCA anywhere.

**Feature count summary:** 13 features with real festival signal (live path) / 14 features with mock (0) festival signal (alternate path) / 8 generic features (third path).

### External Factors — single implementation tree, mixed real/hardcoded by component

| Signal | Real or hardcoded | Evidence |
|---|---|---|
| Weather | **Dynamically computed** | Live Open-Meteo archive API + cache; real rainfall/temperature deviation vs 30-day baseline; hardcoded-0 fallback exists only inside an `except Exception` error path |
| News | **API attempted but effectively always falls back to a static, hand-written 8-article list** under the repo's current `.env` | `NEWS_API_KEY=your_news_api_key_here` (unreplaced placeholder) → live API call returns 401 → caught by a broad `except Exception` → `FALLBACK_DATA` (8 hardcoded headlines dated 2026-04-16 to 2026-04-22) is returned every time |
| Policy | **Always hardcoded to `0.0`** | `external_factors_agent/__init__.py::run_external_factors_agent()`: `policy_signal = 0.0; policy_confidence = 0.0` — never fetched from any source |
| Recency/decay | Computed via real exponential decay, but relative to a **hardcoded frozen "now"**: `CURRENT_DATE = "2026-04-23"` (config constant), not `datetime.now()` | `external_factors_agent/config/settings.py:6`; used by `decay_engine.py` and `ml/feature_engineering.py` |

Fusion weights (`external_fusion.py::WEIGHTS`): `{"weather": 0.4, "policy": 0.35, "news": 0.25}` — meaning **35% of the weighted external signal (policy) is a hardcoded zero**, and the 25%-weighted news component is very likely also a static fallback given the placeholder API key — only the 40%-weighted weather component is reliably dynamic in the current `.env` configuration.

**7 ML features** (`event_count_3d, event_count_7d, avg_confidence, max_impact, sum_impact, recent_event_flag, days_since_last_event`) are used to train a standalone XGBoost model (`ml/trainer.py`, real `.fit()` call, 501-row dataset, 80/20 split, `random_state=42`) — but per Section F/I, this trained XGBoost model is **not wired into the live inference path**; the live path uses the rule-based `external_fusion.compute_external_impact()` instead.

**Separate stub logic, not counted as real functionality:** `cognition/agents/implementations.py::VolatilityAgent`/`ArrivalAgent` use fixed confidence values (0.85, 0.75 respectively) with an explicit code comment "Simplified for now, would use real variance analysis" — this is a different, disconnected orchestration layer, not part of any `.fit()`-traced pipeline.

---

## F. MODEL POOL

| Agent | Models (live/production path) | Count | Implemented | Actually trained | Actually evaluated | Used in final inference |
|---|---|---|---|---|---|---|
| Seasonality | SARIMA (custom), LinearRegression, Ridge, Lasso, RandomForest, GradientBoosting, XGBoost, LightGBM | **8** | Yes | Yes — `bundle.pkl` (14.8MB, last write 2026-05-25) + 34 timestamped `.bak` retraining snapshots | Yes (CV MAPE per model, live tree) | **Yes** |
| Seasonality (alt. `TieredModelPipeline`/`SEASONALITY_MODEL_REGISTRY`) | STLLinearRegression, RandomForest, XGBoost, LightGBM, Ridge, Lasso, MovingAverageBaseline, LagLinear, SARIMA | 9 | Yes | No artifact tied specifically to this registry | No | **No — not wired** |
| Arrival Volume | XGBoost, RandomForest, ElasticityLinear, Ridge, Lasso, GradientBoosting, SimpleBaseline, PolynomialRegression | **8** | Yes | Yes — `bundle.pkl` per commodity (2026-05-25) | Yes (CV MAE, live tree) | **Yes** |
| Arrival (alt. `ArrivalMultiHorizonPipeline`) | same 8-model family, multi-horizon variant | 8 | Yes | Yes, but only in the **stale** `models_backup_20260503_1905` tree | Yes (own fold metrics, stale tree) | **No — superseded** |
| External Factors | XGBoost (single model, `n_estimators=100, max_depth=4, learning_rate=0.1, subsample=0.8, random_state=42`) | **1** | Yes | Yes — `xgb_model.pkl` (159,572 bytes, 2026-04-28) | Not found | **No — not wired**; live path uses non-ML rule-based fusion instead |
| Meta-Ensemble Phase 1 | Rule-based confidence-weighted fusion (`meta_ensemble.py::fuse()`) | N/A (not a trained model) | Yes | N/A | No comparative A/B evidence | **Yes — always active, generates the current production output** |
| Meta-Ensemble Phase 2 | `LearnedEnsemble` — hand-rolled Ridge regression, one per regime (`normal`/`supply_shock`/`external_dominated`) | 1 model class × up to 3 regime instances | Yes | **No — zero `*_ridge.json` model artifacts found anywhere in the repo** | N/A (untrained) | **No — falls back to `phase1_only` mode** |
| Regime-Aware Meta-Ensemble (GARCH+HMM) | `RegimeAwareMetaEnsemble` | N/A | Yes | Not evidenced outside its own test | Only self-contained `backtest()` method, invoked only in `tests/test_regime_system.py` | **No — never instantiated outside tests** |

---

## G. VALIDATION METHODOLOGY

Three distinct, independently coded validation engines exist; two are actively used by the live training paths.

**1. `SeasonalityMultiHorizonPipeline`/`ArrivalMultiHorizonPipeline` (`multi_horizon.py`, both agents — live for Seasonality, superseded for Arrival):**
- `sklearn.TimeSeriesSplit(n_splits=min(5, max(2, len(data)//120)))`, chronological, no shuffling.
- No explicit gap/embargo beyond TimeSeriesSplit's implicit fold boundary.
- Target: `shift(-horizon)` percent-change per horizon (3/5/7/15/30-day) — no forward leakage in target construction.
- Features are lagged/rolling from data available at or before each row's date.
- **Full-data refit after CV**: `final_model = clone(base_model); final_model.fit(X, Y)` before persisting.
- Ranking metric: **MAPE**, per-horizon argmin across models. Weighting: inverse-MAPE.

**2. `AgentEnsemble` (`ensemble/agent_ensemble.py`, live for Arrival):**
- `TimeSeriesSplit(n_splits=5)`, explicit walk-forward.
- Ranking/scoring metric: **MAE**, not MAPE — explicit code comment states MAPE "explodes to 1e17+ when price-change targets are near zero, which eliminates all ML models and leaves only SimpleBaseline" (matches the Section A #8 log evidence of this exact failure mode occurring in production logs before the fix).
- Dict key is still literally named `avg_mape` even though it holds an MAE value — a naming/scoring mismatch left in the code as-is.
- Weighting: `weight_i = (1/MAE_i) / Σ(1/MAE_j)`, `min_weight_threshold=0.01` pruning.
- Full-data refit after CV.
- No explicit gap/embargo.

**3. `training_pipeline_v2.py` (live, produced the Section A #2/#4 measured numbers):**
- Explicit walk-forward with 3 fixed date windows (`WF_WINDOWS`).
- Compares directly against a lag-1 naive baseline computed on the same validation slice — the only baseline comparison in the whole codebase that is methodologically clean (Section B).

**4. `DatasetBuilder.walk_forward_splits()` (Phase 2 meta-ensemble, `ensemble/dataset_builder.py`):**
- Explicit **7-day embargo/gap**: `gap=7`, `train_end = val_start - gap`, module docstring states this "prevents lookahead bias" — the most rigorous of the four engines.
- `n_splits=3`, `min_train=30` records.
- Never actually executes end-to-end in the current deployment (Section I) because 0 of 81/66 prediction records have realized outcomes to build a training set from.

**5. Standalone offline tools not wired into training or inference:** `mandisense_ai/evaluation/` (`backtester.py`, `model_comparison.py`, `statistical_validation.py`, `regime_analysis.py`, `residual_analysis.py`) — imported only by `training/orchestrator.py::CognitionBacktester`, not by any live agent or the prediction controller.

No feature-leakage (future information used at training time) was identified in the live paths' feature-lag logic in either sub-audit.

---

## H. ENSEMBLE WEIGHTING

| Mechanism | Implemented? | Formula/parameters (exact, quoted) |
|---|---|---|
| Equal/static weighting | Fallback only, not a general primary scheme | `LearnedEnsemble._get_soft_regime_weights` fallback `w_normal = max(0.2, ...)` |
| Inverse-error weighting | **Yes** | `weight_i = (1/error_i) / Σ_j(1/error_j)` — inverse-MAPE in `multi_horizon.py::_build_weights`; inverse-MAE in `agent_ensemble.py` (weights below 1% dropped and renormalized in both) |
| Confidence weighting | **Yes** | `meta_ensemble.py::fuse()`: `base_conf = w_s * seasonality.confidence + w_a * arrival.confidence`; confidence floor `0.05`, ceiling `0.95` |
| EMA-based dynamic weighting | **Yes** | `DynamicWeighter`: `alpha = 0.3` (hardcoded default); `smoothed_w = alpha*historical_w + (1-alpha)*base_w` |
| Regime-aware weighting | **Yes**, two independent implementations | `meta_ensemble.py`: `_TREND_REGIME_BOOST = 1.3` (30% boost when regime ∈ {ascending, descending}); separate GARCH/HMM `RegimeAwareMetaEnsemble` — not reachable from production |
| Festival-specific weighting | **Yes** | `DynamicWeighter.festival_models = [STLLinearRegression, SARIMA, PolynomialRegression]`; `boost_factor` default **1.3×** applied when `regimes["festival"]` is true and model is in this list |
| Supply-shock weighting | **Yes** | `DynamicWeighter.shock_models = [GradientBoosting, RandomForest, XGBoost]`; same **1.3×** `boost_factor` when `regimes["supply_shock"]` is true |
| Meta-ensemble (learned combination) | **Yes, implemented, not active** | `LearnedEnsemble` — see Section I |
| Learned residual ensemble | **Yes (same class)** | `residual_target = actual - phase1_prediction`; blend: `final = phase1_prediction + (1.0 - alpha) * learned_residual` |
| Regime-specific models | **Yes (same class), plus an unused 4-state HMM system** | `LearnedEnsemble` trains one Ridge per regime ∈ {normal, supply_shock, external_dominated}; separate `hmm_classifier.py` (Stable/Medium/High/Crisis) reachable only via the unused `RegimeAwareMetaEnsemble` |

**No A/B or comparative accuracy evaluation exists anywhere in code or logs** showing that EMA smoothing, the 1.3× regime/festival/supply-shock boosts, or inverse-error weighting outperform a simpler (e.g. equal-weight) scheme. Any accuracy-improvement claim attached to these mechanisms is **not evidenced**.

---

## I. META-ENSEMBLE / LAYER 2

1. **Phase 1 implemented:** Yes — `meta_ensemble.py`, docstring literally "Phase 1 Confidence-Aware Rule-Based Fusion Layer" / "Phase-1.5." Rule-based, not trained.
2. **Phase 2 implemented:** Yes — `learned_ensemble.py`, docstring "Phase 2 Regime-Aware Ridge Regression Models" / "Phase-2.5 Optimized Inference."
3. **Learned ensemble implemented:** Yes — `SimpleRidge`, a hand-rolled Ridge regression (normal-equations solve, no sklearn dependency by design, per an explicit comment), `alpha=1.0`.
4. **Residual learning implemented:** Yes — target = `actual − phase1_prediction`.
5. **Regime-aware learning implemented:** Yes, at two levels — (a) `LearnedEnsemble`'s 3-regime Ridge models (reachable, but untrained); (b) `RegimeAwareMetaEnsemble` GARCH+HMM system (implemented, unreachable outside tests).
6. **Input features (16, not 11):** `norm_seasonality, arrival_pred, external_score, conf_seasonality, conf_arrival, volatility, supply_stress, phase1_prediction, phase1_confidence, seasonality_x_arrival, arrival_x_stress, external_direction, agreement_flag, magnitude_diff, seasonality_x_vol, conf_agreement`. **Flag:** the module's own docstring and a field comment both say "11 engineered features" — this is stale/incorrect relative to the actual 16-element vector constructed in `extract_features()`. Documentation drift, not a functional bug.
7. **Target:** residual of Phase-1's prediction (`actual_7d_change − phase1_prediction`).
8. **Minimum data required:** `_MIN_TOTAL_RECORDS = 50` overall; `_MIN_REGIME_RECORDS = 20` per regime; `_MIN_RECORDS_FOR_MODEL = 50` (redundant re-check). A fourth constant, `_MIN_RECENT_RECORDS = 10` within a 60-day window, is defined but appears unused in the actual gating logic.
9. **Validation strategy:** `DatasetBuilder.walk_forward_splits()` — chronological, **explicit 7-day gap**, `n_splits=3`, `min_train=30`; rejects a candidate model if `r2_val < 0.0` and falls back to "normal" regime.
10. **Prediction clamps (exact):**
    - `_LEARNED_RESIDUAL_CLAMP = 5.0` (± percentage points)
    - `_PREDICTION_FINAL_CLAMP = 15.0` (also mirrored as `_PREDICTION_CLAMP_MIN/MAX = ±15.0` in `meta_ensemble.py`)
    - `_ALPHA_MIN = 0.3`, `_ALPHA_MAX = 1.0` — "Phase-1 always contributes at least 30%"
    - `_EXTERNAL_BIAS_MAX_MAGNITUDE = 2.0` (± percentage points); `external_fusion.py::MAX_BIAS = 0.02` (±2%, raw score)
11. **Phase 1 contribution to final blend:** `final = phase1_prediction + (1 − alpha) * learned_residual`, with `alpha` dynamically computed from validation R², data volume, and Phase-1/residual sign agreement, clamped to `[0.3, 1.0]` — **by construction Phase 1 can never be fully overridden by Phase 2.** If Phase 2 has no usable regime model, the code explicitly returns `{"final_prediction": phase1_prediction, "alpha": 1.0, "mode": "phase1_only"}`.
12. **Is External Factors connected to live inference?** **Yes, but only the rule-based path.** `PredictionController.predict()` calls `run_external_factors_agent` via `asyncio.gather`, and its `(impact_score, confidence)` output is passed into `run_meta_ensemble(...)`, where `external_bias = impact_score * confidence * 2.0 * attenuation_factor` is added directly into the returned `final_prediction`. Traced and confirmed as a real, non-default code path. **The separately-trained XGBoost external model (Section F) is not part of this path** — it's a different, disconnected implementation.
13. **Are external values mocked/neutral?** Partially — see Section E: policy is always hardcoded `0.0` (35% of the fusion weight); news effectively always falls back to a static 8-headline list under the repo's current (placeholder) API key (25% weight); only weather (40% weight) is reliably dynamic.
14. **Is the final output actually generated by the meta-ensemble?** **The final output is generated by Phase 1 only, currently.** Verified by direct artifact search: `LearnedEnsemble.load()` looks for `*_ridge.json` under `models/meta_ensemble/`; **a filesystem search of the entire repo found zero such files and no `models/meta_ensemble/` directory at all.** Consequently `PredictionController._load_components()` logs `"No trained models found — Phase-1 only mode"` and `self._learned_ensemble` is `None`. Since 0 of 81 and separately 0 of 66 records in `meta_predictions.jsonl` have a realized `actual_7d_change` (all `null`), even the `_MIN_TOTAL_RECORDS = 50` gate for training Phase 2 could not currently be satisfied by real outcome data if training were attempted. **Gap identified: Phase 2 (the "regime-aware learned ensemble," the most sophisticated part of the architecture) is fully implemented in code but has never been trained and cannot currently activate in this deployment — production predictions are Phase-1 rule-based fusion only.**

Separately, `RegimeAwareMetaEnsemble` (GARCH+HMM) is a fully-built third ensemble layer that is instantiated **only inside `tests/test_regime_system.py`** and nowhere in `orchestrator/`, `core/`, or any reachable inference path.

---

## J. INFERENCE / TRAINING PERFORMANCE (measured only)

| Metric | Value | Evidence |
|---|---|---|
| Ensemble `fit()` wall-clock time | 15.28s–43s observed range across 36 logged runs (varies by number of active models: 1 model during the MAPE-bug period ≈15–31s; 8 models post-fix ≈23–43s) | `"fit() complete"` log lines, `agent_ensemble.py:314-318` (`elapsed = time.perf_counter() - t0`), `mandisense_ai/logs/mandisense.log` |
| Per-request prediction latency | 47ms–123,922ms (~124s outlier during a logged agent-retry storm); typical no-model-loaded latency 63–984ms; typical model-loaded latency (tomato/kolar) 2,172–28,047ms | `"[Orchestrator] Prediction complete: ... latency=...ms"`, 66 occurrences, `mandisense_ai/logs/mandisense.log` |
| "Backtest Complete" Direction Accuracy / MAE | Direction Acc 13.3%–61.1%; MAE 4.16%–6.06% (27 log lines, 2026-05-02T18:45–2026-05-03T07:29) | `logs/mandisense.log` — **caveat: the generating function `run_backtest_report` no longer exists anywhere in the current codebase**, so this exact methodology cannot be independently verified from source today |
| Dataset processing time, models-trained-per-run counter, aggregate Prometheus metrics | **NOT FOUND** | `monitoring/metrics.py` defines `PREDICTIONS_TOTAL`/`ACTIVE_MODELS_GAUGE` as instrumentation, but no scraped/exported snapshot of these values was found anywhere |

**Operational flag:** `"No trained models found — Phase-1 only mode"` recurs repeatedly across widely separated timestamps (2026-04-28, and five separate times on 2026-05-15), and 49 of 66 logged "Prediction complete" events show `pred=0.0000` — i.e., the deployed API frequently serves the Phase-1 default/fallback rather than a model-backed prediction.

---

## K. PREDICTION / PRODUCTION EVIDENCE

| Item | Value | Evidence |
|---|---|---|
| Successful prediction runs logged | 65–66 per log file (`"Prediction complete"` count ≈ `"[PredictionLogger] Logged record"` count) | `mandisense_ai/logs/mandisense.log`, `logs/mandisense.log` |
| Logged predictions with a realized/actual outcome | **1 of 21** (`prediction_history.jsonl`: Onion/Lasalgaon, ArrivalVolume/XGBoost, predicted 1200.0, actual 1250.0, error 4%) | `mandisense_ai/data/ensemble/prediction_history.jsonl` |
| Meta-ensemble records with realized outcome | **0 of 81** (and separately 0 of 66 in the duplicate copy) — all `actual_7d_change: null` | `mandisense_ai/data/ensemble/meta_predictions.jsonl`, `data/ensemble/meta_predictions.jsonl` |
| Records eligible for Phase-2/learned-ensemble training | **0** (given the `_MIN_TOTAL_RECORDS=50` gate and zero completed outcomes) | Section I #14 |
| Rolling MAPE history over production traffic | **NOT FOUND** | — |
| Directional accuracy (production, as opposed to the 15-day offline replay in A#5) | **NOT FOUND** | — |
| Confidence/calibration statistics | **NOT FOUND** as a real computed calibration curve; note per Section A that some logged "confidence" values (e.g. 0.95 in the 15-day replay) are constants, not computed | — |
| Error distribution | Only the offline `error_analysis_v2.csv` (429 rows, errors >15%, from the walk-forward CV run, not production traffic) | `mandisense_ai/logs/error_analysis_v2.csv` |
| Cache activity | Real `cache_hit`/`cache_miss` events logged per commodity:mandi:date key; no aggregate hit-ratio computed from them (the 50% figure elsewhere is fabricated, see Section A) | `mandisense_ai/services/prediction_cache` logs |

---

## L. COMMODITY / MANDI COVERAGE

At least **five mutually inconsistent** "configured" commodity/mandi definitions exist in the codebase, none a strict subset/superset of another:

| Source | Commodities | Mandis |
|---|---|---|
| `cognition/registry.py` ("Phase 5B: Unified source of truth") | tomato, onion, potato, garlic, ginger (5) | kolar_apmc, bangalore_apmc (2) |
| `external_factors_agent/config/settings.py` | onion, tomato, rice, wheat, pulses (5) | none defined |
| `data/prepare_datasets.py` / `train_arrival.py` / `train_seasonality.py` | tomato, onion, potato, dry_chillis, garlic (5) | kolar, lasalgaon, agra, guntur, neemuch (single real mandi per commodity) |
| `data/raw/v1`–`v3` / `processed/v4` directory structure | garlic, ginger, onion, potato, tomato (5) | 15 Karnataka APMCs (up to 75 pairs as files) |
| `cognition/world_model/topology.py::MarketRegistry` | none | kolar_apmc, bangalore_apmc, mumbai_apmc, nashik_apmc (4, with coordinates) |

**Configured (union across all sources):** garlic, ginger, onion, potato, tomato, dry_chillies, rice, wheat, pulses (9 named commodities, though rice/wheat/pulses have zero backing data anywhere).

**Actually evaluated (has a MEASURED metric, Section A):** garlic, ginger, onion, potato, tomato × 15 synthetic Karnataka mandis (75 pairs, `per_mandi_metrics_v2.csv`); plus the 5 real single-mandi pairs (dry_chillies/guntur, garlic/neemuch, onion/lasalgaon, potato/agra, tomato/kolar).

**Actually used in generated prediction artifacts:**
- Cognition snapshots (`cognition/storage/snapshots/*.json`, 10 files): exactly the 5 commodities × {kolar_apmc, bangalore_apmc} = 10 pairs, matching `registry.py`.
- `meta_predictions.jsonl` (both copies): 5 pairs — dry_chillis/guntur, onion/nashik, onion/kolar, garlic/mandsaur, tomato/kolar.
- `prediction_history.jsonl`: 2 pairs — Onion/Lasalgaon, tomato/kolar.

**Discrepancy flagged:** `garlic/mandsaur` and `onion/nashik` appear in real generated prediction-log output but **have no matching entry in any of the five configured lists above and no backing raw or processed data file anywhere in the repo** (the only garlic raw file is Neemuch, not Mandsaur; the only onion raw file is Lasalgaon, not Nashik). Cross-referenced with Section J's runtime log ("No trained models found — Phase-1 only mode") and Section K, these are consistent with pure Phase-1 default-fallback predictions (`pred=0.0000, conf=0.9500`) rather than model-backed forecasts for an actually-supported pair.

---

## M. FINAL EVIDENCE TABLE

| Metric / Claim | Exact Value | Status | Evidence | File | Function/Class |
|---|---:|---|---|---|---|
| Final MAPE (1-day horizon, walk-forward, per-pair) | 4.00%–5.14% | MEASURED | `per_mandi_metrics_v2.csv`, 75 rows | `mandisense_ai/logs/per_mandi_metrics_v2.csv` | `training_pipeline_v2.py` |
| Final MAE (arrival ensemble CV, post-fix, units undocumented) | XGBoost 127.19 (best of 8) | MEASURED | log lines from 2026-05-02T19:23 onward | `mandisense_ai/logs/mandisense.log` | `AgentEnsemble.fit()` |
| Final RMSE (per pair, raw price units) | e.g. 79.73–431.57 | MEASURED | `per_mandi_metrics_v2.csv` | same | `training_pipeline_v2.py` |
| Baseline MAPE (lag-1 naive, same pairs/horizon) | 5.23%–7.23% | MEASURED | same file | same | same |
| Improvement vs baseline | 21.2%–34.5% (range; no verified average) | MEASURED | `per_mandi_metrics_v2.csv::improvement_pct` | same | same |
| Forecast horizon actually evaluated | 1-day | MEASURED; 3/5/7/15/30-day are IMPLEMENTED but only historically measured in a superseded backup tree | Section C | multiple | multiple |
| Dataset rows (evaluated set) | 91,275 (v4, 5 commodities × 15 mandis × 18,255) | MEASURED | `data/processed/v4/*.csv` | same | — |
| Date range (evaluated set) | 2023-01-02 → 2026-05-02 | MEASURED | same | same | — |
| Commodities (evaluated) | garlic, ginger, onion, potato, tomato (+dry_chillies in the separate single-mandi set) | MEASURED | Section D | — | — |
| Mandis (evaluated) | 15 synthetic Karnataka APMCs (v4) + 5 real single mandis | MEASURED, flagged as likely synthetic for the 15-mandi set | Section D | — | — |
| Features (max traced to a live `.fit()`) | 13 (Seasonality live), 13 (Arrival live) | IMPLEMENTED/MEASURED-traced | Section E | multiple | multiple |
| Seasonality models | 8 (live), +9 more implemented-but-unwired | IMPLEMENTED/trained | Section F | multiple | multiple |
| Arrival models | 8 (live), +8 more implemented-but-superseded | IMPLEMENTED/trained | Section F | multiple | multiple |
| CV folds | 5 (TimeSeriesSplit, both live engines); 3 windows (walk-forward v2); 3 folds w/ 7-day gap (Phase 2, never executed) | CONFIGURED/MEASURED | Section G | multiple | multiple |
| Dynamic weighting | EMA α=0.3, 1.3× regime/festival/supply-shock boosts | IMPLEMENTED, no accuracy-improvement evidence | Section H | `ensemble/dynamic_weighter.py`, `ensemble/meta_ensemble.py` | `DynamicWeighter` |
| Runtime | fit(): 15–43s; per-request latency: 47ms–124s (outlier) | MEASURED | Section J | `mandisense_ai/logs/mandisense.log` | — |
| Successful predictions (logged) | 65–66 per log file; **1 with a realized outcome** | MEASURED | Section K | `prediction_history.jsonl`, `meta_predictions.jsonl` | — |

---

## N. RESUME-READY FACTS

**SAFE TO CLAIM ON RESUME**

- *"Built a walk-forward-validated XGBoost forecasting pipeline achieving 4.0–5.1% MAPE across 75 commodity-market pairs, a 21–35% error reduction versus a lag-1 naive baseline."* — Exact numbers from `mandisense_ai/logs/per_mandi_metrics_v2.csv`, computed via 3-window walk-forward CV with a same-slice, same-horizon baseline comparison. Safe because both values come from the identical evaluation methodology and dataset.
- *"Engineered a multi-agent ensemble architecture combining 8 regression/boosting models per agent (SARIMA, Ridge, Lasso, Random Forest, Gradient Boosting, XGBoost, LightGBM, etc.) with inverse-error-weighted blending."* — Model roster and weighting formula are directly present in `ensemble/agent_ensemble.py` and `core/agents/seasonality/multi_horizon.py`, with trained `.pkl` artifacts confirming the models were actually fit.
- *"Processed and validated a 91,275-row, 3-year multi-commodity agricultural price time series (5 commodities × 15 markets)."* — Row counts and date range are directly measured from `data/processed/v4/*.csv`. (Caveat below.)
- *"Implemented time-series cross-validation with `TimeSeriesSplit` and an explicit 7-day train/validation embargo to prevent lookahead bias in a two-stage forecasting pipeline."* — `dataset_builder.py`'s `walk_forward_splits(gap=7)` is real, well-documented code, safe to describe as implemented (not as "used in production," since it never actually ran end-to-end — see caveats).
- *"Designed a regime-aware residual-learning meta-ensemble (Ridge-on-residuals, per-market-regime models, dynamic Phase-1/Phase-2 blending with confidence-based clamping)."* — Architecturally real and non-trivial: `learned_ensemble.py` is a complete, working implementation with exact clamps (`alpha ∈ [0.3, 1.0]`, ±15pt final clamp). Fine to describe as "designed/implemented"; do not describe it as "improved production accuracy" (never evaluated) or "currently serving predictions" (it is not — see Do Not Claim).

**DO NOT CLAIM**

- **"Achieved <15% MAPE" as a validated production result of the full system.** No evidence found that this specific proposal target was measured against the live meta-ensemble; the only clean MAPE numbers (4–5%) are for a single 1-day-ahead XGBoost model, not the "MandiSense system" as a whole, and not the 7/30-day horizons the product is framed around.
- **Any claim that the learned/regime-aware meta-ensemble ("Phase 2") is running in production or improved accuracy.** It has zero trained artifacts anywhere in the repo and cannot currently activate — the system serves Phase-1 rule-based fusion only.
- **Any claim about "External Factors" (news/policy sentiment) driving real forecast adjustments.** Policy is hardcoded to 0.0 (35% of that agent's fusion weight); news effectively always falls back to 8 static hardcoded headlines under the repo's placeholder API key; only weather is reliably live.
- **Any specific latency, throughput, or "cache hit ratio" number from `artifacts/evaluation/system_latency_stats.tex`.** Confirmed fabricated via `np.random` and hardcoded template strings.
- **Any precision/recall/F1/Cohen's κ decision-quality number from `artifacts/evaluation/decision_performance_stats.tex`.** Confirmed generated from synthetic 18%-noise-injected labels, not real predictions.
- **A single, unqualified "system-wide MAPE" or "ensemble accuracy" headline number.** No such single number was found; only per-model, per-horizon, per-pair numbers exist, several of which are internally inconsistent (e.g. `model_comparison.tex` shows the illustrative "MandiSense" blend performing worse than plain ARIMA due to a MAPE-computation bug).
- **Any claim of directional accuracy or trend-prediction accuracy above the single measured 53.3% figure**, and even that figure is from a 15-day, single-commodity, single-mandi offline replay with a hardcoded/constant confidence value — not representative of broad production performance.
- **"15 markets" or "91,275 records" as real, independently-sourced market data**, without the caveat that this dataset appears to be a synthetically generated/augmented expansion (same 15 Karnataka mandi names reused for a commodity — garlic — whose real market is over 1,500 km away in Madhya Pradesh).

---

## O. FINAL RECOMMENDATION

Based only on verified evidence, the strongest defensible technical facts for an ML/AI resume entry, in priority order:

1. **Measured, baseline-validated accuracy improvement**: 4.0–5.1% MAPE vs. a 5.2–7.2% lag-1 naive baseline (21–35% relative error reduction) across 75 commodity-market pairs, computed via walk-forward cross-validation with matched methodology — this is the single cleanest, most defensible number in the entire codebase.
2. **Validated time-series methodology, not just modeling**: proper `TimeSeriesSplit`/walk-forward CV with a same-slice baseline comparison for the headline result, plus a more advanced (if unexecuted) 7-day-embargo walk-forward design for the meta-ensemble — worth emphasizing the *methodology rigor*, which is real and well-implemented, over any single accuracy number.
3. **Multi-model ensemble engineering depth**: 8-model heterogeneous ensembles (classical statistical + tree-based + boosting) per agent with inverse-error weighting, actually trained and actually used in inference — real engineering complexity, verifiable via trained artifacts, independent of the unactivated Phase-2 layer.
4. **Architecturally sophisticated (if not-yet-activated) residual/regime-aware meta-learning design**: safe to present as a designed and implemented system component (Ridge-on-residual-of-base-ensemble, confidence-clamped blending, regime segmentation) — a legitimate demonstration of ML system-design maturity — but must be framed as "designed/implemented," never as "improved production results," since it has never trained on real outcomes.
5. **Domain-scale data engineering**: a multi-year, multi-commodity, multi-market pipeline (91,275 rows spanning 3+ years, plus a separate 10-year real single-mandi scrape) with proper train/validation temporal splitting and feature engineering (13 traced features per agent, lag/rolling/momentum/elasticity) — solid evidence of a full data pipeline, with the caveat about likely-synthetic mandi expansion noted above.

Not recommended for emphasis: forecast horizon breadth (7/30-day claims are unevaluated in the live tree), external-factors/NLP sophistication (largely mocked/hardcoded in the current `.env` configuration), and any single "system accuracy" headline (no such number exists cleanly).
