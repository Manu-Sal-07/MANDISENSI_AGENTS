"""Formal tests of the *market silence is informative* hypothesis (Contribution 3).

Two separate questions, each answered with a nested-model comparison under the
same walk-forward folds as the main study and *fixed* (untuned) hyper-parameters
so that neither side gets a tuning advantage:

  A. Reporting.  Does the network-silence feature group improve prediction of
     whether a mandi reports on a given sale day (AUC, log-loss)?
  B. Returns.    Does it improve prediction of the next-day log price return at
     markets that do report (Huber loss / MAE, Diebold-Mariano on squared error)?

Significance is assessed three ways: a day-level moving-block bootstrap of the
paired metric difference, a Diebold-Mariano test (B), and a permutation test
that shuffles the silence features across days *within blocks* (null: silence
carries no information beyond the base features, but keeps its marginal
distribution and short-range autocorrelation).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from gfmc import stats
from gfmc.config import N_HOLD, OUTER_FOLDS, SEED
from gfmc.dataset import DecisionData
from gfmc.experiment import make_plan

PERM_BLOCK = 14


def _stack(dd: DecisionData, idx: np.ndarray, cols: np.ndarray, k: int):
    X = dd.X[idx][:, :, cols]
    n, M, _ = X.shape
    mk = np.broadcast_to(np.arange(M), (n, M))[:, :, None].astype(float)
    return np.concatenate([X, mk], axis=2), dd.elig[idx], dd.obs[idx][:, :, k]


def _permute_blocks(X: np.ndarray, cols: np.ndarray, rng: np.random.Generator, block: int = PERM_BLOCK) -> np.ndarray:
    """Shuffle whole blocks of days for the given feature columns (all markets together)."""
    n = X.shape[0]
    nb = int(np.ceil(n / block))
    order = rng.permutation(nb)
    idx = np.concatenate([np.arange(b * block, min((b + 1) * block, n)) for b in order])[:n]
    out = X.copy()
    out[:, :, cols] = X[idx][:, :, cols]
    return out


def _clf(seed: int):
    import lightgbm as lgb

    return lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=50,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0,
                              random_state=seed, n_jobs=4, verbosity=-1)


def _reg(seed: int):
    import lightgbm as lgb

    return lgb.LGBMRegressor(objective="huber", alpha=0.15, n_estimators=200, learning_rate=0.05, num_leaves=15,
                             min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                             reg_lambda=5.0, random_state=seed, n_jobs=4, verbosity=-1)


def reporting_test(dd: DecisionData, folds=range(len(OUTER_FOLDS)), perms: int = 30) -> Dict:
    """Question A. Returns per-fold and pooled AUC / log-loss for base vs base+silence."""
    base, full = dd.fs.groups["base"], np.concatenate([dd.fs.groups["base"], dd.fs.groups["silence"]])
    sil = np.arange(len(base), len(full))                         # silence columns inside the `full` layout
    rows, day_auc_diff, cell_store = [], [], []
    rng = np.random.default_rng(SEED)
    for f in folds:
        pl = make_plan(dd, f)
        for k in range(N_HOLD):
            Xtr_b, etr, ytr = _stack(dd, pl.train_idx, base, k)
            Xtr_f, _, _ = _stack(dd, pl.train_idx, full, k)
            Xte_b, ete, yte = _stack(dd, pl.test_idx, base, k)
            Xte_f, _, _ = _stack(dd, pl.test_idx, full, k)
            mb = _clf(SEED + f).fit(Xtr_b[etr], ytr[etr].astype(int), categorical_feature=[Xtr_b.shape[2] - 1])
            mf = _clf(SEED + f).fit(Xtr_f[etr], ytr[etr].astype(int), categorical_feature=[Xtr_f.shape[2] - 1])
            pb = mb.predict_proba(Xte_b[ete])[:, 1]
            pf = mf.predict_proba(Xte_f[ete])[:, 1]
            y = yte[ete].astype(int)
            day = np.broadcast_to(np.arange(len(pl.test_idx))[:, None], ete.shape)[ete]
            # permutation null for the silence block (same fitted `mf`, shuffled silence at test time)
            null = []
            for _ in range(perms):
                Xp = _permute_blocks(Xte_f, sil, rng)
                null.append(roc_auc_score(y, mf.predict_proba(Xp[ete])[:, 1]))
            auc_b, auc_f = roc_auc_score(y, pb), roc_auc_score(y, pf)
            rows.append({"fold": f, "k": k, "n": len(y), "auc_base": auc_b, "auc_silence": auc_f,
                         "d_auc": auc_f - auc_b, "ll_base": log_loss(y, pb), "ll_silence": log_loss(y, pf),
                         "perm_p": float((np.sum(np.asarray(null) >= auc_f) + 1) / (len(null) + 1))})
            cell_store.append((y, pb, pf, day, f))
    per = pd.DataFrame(rows)

    # pooled paired bootstrap of the log-loss difference over days (cells are clustered within days)
    d_ll = []
    for y, pb, pf, day, f in cell_store:
        lb = -(y * np.log(np.clip(pb, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - pb, 1e-6, 1)))
        lf = -(y * np.log(np.clip(pf, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - pf, 1e-6, 1)))
        s = pd.Series(lf - lb).groupby(day).mean()
        d_ll.append(s.to_numpy())
    d_ll = np.concatenate(d_ll)
    m, lo, hi = stats.block_bootstrap_mean(d_ll, block=14, reps=4000, seed=1)
    pooled = {"mean_dlogloss": m, "ci_lo": lo, "ci_hi": hi, "mean_dAUC": float(per["d_auc"].mean()),
              "folds_improved": int((per.groupby("fold")["d_auc"].mean() > 0).sum()), "n_folds": int(per["fold"].nunique())}
    return {"per_fold_horizon": per, "pooled": pooled}


def returns_test(dd: DecisionData, folds=range(len(OUTER_FOLDS))) -> Dict:
    """Question B on the 1-day-ahead log return at markets that report."""
    base, full = dd.fs.groups["base"], np.concatenate([dd.fs.groups["base"], dd.fs.groups["silence"]])
    rows, loss_b_all, loss_f_all = [], [], []
    for f in folds:
        pl = make_plan(dd, f)
        ys_tr = np.nan_to_num(dd.Y[pl.train_idx][:, :, 0])
        otr = dd.obs[pl.train_idx][:, :, 0] & dd.elig[pl.train_idx]
        ys_te = np.nan_to_num(dd.Y[pl.test_idx][:, :, 0])
        ote = dd.obs[pl.test_idx][:, :, 0] & dd.elig[pl.test_idx]
        Xb_tr, _, _ = _stack(dd, pl.train_idx, base, 0)
        Xf_tr, _, _ = _stack(dd, pl.train_idx, full, 0)
        Xb_te, _, _ = _stack(dd, pl.test_idx, base, 0)
        Xf_te, _, _ = _stack(dd, pl.test_idx, full, 0)
        mb = _reg(SEED + f).fit(Xb_tr[otr], ys_tr[otr], categorical_feature=[Xb_tr.shape[2] - 1])
        mf = _reg(SEED + f).fit(Xf_tr[otr], ys_tr[otr], categorical_feature=[Xf_tr.shape[2] - 1])
        pb = mb.predict(Xb_te[ote])
        pf = mf.predict(Xf_te[ote])
        y = ys_te[ote]
        day = np.broadcast_to(np.arange(len(pl.test_idx))[:, None], ote.shape)[ote]
        sq_b = pd.Series((pb - y) ** 2).groupby(day).mean().to_numpy()
        sq_f = pd.Series((pf - y) ** 2).groupby(day).mean().to_numpy()
        loss_b_all.append(sq_b)
        loss_f_all.append(sq_f)
        rows.append({"fold": f, "n": len(y), "mae_base": float(np.abs(pb - y).mean()), "mae_silence": float(np.abs(pf - y).mean()),
                     "mae_rw": float(np.abs(y).mean()), "mse_base": float(((pb - y) ** 2).mean()),
                     "mse_silence": float(((pf - y) ** 2).mean())})
    per = pd.DataFrame(rows)
    lb, lf = np.concatenate(loss_b_all), np.concatenate(loss_f_all)
    rep = stats.paired_report(lf, lb, seed=3)             # negative = silence better
    return {"per_fold": per, "dm_silence_vs_base": rep}
