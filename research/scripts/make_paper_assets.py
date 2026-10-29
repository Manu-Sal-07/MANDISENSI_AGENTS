"""Generate every figure, table and number macro of the IEEE Access manuscript from the result files.

    python scripts/make_paper_assets.py [--out ../papers/IEEE_Access]

Single source of truth: nothing in the manuscript is typed by hand except prose. Re-running after any
experiment refreshes all numbers.
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from gfmc.analysis import HEURISTICS, Study  # noqa: E402
from gfmc.config import DEFAULT_ECON, DEFAULT_CONFORMAL, OUTER_FOLDS, SWEEPS  # noqa: E402
from gfmc.data import loader, panel  # noqa: E402

R = Path(__file__).resolve().parents[1] / "results"
BLUE, GREY, GOLD, RED, GREEN, PURPLE = "#1f4e79", "#8c8c8c", "#c49a00", "#c00000", "#4e8b31", "#6f3d9e"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5, "legend.fontsize": 7, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
    "axes.linewidth": 0.7, "lines.linewidth": 1.3,
})
COL, FULL = 3.45, 7.16          # IEEE column / page width in inches

MACROS: dict = {}
LABELS = {
    "rw": "Random walk", "lgbm_obs": "LightGBM (observed)", "xgb_obs": "XGBoost (observed)",
    "ds_mse_obs": "Neural MSE (observed)", "lgbm_filled": "LightGBM (realised)", "lgbm_filled_sil": "LightGBM (realised) + silence",
    "ds_mse_filled": "Neural MSE (realised)", "ds_spo": "Neural SPO+ (realised)", "ds_spo_struct": "SPO+ + reporting head",
    "gfmc_pred": "SPO+ + head + silence", "gfmc_pred_tuneMSE": "SPO+ + head + silence (tuned on MSE)",
    "nearest_today": "Nearest mandi, today", "highest_yesterday": "Highest price yesterday",
    "trailing_best": "Best 7-day mean", "farm_gate": "Farm gate",
}
OBS_LABEL = ("rw", "lgbm_obs", "xgb_obs", "ds_mse_obs")


def macro(name: str, value) -> None:
    MACROS[name] = value


def tex(x, nd=0, pct=False, sign=False) -> str:
    """Format a number for LaTeX (thousands braces, proper minus)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    v = 100 * x if pct else x
    s = f"{abs(v):,.{nd}f}".replace(",", "{,}")
    neg = v < 0 and float(f"{abs(v):.{nd}f}") != 0
    out = ("$-$" if neg else ("$+$" if sign and v > 0 else "")) + s
    return out + ("\\%" if pct else "")


def pfmt(p: float) -> str:
    if p < 1e-4:
        return "$<$.0001"
    return f"{p:.4f}".lstrip("0") if p < 0.001 else f"{p:.3f}".lstrip("0")


def cls_color(m: str) -> str:
    if m in HEURISTICS:
        return GOLD
    if m in OBS_LABEL:
        return GREY
    return BLUE


def save(fig, path: Path) -> None:
    fig.savefig(path, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


# ------------------------------------------------------------------ figures
def fig_arch(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(FULL, 2.7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")

    def box(x, y, w, h, text, fc, fs=7.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.1", fc=fc, ec="#333", lw=0.8))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.25)

    def arrow(x1, y1, x2, y2, ls="-"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=8, lw=0.9, ls=ls, color="#333"))

    # top row: data -> model -> action values
    box(0.5, 25, 17, 13, "Agmarknet exports\nhistory + daily\n2021\u20132026", "#e8eef5")
    box(21, 25, 17, 13, "Day \u00d7 market panel\nreported mask\nno imputation", "#e8eef5")
    box(41.5, 25, 17, 13, "Causal features\nthrough day $t\\!-\\!1$\nbase  |  silence", "#e8eef5")
    box(62, 25, 17, 13, "Price-vector model\nobserved labels  or\nrealised-outcome labels", "#dce9d5")
    box(82.5, 25, 17, 13, "Action values $\\hat r$\n12 markets \u00d7 4 holds\n+ farm gate = 49", "#fbe9c8")
    for x1, x2 in ((17.5, 21), (38, 41.5), (58.5, 62), (79, 82.5)):
        arrow(x1, 31.5, x2, 31.5)

    # bottom row: floor and recommendation
    box(62, 6, 17, 13, "Adaptive conformal floor\n$L=\\hat r-q_t\\hat\\sigma$,  $\\alpha_t$ updated\nwith delayed feedback", "#f6d6d6")
    box(82.5, 6, 17, 13, "Recommendation\nargmax $\\hat r$ or argmax $L$\n+ stated revenue floor", "#fbe9c8")
    box(0.5, 6, 58, 13, "Nested walk-forward evaluation\nouter test block  \u2190  tuning on two inner blocks (Optuna, gap $K\\!+\\!2$ days)\n"
        "\u2190  calibration model fitted before the calibration block  \u2190  final model", "#f1f1f1", fs=6.9)
    arrow(91, 25, 91, 19.4)
    arrow(82.5, 12.5, 79.2, 12.5)
    arrow(70.5, 25, 70.5, 19.4, ls="--")
    ax.text(71.4, 22.0, "$\\hat r$", fontsize=7)
    ax.text(0.5, 1.2, "Realised revenue reaches the learner only after the sale date has passed; the floor never reads an unresolved outcome.",
            fontsize=6.5, style="italic", color="#444")
    save(fig, out / "fig_arch.pdf")


def fig_data(out: Path, hist: pd.DataFrame, daily: pd.DataFrame, pan) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(FULL, 2.7), gridspec_kw={"width_ratios": [1.55, 1], "wspace": 0.42})
    ax = axs[0]
    months = pan.dates.to_period("M")
    uniq = months.unique()
    order = np.argsort(-pan.mask.sum(0))
    heat = np.array([[pan.mask[months == m, j].mean() for m in uniq] for j in order])
    im = ax.imshow(heat, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([pan.markets[j].replace(" APMC", "").replace(" (FF&V) Bengaluru", " (Bengaluru)") for j in order], fontsize=6.5)
    ticks = [i for i, m in enumerate(uniq) if m.month == 1]
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(uniq[i].year) for i in ticks])
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("share of days reporting", fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    ax.set_title("(a) Reporting is irregular and market-specific", loc="left")
    ax.spines[:].set_visible(False)

    ax = axs[1]
    a = hist[hist["commodity"] == "Tomato"].set_index(["date", "market"])["price"]
    b = daily[daily["commodity"] == "Tomato"].set_index(["date", "market"])["price"]
    both = pd.concat([a.rename("h"), b.rename("d")], axis=1, join="inner").dropna()
    ax.scatter(both["d"], both["h"], s=3, alpha=0.35, color=BLUE, lw=0)
    lim = [0, both.max().max() * 1.03]
    ax.plot(lim, lim, color=RED, lw=0.8, ls="--")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    r = np.corrcoef(both["h"], both["d"])[0, 1]
    ax.text(0.04, 0.93, f"$n={len(both):,}$ market-days\n$r={r:.5f}$", transform=ax.transAxes, va="top", fontsize=7)
    ax.set_xlabel("Daily report, weighted modal price (Rs/q)")
    ax.set_ylabel("History export price (Rs/q)")
    ax.set_title("(b) Two independent exports agree", loc="left")
    save(fig, out / "fig_data.pdf")
    macro("XRows", f"{len(both):,}".replace(",", "{,}"))
    macro("XCorr", f"{r:.5f}")


def fig_leak(out: Path, lk: pd.DataFrame, sens: pd.DataFrame) -> None:
    fig, axs = plt.subplots(1, 3, figsize=(FULL, 2.55), gridspec_kw={"width_ratios": [1, 1, 0.62]})
    series = [("published_joint", "Published (global decomposition)", RED), ("causal_joint", "Causal (past only)", BLUE),
              ("raw", "Raw series, no decomposition", GREY)]
    for ax, h in zip(axs[:2], (1, 7)):
        g = lk[lk["h"] == h].copy()
        g["lab"] = g["decomposer"] + "\n" + g["forecaster"].map({"ridge": "Ridge", "lgbm": "LightGBM"})
        x = np.arange(len(g))
        w = 0.26
        for i, (k, lab, c) in enumerate(series):
            ax.bar(x + (i - 1) * w, 100 * g[f"skill_{k}"], w, color=c, label=lab)
        ax.axhline(0, color="k", lw=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(g["lab"], fontsize=6.5)
        ax.set_title(f"({'a' if h == 1 else 'b'}) Horizon $h={h}$ day{'s' if h > 1 else ''}", loc="left")
        ax.set_ylabel("MAE skill vs random walk (%)" if h == 1 else "")
        ax.set_ylim(-22, 78)
    axs[0].legend(loc="upper left", frameon=False, fontsize=6.3)
    ax = axs[2]
    names = ["STL", "VMD", "causal\n(any)"]
    vals = [100 * sens.loc[sens["decomposer"] == "STL", "median_future_sensitivity"].iloc[0],
            100 * sens.loc[sens["decomposer"] == "VMD", "median_future_sensitivity"].iloc[0], 0.0]
    ax.bar(names, vals, color=[RED, RED, BLUE], width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.15, f"{v:.1f}", ha="center", fontsize=7)
    ax.set_ylabel("Change at $t$ when only the\nfuture moves (% of s.d.)")
    ax.set_title("(c) Look-ahead", loc="left")
    save(fig, out / "fig_leak.pdf")


def fig_decision(out: Path, st: Study, main_t: pd.DataFrame) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(FULL, 3.0), gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.55})
    ax = axs[0]
    d = main_t[main_t["method"] != "oracle(hindsight)"].sort_values("revenue")
    y = np.arange(len(d))
    ax.barh(y, d["revenue"], color=[cls_color(m) for m in d["method"]], height=0.72)
    orc = float(main_t.loc[main_t["method"] == "oracle(hindsight)", "revenue"].iloc[0])
    ax.axvline(orc, color="k", ls="--", lw=0.8)
    ax.text(orc - 12, len(d) - 0.4, "hindsight oracle", ha="right", va="center", fontsize=6.5)
    ax.set_yticks(y)
    ax.set_yticklabels([LABELS.get(m, m) for m in d["method"]], fontsize=6.3)
    ax.set_xlim(1200, 2650)
    ax.set_ylim(-0.6, len(d) + 0.2)
    ax.set_xlabel("Mean realised net revenue (Rs/quintal), out of sample")
    ax.set_title("(a) Decision value", loc="left")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="trained on realised outcomes"), Patch(color=GREY, label="trained on observed prices"),
                       Patch(color=GOLD, label="heuristic")], loc="upper center", frameon=False, fontsize=6.1, bbox_to_anchor=(0.30, -0.17), ncol=3, columnspacing=1.0, handlelength=1.2)

    ax = axs[1]
    pf = pd.read_csv(R / "tomato" / "tables" / "per_fold.csv")
    piv = pf.pivot(index="fold", columns="method", values="revenue")
    xs = np.arange(len(piv))
    for m, c, ls, lab in (("ds_spo", BLUE, "-", "Neural SPO+ (realised)"), ("lgbm_obs", GREY, "-", "LightGBM (observed)"),
                          ("highest_yesterday", GOLD, "-", "Highest price yesterday"), ("nearest_today", GOLD, ":", "Nearest mandi, today")):
        ax.plot(xs, piv[m], marker="o", ms=3, color=c, ls=ls, label=lab)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{a[:7]}" for a, _ in OUTER_FOLDS], fontsize=6.3, rotation=18)
    ax.set_xlabel("outer test block (start month)")
    ax.set_ylabel("Mean net revenue (Rs/q)")
    ax.set_ylim(700, 3300)
    ax.legend(frameon=False, fontsize=6.0, loc="lower right", ncol=1)
    ax.set_title("(b) The gain recurs in every fold", loc="left")
    save(fig, out / "fig_decision.pdf")


def fig_effects(out: Path, comp: pd.DataFrame, other: dict) -> None:
    fig, ax = plt.subplots(figsize=(FULL, 3.1))
    keep = [
        ("[label effect] realised-revenue labels vs observed-price labels", "Realised vs observed labels (neural)"),
        ("[label effect, GBM] realised-revenue labels vs observed-price labels", "Realised vs observed labels (LightGBM)"),
        ("GFMC predictor vs LightGBM (predict-then-optimise)", "SPO+ model vs LightGBM predict-then-optimise"),
        ("GFMC predictor vs best simple heuristic", "SPO+ model vs best heuristic"),
        ("[loss effect] SPO+ vs MSE, same labels and network", "SPO+ vs MSE, same labels and network"),
        ("[head effect] reporting head vs none", "Reporting-probability head vs none"),
        ("[silence effect] + network silence features", "Network-silence features (neural)"),
        ("[silence effect] GBM with vs without silence features", "Network-silence features (LightGBM)"),
        ("[tuning effect] tuned on decision regret vs forecast loss", "Tuned on decision regret vs forecast loss"),
        ("structured SPO+ network vs GBM, both on realised labels", "Neural vs LightGBM on identical labels"),
    ]
    ypos, labs = [], []
    for i, (key, lab) in enumerate(keep):
        r = comp[comp["comparison"] == key]
        if r.empty:
            continue
        r = r.iloc[0]
        sig = r["holm_p"] < 0.05
        col = BLUE if (sig and r["regret_diff_A_minus_B"] < 0) else (RED if sig else GREY)
        y = len(keep) - i
        ax.errorbar(r["regret_diff_A_minus_B"], y, xerr=[[r["regret_diff_A_minus_B"] - r["ci_lo"]], [r["ci_hi"] - r["regret_diff_A_minus_B"]]],
                    fmt="o", color=col, ms=4, capsize=2, lw=1.2)
        ax.text(r["ci_hi"] + 6, y, f"Holm $p$ {pfmt(r['holm_p'])}", va="center", fontsize=6.3, color="#444")
        ypos.append(y)
        labs.append(lab)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labs, fontsize=7)
    ax.set_ylim(0.3, len(keep) + 0.8)
    ax.set_xlim(-215, 125)
    ax.set_xlabel("Paired difference in daily regret, Rs/quintal (negative: first method better); 95% block-bootstrap CI")
    ax.set_title("Tomato, five nested walk-forward folds, 963 decision days   (blue: significant gain, grey: not significant, red: significantly worse)",
                 loc="left", fontsize=7.2)
    save(fig, out / "fig_effects.pdf")


def fig_decouple(out: Path, main_t: pd.DataFrame, fc: pd.DataFrame) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(FULL, 2.7), sharey=True)
    m = main_t.merge(fc, on="method")
    m = m[~m["method"].isin(["ds_spo", "ds_spo_struct", "gfmc_pred", "gfmc_pred_tuneMSE"])]   # SPO+ outputs are not price-anchored
    off = {"lgbm_filled": (-30, 7), "lgbm_filled_sil": (7, -13), "ds_mse_filled": (4, -9), "rw": (4, -9)}
    for ax, col in zip(axs, ("skill_vs_rw_observed", "skill_vs_rw_realised")):
        for _, r in m.iterrows():
            ax.scatter(100 * r[col], 100 * r["gap_closed_vs_yday"], color=cls_color(r["method"]), s=26, zorder=3)
        ax.axhline(0, color="k", lw=0.5)
        ax.axvline(0, color="k", lw=0.5)
    ax = axs[0]
    for _, r in m.iterrows():
        if r["method"] in ("lgbm_obs", "xgb_obs", "ds_mse_obs"):
            continue
        ax.annotate(LABELS.get(r["method"], r["method"]), (100 * r["skill_vs_rw_observed"], 100 * r["gap_closed_vs_yday"]), fontsize=6,
                    xytext=off.get(r["method"], (4, 4)), textcoords="offset points")
    ax.annotate("observed-label models\n(LightGBM, XGBoost, neural)", (3.7, -0.6), fontsize=6, xytext=(-62, 18), textcoords="offset points",
                arrowprops=dict(arrowstyle="-", lw=0.5, color="#666"))
    ax.set_xlabel("Forecast MAE skill vs random walk, observed prices (%)")
    ax.set_ylabel("Decision gain over best heuristic\n(share of oracle gap closed, %)")
    ax.set_title("(a) Forecast skill does not rank decisions", loc="left")
    axs[1].set_xlabel("Forecast MAE skill vs random walk, realised labels (%)")
    axs[1].set_title("(b) Skill on realised outcomes does", loc="left")
    save(fig, out / "fig_decouple.pdf")


def fig_floor(out: Path, floors: pd.DataFrame, trace: dict) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(FULL, 2.8), gridspec_kw={"width_ratios": [1, 1.35], "wspace": 0.3})
    ax = axs[0]
    ax.plot([0, 0.3], [0, 0.3], color="k", lw=0.7, ls="--", label="ideal")
    for spec, c, lab in (("gfmc_pred", BLUE, "SPO+ model"), ("lgbm_filled", GREEN, "LightGBM (realised)"), ("lgbm_obs", GREY, "LightGBM (observed)")):
        g = floors[floors["spec"] == spec]
        ad = g[g["policy"] == "adaptive conformal floor"]
        nv = g[g["policy"].str.startswith("naive")]
        ax.plot(ad["alpha"], ad["violation"], marker="o", ms=3.5, color=c, label=f"adaptive: {lab}")
        ax.scatter(nv["alpha"], nv["violation"], marker="s", s=26, facecolor="white", edgecolor=c, lw=1.3, zorder=4)
    ax.scatter([], [], marker="s", s=26, facecolor="white", edgecolor="k", lw=1.3, label="naive Gaussian ($z=1.28$)")
    ax.set_xlabel("target violation rate $\\alpha$")
    ax.set_ylabel("observed violation rate")
    ax.set_xlim(0, 0.42)
    ax.set_ylim(0, 0.34)
    ax.set_xticks([0, 0.1, 0.2, 0.3])
    ax.legend(frameon=False, fontsize=5.9, loc="lower right")
    ax.set_title("(a) Calibration", loc="left")

    ax = axs[1]
    d = pd.to_datetime(trace["dates"])
    viol = (trace["rev"] < trace["floor"]).astype(float).mean(1)
    order = np.argsort(d)
    s = pd.Series(viol[order], index=d[order]).groupby(level=0).mean().rolling(90, min_periods=30).mean()
    a = pd.Series(np.asarray(trace["alpha_t"]).mean(1)[order], index=d[order]).groupby(level=0).mean()
    ax.plot(s.index, s.values, color=BLUE, label="rolling 90-day violation rate")
    ax.axhline(DEFAULT_CONFORMAL.alpha, color="k", ls="--", lw=0.8, label="target $\\alpha=0.10$")
    ax.plot(a.index, a.values, color=RED, lw=0.9, label="adaptive level $\\alpha_t$")
    ax.set_ylim(0, 0.34)
    ax.set_ylabel("rate")
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.legend(frameon=False, fontsize=6.3, loc="upper right")
    ax.set_title("(b) The floor tracks its target over time", loc="left")
    save(fig, out / "fig_floor.pdf")


def fig_sens(out: Path, sens: pd.DataFrame) -> None:
    fig, axs = plt.subplots(1, 3, figsize=(FULL, 2.4), sharey=True)
    meth = [("lgbm_obs", GREY, "LightGBM (observed)"), ("rw", "#bbbbbb", "Random walk"), ("lgbm_filled", GREEN, "LightGBM (realised)"),
            ("ds_spo_struct", BLUE, "SPO+ + head"), ("gfmc_pred", RED, "SPO+ + head + silence")]
    titles = {"transport_per_q_km": "(a) transport Rs/(q$\\cdot$km)", "spoilage_per_day": "(b) spoilage per day", "fallback_discount": "(c) silent-mandi price factor $\\phi$"}
    for ax, p in zip(axs, ("transport_per_q_km", "spoilage_per_day", "fallback_discount")):
        g = sens[sens["param"] == p]
        for m, c, lab in meth:
            gg = g[g["method"] == m].sort_values("value")
            ax.plot(gg["value"], 100 * gg["gap_closed_vs_yday"], marker="o", ms=3, color=c, label=lab)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel(titles[p])
    axs[0].set_ylabel("Oracle gap closed beyond\nbest heuristic (%)")
    axs[0].legend(frameon=False, fontsize=6, loc="center left")
    save(fig, out / "fig_sens.pdf")


# ------------------------------------------------------------------- tables
def write(out: Path, name: str, body: str) -> None:
    (out / f"{name}.tex").write_text(body, encoding="utf-8")


def tables(out: Path, st: Study, pan, hist, main_t, comp, floors, lk, sil, fc, crops) -> None:
    # data
    s = pan.summary()
    dist = hist.drop_duplicates("market").set_index("market")["district"]
    rows = ["\\begin{tabular}{llrrc}", "\\toprule", "Market (APMC) & District & Days & Cover. & Span\\\\", "\\midrule"]
    for _, r in s.iterrows():
        rows.append(f"{r['market'].replace(' APMC', '').replace('(FF&V) ', '').replace('&', '\\&')} & {dist.get(r['market'], '')} & "
                    f"{tex(r['reported_days'])} & {tex(r['coverage'], 0, pct=True)} & {r['first'].year}--{r['last'].year}\\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_data", "\n".join(rows))

    # main results
    t = main_t.set_index("method")
    grp = lambda ms: sorted([m for m in ms if m in t.index], key=lambda m: -t.loc[m, "revenue"])
    order = (grp(["lgbm_filled_sil", "ds_spo", "lgbm_filled", "ds_mse_filled", "ds_spo_struct", "gfmc_pred"])
             + grp(["highest_yesterday", "xgb_obs", "lgbm_obs", "ds_mse_obs", "rw"]) + grp(["trailing_best", "nearest_today", "farm_gate"]))
    rows = ["\\begin{tabular}{lrrrrr}", "\\toprule", "Method & Revenue & Regret & Gap closed & CVaR$_{10}$ & Fallback\\\\", "\\midrule"]
    orc = float(main_t.loc[main_t["method"] == "oracle(hindsight)", "revenue"].iloc[0])
    rows.append(f"\\emph{{Hindsight oracle}} & {tex(orc)} & 0 & 1.00 & -- & --\\\\")
    rows.append("\\midrule")
    best = t.loc[[m for m in order if m in t.index], "revenue"].idxmax()
    for m in order:
        if m not in t.index:
            continue
        r = t.loc[m]
        rev = tex(r["revenue"])
        rev = f"\\textbf{{{rev}}}" if m == best else rev
        rows.append(f"{LABELS.get(m, m)} & {rev} & {tex(r['regret'])} & {tex(r['gap_closed_vs_nearest'], 2)} & {tex(r['cvar10'])} & {tex(r['fallback_rate'], 0, pct=True)}\\\\")
        if m == order[5] or m == order[10]:
            rows.append("\\midrule")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_main", "\n".join(rows))

    # paired effects
    rows = ["\\begin{tabular}{lrrr}", "\\toprule", "Comparison (A vs B) & $\\Delta$ regret & 95\\% CI & Holm $p$\\\\", "\\midrule"]
    pairs = [
        ("[label effect] realised-revenue labels vs observed-price labels", "Realised vs observed labels, neural"),
        ("[label effect, GBM] realised-revenue labels vs observed-price labels", "Realised vs observed labels, LightGBM"),
        ("GFMC predictor vs LightGBM (predict-then-optimise)", "SPO+ + head + silence vs LightGBM (observed)"),
        ("GFMC predictor vs XGBoost (predict-then-optimise)", "SPO+ + head + silence vs XGBoost (observed)"),
        ("GFMC predictor vs random walk", "SPO+ + head + silence vs random walk"),
        ("GFMC predictor vs best simple heuristic", "SPO+ + head + silence vs best heuristic"),
        ("GFMC predictor vs LightGBM on realised-revenue labels", "SPO+ + head + silence vs LightGBM (realised)"),
        ("[loss effect] SPO+ vs MSE, same labels and network", "SPO+ vs MSE, same labels and network"),
        ("[head effect] reporting head vs none", "Reporting head vs none"),
        ("[silence effect] + network silence features", "Silence features, neural"),
        ("[silence effect] GBM with vs without silence features", "Silence features, LightGBM"),
        ("[tuning effect] tuned on decision regret vs forecast loss", "Tuned on regret vs forecast loss"),
        ("structured SPO+ network vs GBM, both on realised labels", "SPO+ + head vs LightGBM, same labels"),
    ]
    for key, lab in pairs:
        r = comp[comp["comparison"] == key]
        if r.empty:
            continue
        r = r.iloc[0]
        rows.append(f"{lab} & {tex(r['regret_diff_A_minus_B'], 0, sign=True)} & [{tex(r['ci_lo'], 0)}, {tex(r['ci_hi'], 0)}] & {pfmt(r['holm_p'])}\\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_effects", "\n".join(rows))

    # leakage
    rows = ["\\begin{tabular}{llcrrrrr}", "\\toprule", "Decomp. & Forecaster & $h$ & Published & Pub.-joint & Causal-joint & Raw & Leak gap [95\\% CI]\\\\", "\\midrule"]
    for _, r in lk.sort_values(["decomposer", "forecaster", "h"]).iterrows():
        rows.append(f"{r['decomposer']} & {'Ridge' if r['forecaster'] == 'ridge' else 'LightGBM'} & {int(r['h'])} & {tex(r['skill_published'], 1, pct=True, sign=True)} & "
                    f"{tex(r['skill_published_joint'], 1, pct=True, sign=True)} & {tex(r['skill_causal_joint'], 1, pct=True, sign=True)} & "
                    f"{tex(r['skill_raw'], 1, pct=True, sign=True)} & {100 * r['leak_gap_skill']:.1f} [{100 * r['leak_gap_ci_lo']:.1f}, {100 * r['leak_gap_ci_hi']:.1f}]\\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_leak", "\n".join(rows))

    # floors
    rows = ["\\begin{tabular}{llcrrrr}", "\\toprule", "Predictor & Policy & $\\alpha$ & Violation & Mean floor & Revenue & CVaR$_{10}$\\\\", "\\midrule"]
    sel = [("gfmc_pred", "SPO+ model"), ("lgbm_filled", "LightGBM (realised)"), ("lgbm_obs", "LightGBM (observed)")]
    for spec, lab in sel:
        g = floors[floors["spec"] == spec]
        p0 = g[g["policy"] == "plug-in (no floor)"].iloc[0]
        rows.append(f"{lab} & plug-in (no floor) & -- & -- & -- & {tex(p0['revenue'])} & {tex(p0['cvar10'])}\\\\")
        for _, r in g[g["policy"] == "adaptive conformal floor"].iterrows():
            rows.append(f" & adaptive conformal & {r['alpha']:.2f} & {tex(r['violation'], 1, pct=True)} & {tex(r['mean_floor'])} & {tex(r['revenue'])} & {tex(r['cvar10'])}\\\\")
        for pol, name in (("static conformal floor", "static conformal"), ("naive Gaussian floor (z=1.28)", "naive Gaussian")):
            r = g[g["policy"] == pol].iloc[0]
            rows.append(f" & {name} & {r['alpha']:.2f} & {tex(r['violation'], 1, pct=True)} & {tex(r['mean_floor'])} & {tex(r['revenue'])} & {tex(r['cvar10'])}\\\\")
        rows.append("\\midrule")
    rows[-1] = "\\bottomrule"
    rows.append("\\end{tabular}")
    write(out, "tab_floor", "\n".join(rows))

    # crops
    rows = ["\\begin{tabular}{lrrrrrr}", "\\toprule", "Crop (markets) & Oracle & Heuristic & LGBM-obs & LGBM-real & SPO+ & Label effect [95\\% CI]\\\\", "\\midrule"]
    for crop, k in crops:
        m = crop["main"].set_index("method")
        e = crop["comp"]
        e = e[e["comparison"].str.contains("label effect")].iloc[0]
        rows.append(f"{k} & {tex(m.loc['oracle(hindsight)', 'revenue'])} & {tex(m.loc['highest_yesterday', 'revenue'])} & {tex(m.loc['lgbm_obs', 'revenue'])} & "
                    f"{tex(m.loc['lgbm_filled', 'revenue'])} & {tex(m.loc['ds_spo', 'revenue'])} & {tex(e['regret_diff_A_minus_B'], 0, sign=True)} [{tex(e['ci_lo'], 0)}, {tex(e['ci_hi'], 0)}]\\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_crops", "\n".join(rows))

    # forecast accuracy (decoupling)
    keep = ["rw", "lgbm_obs", "xgb_obs", "ds_mse_obs", "lgbm_filled", "ds_mse_filled", "ds_spo", "ds_spo_struct"]
    rows = ["\\begin{tabular}{lrrr}", "\\toprule", "Method & Skill, observed & Skill, realised & Gap closed (vs heuristic)\\\\", "\\midrule"]
    mm = main_t.set_index("method")
    for _, r in fc.set_index("method").loc[[k for k in keep if k in fc["method"].values]].reset_index().iterrows():
        rows.append(f"{LABELS.get(r['method'], r['method'])} & {tex(r['skill_vs_rw_observed'], 1, pct=True, sign=True)} & {tex(r['skill_vs_rw_realised'], 1, pct=True, sign=True)} & "
                    f"{tex(mm.loc[r['method'], 'gap_closed_vs_yday'], 1, pct=True, sign=True)}\\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_forecast", "\n".join(rows))

    # silence
    rows = ["\\begin{tabular}{lrrrrr}", "\\toprule", "Fold & AUC base & AUC +silence & $\\Delta$AUC & MAE base & MAE +silence\\\\", "\\midrule"]
    a, b = sil["rep"], sil["ret"]
    ag = a.groupby("fold")[["auc_base", "auc_silence", "d_auc"]].mean()
    for f in ag.index:
        bb = b[b["fold"] == f].iloc[0]
        rows.append(f"{f + 1} & {ag.loc[f, 'auc_base']:.3f} & {ag.loc[f, 'auc_silence']:.3f} & {tex(ag.loc[f, 'd_auc'], 4, sign=True)} "
                    f"& {bb['mae_base']:.4f} & {bb['mae_silence']:.4f}\\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    write(out, "tab_silence", "\n".join(rows))

    # economics parameters
    e = DEFAULT_ECON
    rows = ["\\begin{tabular}{llll}", "\\toprule", "Symbol & Meaning & Default & Sweep\\\\", "\\midrule",
            f"$\\tau$ & transport, Rs per quintal-km & {e.transport_per_q_km} & 0.20, 0.35, 0.70, 1.40\\\\",
            f"$\\rho$ & road / great-circle distance & {e.road_factor} & --\\\\",
            f"$f$ & market fee and commission & {int(100 * e.market_fee)}\\% & --\\\\",
            f"$c_0$ & handling per trip (Rs/q) & {int(e.handling)} & --\\\\",
            "$\\delta$ & spoilage per day (tomato / onion / potato) & 3\\% / 0.8\\% / 0.4\\% & tomato: 1, 3, 6\\%\\\\",
            f"$\\phi$ & price factor if the chosen mandi is silent & {e.fallback_discount} & 0.70, 0.85, 1.00\\\\",
            f"$\\phi_g$ & farm-gate price factor & {e.farmgate_discount} & --\\\\",
            "\\bottomrule", "\\end{tabular}"]
    write(out, "tab_econ", "\n".join(rows))


def numbers(out: Path, st: Study, main_t, comp, floors, lk, sil, crops, fc, auc, floor_run, sens_ls) -> None:
    t = main_t.set_index("method")
    macro("NTest", f"{len(st.test_idx):,}".replace(",", "{,}"))
    macro("NFold", len(st.fold_ids))
    macro("NMkt", st.dd.M)
    macro("NAct", st.dd.M * 4 + 1)
    macro("RevOracle", tex(t.loc["oracle(hindsight)", "revenue"]))
    for m, nm in (("lgbm_obs", "LgbmObs"), ("lgbm_filled", "LgbmFilled"), ("ds_spo", "DsSpo"), ("highest_yesterday", "HighYday"),
                  ("nearest_today", "Nearest"), ("farm_gate", "Gate"), ("rw", "Rw"), ("ds_mse_filled", "DsMseFilled"), ("gfmc_pred", "Gfmc"),
                  ("ds_spo_struct", "DsStruct"), ("lgbm_filled_sil", "LgbmFilledSil"), ("xgb_obs", "XgbObs"), ("ds_mse_obs", "DsMseObs")):
        macro("Rev" + nm, tex(t.loc[m, "revenue"]))
        macro("Gap" + nm, tex(t.loc[m, "gap_closed_vs_nearest"], 2))
        macro("FB" + nm, tex(t.loc[m, "fallback_rate"], 0, pct=True))
    macro("RevFilledLo", tex(min(t.loc[m, "revenue"] for m in ("ds_mse_filled", "lgbm_filled", "ds_spo", "ds_spo_struct", "gfmc_pred", "lgbm_filled_sil"))))
    macro("RevFilledHi", tex(max(t.loc[m, "revenue"] for m in ("ds_mse_filled", "lgbm_filled", "ds_spo", "ds_spo_struct", "gfmc_pred", "lgbm_filled_sil"))))
    macro("PctGainLo", f"{100 * (t.loc[['ds_mse_filled', 'lgbm_filled', 'ds_spo'], 'revenue'].min() / t.loc['lgbm_obs', 'revenue'] - 1):.1f}")
    macro("PctGainHi", f"{100 * (t.loc[['lgbm_filled_sil', 'lgbm_filled', 'ds_spo'], 'revenue'].max() / t.loc['lgbm_obs', 'revenue'] - 1):.1f}")

    def eff(key, nm):
        r = comp[comp["comparison"] == key].iloc[0]
        macro(nm + "D", tex(r["regret_diff_A_minus_B"], 0))
        macro(nm + "DAbs", tex(abs(r["regret_diff_A_minus_B"]), 0))
        macro(nm + "LoAbs", tex(abs(r["ci_lo"]), 0))
        macro(nm + "HiAbs", tex(abs(r["ci_hi"]), 0))
        macro(nm + "Lo", tex(r["ci_lo"], 0))
        macro(nm + "Hi", tex(r["ci_hi"], 0))
        macro(nm + "P", pfmt(r["holm_p"]))
        macro(nm + "Raw", pfmt(r["dm_p"]))
    eff("[label effect] realised-revenue labels vs observed-price labels", "Label")
    eff("[loss effect] SPO+ vs MSE, same labels and network", "Loss")
    eff("[head effect] reporting head vs none", "Head")
    eff("[silence effect] + network silence features", "SilNN")
    eff("[silence effect] GBM with vs without silence features", "SilGbm")
    eff("[tuning effect] tuned on decision regret vs forecast loss", "Tune")
    eff("GFMC predictor vs LightGBM (predict-then-optimise)", "VsLgbm")
    eff("GFMC predictor vs best simple heuristic", "VsHeur")
    eff("GFMC predictor vs random walk", "VsRw")
    eff("structured SPO+ network vs GBM, both on realised labels", "NnGbm")

    for crop, nm in crops:
        e = crop["comp"]
        e = e[e["comparison"].str.contains("label effect")].iloc[0]
        macro(nm + "LabelD", tex(e["regret_diff_A_minus_B"], 0))
        macro(nm + "LabelLo", tex(e["ci_lo"], 0))
        macro(nm + "LabelHi", tex(e["ci_hi"], 0))
        macro(nm + "LabelP", pfmt(e["holm_p"]))
        l = crop["comp"][crop["comp"]["comparison"].str.contains("loss effect")].iloc[0]
        macro(nm + "LossD", tex(l["regret_diff_A_minus_B"], 0))
        macro(nm + "LossP", pfmt(l["dm_p"]))
    # floors
    g = floors[floors["spec"] == "gfmc_pred"]
    for a, nm in ((0.05, "Five"), (0.10, "Ten"), (0.20, "Twenty")):
        r = g[(g["policy"] == "adaptive conformal floor") & (np.isclose(g["alpha"], a))].iloc[0]
        macro("Viol" + nm, tex(r["violation"], 1, pct=True))
    macro("ViolNaiveG", tex(g[g["policy"].str.startswith("naive")].iloc[0]["violation"], 1, pct=True))
    macro("ViolNaiveObs", tex(floors[(floors["spec"] == "lgbm_obs") & floors["policy"].str.startswith("naive")].iloc[0]["violation"], 1, pct=True))
    macro("ViolNaiveFilled", tex(floors[(floors["spec"] == "lgbm_filled") & floors["policy"].str.startswith("naive")].iloc[0]["violation"], 1, pct=True))
    p0 = g[g["policy"] == "plug-in (no floor)"].iloc[0]
    a10 = g[(g["policy"] == "adaptive conformal floor") & (np.isclose(g["alpha"], 0.10))].iloc[0]
    macro("FloorCost", tex(p0["revenue"] - a10["revenue"], 0))
    macro("FloorCostPct", f"{100 * (p0['revenue'] - a10['revenue']) / p0['revenue']:.1f}")
    gl = floors[floors["spec"] == "lgbm_filled"]
    p1 = gl[gl["policy"] == "plug-in (no floor)"].iloc[0]
    a1 = gl[(gl["policy"] == "adaptive conformal floor") & (np.isclose(gl["alpha"], 0.10))].iloc[0]
    macro("FloorCostLgbm", tex(p1["revenue"] - a1["revenue"], 0))
    macro("FloorCostLgbmPct", f"{100 * (p1['revenue'] - a1['revenue']) / p1['revenue']:.0f}")
    macro("MeanFloor", tex(a10["mean_floor"], 0))
    byf = floor_run["violation_by_fold"]
    macro("ViolFoldLo", tex(min(byf.values()), 1, pct=True))
    macro("ViolFoldHi", tex(max(byf.values()), 1, pct=True))
    # leakage
    macro("LeakGapLo", f"{100 * lk['leak_gap_skill'].min():.0f}")
    macro("LeakGapHi", f"{100 * lk['leak_gap_skill'].max():.0f}")
    macro("PubLo", f"{100 * lk['skill_published'].min():.0f}")
    macro("PubHi", f"{100 * lk['skill_published'].max():.0f}")
    macro("PubJointLo", f"{100 * lk['skill_published_joint'].min():.0f}")
    macro("PubJointHi", f"{100 * lk['skill_published_joint'].max():.0f}")
    macro("CauLo", f"{100 * lk['skill_causal_joint'].min():.0f}")
    macro("CauHi", f"{100 * lk['skill_causal_joint'].max():.1f}")
    macro("RawLo", f"{100 * lk['skill_raw'].min():.0f}")
    macro("RawHi", f"{100 * lk['skill_raw'].max():.0f}")
    macro("CauLoAbs", f"{abs(100 * lk['skill_causal_joint'].min()):.0f}")
    macro("CauHiAbs", f"{abs(100 * lk['skill_causal_joint'].max()):.1f}")
    macro("RawLoAbs", f"{abs(100 * lk['skill_raw'].min()):.0f}")
    macro("RawHiAbs", f"{abs(100 * lk['skill_raw'].max()):.0f}")
    macro("PercompLoAbs", f"{abs(100 * lk['skill_causal_percomp'].max()):.0f}")
    macro("PercompHiAbs", f"{abs(100 * lk['skill_causal_percomp'].min()):.0f}")
    macro("LeakNOrigins", f"{int(lk['n'].max()):,}".replace(",", "{,}"))
    sd = pd.read_csv(R / "tomato" / "leakage" / "foundation_skill.csv")
    macro("FoundA", tex(sd.loc[sd["h"] == 1, "skill_foundation"].iloc[0], 1, pct=True))
    macro("FoundB", tex(sd.loc[sd["h"] == 7, "skill_foundation"].iloc[0], 1, pct=True))
    se = pd.read_csv(R / "tomato" / "leakage" / "future_sensitivity.csv")
    macro("SensStl", f"{100 * se.loc[se['decomposer'] == 'STL', 'median_future_sensitivity'].iloc[0]:.1f}")
    macro("SensVmd", f"{100 * se.loc[se['decomposer'] == 'VMD', 'median_future_sensitivity'].iloc[0]:.1f}")
    # silence
    a, b = sil["rep"], sil["ret"]
    sj = json.load(open(R / "tomato" / "silence" / "summary.json"))
    macro("SilDAuc", f"{a['d_auc'].mean():+.4f}".replace("-", "$-$").replace("+", "$+$"))
    macro("SilLLLo", f"{sj['reporting']['ci_lo']:.4f}".replace("-", "$-$"))
    macro("SilLLHi", f"{sj['reporting']['ci_hi']:.4f}")
    macro("SilFolds", f"{sj['reporting']['folds_improved']}")
    macro("SilDMp", f"{sj['returns_dm']['p']:.3f}".lstrip("0"))
    macro("AucBaseLo", f"{a.groupby('fold')['auc_base'].mean().min():.2f}")
    macro("AucBaseHi", f"{a.groupby('fold')['auc_base'].mean().max():.2f}")
    # forecast skill
    f = fc.set_index("method")
    macro("SkObsLgbm", tex(f.loc["lgbm_obs", "skill_vs_rw_observed"], 1, pct=True, sign=True))
    macro("SkObsNn", tex(f.loc["ds_mse_obs", "skill_vs_rw_observed"], 1, pct=True, sign=True))
    macro("SkObsFilled", tex(f.loc["lgbm_filled", "skill_vs_rw_observed"], 1, pct=True, sign=True))
    macro("SkRealFilled", tex(f.loc["lgbm_filled", "skill_vs_rw_realised"], 1, pct=True, sign=True))
    macro("SkRealObs", tex(f.loc["lgbm_obs", "skill_vs_rw_realised"], 1, pct=True, sign=True))
    # sensitivity
    s = sens_ls
    macro("SensGapLo", f"{100 * s[s['method'].isin(['lgbm_filled', 'ds_spo_struct', 'gfmc_pred'])]['gap_closed_vs_yday'].min():.0f}")
    macro("SensGapHi", f"{100 * s[s['method'].isin(['lgbm_filled', 'ds_spo_struct', 'gfmc_pred'])]['gap_closed_vs_yday'].max():.0f}")
    # extra descriptive numbers used in the text
    dd = st.dd
    macro("NCal", f"{dd.panel.T:,}".replace(",", "{,}"))
    macro("NNoReport", int((~dd.panel.mask.any(1)).sum()))
    ec = st.econ
    ps = np.where(dd.elig, dd.realised_price(ec)[:, :, 0], np.nan)
    rng = np.nanmax(ps, 1) - np.nanmin(ps, 1)
    macro("MedRange", tex(np.nanmedian(rng[dd.valid]), 0))
    cell = dd.elig[dd.valid][:, :, None] & np.ones((1, 1, 4), bool)
    macro("SilentShare", tex(float((~dd.obs[dd.valid] & cell).sum() / cell.sum()), 0, pct=True))
    po = pd.read_csv(R / "tomato" / "tables" / "per_origin.csv")
    pv = po.pivot(index="method", columns="origin", values="revenue")
    macro("KolarNearest", tex(pv.loc["nearest_today", "Kolar"], 0))
    macro("KolarLearned", tex(pv.loc["gfmc_pred", "Kolar"], 0))
    macro("KolarLoss", tex(pv.loc["gfmc_pred", "Kolar"] - pv.loc["nearest_today", "Kolar"], 0))
    au = auc[auc["fold"].astype(str) == "all"].set_index("method")["auc"]
    macro("AucStruct", f"{au.loc['ds_spo_struct']:.2f}")
    macro("AucGfmc", f"{au.loc['gfmc_pred']:.2f}")
    ab = pd.read_csv(R / "tomato" / "tables" / "report_auc_baselines.csv").set_index("method")["auc"]
    macro("AucOwn", f"{ab.iloc[0]:.2f}")
    macro("MeanTrain", f"{int(np.mean([len(pl.train_idx) for pl in st.plans.values()])):,}".replace(",", "{,}"))
    macro("BlockLo", int(min(len(pl.test_idx) for pl in st.plans.values())))
    macro("BlockHi", int(max(len(pl.test_idx) for pl in st.plans.values())))
    # data
    macro("DecisionDays", f"{int(st.dd.valid.sum()):,}".replace(",", "{,}"))
    macro("AvgReporting", f"{st.dd.panel.mask.sum(1).mean():.1f}")
    lines = [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in MACROS.items()]
    (out / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "papers" / "IEEE_Access"))
    a = ap.parse_args()
    figs, tabs = Path(a.out) / "figures", Path(a.out) / "tables"
    figs.mkdir(parents=True, exist_ok=True)
    tabs.mkdir(parents=True, exist_ok=True)

    hist, _ = loader.load_history()
    daily, _ = loader.load_daily_reports()
    st = Study("Tomato")
    pan = st.dd.panel
    T = R / "tomato" / "tables"
    main_t = pd.read_csv(T / "main.csv")
    comp = pd.read_csv(T / "comparisons.csv")
    floors = pd.read_csv(T / "floors.csv")
    fc = pd.read_csv(T / "forecast_accuracy.csv")
    auc = pd.read_csv(T / "report_auc.csv")
    sens = pd.read_csv(T / "sensitivity.csv")
    lk = pd.read_csv(R / "tomato" / "leakage" / "summary.csv")
    se = pd.read_csv(R / "tomato" / "leakage" / "future_sensitivity.csv")
    sil = {"rep": pd.read_csv(R / "tomato" / "silence" / "reporting_per_fold_horizon.csv"),
           "ret": pd.read_csv(R / "tomato" / "silence" / "returns_per_fold.csv")}
    crops = []
    for c, k in (("tomato", "Tomato (12)"), ("onion", "Onion (4)"), ("potato", "Potato (3)")):
        crops.append(({"main": pd.read_csv(R / c / "tables" / "main.csv"), "comp": pd.read_csv(R / c / "tables" / "comparisons.csv")}, k))

    fr = st.floor_run("gfmc_pred")
    trace = {"dates": fr["dates"], "alpha_t": fr["alpha_t"], "floor": fr["floor"], "rev": fr["outcome"].revenue}

    fig_arch(figs)
    fig_data(figs, hist, daily, pan)
    fig_leak(figs, lk, se)
    fig_decision(figs, st, main_t)
    fig_effects(figs, comp, {})
    fig_decouple(figs, main_t, fc)
    fig_floor(figs, floors, trace)
    fig_sens(figs, sens)
    tables(tabs, st, pan, hist, main_t, comp, floors, lk, sil, fc, crops)
    numbers(tabs, st, main_t, comp, floors, lk, sil, [(crops[1][0], "Onion"), (crops[2][0], "Potato")], fc, auc, fr, sens)
    print("wrote", len(list(figs.glob("*.pdf"))), "figures,", len(list(tabs.glob("*.tex"))), "tables to", a.out)


if __name__ == "__main__":
    main()
