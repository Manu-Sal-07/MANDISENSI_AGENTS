# GFMC — Results

All numbers are **out of sample** (five nested walk-forward test blocks, 963 decision days, 2024-01-01 → 2026-10-27),
tomato, 12 Karnataka markets, five farmer origins, default economics (METHODOLOGY §2). Tables are in
`results/tomato/tables/`, figures in `results/tomato/figures/`. Every statement below is read from those files.


> **Numbering.** This file keeps the hypothesis labels of `METHODOLOGY.md` (H1, H2a–d, H3, H4). The manuscript renumbers them H1–H5: leakage = H1, realised labels = H2, SPO+ = H3, silence = H4, conformal floor = H5 (the reporting head and tuning criterion are reported as ablations under objective 3).

## Summary of findings

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | Decomposition-hybrid gains are largely look-ahead leakage | **Supported, very large effect** | 30 … 72 pp of skill (95 % CIs all above 25 pp, all p < 0.001) disappears when only the look-ahead differs |
| H2a | Training on *realised* outcomes (incl. the cost of a silent mandi) beats training on observed prices | **Supported** | −Rs 123 /q regret (95 % CI −165 … −87, Holm p < 1e-4); +6–7 % net revenue |
| H2b | SPO+ beats MSE on the same labels and network | **Not supported** | −25 Rs/q, CI −53 … +3, Holm p = 0.51 |
| H2c | A reporting-probability head helps | **Rejected** | +23 Rs/q worse (CI +8 … +36, Holm p = 0.012) |
| H2d | Tuning on decision regret beats tuning on forecast loss | **Not supported** | −8 Rs/q, CI −32 … +15, Holm p = 1.00 |
| H3 | Network market silence carries information beyond own report history | **Rejected** | ΔAUC −0.001 (CI on ΔlogLoss −0.0018 … +0.0028); DM p = 0.157 |
| H4 | An adaptive conformal revenue floor is valid and affordable | **Supported (validity); cost is model-dependent** | violation 4.6 / 10.6 / 23.3 % at α = 5 / 10 / 20 %; naive floor on a standard model violates 27 % vs 10 % target |

The paper's defensible positive claims are therefore **H1**, **H2a** and **H4**. H2b–H2d and H3 are honest negative
results, reported with their confidence intervals; they bound what decision-focused loss functions and silence features
can add on this data.

---

## 1. Contribution 1 — decomposition hybrids under leak-free evaluation

Five densest tomato series (Ramanagara, Kolar, Chintamani, Mulbagal, Binny Mill), ~1,280 scored origins per row
(every third day from 2024-01-01, scored only where the target price was really reported), horizons 1 and 7 days.
Skill = 1 − MAE / MAE(random walk). `future_sensitivity` confirms the mechanism: moving only the *future* by 10 %
changes STL / VMD components at day *t* by 6 % of the series' standard deviation; the causal protocol changes them by exactly 0.

| decomposer | forecaster | h | published (literature recipe) | published-joint | causal-joint | raw series | leakage gap (pub-joint − causal-joint) |
|---|---|---|---|---|---|---|---|
| STL | LightGBM | 1 | **+27.3 %** | +17.2 % | −14.7 % | −13.8 % | **+31.8 pp** [28, 36] |
| STL | LightGBM | 7 | **+40.8 %** | +35.2 % | −11.7 % | −9.8 % | **+46.9 pp** [42, 52] |
| STL | Ridge | 1 | **+28.5 %** | +22.1 % | −7.6 % | −5.7 % | **+29.7 pp** [25, 34] |
| STL | Ridge | 7 | **+41.1 %** | +38.9 % | −2.7 % | −1.5 % | **+41.7 pp** [37, 46] |
| VMD | LightGBM | 1 | **+44.4 %** | +38.4 % | −12.6 % | −13.8 % | **+51.1 pp** [46, 56] |
| VMD | LightGBM | 7 | **+57.9 %** | +50.3 % | −5.8 % | −9.8 % | **+56.1 pp** [51, 61] |
| VMD | Ridge | 1 | **+50.5 %** | +60.7 % | −10.8 % | −5.7 % | **+71.5 pp** [65, 78] |
| VMD | Ridge | 7 | **+62.4 %** | +70.4 % | −0.6 % | −1.5 % | **+71.0 pp** [66, 76] |

* The "published" column reproduces the magnitude reported in the literature (20–60 % improvement over simple baselines).
* With identical model structure and train/test features built the same way, the *only* difference between published-joint
  and causal-joint is whether a component at *t* may see data after *t*. That alone moves skill from +17…+70 % to −15…0 %.
  A naive causal port (train on interior components, apply to endpoint components, `causal_percomp`, −12…−72 %) is worse still;
  it is reported in `leakage/summary.csv` but **not** used for the headline because its train/test mismatch would overstate the gap.
* Causal decomposition adds essentially nothing over the raw series: the paired difference is not significant in 5 of 8 rows;
  of the three significant rows the raw series is better in two (STL-Ridge h = 1, VMD-Ridge h = 1) and causal decomposition in one
  (VMD-LightGBM h = 7, by 4 pp, still below the random walk). No causally-evaluated learned forecaster beats the random walk at
  the 1–7 day horizon (all skills ≤ 0).
* A zero-shot foundation model (Chronos-Bolt-small, no training on this data) has skill −9.4 % (h = 1) and −2.1 % (h = 7)
  against the random walk on the same origins: price history alone is nearly unpredictable here, which is consistent with the
  authors' earlier finding of 1.2–3 % skill on verified data.
* Positive control (unit-tested): with an identity "decomposition" the causal-joint, published-joint and raw pipelines agree to 1e-9.

## 2. Contribution 2 — what actually improves decisions

Mean realised net revenue, Rs per quintal (95 % day-block bootstrap CI of the *level*; tests below are on *paired differences*):

| method | revenue | share of oracle gap closed (vs nearest-mandi rule) | CVaR₁₀ | fallback-trip rate |
|---|---|---|---|---|
| hindsight oracle | 2,570 | 1.000 | — | — |
| **lgbm_filled_sil** (GBM, realised labels, + silence feats) | **2,168** | 0.586 | 801 | 11.6 % |
| **ds_spo** (neural, SPO+, realised labels) | **2,164** | 0.582 | 802 | 12.5 % |
| **lgbm_filled** (GBM, realised labels) | **2,156** | 0.573 | 791 | 12.4 % |
| gfmc_pred (SPO+ + reporting head + silence) | 2,148 | 0.565 | 828 | 10.6 % |
| ds_spo_struct (SPO+ + reporting head) | 2,141 | 0.558 | 820 | 11.9 % |
| ds_mse_filled (neural, MSE, realised labels) | 2,139 | 0.556 | 818 | 11.3 % |
| highest price yesterday (best heuristic) | 2,021 | 0.434 | 690 | 27.8 % |
| xgb_obs / lgbm_obs / ds_mse_obs (predict-then-optimise) | 2,016–2,019 | 0.428–0.432 | 674–681 | 28.7–29.4 % |
| random walk (cost-aware) | 2,006 | 0.419 | 675 | 29.7 % |
| best 7-day mean | 1,993 | 0.405 | 669 | 28.3 % |
| nearest mandi, sell today | 1,600 | 0.000 | 605 | 33.7 % |
| farm gate | 1,344 | −0.264 | 620 | — |

**The Model Confidence Set (α = 0.10) contains exactly the realised-label models**; every observed-label model and every
heuristic is excluded (p = 0.00).

Paired comparisons (daily regret, averaged over origins; negative = first method better; Holm over all 14: the 12 fixed before the tuned results plus 2 added afterwards for the secondary crops, rows 2 and 7):

| comparison | Δ regret (Rs/q) | 95 % CI | Holm p |
|---|---|---|---|
| realised labels vs observed labels (same network) | −123 | −165 … −87 | < 0.0001 |
| realised labels vs observed labels (LightGBM) | −140 | −181 … −102 | < 0.0001 |
| GFMC predictor vs LightGBM predict-then-optimise | −132 | −174 … −90 | < 0.0001 |
| GFMC predictor vs XGBoost predict-then-optimise | −129 | −171 … −89 | < 0.0001 |
| GFMC predictor vs random walk | −141 | −185 … −98 | < 0.0001 |
| GFMC predictor vs best simple heuristic | −127 | −170 … −87 | < 0.0001 |
| neural SPO+ vs LightGBM predict-then-optimise | −149 | −191 … −109 | < 0.0001 |
| SPO+ vs MSE (same labels, same network) | −25 | −53 … +3 | 0.505 |
| reporting head vs none | +23 | +8 … +36 | 0.012 |
| + silence features (neural) | −6 | −27 … +20 | 1 |
| + silence features (GBM) | −12 | −31 … +3 | 0.695 |
| tuned on decision regret vs forecast loss | −8 | −32 … +15 | 1 |
| structured neural vs GBM, both on realised labels | +14 | −8 … +39 | 0.865 |
| GFMC predictor vs LightGBM on the same realised labels | +8 | −18 … +38 | 1 |

**Interpretation.** The gain is carried by the *supervision signal* — learning, from realised revenue, which markets are
silent and what a wasted trip costs — not by the learner: a plain LightGBM on those labels is statistically indistinguishable
from every neural variant. Consistent with this, the fallback-trip rate falls from ~29 % to ~12 %.
The gain is positive in **every** outer fold (e.g. `ds_spo` vs `lgbm_obs`: 2401 / 2783 / 1236 / 2317 / 2126 vs
2248 / 2587 / 1119 / 2233 / 1949 Rs/q) and for every farmer origin (the nearest-mandi rule loses up to Rs 850 /q for a Kolar
farmer; learned policies are origin-invariant at 2,135–2,163).

**Forecast accuracy and decision quality decouple.** Observed-price MAE skill vs the random walk is +3–4 % for the
observed-label models (matching the earlier paper's 1.2–3 %), but **negative** for the best decision models (−2…−6 % for
filled-label GBM/MSE, and far worse for SPO+ whose outputs are not anchored to price levels). On the *realised* (fallback-filled)
targets the ordering reverses: +18–19 % for filled-label models vs +6–8 % for observed-label ones. A forecast-accuracy
leaderboard would pick the wrong models.

**Robustness** (`tables/sensitivity.csv`). Evaluation-time sweeps of transport (Rs 0.20–1.40 /q-km), spoilage (1–6 %/day) and
the silent-mandi discount (0.70–1.00) leave the conclusion unchanged: realised-label models close 17–28 % of the remaining
oracle gap beyond the best heuristic in every setting, observed-label models ≈ 0 %. The gain shrinks as silence becomes costless
(φ = 1.00: 0.17–0.20) but does not vanish, so it is not purely a silence-penalty artefact.

## 3. Contribution 3 — is market silence informative? (negative result)

Fixed, untuned LightGBM on both sides of a nested comparison, five folds × four horizons (`silence/`):

* **Reporting** (will this mandi report on the sale day?): base AUC 0.82–0.92 by fold; adding network-silence features changes
  AUC by +0.005 / −0.001 / 0.000 / −0.009 / 0.000 across folds (mean −0.001); pooled ΔlogLoss +0.0005 (95 % CI −0.0018 … +0.0028);
  improved in 2 of 5 folds; permutation test p between 0.03 and 0.44. Own report-rate alone already gives AUC ≈ 0.79.
* **Returns** (next-day log return at reporting markets): Diebold–Mariano p = 0.157; the silence model is nominally slightly
  *worse* (MSE +0.00013), MAE essentially equal in every fold.

Conclusion: whether a mandi reports is well predictable (AUC ≈ 0.8–0.9) from its **own** reporting history and the calendar, and neighbours' silence adds nothing
measurable. This is a useful negative result: it justifies the standard treatment of missing days and removes silence features
as a claimed novelty.

## 4. The guaranteed floor (adaptive conformal)

Floor L = r̂ − q·σ̂; recommendation = argmax L; α_t adapted online with delayed feedback; calibration warm-started on a
separate out-of-sample block. Scored on test days only (`tables/floors.csv`).

| predictor | policy | target α | observed violation | mean floor (Rs/q) | revenue | CVaR₁₀ |
|---|---|---|---|---|---|---|
| gfmc_pred | plug-in (no floor) | — | — | — | 2,148 | 828 |
| gfmc_pred | **adaptive conformal** | 0.05 | **0.046** | 1,167 | 2,077 | 744 |
| gfmc_pred | **adaptive conformal** | 0.10 | **0.106** | 1,556 | 2,135 | 801 |
| gfmc_pred | **adaptive conformal** | 0.20 | **0.233** | 1,853 | 2,149 | 826 |
| gfmc_pred | static conformal | 0.10 | 0.090 | 1,470 | 2,125 | 766 |
| gfmc_pred | naive Gaussian (z = 1.28) | 0.10 | 0.033 | 1,096 | 2,042 | 643 |
| lgbm_obs | adaptive conformal | 0.10 | 0.078 | 1,151 | 1,858 | 600 |
| lgbm_obs | **naive Gaussian (z = 1.28)** | 0.10 | **0.274** | 1,725 | 1,989 | 659 |
| lgbm_filled | adaptive conformal | 0.10 | 0.090 | 1,357 | 2,004 | 610 |
| lgbm_filled | naive Gaussian | 0.10 | 0.173 | 1,710 | 2,129 | 742 |

* The adaptive floor tracks its target across α (4.6 / 10.6 / 23.3 % vs 5 / 10 / 20 %) **without any distributional assumption**.
  The small overshoot at α = 0.20 (+3 pp) is finite-sample (ACI bounds long-run average miscoverage, and the scored period is
  ~960 days). On the weaker LightGBM baseline the adaptive floor is *conservative* (1.1 / 7.8 / 18.5 %), which is consistent with
  ACI's one-sided guarantee but means the floor is lower (less informative) than it needs to be for a poorly-calibrated predictor.
* The naive Gaussian floor is mis-calibrated in *both* directions: 27 % violation on the standard LightGBM baseline (2.7× the target)
  and 3 % on the GFMC predictor (needlessly conservative). Calibration matters more than the model.
* Violation by outer fold at α = 0.10: 12.3 / 13.3 / 2.6 / 12.7 / 11.5 %; the 160–290-day blocks are short, so fold-level rates
  scatter around the pooled 10.6 %.
* **Cost.** For `gfmc_pred` the 10 % floor costs Rs 13 /q mean revenue (−0.6 %); for `lgbm_filled` it costs Rs 152 (−7 %). The floor does
  **not** improve tail outcomes here (CVaR₁₀ is not higher than plug-in): its value is the *stated, verified guarantee*, not
  risk reduction.
* The guarantee is a long-run average over the observed sequence (ACI), not conditional on a given day or farmer.

## 5. Generalisation to other crops

Same code, same five outer folds, crop-specific spoilage (onion 0.8 %/day, potato 0.4 %/day), reduced budget (10 / 15 Optuna
trials) and a method subset (random walk, LightGBM observed, LightGBM realised, neural MSE-realised, neural SPO+). Onion has 4 and
potato 3 candidate markets, so these are weaker tests of *market choice*; they test whether the label effect and the floor
behaviour transfer (`results/onion/`, `results/potato/`).

| crop | oracle | best heuristic | LightGBM (observed labels) | LightGBM (realised labels) | neural SPO+ | label effect Δ regret [95 % CI], Holm p | SPO+ vs MSE Δ regret [CI] |
|---|---|---|---|---|---|---|---|
| tomato (12 mkts) | 2,570 | 2,021 | 2,016 | 2,156 | 2,164 | **−123** [−165, −87], < 1e-4 | −25 [−54, +4], n.s. |
| onion (4 mkts) | 2,902 | 2,407 | 2,395 | 2,552 | 2,564 | **−157** [−224, −89], < 1e-4 | −23 [−62, +11], n.s. |
| potato (3 mkts) | 2,173 | 1,780 | 1,758 | 1,845 | 1,830 | **−87** [−142, −39], 0.0016 | +1 [−27, +32], n.s. |

* The realised-outcome label effect is positive and significant in all three crops (+6–7 % revenue for tomato and onion, +5 % for potato).
  The fallback-trip rate falls from 43 % → 18–20 % (onion) and 34–35 % → 17–21 % (potato).
* SPO+ is never significantly better than MSE on the same labels (3 crops, 3 CIs spanning 0): the decision-focused *loss* does not
  add reliably; the decision-focused *labels* do.
* Naive Gaussian floor on the standard LightGBM baseline violates 34.5 % (onion) and 25.8 % (potato) against a 10 % target; the
  adaptive floor never exceeds the target (2.7 % and 6.5 % at α = 0.10), i.e. it is valid but conservative with such small action sets.
* Onion and potato report on far fewer days (1.8 and 1.3 markets per day on average vs 8.1 for tomato), so days with no usable
  market are excluded more often; the potato study in particular should be read as supporting evidence, not as a market-choice result.

## 6. Threats to validity

1. Economics are scenario assumptions; conclusions are stable across the sweep, but absolute rupee gains are not estimates of farmer income.
2. "Did not report" ⇒ "no sale there that day" is an assumption. With φ = 1.00 the realised-label advantage shrinks to 0.17–0.20 of the oracle gap but persists.
3. Evaluating policies on historical prices ignores the farmer's own price impact and thin-market capacity (some mandis trade 2–3 t/day).
4. Cross-market price differences are large and persistent (median same-day range ≈ Rs 1,200 /q), so decisions depend more on price
   levels than on distance; τ only matters at the top of the sweep.
5. One state, one crop for the market-choice study; the confidence intervals of levels are wide (price level varies a lot by season).
   Conclusions rest on paired differences, which are tight.
6. Leakage benchmark: two decomposers (STL, VMD) and two forecasters (ridge, LightGBM) on five series; the EMD/CEEMDAN family and
   deep forecasters (LSTM/GRU/TDNN) of the original papers are not re-implemented. The mechanism (two-sided smoothing) is general,
   but the magnitude for those specific models is not measured here.
7. Tuning budgets (20 / 25 trials) are modest; every method received the same budget.
