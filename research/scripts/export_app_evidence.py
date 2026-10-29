"""Export the study's evidence into the MandiSense application.

    python scripts/export_app_evidence.py

Writes  MS-AI/mandisense_ai/data/market_choice/evidence.json   (served at /v1/market-choice/evidence)
        frontend/public/evidence/*.png                    (the paper's figures, for the Evidence page)

Every number comes from results/ (the same files the manuscript is generated from).
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT.parent
R = ROOT / "results"
PAPER_FIGS = ROOT.parent / "papers" / "IEEE_Access" / "figures"
OUT_JSON = APP / "mandisense_ai" / "data" / "market_choice" / "evidence.json"
OUT_FIGS = APP / "frontend" / "public" / "evidence"

LABELS = {
    "rw": "Random walk", "lgbm_obs": "LightGBM, observed prices", "xgb_obs": "XGBoost, observed prices",
    "ds_mse_obs": "Neural, observed prices", "lgbm_filled": "LightGBM, realised outcomes",
    "lgbm_filled_sil": "LightGBM, realised outcomes + silence", "ds_mse_filled": "Neural, realised outcomes",
    "ds_spo": "Neural SPO+, realised outcomes", "ds_spo_struct": "SPO+ + reporting head",
    "gfmc_pred": "SPO+ + head + silence", "gfmc_pred_tuneMSE": "SPO+ + head + silence, tuned on forecast loss",
    "nearest_today": "Nearest mandi, sell today", "highest_yesterday": "Mandi with highest price yesterday",
    "trailing_best": "Best 7-day mean price", "farm_gate": "Sell at the farm gate",
}
OBSERVED = {"rw", "lgbm_obs", "xgb_obs", "ds_mse_obs"}
HEURISTIC = {"nearest_today", "highest_yesterday", "trailing_best", "farm_gate"}

FIGURES = [
    ("fig_decision", "Decision value", "Models trained on realised outcomes (blue) earn more per quintal than models trained on observed prices (grey) or simple rules (gold), and the gain recurs in every test period."),
    ("fig_effects", "What produces the gain", "Only training on realised outcomes helps. The decision-focused loss, a reporting head, other mandis' silence and decision-based tuning add nothing significant."),
    ("fig_floor", "The guaranteed floor", "The conformal floor is broken about as often as it says; a naive Gaussian floor is not."),
    ("fig_leak", "Decomposition hybrids and look-ahead", "Forecasting methods that decompose the price series first look excellent only when the decomposition is allowed to see the future."),
    ("fig_decouple", "Forecast accuracy is not decision value", "The models that choose best are not the ones with the lowest forecast error."),
    ("fig_sens", "Robustness to cost assumptions", "The advantage holds across transport, spoilage and closed-mandi assumptions."),
]


def verdict(r) -> str:
    if r["holm_p"] < 0.05:
        return "better" if r["regret_diff_A_minus_B"] < 0 else "worse"
    return "no_effect"


def main() -> None:
    t = R / "tomato" / "tables"
    main_t = pd.read_csv(t / "main.csv")
    comp = pd.read_csv(t / "comparisons.csv")
    floors = pd.read_csv(t / "floors.csv")
    fc = pd.read_csv(t / "forecast_accuracy.csv")
    lk = pd.read_csv(R / "tomato" / "leakage" / "summary.csv")
    sens = pd.read_csv(R / "tomato" / "leakage" / "future_sensitivity.csv")
    found = pd.read_csv(R / "tomato" / "leakage" / "foundation_skill.csv")
    sil = json.loads((R / "tomato" / "silence" / "summary.json").read_text())
    summ = json.loads((R / "tomato" / "summary.json").read_text())

    oracle = float(main_t.loc[main_t["method"] == "oracle(hindsight)", "revenue"].iloc[0])
    methods = []
    for _, r in main_t[main_t["method"] != "oracle(hindsight)"].iterrows():
        m = r["method"]
        methods.append({
            "method": m, "label": LABELS.get(m, m),
            "class": "heuristic" if m in HEURISTIC else ("observed" if m in OBSERVED else "realised"),
            "revenue": round(float(r["revenue"]), 0), "regret": round(float(r["regret"]), 0),
            "gap_closed": round(float(r["gap_closed_vs_nearest"]), 3), "cvar10": round(float(r["cvar10"]), 0),
            "fallback_rate": round(float(r["fallback_rate"]), 3),
        })
    methods.sort(key=lambda x: -x["revenue"])

    effects = []
    for _, r in comp.iterrows():
        effects.append({"label": r["comparison"], "diff": round(float(r["regret_diff_A_minus_B"]), 1),
                        "ci_lo": round(float(r["ci_lo"]), 1), "ci_hi": round(float(r["ci_hi"]), 1),
                        "holm_p": round(float(r["holm_p"]), 4), "verdict": verdict(r)})

    crops = []
    for crop in ("tomato", "onion", "potato"):
        ct = pd.read_csv(R / crop / "tables" / "comparisons.csv")
        row = ct[ct["comparison"].str.contains("label effect")].iloc[0]
        mt = pd.read_csv(R / crop / "tables" / "main.csv").set_index("method")
        loss = ct[ct["comparison"].str.contains("loss effect")].iloc[0]
        crops.append({
            "crop": crop, "markets": {"tomato": 12, "onion": 4, "potato": 3}[crop],
            "oracle": round(float(mt.loc["oracle(hindsight)", "revenue"]), 0),
            "heuristic": round(float(mt.loc["highest_yesterday", "revenue"]), 0),
            "observed_labels": round(float(mt.loc["lgbm_obs", "revenue"]), 0),
            "realised_labels": round(float(mt.loc["lgbm_filled", "revenue"]), 0),
            "label_effect": {"diff": round(float(row["regret_diff_A_minus_B"]), 0), "ci_lo": round(float(row["ci_lo"]), 0),
                             "ci_hi": round(float(row["ci_hi"]), 0), "holm_p": round(float(row["holm_p"]), 4)},
            "loss_effect": {"diff": round(float(loss["regret_diff_A_minus_B"]), 0), "p": round(float(loss["dm_p"]), 3)},
        })

    floor_rows = []
    for spec, name in (("gfmc_pred", "SPO+ model"), ("lgbm_filled", "LightGBM, realised outcomes"), ("lgbm_obs", "LightGBM, observed prices")):
        for _, r in floors[floors["spec"] == spec].iterrows():
            if r["policy"] == "plug-in (no floor)":
                continue
            floor_rows.append({"predictor": name, "policy": r["policy"], "alpha": None if pd.isna(r["alpha"]) else float(r["alpha"]),
                               "violation": round(float(r["violation"]), 3), "mean_floor": round(float(r["mean_floor"]), 0),
                               "revenue": round(float(r["revenue"]), 0), "cvar10": round(float(r["cvar10"]), 0)})

    leakage = [{
        "decomposer": r["decomposer"], "forecaster": "Ridge" if r["forecaster"] == "ridge" else "LightGBM", "h": int(r["h"]),
        "published": round(float(r["skill_published"]), 3), "published_joint": round(float(r["skill_published_joint"]), 3),
        "causal_joint": round(float(r["skill_causal_joint"]), 3), "raw": round(float(r["skill_raw"]), 3),
        "gap": round(float(r["leak_gap_skill"]), 3), "gap_ci_lo": round(float(r["leak_gap_ci_lo"]), 3),
        "gap_ci_hi": round(float(r["leak_gap_ci_hi"]), 3)} for _, r in lk.iterrows()]

    f = fc.set_index("method")
    mm = main_t.set_index("method")
    decouple = [{"method": m, "label": LABELS.get(m, m), "skill_observed": round(float(f.loc[m, "skill_vs_rw_observed"]), 3),
                 "skill_realised": round(float(f.loc[m, "skill_vs_rw_realised"]), 3),
                 "gap_closed_vs_heuristic": round(float(mm.loc[m, "gap_closed_vs_yday"]), 3)}
                for m in ("lgbm_obs", "xgb_obs", "ds_mse_obs", "lgbm_filled", "ds_mse_filled") if m in f.index]

    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "GFMC study (research/docs/RESULTS.md); every number is out of sample",
        "study": {"crop": "tomato", "mandis": 12, "decision_days": summ["test_days"], "folds": len(summ["folds"]),
                  "period": [str(pd.Timestamp("2024-01-01").date()), "2026-10-27"], "oracle_revenue": oracle,
                  "data": "Agmarknet exports, Karnataka, 2021-2026; no synthetic or imputed prices"},
        "decision": {"methods": methods},
        "effects": effects, "crops": crops, "floors": floor_rows, "leakage": leakage,
        "future_sensitivity": [{"decomposer": r["decomposer"], "median": round(float(r["median_future_sensitivity"]), 4)} for _, r in sens.iterrows()],
        "foundation_model": {str(int(r["h"])): round(float(r["skill_foundation"]), 3) for _, r in found.iterrows()},
        "silence": {"reporting_delta_auc": round(float(sil["reporting"]["mean_dAUC"]), 4), "returns_dm_p": round(float(sil["returns_dm"]["p"]), 3)},
        "forecast_vs_decision": decouple,
        "negative_results": [
            {"id": "spo_loss", "text": "The decision-focused SPO+ loss did not beat a squared-error loss on the same labels in any crop."},
            {"id": "reporting_head", "text": "A model head that predicts whether a mandi will report made decisions slightly worse."},
            {"id": "silence", "text": "Whether neighbouring mandis are silent adds nothing beyond a mandi's own reporting history."},
            {"id": "tuning", "text": "Tuning on decision regret instead of forecast error made no measurable difference."},
            {"id": "floor_tail", "text": "The revenue floor states a verified minimum but does not by itself improve the worst outcomes."},
        ],
        "limitations": [
            "Transport, spoilage, fee and closed-mandi costs are scenario assumptions, not estimates of any farmer's costs.",
            "'Did not report' is treated as 'no sale at that mandi that day'.",
            "Results replay historical prices; they ignore the effect of your own sale on the price and the capacity of small mandis.",
            "Onion and potato have few mandis, so they are weaker tests of choosing between mandis.",
        ],
        "figures": [{"id": i, "title": ti, "caption": ca, "path": f"/evidence/{i}.png"} for i, ti, ca in FIGURES],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    OUT_FIGS.mkdir(parents=True, exist_ok=True)
    made = []
    for fid, _, _ in FIGURES:
        src = PAPER_FIGS / f"{fid}.pdf"
        if not src.exists():
            continue
        subprocess.run(["pdftoppm", "-png", "-r", "170", "-singlefile", str(src), str(OUT_FIGS / fid)], check=True)
        made.append(fid)
    print(f"wrote {OUT_JSON.name} and {len(made)} figures to {OUT_FIGS}")


if __name__ == "__main__":
    main()
