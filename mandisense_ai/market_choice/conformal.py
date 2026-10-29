"""Adaptive conformal revenue floors with delayed feedback.

For the recommended action a_t with predicted revenue r_hat and recent error
scale sigma, the floor is L = r_hat - q * sigma and the recommendation is
argmax L. q is the conformal quantile of past normalised scores of
recommended actions; alpha_t follows adaptive conformal inference
(Gibbs and Candes 2021). Outcomes resolve K days after the sale, so a score is
released only when its sale date is strictly in the past.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from mandisense_ai.market_choice.config import CALIBRATION_WINDOW, DEFAULT_ALPHA, K_MAX

NEG = -1e12
EPS = 1.0
GAMMA = 0.01
MIN_SCORES = 30
DEFAULT_Q = 1.5


def conformal_quantile(scores: np.ndarray, alpha: float, default: float = DEFAULT_Q) -> float:
    """Finite-sample conformal quantile of the scores at level 1 - alpha."""
    if len(scores) < MIN_SCORES:
        return default
    level = float(np.clip(1.0 - alpha, 0.5, 0.995))
    n = len(scores)
    k = min(int(np.ceil((n + 1) * level)), n)
    return float(np.sort(scores)[k - 1])


@dataclass
class FloorRun:
    chosen: np.ndarray            # (n, O)
    floor: np.ndarray             # (n, O)
    q: np.ndarray                 # (n, O)
    alpha_t: np.ndarray           # (n, O)
    scores: List[np.ndarray]      # per origin: resolved normalised scores of recommended actions (chronological)
    sigma: np.ndarray             # (A,) final error scale per action (origin-independent)


def run_floor(r_hat: np.ndarray, R: np.ndarray, amask: np.ndarray, sale_day: np.ndarray, today: np.ndarray,
              alpha: float = DEFAULT_ALPHA, gamma: float = GAMMA, window: int = CALIBRATION_WINDOW,
              halflife: int = 60) -> FloorRun:
    """Online floor procedure over a contiguous stretch of decision days.

    r_hat, R : (n, O, A) predicted and realised revenue (R is read only once its sale date has passed)
    amask    : (n, A) offered actions;  sale_day, today : (n,) panel day indices
    """
    n, O, A = r_hat.shape
    chosen = np.zeros((n, O), dtype=int)
    floor = np.zeros((n, O))
    qs = np.zeros((n, O))
    alphas = np.zeros((n, O))
    lam = 0.5 ** (1.0 / halflife)
    all_scores: List[np.ndarray] = []
    sigma_final = np.full(A, np.nan)

    for o in range(O):
        alpha_t = alpha
        ew = np.full(A, np.nan)
        scores: List[float] = []
        pending: List[tuple] = []
        released = 0
        for d in range(n):
            while released < d and sale_day[released] + K_MAX <= today[d]:
                e = r_hat[released, o] - R[released, o]
                upd = np.where(np.isnan(ew), e ** 2, lam * ew + (1 - lam) * e ** 2)
                ew = np.where(amask[released], upd, ew)
                a_prev, fl_prev, sg_prev = pending[released]
                scores.append(float((r_hat[released, o, a_prev] - R[released, o, a_prev]) / sg_prev))
                alpha_t = alpha_t + gamma * (alpha - float(R[released, o, a_prev] < fl_prev))
                released += 1
            pooled = np.sqrt(np.nanmean(ew)) if np.isfinite(ew).any() else 500.0
            sigma = np.maximum(np.where(np.isnan(ew), pooled, np.sqrt(np.maximum(ew, 0.0))), EPS)
            win = np.asarray(scores[-window:])
            q = conformal_quantile(win, alpha_t)
            L = r_hat[d, o] - q * sigma
            a = int(np.where(amask[d], L, NEG).argmax())
            chosen[d, o], floor[d, o], qs[d, o], alphas[d, o] = a, L[a], q, alpha_t
            pending.append((a, L[a], sigma[a]))
        all_scores.append(np.asarray(scores))
        sigma_final = np.where(np.isnan(ew), np.nan, np.sqrt(np.maximum(ew, 0.0)))
    return FloorRun(chosen=chosen, floor=floor, q=qs, alpha_t=alphas, scores=all_scores, sigma=sigma_final)
