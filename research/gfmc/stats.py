"""Inference utilities: block bootstrap, HAC Diebold-Mariano, Holm, Model Confidence Set.

All comparisons are made on *daily* loss series (revenue averaged over farmer
origins) because the five origins are strongly dependent on each other.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

import numpy as np
from scipy import stats


def block_bootstrap_mean(x: np.ndarray, block: int = 14, reps: int = 4000, seed: int = 0) -> Tuple[float, float, float]:
    """Mean and 95% moving-block-bootstrap CI of a (serially dependent) series."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, max(n - block, 1), size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n]
    means = x[idx].mean(1)
    return float(x.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def newey_west_var(d: np.ndarray, lag: int) -> float:
    d = d - d.mean()
    n = len(d)
    v = np.dot(d, d) / n
    for k in range(1, lag + 1):
        w = 1 - k / (lag + 1)
        v += 2 * w * np.dot(d[k:], d[:-k]) / n
    return v / n


def dm_test(loss_a: np.ndarray, loss_b: np.ndarray, lag: int = 7) -> Dict[str, float]:
    """Two-sided Diebold-Mariano test on d = loss_a - loss_b (negative favours A)."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    var = newey_west_var(d, lag)
    stat = d.mean() / np.sqrt(var) if var > 0 else 0.0
    n = len(d)
    stat *= np.sqrt((n + 1 - 2 * 1 + 1 * (1 - 1) / n) / n) if n > 2 else 1.0     # Harvey small-sample correction (h=1)
    p = 2 * (1 - stats.t.cdf(abs(stat), df=n - 1))
    return {"mean_diff": float(d.mean()), "stat": float(stat), "p": float(p)}


def holm(pvals: Sequence[float]) -> np.ndarray:
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(running, 1.0)
    return adj


def paired_report(loss_a: np.ndarray, loss_b: np.ndarray, block: int = 14, seed: int = 0) -> Dict[str, float]:
    """Mean paired loss difference with bootstrap CI, DM p-value and win rate."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    m, lo, hi = block_bootstrap_mean(d, block=block, seed=seed)
    out = dm_test(loss_a, loss_b)
    out.update({"ci_lo": lo, "ci_hi": hi, "win_rate_a": float((d < 0).mean())})
    return out


def model_confidence_set(losses: Dict[str, np.ndarray], alpha: float = 0.10, block: int = 14, reps: int = 2000,
                         seed: int = 0) -> Dict[str, object]:
    """Hansen-Lunde-Nason MCS (T_max statistic) on daily losses; returns surviving models and p-values."""
    names = list(losses)
    L = np.column_stack([losses[n] for n in names])           # (T, m)
    T = L.shape[0]
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(T / block))
    starts = rng.integers(0, max(T - block, 1), size=(reps, nb))
    boot_idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :T]

    alive = list(range(len(names)))
    mcs_p = {n: 1.0 for n in names}
    pvals_run = 0.0
    while len(alive) > 1:
        sub = L[:, alive]
        m = len(alive)
        dbar_i = sub.mean(0) - sub.mean()                      # deviation from the cross-model mean
        boot_means = np.stack([sub[ix].mean(0) for ix in boot_idx])         # (reps, m)
        sd = (boot_means - boot_means.mean(1, keepdims=True)).std(0, ddof=1)
        sd = np.where(sd < 1e-12, 1e-12, sd)
        t_i = dbar_i / sd
        t_stat = t_i.max()
        t_boot = ((boot_means - boot_means.mean(1, keepdims=True)) - (sub.mean(0) - sub.mean())[None, :]) / sd[None, :]
        p = float((t_boot.max(1) >= t_stat).mean())
        pvals_run = max(pvals_run, p)
        worst = alive[int(np.argmax(t_i))]
        mcs_p[names[worst]] = pvals_run
        if p > alpha:
            break
        alive.remove(worst)
    return {"survivors": [names[i] for i in alive], "p_values": mcs_p}
