"""
Tables, figures and number macros for the insight features and the daily digest, from the served engines and the ingested panel.

    python report/build_insight_assets.py

Writes report/generated/tab_{track,silence,crowd,crowdb,breakdown,whatif}.tex, insight_numbers.tex and
report/figures/fig_{track,silence,crowd}.png. Run after `python scripts/build_track_record.py`.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "report"))

import build_assets as B  # noqa: E402
from mandisense_ai.market_choice import insights, service  # noqa: E402

FIG = ROOT / "report" / "figures"
CROPS = ["tomato", "onion", "potato", "ginger"]
M: list[str] = []


def macro(name: str, value) -> None:
    M.append(rf"\newcommand{{\{name}}}{{{value}}}")


REPL = {"₹": "Rs ", "•": "*", "→": "->", "—": "-", "–": "-", "×": "x", "✅": "[ok]", "⚠️": "[!]", "⚠": "[!]", "🌾": "", "🗓": "", "≥": ">=", "≤": "<=", "−": "-", "’": "'", "“": '"', "”": '"'}


def excerpt(src: Path, first: int, last: int, name: str) -> None:
    """A listing source for the appendix: the given lines, with characters pdflatex's listings cannot print replaced by ASCII."""
    lines = src.read_text(encoding="utf-8").splitlines()[first - 1:last]
    text = "\n".join(lines)
    for k, v in REPL.items():
        text = text.replace(k, v)
    text = "".join(ch if ord(ch) < 128 else f"\\u{ord(ch):04x}" for ch in text)
    (ROOT / "report" / "generated" / name).write_text(text + "\n", encoding="utf-8")


def rs(x, d=0) -> str:
    return B.num(x, d)


def main() -> None:
    origin = service.resolve_origin("kolar", None, None, None)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})

    # ---- track record
    tr = {c: insights.track_record(c) for c in CROPS}
    rows = []
    for c in CROPS:
        a = tr[c]["all"]
        n, h = a["vs_nearest"], a["vs_highest_yesterday"]
        rows.append([c.capitalize(), a["days"], f"{100 * n['win']:.0f} / {100 * n['tie']:.0f} / {100 * n['loss']:.0f}", f"{n['mean']:+,.0f}",
                     f"{100 * h['win']:.0f} / {100 * h['tie']:.0f} / {100 * h['loss']:.0f}", f"{h['mean']:+,.0f}", f"{100 * a['floor_held_share']:.0f}"])
    B.table(["Crop", "Days", "vs nearest: win / tie / loss (\\%)", "Mean gain (Rs/q)", "vs yesterday's best: win / tie / loss (\\%)", "Mean gain (Rs/q)", "Floor held (\\%)"],
            [[("@@" + B.esc(x)) for x in r] for r in rows], "|l|c|c|c|c|c|c|", "tab_track")
    for c in CROPS:
        macro(f"Floor{c.capitalize()}", f"{100 * tr[c]['all']['floor_held_share']:.0f}")
    from mandisense_ai.market_choice.engine import ENGINE

    for c in CROPS:
        bt = ENGINE.meta(c)["backtest"]
        macro(f"Adapt{c.capitalize()}", f"{100 * bt['floor_violation_adaptive']['0.10']:.1f}")
        macro(f"Static{c.capitalize()}", f"{100 * bt['floor_violation_static_out_of_sample']['0.10']:.1f}")
    rows = [[c.capitalize(), f"{100 * ENGINE.meta(c)['backtest']['floor_violation_adaptive']['0.10']:.1f}",
             f"{100 * ENGINE.meta(c)['backtest']['floor_violation_static_out_of_sample']['0.10']:.1f}", f"{100 - 100 * tr[c]['all']['floor_held_share']:.0f}"] for c in CROPS]
    B.table(["Crop", "Served rule, 330-day back-test (\\%)", "Static multiplier, out of sample (\\%)", "Track-record replay (\\%)"],
            [[("@@" + (x if "\\" in x else B.esc(x))) for x in r] for r in rows], "|l|c|c|c|", "tab_floorcmp")
    macro("TrackDays", tr["tomato"]["all"]["days"])
    macro("TrackFrom", tr["tomato"]["window"][0])
    macro("TrackTo", tr["tomato"]["window"][1])

    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    for c, col in zip(CROPS, ["#dc2626", "#2563eb", "#16a34a", "#d97706"]):
        d = tr[c]["days"]
        cum = np.cumsum([x["recommended"] - x["nearest"] for x in d]) / (np.arange(len(d)) + 1)
        ax.plot(range(len(d)), cum, label=c.capitalize(), color=col, lw=1.6)
    ax.set_xlabel("Out-of-sample day")
    ax.set_ylabel("Running mean gain over\nnearest mandi, Rs per quintal")
    ax.legend(frameon=False, fontsize=8, ncol=4)
    plt.tight_layout()
    plt.savefig(FIG / "fig_track.png", dpi=170)
    plt.close()

    # ---- silence tax (tomato)
    rv = insights.reporting_value("tomato")
    rows = [[r["name"], f"{100 * r['reported_share']:.0f}", f"{100 * r['silent_share_open_days']:.0f}", ", ".join(r["closed_weekdays"]) or "none",
             f"{r['worst_open_weekday']} ({100 * r['worst_open_weekday_silent']:.0f}\\%)", f"{rs(r['expected_loss_per_q'])} ({r['expected_loss_pct']}\\%)"]
            for r in rv["mandis"][:8]]
    B.table(["Mandi", "Reported (\\%)", "Surprise silence (\\%)", "Known closed", "Worst other day", "Tax, Rs/q (\\% of price)"],
            [[("@@" + (x if "\\" in x else B.esc(x))) for x in r] for r in rows], "|l|c|c|l|l|r|", "tab_silence")
    top = rv["mandis"][0]
    macro("SilenceTopName", B.esc(top["name"]))
    macro("SilenceTopLoss", rs(top["expected_loss_per_q"]))
    macro("SilenceTopPct", top["expected_loss_pct"])
    macro("SilenceMean", rs(rv["mean_expected_loss_per_q"]))
    macro("SilenceMandis", len(rv["mandis"]))
    macro("ThursdayChik", f"{100 * next(r for r in rv['mandis'] if r['mandi_id'] == 'chikkaballapura_apmc')['silent_by_weekday'][3]:.0f}")

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    names = [r["name"].split(",")[0] for r in rv["mandis"]]
    mat = np.array([r["silent_by_weekday"] for r in rv["mandis"]])
    im = ax.imshow(mat, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    ax.set_yticks(range(len(names)), names, fontsize=7)
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="Share of days with no price")
    plt.tight_layout()
    plt.savefig(FIG / "fig_silence.png", dpi=170)
    plt.close()

    # ---- crowd (tomato, Kolar farmers, 10 quintals each)
    sizes = [1, 20, 200, 2000]
    cs = {n: insights.crowd("tomato", origin, n, 10.0) for n in sizes}
    rows = [[f"{n:,}", f"{rs(c['total_quintals'])}", rs(c["alone"]["net_per_q"]), rs(c["everyone_follows_best"]["net_per_q"]),
             f"{c['everyone_follows_best']['price_drop_pct']:.1f}", rs(c["everyone_goes_nearest"]["net_per_q"]), rs(c["coordinated"]["net_per_q"])]
            for n, c in cs.items()]
    B.table(["Farmers", "Quintals", "One alone", "All follow best", "Price drop at best yard (\\%)", "All go nearest", "Coordinated split"],
            [[("@@" + (x if "\\" in x else B.esc(x))) for x in r] for r in rows], "|r|r|r|r|c|r|r|", "tab_crowd")
    c200 = cs[200]
    macro("CrowdAlone", rs(c200["alone"]["net_per_q"]))
    macro("CrowdBest", rs(c200["everyone_follows_best"]["net_per_q"]))
    macro("CrowdDrop", f"{c200['everyone_follows_best']['price_drop_pct']:.1f}")
    macro("CrowdNearest", rs(c200["everyone_goes_nearest"]["net_per_q"]))
    macro("CrowdCoord", rs(c200["coordinated"]["net_per_q"]))
    macro("CrowdGain", rs(c200["gain_coordinated_vs_everyone_best_per_q"]))
    macro("CrowdYard", rs(c200["recommended_yard_daily_arrivals_q"]))
    macro("CrowdTotal", rs(c200["gain_total_rs"]))

    flexes = [0.0, 0.05, 0.115, 0.2, 0.3]
    cb = {b: insights.crowd("tomato", origin, 200, 10.0, flexibility=b) for b in flexes}
    rows = [[f"{b:.3f}", rs(c["everyone_follows_best"]["net_per_q"]), f"{c['everyone_follows_best']['price_drop_pct']:.1f}", rs(c["coordinated"]["net_per_q"]),
             rs(c["gain_coordinated_vs_everyone_best_per_q"])] for b, c in cb.items()]
    B.table(["Flexibility $b$", "All follow best", "Price drop (\\%)", "Coordinated", "Coordination gain"],
            [[("@@" + (x if "\\" in x or "$" in x else B.esc(x))) for x in r] for r in rows], "|c|r|c|r|r|", "tab_crowdb")

    ns = [1, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    sweep = {n: insights.crowd("tomato", origin, n, 10.0) for n in ns}
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ax.plot(ns, [sweep[n]["alone"]["net_per_q"] for n in ns], "--", color="#64748b", label="One farmer alone")
    ax.plot(ns, [sweep[n]["everyone_follows_best"]["net_per_q"] for n in ns], color="#dc2626", marker="o", ms=3, label="Everyone follows the best action")
    ax.plot(ns, [sweep[n]["everyone_goes_nearest"]["net_per_q"] for n in ns], color="#d97706", marker="o", ms=3, label="Everyone goes to the nearest mandi")
    ax.plot(ns, [sweep[n]["coordinated"]["net_per_q"] for n in ns], color="#16a34a", marker="o", ms=3, label="Coordinated split")
    ax.set_xscale("log")
    ax.set_xlabel("Farmers following the advice (10 quintals each)")
    ax.set_ylabel("Net revenue, Rs per quintal")
    ax.legend(frameon=False, fontsize=7.5)
    plt.tight_layout()
    plt.savefig(FIG / "fig_crowd.png", dpi=170)
    plt.close()

    # ---- breakdown and what-if (tomato, Kolar)
    bd = insights.breakdown("tomato", origin, 10)
    labels = {"recommended": "Advice", "nearest_today": "Nearest mandi, today", "highest_yesterday": "Highest price yesterday", "farm_gate": "Farm gate"}
    rows = []
    for k, v in bd["options"].items():
        o = v["option"]
        parts = {p["key"]: p["value"] for p in v["parts"]}
        where = "Farm gate" if o["kind"] == "farm_gate" else f"{o['mandi_name']}, {'today' if o['hold_days'] == 0 else '+%dd' % o['hold_days']}"
        rows.append([labels[k], where, rs(parts["price"]), rs(parts.get("fee", 0)), rs(parts.get("spoilage", 0)), rs(parts.get("transport", 0)),
                     rs(parts.get("handling", 0)) if "handling" in parts else rs(parts.get("farm_gate_discount", 0)), rs(v["net"])])
    B.table(["Option", "Where and when", "Price", "Fee", "Spoilage", "Transport", "Handling / gate discount", "Net"],
            [[("@@" + B.esc(x)) for x in r] for r in rows], "|l|l|r|r|r|r|r|r|", "tab_breakdown")

    scen = [("Standard costs (tempo, 3\\%/day spoilage)", {}), ("Very dear transport, Rs 3.0 per q-km", {"transport": 3.0}),
            ("Spoilage 5\\% a day", {"spoilage": 0.05}), ("Cannot wait (0 days)", {"max_hold": 0}), ("Cheap shared truck, Rs 0.35", {"transport": 0.35})]
    rows = []
    for name, kw in scen:
        s = insights.simulate("tomato", origin, 10, **kw)
        r = s["recommended"]
        where = "Farm gate" if r["kind"] == "farm_gate" else f"{r['mandi_name']}, {'today' if r['hold_days'] == 0 else '+%dd' % r['hold_days']}"
        rows.append([name, where, rs(r["expected_net_per_q"]), rs(r["floor_per_q"]), "yes" if s["changed"] else "no"])
    B.table(["Scenario (tomato, Kolar)", "Advice", "Net, Rs/q", "Floor, Rs/q", "Changed"], [[("@@" + (x if "\\" in x else B.esc(x))) for x in r] for r in rows],
            "|l|l|r|r|c|", "tab_whatif")
    base = insights.simulate("tomato", origin, 10)
    fl = base["sweeps"]["spoilage"]["flips"]
    macro("SpoilFlipAt", f"{100 * fl[0]['at']:.1f}" if fl else "none")
    macro("TransportFlips", len(base["sweeps"]["transport"]["flips"]))
    rec = base["recommended"]
    macro("AdvMandi", B.esc(rec["mandi_name"]))
    macro("AdvDays", rec["hold_days"])
    macro("AdvNet", rs(rec["expected_net_per_q"]))
    macro("AdvFloor", rs(rec["floor_per_q"]))
    near = bd["options"]["nearest_today"]
    macro("NearNet", rs(near["net"]))

    (ROOT / "report" / "generated" / "insight_numbers.tex").write_text("\n".join(M) + "\n", encoding="utf-8")
    # numbers the deck and the demo script quote
    facts = {"tomato_kolar": {"advice": rec, "nearest_net": near["net"]}, "crowd200": {k: c200[k] for k in ("alone", "everyone_follows_best", "everyone_goes_nearest", "coordinated")},
             "silence_top": rv["mandis"][:3], "track": {c: {"all": tr[c]["all"], "last60": tr[c]["last60"]} for c in CROPS}, "spoil_flip": fl[:1]}
    deck = {
        "track": {c: {"cum": [round(float(v), 1) for v in (np.cumsum([x["recommended"] - x["nearest"] for x in tr[c]["days"]]) / (np.arange(len(tr[c]["days"])) + 1))],
                      "all": tr[c]["all"], "last60": tr[c]["last60"]} for c in CROPS},
        "silence": [{k: r[k] for k in ("name", "reported_share", "silent_share_open_days", "closed_weekdays", "worst_open_weekday", "worst_open_weekday_silent", "expected_loss_per_q", "expected_loss_pct")}
                    for r in rv["mandis"]],
        "silence_mean": rv["mean_expected_loss_per_q"],
        "crowd": {"n": ns, "alone": [sweep[n]["alone"]["net_per_q"] for n in ns], "best": [sweep[n]["everyone_follows_best"]["net_per_q"] for n in ns],
                  "nearest": [sweep[n]["everyone_goes_nearest"]["net_per_q"] for n in ns], "coord": [sweep[n]["coordinated"]["net_per_q"] for n in ns],
                  "drop": [sweep[n]["everyone_follows_best"]["price_drop_pct"] for n in ns]},
        "crowd200": {"alone": c200["alone"]["net_per_q"], "best": c200["everyone_follows_best"]["net_per_q"], "nearest": c200["everyone_goes_nearest"]["net_per_q"],
                     "coord": c200["coordinated"]["net_per_q"], "drop": c200["everyone_follows_best"]["price_drop_pct"], "gain": c200["gain_coordinated_vs_everyone_best_per_q"],
                     "total": c200["gain_total_rs"], "yard": c200["recommended_yard_daily_arrivals_q"]},
        "breakdown": {k: {"where": ("Farm gate" if v["option"]["kind"] == "farm_gate" else v["option"]["mandi_name"]), "hold": v["option"]["hold_days"], "net": v["net"],
                          "parts": {p_["key"]: p_["value"] for p_ in v["parts"]}} for k, v in bd["options"].items()},
        "whatif": [{"name": n_, "advice": ("Farm gate" if r_["kind"] == "farm_gate" else r_["mandi_name"]), "hold": r_["hold_days"], "net": r_["expected_net_per_q"], "floor": r_["floor_per_q"]}
                   for n_, r_ in [(n_, insights.simulate("tomato", origin, 10, **kw)["recommended"]) for n_, kw in scen]],
        "spoil_flip": fl[0]["at"] if fl else None,
        "floor": {c: {"adaptive": ENGINE.meta(c)["backtest"]["floor_violation_adaptive"]["0.10"], "static": ENGINE.meta(c)["backtest"]["floor_violation_static_out_of_sample"]["0.10"],
                      "held": tr[c]["all"]["floor_held_share"]} for c in CROPS},
    }
    (ROOT / "report" / "generated" / "deck_data.json").write_text(json.dumps(deck, indent=1, default=str), encoding="utf-8")
    (ROOT / "report" / "generated" / "insight_facts.json").write_text(json.dumps(facts, indent=1, default=str), encoding="utf-8")
    excerpt(ROOT / "mandisense_ai" / "market_choice" / "insights.py", 196, 232, "code_crowd.txt")
    excerpt(ROOT / "mandisense_ai" / "notify" / "digest.py", 130, 168, "code_digest.txt")
    print("insight assets written")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
