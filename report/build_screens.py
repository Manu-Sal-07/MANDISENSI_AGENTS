"""
Trim the captured screenshots (figures/sys_*, ins_*) to presentable crops and write chapters/sec_screens.tex, the walkthrough section of Chapter 5.

    python report/build_screens.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
OUT = HERE / "chapters" / "sec_screens.tex"


def save(img: Image.Image, name: str) -> str:
    img.convert("RGB").save(FIG / name, optimize=True)
    return f"figures/{name}"


def crop_plain(src: str, name: str, y0: int, h: int) -> str:
    im = Image.open(FIG / src).convert("RGB")
    return save(im.crop((0, y0, im.width, min(im.height, y0 + h))), name)


def crop_tool(src: str, name: str, h: int = 1080) -> str:
    """Bottom-sheet screenshots: keep the sheet, drop the blurred page behind it."""
    im = Image.open(FIG / src).convert("RGB")
    a = np.asarray(im.convert("L"))
    white = (a > 238).mean(axis=1)
    top = 0
    for y in range(160, a.shape[0] - 40):
        if white[y: y + 30].min() > 0.80:
            top = max(0, y - 6)
            break
    head = im.crop((0, 0, im.width, 110))  # app header strip keeps the context
    body = im.crop((0, top, im.width, min(im.height, top + h)))
    out = Image.new("RGB", (im.width, head.height + body.height), "white")
    out.paste(head, (0, 0))
    out.paste(body, (0, head.height))
    return save(out, name)


FARMER = {
    "home": ("sys_farmer_home.png", "Home", 0, 1150),
    "prices": ("sys_farmer_prices.png", "Prices", 0, 1150),
    "mandi": ("sys_farmer_mandi.png", "Mandi", 0, 1150),
    "sellplan": ("sys_farmer_sellplan.png", "Plan", 0, 1150),
    "mymoney": ("sys_farmer_mymoney.png", "Money", 0, 1150),
    "tools": ("sys_farmer_tools.png", "Tools", 0, 1150),
    "accuracy": ("sys_farmer_accuracy.png", "Accuracy", 0, 1150),
    "evidence": ("sys_farmer_evidence.png", "Evidence", 0, 1150),
    "evidence_b": ("sys_farmer_evidence_b.png", "Evidence2", 0, 1150),
}
TOOLS = ["besplace", "fairprice", "harvest", "holdorsell", "lastyear", "wheretosell", "supply", "record", "truck", "plant", "alerts"]

TRIPLE = r"""
\begin{figure}[!t]
\centering
%s
\caption{%s}
\label{%s}
\end{figure}
"""


def minis(files: list[str], subs: list[str], h: str = "9.0cm") -> str:
    cells = []
    for f, sub in zip(files, subs):
        cells.append(r"\begin{minipage}[t]{0.485\textwidth}\centering\fbox{\includegraphics[width=0.94\linewidth,height=%s,keepaspectratio]{%s}}\\[1mm]{\footnotesize %s}\end{minipage}" % (h, f, sub))
    rows = ["\\hfill\n".join(cells[i:i + 2]) if len(cells[i:i + 2]) == 2 else "\\hfill\n".join(cells[i:i + 1]) for i in range(0, len(cells), 2)]
    rows = [r if "hfill" in r else "\\centering " + r for r in rows]
    return "\n\\medskip\n".join(rows)


def triple(label: str, files: list[str], subs: list[str], caption: str, h: str = "9.0cm") -> str:
    return TRIPLE % (minis(files, subs, h), caption, label)


def single(label: str, f: str, caption: str, w: str = "0.96\\textwidth") -> str:
    return (r"\begin{figure}[!t]" "\n" r"\centering" "\n" r"\fbox{\includegraphics[width=%s]{%s}}" "\n" r"\caption{%s}" "\n" r"\label{%s}" "\n" r"\end{figure}" "\n") % (w, f, caption, label)


def main() -> None:
    F = {k: crop_plain(v[0], f"shot_f_{k}.png", v[2], v[3]) for k, v in FARMER.items()}
    T = {k: crop_tool(f"sys_tool_{k}.png", f"shot_t_{k}.png") for k in TOOLS}
    W = {}
    for k, h in [("spreads", 1200), ("mcdesk", 1200), ("shock", 1200), ("gap", 1200), ("transmission", 1200), ("volatility", 1200), ("scenarios", 1200), ("analogs", 1200),
                 ("forward", 1200), ("positions", 1200), ("floormon", 1200), ("audit", 1200), ("council", 1200), ("explorer", 1200), ("aibrief", 1200), ("lab", 1200),
                 ("terminal", 1200), ("trader", 1200), ("tradertools", 1200)]:
        W[k] = crop_plain(f"sys_trader_{k}.png", f"shot_w_{k}.png", 0, h)
    W["crowd"] = crop_plain("ins_trader_crowd-simulator.png", "shot_w_crowd.png", 0, 1200)
    W["repval"] = crop_plain("ins_trader_reporting-value.png", "shot_w_repval.png", 0, 1200)
    W["docs"] = crop_plain("sys_api_docs.png", "shot_w_docs.png", 0, 1200)

    s = []
    s.append(r"""\section{System Walkthrough with Screenshots}
\label{sec:screens}

This section shows the running system. Every figure is a screenshot of the web application served from the stored data of the final system (market prices up to 26 October 2026), captured by a script (\texttt{report/capture\_system.py}) driving a headless browser, so the figures can be regenerated and are not edited. The farmer interface is shown at phone width because that is how most farmers will use it; the trader desk is shown at desktop width. Prices are in rupees per quintal unless stated, and every price on screen carries the date it was reported.

\subsection{Farmer interface}
The farmer interface is built around a single question, ``what is my crop worth today, and where should I sell it?''. It has a language switch (English, Kannada, Hindi), a district selector and a bottom navigation bar with Home, Prices and Tools.
""")
    s.append(triple("fig:sc-farmer1", [F["home"], F["prices"], F["mandi"]], ["(a) Home", "(b) Prices", "(c) One mandi"],
                    "Farmer pages. (a) The home page opens with a plain question, a search box that answers in sentences, and a ticker of the latest prices. (b) The prices page lists the crops with the latest quote, the change over the week and a sparkline. (c) A mandi page shows what each crop fetched there at the latest sale and how many quintals arrived."))
    s.append(r"""The home page (Figure~\ref{fig:sc-farmer1}a) deliberately carries no table: the first thing a farmer sees is the question and a box in which to type one in ordinary words. The prices page (b) shows the quote for each crop together with the date of the last report, so a stale price is never presented as today's. The mandi page (c) is the farmer-side view of one market and links to the plan for selling there.
""")
    s.append(triple("fig:sc-farmer2", [F["sellplan"], F["mymoney"], F["tools"]], ["(a) Plan my sale", "(b) My money", "(c) Farmer tools"],
                    "(a) The sale plan states one recommendation, the amount expected after transport and spoilage, and the day to go. (b) ``My Money'' compares the plans the farmer followed with what the markets recorded; it works on the device only. (c) The tool launcher opens each tool as a sheet over the page."))
    s.append(r"""The sale plan (Figure~\ref{fig:sc-farmer2}a) is the product's central screen. It names one market and one day, shows the amount expected per quintal after the cost of moving the crop, and shows the figure the farmer \emph{can count on at least}, which is the revenue floor of Section~\ref{sec:floors}. ``My Money'' (b) keeps the plans on the farmer's phone, so no account or personal data reach the server. The launcher (c) lists the eleven tools whose screens follow.
""")
    s.append(triple("fig:sc-farmer3", [F["accuracy"], F["evidence"], F["evidence_b"]], ["(a) How accurate are we?", "(b) How we know this works", "(c) What did not work"],
                    "The honesty pages. (a) Hit rates by crop and market, on days the system had not seen. (b) The replay: what the method earns against simple alternatives, in rupees, with the seed-to-seed spread. (c) The negative results are listed beside the positive ones."))
    s.append(r"""Three pages exist only to let a reader check the system. The accuracy page (Figure~\ref{fig:sc-farmer3}a) reports, per crop and market, how often the advice held on days the system had not seen. The evidence page (b) reproduces the main comparison of Chapter~\ref{ch:results} in plain words and in rupees, and (c) lists what did not help. A product that shows its misses is easier to trust than one that does not.
""")
    s.append(r"\subsection{Farmer tools}" "\n" r"Each tool opens as a sheet over the page and answers one question. The sheets below are captured with the sheet in its resting state; the blurred page behind each sheet is cropped away." "\n")
    groups = [
        (["besplace", "fairprice", "harvest"], ["(a) Best place and day", "(b) Fair price check", "(c) My harvest in rupees"],
         "fig:sc-tools1", "Selling tools. (a) The recommended market with expected and guaranteed amounts, options to change the vehicle and the confidence, and the next best choices. (b) A check of whether the price a trader offered is fair. (c) The expected value of the crop on each day ahead, after spoilage.",
         r"The Best Place and Day to Sell sheet (Figure~\ref{fig:sc-tools1}a) asks for the district, the quantity, the vehicle and the confidence level (80, 90 or 95\%), and returns the same recommendation as the service of Section~\ref{sec:service-app}, with the cost arithmetic one tap away. The fair-price check (b) takes the offer a trader made and places it against the distribution of recent prices. The harvest sheet (c) lays the next days side by side as a bar for each, with the expected net value, so the farmer sees what waiting costs."),
        (["holdorsell", "lastyear", "wheretosell"], ["(a) Hold or sell", "(b) This time last year", "(c) Where to sell"],
         "fig:sc-tools2", "Timing and location tools. (a) A hold-or-sell call that weighs spoilage against the expected price gain. (b) Today's price against the same date last year and the seasonal norm. (c) Nearby markets ranked by price after transport.",
         r"Hold or Sell (Figure~\ref{fig:sc-tools2}a) is built for the perishable case: it states the cost of waiting a day, so that ``wait'' is never the free option it appears to be. The seasonal sheet (b) gives context, not a forecast, and is labelled so. The ranking (c) lists markets with distance, gross price and net price per quintal under an assumed transport cost that the farmer can change."),
        (["supply", "record", "truck"], ["(a) Supply signal", "(b) Did we get it right?", "(c) Truck sharing"],
         "fig:sc-tools3", "Context and sharing tools. (a) Arrivals against the usual level. (b) The system's own scorecard of resolved calls. (c) A board for splitting a truck to a market.",
         r"The supply signal (Figure~\ref{fig:sc-tools3}a) reports whether arrivals are unusually high or low, since a glut lowers price. The scorecard (b) is an honest counter: when too few calls have resolved it says so and withholds the rate. The truck-sharing board (c) is a prototype that lets a farmer post a trip so that others can share the transport cost."),
        (["plant", "alerts"], ["(a) What to plant next", "(b) Price alerts"],
         "fig:sc-tools4", "(a) Seasonal patterns by crop for a chosen harvest month, from past years. (b) A price alert that notifies the farmer when a crop reaches a chosen price.",
         r"What to Plant Next (Figure~\ref{fig:sc-tools4}a) is explicitly historical: it shows how each crop has behaved in the chosen month in previous years and does not forecast the coming season. The alert sheet (b) is the entry point for the Telegram digest of Section~\ref{sec:digest-method}."),
    ]
    for ks, subs, lab, cap, txt in groups:
        n = len(ks)
        fig = triple(lab, [T[k] for k in ks], subs, cap, "9.0cm")
        s.append(fig)
        s.append(txt + "\n")
    s.append(r"""
\subsection{Advice that can be checked}
The three panels of Figure~\ref{fig:ui-insight} (Section~\ref{sec:insight-method}) sit inside the Best Place sheet. They show the arithmetic behind the choice, what changes if the farmer's costs differ, and how the advice would have done on days it had not seen. The morning digest of Section~\ref{sec:digest-method} is the same advice delivered as a message.

\subsection{Trader desk}
The trader desk is a set of analytical tools for buyers and for the project's own examination of its method. It is laid out for a wide screen.
""")
    wdesc = [
        ("trader", "Trader home: the day's key signals and entry points to the tools below.", "The trader home page gathers the day's signals, such as the largest price gaps between markets, supply shocks and the status of the advice, and links each to its tool."),
        ("tradertools", "The trader tools index.", "The index lists every analytical tool with a one-line statement of the question it answers."),
        ("spreads", "Spreads between markets for one commodity.", "The spread tool shows the price gap between pairs of markets after transport, with the number of days each gap has lasted. A gap that persists is a signal of a market that is slow to clear."),
        ("mcdesk", "The market-choice desk: the model's recommended market per day and the revenue floor.", "This is the technical view of the recommendation of Section~\\ref{sec:floors}: the chosen market, the expected and floor revenue, the alternatives and the model that produced them."),
        ("shock", "The shock desk: unusual price moves, with the markets affected.", "The desk lists price moves that are unusual relative to a rolling baseline and the markets where they appear. It feeds the shock episodes used for the transmission test of Section~\\ref{sec:spill-method}."),
        ("gap", "Gap arbitrage between mandis.", "The tool pairs a high-price and a low-price market, deducts transport and shrinkage, and shows whether a gap is worth acting on."),
        ("transmission", "Cross-commodity transmission.", "The transmission page shows the estimated response of one crop to a shock in another. When the evidence is too thin the page says so and shows no number, which is the withholding behaviour described in Section~\\ref{sec:transmission}."),
        ("volatility", "Price volatility by commodity and market.", "Rolling volatility of each series, which the farmer pages translate into a plain warning when a price is unusually unsettled."),
        ("scenarios", "Scenario analysis for the revenue of a sale plan.", "The tool changes transport cost, shrinkage and price in turn and shows how the recommended choice and its revenue respond."),
        ("analogs", "Analog days: past days that resembled today.", "The page finds earlier days with a similar price pattern and shows what followed, as an aid to judgement and not as a forecast."),
        ("forward", "Forward price view.", "A forecast with its interval for the coming days, with the forecasting model named on the page."),
        ("positions", "Positions: the sales a trader is tracking.", "A small ledger of intended sales with their marked-to-market value."),
        ("floormon", "Floor monitor: how often the revenue floor has held.", "The monitor tracks, day by day, whether realised revenue stayed above the stated floor and shows the running violation rate against its target, so a drift in calibration is visible."),
        ("audit", "Forecast audit.", "The audit compares each forecaster with the naive predictor on the days it was used and shows where it adds nothing."),
        ("council", "Agent council: specialist forecasters and their weights.", "The council page shows the specialist forecasters and the weight each currently carries, the object of Section~\\ref{sec:architecture}."),
        ("explorer", "Market explorer: any crop, any market, any period.", "The explorer lets a user chart raw reported prices and arrivals, with gaps in reporting shown as gaps."),
        ("aibrief", "The AI brief: a written summary checked against the evidence.", "The brief is written by the language model of Section~\\ref{sec:llm} and every figure in it is checked against the evidence before it is shown. A brief that fails the check is discarded and the page falls back to a plain summary."),
        ("lab", "Intelligence lab: experiment summaries.", "The lab page presents the experiment results of Chapter~\\ref{ch:results} interactively."),
        ("terminal", "Terminal view: dense prices for desk use.", "A compact table of the latest price per market, intended to stay open beside other work."),
        ("crowd", "Crowd simulator: what happens when many farmers follow the same advice.", "The simulator raises the share of farmers following the advice and shows the net revenue under four policies, using a stated price flexibility (Section~\\ref{sec:insight-method})."),
        ("repval", "Reporting value (silence tax): what a market's silence costs.", "The page estimates, per mandi, the revenue lost on days when a market did not report, which is the silence tax of Section~\\ref{sec:insight-method}."),
        ("docs", "The interactive API documentation.", "Every endpoint is documented automatically from the code, with a form to try it; the service is described in Section~\\ref{sec:service-app}."),
    ]
    for i in range(0, len(wdesc), 2):
        grp = wdesc[i:i + 2]
        cells = []
        for j, (k, cap, txt) in enumerate(grp):
            letter = "ab"[j]
            cells.append(r"\fbox{\includegraphics[width=0.93\linewidth]{%s}}\\[0.5mm]{\footnotesize (%s) %s}" % (W[k], letter, cap.rstrip(".")))
        caption = " ".join(f"({'ab'[j]}) {c.rstrip('.')}." for j, (_, c, _) in enumerate(grp))
        s.append("\\begin{figure}[!t]\n\\centering\n" + "\n\\medskip\n".join(cells) + "\n\\caption{" + caption + "}\n\\label{fig:sc-w-" + grp[0][0] + "}\n\\end{figure}\n")
        for _, _, txt in grp:
            s.append(txt + "\n")
        if False:
            s.append("\\clearpage\n")
    OUT.write_text("\n".join(s), encoding="utf-8")
    print("wrote", OUT, len(s))


if __name__ == "__main__":
    main()
