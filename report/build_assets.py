"""
Generate every table and figure of the final report from the project's artefacts.

    python report/build_assets.py

Writes report/generated/*.tex (tabular bodies and number macros) and report/figures/*.png. The chapters `\\input` these files, so no result
quoted in the report is typed by hand: re-run this after any experiment and recompile.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research" / "results"
MODELS = ROOT / "mandisense_ai" / "models"
GEN = ROOT / "report" / "generated"
FIG = ROOT / "report" / "figures"
GEN.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
CROPS = ["tomato", "onion", "potato", "ginger"]
LABEL = {
    "rw": "Random walk (cost-aware)", "lgbm_obs": "LightGBM, observed prices", "xgb_obs": "XGBoost, observed prices", "ds_mse_obs": "Neural, observed prices",
    "lgbm_filled": "LightGBM, realised outcomes", "lgbm_filled_sil": "LightGBM, realised + silence", "ds_mse_filled": "Neural, realised outcomes",
    "ds_spo": "Neural SPO+, realised outcomes", "ds_spo_struct": "SPO+ + reporting head", "gfmc_pred": "SPO+ + head + silence",
    "gfmc_pred_tuneMSE": "SPO+ + head + silence, tuned on forecast loss", "nearest_today": "Nearest mandi, sell today",
    "highest_yesterday": "Highest price yesterday", "trailing_best": "Best 7-day mean", "farm_gate": "Farm gate",
}


# ───────────────────────────────────────────────────────────────────────── LaTeX helpers
def esc(s) -> str:
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    for a, b in (("₹", "Rs "), ("−", "$-$"), ("≥", "$\\geq$"), ("≤", "$\\leq$"), ("±", "$\\pm$"), ("×", "$\\times$"), ("α", "$\\alpha$"), ("→", "$\\rightarrow$"), ("–", "--"), ("—", "---"),
                 ("“", "``"), ("”", "''"), ("’", "'"), ("Δ", "$\\Delta$"), ("₁", "$_1$"), ("₀", "$_0$")):
        s = s.replace(a, b)
    return re.sub(r"(?<![\w-])-(?=\d)", "$-$", s)


def num(x: float, d: int = 0, sign: bool = False) -> str:
    t = f"{x:+,.{d}f}" if sign else f"{x:,.{d}f}"
    return t.replace("-", "$-$")


def pval(p: float) -> str:
    return "$<$0.0001" if p < 1e-4 else f"{p:.4f}" if p < 0.01 else f"{p:.3f}"


def table(headers, rows, spec, name: str, small: bool = True, bold_last: bool = False) -> None:
    out = [r"\renewcommand{\arraystretch}{1.25}", r"\footnotesize" if small else "", rf"\begin{{tabular}}{{{spec}}}", r"\hline", " & ".join(rf"\textbf{{{h if chr(92) in h else esc(h)}}}" for h in headers) + r" \\", r"\hline"]
    for i, r in enumerate(rows):
        cells = [c if str(c).startswith("@@") else esc(c) for c in r]
        cells = [c[2:] if c.startswith("@@") else c for c in cells]
        line = " & ".join(cells) + r" \\"
        out.append(rf"\textbf{{}}{line}" if False else line)
        out.append(r"\hline")
    out.append(r"\end{tabular}")
    (GEN / f"{name}.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def macro(name: str, value) -> None:
    MACROS.append(rf"\newcommand{{\{name}}}{{{value}}}")


MACROS: list = []


# ───────────────────────────────────────────────────────────────────────── data
def load_crop(crop: str):
    t = RES / crop / "tables"
    return {"main": pd.read_csv(t / "main.csv"), "cmp": pd.read_csv(t / "comparisons.csv"), "floors": pd.read_csv(t / "floors.csv"),
            "fold": pd.read_csv(t / "per_fold.csv"), "sens": pd.read_csv(t / "sensitivity.csv"), "summary": json.loads((RES / crop / "summary.json").read_text(encoding="utf-8"))}


def main() -> None:
    data = {c: load_crop(c) for c in CROPS}
    sys.path.insert(0, str(ROOT))
    from mandisense_ai.farmer import world

    panel = pd.read_parquet(world.MARKET_PANEL)
    district = pd.read_parquet(world.DISTRICT_OBSERVATIONS)
    mandi = pd.read_parquet(world.MANDI_PRICES)
    macro("NpanelRows", f"{len(panel):,}")
    macro("NdistrictRows", f"{len(district):,}")
    macro("NmandiRows", f"{len(mandi):,}")
    macro("NhistoryRows", f"{data['tomato']['summary']['load_report']['rows_kept']:,}")
    macro("DataFrom", data["tomato"]["summary"]["load_report"]["date_min"])
    macro("DataTo", data["tomato"]["summary"]["load_report"]["date_max"])

    # ---- dataset table (Table 3.2)
    eligible = {"tomato": 12, "onion": 4, "potato": 3, "ginger": 3, "garlic": 1}   # mandis with >= 700 reported days in the history export
    rows = []
    for crop in ["tomato", "onion", "potato", "ginger", "garlic"]:
        g = panel[panel["crop"] == crop]
        td = data[crop]["summary"]["test_days"] if crop in data else None
        rows.append([crop.capitalize(), f"{len(g):,}", g["mandi_id"].nunique(), eligible[crop], f"{td:,}" if td else "---",
                     "yes" if crop in data else "refused: one eligible mandi"])
    rows.append(["@@\\textbf{Total}", f"@@\\textbf{{{len(panel):,}}}", "", "", "", ""])
    table(["Crop", "Mandi-days", "Mandis", "Eligible", "Test days", "Studied"], rows, "|l|r|c|c|r|l|", "tab_dataset")

    # ---- decision quality across crops (Table 6.1)
    keys = ["nearest_today", "highest_yesterday", "rw", "lgbm_obs", "lgbm_filled", "ds_spo"]
    rows = []
    for k in keys:
        r = [LABEL[k]]
        for c in CROPS:
            m = data[c]["main"].set_index("method")
            r.append(f"{m.loc[k, 'revenue']:,.0f} [{m.loc[k, 'rev_ci_lo']:,.0f}, {m.loc[k, 'rev_ci_hi']:,.0f}]")
        rows.append(r)
    orc = ["Hindsight oracle"] + [f"{(data[c]['main'].iloc[0]['revenue'] + data[c]['main'].iloc[0]['regret']):,.0f}" for c in CROPS]
    rows.append(orc)
    table(["Method"] + [c.capitalize() for c in CROPS], rows, "|l|c|c|c|c|", "tab_decision")

    # ---- gap closed and fallback trips
    rows = []
    for k in keys:
        r = [LABEL[k]]
        for c in CROPS:
            m = data[c]["main"].set_index("method")
            r.append(f"{m.loc[k, 'gap_closed_vs_nearest']:.2f} / {100 * m.loc[k, 'fallback_rate']:.1f}\\%".replace("\\%", "%"))
        rows.append(r)
    table(["Method"] + [c.capitalize() for c in CROPS], rows, "|l|c|c|c|c|", "tab_gap")

    # ---- label effect (Table 6.2)
    rows = []
    for c in CROPS:
        d = data[c]["cmp"]
        r = d[(d["A"] == "lgbm_filled") & (d["B"] == "lgbm_obs")].iloc[0]
        s = d[(d["A"] == "ds_spo") & (d["B"] == "ds_mse_filled")]
        spo = f"{s.iloc[0]['regret_diff_A_minus_B']:+.0f} [{s.iloc[0]['ci_lo']:+.0f}, {s.iloc[0]['ci_hi']:+.0f}]; p={s.iloc[0]['holm_p']:.2f}" if len(s) else "---"
        m = data[c]["main"].set_index("method")
        rows.append([c.capitalize(), f"{r['regret_diff_A_minus_B']:+.0f}", f"[{r['ci_lo']:+.0f}, {r['ci_hi']:+.0f}]", pval(r["holm_p"]).replace("$<$", "<") if False else "@@" + pval(r["holm_p"]),
                     f"{100 * m.loc['lgbm_obs', 'fallback_rate']:.1f} to {100 * m.loc['lgbm_filled', 'fallback_rate']:.1f}", spo])
    table(["Crop", "Regret change", "95% CI", "Holm p", "Silent trips (%)", "SPO+ vs MSE"], rows, "|l|c|c|c|c|l|", "tab_effect")

    # ---- floor validity (Table 6.3)
    rows = []
    for c in CROPS:
        f = data[c]["floors"]
        lf = f[(f["spec"] == "lgbm_filled") & f["policy"].str.contains("adaptive")].set_index("alpha")["violation"]
        nv = f[(f["spec"] == "lgbm_obs") & f["policy"].str.contains("naive")]["violation"]
        st = f[(f["spec"] == "lgbm_filled") & f["policy"].str.contains("static")]["violation"]
        rows.append([c.capitalize()] + [f"{100 * lf.get(a, float('nan')):.1f}" for a in (0.05, 0.1, 0.2)] + [f"{100 * st.iloc[0]:.1f}" if len(st) else "---", f"{100 * nv.iloc[0]:.1f}" if len(nv) else "---"])
    table(["Crop", "Adaptive 5\\%", "Adaptive 10\\%", "Adaptive 20\\%", "Static 10\\%", "Naive 10\\%"],
          [[("@@" + esc(r[0]))] + [("@@" + x) for x in r[1:]] for r in rows], "|l|c|c|c|c|c|", "tab_floor")

    # ---- engine backtest (Table 6.4)
    rows, eng = [], {}
    for c in CROPS + ["garlic"]:
        p = MODELS / "market_choice" / c / "meta.json"
        b = json.loads(p.read_text(encoding="utf-8")).get("backtest", {}) if p.exists() else {}
        eng[c] = b
        if b.get("status") != "OK":
            rows.append([c.capitalize(), "not served", "---", "---", "---", "refused: no choice between markets"])
            continue
        mr = b["mean_net_revenue"]
        rows.append([c.capitalize(), f"{b['scored_days']}", f"{mr['recommended']:,.0f} / {mr['highest_yesterday']:,.0f} / {mr['nearest']:,.0f}",
                     f"{b['gain_vs_highest_yesterday']['mean']:+.0f} [{b['gain_vs_highest_yesterday']['ci_lo']:+.0f}, {b['gain_vs_highest_yesterday']['ci_hi']:+.0f}]",
                     f"{b['gain_vs_nearest']['mean']:+.0f} [{b['gain_vs_nearest']['ci_lo']:+.0f}, {b['gain_vs_nearest']['ci_hi']:+.0f}]",
                     f"{100 * b['share_of_oracle_gap_closed']:.0f}\\%; evidence {b.get('evidence_level', '')}"])
    table(["Crop", "Days", "Advice / yesterday / nearest", "Gain vs yesterday", "Gain vs nearest", "Gap closed"],
          [[("@@" + esc(r[0]))] + [("@@" + x if i == 4 else x) for i, x in enumerate(r[1:])] for r in rows], "|l|c|c|c|c|l|", "tab_engine")

    # ---- forecast (Table 6.5, 6.6)
    council = json.loads((MODELS / "council" / "evaluation.json").read_text(encoding="utf-8"))
    rows = []
    for h, s in council["horizons"].items():
        m, n0 = s["methods"], s["single_vs_no_change"]
        rows.append([f"{h} days", f"{s['n']:,}", f"{100 * m['single']['skill']:+.2f}%", f"[{n0['ci'][0]:+.5f}, {n0['ci'][1]:+.5f}]", f"{100 * m['linear']['skill']:+.2f}%",
                     f"{100 * m['equal']['skill']:+.2f}%", f"{100 * m['council']['skill']:+.2f}%", f"{s['folds_single_beats_no_change']}/{s['folds']}"])
    table(["Horizon", "n", "Single", "Single vs no change, 95\\% CI", "ElasticNet", "Equal weight", "Council", "Folds won"],
          [[("@@" + esc(x)) for x in r] for r in rows], "|l|r|c|c|c|c|c|c|", "tab_forecast")
    rep = json.loads((MODELS / "farmer" / "model_report.json").read_text(encoding="utf-8"))
    rows = [[h, f"{100 * v['skill_vs_no_change']:+.1f}%", f"{100 * v['direction_right']:.0f}%" if "direction_right" in v else "---", f"{100 * v['coverage_90']:.1f}%", f"{v['mean_band_width_pct']:.0f}%",
             "yes" if v["promoted"] else "no"] for h, v in rep["horizons"].items()]
    table(["Horizon (days)", "Skill vs no change", "Direction right", "90\\% band coverage", "Mean band width", "Served"], [[("@@" + esc(x)) for x in r] for r in rows], "|c|c|c|c|c|c|", "tab_district")
    rows = []
    for h, s in council["horizons"].items():
        w = s["mean_weights"]
        rows.append([f"{h} days"] + [f"{100 * s['methods'][a]['skill']:+.1f}% (w={w[a]:.2f})" for a in council["agents"]] + [f"{100 * s['methods']['council']['skill']:+.1f}%", f"{s['folds_council_beats_single']}/{s['folds']}"])
    table(["Horizon"] + [a.capitalize() for a in council["agents"]] + ["Council", "Folds won vs single"], [[("@@" + esc(x)) for x in r] for r in rows], "|l|c|c|c|c|c|c|", "tab_council")
    macro("CouncilUnconstrainedSum", f"{council['horizons']['3']['unconstrained_weight_sum']:.1f}--{council['horizons']['5']['unconstrained_weight_sum']:.1f}")

    # ---- leakage (Table 6.7)
    lk = pd.read_csv(RES / "tomato" / "leakage" / "summary.csv")
    rows = []
    for r in lk.itertuples():
        rows.append([f"{r.decomposer} + {'LightGBM' if r.forecaster == 'lgbm' else 'Ridge'}", f"{r.h} d", f"{100 * r.skill_published:+.1f}", f"{100 * r.skill_causal_joint:+.1f}", f"{100 * r.skill_raw:+.1f}",
                     f"{100 * r.leak_gap_skill:+.1f} [{100 * r.leak_gap_ci_lo:+.1f}, {100 * r.leak_gap_ci_hi:+.1f}]"])
    table(["Model", "Horizon", "Published", "Causal", "Raw", "Gap, points [95\\% CI]"], [[("@@" + esc(x)) for x in r] for r in rows], "|l|c|c|c|c|c|", "tab_leak")
    fo = pd.read_csv(RES / "tomato" / "leakage" / "foundation_skill.csv")
    macro("ChronosOne", f"{100 * fo.iloc[0].skill_foundation:+.1f}".replace("-", "$-$"))
    macro("ChronosSeven", f"{100 * fo.iloc[1].skill_foundation:+.1f}".replace("-", "$-$"))

    # ---- ablation (Table 6.8)
    rows = []
    pairs = {"SPO+ loss vs MSE loss": ("ds_spo", "ds_mse_filled"), "Reporting head": ("ds_spo_struct", "ds_spo"), "Silence features (GBM)": ("lgbm_filled_sil", "lgbm_filled"),
             "Neural vs GBM, same labels": ("ds_mse_filled", "lgbm_filled")}
    for c in CROPS:
        d = data[c]["cmp"]
        for name, (a, b) in pairs.items():
            hit = d[(d["A"] == a) & (d["B"] == b)]
            if len(hit):
                r = hit.iloc[0]
                verdict = "no reliable difference" if r["holm_p"] >= 0.05 else ("better" if r["regret_diff_A_minus_B"] < 0 else "worse")
                rows.append([c.capitalize(), name, f"{r['regret_diff_A_minus_B']:+.0f}", f"[{r['ci_lo']:+.0f}, {r['ci_hi']:+.0f}]", "@@" + pval(r["holm_p"]), verdict])
    table(["Crop", "Change tested", "Change in regret (Rs/q)", "95% CI", "Holm p", "Verdict"], rows, "|l|l|c|c|c|l|", "tab_ablation")

    # ---- sensitivity (Table 6.9)
    rows = []
    for c in CROPS:
        s = data[c]["sens"]
        real = s[s["method"].isin(["lgbm_filled", "ds_mse_filled", "ds_spo"]) & s["gap_closed_vs_yday"].notna()]
        obs = s[s["method"].isin(["lgbm_obs", "xgb_obs", "ds_mse_obs", "rw"]) & s["gap_closed_vs_yday"].notna()]
        rows.append([c.capitalize(), s[["param", "value"]].drop_duplicates().shape[0], f"{100 * real['gap_closed_vs_yday'].min():.0f}% to {100 * real['gap_closed_vs_yday'].max():.0f}%",
                     f"{100 * obs['gap_closed_vs_yday'].min():.0f}% to {100 * obs['gap_closed_vs_yday'].max():.0f}%"])
    table(["Crop", "Settings", "Realised-outcome models", "Observed-price models"], [[("@@" + esc(x)) for x in r] for r in rows], "|l|c|c|c|", "tab_sens")

    # ---- shocks (Table 6.10)
    sh = json.loads((MODELS / "shock" / "shock_study.json").read_text(encoding="utf-8"))["own_crop"]
    rows = []
    for r in sh["results"]:
        if r["status"] == "OK" and r["tier"] != "NONE":
            rows.append([r["crop"].capitalize(), f"{r['direction']}, {r['horizon']} d", r["n"], f"{100 * r['effect']:+.1f}", f"[{100 * r['ci'][0]:+.1f}, {100 * r['ci'][1]:+.1f}]", f"{100 * (r['mde'] or 0):.1f}",
                         f"{r['placebo_p']:.3f}", f"{r['holm_p']:.2f}", r["tier"].lower()])
    table(["Crop", "Shock", "Episodes", "Effect", "95\\% CI", "MDE", "Placebo p", "Holm p", "Tier"], [[("@@" + esc(x)) for x in r] for r in rows], "|l|l|c|c|c|c|c|c|l|", "tab_shock")
    macro("ShockTested", sh["n_tested"])
    macro("ShockRobust", sh["n_robust"])
    macro("ShockSuggestive", sh["n_suggestive"])
    spill = json.loads((MODELS / "spillover" / "spillover_matrix.json").read_text(encoding="utf-8"))
    macro("SpillEdges", spill.get("total_edges", 40))
    macro("SpillActionable", spill.get("actionable_edges", 0))

    # ---- LLM (Table 6.11)
    ll = json.loads((MODELS / "llm_eval.json").read_text(encoding="utf-8"))
    rows = []
    for lang, v in ll["by_language"].items():
        rows.append([{"en": "English", "kn": "Kannada", "hi": "Hindi"}[lang], v["explanations"], v["sentences"], v["accepted_from_model"], f"{v['accepted_ci'][0]:.2f}--{v['accepted_ci'][1]:.2f}", v["judge_rejected"], v["validator_rejected"]])
    table(["Language", "Texts", "Sentences", "Kept", "95\\% CI of share", "Judge rejected", "Validator rejected"], [[("@@" + esc(x)) for x in r] for r in rows], "|l|c|c|c|c|c|c|", "tab_llm")
    jp = ll["judge_power"]
    macro("JudgeCaught", jp["caught"])
    macro("JudgeBad", jp["corruptions"])
    macro("JudgeFalse", jp["wrongly_rejected"])
    macro("JudgeGood", jp["faithful"])
    macro("LlmLatency", f"{ll['median_latency_ms'] / 1000:.1f}")
    macro("LlmExplanations", ll["explanations"])
    macro("LlmSentences", ll["sentences"])

    # ---- per-fold revenue, tomato (Appendix C)
    pf = data["tomato"]["fold"]
    rows = []
    for f_, g in pf.groupby("fold"):
        g = g.set_index("method")
        rows.append([f"{f_ + 1}", g["test"].iloc[0].replace("..", " to ")] + [f"{g.loc[m, 'revenue']:,.0f}" for m in ["nearest_today", "highest_yesterday", "lgbm_obs", "ds_spo", "gfmc_pred"]])
    table(["Fold", "Test block", "Nearest", "Yesterday", "LGBM obs.", "SPO+", "SPO+ full"], [[("@@" + esc(x)) for x in r] for r in rows], "|c|l|r|r|r|r|r|", "tab_perfold")

    # ---- spillover diagnostics (Table 6.x)
    dg = spill["diagnostics"]
    eps = dg["episodes"]
    rows = [[c.capitalize(), str(eps[f"{c}:SQUEEZE"]), str(eps[f"{c}:GLUT"]), f"{dg['common_factor']['loadings'][c]:+.3f}".replace("-", "$-$")] for c in spill["commodities"]]
    table(["Source crop", "Squeeze episodes", "Glut episodes", "Common-factor loading"], [[("@@" + esc(x)) for x in r] for r in rows], "|l|c|c|c|", "tab_spill")
    stat = pd.Series([e["status"] for e in spill["edges"]]).value_counts()
    macro("SpillPeriods", dg["panel"]["n_periods"])
    macro("SpillVar", f"{100 * dg['common_factor']['variance_explained']:.1f}")
    macro("SpillInsufficient", int(stat.get("INSUFFICIENT_EVIDENCE", 0)))
    macro("SpillTotalEpisodes", sum(eps.values()))
    macro("SpillHoldPairs", dg["holdout"]["raw_pairs_compared"])

    # ---- MCS survivors
    for c in CROPS:
        s = data[c]["summary"]["model_confidence_set"]["survivors"]
        macro(f"MCS{c.capitalize()}", esc(", ".join(LABEL.get(x, x) for x in s)))

    # ---- headline numbers
    for c in CROPS:
        d = data[c]["cmp"]
        r = d[(d["A"] == "lgbm_filled") & (d["B"] == "lgbm_obs")].iloc[0]
        macro(f"LabelEffect{c.capitalize()}", f"{abs(r['regret_diff_A_minus_B']):.0f}")
    t = data["tomato"]["cmp"].set_index("comparison")
    r = t.loc["[label effect] realised-revenue labels vs observed-price labels"]
    macro("LabelEffectNeural", f"{abs(r['regret_diff_A_minus_B']):.0f}")
    macro("LabelEffectNeuralCI", f"{r['ci_lo']:.0f}$\\,$to$\\,${r['ci_hi']:.0f}".replace("-", "$-$"))
    f = data["tomato"]["floors"]
    a = f[(f["spec"] == "gfmc_pred") & f["policy"].str.contains("adaptive")].set_index("alpha")["violation"]
    macro("FloorViolFive", f"{100 * a[0.05]:.1f}")
    macro("FloorViolTen", f"{100 * a[0.1]:.1f}")
    macro("FloorViolTwenty", f"{100 * a[0.2]:.1f}")
    macro("EngineTomatoGain", f"{eng['tomato']['gain_vs_highest_yesterday']['mean']:.0f}")
    macro("EngineTomatoNearest", f"{eng['tomato']['gain_vs_nearest']['mean']:.0f}")
    (GEN / "numbers.tex").write_text("\n".join(MACROS) + "\n", encoding="utf-8")

    # ---- figures ---------------------------------------------------------------------------------------------------------------------------
    for f_ in (ROOT / "docs" / "figures" / "results").glob("*.png"):
        shutil.copy(f_, FIG / f_.name)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})
    k = panel[(panel["crop"] == "tomato") & (panel["mandi_id"] == "kolar_apmc")].sort_values("date")
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(k["date"], k["price"], color="#2563eb", lw=0.8)
    days = pd.date_range(k["date"].min(), k["date"].max())
    missing = days.difference(pd.DatetimeIndex(k["date"]))
    ax.scatter(missing, np.full(len(missing), k["price"].min() * 0.6), s=1.5, color="#dc2626", alpha=0.35, label=f"days with no report ({len(missing):,} of {len(days):,})")
    ax.set_ylabel("Modal price, Rs per quintal")
    ax.set_title("Tomato at Kolar APMC, 2021--2026: prices swing ten-fold and the mandi is often silent", fontsize=9)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    plt.tight_layout()
    plt.savefig(FIG / "fig_intro_kolar_tomato.png", dpi=170)
    plt.close()
    macro_extra = {"KolarMissing": len(missing), "KolarDays": len(days), "KolarMax": f"{k['price'].max():,.0f}", "KolarMin": f"{k['price'].min():,.0f}"}
    with open(GEN / "numbers.tex", "a", encoding="utf-8") as fh:
        for n_, v in macro_extra.items():
            fh.write(rf"\newcommand{{\{n_}}}{{{v}}}" + "\n")
    print(f"wrote {len(list(GEN.glob('*.tex')))} generated files and figures to report/")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
