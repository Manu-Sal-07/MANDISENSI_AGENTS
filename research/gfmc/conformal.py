"""Adaptive conformal revenue floors.

Goal. For every recommendation, state a *floor* L such that the realised net
revenue of the recommended action is at least L with probability >= 1 - alpha,
without assuming a distribution, exchangeability, or a correct model.

Method. Let a_t be the action chosen on day t, r_hat its predicted revenue and
sigma_hat its recent error scale. The normalised score

        s_t = (r_hat_t(a_t) - R_t(a_t)) / sigma_hat_t(a_t)

measures how far the outcome fell short of the prediction. The floor is

        L_t(a) = r_hat_t(a) - q_t * sigma_hat_t(a),

and the action recommended is argmax_a L_t(a): the best *guaranteed* revenue.
q_t is the (1 - alpha_t) empirical quantile of past scores of *recommended*
actions, and alpha_t is updated by adaptive conformal inference (Gibbs &
Candes, 2021):

        alpha_{t+1} = alpha_t + gamma * (alpha - 1[R_t(a_t) < L_t(a_t)]).

ACI's guarantee is on the long-run average miscoverage of the sequence
actually observed, for ANY sequence of predictions, which includes sequences
produced by the adaptive selection above. Feedback is delayed: the outcome of
a k-day hold is known k days after the sale, so a score becomes available
only when the sale date has passed (we use sale-date <= today - 1, strictly
past data).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from gfmc.config import DEFAULT_CONFORMAL, K_MAX, Conformal

NEG = -1e12
EPS = 1.0


@dataclass
class FloorResult:
    chosen: np.ndarray       # (n, O) recommended action
    floor: np.ndarray        # (n, O) guaranteed revenue of that action
    q: np.ndarray            # (n, O) multiplier used
    alpha_t: np.ndarray      # (n, O) ACI level used
    sigma: np.ndarray        # (n, O) error scale of the chosen action


def _quantile_level(scores: np.ndarray, level: float, default: float) -> float:
    if len(scores) == 0:
        return default
    level = float(np.clip(level, 0.5, 0.995))
    # conformal finite-sample quantile: ceil((n+1) * level) / n
    n = len(scores)
    k = min(int(np.ceil((n + 1) * level)), n)
    return float(np.sort(scores)[k - 1])


def run_floor(r_hat: np.ndarray, R: np.ndarray, amask: np.ndarray, sale_day: np.ndarray, today: np.ndarray,
              conf: Conformal = DEFAULT_CONFORMAL, adaptive: bool = True, use_scale: bool = True,
              halflife: int = 60, fixed_q: Optional[float] = None) -> FloorResult:
    """Run the online floor procedure over a contiguous stretch of decision days.

    r_hat, R : (n, O, A) predicted / realised revenue (R is used ONLY when it
               has become known, i.e. for days whose sales have completed)
    amask    : (n, A)    offered actions
    sale_day : (n,)      panel day index t of each decision
    fixed_q  : if given, use this constant multiplier (a naive Gaussian-style floor) instead of calibrating
    today    : (n,)      panel day index of the information cut-off for the decision (t - 1)
    """
    n, O, A = r_hat.shape
    chosen = np.zeros((n, O), dtype=int)
    floor = np.zeros((n, O))
    qs = np.zeros((n, O))
    alphas = np.zeros((n, O))
    sig = np.zeros((n, O))
    lam = 0.5 ** (1.0 / halflife)
    default_q = 1.5

    for o in range(O):
        alpha_t = conf.alpha
        ew = np.full(A, np.nan)               # EWMA of squared errors per action
        scores: list[float] = []
        pending: list[tuple] = []             # (decision pos, action, floor, sigma_used)
        released = 0                          # decisions fully resolved so far
        for d in range(n):
            # 1) resolve every earlier decision whose last sale day is strictly in the past
            while released < d and sale_day[released] + K_MAX <= today[d]:
                e = r_hat[released, o] - R[released, o]
                ok = amask[released]
                upd = np.where(np.isnan(ew), e ** 2, lam * ew + (1 - lam) * e ** 2)
                ew = np.where(ok, upd, ew)
                _, a_prev, fl_prev, sg_prev = pending[released]
                s = (r_hat[released, o, a_prev] - R[released, o, a_prev]) / sg_prev
                scores.append(float(s))
                if adaptive:
                    err = float(R[released, o, a_prev] < fl_prev)
                    alpha_t = alpha_t + conf.gamma * (conf.alpha - err)
                released += 1

            # 2) scale per action (pooled fallback until an action has history)
            if use_scale:
                pooled = np.sqrt(np.nanmean(ew)) if np.isfinite(ew).any() else 500.0
                sigma = np.where(np.isnan(ew), pooled, np.sqrt(np.maximum(ew, 0.0)))
                sigma = np.maximum(sigma, EPS)
            else:
                sigma = np.ones(A) * 100.0

            # 3) conformal multiplier from the recent resolved scores of recommended actions
            window = np.asarray(scores[-conf.window:])
            if fixed_q is not None:
                q = float(fixed_q)               # naive floor: no calibration, no adaptation
            else:
                q = _quantile_level(window, 1.0 - alpha_t, default_q) if len(window) >= conf.min_scores else default_q

            L = r_hat[d, o] - q * sigma
            a = int(np.where(amask[d], L, NEG).argmax())
            chosen[d, o], floor[d, o], qs[d, o], alphas[d, o], sig[d, o] = a, L[a], q, alpha_t, sigma[a]
            pending.append((d, a, L[a], sigma[a]))
    return FloorResult(chosen=chosen, floor=floor, q=qs, alpha_t=alphas, sigma=sig)


def violation_rate(R: np.ndarray, res: FloorResult, mask_days: Optional[np.ndarray] = None) -> float:
    got = np.take_along_axis(R, res.chosen[..., None], -1)[..., 0]
    v = got < res.floor
    return float(v[mask_days].mean()) if mask_days is not None else float(v.mean())
