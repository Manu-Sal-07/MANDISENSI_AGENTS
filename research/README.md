# GFMC — Guaranteed-Floor Market Choice

Research code for the MandiSense study: **conformal, decision-focused selling recommendations for smallholder farmers
under informative market silence**, evaluated on real Agmarknet data (Karnataka, 2021–2026).

Read `docs/METHODOLOGY.md` for the problem, models and evaluation protocol and `docs/RESULTS.md` for the findings.

## Contributions and what the evidence says (see `docs/RESULTS.md`)

1. **Leak-free evaluation of decomposition hybrids** (`gfmc/decomp.py`, `gfmc/leakage.py`) — **supported, very large effect**:
   STL / VMD hybrids show +17…+70 % skill over the random walk under the published protocol and −15…0 % when decomposition may
   not see the future (gap 30–72 pp, all p < 0.001); a zero-shot foundation model also has no skill.
2. **Supervising on realised outcomes** (`gfmc/models/`, `gfmc/dataset.py`) — **supported in tomato, onion and potato**:
   training on the farmer's realised net revenue, including the cost of a silent mandi, gives +5–7 % revenue and −Rs 87…157 /q
   regret vs predict-then-optimise (Holm p < 0.002). The SPO+ *loss*, a reporting head and decision-regret tuning add nothing
   significant on top.
3. **Market silence as information** (`gfmc/silence.py`) — **rejected** (a clean negative result): neighbours' silence adds nothing
   beyond a mandi's own report history.
4. **A guaranteed revenue floor** (`gfmc/conformal.py`) — **valid**: adaptive conformal inference with delayed feedback gives
   violation 4.6 / 10.6 / 23.3 % at α = 5 / 10 / 20 % (a naive Gaussian floor violates 27–35 % vs 10 % on the standard baseline).

## Layout

```
gfmc/
  config.py       economics, folds, conformal settings (every assumption in one place)
  data/           loader (portal exports -> long frame), registry (coordinates), panel (day x market + mask)
  features.py     causal features, groups: base | silence
  dataset.py      decision arrays: features through t-1, realised prices from t
  econ.py         net-revenue function and action space (affine in prices)
  models/         base, gbm (LightGBM/XGBoost), neural (DeepSets), losses (SPO+)
  specs.py        the 11 compared methods and their Optuna search spaces
  experiment.py   nested walk-forward tuning, calibration model, final model
  policy.py       decision rules, heuristics, outcome metrics
  conformal.py    adaptive conformal floors
  stats.py        block bootstrap, DM test, Holm, Model Confidence Set
  analysis.py     every table: outcomes, floors, comparisons, sweeps, AUC
  silence.py      Contribution 3 tests
  decomp.py, leakage.py   Contribution 1
scripts/          run_experiments, run_silence, run_leakage, run_foundation, analyze
tests/            data, leakage-safety, SPO+, conformal, stats, decomposition, models, pipeline
results/          <crop>/tables, figures, summary.json, silence/, leakage/ ; cache/ (predictions)
docs/             METHODOLOGY.md, RESULTS.md
```

## Reproduce

```powershell
cd research
python -m venv .venv --system-site-packages        # needs torch, lightgbm, xgboost, statsmodels
.venv\Scripts\python -m pip install optuna matplotlib pytest pyarrow chronos-forecasting
.venv\Scripts\python -m pytest                                              # 57 tests, ~1 min
.venv\Scripts\python scripts\run_experiments.py --crop Tomato --jobs 16     # nested tuning grid (~1.5 h on 32 cores)
.venv\Scripts\python scripts\analyze.py --crop Tomato                       # tables + figures
.venv\Scripts\python scripts\run_silence.py --crop Tomato                   # Contribution 3
.venv\Scripts\python scripts\run_leakage.py --crop Tomato                   # Contribution 1
.venv\Scripts\python scripts\run_foundation.py --crop Tomato                # zero-shot baseline
```

Data are read from `../datasets/year_data/` (portal exports; see METHODOLOGY §1). Predictions are cached in
`results/cache/`, so every script is resumable and `analyze.py` is fast.

## Guarantees the code enforces

* No synthetic data; every price is a portal record. Test fixtures are fabricated only to exercise code.
* Features at index *s* never depend on days after *s* (property tests perturb the future and compare).
* Hyper-parameters are tuned only on inner validation blocks strictly before the outer test block, with a K+2-day gap.
* The conformal floor never reads an outcome before its sale date has passed.
* Calibration residuals come from a model fitted before the calibration block (never in-sample).
