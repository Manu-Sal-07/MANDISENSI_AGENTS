"""
The agent council: specialist forecasters fused by a learned meta-ensemble, evaluated against the single served model.

Design
------
Each *agent* is a gradient-boosted regressor restricted to one family of evidence, so what it can know is explicit:

* ``seasonality``  calendar position and the series' own seasonal deviation;
* ``supply``       arrivals, their trend and the price-arrival elasticity;
* ``activity``     how often the market reports and trades (silence, gaps, report rate);
* ``trend``        price history: lags, returns, rolling statistics, volatility, momentum.

The *meta-ensemble* combines the agents' predicted h-day log-returns with non-negative least-squares weights. Weights are
learned only from the training window of each walk-forward fold: agents are first fitted on the earlier 75% of that window,
asked to predict the later 25%, and the weights are fitted to those out-of-sample predictions. The agents are then refitted on
the whole window and applied, with those weights, to the fold's test rows. A fold never sees its own test period when choosing
weights, which is the point of doing it here and not with the hand-set weights of the earlier fusion layer.

Evaluation is on the same rows, folds, target and metric as the single pooled model (`train._walk_forward_scores`), so the
two can be compared directly. The council is promoted only where its improvement over the single model is significant; where
it is not, it stays available as an explanation of what each specialist sees, and the report says so.

External factors (weather, news) are not an agent here: there is no historical panel of them to validate a weight against, so
they are shown as live context only and carry no forecast weight.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

AGENT_FEATURES: Dict[str, List[str]] = {
    "seasonality": ["month", "day_of_week", "day_of_year", "week_of_year", "month_sin", "month_cos", "doy_sin", "doy_cos",
                    "seasonal_deviation_pct", "seasonal_reference_years"],
    "supply": ["arrivals", "arrivals_lag_1", "arrivals_lag_7", "arrivals_mean_7", "arrivals_dev", "has_arrivals", "price_arrival_elasticity"],
    "activity": ["days_since_prev", "segment_support", "no_trade_30", "mandi_silent_30", "prev_gap_no_trade", "report_rate_90"],
    "trend": ["modal_price", "price_lag_1", "price_lag_2", "price_lag_3", "price_lag_7", "price_lag_14", "return_1", "return_3", "return_7",
              "roll_mean_7", "roll_std_7", "roll_min_7", "roll_max_7", "roll_mean_14", "roll_std_14", "roll_min_14", "roll_max_14",
              "roll_mean_30", "roll_std_30", "roll_min_30", "roll_max_30", "price_position_30", "dev_from_mean_7", "dev_from_mean_30",
              "volatility_7", "volatility_30", "momentum_7"],
}
SHARED = ["commodity_code"]            # every agent knows which crop it is looking at
INNER_SHARE = 0.75
SERVED_HORIZONS = (3, 5, 7)
OUT_DIR = Path(__file__).resolve().parent.parent / "models" / "council"


def agent_columns(features: List[str]) -> Dict[str, List[str]]:
    cols = {name: [c for c in members if c in features] + [c for c in SHARED if c in features] for name, members in AGENT_FEATURES.items()}
    unassigned = set(features) - {c for v in cols.values() for c in v}
    if unassigned:
        raise ValueError(f"Features not owned by any agent: {sorted(unassigned)}")
    return cols


def nnls_weights(predictions: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Non-negative weights minimising squared error, unconstrained in sum (kept as a reported comparison, not served)."""
    w, _ = nnls(predictions, target)
    return w


def constrain(weights: np.ndarray) -> np.ndarray:
    """Scale weights so they sum to at most 1: a convex (or shrunk) combination that cannot amplify the agents' forecasts.

    Agent forecasts at these horizons are small and noisy, so unconstrained least squares inflates them (weights summing to 2-3),
    which fits the weight-learning window and then magnifies noise on the test period. A combination that sums to at most 1
    can only average or shrink toward no change.
    """
    total = float(weights.sum())
    return weights / total if total > 1.0 else weights


def _fit(frame: pd.DataFrame, columns: List[str], target: str, config: ForecastConfig):
    from mandisense_ai.forecasting.train import _make_estimator

    model = _make_estimator(config)
    model.fit(frame[columns], frame[target], verbose=False)
    return model


def _fit_agents(train: pd.DataFrame, cols: Dict[str, List[str]], target: str, config: ForecastConfig) -> Dict[str, Any]:
    return {name: _fit(train, c, target, config) for name, c in cols.items()}


def _predict(models: Dict[str, Any], frame: pd.DataFrame, cols: Dict[str, List[str]]) -> np.ndarray:
    return np.column_stack([models[name].predict(frame[c]) for name, c in cols.items()])


def learn_weights(train: pd.DataFrame, cols: Dict[str, List[str]], target: str, config: ForecastConfig) -> np.ndarray:
    """Weights fitted on the later part of `train` by agents that saw only its earlier part."""
    train = train.sort_values("date")
    cut = train["date"].quantile(INNER_SHARE)
    early, late = train[train["date"] <= cut], train[train["date"] > cut]
    if len(early) < config.min_train_rows // 2 or len(late) < 50:
        return np.full(len(cols), 1.0 / len(cols))
    inner = _fit_agents(early, cols, target, config)
    return nnls_weights(_predict(inner, late, cols), late[target].to_numpy())


def evaluate(frame: pd.DataFrame, features: List[str], horizon: int, config: ForecastConfig = DEFAULT_CONFIG) -> Dict[str, Any]:
    """Walk-forward comparison for one horizon: no change, single model, each agent, equal-weight and learned-weight councils."""
    from mandisense_ai.forecasting.train import _apply_arrival_dropout, _make_estimator, _mask_arrivals

    cols = agent_columns(features)
    names = list(cols)
    target = f"y_h{horizon}"
    usable = frame[frame[target].notna()].sort_values("date").reset_index(drop=True)
    cuts = [usable["date"].quantile(q) for q in np.linspace(0.5, 1.0, config.walk_forward_folds + 1)]

    rows: List[pd.DataFrame] = []
    fold_weights: List[np.ndarray] = []
    fold_raw: List[np.ndarray] = []
    for k in range(config.walk_forward_folds):
        train = usable[usable["date"] <= cuts[k]]
        valid = usable[(usable["date"] > cuts[k]) & (usable["date"] <= cuts[k + 1])]
        if len(train) < config.min_train_rows or len(valid) < 20:
            continue
        train = _apply_arrival_dropout(train, features, config, seed=config.random_seed + horizon * 100 + k)

        single = _make_estimator(config)
        single.fit(train[features], train[target], verbose=False)
        agents = _fit_agents(train, cols, target, config)
        raw_weights = learn_weights(train, cols, target, config)
        weights = constrain(raw_weights)
        fold_weights.append(weights)
        fold_raw.append(raw_weights)

        out = valid[["date", "commodity", "mandi_id"]].copy()
        out["fold"], out["actual"] = k, valid[target].to_numpy()
        out["single"] = single.predict(valid[features])
        agent_pred = _predict(agents, valid, cols)
        for i, name in enumerate(names):
            out[name] = agent_pred[:, i]
        out["equal"] = agent_pred.mean(axis=1)
        out["council"] = agent_pred @ weights
        out["council_raw"] = agent_pred @ raw_weights

        masked = _mask_arrivals(valid, features)                       # the condition when a feed carries no volumes
        out["single_masked"] = single.predict(masked[features])
        out["council_masked"] = _predict(agents, masked, cols) @ weights
        rows.append(out)

    if not rows:
        return {"status": "INSUFFICIENT_DATA", "horizon": horizon}
    return {"status": "OK", "horizon": horizon, "rows": pd.concat(rows, ignore_index=True), "weights": np.vstack(fold_weights), "raw_weights": np.vstack(fold_raw), "names": names}


def summarise(result: Dict[str, Any], seed: int = 20261029) -> Dict[str, Any]:
    """MAE, skill against no change, and paired block-bootstrap intervals for council versus single model."""
    from mandisense_ai.farmer.transmission import BLOCK_WEEKS, _block_bootstrap_ci

    d = result["rows"]
    y = d["actual"].to_numpy()
    dates = d["date"].astype(str).to_numpy()
    mae = lambda p: float(np.mean(np.abs(y - p)))                       # noqa: E731
    base = float(np.mean(np.abs(y)))                                    # no change: forecast return 0
    methods = ["single", "equal", "council", "council_raw", *result["names"]]
    table = {m: {"mae": round(mae(d[m].to_numpy()), 5), "skill": round(1 - mae(d[m].to_numpy()) / base, 4)} for m in methods}

    def paired(a: str, b: str, ya: Optional[np.ndarray] = None) -> Dict[str, Any]:
        diff = np.abs(y - d[a].to_numpy()) - np.abs(y - d[b].to_numpy())   # negative: a is better than b
        lo, hi = _block_bootstrap_ci(diff, dates, BLOCK_WEEKS, 1000, seed)
        return {"mean_abs_error_diff": round(float(diff.mean()), 5), "ci": [round(float(lo), 5), round(float(hi), 5)],
                "a_better": bool(hi < 0), "b_better": bool(lo > 0)}

    masked = {"single": round(1 - mae(d["single_masked"].to_numpy()) / base, 4), "council": round(1 - mae(d["council_masked"].to_numpy()) / base, 4)}
    folds_won = int(sum(np.mean(np.abs(g["actual"] - g["council"])) < np.mean(np.abs(g["actual"] - g["single"])) for _, g in d.groupby("fold")))
    return {"horizon": result["horizon"], "n": int(len(d)), "folds": int(d["fold"].nunique()), "no_change_mae": round(base, 5), "methods": table,
            "council_vs_single": paired("council", "single"), "council_vs_no_change": {
                "mean_abs_error_diff": round(float(np.mean(np.abs(y - d["council"].to_numpy())) - base), 5)},
            "equal_vs_single": paired("equal", "single"), "arrival_masked_skill": masked, "folds_council_beats_single": folds_won,
            "mean_weights": {n: round(float(w), 3) for n, w in zip(result["names"], result["weights"].mean(axis=0))},
            "weight_sum": round(float(result["weights"].sum(axis=1).mean()), 3),
            "unconstrained_weight_sum": round(float(result["raw_weights"].sum(axis=1).mean()), 3)}


def promote(summary: Dict[str, Any]) -> bool:
    """The council replaces the single model at a horizon only if it is significantly better and wins most folds."""
    s = summary["council_vs_single"]
    return bool(s["a_better"] and summary["folds_council_beats_single"] >= max(3, summary["folds"] - 1))


def final_forecasts(observations: pd.DataFrame, frame: pd.DataFrame, features: List[str], summaries: Dict[int, Dict[str, Any]],
                    config: ForecastConfig = DEFAULT_CONFIG) -> Dict[str, Any]:
    """Refit every agent on all data and score the latest feature row of every series, with the per-agent view kept."""
    from mandisense_ai.forecasting.features import latest_feature_rows
    from mandisense_ai.forecasting.train import _apply_arrival_dropout, _make_estimator

    cols = agent_columns(features)
    names = list(cols)
    codes = frame[["commodity", "commodity_code"]].drop_duplicates().set_index("commodity")["commodity_code"].to_dict()
    latest = latest_feature_rows(observations, config)
    latest["commodity_code"] = latest["commodity"].map(codes)
    out: Dict[str, Any] = {}
    for h, summ in summaries.items():
        target = f"y_h{h}"
        usable = frame[frame[target].notna()].sort_values("date")
        usable = _apply_arrival_dropout(usable, features, config, seed=config.random_seed + h * 100 + 99)
        agents = _fit_agents(usable, cols, target, config)
        single = _make_estimator(config)
        single.fit(usable[features], usable[target], verbose=False)
        w = constrain(np.array([summ["mean_weights"][n] for n in names]))      # re-applied: stored weights are rounded for display
        pa = _predict(agents, latest, cols)
        ps = single.predict(latest[features])
        for i, row in enumerate(latest.itertuples()):
            key = f"{row.commodity}|{row.mandi_id}"
            price = float(row.modal_price)
            pct = lambda r: round(100 * (float(np.exp(r)) - 1), 2)       # noqa: E731
            out.setdefault(key, {"commodity": row.commodity, "mandi_id": row.mandi_id, "as_of": str(pd.Timestamp(row.date).date()),
                                 "last_price": price, "horizons": {}})["horizons"][str(h)] = {
                "agents": {n: pct(pa[i, j]) for j, n in enumerate(names)}, "weights": {n: float(w[j]) for j, n in enumerate(names)},
                "council_pct": pct(float(pa[i] @ w)), "single_pct": pct(ps[i]), "promoted": promote(summ),
                "council_price": round(price * float(np.exp(pa[i] @ w)), 2)}
    return out


def run(output_dir: Path = OUT_DIR, horizons=SERVED_HORIZONS, config: ForecastConfig = DEFAULT_CONFIG) -> Dict[str, Any]:
    from mandisense_ai.forecasting.sources.backfill import load_all_history
    from mandisense_ai.forecasting.train import _prepare_training_frame

    t0 = time.time()
    observations = load_all_history()
    frame, features = _prepare_training_frame(observations, config)
    summaries: Dict[int, Dict[str, Any]] = {}
    for h in horizons:
        res = evaluate(frame, features, h, config)
        if res["status"] == "OK":
            summaries[h] = summarise(res)
            logger.info("council h=%s skill %s vs single %s", h, summaries[h]["methods"]["council"]["skill"], summaries[h]["methods"]["single"]["skill"])
    forecasts = final_forecasts(observations, frame, features, summaries, config)
    result = {"generated_at": pd.Timestamp.utcnow().isoformat(), "seconds": round(time.time() - t0, 1), "agents": {k: len(v) for k, v in agent_columns(features).items()},
              "rule": "promote where the paired block-bootstrap CI of (council - single) absolute error excludes 0 on the better side and the council wins at least 3 folds",
              "horizons": {str(h): {**s, "promoted": promote(s)} for h, s in summaries.items()}}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    (output_dir / "forecasts.json").write_text(json.dumps({"generated_at": result["generated_at"], "series": forecasts}, indent=1), encoding="utf-8")
    return result
