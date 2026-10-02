"""
Cross-commodity and cross-district transmission on the real farmer data world.

Two questions, kept apart because they need different evidence:

  Test A - "does a shock to one crop move another crop, in the same place?"
            (cross-commodity spillover, same district)
  Test B - "does a price gap between two places for the SAME crop close, and
            how fast?" (spatial transmission / neighbour-district signal)

Both read mandisense_ai.farmer.world (the real district observation table),
never the trader side's v4-derived data or the existing
mandisense_ai/spillover/ or mandisense_ai/trader/arbitrage.py pipelines,
which this module does not modify and does not depend on.

Every publication rule here is the one written in
IEEE_Paper/experiments/PREREGISTERED_ADDENDUM_2_TRANSMISSION.txt, which was
written before any result in this module was computed. Changing a threshold
here without updating that file is exactly the failure mode the addendum
exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry
from mandisense_ai.farmer.significance import dm_test, holm

# ── shared configuration (mirrors the addendum; change both together) ──────

Z_ONSET = 1.5
MIN_GAP_DAYS = 7
ROLL_WINDOW = 60
MIN_ROLL_PRINTS = 30
HORIZON_DAYS = 14
MATCH_TOLERANCE_DAYS = 3
MIN_EPISODES = 8
BOOTSTRAP_B = 2000
BLOCK_WEEKS = 8
FDR_Q = 0.10
PLACEBO_N = 500
PLACEBO_MIN_SHIFT_DAYS = 90
MIN_ABS_EFFECT = 0.01
MIN_STABILITY_SHARE = 0.75
MIN_STABLE_DISTRICTS = 3
MIN_ONSETS_FOR_STABILITY = 8

MIN_COMMON_WEEKS = 150


# ────────────────────────────────────────────────── shock / episode detection


def arrival_surprise(series: pd.DataFrame) -> pd.Series:
    """z-score of log arrivals against a trailing, lagged norm. Only ever uses
    information available the day before, so a shock can be used as a
    predictor of what happens next without looking at its own future."""
    s = series.sort_values("date").set_index("date")
    la = np.log(s["arrivals"].where(s["arrivals"] > 0))
    mu = la.rolling(ROLL_WINDOW, min_periods=MIN_ROLL_PRINTS).mean().shift(1)
    sd = la.rolling(ROLL_WINDOW, min_periods=MIN_ROLL_PRINTS).std().shift(1)
    return (la - mu) / sd


def onsets(z: pd.Series, direction: str) -> List[pd.Timestamp]:
    flag = (z >= Z_ONSET) if direction == "glut" else (z <= -Z_ONSET)
    flag = flag.fillna(False)
    starts = flag & ~flag.shift(1, fill_value=False)
    kept: List[pd.Timestamp] = []
    last: Optional[pd.Timestamp] = None
    for t in flag.index[starts]:
        if last is None or (t - last).days >= MIN_GAP_DAYS:
            kept.append(t)
            last = t
    return kept


class NearestLookup:
    """Reusable, vectorised "nearest print within `tol` days" index over one
    price series — built once per (district, crop) and reused across every
    shock date and every placebo draw, instead of rescanning the series with
    a fresh boolean mask on every call."""

    def __init__(self, prices: pd.Series, tol: int = MATCH_TOLERANCE_DAYS):
        self.index = prices.index.values.astype("datetime64[ns]")
        self.values = np.log(prices.to_numpy(dtype=float))
        self.tol = np.timedelta64(tol, "D")

    def at(self, target: pd.Timestamp) -> Optional[float]:
        t = np.datetime64(target)
        pos = np.searchsorted(self.index, t)
        candidates = [p for p in (pos - 1, pos) if 0 <= p < len(self.index)]
        if not candidates:
            return None
        diffs = [abs(self.index[p] - t) for p in candidates]
        best = candidates[int(np.argmin(diffs))]
        return float(self.values[best]) if diffs[int(np.argmin(diffs))] <= self.tol else None


def _price_change(prices, t0: pd.Timestamp, days: int, tol: int = MATCH_TOLERANCE_DAYS) -> Optional[float]:
    """log price at (t0 + days) minus log price at t0, each matched to the
    nearest print within `tol` days; None if either side has no close print.
    `prices` may be a pandas Series (ad hoc use) or a prebuilt NearestLookup
    (hot paths: the placebo loop)."""
    lookup = prices if isinstance(prices, NearestLookup) else NearestLookup(prices, tol)
    before = lookup.at(t0)
    after = lookup.at(t0 + pd.Timedelta(days=days))
    if before is None or after is None:
        return None
    return after - before


def _block_bootstrap_ci(values: np.ndarray, dates: np.ndarray, block_weeks: int = BLOCK_WEEKS, B: int = BOOTSTRAP_B,
                         seed: int = 20261001) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    order = np.argsort(dates)
    values, dates = values[order], dates[order]
    weeks = pd.PeriodIndex(pd.to_datetime(dates), freq="W")
    uniq = np.array(sorted(set(weeks)))
    by_week = {w: np.where(weeks == w)[0] for w in uniq}
    n_blocks = int(np.ceil(len(uniq) / block_weeks))
    means = []
    for _ in range(B):
        starts = rng.integers(0, max(1, len(uniq) - block_weeks), n_blocks)
        idx = np.concatenate([np.concatenate([by_week[w] for w in uniq[s:s + block_weeks]]) for s in starts])
        means.append(values[idx].mean())
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


@dataclass
class Episode:
    district: str
    date: pd.Timestamp
    target_change: float
    peer_change: float
    own_past_change: float


def _episode_table(obs: pd.DataFrame, source_crop: str, target_crop: str, direction: str,
                    peer_crops: List[str]) -> List[Episode]:
    rows: List[Episode] = []
    for district in sorted(obs["mandi_id"].unique()):
        d_obs = obs[obs["mandi_id"] == district]
        src = d_obs[d_obs["commodity"] == source_crop]
        tgt = d_obs[d_obs["commodity"] == target_crop]
        if src.empty or tgt.empty:
            continue
        z = arrival_surprise(src)
        shocks = onsets(z, direction)
        if not shocks:
            continue
        tgt_prices = NearestLookup(tgt.sort_values("date").set_index("date")["modal_price"])
        peer_series = {
            c: NearestLookup(d_obs[d_obs["commodity"] == c].sort_values("date").set_index("date")["modal_price"])
            for c in peer_crops if c not in (source_crop, target_crop)
        }
        for t0 in shocks:
            change = _price_change(tgt_prices, t0, HORIZON_DAYS)
            past = _price_change(tgt_prices, t0 - pd.Timedelta(days=HORIZON_DAYS), HORIZON_DAYS)
            if change is None:
                continue
            peer_vals = [v for s in peer_series.values() if (v := _price_change(s, t0, HORIZON_DAYS)) is not None]
            peer_mean = float(np.mean(peer_vals)) if peer_vals else 0.0
            rows.append(Episode(district, t0, change, peer_mean, past if past is not None else 0.0))
    return rows


def _fit_local_projection(episodes: List[Episode]) -> Dict[str, Any]:
    """OLS of target change on an intercept, peer mean change and the
    target's own prior-window change, with district fixed effects folded in
    via demeaning. Returns the shock's implied effect (the demeaned mean of
    the residual target change) and its block-bootstrap interval."""
    import pandas as pd

    df = pd.DataFrame([e.__dict__ for e in episodes])
    df["district"] = df["district"].astype("category")
    # District-demean every column (fixed effects without a design matrix).
    for col in ("target_change", "peer_change", "own_past_change"):
        df[col + "_d"] = df[col] - df.groupby("district")[col].transform("mean")
    X = np.column_stack([np.ones(len(df)), df["peer_change_d"], df["own_past_change_d"]])
    y = df["target_change_d"].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    effect = float(beta[0]) + float(df["target_change"].mean()) - float(df["target_change_d"].mean())
    # The intercept of the demeaned regression recovers the shock's average
    # effect net of peers and own momentum; re-centre on the raw mean so it
    # reads as "average log change attributable to the shock".
    effect = float(df["target_change"].mean() - (X[:, 1:] @ beta[1:]).mean())
    lo, hi = _block_bootstrap_ci(df["target_change_d"].to_numpy() + effect, df["date"].astype(str).to_numpy())
    return {"effect": effect, "ci": [lo, hi], "n": len(df)}


def _placebo_p(obs: pd.DataFrame, source_crop: str, target_crop: str, direction: str, peer_crops: List[str],
               observed_effect: float, seed: int = 20261001) -> float:
    """Circular-shift placebo. The per-district shock dates and target price
    series depend only on (source_crop, target_crop, direction), not on the
    random shift, so they are computed once and reused across all draws —
    the loop body below only re-matches shifted dates to the already-built
    target price series."""
    rng = np.random.default_rng(seed)
    per_district = []
    for district in sorted(obs["mandi_id"].unique()):
        d_obs = obs[obs["mandi_id"] == district]
        src = d_obs[d_obs["commodity"] == source_crop]
        tgt = d_obs[d_obs["commodity"] == target_crop]
        if src.empty or tgt.empty:
            continue
        shocks = onsets(arrival_surprise(src), direction)
        span = (src["date"].max() - src["date"].min()).days
        if not shocks or span <= 2 * PLACEBO_MIN_SHIFT_DAYS:
            continue
        tgt_prices = tgt.sort_values("date").set_index("date")["modal_price"]
        per_district.append((shocks, span, NearestLookup(tgt_prices)))

    if not per_district:
        return 1.0

    exceed = 0
    for _ in range(PLACEBO_N):
        changes: List[float] = []
        for shocks, span, tgt_prices in per_district:
            shift = int(rng.integers(PLACEBO_MIN_SHIFT_DAYS, span - PLACEBO_MIN_SHIFT_DAYS))
            for t0 in shocks:
                change = _price_change(tgt_prices, t0 + pd.Timedelta(days=shift), HORIZON_DAYS)
                if change is not None:
                    changes.append(change)
        if len(changes) < MIN_EPISODES:
            continue
        if abs(np.mean(changes)) >= abs(observed_effect):
            exceed += 1
    return (exceed + 1) / (PLACEBO_N + 1)


def _stability(obs: pd.DataFrame, source_crop: str, target_crop: str, direction: str) -> Dict[str, Any]:
    signs = []
    for district in sorted(obs["mandi_id"].unique()):
        d_obs = obs[obs["mandi_id"] == district]
        src, tgt = d_obs[d_obs["commodity"] == source_crop], d_obs[d_obs["commodity"] == target_crop]
        if src.empty or tgt.empty:
            continue
        shocks = onsets(arrival_surprise(src), direction)
        if len(shocks) < MIN_ONSETS_FOR_STABILITY:
            continue
        tgt_prices = tgt.sort_values("date").set_index("date")["modal_price"]
        changes = [c for t0 in shocks if (c := _price_change(tgt_prices, t0, HORIZON_DAYS)) is not None]
        if changes:
            signs.append((district, np.sign(np.mean(changes))))
    if not signs:
        return {"stable": False, "districts": 0, "agree": 0}
    overall_sign = np.sign(np.mean([s for _, s in signs]))
    agree = sum(1 for _, s in signs if s == overall_sign)
    return {"stable": len(signs) >= MIN_STABLE_DISTRICTS and agree / len(signs) >= MIN_STABILITY_SHARE,
            "districts": len(signs), "agree": agree}


def _pre_trend_t(episodes: List[Episode]) -> float:
    vals = [e.own_past_change for e in episodes]
    if len(vals) < 5:
        return 0.0
    arr = np.array(vals)
    se = arr.std(ddof=1) / np.sqrt(len(arr))
    return float(arr.mean() / se) if se > 0 else 0.0


def run_test_a(obs: pd.DataFrame, crops: List[str]) -> Dict[str, Any]:
    """Every (source crop, target crop, shock direction) edge, same district."""
    edges = []
    for source, target in permutations(crops, 2):
        for direction in ("glut", "squeeze"):
            peer_crops = [c for c in crops if c not in (source, target)]
            episodes = _episode_table(obs, source, target, direction, peer_crops)
            key = f"{source}->{target}:{direction}"
            if len(episodes) < MIN_EPISODES:
                edges.append({"source": source, "target": target, "shock": direction, "status": "INSUFFICIENT_EVIDENCE",
                             "n_episodes": len(episodes)})
                continue
            fit = _fit_local_projection(episodes)
            placebo_p = _placebo_p(obs, source, target, direction, peer_crops, fit["effect"])
            pre_t = _pre_trend_t(episodes)
            stability = _stability(obs, source, target, direction)
            se = (fit["ci"][1] - fit["ci"][0]) / (2 * 1.96)
            mde = 2.8 * se if se > 0 else None
            edges.append({
                "source": source, "target": target, "shock": direction, "status": "OK",
                "n_episodes": fit["n"], "effect": round(fit["effect"], 4), "ci": [round(c, 4) for c in fit["ci"]],
                "placebo_p": round(placebo_p, 4), "pre_trend_t": round(pre_t, 3),
                "stability": stability, "min_detectable_effect": round(mde, 4) if mde else None,
                "districts": sorted(obs[obs.commodity.isin([source, target])]["mandi_id"].unique().tolist()),
            })
    ci_excl0 = [e for e in edges if e["status"] == "OK" and not (e["ci"][0] <= 0 <= e["ci"][1])]
    pvals_for_fdr = []
    for e in edges:
        if e["status"] != "OK":
            continue
        se = (e["ci"][1] - e["ci"][0]) / (2 * 1.96)
        z = e["effect"] / se if se > 0 else 0.0
        from scipy import stats as _st
        pvals_for_fdr.append((e, float(2 * _st.norm.sf(abs(z)))))
    if pvals_for_fdr:
        order = np.argsort([p for _, p in pvals_for_fdr])
        m = len(pvals_for_fdr)
        passed = set()
        for rank, idx in enumerate(order, start=1):
            e, p = pvals_for_fdr[idx]
            if p <= (rank / m) * FDR_Q:
                passed.add(id(e))
            else:
                break
        for e, _ in pvals_for_fdr:
            e["fdr_pass"] = id(e) in passed
    for e in edges:
        if e["status"] != "OK":
            e["published"] = False
            continue
        e["published"] = bool(
            e.get("fdr_pass") and abs(e["pre_trend_t"]) < 2 and e["stability"]["stable"]
            and abs(e["effect"]) >= MIN_ABS_EFFECT and e["placebo_p"] <= 0.05
        )
    return {"edges": edges, "n_tested": len(edges), "n_published": sum(e["published"] for e in edges)}


# ───────────────────────────────────────────────────────── Test B: gap ECM


def _weekly_log_price(obs: pd.DataFrame, crop: str, district: str) -> pd.Series:
    s = obs[(obs.commodity == crop) & (obs.mandi_id == district)].sort_values("date").set_index("date")["modal_price"]
    return np.log(s).resample("W").mean()


def run_test_b(obs: pd.DataFrame, crops: List[str]) -> Dict[str, Any]:
    from statsmodels.tsa.stattools import adfuller

    results = []
    for crop in crops:
        districts = sorted(obs[obs.commodity == crop]["mandi_id"].unique())
        series = {d: _weekly_log_price(obs, crop, d) for d in districts}
        for a, b in permutations(districts, 2):
            joint = pd.concat([series[a], series[b]], axis=1, join="inner").dropna()
            joint.columns = ["a", "b"]
            if len(joint) < MIN_COMMON_WEEKS:
                continue
            gap = (joint["b"] - joint["a"])
            dgap = gap.shift(-1) - gap
            m = dgap.notna()
            X = np.column_stack([np.ones(m.sum()), gap[m].to_numpy()])
            beta, *_ = np.linalg.lstsq(X, dgap[m].to_numpy(), rcond=None)
            kappa = float(beta[1])
            resid = dgap[m].to_numpy() - X @ beta
            # Newey-West (4 lags) standard error of kappa -- reported for
            # context, but NOT used to decide closure: under the null of no
            # mean reversion (kappa=0, a unit root), the OLS t-statistic on
            # kappa does not follow a standard t-distribution, it follows the
            # (left-skewed) Dickey-Fuller distribution. Testing it against a
            # plain t-distribution understates how often a pure random walk
            # produces a kappa that LOOKS significant by chance (verified:
            # caught by this module's own test suite on simulated random-walk
            # gaps). The augmented Dickey-Fuller test below uses the correct
            # distribution and is what closure is actually gated on.
            from mandisense_ai.farmer.significance import newey_west_var
            xc = gap[m].to_numpy() - gap[m].mean()
            infl = xc * resid
            se = np.sqrt(newey_west_var(infl, 4) / m.sum()) / np.sqrt((xc ** 2).mean())
            t_stat = kappa / se if se > 0 else 0.0
            from scipy import stats as _st
            p = float(2 * _st.t.sf(abs(t_stat), m.sum() - 2))
            adf_p = float(adfuller(gap.dropna(), maxlag=4, autolag="AIC")[1])
            half_life = float(np.log(0.5) / np.log(1 + kappa)) if -1 < kappa < 0 else None
            results.append({
                "crop": crop, "from": a, "to": b, "n_weeks": int(m.sum()), "kappa": round(kappa, 4),
                "p": round(p, 4), "adf_p": round(adf_p, 4), "half_life_weeks": round(half_life, 2) if half_life else None,
                "mean_gap_pct": round(float(np.exp(gap.mean()) - 1) * 100, 2),
            })
    # Holm over distinct unordered pairs (kappa is symmetric in behaviour; test
    # once per pair), on the ADF p-value -- the test whose null distribution
    # actually matches "this gap has a unit root" (see the comment above).
    seen, pvals, pos = {}, [], []
    for i, r in enumerate(results):
        key = (r["crop"], frozenset((r["from"], r["to"])))
        if key not in seen:
            seen[key] = i
            pvals.append(r["adf_p"])
            pos.append(i)
    adj = holm(pvals) if pvals else []
    for i, a in zip(pos, adj):
        results[i]["adf_p_holm"] = round(float(a), 4)
    for r in results:
        key = (r["crop"], frozenset((r["from"], r["to"])))
        r.setdefault("adf_p_holm", results[seen[key]].get("adf_p_holm"))
        r["p_holm"] = r["adf_p_holm"]  # kept under both names: callers read p_holm
        r["closes"] = bool(r["kappa"] < 0 and r["adf_p_holm"] is not None and r["adf_p_holm"] < 0.05)
    return {"pairs": results, "n_tested": len(seen), "n_closing": sum(1 for r in results if r["closes"]) // 2}


def neighbour_signal_series(obs: pd.DataFrame, crop: str, district: str) -> Optional[pd.Series]:
    """Mean weekly log-gap from `district` to its crop-sharing neighbours
    (positive = neighbours dearer), the farmer- and trader-facing quantity
    behind both the field-board note and the sell-plan travel discount."""
    districts = sorted(obs[obs.commodity == crop]["mandi_id"].unique())
    if district not in districts or len(districts) < 2:
        return None
    own = _weekly_log_price(obs, crop, district)
    others = [_weekly_log_price(obs, crop, d) for d in districts if d != district]
    gaps = pd.concat([o - own for o in others], axis=1).mean(axis=1)
    return gaps.dropna()


def evaluate_neighbour_signal(obs: pd.DataFrame, crop: str, district: str) -> Optional[Dict[str, Any]]:
    """Does the current neighbour gap predict next week's own price change
    better than assuming no change? Out-of-sample, expanding window."""
    gap = neighbour_signal_series(obs, crop, district)
    own = _weekly_log_price(obs, crop, district)
    if gap is None or len(gap) < 150:
        return None
    df = pd.concat([gap.rename("gap"), own.rename("p")], axis=1, join="inner").dropna()
    df["y"] = df["p"].shift(-1) - df["p"]
    df = df.dropna()
    if len(df) < 120:
        return None
    preds, actual, dates = [], [], []
    start = 100
    for i in range(start, len(df)):
        train = df.iloc[:i]
        X = np.column_stack([np.ones(len(train)), train["gap"].to_numpy()])
        beta, *_ = np.linalg.lstsq(X, train["y"].to_numpy(), rcond=None)
        preds.append(beta[0] + beta[1] * df["gap"].iloc[i])
        actual.append(df["y"].iloc[i])
        dates.append(df.index[i])
    preds, actual = np.array(preds), np.array(actual)
    mae_model = np.abs(actual - preds).mean()
    mae_naive = np.abs(actual).mean()
    skill = 1 - mae_model / mae_naive if mae_naive > 0 else 0.0
    _, p, n = dm_test(np.abs(actual), np.abs(actual - preds), np.array(dates), 1)
    return {"crop": crop, "district": district, "n": len(preds), "skill": round(float(skill), 4),
            "dm_p": round(p, 4), "earns_signal": bool(skill > 0 and p < 0.05)}
