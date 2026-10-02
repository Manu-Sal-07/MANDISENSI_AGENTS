"""
Build the cross-commodity / cross-district transmission artifact for the
farmer data world (Test A, B from PREREGISTERED_ADDENDUM_2_TRANSMISSION.txt).

    python scripts/build_transmission.py            # A + B + neighbour signals
    python scripts/build_transmission.py --test-c    # also run Test C (slow:
                                                      #   retrains the walk-forward
                                                      #   model with and without
                                                      #   transmission features)

Writes:
  mandisense_ai/models/farmer/transmission_matrix.json   (served to the app)
  IEEE_Paper/experiments/results/transmission_stats.json (for the paper)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mandisense_ai.farmer import registry, transmission as tr, world  # noqa: E402

RESULTS_DIR = Path(r"D:\BMS COLL\PROJECT\MS-AI\IEEE_Paper\experiments\results")


def run_test_c(obs) -> dict:
    """Does adding transmission features to the production forecaster help?
    Re-runs the single-model walk-forward protocol with and without the
    extra features and compares them with the paper's own DM test."""
    import numpy as np
    import pandas as pd

    from mandisense_ai.forecasting.config import DEFAULT_CONFIG as CFG
    from mandisense_ai.forecasting.train import _prepare_training_frame, _apply_arrival_dropout, _make_estimator, _sample_weights
    import stats_lib as sl  # type: ignore
    sys.path.insert(0, str(Path(r"D:\BMS COLL\PROJECT\MS-AI\IEEE_Paper\experiments")))
    import stats_lib as sl  # noqa: E402,F811

    crops = sorted(obs["commodity"].unique())
    extra_frames = []
    for crop in crops:
        districts = sorted(obs[obs.commodity == crop]["mandi_id"].unique())
        for district in districts:
            gap = tr.neighbour_signal_series(obs, crop, district)
            if gap is None:
                continue
            daily_gap = gap.reindex(pd.date_range(gap.index.min(), gap.index.max(), freq="D")).ffill(limit=6)
            extra_frames.append(pd.DataFrame({"date": daily_gap.index, "commodity": crop, "mandi_id": district,
                                              "neighbour_gap": daily_gap.to_numpy(),
                                              "neighbour_gap_chg_7d": daily_gap.diff(7).to_numpy()}))
    extra = pd.concat(extra_frames, ignore_index=True) if extra_frames else pd.DataFrame()

    frame, features = _prepare_training_frame(obs, CFG)
    frame = frame.merge(extra, on=["date", "commodity", "mandi_id"], how="left")
    frame["neighbour_gap"] = frame["neighbour_gap"].fillna(0.0)
    frame["neighbour_gap_chg_7d"] = frame["neighbour_gap_chg_7d"].fillna(0.0)
    new_features = features + ["neighbour_gap", "neighbour_gap_chg_7d"]

    horizons = {}
    for h in CFG.horizons:
        y = f"y_h{h}"
        usable = frame[frame[y].notna()].sort_values(["date", "mandi_id", "commodity"], kind="mergesort").reset_index(drop=True)
        cuts = [usable["date"].quantile(q) for q in np.linspace(0.5, 1.0, CFG.walk_forward_folds + 1)]
        rows = []
        for i in range(CFG.walk_forward_folds):
            train = usable[usable["date"] <= cuts[i]]
            valid = usable[(usable["date"] > cuts[i]) & (usable["date"] <= cuts[i + 1])]
            if len(train) < CFG.min_train_rows or len(valid) < 20:
                continue
            for feat_set, tag in ((features, "base"), (new_features, "with_transmission")):
                fit = _apply_arrival_dropout(train, feat_set, CFG, seed=CFG.random_seed + h * 100 + i)
                model = _make_estimator(CFG)
                model.fit(fit[feat_set], fit[y], sample_weight=_sample_weights(fit, CFG), verbose=False)
                pred = model.predict(valid[feat_set])
                rows.append(pd.DataFrame({"tag": tag, "date": valid["date"].to_numpy(), "actual": valid[y].to_numpy(), "pred": pred}))
        fold_df = pd.concat(rows, ignore_index=True)
        base = fold_df[fold_df.tag == "base"].reset_index(drop=True)
        trans = fold_df[fold_df.tag == "with_transmission"].reset_index(drop=True)
        mae_base = np.abs(base.actual - base.pred).mean()
        mae_trans = np.abs(trans.actual - trans.pred).mean()
        skill_gain = 1 - mae_trans / mae_base
        abs_base, abs_trans = np.abs(base.actual - base.pred).to_numpy(), np.abs(trans.actual - trans.pred).to_numpy()
        stat, p, n = sl.dm_test(abs_base, abs_trans, base.date.to_numpy(), h)
        lo, hi = sl.block_boot(pd.DataFrame({"date": base.date, "a": abs_base, "b": abs_trans}),
                               lambda g: 1 - g["b"].mean() / g["a"].mean(), B=1000)
        horizons[str(h)] = {"mae_base": float(mae_base), "mae_with_transmission": float(mae_trans),
                            "skill_gain_pct": round(float(skill_gain) * 100, 3), "ci": [round(float(lo) * 100, 3), round(float(hi) * 100, 3)],
                            "dm_p": float(p)}
    from mandisense_ai.farmer.significance import holm
    pvals = [horizons[str(h)]["dm_p"] for h in CFG.horizons]
    for h, adj in zip(CFG.horizons, holm(pvals)):
        horizons[str(h)]["dm_p_holm"] = round(float(adj), 4)
    helps = any(horizons[str(h)]["dm_p_holm"] < 0.05 and horizons[str(h)]["ci"][0] > 0 for h in CFG.horizons)
    return {"horizons": horizons, "transmission_helps_forecast": helps}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-c", action="store_true")
    args = parser.parse_args()

    obs = world.district_observations()
    crops = sorted(obs["commodity"].unique())
    print(f"crops={crops}", flush=True)

    t0 = time.time()
    test_a = tr.run_test_a(obs, crops)
    print(f"Test A done: {test_a['n_published']}/{test_a['n_tested']} published, {time.time()-t0:.0f}s", flush=True)

    t0 = time.time()
    test_b = tr.run_test_b(obs, crops)
    print(f"Test B done: {test_b['n_closing']}/{test_b['n_tested']} pairs close, {time.time()-t0:.0f}s", flush=True)

    neighbour = {}
    for crop in crops:
        for district in sorted(obs[obs.commodity == crop]["mandi_id"].unique()):
            r = tr.evaluate_neighbour_signal(obs, crop, district)
            if r:
                neighbour[f"{crop}/{district}"] = r
    n_earned = sum(v["earns_signal"] for v in neighbour.values())
    print(f"Neighbour signal: {n_earned}/{len(neighbour)} series earn it", flush=True)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {"from": str(obs["date"].min().date()), "to": str(obs["date"].max().date()), "crops": crops,
                 "districts": sorted(obs["mandi_id"].unique().tolist())},
        "test_a_cross_commodity": test_a,
        "test_b_spatial_gaps": test_b,
        "neighbour_signal": neighbour,
    }

    if args.test_c:
        t0 = time.time()
        out["test_c_forecast_value"] = run_test_c(obs)
        print(f"Test C done, {time.time()-t0:.0f}s", flush=True)

    world.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (world.MODEL_DIR / "transmission_matrix.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "transmission_stats.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("WROTE transmission_matrix.json and transmission_stats.json", flush=True)


if __name__ == "__main__":
    main()
