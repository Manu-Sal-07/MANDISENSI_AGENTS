"""Training, backtesting, calibration and serving of the market-choice engine.

Design (all of it verified in the GFMC study):

* Learn from what the farmer would actually have received. The training label
  for a (mandi, hold) cell is the log of the REALISED price: the mandi's own
  price if it reported on the sale day, otherwise a discounted fallback (the
  trip is wasted). This is the one change that moved decisions in the study.
* Predict, for every offered mandi and hold of 0-3 days, the sale-day price;
  turn it into net revenue per quintal with the farmer's own costs.
* State a floor L = r_hat - q * sigma and recommend the action with the best
  floor. q is a conformal quantile of past scores of recommended actions, so
  the floor is violated about alpha of the time without distributional
  assumptions. Backtest results ship with every crop.
"""

from __future__ import annotations

import json
import shutil
import threading
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry
from mandisense_ai.market_choice import econ as E
from mandisense_ai.market_choice.conformal import conformal_quantile, run_floor
from mandisense_ai.market_choice.config import (ALPHAS, ARTIFACT_DIR, CALIBRATION_WINDOW, DEFAULT_ALPHA, EVIDENCE_MARKETS,
                                                GAP_DAYS, K_MAX, MAX_STALENESS, MIN_MARKETS, N_HOLD, WARMUP_DAYS,
                                                Economics, economics_for)
from mandisense_ai.market_choice.features import FeatureSet, build_features
from mandisense_ai.market_choice.panel import Panel, build_panel, load_long
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

NEG = -1e12
ORIGINS: Dict[str, Tuple[float, float]] = {d.id: (d.lat, d.lon) for d in registry.DISTRICTS.values()}
STREAM_DAYS = 480           # backtest window (most recent valid decision days)
STREAM_SEGMENTS = 3         # refits inside the window
BURN_IN_DAYS = 150          # days used to warm up the floor before it is scored
HP = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=40, subsample=0.8,
          subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0, verbosity=-1, n_jobs=4)


# ------------------------------------------------------------------ dataset
@dataclass(frozen=True)
class DecisionData:
    panel: Panel
    fs: FeatureSet
    days: np.ndarray            # (D,) panel day index of each decision
    X: np.ndarray               # (D, M, F) features known on the morning of the decision day
    ref_lp: np.ndarray          # (D, M)
    elig: np.ndarray            # (D, M)
    obs: np.ndarray             # (D, M, K) the mandi reported on the sale day
    P_obs: np.ndarray           # (D, M, K)
    P_ref: np.ndarray           # (D, K) mean reported price on each sale day
    gate_ref: np.ndarray        # (D,)
    valid: np.ndarray           # (D,)

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.panel.dates[self.days]

    def action_mask(self) -> np.ndarray:
        m = np.repeat(self.elig, N_HOLD, axis=1)
        return np.concatenate([m, np.ones((len(self.days), 1), dtype=bool)], axis=1)

    def realised_price(self, e: Economics) -> np.ndarray:
        return np.where(self.obs, self.P_obs, e.silent_price_factor * self.P_ref[:, None, :])

    def realised_revenue(self, idx: np.ndarray, origin: Tuple[float, float], e: Economics) -> np.ndarray:
        price = np.nan_to_num(self.realised_price(e)[idx], nan=0.0)
        gate = np.nan_to_num(self.gate_ref[idx], nan=0.0)
        return E.revenue_from_prices(price, gate, self.panel.dist_km(origin), e)


def build_dataset(panel: Panel, fs: Optional[FeatureSet] = None, warmup: int = WARMUP_DAYS) -> DecisionData:
    fs = fs or build_features(panel)
    T, M = panel.T, panel.M
    t_all = np.arange(warmup + 1, T - K_MAX)
    s = t_all - 1
    ref_lp = fs.lp[s]
    elig = (fs.stale[s] <= MAX_STALENESS) & ~np.isnan(ref_lp)
    P_obs = np.full((len(t_all), M, N_HOLD), np.nan)
    P_ref = np.full((len(t_all), N_HOLD), np.nan)
    for k in range(N_HOLD):
        pk = panel.price[t_all + k]
        P_obs[:, :, k] = pk
        n = np.sum(~np.isnan(pk), axis=1)
        P_ref[:, k] = np.where(n > 0, np.nansum(pk, axis=1) / np.maximum(n, 1), np.nan)
    pt = panel.price[t_all]
    n0 = np.sum(~np.isnan(pt), axis=1)
    gate_ref = np.where(n0 > 0, np.nansum(pt, axis=1) / np.maximum(n0, 1), np.nan)
    valid = ~np.isnan(P_ref).any(1) & ~np.isnan(gate_ref) & elig.any(1)
    return DecisionData(panel=panel, fs=fs, days=t_all, X=fs.X[s], ref_lp=ref_lp, elig=elig, obs=~np.isnan(P_obs),
                        P_obs=P_obs, P_ref=P_ref, gate_ref=gate_ref, valid=valid)


# -------------------------------------------------------------------- model
def _stack(X: np.ndarray, elig: np.ndarray) -> np.ndarray:
    n, M, _ = X.shape
    mk = np.broadcast_to(np.arange(M), (n, M))[:, :, None].astype(float)
    return np.concatenate([X, mk], axis=2)[elig]


@dataclass
class Bundle:
    regs: List[Any]
    clfs: List[Any]
    n_markets: int

    def predict(self, X: np.ndarray, elig: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        n, M, _ = X.shape
        rows = _stack(X, elig)
        yhat = np.zeros((n, M, N_HOLD))
        prep = np.full((n, M, N_HOLD), 0.85)
        if len(rows) == 0:
            return yhat, prep
        for k in range(N_HOLD):
            plane = np.zeros((n, M))
            plane[elig] = self.regs[k].predict(rows)
            yhat[:, :, k] = plane
            pp = np.full((n, M), 0.85)
            pp[elig] = self.clfs[k].predict_proba(rows)[:, 1]
            prep[:, :, k] = pp
        return yhat, prep


def fit_bundle(dd: DecisionData, idx: np.ndarray, e: Economics) -> Bundle:
    import lightgbm as lgb

    real = dd.realised_price(e)[idx]
    ref = np.exp(np.nan_to_num(dd.ref_lp[idx], nan=0.0))[:, :, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        filled = np.nan_to_num(np.log(np.where(real > 0, real, np.nan) / ref), nan=0.0)
    elig = dd.elig[idx]
    rows = _stack(dd.X[idx], elig)
    cat = [rows.shape[1] - 1]
    regs, clfs = [], []
    for k in range(N_HOLD):
        y = filled[:, :, k][elig]
        regs.append(lgb.LGBMRegressor(objective="huber", alpha=0.15, random_state=20 + k, **HP).fit(rows, y, categorical_feature=cat))
        clfs.append(lgb.LGBMClassifier(random_state=40 + k, **HP).fit(rows, dd.obs[idx][:, :, k][elig].astype(int), categorical_feature=cat))
    return Bundle(regs=regs, clfs=clfs, n_markets=dd.panel.M)


# ------------------------------------------------------------- price helpers
def price_from_yhat(ref_lp: np.ndarray, yhat: np.ndarray) -> np.ndarray:
    return np.exp(np.nan_to_num(ref_lp, nan=0.0))[..., None] * np.exp(yhat)


def revenue_from_yhat(dd: DecisionData, idx: np.ndarray, yhat: np.ndarray, e: Economics,
                      origins: Dict[str, Tuple[float, float]] = ORIGINS) -> np.ndarray:
    price = price_from_yhat(dd.ref_lp[idx], yhat)
    w = dd.elig[idx].astype(float)
    gate = (price[:, :, 0] * w).sum(1) / np.maximum(w.sum(1), 1.0)
    return np.stack([E.revenue_from_prices(price, gate, dd.panel.dist_km(o), e) for o in origins.values()], axis=1)


# ------------------------------------------------------------------ backtest
def _block_bootstrap(x: np.ndarray, block: int = 14, reps: int = 2000, seed: int = 0) -> Tuple[float, float, float]:
    x = np.asarray(x, float)
    n = len(x)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, max(n - block, 1), size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n]
    m = x[idx].mean(1)
    return float(x.mean()), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def _heuristic_choice(dd: DecisionData, idx: np.ndarray, kind: str, origin: Tuple[float, float]) -> np.ndarray:
    n, M = len(idx), dd.panel.M
    dist = dd.panel.dist_km(origin)
    elig = dd.elig[idx]
    if kind == "nearest":
        m = np.argmin(np.where(elig, dist[None, :], np.inf), axis=1)
    else:
        m = np.argmax(np.where(elig, dd.ref_lp[idx], -np.inf), axis=1)
    return m * N_HOLD


def _sigma_path(r_hat0: np.ndarray, R0: np.ndarray, am: np.ndarray, sale: np.ndarray, today: np.ndarray,
                halflife: int = 60) -> Tuple[np.ndarray, np.ndarray]:
    """Per-action error scale known on each decision day (resolved days only).

    Mandi-action errors do not depend on the farmer's origin (the trip cost
    cancels between predicted and realised revenue), so one origin suffices.
    Returns the (n, A) path and the final (A,) scale.
    """
    n, A = r_hat0.shape
    lam = 0.5 ** (1.0 / halflife)
    ew = np.full(A, np.nan)
    path = np.zeros((n, A))
    released = 0
    for d in range(n):
        while released < d and sale[released] + K_MAX <= today[d]:
            err = (r_hat0[released] - R0[released]) ** 2
            upd = np.where(np.isnan(ew), err, lam * ew + (1 - lam) * err)
            ew = np.where(am[released], upd, ew)
            released += 1
        pooled = float(np.sqrt(np.nanmean(ew))) if np.isfinite(ew).any() else 500.0
        path[d] = np.maximum(np.where(np.isnan(ew), pooled, np.sqrt(np.maximum(ew, 0.0))), 1.0)
    pooled = float(np.sqrt(np.nanmean(ew))) if np.isfinite(ew).any() else 500.0
    final = np.maximum(np.where(np.isnan(ew), pooled, np.sqrt(np.maximum(ew, 0.0))), 1.0)
    return path, final


def _aci_stream(score: np.ndarray, sale: np.ndarray, today: np.ndarray, alpha: float, gamma: float = 0.01,
                window: int = CALIBRATION_WINDOW, burn_in: int = 0) -> Tuple[float, float]:
    """Adaptive conformal inference over normalised scores of recommended actions.

    score (n, O): day-by-origin scores (r_hat - R) / sigma. A score becomes known only once its sale
    date is strictly in the past (delayed feedback). Returns the final alpha_t averaged over origins
    and the online violation rate after `burn_in` days.
    """
    n, O = score.shape
    finals, viol = [], []
    for o in range(O):
        alpha_t = alpha
        released = 0
        known: List[float] = []
        qs = np.zeros(n)
        for d in range(n):
            while released < d and sale[released] + K_MAX <= today[d]:
                err = float(score[released, o] > qs[released])
                alpha_t = alpha_t + gamma * (alpha - err)
                known.append(float(score[released, o]))
                released += 1
            qs[d] = conformal_quantile(np.asarray(known[-window:]), alpha_t)
        finals.append(alpha_t)
        viol.append(float((score[burn_in:, o] > qs[burn_in:]).mean()))
    return float(np.mean(finals)), float(np.mean(viol))


def backtest(dd: DecisionData, e: Economics, daily: bool = False) -> Dict[str, Any]:
    """Walk-forward out-of-sample evaluation over the most recent decision days.

    The served policy is the plug-in one: recommend the action with the best
    EXPECTED net revenue and attach a conformal floor to it. (Choosing by the
    floor instead is evaluated as the "safest" alternative; the study found it
    gives up expected revenue.) Every refit uses only data before its block.
    """
    valid = np.flatnonzero(dd.valid)
    stream = valid[-STREAM_DAYS:]
    if len(stream) < BURN_IN_DAYS + 60:
        return {"status": "INSUFFICIENT_HISTORY", "days": int(len(stream))}
    dates = dd.dates
    yh = []
    for seg in np.array_split(stream, STREAM_SEGMENTS):
        cutoff = dates[seg[0]] - timedelta(days=GAP_DAYS)
        train = valid[dates[valid] < cutoff]
        if len(train) < 200:
            return {"status": "INSUFFICIENT_HISTORY", "days": int(len(train))}
        yh.append(fit_bundle(dd, train, e).predict(dd.X[seg], dd.elig[seg])[0])
    yhat = np.concatenate(yh)

    am = dd.action_mask()[stream]
    r_hat = revenue_from_yhat(dd, stream, yhat, e)
    R = np.stack([dd.realised_revenue(stream, o, e) for o in ORIGINS.values()], axis=1)
    sale = dd.days[stream]
    n, O, A = R.shape
    M_ = dd.panel.M

    take = lambda a: np.take_along_axis(R, a[..., None], -1)[..., 0]
    plug = np.where(am[:, None, :], r_hat, NEG).argmax(-1)
    oracle = np.where(am[:, None, :], R, NEG).max(-1)
    near = np.stack([_heuristic_choice(dd, stream, "nearest", o) for o in ORIGINS.values()], axis=1)
    high = np.stack([_heuristic_choice(dd, stream, "highest", o) for o in ORIGINS.values()], axis=1)

    # safest alternative: the action with the best online conformal floor
    run = run_floor(r_hat, R, am, sale, sale - 1)
    got = {"recommended": take(plug), "safest": take(run.chosen), "nearest": take(near),
           "highest_yesterday": take(high), "farm_gate": R[:, :, -1], "oracle": oracle}

    ev = np.arange(n) >= BURN_IN_DAYS
    day = lambda x: x[ev].mean(1)
    g_hi = _block_bootstrap(day(got["recommended"]) - day(got["highest_yesterday"]), seed=0)
    g_ne = _block_bootstrap(day(got["recommended"]) - day(got["nearest"]), seed=1)
    g_sf = _block_bootstrap(day(got["safest"]) - day(got["highest_yesterday"]), seed=2)

    # floor on the RECOMMENDED action: per-day error scale (resolved days only), conformal quantile from the
    # first half of the scored period, violation measured out of sample on the second half
    path, sigma_final = _sigma_path(r_hat[:, 0, :], R[:, 0, :], am, sale, sale - 1)
    rh_c = np.take_along_axis(r_hat, plug[..., None], -1)[..., 0]
    sig_c = path[np.arange(n)[:, None], plug]
    score = (rh_c - got["recommended"]) / sig_c
    half = BURN_IN_DAYS + (n - BURN_IN_DAYS) // 2
    static_oos = {f"{a:.2f}": round(float((score[half:] > conformal_quantile(score[BURN_IN_DAYS:half].ravel(), a)).mean()), 3)
                  for a in ALPHAS}
    aci = {a_: _aci_stream(score, sale, sale - 1, a_, burn_in=BURN_IN_DAYS) for a_ in ALPHAS}
    pooled_scores = score[BURN_IN_DAYS:].ravel()
    pooled_scores = pooled_scores[np.isfinite(pooled_scores)]

    is_mkt = plug < M_ * N_HOLD
    m_ix, k_ix = np.where(is_mkt, plug // N_HOLD, 0), np.where(is_mkt, plug % N_HOLD, 0)
    silent = ~dd.obs[stream][np.arange(n)[:, None], m_ix, k_ix] & is_mkt

    months = pd.Series(dates[stream][ev]).dt.to_period("M").astype(str).to_numpy()
    monthly = pd.DataFrame({"m": months, "recommended": day(got["recommended"]), "nearest": day(got["nearest"]),
                            "highest": day(got["highest_yesterday"]), "oracle": day(got["oracle"])}).groupby("m").mean()

    mean = lambda k: float(got[k][ev].mean())
    gap = mean("oracle") - mean("nearest")
    ci = lambda t: {"mean": round(t[0], 1), "ci_lo": round(t[1], 1), "ci_hi": round(t[2], 1)}
    return {
        "status": "OK",
        "window": [str(dates[stream][BURN_IN_DAYS].date()), str(dates[stream][-1].date())],
        "scored_days": int(ev.sum()),
        "mean_net_revenue": {k: round(mean(k), 1) for k in got},
        "share_of_oracle_gap_closed": round((mean("recommended") - mean("nearest")) / gap, 3) if gap > 0 else None,
        "gain_vs_highest_yesterday": ci(g_hi),
        "gain_vs_nearest": ci(g_ne),
        "safest_gain_vs_highest_yesterday": ci(g_sf),
        "silent_trip_rate": round(float(silent[ev].mean()), 3),
        "floor_violation_static_out_of_sample": static_oos,
        "floor_violation_adaptive": {f"{a_:.2f}": round(v[1], 3) for a_, v in aci.items()},
        "alpha_effective": {f"{a_:.2f}": round(v[0], 4) for a_, v in aci.items()},
        "evidence_level": "strong" if g_hi[1] > 0 and dd.panel.M >= EVIDENCE_MARKETS else "limited",
        "monthly": {"months": list(monthly.index), "recommended": monthly["recommended"].round(0).tolist(),
                    "nearest": monthly["nearest"].round(0).tolist(), "highest": monthly["highest"].round(0).tolist(),
                    "oracle": monthly["oracle"].round(0).tolist()},
        "_scores": pooled_scores[-6000:],
        "_sigma": sigma_final,
        **({"_daily": _daily_record(dates[stream], ev, half, got, score, rh_c, sig_c, aci[DEFAULT_ALPHA][0])} if daily else {}),
    }


def _daily_record(stream_dates: np.ndarray, ev: np.ndarray, half: int, got: Dict[str, np.ndarray], score: np.ndarray,
                  rh_c: np.ndarray, sig_c: np.ndarray, alpha_eff: float) -> Dict[str, Any]:
    """Day-by-day out-of-sample record of the served policy, for the public track record.

    Only days in the second half of the scored period are listed: the floor multiplier is fitted on the first half,
    so these days were never used to set the floor they are judged against.
    """
    q = conformal_quantile(score[BURN_IN_DAYS:half].ravel(), alpha_eff)
    floor = rh_c - q * sig_c
    held = got["recommended"] >= floor
    rows = []
    for i in np.flatnonzero(ev)[np.flatnonzero(ev) >= half]:
        rows.append({"date": str(stream_dates[i].date()),
                     "recommended": round(float(got["recommended"][i].mean()), 1), "nearest": round(float(got["nearest"][i].mean()), 1),
                     "highest_yesterday": round(float(got["highest_yesterday"][i].mean()), 1), "oracle": round(float(got["oracle"][i].mean()), 1),
                     "floor": round(float(floor[i].mean()), 1), "floor_held": round(float(held[i].mean()), 2)})
    return {"q": round(float(q), 4), "alpha_effective": round(float(alpha_eff), 4), "days": rows}


# ----------------------------------------------------------------- training
def train_crop(crop: str, long: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
    long = load_long() if long is None else long
    panel = build_panel(long, crop)
    if panel is None or panel.M < MIN_MARKETS:
        logger.info("market-choice: %s skipped (markets=%s)", crop, getattr(panel, "M", 0))
        return None
    e = economics_for(crop)
    dd = build_dataset(panel)
    valid = np.flatnonzero(dd.valid)
    if len(valid) < 400:
        return None
    bt = backtest(dd, e)
    out = ARTIFACT_DIR / crop
    if bt.get("status") != "OK":
        # No validated backtest means no validated floor: serving it would present an unchecked guarantee.
        if out.exists():
            shutil.rmtree(out)
        logger.info("market-choice: %s not served (backtest %s)", crop, bt.get("status"))
        return {"crop": crop, "served": False, "n_markets": panel.M, "backtest": bt}
    bundle = fit_bundle(dd, valid, e)
    scores = bt.pop("_scores", np.array([]))
    sigma = bt.pop("_sigma", None)
    bt.pop("_daily", None)
    meta = {
        "crop": crop, "markets": list(panel.markets), "n_markets": panel.M, "trained_through": str(panel.dates[-1].date()),
        "n_train_days": int(len(valid)), "economics": asdict(e), "limited_evidence": panel.M < EVIDENCE_MARKETS,
        "backtest": bt, "alphas": list(ALPHAS),
        "q": {f"{a:.2f}": round(conformal_quantile(scores, _effective_alpha({"backtest": bt}, a)), 4) for a in ALPHAS} if len(scores) else None,
        "calibration_scores": int(len(scores)),
    }
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out / "model.joblib")
    np.save(out / "scores.npy", scores)
    if sigma is not None:
        np.save(out / "sigma.npy", sigma)
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    logger.info("market-choice: trained %s (%d markets, %d days)", crop, panel.M, len(valid))
    return meta


def train_all(crops: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    long = load_long()
    crops = list(crops) if crops else sorted(long["crop"].unique())
    return {c: train_crop(c, long) for c in crops}


# ------------------------------------------------------------------ serving
def _effective_alpha(meta: Dict[str, Any], alpha: float) -> float:
    """The ACI-adjusted miscoverage level learned in the backtest for this crop (shifted for other targets)."""
    eff = (meta.get("backtest") or {}).get("alpha_effective") or {}
    key = f"{alpha:.2f}"
    if key in eff:
        return float(eff[key])
    shift = float(eff.get(f"{DEFAULT_ALPHA:.2f}", DEFAULT_ALPHA)) - DEFAULT_ALPHA
    return float(np.clip(alpha + shift, 0.01, 0.5))


class MarketChoiceEngine:
    """Loads the trained artifacts lazily and turns the latest prices into a recommendation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: Dict[str, Dict[str, Any]] = {}
        self._panels: Dict[str, Tuple[float, Panel, FeatureSet]] = {}

    # -- artifacts
    def crops(self) -> List[str]:
        if not ARTIFACT_DIR.exists():
            return []
        return sorted(p.name for p in ARTIFACT_DIR.iterdir() if (p / "meta.json").exists())

    def meta(self, crop: str) -> Optional[Dict[str, Any]]:
        art = self._load(crop)
        return art["meta"] if art else None

    def _load(self, crop: str) -> Optional[Dict[str, Any]]:
        crop = crop.lower()
        folder = ARTIFACT_DIR / crop
        meta_path = folder / "meta.json"
        if not meta_path.exists():
            return None
        stamp = meta_path.stat().st_mtime
        with self._lock:
            hit = self._models.get(crop)
            if hit and hit["stamp"] == stamp:
                return hit
            art = {
                "stamp": stamp, "meta": json.loads(meta_path.read_text(encoding="utf-8")),
                "bundle": joblib.load(folder / "model.joblib"),
                "scores": np.load(folder / "scores.npy") if (folder / "scores.npy").exists() else np.array([]),
                "sigma": np.load(folder / "sigma.npy") if (folder / "sigma.npy").exists() else None,
            }
            self._models[crop] = art
            return art

    def _panel(self, crop: str) -> Optional[Tuple[Panel, FeatureSet]]:
        from mandisense_ai.market_choice.config import PANEL_FILE

        if not PANEL_FILE.exists():
            return None
        stamp = PANEL_FILE.stat().st_mtime
        hit = self._panels.get(crop)
        if hit and hit[0] == stamp:
            return hit[1], hit[2]
        panel = build_panel(load_long(), crop)
        if panel is None:
            return None
        fs = build_features(panel)
        self._panels[crop] = (stamp, panel, fs)
        return panel, fs

    # -- the recommendation
    def evaluate(self, crop: str, origin: Tuple[float, float], alpha: float = DEFAULT_ALPHA,
                 transport_per_q_km: Optional[float] = None) -> Dict[str, Any]:
        """Action values for every offered (mandi, hold) from one origin. Raises LookupError if unavailable."""
        crop = crop.lower()
        art = self._load(crop)
        pf = self._panel(crop)
        if art is None or pf is None:
            raise LookupError(f"No market-choice model for '{crop}'.")
        panel, fs = pf
        meta = art["meta"]
        if list(panel.markets) != meta["markets"]:
            raise LookupError("The market set changed since training; retrain the market-choice model.")
        T, M = panel.T, panel.M
        s = T - 1
        ref_lp = fs.lp[s]
        elig = (fs.stale[s] <= MAX_STALENESS) & ~np.isnan(ref_lp)
        if not elig.any():
            raise LookupError("No mandi has reported recently enough to advise on.")
        e = economics_for(crop, transport_per_q_km)
        yhat, prep = art["bundle"].predict(fs.X[s:s + 1], elig[None, :])
        price = price_from_yhat(ref_lp[None, :], yhat)[0]                    # (M, K)
        gate_price = float(price[elig, 0].mean())
        dist = panel.dist_km(origin)
        r_hat = E.revenue_from_prices(price[None], np.array([gate_price]), dist, e)[0]

        sigma = art["sigma"] if art["sigma"] is not None else np.full(E.n_actions(M), 150.0)
        sigma = np.where(np.isfinite(sigma), sigma, 150.0)
        scores = art["scores"]
        q = conformal_quantile(scores[-CALIBRATION_WINDOW * len(ORIGINS):], _effective_alpha(meta, alpha))
        floor = r_hat - q * sigma
        offered = np.concatenate([np.repeat(elig, N_HOLD), [True]])
        return {
            "panel": panel, "meta": meta, "econ": e, "elig": elig, "price": price, "prep": prep[0], "r_hat": r_hat,
            "floor": floor, "sigma": sigma, "q": q, "alpha": alpha, "offered": offered, "dist": dist,
            "gate_price": gate_price, "decision_day": panel.dates[-1] + timedelta(days=1), "as_of": panel.dates[-1], "ref_lp": ref_lp,
            "last_price": np.exp(np.nan_to_num(ref_lp)), "stale": fs.stale[s],
        }


ENGINE = MarketChoiceEngine()
