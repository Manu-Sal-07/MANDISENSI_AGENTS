# Phase 7 — Exploratory Analysis & Visualisation Audit

> **Project:** MandiSense AI (Multi-Agent Agricultural Price Intelligence)
> **Audit date:** 2026-09-06
> **Scope:** Every plot, descriptive statistic, dashboard, and human-facing output in the repo.

---

## 1. Chart Inventory

Every plot produced anywhere in the codebase, catalogued by generator.

### 1A. Scratch Figure-Generation Scripts (`scratch/`)

| # | Chart Type | File : Lines | Data Plotted (Exact Columns) | Grouping / Hue | Aggregation Applied | Axes & Scale | Title / Labels | Saved To | Consumed By |
|---|-----------|-------------|------------------------------|----------------|---------------------|-------------|---------------|---------|------------|
| 1 | Line + scatter overlay | [generate_plot.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_plot.py) : 27–57 | `modal_price`, synthetic `predicted_price` (3-day rolling mean × noise) | Colour: actual=`#1e293b`, pred=`#10b981`; scatter red for >4% error | Rolling mean window=3 | Y: "Price (INR per Quintal)", X: "Observation Period (2026)", linear | "Time-Series Convergence: MandiSense AI vs. Real-World Volatility" | `artifacts/price_forecast_comparison.png` | Standalone demo artefact |
| 2 | 100% Stacked bar | [generate_agent_contribution.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_agent_contribution.py) : 198–252 | `s_contrib`, `a_contrib`, `e_contrib` (agent contribution %) | Regime: Stable / Volatile / Supply Shock / Festival Demand Spike | Mean across regime samples, normalized to 100% | Y: "Relative Agent Contribution (%)" 0–100, X: regime name, linear | "Agent Contribution Analysis Across Market Regimes" | `imag/figure_5_3_agent_contribution.{png,pdf,svg}`, `imag/agent_contributions.png` | LaTeX report Fig 5.3(a), PPT |
| 3 | Grouped boxplot | [generate_agent_contribution.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_agent_contribution.py) : 257–320 | `w_s`, `w_a`, `w_e` (ensemble weights) | 3 agents × 4 regimes side-by-side | Raw distribution per agent per regime | Y: "Agent Ensembling Weight Allocation" 0–1.0, linear | "Figure 5.3(b): Dynamic Agent Weight Distributions" | `imag/figure_5_3b_weight_distribution.{png,pdf}` | LaTeX report Fig 5.3(b) |
| 4 | SHAP beeswarm (custom scatter) | [generate_shap_plots.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_shap_plots.py) : 102–158 | `shap_values` (top 12 features) from RF trained on 14-feature X matrix | Colour: feature value magnitude (coolwarm cmap) | None (raw SHAP per observation) | X: "SHAP Value (Impact on Prediction Return)", Y: feature names, linear | "Figure 5.6(a): SHAP Feature Importance Beeswarm Plot" | `imag/figure_5_6a_shap_beeswarm.{png,pdf,svg}`, `imag/shap_summary.png` | LaTeX report Fig 5.6(a) |
| 5 | Horizontal bar chart | [generate_shap_plots.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_shap_plots.py) : 160–178 | `mean_abs_shap` per feature | None (sorted ascending) | Mean absolute SHAP value | X: "Mean Absolute SHAP Value", Y: feature names, linear | "Figure 5.6(b): Mean Absolute SHAP Importance" | `imag/figure_5_6b_shap_bar.png`, `imag/shap_bar_importance.png` | LaTeX report Fig 5.6(b) |
| 6 | Horizontal bar chart (categories) | [generate_shap_plots.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_shap_plots.py) : 180–219 | Cumulative `mean_abs_shap` grouped by 5 categories | 5 colours per category | Sum of member SHAP values | X: "Cumulative Mean Absolute SHAP Value", Y: category names, linear | "Figure 5.6(c): Feature Category Importance" | `imag/figure_5_6c_category_bar.png`, `imag/feature_category_importance.png` | LaTeX report Fig 5.6(c) |
| 7 | Heatmap (confusion matrix) | [generate_decision_performance.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_decision_performance.py) : 105–141 | Row-normalized confusion matrix of `actual_class` vs `predicted_class` (BUY/SELL/HOLD/WAIT) | Blues cmap, annotated with count + % | Row-normalization | Y: "Ground Truth Outcome", X: "Predicted Directive", linear | "Figure 5.7(a): Decision Engine Normalized Confusion Matrix" | `imag/figure_5_7a_confusion.{png,pdf,svg}`, `imag/decision_confusion.png` | LaTeX report Fig 5.7(a) |
| 8 | Grouped bar chart | [generate_decision_performance.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_decision_performance.py) : 143–171 | `precision_c`, `recall_c`, `f1_c` per class | 3 metrics × 4 classes, adjacent bars | sklearn `precision_recall_fscore_support` | Y: "Metric Value (0.0–1.0)", X: directive class, linear | "Figure 5.7(b): Directive Classification Performance Summary" | `imag/figure_5_7b_class_metrics.png`, `imag/decision_class_metrics.png` | LaTeX report Fig 5.7(b) |
| 9 | Calibration line plot | [generate_decision_performance.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_decision_performance.py) : 173–206 | `simulated_confidence` buckets vs observed `is_correct` rate | Perfect calibration diagonal + observed curve | `pd.cut` into 5 buckets, `groupby.mean` | Y: "Observed Decision Accuracy", X: confidence intervals, linear | "Figure 5.7(c): Confidence Calibration Assessment Curve" | `imag/figure_5_7c_calibration.png`, `imag/confidence_accuracy_curve.png` | LaTeX report Fig 5.7(c) |
| 10 | 3-panel time series (price + volatility + regime band) | [generate_regime_timeline.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_regime_timeline.py) : 104–202 | `modal_price`, `garch_volatility`, `realized_volatility`, `regime` (HMM states 1–4), alerts | 4 regime colours via axvspan; alert markers ▲▼ | EGARCH(1,1) conditional variance; HMM 4-state; 2σ/3σ threshold | Y1: price (linear), Y2: volatility % (linear), Y3: regime colourbar | "Figure 5.4: Volatility and Regime Detection Timeline" | `imag/figure_5_4_regime_timeline.{png,pdf,svg}`, `imag/regime_timeline.png` | LaTeX report Fig 5.4 |
| 11 | Heatmap (spillover matrix) | [generate_cross_commodity_suite.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_cross_commodity_suite.py) : 52–77 | 6×6 hard-coded `spillover_matrix` (Tomato/Onion/Potato/Garlic/Ginger/Dry Chillies) | Blues cmap, stars for Granger-significant links | Row-normalized to sum=1 | X: "Target Commodity", Y: "Source Commodity", linear | "Figure 5.5(a): Commodity Price Spillover Heatmap" | `imag/figure_5_5a_spillover.png` | LaTeX report Fig 5.5(a) |
| 12 | Line plot (impulse-response) | [generate_cross_commodity_suite.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_cross_commodity_suite.py) : 79–107 | Analytical IRF curves: `10·e^{-0.4t}`, `3.5t·e^{-0.35t}`, `2t·e^{-0.25t}`, `0.5t·e^{-0.2t}` | 4 commodities: Tomato(self), Onion, Potato, Garlic | None (analytical formulas) | X: "Days Elapsed Post-Shock", Y: "Price Shock Response (%)", linear | "Figure 5.5(b): Price Impulse Response to +10% Tomato Supply Shock" | `imag/figure_5_5b_irf.png` | LaTeX report Fig 5.5(b) |
| 13 | Vertical bar chart (net spillover) | [generate_cross_commodity_suite.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_cross_commodity_suite.py) : 109–139 | `net_spillover` = outflows − inflows per commodity | Red=net exporter, Blue=net importer | Sum of off-diagonal outflows − inflows | Y: "Net Spillover Contribution (%)", X: commodity names, linear | "Figure 5.5(c): Net Exporter vs Net Importer of Price Shocks" | `imag/figure_5_5c_net_spillover.png` | LaTeX report Fig 5.5(c) |
| 14 | Combined 1×3 subplot (heatmap + IRF + net spillover) | [generate_cross_commodity_suite.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_cross_commodity_suite.py) : 141–192 | Same data as charts 11–13 combined | Same as above | Same as above | Same as above, subfigure labeled (a)(b)(c) | Subfigure titles as above | `imag/dependency_network.png` | LaTeX report combined figure |
| 15 | Histogram (latency distribution) | [generate_system_latency.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_system_latency.py) : 52–80 | `cache_hits` (N(12,3), n=2500), `cache_misses` (N(280,45), n=1200) | Green=cached, Blue=non-cached | None (raw synthetic draws) | X: "Request Response Latency (ms)" 0–600, Y: frequency, linear | "Figure 5.9(a): FastAPI Request Latency Distribution" | `imag/figure_5_9a_latency_hist.{png,pdf,svg}`, `imag/system_latency.png` | LaTeX report Fig 5.9(a) |
| 16 | Boxplot comparison (log-scale Y) | [generate_system_latency.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_system_latency.py) : 82–117 | 4 synthetic latency distributions | 4 operation modes | None (raw distributions) | Y: latency ms **log scale**, X: operation mode, no outlier display | "Figure 5.9(b): Latency Boxplot Comparison by Operation Mode" | `imag/figure_5_9b_latency_boxplot.png`, `imag/latency_boxplot.png` | LaTeX report Fig 5.9(b) |
| 17 | Line plot (load scaling) | [generate_system_latency.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_system_latency.py) : 119–147 | 10 hard-coded `(users, latency)` pairs | 3 shaded zones: Stability/Degradation/Congestion | None (hard-coded tabular data) | X: "Number of Concurrent API Clients", Y: "Average Request Latency (ms)", linear | "Figure 5.9(c): Horizontal Scalability & Concurrency Benchmark" | `imag/figure_5_9c_load_scaling.png`, `imag/load_scaling_curve.png` | LaTeX report Fig 5.9(c) |
| 18 | Scatter timeline (circuit breaker) | [generate_system_latency.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_system_latency.py) : 149–193 | Synthetic 120-step timeline: normal→outage→half-open→recovery | 3 colours: green=normal, red=outage, orange=probing | None (procedurally generated) | X: "Operational Timeline (Seconds)", Y: "Inference API Latency (ms)" 0–380, linear | "Figure 5.9(d): Circuit Breaker Tripping and Self-Healing Timeline" | `imag/figure_5_9d_cb_timeline.png`, `imag/circuit_breaker_timeline.png` | LaTeX report Fig 5.9(d) |
| 19 | Infographic — timeline cards (6 stages) | [generate_forecast_evolution.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_forecast_evolution.py) : 1–199 | Text-only (no data plotted) — methods/strengths/limits per stage | 6 colour-coded cards with directional arrows | N/A — conceptual diagram | Pure annotation canvas (18×10.5 in) | "Historical Evolution of Agricultural Price Forecasting Methodologies" | `imag/forecast_evolution.{png,pdf,svg}` | LaTeX report literature review figure |
| 20 | Infographic — taxonomy tree | [generate_forecasting_taxonomy.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_forecasting_taxonomy.py) : 1–275 | Text-only (no data plotted) — categories, subcategories, analytical properties | 4 columns with sub-branches and terminal MandiSense node | N/A — conceptual diagram | Pure annotation canvas (19×12 in) | "Taxonomy of Agricultural Time-Series Forecasting Approaches" | `imag/forecasting_taxonomy.{png,pdf,svg}` | LaTeX report literature review figure |

### 1B. Evaluation Module Charts (`mandisense_ai/evaluation/`)

| # | Chart Type | File : Lines | Data Plotted | Grouping / Hue | Aggregation | Axes & Scale | Title / Labels | Saved To | Consumed By |
|---|-----------|-------------|-------------|----------------|-------------|-------------|---------------|---------|------------|
| 21 | Line plot (actual vs predicted) | [time_series_viz.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/time_series_viz.py) : 52–84 | `modal_price`, `predicted_price` (Ridge on 7 lags) | Blue=actual, Green(dashed)=predicted; fill_between for over/under-prediction | Ridge(alpha=1.0) walk-forward 80/20 split | Y: "Modal Price (₹/Quintal)", X: date, linear | "Time-Series Forecast Validation: Tomato (Kolar Mandi)" | `artifacts/evaluation/predicted_vs_actual.png` | LaTeX snippet in `forecast_viz.tex` |
| 22 | Histogram + KDE (residuals) | [residual_analysis.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/residual_analysis.py) : 30–47 | `residual` = `actual_price` − `predicted_price` | Single colour (MANDI_BLUE), KDE overlay | seaborn `histplot(kde=True)`, 30 bins | X: "Residual Value", Y: "Frequency", linear | "Distribution of Prediction Residuals ($y − ŷ$)" | `artifacts/evaluation/residual_distribution.png` | LaTeX snippet in `residual_stats.tex` |
| 23 | Bar chart (regime MAE) | [regime_analysis.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/regime_analysis.py) : 59–83 | `abs_error` grouped by `regime` (Stable/Volatile/Shock) | 3 colours: green/blue/red | `groupby('regime')['abs_error'].agg(['mean','std','count'])` | Y: "Mean Absolute Error (%)", X: regime, linear, error bars=SE | "Model Error (MAE) Across Market Regimes" | `artifacts/evaluation/regime_performance.png` | LaTeX snippet in `regime_performance.tex` |
| 24 | 3-panel bar chart (MAPE, MAE, RMSE) | [model_comparison.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/model_comparison.py) : 102–124 | MAPE, MAE, RMSE for ARIMA / RF / XGBoost / MandiSense | 4 model colours per subplot | Walk-forward 85/15 split; per-model sklearn metrics | Y: metric value, X: model name, linear | "{Metric} Comparison" | `artifacts/evaluation/model_comparison.png` | LaTeX snippet in `model_comparison.tex` |
| 25 | Boxplot (baseline vs proposed) | [error_boxplot.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/error_boxplot.py) : 58–96 | `Baseline` abs error vs `MandiSense AI` abs error | Grey=baseline, Blue=proposed; show means | Seaborn boxplot with mean marker | Y: "Absolute Error (%)", X: model, linear | "Prediction Error Distribution: Baseline vs. MandiSense AI" | `artifacts/evaluation/model_error_comparison.png` | LaTeX snippet in `error_comparison.tex` |
| 26 | KDE (error distribution overlay) | [error_distribution.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/error_distribution.py) : 49–84 | `Baseline` abs error, `MandiSense AI` abs error | Grey fill=baseline, Blue fill=proposed; mean verticals | Seaborn KDE, xlim capped at 95th percentile | X: "Mean Absolute Error (%)", Y: "Density", linear | "Error Distribution: Baseline vs. MandiSense AI" | `artifacts/evaluation/error_kde_comparison.png` | LaTeX snippet in `error_distribution.tex` |

### 1C. Additional Generated Figures (in `imag/figures/`)

| # | Chart Type | File | Data | Notes |
|---|-----------|------|------|-------|
| 27 | Metrics comparison bar chart | `imag/figures/metrics_comparison.png` (384 KB) | Unknown (no generator found in repo) | Orphan — no generating script located |
| 28 | Predicted vs actual overlay | `imag/figures/predicted_comparision.png` (466 KB) | Unknown | Orphan — note spelling error ("comparision") |
| 29 | Residual distribution | `imag/figures/residual_distribution.png` (356 KB) | Unknown | Possibly an earlier version of chart #22 |

**Total charts identified: 29** (20 from scratch scripts, 6 from evaluation modules, 3 orphans).

---

## 2. Per-Chart Conclusions & Validity Assessment

### Chart 1 — Price Forecast Convergence (`generate_plot.py`)
- **Question answered:** Does MandiSense forecast track real tomato prices?
- **Author's conclusion:** *Title implies convergence: "MandiSense AI vs. Real-World Volatility"*
- **⚠ Validity concern:** The "predicted" series is **fabricated in-script** as a 3-day rolling mean × gaussian noise (`np.random.normal(0, 0.015)`). This is **not a real model output**. The plot is cosmetic — it cannot evidence any forecasting capability. The script even calls it `df['predicted_price'] = df['price'].rolling(window=3)…`

### Charts 2–3 — Agent Contribution Analysis (`generate_agent_contribution.py`)
- **Question answered:** How do the three agents (Seasonality, Arrival, External) allocate weight under different market regimes?
- **Author's conclusion:** (implied by normalised stacking) Seasonality dominates in Stable, Arrival rises in Supply Shock, External rises in Festival periods.
- **⚠ Validity concern:** The script **back-fills insufficient regimes with synthetic samples** (lines 107–159). 25 synthetic Volatile samples, 20 Festival samples, 15 Supply Shock samples are injected when real data is sparse. The chart mixes real and synthetic data without disclosure. **The conclusions may reflect the synthetic parameter distributions more than actual market behaviour.** The chart appears to validate the ensemble design by construction.

### Charts 4–6 — SHAP Analysis (`generate_shap_plots.py`)
- **Question answered:** Which features drive forecasting predictions? Which categories contribute most?
- **Author's conclusion:** (from SHAP ranking) Price lags and arrival dynamics dominate importance.
- **⚠ Validity concerns:**
  1. **Feature fabrication:** `Festival Signal`, `Weather Impact Score`, `Policy Impact Score`, `Cross-Commodity Onion/Garlic` are **entirely synthetic** (lines 64–70), generated via `np.random.uniform` conditioned on month. SHAP values for these features reflect synthetic noise, not real signals.
  2. The model is a `RandomForestRegressor(n_estimators=100)` **trained on the same data it explains** — no train/test split for SHAP computation, which inflates importance of in-sample noise.

### Charts 7–9 — Decision Engine Performance (`generate_decision_performance.py`)
- **Question answered:** How accurately does the decision engine classify BUY/SELL/HOLD/WAIT?
- **Author's conclusion:** (implied by reported accuracy ~82%, high Cohen's Kappa) Decision engine performs well.
- **⚠ Validity concerns:**
  1. `predicted_class` is **literally copied from `actual_class` then 18% randomly perturbed** (lines 55–63). This is **not a real model prediction**. The confusion matrix is structurally guaranteed to show ~82% accuracy.
  2. `simulated_confidence` is **engineered to correlate with correctness** (lines 66–70): correct → U(0.72, 0.98), incorrect → U(0.35, 0.68). The calibration curve is **circular by construction**.

### Chart 10 — Regime Timeline (`generate_regime_timeline.py`)
- **Question answered:** How do volatility regimes evolve over time? When do GARCH volatility alerts fire?
- **Author's conclusion:** (from statistics table) System detects N warning and N critical alerts; regimes track price dynamics.
- **✓ Validity:** This chart uses **real APMC data** (`kolar.csv`), real EGARCH fitting, and real HMM classification. The underlying analysis is methodologically sound. The 2σ/3σ alert thresholds are properly derived from the fitted model.

### Charts 11–14 — Cross-Commodity Spillover (`generate_cross_commodity_suite.py`)
- **Question answered:** How do price shocks propagate across agricultural commodities?
- **Author's conclusion:** Tomato is a net price-shock exporter; Dry Chillies are mostly localized.
- **⚠ Validity concerns:**
  1. The 6×6 spillover matrix is **entirely hard-coded** (lines 21–28), not computed from data.
  2. The IRF curves are **analytical toy formulas** (`10·e^{-0.4t}` etc.), not estimated from VAR models.
  3. Granger significance is approximated as `spillover_matrix > 0.08` — not a statistical test.
  4. The chart **presents fabricated data as empirical results**. Any conclusions about commodity price transmission drawn from this chart are **unsupported**.

### Charts 15–18 — System Latency (`generate_system_latency.py`)
- **Question answered:** What is the system's operational latency profile?
- **Author's conclusion:** (from statistics) Median 12ms cached, 280ms DB, p95/p99 SLA met.
- **⚠ Validity concerns:**
  1. All latency data is **synthetic** (`np.random.normal` draws with `seed=42`), not collected from actual system operation.
  2. The load-scaling curve is **10 hard-coded data points**, not from load testing.
  3. The circuit-breaker timeline is **procedurally generated**, not from real outage logs.
  4. The report presents these as "actual log metrics" (line 15 comment: "DATA GENERATION BASED ON ACTUAL LOG METRICS") — this is misleading.

### Charts 19–20 — Literature Review Infographics
- **Question answered:** Conceptual taxonomy and historical evolution of forecasting approaches.
- **✓ No data claim** — these are correctly presented as conceptual diagrams with no empirical assertions.

### Charts 21–26 — Evaluation Module Charts
- **Question answered:** Walk-forward validation metrics for Ridge baseline.
- **Author's conclusions:** (from generated LaTeX snippets) MandiSense ensemble improves over persistence baseline; residuals are approximately centred.
- **⚠ Validity concerns:**
  1. The "MandiSense AI" in `model_comparison.py` is actually `0.2·ARIMA + 0.4·RF + 0.4·XGBoost` — a **simplified proxy**, not the actual production ensemble.
  2. `residual_analysis.py` uses **fully synthetic data** in `__main__` (lines 84–87): `np.random.normal(0, 5, 1000)`.
  3. `error_boxplot.py` and `error_distribution.py` read from parquet files that may not reflect production pipeline outputs.
  4. `regime_analysis.py` uses **real raw data** with a genuine Ridge walk-forward validation — this is the most rigorous of the evaluation modules.

---

## 3. EDA Findings Ledger

### 3A. Descriptive Statistics & Distribution Checks

| ID | Finding Type | Location | Computation | Result (if committed) |
|----|------------|----------|------------|----------------------|
| EDA-1 | Rolling correlation (price–arrivals) | [feature_engineering.py:149–164](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/preprocessing/feature_engineering.py#L149-L164) | `modal_price.rolling(14).corr(arrivals_tonnes)` | Computed as feature `price_arrival_corr_14`; no standalone EDA output |
| EDA-2 | Feature collinearity check | [validator.py:242–274](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/preprocessing/validator.py#L242-L274) | `df[numeric_cols].corr().abs()`, threshold=0.95 | Produces WARNING if >0.95 pairs found; no saved output |
| EDA-3 | Rolling correlation (log_price–log_arrivals) | [multi_horizon.py:226](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/core/agents/arrival/multi_horizon.py#L226) | `log_price.rolling(30).corr(log_arrivals)` | Used as feature `price_arrival_elasticity`; no standalone EDA output |
| EDA-4 | Rolling correlation (price–arrivals, agent features) | [agent_features.py:164](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/preprocessing/agent_features.py#L164) | `modal_price.rolling(14).corr(arrivals_tonnes)` | Computed as feature; no standalone EDA output |
| EDA-5 | Returns calculation | Multiple generators | `modal_price.pct_change()` | Used throughout; no standalone distribution analysis committed |
| EDA-6 | Volatility quantiles | [regime_analysis.py:29–30](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/regime_analysis.py#L29-L30) | `volatility.quantile(0.33)`, `volatility.quantile(0.66)` | Used to define regime boundaries (Stable/Volatile/Shock) |
| EDA-7 | GARCH conditional variance | [generate_regime_timeline.py:44–49](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_regime_timeline.py#L44-L49) | EGARCH(1,1) fitted on returns | Conditional volatility series produced; statistics summarized in LaTeX table |
| EDA-8 | HMM state distribution | [generate_regime_timeline.py:58–64](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_regime_timeline.py#L58-L64) | Gaussian HMM 4-state fitted on price/vol features | Regime sequence produced; transition probabilities from `get_state_statistics()` |
| EDA-9 | SHAP value computation | [generate_shap_plots.py:82–96](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_shap_plots.py#L82-L96) | TreeExplainer on RandomForestRegressor | Top 10 features ranked; LaTeX table in `shap_stats.tex` |
| EDA-10 | Classification metrics | [generate_decision_performance.py:82–103](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_decision_performance.py#L82-L103) | sklearn `accuracy_score`, `cohen_kappa_score`, `precision_recall_fscore_support` | Overall acc, kappa, balanced acc, per-class P/R/F1; LaTeX in `decision_performance_stats.tex` |
| EDA-11 | Latency percentiles | [generate_system_latency.py:37–42](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/generate_system_latency.py#L37-L42) | `np.mean`, `np.median`, `np.percentile(95/99)` on synthetic data | Percentile values printed and saved in `system_latency_stats.tex` |
| EDA-12 | Paired t-test | [statistical_validation.py:38–39](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/statistical_validation.py#L38-L39) | `scipy.stats.ttest_rel(baseline_ae, proposed_ae)` | t-statistic and p-value saved in `statistical_validation.tex` |
| EDA-13 | Model comparison metrics | [model_comparison.py:50–100](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/model_comparison.py#L50-L100) | MAPE, MAE, RMSE for ARIMA/RF/XGBoost/Ensemble | Table in `model_comparison.tex` |
| EDA-14 | Residual statistics | [residual_analysis.py:25–28](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/residual_analysis.py#L25-L28) | Mean, std, RMSE, MAE of residuals | LaTeX table in `residual_stats.tex` |
| EDA-15 | Regime data check | [check_data_regimes.py](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/scratch/check_data_regimes.py) | Counts per regime from `meta_predictions.jsonl`; sample weights | Printed to stdout only; **not committed** |

### 3B. Hypothesis Tests

| Test | Location | Result | Committed? |
|------|----------|--------|-----------|
| Paired t-test (baseline vs proposed MAE) | [statistical_validation.py:39](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/evaluation/statistical_validation.py#L39) | p-value expected << 0.05 (in-sample Ridge vs persistence) | Yes — LaTeX paragraph in `statistical_validation.tex` |

### 3C. What Is Missing

> [!CAUTION]
> **There is no committed EDA notebook or script** that performs standard exploratory analysis on the raw APMC data:
> - No `.describe()` output is saved anywhere
> - No distribution plots of raw `modal_price`, `min_price`, `max_price`, or `arrivals`
> - No missing-value analysis (`.isnull().sum()`) is persisted
> - No `value_counts()` for categorical columns (mandi_id, commodity)
> - No `skew()`/`kurtosis()` of price distributions
> - No `.nunique()` audit
> - No `crosstab` or `pivot_table` for multi-mandi/multi-commodity comparisons
> - No stationarity tests (ADF, KPSS) are committed as EDA outputs
> - No autocorrelation / partial autocorrelation analysis is saved
> - No seasonality decomposition results are persisted
>
> **The EDA layer is essentially absent.** All "exploration" is embedded within feature-engineering code or figure-generation scripts, never surfaced as standalone findings.

---

## 4. Traceability: EDA → Decisions

### 4A. Decisions WITH Supporting EDA

| Decision | Phase | Linked EDA |
|----------|-------|-----------|
| 14-day rolling window for price-arrival correlation | Feature Eng. (Phase 5) | EDA-1 (rolling corr computed in `feature_engineering.py`) |
| 0.95 collinearity threshold for feature validation | Preprocessing (Phase 4) | EDA-2 (collinearity check in `validator.py`) |
| 4-state HMM for regime classification | Feature Eng. (Phase 5) | EDA-8 (fitted in `generate_regime_timeline.py`) |
| EGARCH(1,1) for conditional volatility | Feature Eng. (Phase 5) | EDA-7 (fitted in `generate_regime_timeline.py`) |
| Paired t-test for model validation | Evaluation | EDA-12 (in `statistical_validation.py`) |

### 4B. Decisions WITHOUT Supporting EDA (Unjustified Choices)

> [!WARNING]
> The following design decisions appear in the codebase but have **no EDA evidence** linking them to any data-driven finding.

| # | Decision | Where It Appears | Missing Evidence |
|---|----------|-----------------|-----------------|
| 1 | **7-day forecast horizon** | Throughout pipeline (target_7d) | No analysis showing why 7 days is optimal vs 3, 5, 14, or 30 |
| 2 | **Choice of Ridge regression as baseline** | All evaluation modules | No comparison of baseline alternatives (persistence, drift, seasonal naïve) |
| 3 | **3% threshold for BUY/SELL classification** | `generate_decision_performance.py:30–31` | No analysis of price movement distribution to justify 3% |
| 4 | **5% volatility threshold for WAIT classification** | `generate_decision_performance.py:40` | No empirical derivation from volatility distribution |
| 5 | **30-day rolling window for seasonality features** | `feature_engineering.py`, `generate_shap_plots.py` | No window-length optimisation or autocorrelation analysis |
| 6 | **Alpha=1.0 for Ridge regression** | All Ridge-based evaluation code | No cross-validation or hyperparameter search |
| 7 | **0.2/0.4/0.4 ensemble weights (ARIMA/RF/XGBoost)** | `model_comparison.py:95` | Hard-coded; no weighting optimisation or ablation |
| 8 | **Arrival supply_stress threshold 0.5 for "Supply Shock"** | `generate_agent_contribution.py:83` | No empirical derivation |
| 9 | **External confidence threshold 0.3/0.4 for "Festival"** | Multiple scripts | No empirical derivation |
| 10 | **2σ/3σ thresholds for volatility alerts** | `generate_regime_timeline.py:74–75` | While standard in finance, no validation that these thresholds are appropriate for Indian agricultural mandi data (which may have non-Gaussian volatility) |
| 11 | **Outlier detection method (IQR vs z-score vs custom)** | Pipeline code | No comparative EDA showing which outlier method best fits the raw data distribution |
| 12 | **Choice of 6 commodities for cross-commodity analysis** | `generate_cross_commodity_suite.py` | No EDA establishing which commodities are actually correlated in the dataset |
| 13 | **Missing-value imputation strategy** | Cleaning pipeline | No analysis of missingness patterns (MCAR/MAR/MNAR) |
| 14 | **Daily frequency assumption** | Pipeline | No analysis of actual data frequency/gaps in raw APMC data |

---

## 5. Dashboards & Reports

### 5A. Interactive Dashboards

| Framework | Location | Status |
|----------|----------|--------|
| Streamlit | — | **Not found in repo** |
| Dash | — | **Not found in repo** |
| Gradio | — | **Not found in repo** |
| Panel / PyGWalker | — | **Not found in repo** |

**No interactive dashboard exists.** The frontend is a Next.js web application serving prediction API results, not an EDA/analytics dashboard.

### 5B. Static Reports

| # | Report Type | Location | Pages | Generator | Audience |
|---|-----------|----------|-------|----------|---------|
| 1 | LaTeX Final Report | [imag/final_report.tex](file:///d:/BMS%20COLL/PROJECT/MS-AI/imag/final_report.tex) → [final_report.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/imag/final_report.pdf) (2.5 MB) | ~100+ pages | pdflatex | Academic committee |
| 2 | LaTeX New Report (extended) | [imag/new_report.tex](file:///d:/BMS%20COLL/PROJECT/MS-AI/imag/new_report.tex) → [new_report.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/imag/new_report.pdf) (3.7 MB) | ~120+ pages | pdflatex | Academic committee |
| 3 | LaTeX Final Presentation | [imag/final_presentation.tex](file:///d:/BMS%20COLL/PROJECT/MS-AI/imag/final_presentation.tex) → [final_presentation.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/imag/final_presentation.pdf) (305 KB) | Beamer slides | pdflatex | Viva committee |
| 4 | Beamer PPT (presentation/) | [presentation/ppt.tex](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/presentation/ppt.tex) → [ppt.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/presentation/ppt.pdf) (436 KB) | ~45 slides | pdflatex | Viva committee |
| 5 | Beamer PPT v2 (presentation/) | [presentation/ppt1.tex](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/presentation/ppt1.tex) → [ppt1.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/presentation/ppt1.pdf) (694 KB) | ~45+ slides | pdflatex | Viva committee |
| 6 | Beamer PPT (outer presentation/) | [presentation/presentation.tex](file:///d:/BMS%20COLL/PROJECT/MS-AI/presentation/presentation.tex) → [presentation.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/presentation/presentation.pdf) (452 KB) | ~45 slides | pdflatex | Viva committee |
| 7 | PowerPoint Deck | [MandiSense_AI_Deck.pptx](file:///d:/BMS%20COLL/PROJECT/MS-AI/MandiSense_AI_Deck.pptx) (49 KB) | Unknown | python-pptx via `mandisense_deck.py` | Stakeholder demo |
| 8 | Capstone Report PDF | [capstone.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/capstone.pdf) (351 KB) | Unknown | Unknown source | Academic submission |
| 9 | README PDF | [README.pdf](file:///d:/BMS%20COLL/PROJECT/MS-AI/MS-AI/README.pdf) (829 KB) | N/A | From README.md | Repository documentation |
| 10 | Visual Audit HTML | [presentation/visual_audit.html](file:///d:/BMS%20COLL/PROJECT/MS-AI/presentation/visual_audit.html) (5 KB) | Single page | Unknown | Slide verification |
| 11 | Speaker Notes DOC | [MandiSense_AI_Presentation_Speaker_Notes.doc](file:///d:/BMS%20COLL/PROJECT/MS-AI/MandiSense_AI_Presentation_Speaker_Notes.doc) (121 KB) | N/A | Unknown | Presentation prep |

### 5C. Report Refresh Mechanism

All reports are **batch-generated** via LaTeX compilation or Python scripts. There is no automated refresh, no CI/CD pipeline for report generation, and no scheduling. The figure-generation scripts are standalone and must be run manually before recompilation.

---

## 6. Presentation-Layer Outputs (Human-Facing Files)

Every file the project produces for human consumption:

### 6A. Image Outputs (PNG/PDF/SVG)

| Path | Format | Generator Script | Consumer |
|------|--------|-----------------|---------|
| `imag/figure_5_3_agent_contribution.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_agent_contribution.py` | LaTeX report Fig 5.3(a) |
| `imag/figure_5_3b_weight_distribution.{png,pdf}` | PNG+PDF | `scratch/generate_agent_contribution.py` | LaTeX report Fig 5.3(b) |
| `imag/figure_5_4_regime_timeline.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_regime_timeline.py` | LaTeX report Fig 5.4 |
| `imag/figure_5_5a_spillover.png` | PNG | `scratch/generate_cross_commodity_suite.py` | LaTeX report Fig 5.5(a) |
| `imag/figure_5_5b_irf.png` | PNG | `scratch/generate_cross_commodity_suite.py` | LaTeX report Fig 5.5(b) |
| `imag/figure_5_5c_net_spillover.png` | PNG | `scratch/generate_cross_commodity_suite.py` | LaTeX report Fig 5.5(c) |
| `imag/dependency_network.png` | PNG | `scratch/generate_cross_commodity_suite.py` | LaTeX report combined figure |
| `imag/figure_5_6a_shap_beeswarm.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_shap_plots.py` | LaTeX report Fig 5.6(a) |
| `imag/figure_5_6b_shap_bar.png` | PNG | `scratch/generate_shap_plots.py` | LaTeX report Fig 5.6(b) |
| `imag/figure_5_6c_category_bar.png` | PNG | `scratch/generate_shap_plots.py` | LaTeX report Fig 5.6(c) |
| `imag/figure_5_7a_confusion.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_decision_performance.py` | LaTeX report Fig 5.7(a) |
| `imag/figure_5_7b_class_metrics.png` | PNG | `scratch/generate_decision_performance.py` | LaTeX report Fig 5.7(b) |
| `imag/figure_5_7c_calibration.png` | PNG | `scratch/generate_decision_performance.py` | LaTeX report Fig 5.7(c) |
| `imag/figure_5_9a_latency_hist.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_system_latency.py` | LaTeX report Fig 5.9(a) |
| `imag/figure_5_9b_latency_boxplot.png` | PNG | `scratch/generate_system_latency.py` | LaTeX report Fig 5.9(b) |
| `imag/figure_5_9c_load_scaling.png` | PNG | `scratch/generate_system_latency.py` | LaTeX report Fig 5.9(c) |
| `imag/figure_5_9d_cb_timeline.png` | PNG | `scratch/generate_system_latency.py` | LaTeX report Fig 5.9(d) |
| `imag/forecast_evolution.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_forecast_evolution.py` | LaTeX report lit review |
| `imag/forecasting_taxonomy.{png,pdf,svg}` | PNG+PDF+SVG | `scratch/generate_forecasting_taxonomy.py` | LaTeX report lit review |
| `artifacts/evaluation/predicted_vs_actual.png` | PNG | `evaluation/time_series_viz.py` | LaTeX snippet |
| `artifacts/evaluation/residual_distribution.png` | PNG | `evaluation/residual_analysis.py` | LaTeX snippet |
| `artifacts/evaluation/regime_performance.png` | PNG | `evaluation/regime_analysis.py` | LaTeX snippet |
| `artifacts/evaluation/model_comparison.png` | PNG | `evaluation/model_comparison.py` | LaTeX snippet |
| `artifacts/evaluation/model_error_comparison.png` | PNG | `evaluation/error_boxplot.py` | LaTeX snippet |
| `artifacts/evaluation/error_kde_comparison.png` | PNG | `evaluation/error_distribution.py` | LaTeX snippet |
| `artifacts/price_forecast_comparison.png` | PNG | `scratch/generate_plot.py` | Standalone demo |
| `imag/figures/metrics_comparison.png` | PNG | Unknown | Orphan |
| `imag/figures/predicted_comparision.png` | PNG | Unknown | Orphan |
| `imag/figures/residual_distribution.png` | PNG | Unknown | Orphan |

### 6B. LaTeX Outputs (TEX)

| Path | Content | Generator |
|------|---------|----------|
| `artifacts/evaluation/agent_contribution_stats.tex` | Contribution % table by regime | `scratch/generate_agent_contribution.py` |
| `artifacts/evaluation/shap_stats.tex` | SHAP importance table | `scratch/generate_shap_plots.py` |
| `artifacts/evaluation/decision_performance_stats.tex` | P/R/F1 classification table | `scratch/generate_decision_performance.py` |
| `artifacts/evaluation/regime_timeline_stats.tex` | HMM regime statistics table | `scratch/generate_regime_timeline.py` |
| `artifacts/evaluation/cross_commodity_stats.tex` | Spillover statistics table | `scratch/generate_cross_commodity_suite.py` |
| `artifacts/evaluation/system_latency_stats.tex` | Latency percentile table | `scratch/generate_system_latency.py` |
| `artifacts/evaluation/forecast_viz.tex` | Figure inclusion snippet | `evaluation/time_series_viz.py` |
| `artifacts/evaluation/residual_stats.tex` | Residual metric table | `evaluation/residual_analysis.py` |
| `artifacts/evaluation/regime_performance.tex` | MAE by regime table | `evaluation/regime_analysis.py` |
| `artifacts/evaluation/model_comparison.tex` | Model benchmark table | `evaluation/model_comparison.py` |
| `artifacts/evaluation/error_comparison.tex` | Error boxplot figure snippet | `evaluation/error_boxplot.py` |
| `artifacts/evaluation/error_distribution.tex` | KDE figure snippet | `evaluation/error_distribution.py` |
| `artifacts/evaluation/statistical_validation.tex` | Paired t-test paragraph | `evaluation/statistical_validation.py` |

### 6C. PDF Outputs

| Path | Size | Source |
|------|------|--------|
| `imag/final_report.pdf` | 2.5 MB | `imag/final_report.tex` |
| `imag/new_report.pdf` | 3.7 MB | `imag/new_report.tex` |
| `imag/report.pdf` | 2.5 MB | `imag/final_report.tex` variant |
| `imag/final_presentation.pdf` | 305 KB | `imag/final_presentation.tex` |
| `imag/ppt (1).pdf` | 242 KB | Unknown |
| `ppt.pdf` (root) | 434 KB | `ppt.tex` (root) |
| `presentation/ppt.pdf` | 436 KB | `presentation/ppt.tex` |
| `presentation/ppt1.pdf` | 694 KB | `presentation/ppt1.tex` |
| `presentation/presentation.pdf` | 452 KB | `presentation/presentation.tex` |
| `capstone.pdf` | 351 KB | Unknown source |
| `README.pdf` | 829 KB | From README.md |

### 6D. Other Human-Facing Outputs

| Path | Format | Content |
|------|--------|---------|
| `MandiSense_AI_Deck.pptx` | PPTX | PowerPoint presentation |
| `MandiSense_AI_Presentation_Speaker_Notes.doc` | DOC | Speaker notes |
| `mandisense_ai_elite_presentation_script.docx` | DOCX | Elite presentation script |
| `mandisense_ai_presentation_script.docx` | DOCX | Presentation script |
| `presentation/visual_audit.html` | HTML | Slide verification page |
| `evaluation/results/tomato_kolar_apmc_replay.json` | JSON | Backtester replay log (3.9 KB) |

---

## 7. Critical Summary

### 7A. Synthetic Data Prevalence

> [!CAUTION]
> **Of the 26 data-bearing charts in the repository, at least 14 (54%) use wholly or partially fabricated data** presented as empirical results. This includes:
> - Decision engine performance (charts 7–9): fabricated predictions
> - Cross-commodity analysis (charts 11–14): hard-coded matrices
> - System latency (charts 15–18): synthetic random draws
> - SHAP analysis (charts 4–6): 5 of 14 features are synthetic
> - Agent contribution (charts 2–3): augmented with synthetic regime samples
> - Price forecast demo (chart 1): fabricated predictions
>
> Only charts **10** (Regime Timeline), **21** (time series viz), **23** (regime MAE analysis), and **24** (model comparison) use real data end-to-end.

### 7B. Missing EDA Foundation

The project has **no systematic EDA phase**. There are:
- Zero Jupyter notebooks
- Zero `.describe()` or `.info()` outputs saved
- Zero distribution analyses of raw data
- Zero stationarity tests committed
- Zero correlation matrices saved as standalone EDA outputs

All "analysis" is embedded within figure-generation scripts or feature-engineering code, making it impossible to trace design decisions back to data-driven exploration.

### 7C. Decisions Without Evidence (Summary)

14 significant design decisions have **no traceable EDA justification** (see Section 4B). The most critical are:
1. The 7-day forecast horizon choice
2. The 3% BUY/SELL threshold
3. The 30-day rolling window for seasonality
4. The ensemble weight allocation (0.2/0.4/0.4)
5. The choice of 6 commodities for cross-commodity analysis
