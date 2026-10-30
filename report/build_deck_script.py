"""
Standalone presenter's document: speaker notes for every slide, the live-demo run-of-show with exact on-screen values, set-up checklist, fallbacks and a question bank.

    python report/build_deck_script.py        ->  report/Review2_Speaker_Notes_and_Demo.docx

Same source as the notes inside the deck (report/deck_notes.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_notes as DN  # noqa: E402

OUT = Path(__file__).resolve().parent / "Review2_Speaker_Notes_and_Demo_v2.docx"
ORDER = [("title", "Title"), ("toc", "Table of contents"), ("intro", "Introduction and problem statement"), ("obj", "Objectives"), ("meth", "Methodology and architecture"),
         ("form", "Key formulation"), ("two", "Decision intelligence and spillover"), ("insmeth", "Insight features: method"), ("impl", "Implementation and integration"),
         ("overview", "What you will see"), ("demo1", "LIVE DEMO 1/2: farmer tool"), ("demo2", "LIVE DEMO 2/2: trader desk and Telegram"), ("tools", "Tools and code quality"),
         ("setup", "Experimental setup"), ("res", "Results: decision quality"), ("val", "Statistical validation"), ("floor", "Verified floors and back-test"),
         ("why", "Why this mandi, what if"), ("track", "Public track record"), ("silence", "Silence tax"), ("crowd", "Crowd simulator"), ("digest", "Daily digest on Telegram"),
         ("leak", "Look-ahead audit"), ("null", "Council, shocks, spillover, language layer"), ("bench", "Comparative benchmarking"), ("nov", "Novelty"), ("opt", "Optimisation and ablation"),
         ("wbs", "WBS and critical path"), ("risk", "Schedule and risk"), ("rep", "Report and documentation"), ("sdg", "SDG mapping"), ("paper", "Research paper status"),
         ("conc", "Conclusion and future work"), ("ref", "References"), ("thanks", "Thank you")]
NAVY = RGBColor(0x1F, 0x2A, 0x44)
BLUE = RGBColor(0x1F, 0x4E, 0x79)


def shade(cell, hex_):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hex_)
    tc.append(sh)


def rich(par, text, size=10.5):
    """**bold** and `code` inside a paragraph."""
    for part in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not part:
            continue
        if part.startswith("**"):
            r = par.add_run(part[2:-2]); r.bold = True
        elif part.startswith("`"):
            r = par.add_run(part[1:-1]); r.font.name = "Consolas"
        else:
            r = par.add_run(part)
        r.font.size = Pt(size)


def para(doc, text="", size=10.5, bold=False, italic=False, color=None, space=4, style=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(space)
    if bold or italic or color:
        r = p.add_run(text); r.bold = bold; r.italic = italic; r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    else:
        rich(p, text, size)
    return p


def table(doc, rows, widths, header=True, size=9.5):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(widths[j])
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            rich(p, str(val), size)
            if header and i == 0:
                shade(c, "1F4E79")
                for r in p.runs:
                    r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
            elif i % 2 == 0:
                shade(c, "EEF4F9")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def main() -> None:
    d = Document()
    sec = d.sections[0]
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.6)
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)

    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("MandiSense AI: Review 2\nPresenter's Script, Live Demo and Question Bank")
    r.bold = True; r.font.size = Pt(20); r.font.color.rgb = NAVY
    para(d, "Project Work Phase 2 (23DS7PWPP2) · B.M.S. College of Engineering · Srijan C Vachadmath, Manohara Salmani, Shreejith Shah · Guide: Dr. Kalyan N", 10, italic=True, space=8).alignment = WD_ALIGN_PARAGRAPH.CENTER

    d.add_heading("How to use this document", level=1)
    for line in [
        "The same text is in the notes pane of every slide of **MandiSense_Review2_Final.pptx** (open Presenter View). This document adds the set-up checklist, the demo run-of-show with the exact on-screen values, fall-backs and a question bank.",
        "Each slide is tagged **CORE** (always present) or **SKIP IF SHORT** (drop it if time is tight). The **25-minute path** is listed below; the full deck with the live demo takes about 45 minutes.",
        "All numbers are from the data loaded on **29 October 2026** (prices up to **26 October 2026**). If the data are reloaded, re-run `python report/build_insight_assets.py` and re-check every number before presenting.",
        "Speak the words under SAY almost exactly as written; the SHOW line is a stage direction, not to be read aloud.",
    ]:
        para(d, line, style="List Bullet")

    d.add_heading("The whole project in six lines", level=1)
    para(d, "If you remember nothing else, say these six lines in this order. Every slide below expands one of them.", italic=True, space=3)
    for line in DN.STORY:
        para(d, line, style="List Number", space=2)

    d.add_heading("Say it simply: a small glossary", level=1)
    para(d, "The slides use a few technical words. When you speak, use the plain version on the right. If an examiner uses the technical word, you can answer with the plain version and then say the technical word once.", italic=True, space=3)
    table(d, [["Technical word on the slide", "What to say"]] + [[a, b] for a, b in DN.GLOSSARY], [5.2, 11.8])

    d.add_heading("Rules for speaking", level=1)
    for line in ["Use short sentences. Pause after each number.",
                 "Say the words under SAY almost exactly as written. They are written to be spoken, not read from the slide.",
                 "Never read a formula aloud. Point at it and say what it does.",
                 "Round numbers when you speak (about 1,800 rupees), unless the slide and the screen show the exact figure and you are pointing at it.",
                 "If you do not know an answer, say: 'We have not tested that. It is in our future work.'"]:
        para(d, line, style="List Bullet", space=2)

    d.add_heading("Time plan", level=1)
    rows = [["#", "Slide", "Tag", "Min"]]
    tot = 0.0
    for i, (k, name) in enumerate(ORDER, 1):
        n = DN.N[k]
        tot += n["minutes"]
        rows.append([i, name, n["tier"], f"{n['minutes']:g}"])
    rows.append(["", "**Total, full deck**", "", f"**{tot:.0f}**"])
    table(d, rows, [1.0, 10.5, 3.2, 1.5])
    short = sum(DN.N[k]["minutes"] for k in DN.SHORT_PATH)
    para(d, f"**25-minute path** ({short:.0f} min including both demo parts): " + ", ".join(dict(ORDER)[k] for k in DN.SHORT_PATH) + ".", space=6)

    d.add_heading("Set-up checklist (do this before the panel enters)", level=1)
    table(d, [["When", "Action"]] + [[a, b] for a, b in DN.DEMO_SETUP], [2.2, 14.8])

    d.add_page_break()
    d.add_heading("Slide-by-slide script", level=1)
    for i, (k, name) in enumerate(ORDER, 1):
        n = DN.N[k]
        h = d.add_heading(f"Slide {i} · {name}", level=2)
        para(d, f"[{n['tier']} · about {n['minutes']:g} min]", 9.5, italic=True, color=BLUE, space=2)
        para(d, "SAY", 9.5, bold=True, color=NAVY, space=1)
        for chunk in n["say"].split("\n"):
            if chunk.strip():
                para(d, chunk.strip(), space=3)
        if n["show"]:
            para(d, "SHOW / CLICK", 9.5, bold=True, color=NAVY, space=1)
            para(d, n["show"], space=3)
        if n["quote"]:
            para(d, "NUMBERS TO QUOTE", 9.5, bold=True, color=NAVY, space=1)
            for q in n["quote"]:
                para(d, q, style="List Bullet", space=1)
        if n["ask"]:
            para(d, "IF ASKED", 9.5, bold=True, color=NAVY, space=1)
            for q, a in n["ask"]:
                para(d, f"**Q:** {q}", space=1)
                para(d, f"**A:** {a}", space=3)
        if n["nxt"]:
            para(d, f"**Transition:** {n['nxt']}", 10, space=6)

    d.add_page_break()
    d.add_heading("Live demonstration: run-of-show", level=1)
    para(d, "Three parts, about ten minutes in total. Click exactly as written; the right-hand column is what must appear on screen. If it does not, use the fall-backs on the next page.", space=6)
    rows = [["Step", "Where / click", "Settings", "Must appear on screen", "Say"]]
    group = ""
    for sid, grp, click, settings, see, say in DN.DEMO_STEPS:
        if grp and grp != group:
            rows.append(["", f"**{grp}**", "", "", ""])
            group = grp
        rows.append([sid, click, settings, see, say])
    table(d, rows, [1.1, 3.6, 3.0, 6.2, 3.4], size=8.5)

    d.add_heading("If something goes wrong", level=1)
    table(d, [["Situation", "What to do"]] + [[a, b] for a, b in DN.CONTINGENCY], [4.5, 12.5])

    d.add_heading("Question bank", level=1)
    para(d, "Answers are short on purpose: say the first sentence, then stop and wait.", italic=True, space=4)
    for q, a in DN.QA:
        para(d, f"**Q. {q}**", space=1)
        para(d, a, space=6)

    d.add_heading("Three sentences to keep in your head", level=1)
    for line in ["We train on what the farmer actually keeps, and that, not a fancier loss, is what improves decisions in all four crops.",
                 "We publish a claim only when the evidence supports it, which is why the council, the shocks and the spillover are reported as not served.",
                 "We show the farmer the real score, including the 84 percent floor and the crowd scenario's stated assumption, because trust comes from what you admit."]:
        para(d, line, style="List Number")

    d.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
