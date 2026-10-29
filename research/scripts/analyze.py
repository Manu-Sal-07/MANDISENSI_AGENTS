"""Build every table and figure of the decision study from cached predictions.

    python scripts/analyze.py [--crop Tomato]

Outputs: results/<crop>/tables/*.csv, results/<crop>/figures/*.png, results/<crop>/summary.json
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gfmc.analysis import HEURISTICS, Study  # noqa: E402
from gfmc.config import RESULTS_DIR, SWEEPS  # noqa: E402

PALETTE = {"proposed": "#0b6e4f", "ablation": "#4c78a8", "baseline": "#9a9a9a", "heuristic": "#c8a951"}
PAIRS = [
    ("gfmc_pred", "rw", "GFMC predictor vs random walk"),
    ("gfmc_pred", "lgbm_obs", "GFMC predictor vs LightGBM (predict-then-optimise)"),
    ("gfmc_pred", "xgb_obs", "GFMC predictor vs XGBoost (predict-then-optimise)"),
    ("gfmc_pred", "lgbm_filled", "GFMC predictor vs LightGBM on realised-revenue labels"),
    ("gfmc_pred", "highest_yesterday", "GFMC predictor vs best simple heuristic"),
    ("ds_mse_filled", "ds_mse_obs", "[label effect] realised-revenue labels vs observed-price labels"),
    ("lgbm_filled", "lgbm_obs", "[label effect, GBM] realised-revenue labels vs observed-price labels"),
    ("ds_spo", "lgbm_obs", "SPO+ network on realised labels vs LightGBM predict-then-optimise"),
    ("ds_spo", "ds_mse_filled", "[loss effect] SPO+ vs MSE, same labels and network"),
    ("ds_spo_struct", "ds_spo", "[head effect] reporting head vs none"),
    ("gfmc_pred", "ds_spo_struct", "[silence effect] + network silence features"),
    ("lgbm_filled_sil", "lgbm_filled", "[silence effect] GBM with vs without silence features"),
    ("gfmc_pred", "gfmc_pred_tuneMSE", "[tuning effect] tuned on decision regret vs forecast loss"),
    ("ds_spo_struct", "lgbm_filled", "structured SPO+ network vs GBM, both on realised labels"),
]
LADDER = ["rw", "lgbm_obs", "lgbm_filled", "ds_mse_filled", "ds_spo", "ds_spo_struct", "gfmc_pred"]


OBSERVED_LABEL = ("rw", "lgbm_obs", "xgb_obs", "ds_mse_obs")


def color(m: str) -> str:
    """Green: trained on realised-outcome labels (the finding). Grey: forecast-trained. Gold: heuristics."""
    if m in HEURISTICS:
        return PALETTE["heuristic"]
    if m in OBSERVED_LABEL:
        return PALETTE["baseline"]
    return PALETTE["proposed"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", default="Tomato")
    a = ap.parse_args()
    out = RESULTS_DIR / a.crop.lower()
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    st = Study(a.crop)
    print("available specs:", st.available, flush=True)
    summary = {"crop": a.crop, "test_days": int(len(st.test_idx)), "folds": st.fold_ids,
               "specs": st.available, "load_report": st.load_report.as_dict()}

    main_t = st.main_table()
    main_t.to_csv(out / "tables" / "main.csv", index=False)
    st.per_fold_table(["nearest_today", "highest_yesterday"] + [m for m in ["lgbm_obs", "ds_spo", "gfmc_pred"] if m in st.available]) \
        .to_csv(out / "tables" / "per_fold.csv", index=False)
    st.per_origin_table(["nearest_today", "highest_yesterday"] + [m for m in ["lgbm_obs", "gfmc_pred"] if m in st.available]) \
        .to_csv(out / "tables" / "per_origin.csv", index=False)
    comp = st.comparisons(PAIRS)
    comp.to_csv(out / "tables" / "comparisons.csv", index=False)
    mcs = st.confidence_set(list(HEURISTICS) + st.available)
    summary["model_confidence_set"] = mcs
    st.forecast_table().to_csv(out / "tables" / "forecast_accuracy.csv", index=False)
    auc = st.report_auc()
    auc.to_csv(out / "tables" / "report_auc.csv", index=False)
    st.report_auc_baselines().to_csv(out / "tables" / "report_auc_baselines.csv", index=False)

    floor_specs = [s for s in ("gfmc_pred", "ds_spo_struct", "lgbm_filled", "lgbm_obs", "rw") if s in st.available]
    floors = st.floor_table(floor_specs)
    floors.to_csv(out / "tables" / "floors.csv", index=False)
    if "gfmc_pred" in st.available:
        r = st.floor_run("gfmc_pred")
        summary["gfmc_floor_violation"] = r["violation"]
        summary["gfmc_floor_violation_by_fold"] = r["violation_by_fold"]

    sweep_methods = [m for m in ("rw", "lgbm_obs", "lgbm_filled", "ds_spo_struct", "gfmc_pred") if m in st.available]
    st.sweep(sweep_methods, SWEEPS).to_csv(out / "tables" / "sensitivity.csv", index=False)

    # ----------------------------------------------------------- figures
    _fig_main(main_t, out / "figures" / "fig_main_revenue.png")
    _fig_ladder(main_t, out / "figures" / "fig_ablation_ladder.png")
    if len(floors):
        _fig_floor(floors, out / "figures" / "fig_floor_calibration.png")
        _fig_risk(main_t, floors, out / "figures" / "fig_risk_return.png")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("wrote", out, flush=True)


def _fig_main(t: pd.DataFrame, path: Path) -> None:
    orc_row = t.loc[t["method"] == "oracle(hindsight)", "revenue"]
    orc = float(orc_row.iloc[0]) if len(orc_row) else None
    t = t[t["method"] != "oracle(hindsight)"].sort_values("revenue")
    fig, ax = plt.subplots(figsize=(8.2, 0.34 * len(t) + 1.3))
    err = np.vstack([t["revenue"] - t["rev_ci_lo"], t["rev_ci_hi"] - t["revenue"]])
    ax.barh(t["method"], t["revenue"], xerr=err, color=[color(m) for m in t["method"]], ecolor="#333", capsize=2)
    ax.set_xlabel("Mean realised net revenue (Rs / quintal), out of sample")
    ax.set_xlim(t["revenue"].min() * 0.9, max(t["rev_ci_hi"].max(), orc or 0) * 1.03)
    if orc:
        ax.axvline(orc, ls="--", color="#555", lw=1)
        ax.text(orc, -0.9, " hindsight oracle", fontsize=8, color="#555", va="top")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _fig_ladder(t: pd.DataFrame, path: Path) -> None:
    rows = [t[t["method"] == m].iloc[0] for m in LADDER if (t["method"] == m).any()]
    if not rows:
        return
    d = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(range(len(d)), d["gap_closed_vs_yday"], marker="o", color=PALETTE["proposed"])
    for i, v in enumerate(d["gap_closed_vs_yday"]):
        ax.annotate(f"{v:.2f}", (i, v), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels(d["method"], rotation=25, ha="right")
    ax.set_ylabel("Share of oracle gap closed\n(relative to 'highest price yesterday')")
    ax.axhline(0, color="#999", lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _fig_floor(f: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.0, 4.8))
    ax.plot([0, 0.3], [0, 0.3], ls="--", color="#777", lw=1, label="ideal (violation = alpha)")
    for spec, ls, col in (("gfmc_pred", "-", PALETTE["proposed"]), ("lgbm_obs", "--", "#7a7a7a")):
        g = f[f["spec"] == spec]
        if g.empty:
            continue
        ad = g[g["policy"] == "adaptive conformal floor"]
        ax.plot(ad["alpha"], ad["violation"], marker="o", ls=ls, color=col, label=f"adaptive conformal - {spec}")
        nv = g[g["policy"].str.startswith("naive")]
        ax.scatter(nv["alpha"], nv["violation"], marker="s", color=col, edgecolor="#c0392b", linewidth=1.6, s=55,
                   label=f"naive Gaussian floor (z = 1.28) - {spec}")
    ax.set_xlabel("target floor-violation rate alpha")
    ax.set_ylabel("observed violation rate (out of sample)")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _fig_risk(main_t: pd.DataFrame, floors: pd.DataFrame, path: Path) -> None:
    d = main_t[~main_t["method"].isin(["oracle(hindsight)"])]
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.scatter(d["revenue"], d["cvar10"], c=[color(m) for m in d["method"]], s=45)
    for _, r in d.iterrows():
        ax.annotate(r["method"], (r["revenue"], r["cvar10"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    g = floors[(floors["spec"] == "gfmc_pred") & (floors["policy"] == "adaptive conformal floor") & (floors["alpha"] == 0.10)]
    if len(g):
        ax.scatter(g["revenue"], g["cvar10"], marker="*", s=170, c=PALETTE["proposed"], edgecolor="k", zorder=5,
                   label="GFMC + conformal floor (alpha = 0.10)")
        ax.legend(fontsize=8, frameon=False)
    ax.set_xlabel("mean net revenue (Rs / quintal)")
    ax.set_ylabel("CVaR10: mean of worst 10% outcomes (Rs / quintal)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
