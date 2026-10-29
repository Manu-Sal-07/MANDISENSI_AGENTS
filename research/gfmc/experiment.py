"""Nested walk-forward training and prediction.

For every outer test block [a, b):

  * inner folds (hyper-parameter search only): two consecutive 6-month blocks
    before `a`; each is scored by a model trained strictly before it (with a
    K+2 day gap so no target window overlaps the validation block);
  * best hyper-parameters are refit twice:
        calibration model  - trained before the LAST inner block, predicts it.
                             Its out-of-sample errors warm-start the conformal
                             floor, so calibration is never in-sample;
        final model        - trained on everything before `a`, predicts [a, b).

Nothing tuned or fitted ever sees an outer test day.
"""

from __future__ import annotations

import json
import zlib
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from gfmc import policy as P
from gfmc.config import CACHE_DIR, DEFAULT_ECON, K_MAX, OUTER_FOLDS, SEED, Economics
from gfmc.data import loader, panel
from gfmc.dataset import DecisionData, build_decision_data, econ_for
from gfmc.models.gbm import filled_targets
from gfmc.specs import SPEC_BY_NAME, Spec, build, suggest

GAP_DAYS = K_MAX + 2
INNER_BLOCK_DAYS = 183


@dataclass(frozen=True)
class FoldPlan:
    fold: int
    test: Tuple[str, str]
    train_idx: np.ndarray          # final model training days
    calib_train_idx: np.ndarray    # calibration model training days
    calib_idx: np.ndarray          # last inner block (calibration stretch)
    test_idx: np.ndarray
    inner: Tuple[Tuple[np.ndarray, np.ndarray], ...]    # (train_idx, val_idx) pairs


def make_plan(dd: DecisionData, fold: int, folds=OUTER_FOLDS) -> FoldPlan:
    a, b = pd.Timestamp(folds[fold][0]), pd.Timestamp(folds[fold][1])
    gap = pd.Timedelta(days=GAP_DAYS)
    blk = pd.Timedelta(days=INNER_BLOCK_DAYS)
    v2s, v1s = a - blk, a - 2 * blk
    d = dd.dates
    valid = dd.valid
    sel = lambda lo, hi: np.flatnonzero((d >= lo) & (d < hi) & valid)
    start = d[0]
    inner = ((sel(start, v1s - gap), sel(v1s, v2s)), (sel(start, v2s - gap), sel(v2s, a)))
    return FoldPlan(fold=fold, test=(str(a.date()), str(b.date())), train_idx=sel(start, a - gap),
                    calib_train_idx=sel(start, v2s - gap), calib_idx=sel(v2s, a), test_idx=sel(a, b), inner=inner)


# --------------------------------------------------------------- objectives
def _val_objective(spec: Spec, dd: DecisionData, ec: Economics, idx: np.ndarray, yhat: np.ndarray) -> float:
    if spec.tune_on == "regret":
        am = dd.action_mask()[idx]
        R = P.realised_revenue(dd, idx, ec)
        r_hat = P.revenue_from_logret(dd, idx, yhat, ec)
        out = P.score(R, am, P.choose(r_hat, am), dd, idx)
        return float(out.regret.mean())
    # forecast loss on the model's native labels (Huber, as in training)
    if spec.native_labels == "filled":
        y = filled_targets(dd, idx, ec)
        m = np.broadcast_to(dd.elig[idx][:, :, None], y.shape)
    else:
        y = np.nan_to_num(dd.Y[idx])
        m = dd.obs[idx] & dd.elig[idx][:, :, None]
    e = np.abs(yhat - y)[m]
    delta = 0.15
    return float(np.where(e <= delta, 0.5 * e ** 2, delta * (e - 0.5 * delta)).mean())


def tune(spec: Spec, dd: DecisionData, ec: Economics, plan: FoldPlan, cols: np.ndarray, n_trials: int,
         seed: int) -> Dict:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    if spec.tune_on == "none" or n_trials <= 0 or spec.family == "rw":
        return {}

    def objective(trial) -> float:
        hp = suggest(spec, trial)
        vals = []
        for tr, va in plan.inner:
            m = build(spec, hp).fit(dd, tr, ec, cols)
            vals.append(_val_objective(spec, dd, ec, va, m.predict(dd, va)))
        return float(np.mean(vals))

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return dict(study.best_params)


# ------------------------------------------------------------------- task
def run_task(spec_name: str, fold: int, crop: str = "Tomato", n_trials: int = 16, final_seeds: int = 3,
             cache: bool = True, ec: Optional[Economics] = None) -> Dict:
    """Tune, refit and predict one (model, fold). Resumable via an on-disk cache."""
    warnings.filterwarnings("ignore")
    out_dir = CACHE_DIR / crop.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"fold{fold}_{spec_name}.npz"
    if cache and path.exists():
        return {"spec": spec_name, "fold": fold, "cached": True}

    spec = SPEC_BY_NAME[spec_name]
    history, _ = loader.load_history()
    pan = panel.build_panel(history, crop)
    dd = build_decision_data(pan)
    ec = ec or econ_for(crop)
    plan = make_plan(dd, fold)
    cols = dd.fs.cols(*spec.groups)

    t0 = time.time()
    seed = SEED + 1000 * fold + (zlib.crc32(spec_name.encode()) % 997)
    best = tune(spec, dd, ec, plan, cols, n_trials, seed)
    tune_s = time.time() - t0

    cal_model = build(spec, best, n_seeds=final_seeds).fit(dd, plan.calib_train_idx, ec, cols)
    y_cal = cal_model.predict(dd, plan.calib_idx)
    fin = build(spec, best, n_seeds=final_seeds).fit(dd, plan.train_idx, ec, cols)
    y_test = fin.predict(dd, plan.test_idx)
    rep = getattr(fin, "report_prob_", None)
    rep_cal = getattr(cal_model, "report_prob_", None)

    np.savez_compressed(path, y_test=y_test, y_cal=y_cal, test_idx=plan.test_idx, calib_idx=plan.calib_idx,
                        report_test=rep if rep is not None else np.zeros(0),
                        report_cal=rep_cal if rep_cal is not None else np.zeros(0),
                        hp=json.dumps(best), seconds=time.time() - t0, tune_seconds=tune_s)
    return {"spec": spec_name, "fold": fold, "cached": False, "seconds": time.time() - t0, "hp": best}


def load_task(spec_name: str, fold: int, crop: str = "Tomato") -> Dict:
    z = np.load(CACHE_DIR / crop.lower() / f"fold{fold}_{spec_name}.npz", allow_pickle=False)
    return {k: (z[k] if k != "hp" else json.loads(str(z[k]))) for k in z.files}
