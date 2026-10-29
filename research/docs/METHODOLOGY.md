# GFMC — Methodology

**Guaranteed-Floor Market Choice**: conformal, decision-focused selling recommendations for smallholder farmers
under informative market silence.

This document defines the problem, the three contributions, the evaluation protocol and every assumption.
Results are in `RESULTS.md`; commands to reproduce them are in `../README.md`.

---

## 1. Data

| Item | Value |
|---|---|
| Source | Agmarknet portal exports (agmarknet.gov.in), downloaded by the project team |
| History export | "All Type of Report (All Grades)": arrivals-weighted modal price and total arrivals per market, crop and day, 2021-01-01 → 2026-10-26, Karnataka, 19 markets, 8 crops |
| Daily export | "Daily Price Arrival Report": per variety/grade min, max, modal price and arrivals, 2025-11-07 → 2026-10-28 |
| Integrity check | Where the two exports overlap (3,307 tomato market-days) they agree: Pearson r = 0.99996, median relative difference 0.0, 99.97% within 5% |
| Primary crop | Tomato: 12 markets with ≥ 700 reported days; on average 8.1 markets report per day |
| Secondary crops | Onion (4 markets), Potato (3 markets) — too few markets for a market-choice study, used as generalisation checks |
| Synthetic data | **None.** Every price in every result is a real portal record. Test fixtures in `tests/` are fabricated arrays used only to verify code, never results. |

A *cell* of the panel (day × market) is **observed** only if the mandi reported a price that day. Nothing is imputed
into the panel. A forward-filled view is derived downstream and always travels with a staleness counter.

Parsing (`gfmc/data/loader.py`) drops the portal's footer rows, rejects unexpected units, checks key uniqueness and
records a `LoadReport` (rows read / dropped / kept) that the paper's data section can quote verbatim.

## 2. The decision problem

On the morning of day *t* the farmer knows every price through day *t − 1*. He has one quintal of produce and chooses

* **sell at market *m* after holding *k* days**, *k* ∈ {0, 1, 2, 3} — i.e. sell on day *t + k*; or
* **sell at the farm gate** to a local trader on day *t*.

For a farmer at origin ℓ the realised net revenue (Rs / quintal) is

```
R(m,k | ℓ) = (1 − f)(1 − δ)^k · P(m, t+k)  −  τ · ρ · d(ℓ,m)  −  c0           if market m reported on t+k
R(m,k | ℓ) = (1 − f)(1 − δ)^k · φ · P̄(t+k) −  τ · ρ · d(ℓ,m)  −  c0           if it did not (wasted trip)
R(farm-gate) = φ_g · P̄(t)
```

where P̄ is the mean price among markets that did report that day. Parameters (scenario assumptions, not estimates):

| symbol | meaning | default | swept |
|---|---|---|---|
| τ | transport, Rs per quintal-km | 0.35 | 0.20, 0.35, 0.70, 1.40 |
| ρ | road / great-circle distance | 1.3 | — |
| f | market fee + commission | 4 % | — |
| c0 | handling per trip | Rs 20 | — |
| δ | daily spoilage (tomato / onion / potato) | 3 % / 0.8 % / 0.4 % | tomato: 1, 3, 6 % |
| φ | discount if the chosen mandi is silent | 0.85 | 0.70, 0.85, 1.00 |
| φ_g | farm-gate discount | 0.80 | — |

Five farmer origins (the district centres of Bengaluru, Kolar, Chikkaballapur, Bengaluru South, Bengaluru Rural).
A market is *offered* only if it reported within the last 14 days. Action count: 12 markets × 4 holds + 1 = 49.

**Revenue is affine in the price vector**, so the SPO+ surrogate loss is exact for this problem (§3.2).

**Evaluation honesty.** Days on which no market reports (27 of 2,125) are excluded from training and scoring; this is
reported. Whether "did not report" truly means "closed / no sale" is an assumption; φ = 1.00 makes silence free and is part
of the sensitivity sweep.

## 3. Contributions

### 3.1 Contribution 1 — decomposition hybrids under leak-free evaluation

*Hypothesis.* The accuracy gains reported by decomposition hybrids (STL-LSTM, CEEMDAN-TDNN, VMD-LSTM,
ICEEMDAN-VMD-GRU, … — the project's literature survey) are largely look-ahead leakage: STL and VMD are two-sided
smoothers, so a component at day *t* depends on data after *t*.

*Protocol* (`gfmc/leakage.py`). Identical forecasters, lags, refit schedule and origins under two protocols that differ only in
how components at and before the origin are computed — **published** (decompose the whole series once) and **causal**
(decompose only data available at each origin) — plus a raw-series control, the random walk, and a zero-shot foundation model
(Chronos-Bolt). Mechanism check: `future_sensitivity` measures how much a component at *t* moves when only the future changes
(exactly zero for the causal protocol, unit-tested).

### 3.2 Contribution 2 — decision-focused learning with a reporting head

*Hypothesis.* Training the price model on the farmer's realised revenue, including the penalty for a silent mandi,
yields better decisions than training on observed prices, even when point accuracy is not better.

*Models* (`gfmc/models/`). A DeepSets network: a shared per-market encoder, an order-invariant context over the offered
markets, and a head emitting the four hold-*k* log-returns. Trained with

| spec | labels | loss |
|---|---|---|
| `ds_mse_obs` | observed prices only | Huber |
| `ds_mse_filled` | realised prices (silent cells carry the fallback) | Huber |
| `ds_spo` | realised revenue | **SPO+** + auxiliary Huber |
| `ds_spo_struct` | realised revenue | SPO+ with a **reporting head**: expected price = ρ·p̂ + (1−ρ)·φ·P̄ |
| `gfmc_pred` | as above + network-silence features | pre-specified full model; evaluated as the most complete ablation (RESULTS §2: not better than simpler variants) |

SPO+ (Elmachtoub & Grigas 2022) for a maximisation over a finite action set with a* = argmax r:

```
SPO+(r̂, r) = max_a (2 r̂_a − r_a) − 2 r̂_{a*} + r_{a*}
```

Properties verified in `tests/test_core.py`: non-negative, zero at the truth, an upper bound on realised regret, respects the
offered set, matches a brute-force evaluation, gradient pushes toward the optimal action.

*Baselines.* Random walk (cost-aware), LightGBM and XGBoost trained on observed prices (the standard predict-then-optimise),
LightGBM trained on the same realised labels (separates "better labels" from "better learner"), and four heuristics
(nearest mandi today; highest price yesterday; best 7-day mean; farm gate).

### 3.3 Contribution 3 — is market silence informative?

*Two nested-model tests* (`gfmc/silence.py`), fixed untuned hyper-parameters on both sides:
(A) does a network-silence feature group improve prediction of *whether a mandi reports* (AUC, log-loss, day-block
bootstrap, permutation test)? (B) does it improve the next-day return forecast at reporting markets (Diebold–Mariano on
squared error)? Network-silence features: distance-weighted share of neighbours silent (today, lagged, 7-day mean, change),
number reporting, own-silent-while-neighbours-active, days since the last mass-silence event, silent volume share,
neighbour staleness. *Own* staleness and report rate are in the base set, so the base model is already a strong treatment
of missing data.

### 3.4 The guaranteed floor (adaptive conformal)

For the chosen action *a* with predicted revenue r̂ and recent error scale σ̂, the floor is **L = r̂ − q·σ̂**, and the
recommendation is argmax L (the best *guaranteed* revenue). q is the (1 − α_t) empirical quantile of past normalised scores of
recommended actions; α_t follows adaptive conformal inference (Gibbs & Candès 2021),
α_{t+1} = α_t + γ(α − 1[R < L]). ACI bounds the long-run miscoverage of the *observed* sequence for any prediction
sequence, including adaptively selected actions. Feedback is delayed: a *k*-day hold resolves *k* days after the sale; the
code only releases an outcome once its sale date is strictly in the past (tested by corrupting not-yet-known outcomes).
The calibration stream is produced by a separate model fitted *before* the calibration block, so calibration residuals are
never in-sample. Compared with a static conformal quantile and a naive Gaussian floor (z = 1.28).

### 3.5 Pre-specified hypotheses and where they stand

The model ladder (`specs.py`), the 12 paired comparisons (`scripts/analyze.py: PAIRS`), the silence tests and the leakage
protocol were fixed **before** the tuned results were seen. Outcomes (RESULTS.md): H1 leakage — supported; label effect
(realised-outcome supervision) — supported in three crops; SPO+ over MSE — not supported; reporting head — rejected; silence
features — rejected; decision-regret tuning over forecast-loss tuning — not supported; adaptive conformal floor — valid. The
paper's positive claims are limited to what survived; the rest are reported as bounded negative results.

## 4. Evaluation protocol

* **Nested walk-forward.** Five outer test blocks (2024-H1, 2024-H2, 2025-H1, 2025-H2, 2026-01 → 2026-10-27): 963 decision
  days. For each: two inner 6-month validation blocks drive Optuna (TPE) hyper-parameter search; a K+2-day gap separates
  every training window from its validation or test block so that no 4-day target window overlaps.
* **Tuning budget.** 20 trials (neural) / 25 trials (GBM) per method per fold. Every method gets the same budget. Methods are
  tuned on their *native* criterion (decision regret for decision-trained models, forecast loss for forecast-trained ones);
  `gfmc_pred_tuneMSE` isolates the effect of the tuning criterion.
* **Metrics.** Mean realised net revenue with day-block bootstrap CIs; regret to a hindsight oracle; share of the oracle gap
  closed (relative to the nearest-mandi rule and to the strongest heuristic); CVaR₁₀ and 10th percentile; fallback-trip rate;
  floor violation vs α; forecast MAE skill vs the random walk (to show decoupling of forecast and decision quality);
  reporting AUC.
* **Inference.** Paired daily regret differences (averaged over the five origins, which are strongly dependent): moving-block
  bootstrap (block 14), Newey–West Diebold–Mariano, Holm correction across all pre-specified comparisons, Hansen–Lunde–Nason
  Model Confidence Set.
* **Sensitivity.** One-at-a-time sweeps of τ, δ and φ at evaluation time (the farmer knows his own costs; the models were
  trained under the default assumptions, so this also tests robustness to misspecified economics).
* **Leakage control.** `tests/test_leakage.py` proves features at index *s* are invariant to any change of the future, targets are
  strictly future prices, and eligibility uses only past staleness. (These tests caught a real bug during development: two
  features were centred on a whole-series mean.)

## 5. Limitations (stated up front)

1. Transport, spoilage, fee and fallback parameters are scenario assumptions, not estimates; the sweep shows how conclusions move.
2. Cross-market price differences are large and persistent (median same-day range ≈ Rs 1,200/q), so decisions are driven more by
   price levels than by distance; transport only becomes decisive at the high end of the sweep.
3. "Did not report" is treated as "no sale at that mandi that day". Some silent days may be reporting failures of an operating
   market; φ = 1.00 bounds this.
4. One state, one region, 5.8 years. Onion and potato have too few markets for the market-choice problem.
5. Recommendations are for a one-quintal lot with no price impact; thin markets (arrivals of 2–3 t/day) cannot absorb large lots.
6. The zero-shot foundation model is evaluated on forecast accuracy only (it makes no decisions).
