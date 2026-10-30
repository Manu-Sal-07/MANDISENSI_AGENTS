"""
Build the Review-2 deck from the department template (PP2_Template_-_Review2.pptx).

    python report/build_deck.py

Every number comes from the same artefacts as the thesis (research/results, models/), so slides and report agree.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
TEMPLATE = ROOT.parent / "PP2_Template_-_Review2.pptx"
OUT = ROOT / "report" / "MandiSense_Review2_Final_v2.pptx"
FIG = ROOT / "report" / "figures"
RES = ROOT / "research" / "results"
MODELS = ROOT / "mandisense_ai" / "models"

NAVY, BLUE, MID, LIGHT, PALE = "1F2A44", "1F4E79", "2E75B6", "DCEBF5", "F1F7FB"
ORANGE, GREEN, RED, GREY, WHITE = "D9822B", "2E8B57", "C0392B", "5F6B7A", "FFFFFF"
CROPS = ["tomato", "onion", "potato", "ginger"]
FS = 1.22


def rgb(h): return RGBColor.from_string(h)


# ───────────────────────────────────────────────────────────── slide plumbing
def dup(prs, src):
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    rid = {}
    for r in src.part.rels.values():
        if r.reltype == RT.IMAGE:
            rid[r.rId] = new.part.relate_to(r.target_part, RT.IMAGE)
    tree = new.shapes._spTree
    for el in list(src.shapes._spTree)[2:]:
        c = copy.deepcopy(el)
        for node in c.iter():
            for k in list(node.attrib):
                if k.endswith("}embed") and node.attrib[k] in rid:
                    node.attrib[k] = rid[node.attrib[k]]
        tree.append(c)
    return new


def reorder(prs, order):
    lst = prs.slides._sldIdLst
    ids = list(lst)
    for e in ids:
        lst.remove(e)
    for i in order:
        lst.append(ids[i])


def keep_shape(sh):
    if sh.name in ("Rectangle 10", "object 8", "object 10", "Slide Number Placeholder 2", "TextBox 7"):
        return True
    return sh.shape_type == 13 and sh.left < Inches(1.0)


def drop(prs, slide):
    """Remove a slide completely (its entry and its package part)."""
    lst = prs.slides._sldIdLst
    sid = slide.slide_id
    for e in list(lst):
        if e.id == sid:
            prs.part.drop_rel(e.rId)
            lst.remove(e)
            break


def shape(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    raise KeyError(name)


def set_title(slide, text):
    sh = shape(slide, "object 8")
    p = sh.text_frame.paragraphs[0]
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    for extra in sh.text_frame.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def set_bullets(slide, items, x=1.1, y=1.9, w=19.8, h=3.0, size=26):
    """items: str or (lead, rest). Re-uses the template paragraph so bullets and spacing match."""
    sh = shape(slide, "Content Guidance")
    sh.left, sh.top, sh.width, sh.height = Inches(x), Inches(y), Inches(w), Inches(h)
    body = sh.text_frame._txBody
    paras = body.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}p")
    proto = copy.deepcopy(paras[0])
    for p in paras:
        body.remove(p)
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for it in items:
        lead, rest = (it if isinstance(it, tuple) else (None, it))
        p = copy.deepcopy(proto)
        runs = p.findall(A + "r")
        for r in runs[1:]:
            p.remove(r)
        r0 = runs[0]
        r0.find(A + "rPr").set("sz", str(size * 100))
        if lead:
            r0.find(A + "t").text = lead + " "
            r0.find(A + "rPr").set("b", "1")
            r1 = copy.deepcopy(r0)
            r1.find(A + "rPr").attrib.pop("b", None)
            r1.find(A + "t").text = rest
            r0.addnext(r1)
        else:
            r0.find(A + "t").text = rest
        body.append(p)
    return sh


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ───────────────────────────────────────────────────────────── drawing helpers
def text(slide, x, y, w, h, content, size=20, bold=False, color=NAVY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         fill=None, line=None, shape_type=None, italic=False, margin=0.08, font="Calibri"):
    if fill or line or shape_type:
        sh = slide.shapes.add_shape(shape_type or MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line); sh.line.width = Pt(1.5)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
    else:
        sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    lines = content if isinstance(content, list) else [content]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        segs = ln if isinstance(ln, list) else [ln]
        for seg in segs:
            t, b = (seg if isinstance(seg, tuple) else (seg, bold))
            r = p.add_run()
            r.text = t
            r.font.size = Pt(round(size * FS)); r.font.bold = b; r.font.italic = italic
            r.font.color.rgb = rgb(color); r.font.name = font
    return sh


def card(slide, x, y, w, h, head, body, head_fill=BLUE, size=18, body_fill=PALE, head_h=0.62, head_size=20):
    text(slide, x, y, w, head_h, head, size=head_size, bold=True, color=WHITE, fill=head_fill, anchor=MSO_ANCHOR.MIDDLE, margin=0.15)
    return text(slide, x, y + head_h, w, h - head_h, body, size=size, fill=body_fill, margin=0.18, anchor=MSO_ANCHOR.TOP)


def stat(slide, x, y, w, h, big, small, color=BLUE):
    text(slide, x, y, w, h * 0.55, big, size=40, bold=True, color=color, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM, fill=PALE)
    text(slide, x, y + h * 0.55, w, h * 0.45, small, size=16, color=GREY, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP, fill=PALE)


def arrow(slide, x1, y1, x2, y2, color=GREY, width=2.25):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    ln.append(etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd", type="triangle"))
    return c


def table(slide, rows, x, y, w, col_w, row_h=0.55, size=18, head_size=None, head_fill=BLUE, zebra=True, bold_first_col=False, aligns=None, hl_rows=()):
    nr, nc = len(rows), len(rows[0])
    gs = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    tb = gs.table
    tot = sum(col_w)
    for j, cw in enumerate(col_w):
        tb.columns[j].width = Inches(w * cw / tot)
    for i in range(nr):
        tb.rows[i].height = Inches(row_h)
        for j in range(nc):
            c = tb.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            val = rows[i][j]
            color = NAVY
            if isinstance(val, tuple):
                val, color = val
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = (aligns[j] if aligns else PP_ALIGN.LEFT) if i else PP_ALIGN.CENTER
            r = p.add_run(); r.text = str(val)
            r.font.size = Pt(round((head_size or size) * FS)) if i == 0 else Pt(round(size * FS))
            r.font.name = "Calibri"
            r.font.bold = (i == 0) or (bold_first_col and j == 0) or (i in hl_rows)
            r.font.color.rgb = rgb(WHITE if i == 0 else color)
            c.fill.solid()
            c.fill.fore_color.rgb = rgb(head_fill if i == 0 else (LIGHT if i in hl_rows else (PALE if (zebra and i % 2 == 0) else WHITE)))
    return gs


def picture(slide, path, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


# ───────────────────────────────────────────────────────────── data
def load():
    d = {}
    for c in CROPS:
        t = RES / c / "tables"
        d[c] = {"main": pd.read_csv(t / "main.csv").set_index("method"), "cmp": pd.read_csv(t / "comparisons.csv"), "floors": pd.read_csv(t / "floors.csv"),
                "summary": json.loads((RES / c / "summary.json").read_text(encoding="utf-8"))}
    return d


def pages() -> int:
    try:
        out = subprocess.run(["pdfinfo", str(ROOT / "report" / "main.pdf")], capture_output=True, text=True).stdout
        return int([l for l in out.splitlines() if l.startswith("Pages")][0].split()[1])
    except Exception:
        return 0


def fmt(x, d=0, sign=False):
    s = f"{x:+,.{d}f}" if sign else f"{x:,.{d}f}"
    return s.replace("-", "−")


# ───────────────────────────────────────────────────────────── build
def main():
    PAGES = pages()
    D = load()
    prs = Presentation(str(TEMPLATE))
    S = list(prs.slides)
    t_title, t_toc = S[0], S[1]
    content = S[2:19]
    thanks = S[19]
    (s_intro, s_obj, s_meth, s_impl, s_tools, s_setup, s_res, s_bench, s_nov, s_opt, s_wbs, s_risk, s_rep, s_sdg, s_paper, s_conc, s_ref) = content

    # ---- 1 title
    box = shape(t_title, "Text Box 4")
    for p in box.text_frame.paragraphs:
        pass
    obj2 = shape(t_title, "object 2")
    obj2.top = obj2.top + Inches(0.9)
    for p in obj2.text_frame.paragraphs:
        for r in p.runs:
            t = r.text
            if "Teammate 1" in t: r.text = "Srijan C Vachadmath (1BM23CD060)"
            elif "Teammate 2" in t: r.text = "Manohara Salmani (1BM23CD035)"
            elif "Teammate 3" in t: r.text = "Shreejith Shah (1BM23CD057)"
            elif "Guide Name" in t: r.text = "Dr. Kalyan N"
    for p in box.text_frame.paragraphs:
        for r in p.runs:
            if "Project Title" in r.text:
                r.text = "MandiSense AI: Where and When to Sell, with Verified Revenue Floors"
                r.font.size = Pt(30)
    notes(t_title, "Review 2 of Project Work Phase 2. MandiSense AI recommends where and when a Kolar-belt farmer should sell, and states a revenue floor it has been tested to respect.")

    # ---- 3 intro
    set_title(s_intro, "Introduction and Problem Statement")
    set_bullets(s_intro, [
        ("Context:", "farmers in the Bengaluru–Kolar belt choose a mandi and a day with only yesterday's price. Kolar tomato ranged Rs 100–9,330 per quintal and was silent on 189 of 2,125 days."),
        ("Problem:", "choose (mandi, hold 0–3 days) or the farm gate to maximise net revenue, and state a floor that holds."),
        ("Gap:", "models are judged on forecast error, not decisions; reporting gaps are ignored; decompose-then-forecast gains are unaudited [1]–[6]."),
        ("Scope:", "tomato, onion, potato, ginger; Agmarknet only; offline evaluation. Garlic refused (one eligible mandi)."),
    ], w=10.6, h=7.6, size=24)
    picture(s_intro, FIG / "fig_intro_kolar_tomato.png", 12.0, 2.0, w=9.0)
    stat(s_intro, 12.0, 5.7, 2.85, 2.0, "63,524", "real Agmarknet records")
    stat(s_intro, 15.05, 5.7, 2.85, 2.0, "36,821", "mandi-days in the panel")
    stat(s_intro, 18.1, 5.7, 2.9, 2.0, "4 crops", "plus garlic refused", color=ORANGE)
    text(s_intro, 12.0, 8.1, 9.0, 2.7, [[("Why it matters: ", True), ("a farmer who gambles a harvest needs a minimum expected revenue, not just a forecast. Information frictions of exactly this kind measurably hurt small sellers [7], [8].", False)]], size=20, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_intro, "Recap of Review 1, kept short. The key idea: the question is a decision under uncertainty with missing data, not a forecasting question.")

    # ---- 4 objectives
    set_title(s_obj, "Objectives")
    set_bullets(s_obj, [("Status:", "7 met · 1 partly met (floors) · 1 null result (spillover) · 1 built and tested (digest, shown live today).")], h=0.9, size=24)
    rows = [["#", "Objective (approved scope)", "Status", "Evidence"],
            ["1", "Real-data panel, ≥30,000 mandi-days, exclusions recorded", ("Met", GREEN), "36,821 mandi-days; 63,524 records"],
            ["2", "Revenue formulation + market-choice model; ≥500 held-out days per crop", ("Met", GREEN), "511–963 scored days per crop"],
            ["3", "Test label and loss effects with paired tests", ("Met", GREEN), "Realised labels: −87 to −157 Rs/q; SPO+ no gain"],
            ["4", "Floor violation within 2 points of nominal 10%", ("Partly", ORANGE), "Tomato 9.0%, ginger 10.5%; onion 6.3%, potato 6.9%"],
            ["5", "FastAPI + trilingual app, tests, reproducible pipeline", ("Met", GREEN), "669 backend + 11 web tests; one-command pipeline"],
            ["6", "Audit decompose-then-forecast leakage; foundation-model baseline", ("Met", GREEN), "+27…62% skill → −15…−1% when causal"],
            ["7", "LLM decision intelligence, grounded and verified", ("Met", GREEN), "Judge caught 9/9 corrupted; 30 unit tests"],
            ["8", "Cross-commodity spillover with FDR control", ("Null result", RED), "0 of 40 edges published: no shock episodes"],
            ["9", "Inspectable advice: breakdown, what-if, track record, silence tax, crowd", ("Met", GREEN), "Parts add up to net; replay 165 days; 11 tests"],
            ["10", "Dated morning digest on a free channel (Telegram), EN/KN/HI", ("Built, tested", ORANGE), "8 tests; live demo today; no farmer pilot"]]
    table(s_obj, rows, 1.1, 2.55, 19.8, [0.5, 9, 2.4, 8], row_h=0.78, size=17, aligns=[PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT])
    notes(s_obj, "Each objective is mapped to the result that demonstrates it. Objective 4 is only partly met because onion and potato floors were more cautious than needed. Objective 8 is met as engineering; it publishes no transmission result.")

    # ---- 5 methodology & architecture
    set_title(s_meth, "Proposed Methodology and System Architecture")
    set_bullets(s_meth, [
        ("Idea:", "train on what the farmer would actually receive (price net of transport, shrinkage and silent markets), not on the posted price."),
        ("Action:", "(mandi, hold 0–3 days) or farm gate; recommendation = best guaranteed revenue, with an adaptive conformal floor."),
        ("Rejected:", "predict-then-optimise on posted prices and decompose-then-forecast hybrids (they never see a silent market, and leak the future)."),
    ], h=3.7, size=24)
    bx = [(1.1, "Agmarknet\nexports"), (4.0, "Clean + audit\nloader, checks"), (6.9, "Market panel,\nobservation store")]
    ytop = 6.0
    for x, lab in bx:
        text(s_meth, x, ytop, 2.5, 1.2, lab.split("\n"), size=18, bold=True, color=NAVY, fill=LIGHT, line=MID, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    arrow(s_meth, 3.6, ytop + 0.6, 4.0, ytop + 0.6); arrow(s_meth, 6.5, ytop + 0.6, 6.9, ytop + 0.6)
    eng = [(10.4, 5.0, "Market-choice engines\n+ conformal floors"), (10.4, 6.5, "Forecasters\n+ specialist council"), (10.4, 8.0, "Shock study\n+ spillover")]
    for x, y, lab in eng:
        text(s_meth, x, y, 3.3, 1.2, lab.split("\n"), size=18, bold=True, fill=LIGHT, line=MID, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
        arrow(s_meth, 9.4, ytop + 0.6, 10.4, y + 0.6, color=GREY)
        arrow(s_meth, 13.7, y + 0.6, 14.6, ytop + 0.6 + 0.3, color=GREY)
    text(s_meth, 14.6, ytop - 0.15, 2.9, 1.5, ["FastAPI service", "farmer · trader · chat"], size=18, bold=True, fill=BLUE, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s_meth, 18.1, ytop - 0.15, 2.8, 1.5, ["Next.js app", "EN · KN · HI"], size=18, bold=True, fill=NAVY, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    arrow(s_meth, 17.5, ytop + 0.6, 18.1, ytop + 0.6)
    text(s_meth, 14.6, 8.3, 6.3, 1.4, ["Language layer: decision-intelligence briefs,", "explanation writer + independent judge"], size=17, bold=True, fill=ORANGE, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    arrow(s_meth, 17.7, 8.3, 16.9, 7.55, color=ORANGE)
    text(s_meth, 1.1, 9.9, 13.0, 1.2, "Data layer → model layer → service layer (engines + five insight features) → language layer → presentation. All results use real portal records; no synthetic data enter any result.", size=18, italic=True, color=GREY)
    text(s_meth, 14.6, 9.95, 6.3, 1.0, ["Telegram bot · 7 am digest"], size=17, bold=True, fill=GREEN, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    arrow(s_meth, 17.7, 9.95, 17.7, 9.75, color=GREEN)
    notes(s_meth, "Five layers. The distinctive choices: label = realised revenue, and the language model is a writer whose output is verified and may be discarded.")

    # ---- 5b formulation
    s_form = dup(prs, s_meth)
    for sh in list(s_form.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_form, "Key Formulation: Revenue, Loss and Verified Floor")
    eqs = [("Net revenue of action (m, k) from origin ℓ", "R(m,k | ℓ) = (1 − f)(1 − δ)ᵏ · P̃(m, t+k) − τ·ρ·d(ℓ,m) − c₀", "P̃ = P if market m reported on day t+k, else φ · P̄(t+k) (wasted trip); farm gate pays φ_g · P̄(t)"),
           ("Decision-focused loss (SPO+)", "L(r̂, r) = max_a (2r̂ₐ − rₐ) − 2r̂ₐ* + rₐ*", "non-negative, zero at the truth, upper-bounds regret; tested against squared error"),
           ("Guaranteed floor and adaptive level", "L = r̂ − q·σ̂ ;   αₜ₊₁ = αₜ + γ (α − 1[R < L])", "q = (1 − αₜ) quantile of past normalised scores; outcomes of a k-day hold are released only after the sale date")]
    y = 1.8
    for head, eq, note in eqs:
        text(s_form, 1.1, y, 12.4, 0.5, head, size=19, bold=True, color=BLUE)
        text(s_form, 1.1, y + 0.5, 12.4, 0.85, eq, size=24, bold=True, fill=PALE, anchor=MSO_ANCHOR.MIDDLE, margin=0.2, font="Cambria Math")
        text(s_form, 1.1, y + 1.4, 12.4, 0.9, note, size=17, color=GREY)
        y += 2.9
    rows = [["Sym.", "Meaning", "Default"],
            ["f", "market fee + commission", "4 %"], ["c₀", "handling per trip", "Rs 20"], ["τ", "transport, Rs per quintal-km", "0.35"],
            ["ρ", "road / great-circle distance", "1.3"], ["δ", "daily spoilage (tomato / onion / potato)", "3 / 0.8 / 0.4 %"],
            ["φ", "price discount if mandi silent", "0.85"], ["φ_g", "farm-gate discount", "0.80"], ["α, γ", "floor level, ACI step", "0.10, 0.01"]]
    table(s_form, rows, 14.0, 1.9, 6.9, [1.0, 3.8, 1.9], row_h=0.62, size=17, aligns=[PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.CENTER])
    text(s_form, 14.0, 7.7, 6.9, 2.9, [[("Parameters are scenario assumptions, not estimates. ", True), ("τ, δ and φ are swept at evaluation time; conclusions hold across all 10 settings per crop.", False)]], size=19, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_form, "Revenue is affine in the price vector, so SPO+ is exact for this problem. The floor is the best guaranteed revenue; outcomes feed the calibrator only after the sale date has passed.")

    # ---- 5c LLM + spillover method
    s_two = dup(prs, s_form)
    for sh in list(s_two.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_two, "Decision Intelligence and Cross-Commodity Spillover")
    card(s_two, 1.1, 1.9, 9.7, 8.4, "Objective 7: grounded decision briefs", [
        [("1. Evidence bundle: ", True), ("flat map of dotted keys (forecast.h5.point, market-choice, arrivals, spillover) + what was unavailable", False)],
        [("2. Provider fills a fixed schema: ", True), ("action BUY/SELL/HOLD/WAIT, confidence (may be INSUFFICIENT_EVIDENCE), factors that each cite an evidence key", False)],
        [("3. Grounding check: ", True), ("every figure within 1% of an evidence value, every key exists, no market named outside the evidence", False)],
        [("4. Never fails silently: ", True), ("failing provider → deterministic fallback; ungrounded brief served as grounded:false with issues listed", False)],
        [("Policy: ", True), ("a HOLD is overridden when spoilage outruns the expected gain", False)]], size=23)
    card(s_two, 11.2, 1.9, 9.7, 8.4, "Objective 8: spillover between crops", [
        [("Panel: ", True), ("weekly returns of 5 crops, 232 weeks, one reference market each", False)],
        [("Clean: ", True), ("remove first common factor (24.5% of variance) and calendar-month means so shared shocks are not read as transmission", False)],
        [("Episodes: ", True), ("source crop in squeeze or glut; onsets <4 weeks apart merged", False)],
        [("Effect: ", True), ("mean response of target over h = 1–4 weeks minus its unconditional baseline", False)],
        [("Inference: ", True), ("bootstrap over whole episodes (2,000 draws, 90%); Benjamini–Hochberg FDR 10% across 40 edges", False)],
        [("Gates: ", True), ("≥8 episodes, CI excludes 0, |effect| ≥ 1%; otherwise INSUFFICIENT_EVIDENCE", False)]], size=23, head_fill=ORANGE)
    notes(s_two, "Both services share one principle: publish a claim only when the evidence supports it, otherwise say so.")

    # ---- 6 implementation
    set_title(s_impl, "Implementation and System Integration")
    set_bullets(s_impl, [
        ("Integrated:", "one pipeline command runs 13 stages from raw exports to tests; API, web app, engines and language layer share one data store."),
        ("Manual:", "refreshing Agmarknet exports (download by hand); public deployment config exists but is not verified live."),
        ("Defects fixed:", "NumPy 2 broke pandas; fresh clone missed the observation store; hard deletion emptied trader pages; council weights summed above 1."),
    ], h=3.7, size=25)
    stages = ["world", "forecasts", "market\nchoice", "track\nrecord", "transmission", "shock", "spillover", "council", "research\nevidence", "results\ndoc", "tests"]
    x0, y0, w, h, gap = 1.1, 5.9, 1.6, 1.15, 0.16
    for i, st in enumerate(stages):
        xx = x0 + i * (w + gap)
        text(s_impl, xx, y0, w, h, st.split("\n"), size=15, bold=True, fill=LIGHT if i < len(stages) - 1 else GREEN, color=NAVY if i < len(stages) - 1 else WHITE, line=MID, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.03)
        if i < len(stages) - 1:
            arrow(s_impl, xx + w, y0 + h / 2, xx + w + gap, y0 + h / 2, width=2)
    text(s_impl, 1.1, 7.35, 19.8, 0.5, "scripts/pipeline.py: each stage has declared outputs; run alone, skipped, or dry-run (--list, --only, --skip, --dry-run)", size=17, italic=True, color=GREY)
    xcur = 1.1
    for fn in ("ui_farmer_home.png", "ui_market_choice.png", "ui_trader_hub.png"):
        pic = picture(s_impl, FIG / fn, xcur, 8.0, h=3.3)
        xcur += pic.width / 914400 + 0.35
    text(s_impl, 16.4, 8.0, 4.5, 3.3, [[("Endpoints: ", True), ("/v1/market-choice (+5 insight routes), /v1/farmer, /v1/trader, /v1/shock, /v1/council, /v1/spillover, /v1/intelligence, /v1/chat, /v1/notify", False)]], size=16, fill=PALE, margin=0.15, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_impl, "End-to-end flow. The live demonstration follows on the next slide; the screenshots here only show what the screens contain.")

    # ---- 6b demo plan
    s_demo = dup(prs, s_impl)
    for sh in list(s_demo.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_demo, "Live Demonstration Plan")
    steps = [("1", "Start the stack", "uvicorn api.main:app and npm run dev; open the farmer home in Kannada"),
             ("2", "Farmer: best place to sell", "recommendation with reasons, verified floor and evidence level"),
             ("3", "Trader: Market-Choice Desk", "per-crop engines, floor monitor, back-test gain over the heuristics"),
             ("4", "AI brief and chat", "grounded brief with cited factors; ask a question in Hindi"),
             ("5", "Shock desk and council", "evidence tiers shown honestly (suggestive, not robust)"),
             ("6", "Show the refusal", "garlic: the engine declines instead of guessing")]
    for i, (n, head, body) in enumerate(steps):
        col, row = i % 2, i // 2
        x, y = 1.1 + col * 10.0, 1.9 + row * 2.2
        text(s_demo, x, y, 0.9, 1.9, n, size=36, bold=True, color=WHITE, fill=BLUE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        text(s_demo, x + 0.9, y, 8.8, 1.9, [[(head, True)], [(body, False)]], size=20, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    text(s_demo, 1.1, 8.6, 19.8, 2.4, [[("This is a live demonstration. ", True), ("Everything shown runs from the repository; no recording is used. If the network is down, the language layer falls back to rule-based text and the demonstration continues unchanged.", False)]], size=21, fill=LIGHT, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_demo, "Run the six steps live. Step 6 is deliberate: it shows the system refusing a crop with no market choice.")

    # ---- 7 tools & quality
    set_title(s_tools, "Tools, Technology Stack and Code Quality")
    set_bullets(s_tools, [
        ("Repository:", "Git, 69 commits; README, requirements.lock, docs for architecture, tool choices, shock study, council and LLM evaluation; CI workflow."),
        ("Reproducible:", "pipeline.py regenerates all artefacts; the thesis tables are generated from them, not typed."),
        ("Tested:", "669 backend tests and 11 web tests passing; a 60-check smoke test of every endpoint and page; fresh-clone check; CI."),
    ], h=3.0, size=24)
    rows = [["Layer", "Tool (version)", "Why chosen"],
            ["Data / stats", "NumPy 1.26.4, pandas 2.1.4, SciPy 1.11.4, statsmodels 0.14.1", "tested, pinned stack"],
            ["Learning", "LightGBM 4.6.0, XGBoost 2.0.3, scikit-learn 1.3.2, Optuna, PyTorch (research env)", "trees win on tabular [19]; Optuna TPE [20]"],
            ["Backend", "FastAPI 0.136.1, Uvicorn 0.46.0, Pydantic 2.13.3", "typed requests, auto API docs"],
            ["Frontend", "Next.js 16.2.4, React 19.2.4, TypeScript 5, Tailwind 4", "fast pages on weak connections"],
            ["Language layer", "gpt-oss-120b writer, Qwen judge (Groq); Claude provider optional", "two model families; deterministic fallback"],
            ["Quality", "pytest 9.0.3, vitest 3.2, GitHub Actions, Docker, Render file", "automated checks on every push"]]
    table(s_tools, rows, 1.1, 4.7, 19.8, [2.2, 8.8, 5.6], row_h=0.9, size=17, bold_first_col=True)
    notes(s_tools, "Choices and rejected alternatives are recorded in docs/TOOL_CHOICES.md. Research tests need a separate PyTorch environment by design.")

    # ---- 8 setup
    set_title(s_setup, "Experimental Setup and Evaluation Metrics")
    set_bullets(s_setup, [
        ("Split:", "nested walk-forward, 5 outer blocks (2024-H1 → 2026-10); inner validation by Optuna (20 neural / 25 boosting trials); K+2-day gap before every block."),
        ("Setup:", "Core i9-13900HX, 31.7 GB, RTX 4060; fixed seeds recorded in configuration; same tuning budget for every method."),
        ("Metrics:", "realised revenue, regret to hindsight oracle, share of oracle gap closed, silent-market trips, floor violation, forecast skill."),
        ("Baselines (all retrained):", "random walk, LightGBM/XGBoost on observed prices, nearest mandi, highest price yesterday, best 7-day mean, farm gate."),
    ], h=5.0, size=25)
    rows = [["Crop", "Mandi-days", "Mandis", "Eligible", "Test days", "Studied"],
            ["Tomato", "17,582", "14", "12", "963", "yes"], ["Onion", "5,343", "11", "4", "511", "yes"], ["Potato", "5,000", "12", "3", "569", "yes"],
            ["Ginger", "6,423", "10", "3", "776", "yes"], ["Garlic", "2,473", "7", "1", "—", ("refused", RED)], [("Total", NAVY), "36,821", "", "", "", ""]]
    table(s_setup, rows, 1.1, 7.0, 12.4, [1.6, 1.8, 1.3, 1.3, 1.4, 1.7], row_h=0.6, size=18, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 5, hl_rows=(6,))
    text(s_setup, 14.0, 7.0, 6.9, 4.3, [[("Inference: ", True), ("moving-block bootstrap (block 14); Newey–West Diebold–Mariano; Holm across all pre-specified comparisons; model confidence set [24]–[27].", False)], [("Pre-specified: ", True), ("model ladder, 12 paired comparisons, silence tests and leakage protocol were fixed before tuned results were seen.", False)]], size=18, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_setup, "Dataset: two Agmarknet exports that agree on 3,307 overlapping tomato market-days (r = 0.99996). Eligible = markets with at least 700 reported days.")

    # ---- 9 results: decision quality (chart)
    set_title(s_res, "Results and Validation: Decision Quality")
    set_bullets(s_res, [
        ("Result:", "models trained on realised revenue earn the most in every crop; the oracle bounds what is possible."),
        ("Why:", "observed-price models send 12–43% of trips to a silent market; realised-label models cut that to 5–21%."),
    ], h=2.0, size=25)
    cd = CategoryChartData()
    cd.categories = [c.capitalize() for c in CROPS]
    series = [("Nearest mandi", "nearest_today"), ("Highest price yesterday", "highest_yesterday"), ("LightGBM, observed prices", "lgbm_obs"), ("LightGBM, realised outcomes", "lgbm_filled"), ("Neural SPO+", "ds_spo")]
    for name, key in series:
        cd.add_series(name, [round(D[c]["main"].loc[key, "revenue"]) for c in CROPS])
    cd.add_series("Hindsight oracle", [round(D[c]["main"].iloc[0]["revenue"] + D[c]["main"].iloc[0]["regret"]) for c in CROPS])
    gf = s_res.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1.1), Inches(3.5), Inches(14.2), Inches(7.6), cd)
    ch = gf.chart
    ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False; ch.legend.font.size = Pt(20)
    ch.value_axis.tick_labels.font.size = Pt(20); ch.category_axis.tick_labels.font.size = Pt(22)
    ch.value_axis.has_major_gridlines = True; ch.value_axis.major_gridlines.format.line.color.rgb = rgb("D5DBE3")
    ch.has_title = True; ch.chart_title.text_frame.text = "Mean realised net revenue, Rs per quintal"; ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(22)
    for s_, col in zip(ch.plots[0].series, ["A9B4C2", "7F8FA6", "C9A24A", MID, BLUE, "9AA0A6"]):
        s_.format.fill.solid(); s_.format.fill.fore_color.rgb = rgb(col)
    ch.plots[0].gap_width = 60
    tm = D["tomato"]
    stat(s_res, 15.8, 3.5, 5.1, 2.2, f"Rs {tm['main'].loc['lgbm_filled', 'revenue']:,.0f}", "tomato, realised-label model (oracle 2,570)")
    stat(s_res, 15.8, 6.0, 5.1, 2.2, "+Rs 556", "over nearest mandi, tomato (1,600 → 2,156)", color=GREEN)
    stat(s_res, 15.8, 8.5, 5.1, 2.6, "Holm p < 0.002", "labels effect in all four crops", color=ORANGE)
    notes(s_res, "Test set: 963/511/569/776 held-out decision days. Intervals are in the report (Table 6.1). The ordering is the same in every crop.")

    # ---- 9b statistical validation: label effect + SPO+
    s_val = dup(prs, s_res)
    for sh in list(s_val.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_val, "Statistical Validation: What Actually Improved Decisions")
    rows = [["Crop", "Labels: realised vs observed\n(Δ regret, Rs/q)", "95% CI", "Holm p", "SPO+ vs squared error\n(Δ regret, Rs/q)", "Holm p"]]
    for c in CROPS:
        cm = D[c]["cmp"]
        a = cm[(cm["A"] == "lgbm_filled") & (cm["B"] == "lgbm_obs")].iloc[0]
        b = cm[(cm["A"] == "ds_spo") & (cm["B"] == "ds_mse_filled")].iloc[0]
        pv = lambda p: "< 0.0001" if p < 1e-4 else f"{p:.3f}"
        rows.append([c.capitalize(), (fmt(a["regret_diff_A_minus_B"], 0, True), GREEN), f"[{fmt(a['ci_lo'], 0, True)}, {fmt(a['ci_hi'], 0, True)}]", pv(a["holm_p"]),
                     (f"{fmt(b['regret_diff_A_minus_B'], 0, True)}  [{fmt(b['ci_lo'], 0, True)}, {fmt(b['ci_hi'], 0, True)}]", GREY), f"{b['holm_p']:.2f}"])
    table(s_val, rows, 1.1, 1.9, 19.8, [1.6, 3.6, 3.0, 1.8, 4.6, 1.5], row_h=0.95, size=19, head_size=17, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 5)
    card(s_val, 1.1, 7.0, 6.3, 3.9, "Finding", ["Better labels, not a fancier loss: realised-outcome supervision cuts regret in all four crops; SPO+ adds nothing reliable."], size=23)
    card(s_val, 7.85, 7.0, 6.3, 3.9, "Model confidence set", ["Only realised-label models survive in every crop; no observed-price model does. Tomato keeps 7 specifications; the others 3."], size=23, head_fill=MID)
    card(s_val, 14.6, 7.0, 6.3, 3.9, "Limits", ["One region, one source, 5.8 years; revenue parameters are scenarios; silent day treated as no sale; offline only."], size=23, head_fill=RED)
    notes(s_val, "Paired daily regret differences, moving-block bootstrap, Newey-West Diebold-Mariano, Holm correction across all pre-specified comparisons.")

    # ---- 9c floors + engines
    s_floor = dup(prs, s_val)
    for sh in list(s_floor.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_floor, "Verified Floors and Served-Engine Back-test")
    rows = [["Floor violation (%)\ntarget 10%", "Adaptive 5%", "Adaptive 10%", "Adaptive 20%", "Static 10%", "Naive Gaussian"]]
    for c in CROPS:
        f = D[c]["floors"]
        ad = f[(f["spec"] == "lgbm_filled") & f["policy"].str.contains("adaptive")].set_index("alpha")["violation"]
        st = f[(f["spec"] == "lgbm_filled") & f["policy"].str.contains("static")]["violation"].iloc[0]
        nv = f[(f["spec"] == "lgbm_obs") & f["policy"].str.contains("naive")]["violation"].iloc[0]
        rows.append([c.capitalize()] + [(f"{100 * ad[a]:.1f}", GREEN if abs(ad[a] * 100 - a * 100) < 2.5 else ORANGE) for a in (0.05, 0.1, 0.2)] + [f"{100 * st:.1f}", (f"{100 * nv:.1f}", RED if nv > 0.15 else NAVY)])
    table(s_floor, rows, 1.1, 1.9, 9.6, [2.4, 1.6, 1.6, 1.6, 1.5, 1.8], row_h=0.8, size=18, head_size=15, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 5)
    text(s_floor, 1.1, 6.2, 9.6, 3.0, "Adaptive floors track the nominal level; the static quantile is cautious; a naive Gaussian floor is breached on 26–35% of days in three crops.", size=20, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    picture(s_floor, FIG / "fig_floor_calibration.png", 1.1, 8.65, h=2.5) if False else None
    eng = []
    for c in CROPS:
        b = json.loads((MODELS / "market_choice" / c / "meta.json").read_text(encoding="utf-8"))["backtest"]
        g, n = b["gain_vs_highest_yesterday"], b["gain_vs_nearest"]
        eng.append([c.capitalize(), f"{fmt(g['mean'], 0, True)} [{fmt(g['ci_lo'], 0, True)}, {fmt(g['ci_hi'], 0, True)}]", fmt(n["mean"], 0, True), f"{100 * b['share_of_oracle_gap_closed']:.0f}%",
                    (b["evidence_level"], GREEN if b["evidence_level"] == "strong" else ORANGE)])
    rows = [["Back-test, last 330 days", "Gain vs highest yesterday (Rs/q)", "vs nearest", "Gap closed", "Evidence"]] + eng
    table(s_floor, rows, 11.2, 1.9, 9.7, [2.1, 3.6, 1.6, 1.5, 1.6], row_h=0.8, size=17, head_size=15, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 4)
    cdg = CategoryChartData()
    cdg.categories = [c.capitalize() for c in CROPS]
    gy_, gn_ = [], []
    for c in CROPS:
        bb = json.loads((MODELS / "market_choice" / c / "meta.json").read_text(encoding="utf-8"))["backtest"]
        gy_.append(round(bb["gain_vs_highest_yesterday"]["mean"])); gn_.append(round(bb["gain_vs_nearest"]["mean"]))
    cdg.add_series("vs highest price yesterday", gy_)
    cdg.add_series("vs nearest mandi", gn_)
    gfc = s_floor.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(11.2), Inches(6.0), Inches(9.7), Inches(5.2), cdg)
    cc = gfc.chart
    cc.has_legend = True; cc.legend.position = XL_LEGEND_POSITION.BOTTOM; cc.legend.include_in_layout = False; cc.legend.font.size = Pt(18)
    cc.value_axis.tick_labels.font.size = Pt(18); cc.category_axis.tick_labels.font.size = Pt(20)
    cc.has_title = True; cc.chart_title.text_frame.text = "Back-test gain of the advice, Rs per quintal"; cc.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    cc.value_axis.major_gridlines.format.line.color.rgb = rgb("D5DBE3")
    for s_, col in zip(cc.plots[0].series, [MID, ORANGE]):
        s_.format.fill.solid(); s_.format.fill.fore_color.rgb = rgb(col)
    cc.plots[0].gap_width = 60
    notes(s_floor, "Floors are calibrated online with delayed feedback. Back-test gains are significant for tomato, onion and ginger; potato's gain over the best heuristic (Rs 15, CI −38 to +60) is not distinguishable from zero, so the app labels it limited evidence. Garlic is refused.")

    # ---- 9d leakage
    s_leak = dup(prs, s_val)
    for sh in list(s_leak.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_leak, "Look-Ahead Audit of Decompose-then-Forecast Models")
    lk = pd.read_csv(RES / "tomato" / "leakage" / "summary.csv")
    cd = CategoryChartData()
    labs = [f"{r.decomposer} + {'LGBM' if r.forecaster == 'lgbm' else 'Ridge'}, {r.h} d" for r in lk.itertuples()]
    cd.categories = labs
    cd.add_series("Published protocol (decomposed once)", [round(100 * v, 1) for v in lk["skill_published"]])
    cd.add_series("Causal protocol", [round(100 * v, 1) for v in lk["skill_causal_joint"]])
    gf = s_leak.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1.1), Inches(1.8), Inches(13.2), Inches(8.9), cd)
    ch = gf.chart
    ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False; ch.legend.font.size = Pt(20)
    ch.value_axis.tick_labels.font.size = Pt(20); ch.category_axis.tick_labels.font.size = Pt(17)
    ch.has_title = True; ch.chart_title.text_frame.text = "Skill vs random walk, tomato (%)"; ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(22)
    ch.value_axis.major_gridlines.format.line.color.rgb = rgb("D5DBE3")
    for s_, col in zip(ch.plots[0].series, [RED, BLUE]):
        s_.format.fill.solid(); s_.format.fill.fore_color.rgb = rgb(col)
    fo = pd.read_csv(RES / "tomato" / "leakage" / "foundation_skill.csv")
    stat(s_leak, 14.8, 1.9, 6.1, 2.4, "+27 … +62%", "skill under the published protocol", color=RED)
    stat(s_leak, 14.8, 4.6, 6.1, 2.4, "−15 … −1%", "the same models, causal decomposition", color=BLUE)
    text(s_leak, 14.8, 7.3, 6.1, 3.4, [[("Why: ", True), ("STL and VMD are two-sided smoothers, so the component at day t already contains later prices. Zero-shot Chronos-Bolt [17] scores " + f"{100 * fo.iloc[0].skill_foundation:+.1f}".replace("-", "−") + "% at 1 day: no model here beats the random walk on the daily tomato series.", False)]], size=18, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_leak, "Identical forecasters, lags and origins under two protocols. The claim is about the protocol the hybrid papers describe; we did not audit those specific papers.")

    # ---- 9e other studies (null results)
    s_null = dup(prs, s_val)
    for sh in list(s_null.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_null, "Council, Shocks, Spillover and Language Layer")
    council = json.loads((MODELS / "council" / "evaluation.json").read_text(encoding="utf-8"))["horizons"]
    sk = lambda h, k: 100 * council[h]["methods"][k]["skill"]
    ll = json.loads((MODELS / "llm_eval.json").read_text(encoding="utf-8"))
    rows = [["Study", "What was tested", "Result", "Verdict"],
            ["Specialist council", "4 feature-family agents, weights ≤ 1, 4 folds", f"council {sk('3','council'):+.1f}…{sk('7','council'):+.1f}% vs single {sk('3','single'):+.1f}…{sk('7','single'):+.1f}% skill; wins 0–1 of 4 folds", ("Not promoted", ORANGE)],
            ["Supply-shock event study", "30 crop–horizon tests, placebo shifts, Holm", "0 robust, 5 suggestive; effects as large as the detectable minimum", ("Not served", ORANGE)],
            ["Cross-commodity spillover", "5 crops, 40 edges, FDR 10%, ≥8 episodes", "0 shock episodes in all 10 source cells; 40/40 insufficient evidence", ("Withheld", RED)],
            ["District forecasts", "3-, 5-, 7-day vs no change, 90% band", "skill +3.0…+4.0%, coverage 89.8%; 1-day not distinguishable", ("Served 3/5/7 d", GREEN)],
            ["Explanation layer", "24 texts, 120 sentences, EN/KN/HI, independent judge", "kept: EN 0.83–0.99, KN 0.62–0.88, HI 0.68–0.91; judge caught 9/9 corrupted, 0/3 false alarms", ("Verified, small n", GREEN)]]
    table(s_null, rows, 1.1, 1.9, 19.8, [3.0, 5.0, 8.2, 2.6], row_h=1.35, size=18, bold_first_col=True)
    text(s_null, 1.1, 10.0, 19.8, 1.2, "Zero spillover episodes is also a finding about the pipeline: the detector depends on supply-regime labels that the real panel does not yet supply. Listed under future work.", size=18, italic=True, color=GREY)
    notes(s_null, "These are reported as null results on purpose: a result that did not clear its evidence floor is not served.")

    # ---- 10 benchmarking
    set_title(s_bench, "Comparative Benchmarking")
    set_bullets(s_bench, [
        ("Same split, same metric, all retrained:", "no published study scores mandi choice by regret on real reporting-gap data, so baselines are the heuristics farmers use and the standard predict-then-optimise models."),
        ("Where we win:", "all four crops vs every heuristic and every observed-price model. Where we do not:"),
        ("", "potato back-test gain is not distinguishable from the best heuristic, and SPO+ ties the squared-error loss."),
    ], h=3.8, size=25)
    rows = [["Gap closed (nearest → oracle) / silent-market trips", "Tomato", "Onion", "Potato", "Ginger"]]
    for name, key in [("Nearest mandi, sell today", "nearest_today"), ("Highest price yesterday", "highest_yesterday"), ("LightGBM, observed prices", "lgbm_obs"),
                      ("LightGBM, realised outcomes (ours)", "lgbm_filled"), ("Neural SPO+, realised outcomes (ours)", "ds_spo")]:
        rows.append([name] + [f"{D[c]['main'].loc[key, 'gap_closed_vs_nearest']:.2f} / {100 * D[c]['main'].loc[key, 'fallback_rate']:.0f}%" for c in CROPS])
    table(s_bench, rows, 1.1, 5.9, 19.8, [6.2, 3, 3, 3, 3], row_h=0.82, size=19, head_size=17, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 4, hl_rows=(4, 5))
    notes(s_bench, "Gap closed is the share of the gap between the nearest-mandi rule and the hindsight oracle. Published decompose-then-forecast results are compared under their own protocol and the causal one on the previous slide.")

    # ---- 11 novelty
    set_title(s_nov, "Novelty and Research Contribution")
    set_bullets(s_nov, [
        ("In one sentence:", "supervise market choice on realised, silence-aware revenue, certify it with delayed-feedback conformal floors, and audit the leakage in published hybrids."),
    ], h=1.6, size=24)
    card(s_nov, 1.1, 3.6, 6.3, 5.6, "Already exists", ["Forecasters of agricultural prices [9]–[14]", "SPO+ and decision-focused learning [21], [22]", "Adaptive conformal inference [25]–[28]"], size=22, head_fill=GREY)
    card(s_nov, 7.85, 3.6, 6.3, 5.6, "New here", ["Revenue labels that include silent markets, on real mandi data", "Floors for selected actions whose outcome resolves k days later", "Measured size of look-ahead leakage in STL/VMD hybrids", "Verified language briefs and a withheld-by-default spillover engine"], size=22, head_fill=GREEN)
    card(s_nov, 14.6, 3.6, 6.3, 5.6, "Ours vs adapted", ["Ours: formulation, pipeline, leakage protocol, grounding verifier, engines, app", "Adapted: SPO+ [21], ACI [26], DeepSets [29], Optuna [20], Chronos [17]"], size=22, head_fill=BLUE)
    text(s_nov, 1.1, 9.6, 19.8, 1.4, "Honest scope: the positive contribution that survived testing is the label effect, the floor validity and the audit; the loss, reporting head, silence features, council and spillover are bounded negative results.", size=20, fill=PALE, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_nov, "Claims limited to what held on held-out data. Negative results are part of the contribution.")

    # ---- 12 ablation
    set_title(s_opt, "Optimization and Ablation Study")
    set_bullets(s_opt, [
        ("Tuning:", "Optuna TPE per fold on each method's native criterion; same budget for all. Tuning on forecast loss instead of regret: no reliable change."),
        ("Cost:", "served boosting model chosen over the neural one: equal decisions, far cheaper to train, run and explain."),
    ], h=2.3, size=25)
    rows = [["One change at a time", "Δ regret, Rs/q (95% CI)", "Holm p", "Verdict"]]
    tm = D["tomato"]["cmp"]
    for lab, a, b in [("SPO+ loss instead of squared error", "ds_spo", "ds_mse_filled"), ("Add reporting head (SPO+)", "ds_spo_struct", "ds_spo"),
                      ("Add network-silence features (GBM)", "lgbm_filled_sil", "lgbm_filled"), ("Neural instead of boosting, same labels", "ds_mse_filled", "lgbm_filled")]:
        hit = tm[(tm["A"] == a) & (tm["B"] == b)]
        if not len(hit):
            continue
        r = hit.iloc[0]
        v = ("no reliable difference", GREY) if r["holm_p"] >= 0.05 else (("better", GREEN) if r["regret_diff_A_minus_B"] < 0 else ("worse", RED))
        rows.append([lab, f"{fmt(r['regret_diff_A_minus_B'], 0, True)}  [{fmt(r['ci_lo'], 0, True)}, {fmt(r['ci_hi'], 0, True)}]", f"{r['holm_p']:.3f}", v])
    table(s_opt, rows, 1.1, 4.6, 19.8, [6.8, 5.2, 1.8, 4.2], row_h=0.8, size=19, aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.LEFT])
    text(s_opt, 1.1, 9.0, 19.8, 2.0, [[("Tried and did not work: ", True), ("reporting head (worse, p = 0.012), silence features, decision-regret tuning, unconstrained council weights (summed 2.4–3.1, significantly worse), SPO+ over squared error. Ablations shown for tomato; the other crops agree.", False)]], size=19, fill=PALE, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_opt, "Each row changes one thing. Failures are documented, not hidden.")

    # ---- 13 WBS & critical path
    set_title(s_wbs, "Project Planning: WBS and Critical Path")
    pk = [("1 Management & documentation", "130 h", "Shreejith"), ("2 Data", "100 h", "Manohara"), ("3 Models & research", "290 h", "Manohara"), ("4 Application", "360 h", "Srijan"), ("5 Verification", "90 h", "Shreejith / Manohara")]
    rows = [["WBS package", "Hours", "Primary owner"]] + [list(p) for p in pk] + [["Total", "970 h", ""]]
    table(s_wbs, rows, 1.1, 1.9, 8.8, [4.6, 1.4, 2.8], row_h=0.66, size=17, aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT], hl_rows=(6,))
    text(s_wbs, 1.1, 6.95, 8.8, 0.8, "Hours are team estimates, not logged time. Each leaf task has one owner; children sum to parents.", size=14, italic=True, color=GREY)
    shape(s_wbs, "Content Guidance")._element.getparent().remove(shape(s_wbs, "Content Guidance")._element)
    dur = {"A": 2, "B": 3, "C": 4, "D": 4, "E": 5, "F": 3, "G": 4, "H": 3, "I": 3, "J": 2, "K": 3}
    nm = {"A": "Requirements", "B": "Data", "C": "Market choice", "D": "Backend", "E": "Web app", "F": "Forecasters", "G": "Experiments", "H": "LLM layer", "I": "Testing", "J": "Integration", "K": "Report"}
    X = [10.3 + i * 2.12 for i in range(5)]
    coords = {"A": (X[0], 1.9), "B": (X[1], 1.9), "C": (X[2], 1.9), "F": (X[3], 1.9), "G": (X[4], 1.9),
              "I": (X[4], 4.0), "J": (X[3], 4.0), "K": (X[2], 4.0), "D": (X[0], 6.0), "E": (X[1], 6.0), "H": (X[2], 6.0)}
    for k, (x, y) in coords.items():
        crit = k in "ABCFGIJK"
        text(s_wbs, x, y, 1.9, 1.5, [[(k, True)], [(nm[k], False)], [(f"{dur[k]} wk", False)]], size=14, fill="F8D9D5" if crit else LIGHT, line=RED if crit else MID, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE, margin=0.03)
    for a_, b_ in [("A", "B"), ("B", "C"), ("C", "F"), ("F", "G")]:
        arrow(s_wbs, coords[a_][0] + 1.9, coords[a_][1] + 0.75, coords[b_][0], coords[b_][1] + 0.75, color=RED, width=2.5)
    arrow(s_wbs, X[4] + 0.95, 3.4, X[4] + 0.95, 4.0, color=RED, width=2.5)
    for a_, b_ in [("I", "J"), ("J", "K")]:
        arrow(s_wbs, coords[a_][0], coords[a_][1] + 0.75, coords[b_][0] + 1.9, coords[b_][1] + 0.75, color=RED, width=2.5)
    arrow(s_wbs, X[0] + 0.95, 3.4, X[0] + 0.95, 6.0, color=MID, width=2)
    arrow(s_wbs, X[0] + 1.9, 6.75, X[1], 6.75, color=MID, width=2)
    text(s_wbs, X[3] - 0.1, 5.9, 4.6, 1.7, ["Critical path (red):", "A→B→C→F→G→I→J→K", "2+3+4+3+4+3+2+3 = 24 weeks", "D, E, H have slack"], size=15, bold=True, color=RED)
    text(s_wbs, 1.1, 7.9, 19.8, 3.3, [[("Worked slack, activity E: ", True), ("LF(E) = LS(I) = 16 weeks, so LS(E) = 16 − 5 = 11; ES(E) = 6; slack = 11 − 6 = 5 weeks. ", False), ("For H: ", True), ("LS = 16 − 3 = 13, ES = 6, slack = 7. ", False), ("For D: ", True), ("LF = min(LS(E), LS(H)) = 11, LS = 7, ES = 2, slack = 5.", False)],
                                      [("RAM: ", True), ("every work package has one primary owner (R) and the guide is accountable (A); Manohara 430 h, Srijan 360 h, Shreejith 180 h.", False)]], size=19, fill=PALE, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_wbs, "Planned 24 weeks from 27 April 2026. The baseline was reconstructed from the Phase-1 roadmap. Owners follow the team's split; the commit history does not corroborate work of the second and third members and the report says so.")

    # ---- 14 schedule & risk
    set_title(s_risk, "Schedule Tracking and Risk Management")
    shape(s_risk, "Content Guidance")._element.getparent().remove(shape(s_risk, "Content Guidance")._element)
    acts = [("A Requirements", 0, 2, 0, 3), ("B Data", 2, 5, 3, 24), ("C Market choice", 5, 9, 6, 26), ("D Backend API", 2, 6, 1, 23), ("E Web application", 6, 11, 6, 24),
            ("F Forecasters", 9, 12, 22, 26), ("G Experiments", 12, 16, 24, 27), ("H LLM layer", 6, 9, 22, 24), ("I Testing", 16, 19, 22, 27), ("J Integration", 19, 21, 25, 27), ("K Report", 21, 24, 25, 27.3)]
    gx, gy, gw, rh = 4.3, 2.35, 8.0, 0.44
    unit = gw / 28
    for wk in range(0, 29, 4):
        text(s_risk, gx + wk * unit - 0.3, 1.78, 0.6, 0.4, str(wk), size=13, color=GREY, align=PP_ALIGN.CENTER, margin=0)
        ln = s_risk.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(gx + wk * unit), Inches(gy), Inches(gx + wk * unit), Inches(gy + rh * 11 + 0.1)); ln.line.color.rgb = rgb("D5DBE3"); ln.line.width = Pt(0.75)
    for i, (n_, b0, b1, a0, a1) in enumerate(acts):
        y = gy + i * rh
        text(s_risk, 1.1, y, 3.1, rh, n_, size=14, align=PP_ALIGN.RIGHT, margin=0.04, anchor=MSO_ANCHOR.MIDDLE)
        text(s_risk, gx + b0 * unit, y + 0.02, (b1 - b0) * unit, 0.17, "", fill="9DB9D6")
        text(s_risk, gx + a0 * unit, y + 0.21, (a1 - a0) * unit, 0.17, "", fill=ORANGE)
    text(s_risk, gx, gy + rh * 11 + 0.15, 1.5, 0.3, "baseline", size=13, color="6A8FB8", margin=0)
    text(s_risk, gx + 1.8, gy + rh * 11 + 0.15, 1.5, 0.3, "actual", size=13, color=ORANGE, margin=0)
    text(s_risk, 1.1, 7.6, 11.0, 3.4, [[("Slip: ", True), ("24 weeks planned, about 27 actual (+3.3 weeks, 14%). Data (B) was reopened after the first dataset proved synthetic, which pushed C and G on the critical path; D, E and H sat on slack and absorbed their delay.", False)],
                                     [("Milestones: ", True), ("M1 requirements (wk 3), M2 first deployed prototype 9 Jun, M3 farmer suite 30 Sep, M4 research results 29 Oct, M5 report (wk 27).", False)]], size=17, fill=PALE, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    rows = [["Risk", "P×I", "Response", "Status"],
            ["R1 Source data synthetic", "15", "Re-acquired Agmarknet exports, integrity check, removed synthetic", ("Occurred", RED)],
            ["R2 Look-ahead leakage", "20", "Leakage unit tests; caught 2 whole-series-centred features", ("Occurred", RED)],
            ["R3 Hard deletion broke trader pages", "9", "Soft delete, re-seeding, id aliasing", ("Occurred", RED)],
            ["R4 NumPy 2 broke pandas", "9", "Pinned 1.26.4; lock file", ("Occurred", RED)],
            ["R5 LLM rate limit 8k tokens/min", "8", "Throttling, small evaluation set", ("Occurred", RED)],
            ["R6 Uneven team contribution", "12", "Contribution record; owner split", ("Open", ORANGE)],
            ["R7 Deployment unverified", "9", "Docker + Render files; to verify", ("Open", ORANGE)],
            ["R8 No field trial", "12", "Stated limitation; survey ready", ("Open", ORANGE)],
            ["R10 Stale server served old code", "6", "Restart; smoke test lists every endpoint", ("Occurred", RED)]]
    table(s_risk, rows, 12.5, 1.8, 8.4, [3.6, 0.8, 4.4, 1.5], row_h=0.7, size=14, head_size=14, aligns=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.CENTER])
    text(s_risk, 12.5, 9.2, 8.4, 1.9, [[("Materialised: R1. ", True), ("Trigger: results that looked too clean. Action: discard, rebuild from portal exports, re-run every experiment (see report Ch. 4).", False)]], size=16, fill=LIGHT, margin=0.2, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_risk, "Baseline reconstructed; actual spans from commit dates (first commit 28 April, last 29 October). There is no repository activity between 10 June and 28 September.")

    # ---- 15 report & documentation
    set_title(s_rep, "Project Report and Documentation Status")
    set_bullets(s_rep, [
        ("Report:", f"BMSCE thesis template, {PAGES} pages, compiled in LaTeX; Chapters 1–7 written, now including the insight features and the digest; every table generated from experiment artefacts."),
        ("Appendices:", "A code (read from source), B survey instrument, C per-fold evaluation, D dataset, E PO and SDG mapping, F similarity record."),
        ("Remaining:", "official Drillbit report, CO–PO matrix from the course file, declaration date, supervisor corrections."),
    ], h=3.6, size=25)
    rows = [["Item", "State"], ["Chapters 1–7", ("complete", GREEN)], ["Appendices A–E", ("complete (E: CO–PO table to be inserted)", ORANGE)], ["Appendix F similarity record", ("pending: Drillbit not yet run", RED)],
            ["Figures and tables", ("numbered, captioned, referenced", GREEN)], ["Citations", ("40 IEEE-style entries, all cited", GREEN)]]
    table(s_rep, rows, 1.1, 5.0, 12.0, [4.4, 7.6], row_h=0.8, size=19, aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT])
    text(s_rep, 13.7, 5.0, 7.2, 4.8, [[("Similarity: ", True), ("target ≤ 20% with Drillbit, references excluded. The official check has not been run yet; no percentage is claimed. A self-check of the conference draft found no verbatim web matches, which is not a substitute.", False)]], size=19, fill=PALE, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)
    notes(s_rep, "Be explicit: the Drillbit percentage and date will be entered in Appendix F once the official report exists.")

    # ---- 16 SDG
    set_title(s_sdg, "SDG Mapping and Societal Impact")
    set_bullets(s_sdg, [("Stakeholders:", "smallholder farmers (need a plain answer and a floor), traders (need evidence tiers and arrivals), mandi officials and policy makers (need transparent data use).")], h=1.8, size=25)
    rows = [["SDG / target", "Link", "Support in our results", "Status"],
            ["2 / 2.3", "income of small-scale producers through market information", "back-test gains Rs 60–202 per quintal over the best simple rule in 3 of 4 crops; morning digest on a free channel (untested with farmers)", ("Measured offline", GREEN)],
            ["1 / 1.4", "access to economic services", "free trilingual tool for small sellers", ("Not measured", ORANGE)],
            ["12 / 12.3", "reduce food loss along supply chains", "spoilage built into advice; kg avoided not measured", ("Potential", ORANGE)],
            ["9 / 9.c", "access to information technology", "open pipeline on a public data feed", ("Engineering", GREY)]]
    table(s_sdg, rows, 1.1, 3.9, 19.8, [1.8, 5.2, 7.4, 2.6], row_h=1.1, size=19, bold_first_col=True)
    text(s_sdg, 1.1, 10.4, 19.8, 0.9, "Impact is claimed only where held-out numbers support it; the benefit to farmers' real income needs a field trial.", size=19, italic=True, color=GREY)
    notes(s_sdg, "Numbered targets, not only goal numbers. The offline gains are not real income.")

    # ---- 17 paper
    set_title(s_paper, "Research Paper Status")
    set_bullets(s_paper, [
        ("Primary target:", "IEEE Access, a broad applied-engineering journal that accepts long empirical papers with negative results."),
        ("Status:", "manuscripts drafted; none submitted yet, so there is no acknowledgement, review or acceptance to show."),
    ], h=2.6, size=25)
    rows = [["Manuscript", "Venue", "Pages", "Status"],
            ["Where and When to Sell: Outcome-Supervised Market Choice with Conformal Revenue Floors, and a Look-Ahead Audit of Decomposition Forecasters", "IEEE Access", "14", ("Drafted, not submitted", ORANGE)],
            ["Fusing Specialist Agents and Market Signals into Calibrated Price Ranges: A Pre-Registered Evaluation on Indian Agricultural Mandis", "CICPS 2027 (Springer LNNS)", "12", ("Drafted, not submitted", ORANGE)],
            ["MandiSense project proposal", "KSCST SPP 50th series", "14", ("Proposal drafted", ORANGE)]]
    table(s_paper, rows, 1.1, 4.5, 19.8, [9.4, 4.2, 1.2, 3.4], row_h=1.35, size=18, aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT])
    text(s_paper, 1.1, 10.0, 19.8, 1.2, "Similarity: only a self-conducted check exists for the conference draft (no verbatim web matches). Official Drillbit percentages will be added at submission.", size=18, italic=True, color=GREY)
    notes(s_paper, "Do not claim submission. The next step is to submit the IEEE Access manuscript and attach the acknowledgement mail.")

    # ---- 18 conclusion
    set_title(s_conc, "Conclusion and Future Work")
    set_bullets(s_conc, [
        ("Key outcome:", "advice trained on realised revenue beats the best simple rule by Rs 170 per quintal for tomato and Rs 202 for ginger, with floors that hold their level."),
        ("Against objectives:", "7 met, 1 partly met, 1 null result, 1 built and tested (the digest); negative results reported."),
    ], h=3.0, size=25)
    card(s_conc, 1.1, 4.5, 9.7, 6.4, "Limitations", ["One region, one source, 5.8 years", "Offline only; no farmer acted on the advice; digest not piloted", "Revenue and crowd parameters are scenarios; replayed floors held 84–92% (aim 90%)", "Briefs checked for traceability, not user-tested", "Spillover found no episodes; deployment unverified"], size=25, head_fill=RED)
    card(s_conc, 11.2, 4.5, 9.7, 6.4, "Future work (from those limits)", ["Field pilot through the bot, with an outcome form and the survey", "Estimate transport, spoilage and silence from data", "Diagnose the spillover labelling; define episodes from arrivals", "User test of briefs; native-speaker review of KN/HI", "Verify deployment and monitor live floor violations"], size=25, head_fill=GREEN)
    notes(s_conc, "Everything under future work follows from a stated limitation.")

    # ---- 19 references
    set_title(s_ref, "References")
    refs = ["[1] P. Birthal et al., J. Agribusiness Develop. Emerg. Econ., 2019", "[2] AGMARKNET, Directorate of Marketing and Inspection, Govt. of India",
            "[3] R. Jensen, Quart. J. Econ., 122(3), 2007", "[4] J. Aker, AEJ: Appl. Econ., 2(3), 2010", "[5] S. Ray et al., Appl. Soft Comput., 149, 2023", "[6] K. Meena, B. Chaitra, IEEE Access, 12, 2024",
            "[7] G. Jha, K. Sinha, Neural Comput. Appl., 24, 2014", "[8] Wu et al., Expert Syst., 2026", "[9] R. Cleveland et al., J. Official Statist., 6(1), 1990", "[10] Hyndman, Athanasopoulos, Forecasting: Principles and Practice, 3e, 2021",
            "[11] A. Sathe et al., Results Eng., 27, 2025", "[12] B. Celik, S. Celik, Borsa Istanbul Rev., 2025", "[13] K. Dragomiretskiy, D. Zosso, IEEE TSP, 62(3), 2014", "[14] Bergmeir, Benítez, Inf. Sci., 191, 2012",
            "[15] Cerqueira et al., Mach. Learn., 109, 2020", "[16] Bundak et al., IEEE Access, 13, 2025", "[17] Ansari et al., Chronos, TMLR, 2024", "[18] Wang, Zhang, arXiv:2601.06371, 2026"]
    refs2 = ["[19] Grinsztajn et al., NeurIPS D&B, 2022", "[20] Akiba et al., Optuna, KDD, 2019", "[21] Elmachtoub, Grigas, Manage. Sci., 68(1), 2022", "[22] Mandi et al., J. Artif. Intell. Res., 80, 2024",
             "[23] Chen, Guestrin, XGBoost, KDD, 2016; Ke et al., LightGBM, NeurIPS, 2017", "[24] Diebold, Mariano, JBES, 13(3), 1995", "[25] Newey, West, Econometrica, 55(3), 1987", "[26] Gibbs, Candès, NeurIPS, 2021",
             "[27] Hansen, Lunde, Nason, Econometrica, 79(2), 2011", "[28] Vovk et al., Algorithmic Learning in a Random World, 2005; Angelopoulos, Bates, 2023", "[29] Zaheer et al., Deep Sets, NeurIPS, 2017",
             "[30] Holm, Scand. J. Statist., 6(2), 1979", "[31] Künsch, Ann. Statist., 17(3), 1989", "[32] Romano et al., CQR, NeurIPS, 2019", "[33] Rubin, Biometrika, 63(3), 1976", "[34] Che et al., Sci. Rep., 8, 2018",
             "Full 40-entry list with all details is in the thesis bibliography."]
    sh = set_bullets(s_ref, [("", r) for r in refs], x=1.1, y=1.9, w=9.8, h=9.2, size=19)
    tgt = shape(s_ref, "Content Guidance")
    c2 = copy.deepcopy(tgt._element)
    s_ref.shapes._spTree.append(c2)
    sh2 = [s for s in s_ref.shapes if s.name == "Content Guidance"][-1]
    sh2.left = Inches(11.2)
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    body = sh2.text_frame._txBody
    paras = body.findall(A + "p")
    proto = copy.deepcopy(paras[0])
    for p in paras:
        body.remove(p)
    for r_ in refs2:
        p = copy.deepcopy(proto)
        rr = p.findall(A + "r")
        for x_ in rr[1:]:
            p.remove(x_)
        rr[0].find(A + "t").text = r_
        body.append(p)
    notes(s_ref, "IEEE style, numbered. Full vetted list of 40 entries is in the thesis.")

    # ================================================================ insight and demo slides
    DD = json.loads((ROOT / "report" / "generated" / "deck_data.json").read_text(encoding="utf-8"))
    clean = lambda x: str(x).replace("\\%", "%").replace("\\", "")
    FIGS = ROOT / "report" / "figures"

    def fresh(title):
        sl = dup(prs, s_val)
        for sh in list(sl.shapes):
            if not keep_shape(sh):
                sh._element.getparent().remove(sh._element)
        set_title(sl, title)
        return sl

    def img(sl, name, x, y, max_w, max_h):
        from PIL import Image

        w, h = Image.open(FIGS / name).size
        sc = min(max_w / w, max_h / h)
        return picture(sl, FIGS / name, x, y, w=w * sc, h=h * sc)

    # ---- insight method
    s_insmeth = fresh("Insight Features: Method")
    items = [("1  Breakdown: why this mandi", "R = P − fP − (1−f)·P·[1 − (1−δ)ᵏ] − τρd − c₀", "the parts add up to the served net revenue; the code asserts it"),
             ("2  What if: break-even cost", "x* = min { x on grid : a*(x) ≠ a*(x₀) }", "re-price every action under the farmer's costs; report where the best action flips"),
             ("3  Track record", "win: gain > ₹1 · tie: |gain| ≤ ₹1 · loss: gain < −₹1", "only days after the floor multiplier was fitted; floor held if R ≥ L"),
             ("4  Silence tax", "Tₘ = sₘ · max( P̄ₘ − φ·P̄day , 0 )", "s = surprise silence on open days; weekdays silent ≥ 90% are known closed days"),
             ("5  Crowd simulator", "Pₘ(x) = Pₘ · (1 + x / Aₘ)^(−b)", "Aₘ = median daily arrivals; b = 0.115 is an association (SE 0.023): a scenario")]
    pos = [(1.1, 1.8), (1.1, 5.2), (1.1, 8.6), (11.3, 1.8), (11.3, 5.2)]
    for (head, eq, note), (x, y) in zip(items, pos):
        text(s_insmeth, x, y, 9.7, 0.55, head, size=19, bold=True, color=BLUE)
        text(s_insmeth, x, y + 0.6, 9.7, 1.0, eq, size=20, bold=True, fill=PALE, anchor=MSO_ANCHOR.MIDDLE, margin=0.2, font="Cambria Math")
        text(s_insmeth, x, y + 1.7, 9.7, 1.2, note, size=17, color=GREY)
    text(s_insmeth, 11.3, 8.6, 9.7, 2.5, [[("None of these fits a model at request time. ", True), ("Each reads the served engine and the ingested panel, and every assumption is returned with the answer.", False)]], size=19, fill=LIGHT, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)

    # ---- overview of the features
    s_ov = fresh("What You Will See: Five Features and a Digest")
    cards = [("1  Why this mandi?", "Per-quintal arithmetic of the advice: price − fee − spoilage − transport − handling = net.\nFarmer app · /breakdown", BLUE),
             ("2  What if my costs differ?", "Sliders for transport, spoilage and longest wait; the advice updates and says where it flips.\nFarmer app · /simulate", BLUE),
             ("3  Has this advice worked?", "The advice replayed on 165 days it had not seen: wins, ties, losses; floor score.\nFarmer app · /track-record", BLUE),
             ("4  Silence Tax", "Rupees lost per quintal on a trip because a mandi reports no price; weekday strip.\nTrader desk · /reporting-value", ORANGE),
             ("5  Crowd Simulator", "What happens to a mandi's price when 200 farmers follow the same advice; coordinated split.\nTrader desk · /crowd", ORANGE),
             ("6  Daily digest", "A dated morning message with advice only where evidence is strong.\nTelegram bot · /v1/notify", GREEN)]
    for i, (h_, b_, c_) in enumerate(cards):
        card(s_ov, 1.1 + (i % 3) * 6.75, 1.9 + (i // 3) * 4.9, 6.45, 4.5, h_, [ln for ln in b_.split("\n")], size=22, head_fill=c_)

    # ---- demo slides (live)
    s_d1 = s_demo
    for sh in list(s_d1.shapes):
        if not keep_shape(sh):
            sh._element.getparent().remove(sh._element)
    set_title(s_d1, "Live Demonstration (1/2): Farmer Tool")
    rows = [["Step", "Do", "You will see"],
            ["A1", "Tools → Best Place & Day to Sell · Kolar, tomato, 10 q, tempo", "Ramanagara, Wed 28 Oct, 103 km · ₹1,824 expected · ₹1,316 floor · ₹592 above nearest"],
            ["A2", "Open “Why this mandi?”", "2,081 − 83 − 60 − 94 − 20 = ₹1,824; nearest Kolar ₹1,233"],
            ["A3", "What if: drag transport to ₹3.00", "Same advice, net ₹1,515"],
            ["A4", "What if: drag spoilage to 5%", "Advice changes: Ramanagara today, ₹1,789"],
            ["A5", "Open “Has this advice worked?”", "93% better than nearest · floor held 84% (aim 90%)"],
            ["A6", "Switch language to Kannada, then back", "All panels in Kannada"]]
    table(s_d1, rows, 1.1, 1.9, 19.8, [0.9, 8.2, 10.7], row_h=1.15, size=17, bold_first_col=True)
    text(s_d1, 1.1, 10.2, 19.8, 1.1, "Live: the demonstration runs from the repository. Figures are from the data loaded on 29 October 2026 (prices to 26 October).", size=18, italic=True, color=GREY)
    s_d2 = fresh("Live Demonstration (2/2): Trader Desk and Telegram")
    rows = [["Step", "Do", "You will see"],
            ["B1", "Trader tools → Silence Tax (tomato)", "Kanakapura ₹313 (16.5%); Chikkaballapur closed Thursdays; Kolar ₹0 ≠ reliable"],
            ["B2", "Crowd Simulator: 200 farmers × 10 q", "Alone ₹1,824 · all follow best ₹1,194 (−32.5%) · nearest ₹1,207 · coordinated ₹1,436"],
            ["B3", "Drag farmers to 1; flexibility b to 0", "All policies equal: the assumption is explicit"],
            ["C1", "Phone: @MandiAis_BOT → /today", "Dated digest: Ramanagara, ₹1,824, floor ₹1,316; potato prices only"],
            ["C2", "Send “onion chintamani”", "Digest for that crop and place"],
            ["C3", "Run send_daily_digest.py (the 7 am job)", "Phone buzzes; log line shows sent"],
            ["D1", "Optional: API docs", "Five insight endpoints + notify routes"]]
    table(s_d2, rows, 1.1, 1.9, 19.8, [0.9, 8.2, 10.7], row_h=1.0, size=17, bold_first_col=True)
    text(s_d2, 1.1, 10.2, 19.8, 1.1, "Fallback if the network is down: the digest builder runs offline (--dry-run); every screen also appears as a real screenshot on the results slides.", size=18, italic=True, color=GREY)

    # ---- why this mandi / what if
    s_why = fresh("Explaining the Advice: Why This Mandi, What If")
    img(s_why, "ins_farmer_why.png", 1.1, 1.8, 6.9, 8.9)
    img(s_why, "ins_farmer_whatif.png", 8.3, 1.8, 6.9, 8.9)
    bd = DD["breakdown"]
    text(s_why, 15.5, 1.8, 5.4, 8.9, [
        [("Parts add up. ", True), ("₹2,081 − 83 − 60 − 94 − 20 = ₹1,824; nearest mandi keeps ₹1,232.", False)],
        [("Why it wins. ", True), ("Expected price is ₹776 higher; extra transport ₹94 and spoilage ₹60 do not cancel it.", False)],
        [("Robust to the truck. ", True), ("Transport up to ₹3.00 per q-km: same advice (net ₹1,515).", False)],
        [("Sensitive to shelf life. ", True), ("At 5.0% spoilage a day, or no waiting: Ramanagara today, ₹1,789.", False)],
        [("Floor is indicative ", True), ("when costs are far from the defaults; the screen says so.", False)]], size=17, fill=PALE, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)

    # ---- track record
    s_track = fresh("Public Track Record on Days the Advice Had Not Seen")
    tr = DD["track"]
    rows = [["Crop", "vs nearest: win / tie / loss", "vs yesterday's best: win / tie / loss", "Floor held"]]
    for c in CROPS:
        a_ = tr[c]["all"]
        n_, h_ = a_["vs_nearest"], a_["vs_highest_yesterday"]
        rows.append([c.capitalize(), f"{100 * n_['win']:.0f} / {100 * n_['tie']:.0f} / {100 * n_['loss']:.0f} %", f"{100 * h_['win']:.0f} / {100 * h_['tie']:.0f} / {100 * h_['loss']:.0f} %",
                     (f"{100 * a_['floor_held_share']:.0f}%", ORANGE if a_["floor_held_share"] < 0.9 else GREEN)])
    table(s_track, rows, 1.1, 1.9, 9.8, [1.5, 3.2, 3.6, 1.6], row_h=0.8, size=15, head_size=14, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 3)
    cdt = CategoryChartData()
    n_days = len(tr["tomato"]["cum"])
    cdt.categories = [str(i + 1) for i in range(n_days)]
    for c in ["tomato", "onion", "potato"]:
        cdt.add_series(c.capitalize(), tr[c]["cum"])
    gfc = s_track.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(11.3), Inches(1.8), Inches(9.6), Inches(6.0), cdt)
    cc = gfc.chart
    cc.has_legend = True; cc.legend.position = XL_LEGEND_POSITION.BOTTOM; cc.legend.include_in_layout = False; cc.legend.font.size = Pt(16)
    cc.value_axis.tick_labels.font.size = Pt(16); cc.category_axis.tick_labels.font.size = Pt(12)
    cc.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    cc.has_title = True; cc.chart_title.text_frame.text = "Running mean gain over the nearest mandi, Rs per quintal (days 1 to %d; ginger, mean +Rs %d, is off this scale)" % (n_days, round(tr["ginger"]["all"]["vs_nearest"]["mean"]))
    cc.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
    for s_, col in zip(cc.plots[0].series, ["C0392B", "2E75B6", "2E8B57"]):
        s_.format.line.color.rgb = rgb(col); s_.format.line.width = Pt(2.5); s_.smooth = False
    text(s_track, 1.1, 6.3, 9.8, 2.7, [[("The honest part. ", True), ("The floor, set to hold 9 days in 10, held on 84 / 89 / 92 / 86% of replayed days.", False)],
                                        [("Why lower than the back-test: ", True), ("one multiplier fitted on half the window is the strictest of three evaluations (served rule violated 9.6–12.3%).", False)]], size=17, fill=LIGHT, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)
    text(s_track, 1.1, 9.35, 20.0, 1.6, "165 out-of-sample days, 12 May to 23 Oct 2026. A tie is a difference of at most ₹1: against yesterday's highest price the advice often picks the same action, so most days tie.", size=16, italic=True, color=GREY)

    # ---- silence tax
    s_sil = fresh("Silence Tax: What an Unreliable Mandi Costs a Trip")
    img(s_sil, "fig_silence.png", 1.1, 1.8, 10.2, 6.0)
    rows = [["Mandi", "Reported", "Surprise silence", "Known closed", "Tax per quintal"]]
    for r in DD["silence"][:7]:
        rows.append([r["name"].split(",")[0], f"{100 * r['reported_share']:.0f}%", f"{100 * r['silent_share_open_days']:.0f}%", ", ".join(r["closed_weekdays"]) or "—",
                     f"₹{r['expected_loss_per_q']:,.0f} ({r['expected_loss_pct']}%)"])
    table(s_sil, rows, 11.6, 1.8, 9.3, [2.2, 1.5, 1.8, 1.7, 2.4], row_h=0.75, size=14, head_size=13, aligns=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 4)
    text(s_sil, 1.1, 8.0, 19.8, 3.0, [[("Mean ₹%d per quintal per trip over 13 tomato mandis. " % DD["silence_mean"], True), ("Kanakapura loses ₹313 (16.5% of its price); Chikkaballapur reported on none of last year's Thursdays, so it is treated as closed that day.", False)],
                                        [("Two cautions: ", True), ("a silent day may be a closed mandi or a missed upload; and ₹0 for a cheap mandi such as Kolar does not mean it is reliable, which is why surprise silence is shown beside it.", False)]], size=18, fill=PALE, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)

    # ---- crowd
    s_crowd = fresh("Crowd Simulator: What If Everyone Follows the Advice?")
    cw = DD["crowd"]
    cdt = CategoryChartData()
    cdt.categories = [f"{n:,}" for n in cw["n"]]
    cdt.add_series("One farmer alone", cw["alone"]); cdt.add_series("Everyone follows the best action", cw["best"])
    cdt.add_series("Everyone goes to the nearest mandi", cw["nearest"]); cdt.add_series("Coordinated split", cw["coord"])
    gfc = s_crowd.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(1.1), Inches(1.8), Inches(12.6), Inches(7.2), cdt)
    cc = gfc.chart
    cc.has_legend = True; cc.legend.position = XL_LEGEND_POSITION.BOTTOM; cc.legend.include_in_layout = False; cc.legend.font.size = Pt(16)
    cc.value_axis.tick_labels.font.size = Pt(16); cc.category_axis.tick_labels.font.size = Pt(16)
    cc.has_title = True; cc.chart_title.text_frame.text = "Net revenue per quintal (Rs) against the number of farmers (10 quintals each)"
    cc.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
    for s_, col in zip(cc.plots[0].series, ["8A94A6", "C0392B", "D9822B", "2E8B57"]):
        s_.format.line.color.rgb = rgb(col); s_.format.line.width = Pt(2.75); s_.smooth = False
    c2 = DD["crowd200"]
    stat(s_crowd, 14.2, 1.8, 6.7, 2.3, f"−{c2['drop']:.1f}%", "price drop at the best yard (200 farmers)", color=RED)
    stat(s_crowd, 14.2, 4.35, 6.7, 2.3, f"₹{c2['gain']:,.0f}/q", "gain of the coordinated split", color=GREEN)
    stat(s_crowd, 14.2, 6.9, 6.7, 2.3, f"₹{c2['total']:,.0f}", "gain for the group of 200", color=GREEN)
    text(s_crowd, 1.1, 9.3, 19.8, 1.9, [[("Scenario, not a measurement. ", True), (f"The yard usually receives about {c2['yard']:.0f} quintals a day. Price flexibility b = 0.115 is an association in past data; at b = 0 every policy is equal. A field pilot is needed to measure the real response.", False)]], size=18, fill=LIGHT, margin=0.25, anchor=MSO_ANCHOR.MIDDLE)

    # ---- digest
    s_dig = fresh("Daily Digest on Telegram")
    img(s_dig, "ins_digest.png", 1.1, 1.8, 10.0, 8.9)
    text(s_dig, 11.6, 1.8, 9.3, 8.9, [
        [("Dated, always. ", True), ("Every price shows its date; the second line says how old the data is (there is no live feed).", False)],
        [("Advice only with evidence. ", True), ("Tomato, onion, ginger: best place and day with the floor. Potato, garlic: prices only.", False)],
        [("Warns about silent days. ", True), ("If the recommended mandi is usually silent on the sale weekday, it says so.", False)],
        [("Three languages, free. ", True), ("English, Kannada, Hindi; Telegram Bot API; /start, /today, /stop, or type “tomato kolar”.", False)],
        [("Logged and tested. ", True), ("Every send is logged (2 logged sends to a real account); 8 unit tests with a fake client.", False)],
        [("Not claimed: ", True), ("a farmer pilot, or a live price feed.", False)]], size=21, fill=PALE, margin=0.3, anchor=MSO_ANCHOR.MIDDLE)

    # ---- order
    idx = {s.slide_id: i for i, s in enumerate(prs.slides)}
    order_slides = [t_title, t_toc, s_intro, s_obj, s_meth, s_form, s_two, s_insmeth, s_impl, s_ov, s_d1, s_d2, s_tools, s_setup, s_res, s_val, s_floor, s_why, s_track, s_sil, s_crowd, s_dig,
                    s_leak, s_null, s_bench, s_nov, s_opt, s_wbs, s_risk, s_rep, s_sdg, s_paper, s_conc, s_ref, thanks]
    import deck_notes as DN

    keymap = {"title": t_title, "toc": t_toc, "intro": s_intro, "obj": s_obj, "meth": s_meth, "form": s_form, "two": s_two, "insmeth": s_insmeth, "impl": s_impl, "overview": s_ov,
              "demo1": s_d1, "demo2": s_d2, "tools": s_tools, "setup": s_setup, "res": s_res, "val": s_val, "floor": s_floor, "why": s_why, "track": s_track, "silence": s_sil,
              "crowd": s_crowd, "digest": s_dig, "leak": s_leak, "null": s_null, "bench": s_bench, "nov": s_nov, "opt": s_opt, "wbs": s_wbs, "risk": s_risk, "rep": s_rep, "sdg": s_sdg,
              "paper": s_paper, "conc": s_conc, "ref": s_ref, "thanks": thanks}
    for k_, sl_ in keymap.items():
        notes(sl_, DN.render(k_))
    assert set(keymap) == set(DN.N), set(DN.N) ^ set(keymap)
    reorder(prs, [idx[s.slide_id] for s in order_slides])
    prs.save(str(OUT))
    print("saved", OUT, len(order_slides), "slides")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
