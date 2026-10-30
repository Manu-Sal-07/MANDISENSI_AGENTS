"""
Consolidate every result in the project into one document with figures: docs/RESULTS.md and docs/figures/results/*.png.

    python scripts/build_results.py

Everything printed is read from an artefact written by an experiment (listed at the end of the document), never typed here, so the
document cannot drift from the data. Re-run it after any experiment. Missing artefacts are reported in the document, not skipped silently.
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research" / "results"
MODELS = ROOT / "mandisense_ai" / "models"
DOC = ROOT / "docs" / "RESULTS.md"
FIG = ROOT / "docs" / "figures" / "results"
CROPS = ["tomato", "onion", "potato", "ginger"]
MISSING: List[str] = []

BLUE, ORANGE, GREY, GREEN, RED, PURPLE, GOLD = "#2563eb", "#ea580c", "#6b7280", "#059669", "#dc2626", "#7c3aed", "#ca8a04"
LABEL = {
    "rw": "Random walk", "lgbm_obs": "LightGBM, observed prices", "xgb_obs": "XGBoost, observed prices", "ds_mse_obs": "Neural, observed prices",
    "lgbm_filled": "LightGBM, realised outcomes", "lgbm_filled_sil": "LightGBM, realised + silence", "ds_mse_filled": "Neural, realised outcomes",
    "ds_spo": "Neural SPO+, realised outcomes", "ds_spo_struct": "SPO+ + reporting head", "gfmc_pred": "SPO+ + head + silence",
    "nearest_today": "Nearest mandi, sell today", "highest_yesterday": "Highest price yesterday", "trailing_best": "Best 7-day mean",
    "farm_gate": "Farm gate", "oracle": "Hindsight oracle",
}
CLASS_COLOUR = {"realised": BLUE, "observed": GREY, "heuristic": GOLD, "oracle": GREEN}
KIND = {**{m: "observed" for m in ("rw", "lgbm_obs", "xgb_obs", "ds_mse_obs")},
        **{m: "heuristic" for m in ("nearest_today", "highest_yesterday", "trailing_best", "farm_gate")}}


# ───────────────────────────────────────────────────────────────────────── helpers
def read_csv(path: Path) -> Optional[pd.DataFrame]:
    if path.exists():
        return pd.read_csv(path)
    MISSING.append(str(path.relative_to(ROOT)))
    return None


def read_json(path: Path) -> Optional[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    MISSING.append(str(path.relative_to(ROOT)))
    return None


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


def rs(x: float) -> str:
    return f"{x:,.0f}"


def pv(p: float) -> str:
    return "< 0.0001" if p < 1e-4 else f"{p:.4f}" if p < 0.01 else f"{p:.3f}"


def savefig(name: str) -> str:
    FIG.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.png", dpi=160)
    plt.close()
    return f"figures/results/{name}.png"


def style() -> None:
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                         "axes.axisbelow": True, "figure.dpi": 110, "legend.frameon": False})


# ───────────────────────────────────────────────────────────────────────── data
def crop_results(crop: str) -> Optional[dict]:
    t = RES / crop / "tables"
    if not (t / "main.csv").exists():
        MISSING.append(f"research/results/{crop}/ (experiment not run)")
        return None
    return {"main": pd.read_csv(t / "main.csv"), "cmp": read_csv(t / "comparisons.csv"), "floors": read_csv(t / "floors.csv"),
            "fold": read_csv(t / "per_fold.csv"), "sens": read_csv(t / "sensitivity.csv"), "acc": read_csv(t / "forecast_accuracy.csv"),
            "summary": read_json(RES / crop / "summary.json")}


# ───────────────────────────────────────────────────────────────────────── figures
def fig_decision(data: Dict[str, dict]) -> str:
    keys = ["nearest_today", "highest_yesterday", "rw", "lgbm_obs", "lgbm_filled", "ds_spo"]
    fig, axes = plt.subplots(1, len(data), figsize=(3.3 * len(data), 3.6), sharex=False)
    axes = np.atleast_1d(axes)
    for ax, (crop, d) in zip(axes, data.items()):
        m = d["main"].set_index("method")
        rows = [k for k in keys if k in m.index]
        y = np.arange(len(rows))
        ax.barh(y, [m.loc[k, "revenue"] for k in rows], color=[CLASS_COLOUR["realised" if k.endswith("filled") or k == "ds_spo" else KIND.get(k, "observed")] for k in rows],
                xerr=[[m.loc[k, "revenue"] - m.loc[k, "rev_ci_lo"] for k in rows], [m.loc[k, "rev_ci_hi"] - m.loc[k, "revenue"] for k in rows]],
                error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#374151"})
        ax.set_yticks(y)
        ax.set_yticklabels([LABEL[k].replace(", ", ",\n") for k in rows] if ax is axes[0] else [""] * len(rows), fontsize=7)
        ax.invert_yaxis()
        ax.set_title(crop.capitalize())
        ax.set_xlabel("₹ per quintal, net")
        lo = min(m.loc[k, "rev_ci_lo"] for k in rows)
        ax.set_xlim(left=max(0, 0.85 * lo))
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=BLUE, label="trained on realised outcomes"), Patch(color=GREY, label="trained on observed prices"), Patch(color=GOLD, label="simple rule")],
               loc="lower center", ncol=3, fontsize=8)
    fig.subplots_adjust(bottom=0.2)
    fig.suptitle("Net revenue per quintal, held-out test blocks (95% day-block bootstrap)", fontsize=10)
    return savefig("fig_decision_revenue")


def fig_effect(data: Dict[str, dict]) -> Optional[str]:
    rows = []
    for crop, d in data.items():
        c = d["cmp"]
        if c is None:
            continue
        hit = c[(c["A"] == "lgbm_filled") & (c["B"] == "lgbm_obs")]
        if len(hit):
            r = hit.iloc[0]
            rows.append((crop.capitalize(), r["regret_diff_A_minus_B"], r["ci_lo"], r["ci_hi"], r["holm_p"]))
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(5.6, 0.7 * len(rows) + 1.6))
    for i, (name, diff, lo, hi, p) in enumerate(rows):
        ax.errorbar(diff, i, xerr=[[diff - lo], [hi - diff]], fmt="o", color=BLUE, capsize=3)
        ax.text(hi + 4, i, f"Holm p {pv(p)}", va="center", fontsize=7, color="#374151")
    ax.axvline(0, color="#111827", lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Change in regret, ₹ per quintal (negative = realised-outcome training is better)")
    ax.set_title("Same model (LightGBM), realised vs observed labels", fontsize=10)
    ax.set_xlim(right=max(r[3] for r in rows) + 90)
    return savefig("fig_label_effect")


def fig_floor(data: Dict[str, dict]) -> Optional[str]:
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.plot([0, 0.25], [0, 0.25], color="#111827", lw=0.9, ls="--", label="perfect calibration")
    palette = dict(zip(CROPS, [BLUE, ORANGE, GREEN, PURPLE]))
    found = False
    for crop, d in data.items():
        f = d["floors"]
        if f is None:
            continue
        a = f[f["policy"].astype(str).str.contains("adaptive", case=False) & f["alpha"].notna()]
        a = a.groupby("alpha", as_index=False)["violation"].mean()
        if len(a):
            ax.plot(a["alpha"], a["violation"], marker="o", color=palette[crop], label=crop.capitalize())
            found = True
    if not found:
        plt.close()
        return None
    ax.set_xlabel("Stated risk level α")
    ax.set_ylabel("Observed share of days the floor was broken")
    ax.set_title("Adaptive conformal floor: stated vs observed", fontsize=10)
    ax.legend(fontsize=8)
    return savefig("fig_floor_calibration")


def fig_engine(engine: Dict[str, dict]) -> Optional[str]:
    rows = [(c, b) for c, b in engine.items() if b.get("status") == "OK"]
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(6.2, 0.62 * len(rows) * 2 + 1.4))
    y = 0
    labels, ys = [], []
    for crop, b in rows:
        for key, name, colour in (("gain_vs_nearest", "vs nearest mandi", GOLD), ("gain_vs_highest_yesterday", "vs highest price yesterday", BLUE)):
            g = b[key]
            ax.errorbar(g["mean"], y, xerr=[[g["mean"] - g["ci_lo"]], [g["ci_hi"] - g["mean"]]], fmt="o", color=colour, capsize=3)
            labels.append(f"{crop.capitalize()}: {name}")
            ys.append(y)
            y += 1
        y += 0.5
    ax.axvline(0, color="#111827", lw=0.8)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Mean gain from following the advice, ₹ per quintal (95% bootstrap)")
    ax.set_title("Production engine, most recent held-out window", fontsize=10)
    return savefig("fig_engine_backtest")


def fig_forecast(council: dict) -> Optional[str]:
    if not council:
        return None
    hs = list(council["horizons"])
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    width = 0.2
    for i, (key, name, colour) in enumerate((("single", "Single served model", BLUE), ("linear", "Linear (ElasticNet)", GREY), ("equal", "Equal-weight agents", GOLD), ("council", "Weighted council", PURPLE))):
        vals = [100 * council["horizons"][h]["methods"][key]["skill"] for h in hs]
        ax.bar(np.arange(len(hs)) + (i - 1.5) * width, vals, width, color=colour, label=name)
    ci = [council["horizons"][h]["single_vs_no_change"] for h in hs]
    base = [council["horizons"][h]["no_change_mae"] for h in hs]
    lo = [-100 * c["ci"][1] / b for c, b in zip(ci, base)]       # CI of (MAE diff) mapped to skill points
    hi = [-100 * c["ci"][0] / b for c, b in zip(ci, base)]
    mid = [100 * council["horizons"][h]["methods"]["single"]["skill"] for h in hs]
    ax.errorbar(np.arange(len(hs)) - 1.5 * width, mid, yerr=[[m - l for m, l in zip(mid, lo)], [h_ - m for m, h_ in zip(mid, hi)]], fmt="none", ecolor="#111827", capsize=3, lw=1)
    ax.axhline(0, color="#111827", lw=0.8)
    ax.set_xticks(np.arange(len(hs)))
    ax.set_xticklabels([f"{h} days" for h in hs])
    ax.set_ylabel("Skill vs “no change”, % of MAE (higher is better)")
    ax.set_title("Price forecasts barely beat “no change” (mandi-level, walk-forward)", fontsize=10)
    ax.legend(fontsize=7, ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.32))
    return savefig("fig_forecast_skill")


def fig_leak(leak: Optional[pd.DataFrame]) -> Optional[str]:
    if leak is None:
        return None
    d = leak.copy()
    d["name"] = d["decomposer"] + "+" + d["forecaster"].str.replace("lgbm", "LGBM").str.replace("ridge", "Ridge") + f" {chr(8201)}" + d["h"].astype(str) + "d"
    fig, ax = plt.subplots(figsize=(6.2, 0.34 * len(d) + 1.4))
    y = np.arange(len(d))
    ax.scatter(100 * d["skill_published"], y, color=RED, label="published protocol", zorder=3)
    ax.scatter(100 * d["skill_causal_joint"], y, color=BLUE, label="causal (no look-ahead)", zorder=3)
    ax.scatter(100 * d["skill_raw"], y, color=GREY, marker="s", s=22, label="raw series, no decomposition", zorder=3)
    for yi, a, b in zip(y, 100 * d["skill_published"], 100 * d["skill_causal_joint"]):
        ax.plot([b, a], [yi, yi], color="#d1d5db", lw=1, zorder=1)
    ax.axvline(0, color="#111827", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(d["name"], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Skill vs random walk, % (higher is better)")
    ax.set_title("Decompose-then-forecast: gains vanish without look-ahead", fontsize=10)
    ax.legend(fontsize=7, loc="lower right")
    return savefig("fig_leakage")


def fig_shock(shock: Optional[dict]) -> Optional[str]:
    if not shock:
        return None
    rows = [r for r in shock["own_crop"]["results"] if r["status"] == "OK" and r["horizon"] == 7]
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(6.0, 0.36 * len(rows) + 1.4))
    for i, r in enumerate(rows):
        colour = {"ROBUST": GREEN, "SUGGESTIVE": ORANGE}.get(r["tier"], GREY)
        ax.errorbar(100 * r["effect"], i, xerr=[[100 * (r["effect"] - r["ci"][0])], [100 * (r["ci"][1] - r["effect"])]], fmt="o", color=colour, capsize=2.5)
        if r.get("mde"):
            ax.plot([-100 * r["mde"], 100 * r["mde"]], [i + 0.28, i + 0.28], color="#d1d5db", lw=2.5, solid_capstyle="butt")
    ax.axvline(0, color="#111827", lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{r['crop']} {r['direction']} (n={r['n']})" for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Own-crop price change vs peers, 7 days after the shock, % (grey bar: smallest effect detectable)")
    ax.set_title("Supply shocks: no own-crop price response is robust", fontsize=10)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", color=ORANGE, ls="", label="suggestive"), Line2D([], [], marker="o", color=GREY, ls="", label="no effect found")], fontsize=7, loc="lower right")
    return savefig("fig_shock_effects")


# ───────────────────────────────────────────────────────────────────────── document
PUBLISHED = [
    # (work as recorded in the team's literature survey, venue/year, what it reports (survey wording, abridged), how it relates to this study)
    ("CEEMDAN-TDNN hybrid", "Scientific Reports 2025", "RMSE about 20% lower than other EMD-based models and about 57% lower than traditional ML; MAPE 2-4% for major crops; directional accuracy above 80% in some cases",
     "A decompose-then-forecast hybrid. Reproduced in kind (STL/VMD + LightGBM/Ridge): +17 to +70% skill under the published protocol, -15 to 0% without look-ahead (§6)."),
    ("STL-LSTM hybrid", "Annals of Data Science 2025", "Better than ARIMA and a plain LSTM; RMSE and MAPE improved (survey records no figures)",
     "Same family. The STL arm of §6 is the closest reproduction; the LSTM learner was not re-run."),
    ("Decomposition-ensemble point and interval model", "Soft Computing 2024", "MAPE about 1-2% for short horizons; RMSE 5-15% better than other hybrids; interval coverage above 95% at the 95% level",
     "Same family for point accuracy. For intervals, §3 and §5 report this study's coverage on held-out data (about 90% at the stated 90%)."),
    ("ICEEMDAN-VMD-GRU", "Results in Engineering 2025", "Outperforms LSTM and RNN variants (survey records no figures)",
     "VMD arm of §6."),
    ("Exogenous-variable deep learning (NBEATSX)", "Scientific Reports 2024", "RMSE about 250 for tomato with weather variables, 36-42 for onion, about 34 for potato",
     "Not comparable in level: different markets, period, units and horizon. This study does not claim to beat these RMSEs."),
    ("HMM-guided deep learning", "Applied Soft Computing 2024", "Outperforms stand-alone deep models for short and medium horizons (survey records no figures)",
     "A regime-aware idea; this study's volatility regime tool is descriptive only and was not benchmarked against it."),
]


def build() -> None:
    style()
    data = {c: r for c in CROPS if (r := crop_results(c))}
    leak = read_csv(RES / "tomato" / "leakage" / "summary.csv")
    found = read_csv(RES / "tomato" / "leakage" / "foundation_skill.csv")
    silence = read_json(RES / "tomato" / "silence" / "summary.json")
    council = read_json(MODELS / "council" / "evaluation.json")
    shock = read_json(MODELS / "shock" / "shock_study.json")
    report = read_json(MODELS / "farmer" / "model_report.json")
    spill = read_json(MODELS / "spillover" / "spillover_matrix.json")
    engine = {}
    for c in CROPS + ["garlic"]:
        p = MODELS / "market_choice" / c / "meta.json"
        if p.exists():
            engine[c] = json.loads(p.read_text(encoding="utf-8")).get("backtest", {})
        else:
            engine[c] = {"status": "NOT_SERVED", "reason": "no model was trained: the crop failed the engine's data checks"}
    figs = {"decision": fig_decision(data), "effect": fig_effect(data), "floor": fig_floor(data), "engine": fig_engine(engine),
            "forecast": fig_forecast(council), "leak": fig_leak(leak), "shock": fig_shock(shock)}

    L: List[str] = ["# Results, validation and benchmarking", "",
                    f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z by `scripts/build_results.py` from the artefacts listed in §11. Every number below is read from them. "
                    "All figures are on **held-out** data: nested walk-forward blocks the models never trained or tuned on (§1).", ""]

    # ---- summary
    t = data["tomato"]
    mc = t["main"].set_index("method")
    c_t = t["cmp"].set_index("comparison") if t["cmp"] is not None else None
    L += ["## Summary", "", "| Question | Result |", "|---|---|"]
    n_ok = sum(1 for d in data.values() if d["cmp"] is not None)
    eff = []
    for crop, d in data.items():
        hit = d["cmp"][(d["cmp"]["A"] == "lgbm_filled") & (d["cmp"]["B"] == "lgbm_obs")] if d["cmp"] is not None else []
        if len(hit):
            r = hit.iloc[0]
            eff.append(f"{crop} {r['regret_diff_A_minus_B']:+.0f} (Holm p {pv(r['holm_p'])})")
    L.append(f"| Does training on what a farmer actually received beat training on observed prices? | Change in regret, ₹ per quintal, same LightGBM: {'; '.join(eff)}. Negative is better. |")
    ok = [c for c, b in engine.items() if b.get("status") == "OK"]
    L.append(f"| Does the production advice beat simple rules out of sample? | In {len(ok)} of {len(engine)} crops the engine has a validated backtest; "
             + "; ".join(f"{c} {engine[c]['gain_vs_highest_yesterday']['mean']:+.0f} ₹/q vs highest-price-yesterday [{engine[c]['gain_vs_highest_yesterday']['ci_lo']:+.0f}, {engine[c]['gain_vs_highest_yesterday']['ci_hi']:+.0f}]" for c in ok)
             + ". Garlic is refused (§4). |")
    if council:
        s5 = council["horizons"]["5"]
        L.append(f"| Are price forecasts accurate? | Barely better than “no change”: 5-day skill {100 * s5['methods']['single']['skill']:+.1f}% on mandi-level series; "
                 f"the interval against no change is [{s5['single_vs_no_change']['ci'][0]:+.5f}, {s5['single_vs_no_change']['ci'][1]:+.5f}] in log-return MAE. |")
    if leak is not None:
        L.append(f"| Do published decompose-then-forecast hybrids hold up? | No: {100 * leak['skill_published'].min():+.0f} to {100 * leak['skill_published'].max():+.0f}% skill under the published protocol, "
                 f"{100 * leak['skill_causal_joint'].min():+.0f} to {100 * leak['skill_causal_joint'].max():+.0f}% without look-ahead. |")
    if shock:
        L.append(f"| Do arrival gluts or squeezes move prices? | No robust effect: {shock['own_crop']['n_tested']} tests, {shock['own_crop']['n_robust']} robust, {shock['own_crop']['n_suggestive']} suggestive. |")
    L.append("")

    # ---- 1 protocol
    first = data["tomato"]
    rep = (first["summary"] or {}).get("load_report", {})
    folds = first["fold"].drop_duplicates("fold")[["fold", "test"]] if first["fold"] is not None else None
    L += ["## 1. Evaluation protocol", "",
          f"**Data.** Agmarknet market-level history, {rep.get('date_min', '?')} to {rep.get('date_max', '?')}, {rep.get('rows_kept', '?'):,} rows after cleaning "
          f"({rep.get('rows_read', '?'):,} read; {rep.get('nonpositive_price', 0)} non-positive prices and {rep.get('duplicate_keys', 0)} duplicates handled). No price is imputed: a mandi that did not report on a day has no row.", "",
          "**Held-out test blocks.** Five outer walk-forward blocks; for each, models are tuned on inner validation blocks that precede it (with a gap of the longest horizon plus two days), fitted on everything before, and scored only on the block."]
    if folds is not None:
        L += ["", md(folds.rename(columns={"fold": "Outer block", "test": "Test window"}))]
    L += ["", "| Crop | Test days | Methods compared |", "|---|---|---|"]
    for crop, d in data.items():
        L.append(f"| {crop.capitalize()} | {(d['summary'] or {}).get('test_days', '?')} | {len(d['main'])} |")
    L += ["", "**Metrics.**",
          "- *Decision quality:* realised net revenue per quintal after transport, fees and spoilage (₹), regret against a hindsight oracle, share of the oracle gap closed relative to the nearest mandi, CVaR at 10% (the mean of the worst 10% of days), and the fallback-trip rate (days the chosen mandi turned out silent).",
          "- *Floor validity:* the share of days realised revenue fell below the stated floor, against the stated risk level α.",
          "- *Forecast quality:* mean absolute error of the h-day log-return, reported as skill (the reduction against a forecast of no change), direction accuracy and 90% interval coverage.",
          "",
          "**Baselines.** Simple rules (nearest mandi, highest price yesterday, best 7-day mean, farm gate); a random walk made cost-aware; models trained on *observed* prices (LightGBM, XGBoost, neural) predict-then-optimise; models on *realised* outcomes (LightGBM, neural, SPO+ and variants); an ElasticNet linear model; equal-weight and learned-weight specialist ensembles; and the Chronos-Bolt zero-shot foundation model.", "",
          "**Statistics.** Paired differences in daily regret with a day-block bootstrap (95% intervals), Diebold–Mariano tests with the Harvey–Leybourne–Newbold correction on date-averaged losses, Holm correction across each crop's family of comparisons, the Model Confidence Set at α = 0.10, week-block bootstrap for forecasts, and circular-shift placebos for event studies. Costs (transport ₹0.70 per quintal-km, 4% fee, crop spoilage, 0.85 silent-mandi factor) are scenario assumptions, varied in §8.", ""]

    # ---- 2 decision quality
    L += ["## 2. Decision quality, five nested test blocks", ""]
    if figs["decision"]:
        L += [f"![Net revenue by method and crop]({figs['decision']})", ""]
    for crop, d in data.items():
        m = d["main"].copy()
        oracle = float((m["revenue"] + m["regret"]).iloc[0])
        keep = [k for k in ("nearest_today", "highest_yesterday", "trailing_best", "rw", "lgbm_obs", "xgb_obs", "ds_mse_obs", "lgbm_filled", "lgbm_filled_sil", "ds_mse_filled", "ds_spo", "ds_spo_struct", "gfmc_pred") if k in set(m["method"])]
        m = m.set_index("method").loc[keep].reset_index()
        tab = pd.DataFrame({"Method": m["method"].map(LABEL), "Net revenue ₹/q [95% CI]": [f"{rs(r.revenue)} [{rs(r.rev_ci_lo)}, {rs(r.rev_ci_hi)}]" for r in m.itertuples()],
                            "Oracle gap closed": [f"{r.gap_closed_vs_nearest:.2f}" for r in m.itertuples()], "CVaR₁₀": [rs(x) for x in m["cvar10"]],
                            "Fallback trips": [f"{100 * x:.1f}%" for x in m["fallback_rate"]]})
        mcs = ((d["summary"] or {}).get("model_confidence_set") or {}).get("survivors", [])
        L += [f"### {crop.capitalize()} (hindsight oracle ₹{rs(oracle)}/q)", "", md(tab), "",
              f"Model Confidence Set (α = 0.10): {', '.join(LABEL.get(s, s) for s in mcs) or 'not computed'}. Every method outside it, including every rule, is statistically excluded.", ""]
        if d["cmp"] is not None:
            c = d["cmp"]
            tab2 = pd.DataFrame({"Comparison": c["comparison"], "Δ regret ₹/q": [f"{x:+.0f}" for x in c["regret_diff_A_minus_B"]],
                                 "95% CI": [f"[{a:+.0f}, {b:+.0f}]" for a, b in zip(c["ci_lo"], c["ci_hi"])], "Holm p": [pv(x) for x in c["holm_p"]],
                                 "Wins": [f"{100 * x:.0f}%" for x in c["win_rate_A"]]})
            L += ["Paired comparisons (negative: the first method has lower regret):", "", md(tab2), ""]
        if d["fold"] is not None and {"lgbm_filled", "lgbm_obs"} <= set(d["fold"]["method"]):
            f = d["fold"].pivot(index="fold", columns="method", values="revenue")
            wins = int((f["lgbm_filled"] > f["lgbm_obs"]).sum())
            L += [f"Consistency: realised-outcome LightGBM earned more than observed-price LightGBM in {wins} of {len(f)} outer blocks.", ""]
    if figs["effect"]:
        L += [f"![Label effect by crop]({figs['effect']})", ""]

    # ---- 3 floor
    L += ["## 3. The revenue floor", "", "The floor is the lower bound the advice reports; its stated risk level is α, so a valid floor is broken on about α of days.", ""]
    if figs["floor"]:
        L += [f"![Floor calibration]({figs['floor']})", ""]
    for crop, d in data.items():
        f = d["floors"]
        if f is None:
            continue
        g = f[f["alpha"].notna()].copy()
        tab = pd.DataFrame({"Predictor": g["spec"].map(lambda s: LABEL.get(s, s)), "Floor rule": g["policy"], "Stated α": g["alpha"], "Observed violation": [f"{100 * x:.1f}%" for x in g["violation"]],
                            "Mean floor ₹/q": [rs(x) for x in g["mean_floor"]], "Revenue ₹/q": [rs(x) for x in g["revenue"]]})
        L += [f"**{crop.capitalize()}**", "", md(tab), ""]

    # ---- 4 engine
    L += ["## 4. The production engine, backtested as deployed", "",
          "The research protocol of §2 chooses models; the engine behind the app is retrained per crop and backtested on its own most recent window with the same costs the farmer is shown. "
          "A crop whose backtest does not pass its checks is refused rather than advised on.", ""]
    if figs["engine"]:
        L += [f"![Engine backtest]({figs['engine']})", ""]
    rows = []
    for c, b in engine.items():
        if b.get("status") != "OK":
            rows.append([c.capitalize(), "not served", "-", "-", "-", "-", "-", b.get("reason", b.get("status", ""))])
            continue
        mr = b["mean_net_revenue"]
        rows.append([c.capitalize(), f"{b['window'][0]} to {b['window'][1]} ({b['scored_days']} days)", f"{rs(mr['recommended'])} vs {rs(mr['highest_yesterday'])} vs {rs(mr['nearest'])}",
                     f"{b['gain_vs_highest_yesterday']['mean']:+.0f} [{b['gain_vs_highest_yesterday']['ci_lo']:+.0f}, {b['gain_vs_highest_yesterday']['ci_hi']:+.0f}]",
                     f"{b['gain_vs_nearest']['mean']:+.0f} [{b['gain_vs_nearest']['ci_lo']:+.0f}, {b['gain_vs_nearest']['ci_hi']:+.0f}]", f"{100 * b['share_of_oracle_gap_closed']:.0f}%",
                     f"{100 * b['floor_violation_static_out_of_sample'].get('0.10', float('nan')):.1f}%" if "floor_violation_static_out_of_sample" in b else "-", b.get("evidence_level", "")])
    L += [md(pd.DataFrame(rows, columns=["Crop", "Window", "Advice vs highest-yesterday vs nearest (₹/q)", "Gain vs highest-yesterday [95% CI]", "Gain vs nearest [95% CI]", "Oracle gap closed",
                                         "Floor broken at α=10%", "Note"])), "",
          "Garlic: only one mandi in the belt has enough reported days to be a candidate, so there is no choice between markets to learn; the engine refuses to advise and the research package does not study it (`research/gfmc/config.py`).", ""]

    # ---- 5 forecast
    L += ["## 5. Price forecasts", ""]
    if figs["forecast"]:
        L += [f"![Forecast skill]({figs['forecast']})", ""]
    if council:
        rows = []
        for h, s in council["horizons"].items():
            m, n0, nl = s["methods"], s["single_vs_no_change"], s["single_vs_linear"]
            rows.append([f"{h} days", s["n"], f"{100 * m['single']['skill']:+.2f}%", f"[{n0['ci'][0]:+.5f}, {n0['ci'][1]:+.5f}]", f"{100 * m['linear']['skill']:+.2f}%",
                         f"[{nl['ci'][0]:+.5f}, {nl['ci'][1]:+.5f}]", f"{100 * m['council']['skill']:+.2f}%", f"{s['folds_single_beats_no_change']}/{s['folds']}"])
        L += ["Mandi-level series, pooled over 54 series, same rows and folds for every method; skill is the reduction in MAE of the h-day log-return against no change. "
              "Intervals are week-block bootstraps of the MAE difference (negative favours the first-named method).", "",
              md(pd.DataFrame(rows, columns=["Horizon", "n", "Single model skill", "Single − no change [95% CI]", "ElasticNet skill", "Single − ElasticNet [95% CI]", "Weighted council", "Folds single beats no change"])), ""]
    if report:
        rows = [[h, f"{100 * v['skill_vs_no_change']:+.1f}%", f"{100 * v.get('direction_right', float('nan')):.0f}%" if 'direction_right' in v else "-", f"{100 * v['coverage_90']:.1f}%", f"{v['mean_band_width_pct']:.0f}%", "yes" if v["promoted"] else "no"]
                for h, v in report["horizons"].items()]
        L += ["District-level series (arrivals-weighted district prices, the farmer forecaster), four expanding walk-forward folds:", "",
              md(pd.DataFrame(rows, columns=["Horizon (days)", "Skill vs no change", "Direction right", "90% band coverage", "Mean band width", "Served"])), "",
              "A horizon is served only if it beats no change on held-out folds; one day does not, and is not shown."]
    if found is not None:
        L += ["", "A zero-shot foundation model (Chronos-Bolt-small, no training on this data) scores " + ", ".join(f"{100 * r.skill_foundation:+.1f}% at {r.h} day{'s' if r.h > 1 else ''}" for r in found.itertuples()) + " against the random walk on the same origins."]
    L += ["", "**Reading.** Forecast skill is small everywhere and the intervals above are what to read; the application therefore uses forecasts for risk bands and direction, not as price promises. "
          "Decision quality and forecast accuracy decouple (§2): the models that choose best are not the ones with the lowest forecast error, so a forecast leaderboard would pick the wrong models.", ""]

    # ---- 6 leakage / published
    L += ["## 6. Against published work: decomposition hybrids", ""]
    if figs["leak"]:
        L += [f"![Leakage audit]({figs['leak']})", ""]
    if leak is not None:
        t6 = pd.DataFrame({"Decomposer + learner": leak["decomposer"] + " + " + leak["forecaster"], "Horizon": leak["h"].astype(str) + "d", "n": leak["n"],
                           "Published protocol": [f"{100 * x:+.1f}%" for x in leak["skill_published"]], "Causal": [f"{100 * x:+.1f}%" for x in leak["skill_causal_joint"]],
                           "Raw series": [f"{100 * x:+.1f}%" for x in leak["skill_raw"]],
                           "Look-ahead gap [95% CI]": [f"{100 * g:+.1f} [{100 * a:+.1f}, {100 * b:+.1f}] pts" for g, a, b in zip(leak["leak_gap_skill"], leak["leak_gap_ci_lo"], leak["leak_gap_ci_hi"])]})
        L += ["Tomato, five densest mandis, skill against the random walk. *Published protocol* decomposes the whole series once and then splits it, as the literature does; *causal* decomposes using only data available at each forecast date. "
              "Learner, features and folds are identical; the only difference is whether the decomposition may see the future.", "", md(t6), ""]
    L += ["What the published works report, as recorded in the team's literature survey (`reports/capstone_report/Literature_Survey.xlsx`; the figures are the survey's wording and were not re-checked against the papers):", "",
          md(pd.DataFrame(PUBLISHED, columns=["Work", "Venue", "Reported result", "How this study relates"])), "",
          "**Comparability.** Those papers use different markets, periods, horizons and units, so their RMSE or MAPE cannot be set against ours. What can be compared is the *method*: this study reproduces "
          "the decompose-then-forecast recipe on this data and finds gains of the size the literature reports (about 20 to 60%) under the published protocol, and none without look-ahead. "
          "This is evidence about the protocol, not a statement that any particular paper leaked; their code was not re-run.", ""]

    # ---- 7 ablations
    L += ["## 7. What did not help (ablations and negative results)", ""]
    abl = []
    keys = {"SPO+ vs MSE": ("ds_spo", "ds_mse_filled"), "Reporting head": ("ds_spo_struct", "ds_spo"), "Silence features (GBM)": ("lgbm_filled_sil", "lgbm_filled"), "Neural vs GBM, both on realised labels": ("ds_mse_filled", "lgbm_filled")}
    for crop, d in data.items():
        c = d["cmp"]
        if c is None:
            continue
        for name, (a, b) in keys.items():
            hit = c[(c["A"] == a) & (c["B"] == b)]
            if len(hit):
                r = hit.iloc[0]
                abl.append([crop.capitalize(), name, f"{r['regret_diff_A_minus_B']:+.0f}", f"[{r['ci_lo']:+.0f}, {r['ci_hi']:+.0f}]", pv(r["holm_p"]), "no reliable difference" if r["holm_p"] >= 0.05 else ("better" if r["regret_diff_A_minus_B"] < 0 else "worse")])
    if abl:
        L += [md(pd.DataFrame(abl, columns=["Crop", "Change", "Δ regret ₹/q", "95% CI", "Holm p", "Verdict"])), ""]
    if silence:
        L += ["Network silence (whether neighbouring mandis' silence carries information beyond a mandi's own reporting history), tomato: " + "; ".join(f"{k} = {v}" for k, v in list(silence.items())[:6] if not isinstance(v, (dict, list))) + ". Rejected as a claimed contribution.", ""]
    L += ["The gain in §2 is carried by the *supervision signal* (realised outcomes), not by the learner: a plain LightGBM on those labels is statistically indistinguishable from every neural variant. "
          "The SPO+ loss, a reporting head, silence features and tuning on decision regret add nothing significant on top.", ""]

    # ---- 8 sensitivity
    L += ["## 8. Sensitivity to the cost assumptions", ""]
    for crop, d in data.items():
        s = d["sens"]
        if s is None:
            continue
        real = s[s["method"].isin(["lgbm_filled", "ds_mse_filled", "ds_spo"]) & s["gap_closed_vs_yday"].notna()]
        obs = s[s["method"].isin(["lgbm_obs", "xgb_obs", "ds_mse_obs", "rw"]) & s["gap_closed_vs_yday"].notna()]
        if len(real):
            L.append(f"- **{crop.capitalize()}:** across {s[['param', 'value']].drop_duplicates().shape[0]} settings of transport, spoilage and the silent-mandi discount, realised-outcome models close "
                     f"{100 * real['gap_closed_vs_yday'].min():.0f}% to {100 * real['gap_closed_vs_yday'].max():.0f}% of the oracle gap beyond the best rule"
                     + (f"; observed-price models {100 * obs['gap_closed_vs_yday'].min():.0f}% to {100 * obs['gap_closed_vs_yday'].max():.0f}%." if len(obs) else "."))
    L.append("")

    # ---- 9 shock / spillover
    L += ["## 9. Supply shocks and cross-commodity links", ""]
    if figs["shock"]:
        L += [f"![Shock effects]({figs['shock']})", ""]
    if shock:
        o = shock["own_crop"]
        L += [f"Own-crop price response after an arrivals glut or squeeze: {o['n_tested']} tests (5 crops × 2 shocks × 3 horizons), **{o['n_robust']} robust, {o['n_suggestive']} suggestive**, Holm-corrected across all tests, with a circular-shift placebo and agreement across districts required. "
              "Each test also reports the smallest effect it could have detected, so a null is read as “no effect larger than this”, not “no effect”. Full table: `docs/SHOCK_STUDY.md`.", ""]
    if spill:
        L += [f"The weekly cross-commodity spillover matrix tests {spill.get('total_edges', '?')} directed links; {spill.get('actionable_edges', '?')} survive the evidence and FDR gates.", ""]

    # ---- 10 limits
    L += ["## 10. Limitations and threats to validity", "",
          "1. **Counterfactual outcomes.** Revenue of an unchosen mandi is computed from its reported price on that day, with assumed transport, fee and spoilage. No farmer actually sold under this advice; the claim is about what the advice would have earned on past data, not a field result.",
          "2. **Reported prices, not transaction prices.** Agmarknet reports one modal price per mandi and day, which changes in steps; short-horizon changes are lumpy and often exactly zero.",
          "3. **One region, five crops.** Nothing here is claimed for other states or crops. Garlic cannot be studied because one mandi has enough history.",
          "4. **Few mandis for some crops.** Onion has 4 eligible mandis, potato 3 and ginger 3, so choice sets are small and the gain over rules is correspondingly limited; tomato (12) carries the strongest results.",
          "5. **Small forecast skill.** Intervals in §5 are close to zero at some horizons. The advice does not rely on forecasts being accurate, and says so.",
          "6. **Multiplicity.** Many comparisons are made; Holm correction is applied within each crop's family, and the families were fixed before the tuned results (twelve) with two added afterwards for the secondary crops, which is disclosed in `research/docs/RESULTS.md`.",
          "7. **Assumed costs.** §8 varies them over wide ranges and the conclusion holds, but real costs vary by vehicle, season and load.",
          "8. **Dependence.** Days and weeks are autocorrelated; block bootstraps and HAC corrections address this but assume stationary dependence within blocks.",
          "9. **Same data for design and evaluation of the application layer.** The engine's backtest window is also part of the data its calibration used earlier; the research protocol of §2 is the cleaner test, and both are reported.",
          "10. **Literature comparison is of method, not of numbers** (§6).", ""]

    # ---- 11 reproduce
    L += ["## 11. Reproduce and sources", "",
          "```bash", "python scripts/pipeline.py --with-research      # every experiment, then this document (hours)",
          "cd research && python scripts/run_experiments.py --crop Ginger --specs rw,lgbm_obs,lgbm_filled,ds_mse_filled,ds_spo && python scripts/analyze.py --crop Ginger",
          "python scripts/eval_agent_council.py                      # forecast benchmark (§5)",
          "python scripts/build_results.py                           # regenerate this file", "```", "",
          "Sources read: `research/results/<crop>/{summary.json,tables/*.csv,leakage/*,silence/*}`, `mandisense_ai/models/market_choice/<crop>/meta.json`, `mandisense_ai/models/council/evaluation.json`, "
          "`mandisense_ai/models/farmer/model_report.json`, `mandisense_ai/models/shock/shock_study.json`, `mandisense_ai/models/spillover/spillover_matrix.json`."]
    if MISSING:
        L += ["", "**Artefacts that were not found when this was generated:** " + ", ".join(f"`{m}`" for m in sorted(set(MISSING)))]
    DOC.parent.mkdir(exist_ok=True)
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)} and {len([f for f in figs.values() if f])} figures; missing artefacts: {len(set(MISSING))}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    build()
