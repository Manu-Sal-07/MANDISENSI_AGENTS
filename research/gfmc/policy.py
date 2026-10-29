"""Decision rules and decision-level metrics.

A *policy* turns predicted revenues r_hat (n, O, A) into one chosen action per
(day, origin). All learned models share the same plug-in rule (argmax of
predicted revenue); heuristics are expressed as pseudo-predictions so that
every method flows through the same evaluation code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from gfmc import econ as E
from gfmc.config import N_HOLD, Economics
from gfmc.data import registry
from gfmc.dataset import DecisionData
from gfmc.models.base import price_from_logret

NEG = -1e12


def origin_list(origins: Dict[str, Tuple[float, float]] | None = None):
    o = origins or registry.ORIGINS
    return list(o.keys()), list(o.values())


def revenue_from_logret(dd: DecisionData, idx: np.ndarray, yhat: np.ndarray, econ_: Economics,
                        origins: Dict[str, Tuple[float, float]] | None = None) -> np.ndarray:
    """(n, O, A) predicted revenue implied by predicted log-returns."""
    _, coords = origin_list(origins)
    price = price_from_logret(dd, idx, yhat)                              # (n, M, K)
    w = dd.elig[idx].astype(float)
    gate = (price[:, :, 0] * w).sum(1) / np.maximum(w.sum(1), 1.0)
    out = [E.revenue_from_prices(price, gate, dd.panel.dist_km(c), econ_) for c in coords]
    return np.stack(out, axis=1)


def realised_revenue(dd: DecisionData, idx: np.ndarray, econ_: Economics,
                     origins: Dict[str, Tuple[float, float]] | None = None) -> np.ndarray:
    _, coords = origin_list(origins)
    return np.stack([dd.realised_revenue(c, econ_)[idx] for c in coords], axis=1)


def choose(r_hat: np.ndarray, amask: np.ndarray) -> np.ndarray:
    """(n, O) argmax of predicted revenue over offered actions."""
    return np.where(amask[:, None, :], r_hat, NEG).argmax(-1)


# ---------------------------------------------------------------- heuristics
def heuristic_scores(name: str, dd: DecisionData, idx: np.ndarray, econ_: Economics,
                     origins: Dict[str, Tuple[float, float]] | None = None) -> np.ndarray:
    """Pseudo-predicted revenues that make a heuristic argmax-compatible, shape (n, O, A)."""
    names, coords = origin_list(origins)
    n, M, A = len(idx), dd.M, E.n_actions(dd.M)
    out = np.full((n, len(coords), A), NEG)
    elig = dd.elig[idx]
    ref = np.exp(np.nan_to_num(dd.ref_lp[idx], nan=0.0))
    for o, c in enumerate(coords):
        dist = dd.panel.dist_km(c)
        if name == "nearest_today":                         # nearest offered mandi, sell today
            s = np.where(elig, -dist[None, :], NEG)
            out[:, o, 0:M * N_HOLD:N_HOLD] = s
        elif name == "highest_yesterday":                   # cost-blind: mandi with the highest last price, sell today
            s = np.where(elig, ref, NEG)
            out[:, o, 0:M * N_HOLD:N_HOLD] = s
        elif name == "trailing_best":                       # best 7-day mean price, sell today
            lp = dd.fs.lp[dd.days[idx][:, None] - 1 - np.arange(7)[None, :]]          # (n, 7, M)
            s = np.where(elig, np.exp(np.nanmean(lp, axis=1)), NEG)
            out[:, o, 0:M * N_HOLD:N_HOLD] = s
        elif name == "farm_gate":
            out[:, o, -1] = 1.0
        else:
            raise KeyError(name)
    return out


# ------------------------------------------------------------------- metrics
@dataclass
class Outcome:
    chosen: np.ndarray       # (n, O)
    revenue: np.ndarray      # (n, O) realised
    oracle: np.ndarray       # (n, O) hindsight best among offered actions
    fallback: np.ndarray     # (n, O) bool: chosen mandi was silent on the sale day

    @property
    def regret(self) -> np.ndarray:
        return self.oracle - self.revenue


def score(R: np.ndarray, amask: np.ndarray, chosen: np.ndarray, dd: DecisionData, idx: np.ndarray) -> Outcome:
    n, O, A = R.shape
    got = np.take_along_axis(R, chosen[..., None], -1)[..., 0]
    oracle = np.where(amask[:, None, :], R, NEG).max(-1)
    M = dd.M
    is_mkt = chosen < M * N_HOLD
    m = np.where(is_mkt, chosen // N_HOLD, 0)
    k = np.where(is_mkt, chosen % N_HOLD, 0)
    silent = ~dd.obs[idx][np.arange(n)[:, None], m, k]
    return Outcome(chosen=chosen, revenue=got, oracle=oracle, fallback=silent & is_mkt)


def cvar(x: np.ndarray, level: float = 0.10) -> float:
    """Mean of the worst `level` share of outcomes (lower tail, since x is revenue)."""
    flat = np.sort(np.asarray(x).ravel())
    k = max(int(np.ceil(level * len(flat))), 1)
    return float(flat[:k].mean())


def summarise(out: Outcome, baseline_revenue: np.ndarray | None = None) -> Dict[str, float]:
    d = {
        "mean_revenue": float(out.revenue.mean()),
        "mean_regret": float(out.regret.mean()),
        "oracle": float(out.oracle.mean()),
        "cvar10_revenue": cvar(out.revenue, 0.10),
        "p10_revenue": float(np.quantile(out.revenue, 0.10)),
        "fallback_rate": float(out.fallback.mean()),
    }
    if baseline_revenue is not None:
        gap = out.oracle.mean() - baseline_revenue.mean()
        d["share_of_oracle_gap_closed"] = float((out.revenue.mean() - baseline_revenue.mean()) / gap) if gap > 0 else float("nan")
    return d
