"""Assemble every reported number from the cached out-of-sample predictions.

Nothing here trains a model. All metrics are computed on the five outer test
blocks only; the calibration stretch before each block is used solely to
warm-start the conformal floor and is never scored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from gfmc import conformal, policy as P, stats
from gfmc.config import (DEFAULT_CONFORMAL, N_HOLD, OUTER_FOLDS, Conformal, Economics)
from gfmc.data import loader, panel
from gfmc.dataset import DecisionData, build_decision_data, econ_for
from gfmc.experiment import load_task, make_plan
from gfmc.models.gbm import filled_targets
from gfmc.specs import SPEC_BY_NAME, SPECS

HEURISTICS = ("nearest_today", "highest_yesterday", "trailing_best", "farm_gate")
REFERENCE = "nearest_today"          # 0% of the oracle gap
STRONG_HEURISTIC = "highest_yesterday"


@dataclass
class Fold:
    plan: object
    test_idx: np.ndarray
    calib_idx: np.ndarray


class Study:
    """Out-of-sample decision study for one crop."""

    def __init__(self, crop: str = "Tomato", econ: Optional[Economics] = None, specs: Optional[Sequence[str]] = None,
                 folds: Optional[Sequence[int]] = None):
        history, self.load_report = loader.load_history()
        self.crop = crop
        self.dd: DecisionData = build_decision_data(panel.build_panel(history, crop))
        self.econ = econ or econ_for(crop)
        self.fold_ids = list(folds) if folds is not None else list(range(len(OUTER_FOLDS)))
        self.plans = {f: make_plan(self.dd, f) for f in self.fold_ids}
        self.specs = [s for s in (specs or [s.name for s in SPECS])]
        self.pred: Dict[Tuple[str, int], Dict] = {}
        for s in self.specs:
            for f in self.fold_ids:
                try:
                    self.pred[(s, f)] = load_task(s, f, crop)
                except FileNotFoundError:
                    pass
        self.available = [s for s in self.specs if all((s, f) in self.pred for f in self.fold_ids)]
        self._test_idx = np.concatenate([self.plans[f].test_idx for f in self.fold_ids])
        self._fold_of = np.concatenate([np.full(len(self.plans[f].test_idx), f) for f in self.fold_ids])

    # ------------------------------------------------------------ helpers
    @property
    def test_idx(self) -> np.ndarray:
        return self._test_idx

    @property
    def test_dates(self) -> pd.DatetimeIndex:
        return self.dd.dates[self._test_idx]

    def _R(self, idx: np.ndarray, econ: Optional[Economics] = None) -> np.ndarray:
        return P.realised_revenue(self.dd, idx, econ or self.econ)

    def _amask(self, idx: np.ndarray) -> np.ndarray:
        return self.dd.action_mask()[idx]

    def yhat(self, spec: str, split: str = "test") -> np.ndarray:
        key = "y_test" if split == "test" else "y_cal"
        return np.concatenate([self.pred[(spec, f)][key] for f in self.fold_ids]) if split == "test" else None

    def r_hat(self, spec: str, fold: int, split: str, econ: Optional[Economics] = None) -> np.ndarray:
        z = self.pred[(spec, fold)]
        idx = self.plans[fold].test_idx if split == "test" else self.plans[fold].calib_idx
        return P.revenue_from_logret(self.dd, idx, z["y_test" if split == "test" else "y_cal"], econ or self.econ)

    # ---------------------------------------------------------- outcomes
    def outcome(self, method: str, econ: Optional[Economics] = None) -> P.Outcome:
        """Pooled out-of-sample Outcome of a learned spec or a heuristic (plug-in argmax policy)."""
        ec = econ or self.econ
        parts = []
        for f in self.fold_ids:
            idx = self.plans[f].test_idx
            am, R = self._amask(idx), self._R(idx, ec)
            r_hat = (P.heuristic_scores(method, self.dd, idx, ec) if method in HEURISTICS
                     else self.r_hat(method, f, "test", ec))
            parts.append(P.score(R, am, P.choose(r_hat, am), self.dd, idx))
        return P.Outcome(*(np.concatenate([getattr(p, a) for p in parts]) for a in ("chosen", "revenue", "oracle", "fallback")))

    def daily(self, out: P.Outcome, kind: str = "revenue") -> np.ndarray:
        """(n_days,) value averaged over the five farmer origins."""
        v = out.revenue if kind == "revenue" else out.regret
        return v.mean(1)

    # ------------------------------------------------------------ tables
    def main_table(self, econ: Optional[Economics] = None) -> pd.DataFrame:
        names = list(HEURISTICS) + self.available
        outs = {n: self.outcome(n, econ) for n in names}
        ref = outs[REFERENCE].revenue
        strong = outs[STRONG_HEURISTIC].revenue
        rows = []
        for i, n in enumerate(names):
            o = outs[n]
            m, lo, hi = stats.block_bootstrap_mean(self.daily(o), seed=i)
            s = P.summarise(o, ref)
            gap_strong = (o.revenue.mean() - strong.mean()) / max(o.oracle.mean() - strong.mean(), 1e-9)
            rows.append({"method": n, "revenue": m, "rev_ci_lo": lo, "rev_ci_hi": hi, "regret": s["mean_regret"],
                         "gap_closed_vs_nearest": s["share_of_oracle_gap_closed"], "gap_closed_vs_yday": gap_strong,
                         "cvar10": s["cvar10_revenue"], "p10": s["p10_revenue"], "fallback_rate": s["fallback_rate"]})
        t = pd.DataFrame(rows)
        t.loc[len(t)] = {"method": "oracle(hindsight)", "revenue": float(outs[REFERENCE].oracle.mean()),
                         "regret": 0.0, "gap_closed_vs_nearest": 1.0}
        return t

    def per_fold_table(self, methods: Sequence[str]) -> pd.DataFrame:
        rows = []
        for n in methods:
            o = self.outcome(n)
            for f in self.fold_ids:
                m = self._fold_of == f
                rows.append({"method": n, "fold": f, "test": f"{OUTER_FOLDS[f][0]}..{OUTER_FOLDS[f][1]}",
                             "revenue": float(o.revenue[m].mean()), "regret": float(o.regret[m].mean())})
        return pd.DataFrame(rows)

    def per_origin_table(self, methods: Sequence[str]) -> pd.DataFrame:
        from gfmc.data import registry

        rows = []
        for n in methods:
            o = self.outcome(n)
            for j, origin in enumerate(registry.ORIGINS):
                rows.append({"method": n, "origin": origin, "revenue": float(o.revenue[:, j].mean()),
                             "regret": float(o.regret[:, j].mean())})
        return pd.DataFrame(rows)

    # ------------------------------------------------------ comparisons
    def comparisons(self, pairs: Sequence[Tuple[str, str, str]]) -> pd.DataFrame:
        """(A, B, label) -> paired regret difference A - B (negative = A better), Holm-adjusted."""
        cache: Dict[str, np.ndarray] = {}

        def reg(n):
            if n not in cache:
                cache[n] = self.daily(self.outcome(n), "regret")
            return cache[n]

        rows = []
        for k, (a, b, label) in enumerate(pairs):
            if a not in self.available + list(HEURISTICS) or b not in self.available + list(HEURISTICS):
                continue
            r = stats.paired_report(reg(a), reg(b), seed=k)
            rows.append({"comparison": label, "A": a, "B": b, "regret_diff_A_minus_B": r["mean_diff"],
                         "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"], "dm_p": r["p"], "win_rate_A": r["win_rate_a"]})
        t = pd.DataFrame(rows)
        if len(t):
            t["holm_p"] = stats.holm(t["dm_p"].to_numpy())
        return t

    def confidence_set(self, methods: Sequence[str], alpha: float = 0.10) -> Dict[str, object]:
        return stats.model_confidence_set({m: self.daily(self.outcome(m), "regret") for m in methods}, alpha=alpha)

    # ---------------------------------------------------------- floors
    def floor_run(self, spec: str, conf: Conformal = DEFAULT_CONFORMAL, adaptive: bool = True,
                  fixed_q: Optional[float] = None, econ: Optional[Economics] = None) -> Dict:
        """Online floor policy on calibration + test stretch of every fold; scored on test only."""
        ec = econ or self.econ
        chosen, floor, rev, oracle, test_mask, fb, alphas, dates = [], [], [], [], [], [], [], []
        viol_by_fold: Dict[int, float] = {}
        for f in self.fold_ids:
            pl = self.plans[f]
            idx = np.concatenate([pl.calib_idx, pl.test_idx])
            r_hat = np.concatenate([self.r_hat(spec, f, "cal", ec), self.r_hat(spec, f, "test", ec)])
            R = self._R(idx, ec)
            am = self._amask(idx)
            sale = self.dd.days[idx]
            res = conformal.run_floor(r_hat, R, am, sale, sale - 1, conf, adaptive=adaptive, fixed_q=fixed_q)
            tm = np.arange(len(idx)) >= len(pl.calib_idx)
            out = P.score(R, am, res.chosen, self.dd, idx)
            got = out.revenue
            chosen.append(res.chosen[tm])
            floor.append(res.floor[tm])
            rev.append(got[tm])
            oracle.append(out.oracle[tm])
            fb.append(out.fallback[tm])
            alphas.append(res.alpha_t[tm])
            dates.append(self.dd.dates[idx][tm])
            viol_by_fold[f] = float((got[tm] < res.floor[tm]).mean())
        floor, rev = np.concatenate(floor), np.concatenate(rev)
        out = P.Outcome(chosen=np.concatenate(chosen), revenue=rev, oracle=np.concatenate(oracle),
                        fallback=np.concatenate(fb))
        return {"outcome": out, "floor": floor, "violation": float((rev < floor).mean()),
                "violation_by_fold": viol_by_fold, "alpha_t": np.concatenate(alphas),
                "dates": np.concatenate([np.asarray(d) for d in dates])}

    def floor_table(self, specs: Sequence[str], alphas: Sequence[float] = (0.05, 0.10, 0.20)) -> pd.DataFrame:
        ref = self.outcome(REFERENCE).revenue
        rows = []
        for s in specs:
            if s not in self.available:
                continue
            plain = self.outcome(s)
            rows.append({"spec": s, "policy": "plug-in (no floor)", "alpha": np.nan, "violation": np.nan,
                         "mean_floor": np.nan, **self._floor_metrics(plain, ref)})
            for a in alphas:
                r = self.floor_run(s, Conformal(alpha=a, gamma=DEFAULT_CONFORMAL.gamma))
                rows.append({"spec": s, "policy": "adaptive conformal floor", "alpha": a, "violation": r["violation"],
                             "mean_floor": float(r["floor"].mean()), **self._floor_metrics(r["outcome"], ref)})
            r = self.floor_run(s, adaptive=False)
            rows.append({"spec": s, "policy": "static conformal floor", "alpha": DEFAULT_CONFORMAL.alpha,
                         "violation": r["violation"], "mean_floor": float(r["floor"].mean()),
                         **self._floor_metrics(r["outcome"], ref)})
            r = self.floor_run(s, fixed_q=1.2816, adaptive=False)
            rows.append({"spec": s, "policy": "naive Gaussian floor (z=1.28)", "alpha": 0.10,
                         "violation": r["violation"], "mean_floor": float(r["floor"].mean()),
                         **self._floor_metrics(r["outcome"], ref)})
        return pd.DataFrame(rows)

    @staticmethod
    def _floor_metrics(o: P.Outcome, ref_revenue: np.ndarray) -> Dict[str, float]:
        s = P.summarise(o, ref_revenue)
        return {"revenue": s["mean_revenue"], "cvar10": s["cvar10_revenue"], "p10": s["p10_revenue"],
                "gap_closed": s["share_of_oracle_gap_closed"], "fallback_rate": s["fallback_rate"]}

    # ------------------------------------------------- forecast accuracy
    def forecast_table(self) -> pd.DataFrame:
        """Log-return accuracy against observed prices and against realised (fallback-filled) prices."""
        rows = []
        idx = self.test_idx
        y_obs = np.nan_to_num(self.dd.Y[idx])
        obs = self.dd.obs[idx] & self.dd.elig[idx][:, :, None]
        y_fill = filled_targets(self.dd, idx, self.econ)
        elig = np.broadcast_to(self.dd.elig[idx][:, :, None], y_fill.shape)
        base_obs = np.abs(0 - y_obs)[obs].mean()
        base_fill = np.abs(0 - y_fill)[elig].mean()
        for s in ["rw"] + [x for x in self.available if x != "rw"]:
            yh = self.yhat(s)
            mo = np.abs(yh - y_obs)[obs].mean()
            mf = np.abs(yh - y_fill)[elig].mean()
            rows.append({"method": s, "MAE_observed": mo, "skill_vs_rw_observed": 1 - mo / base_obs,
                         "MAE_realised": mf, "skill_vs_rw_realised": 1 - mf / base_fill})
        return pd.DataFrame(rows)

    # ---------------------------------------------------- reporting AUC
    def report_auc(self) -> pd.DataFrame:
        rows = []
        for s in self.available:
            if self.pred[(s, self.fold_ids[0])]["report_test"].size == 0:
                continue
            for f in self.fold_ids + ["all"]:
                fl = self.fold_ids if f == "all" else [f]
                p = np.concatenate([self.pred[(s, g)]["report_test"][self.dd.elig[self.plans[g].test_idx]] for g in fl])
                y = np.concatenate([self.dd.obs[self.plans[g].test_idx][self.dd.elig[self.plans[g].test_idx]] for g in fl])
                rows.append({"method": s, "fold": f, "auc": float(roc_auc_score(y.ravel(), p.ravel()))})
        return pd.DataFrame(rows)

    def report_auc_baselines(self) -> pd.DataFrame:
        """AUC of trivial scores for 'will this mandi report on the sale day?'."""
        names = self.dd.fs.names
        rows = []
        for label, col in (("own report rate (30d)", "report_rate_30"), ("own report rate (7d)", "report_rate_7")):
            j = names.index(col)
            p = self.dd.X[self.test_idx][:, :, j][:, :, None] * np.ones((1, 1, N_HOLD))
            m = np.broadcast_to(self.dd.elig[self.test_idx][:, :, None], p.shape)
            rows.append({"method": label, "auc": float(roc_auc_score(self.dd.obs[self.test_idx][m], p[m]))})
        return pd.DataFrame(rows)

    # --------------------------------------------------------- sweeps
    def sweep(self, methods: Sequence[str], sweeps: Dict[str, Sequence[float]]) -> pd.DataFrame:
        rows = []
        for param, values in sweeps.items():
            for v in values:
                ec = self.econ.but(**{param: v})
                outs = {m: self.outcome(m, ec) for m in list(HEURISTICS) + list(methods)}
                strong = outs[STRONG_HEURISTIC].revenue.mean()
                oracle = outs[REFERENCE].oracle.mean()
                for m, o in outs.items():
                    rows.append({"param": param, "value": v, "method": m, "revenue": float(o.revenue.mean()),
                                 "gap_closed_vs_yday": float((o.revenue.mean() - strong) / max(oracle - strong, 1e-9)),
                                 "fallback_rate": float(o.fallback.mean())})
        return pd.DataFrame(rows)
