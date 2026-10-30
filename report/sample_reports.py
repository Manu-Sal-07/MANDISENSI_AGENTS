"""
Illustration only: two SAMPLE similarity / AI-text report pages with fictional details.
Not an official report and not derived from any real submission.

    python report/sample_reports.py  ->  report/sample_similarity_index.pdf, sample_plag_index.pdf, sample_both_pages.pdf
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

OUT = Path(__file__).resolve().parent
BLUE, RED, GREY = "#2b6ea8", "#9a1b3a", "#555555"
W, H = 8.27, 11.69  # A4


def base(title: str):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(plt.Rectangle((0.03, 0.02), 0.94, 0.96, fill=False, ec="#888888", lw=1.5))
    ax.text(0.5, 0.925, title, ha="center", fontsize=17, fontweight="bold", color="#1a2a44")
    ax.text(0.5, 0.895, "SAMPLE REPORT  -  ILLUSTRATION ONLY", ha="center", fontsize=10, color=RED, fontweight="bold")
    ax.plot([0.07, 0.93], [0.88, 0.88], color=BLUE, lw=3)
    ax.text(0.5, 0.5, "SAMPLE - NOT AN OFFICIAL REPORT", rotation=35, ha="center", va="center", fontsize=26, color="#cc0000", alpha=0.13, fontweight="bold")
    ax.text(0.5, 0.035, "Illustration made for demonstration. Details are fictional. This is not output of any plagiarism or AI-detection tool and must not be submitted or presented as one.",
            ha="center", fontsize=7, color=GREY, wrap=True)
    return fig, ax


def table(ax, rows, y0, label_x=0.1, val_x=0.38, step=0.026):
    for i, (k, v) in enumerate(rows):
        y = y0 - i * step
        ax.text(label_x, y, k, fontsize=10, color=RED)
        ax.text(val_x, y, v, fontsize=10, color=GREY)


def pie(fig, rect, vals, labels, colors, title=None):
    a = fig.add_axes(rect)
    a.pie(vals, colors=colors, startangle=90, counterclock=False, wedgeprops={"edgecolor": "#777", "linewidth": 0.6})
    a.legend(labels, loc="upper center", bbox_to_anchor=(0.5, 0.0), fontsize=8.5, frameon=False, ncol=1)
    if title:
        a.set_title(title, fontsize=10, fontweight="bold")
    return a


def page_similarity() -> plt.Figure:
    fig, ax = base("Similarity Report (Sample)")
    ax.text(0.1, 0.845, "Submission Information", fontsize=12, style="italic", fontweight="bold", color=BLUE)
    table(ax, [("Author Name", "A. Student (fictional)"), ("Title", "Sample Thesis Title"), ("Paper/Submission ID", "SAMPLE-0000"),
               ("Submitted by", "sample@example.org"), ("Submission Date", "2026-01-01"), ("Total Pages, Total Words", "96, 27,580"),
               ("Document type", "Research Report")], 0.815)
    ax.text(0.1, 0.62, "Result Information", fontsize=12, style="italic", fontweight="bold", color=BLUE)
    ax.text(0.1, 0.59, "Similarity", fontsize=11, color=RED)
    ax.text(0.22, 0.59, "6 %", fontsize=14, fontweight="bold", color="#1b7a1b")
    ax.add_patch(plt.Rectangle((0.1, 0.565), 0.8, 0.012, fc="#eeeeee", ec="none"))
    ax.add_patch(plt.Rectangle((0.1, 0.565), 0.8 * 0.06, 0.012, fc="#6fb36f", ec="none"))
    pie(fig, [0.1, 0.33, 0.33, 0.2], [3.4, 1.9, 0.7], ["Journal/\nPublication 3.4%", "Internet 1.9%", "Student\nPaper 0.7%"], ["#ff6b6b", "#eeaaaa", "#e6d6f0"], "Sources Type")
    pie(fig, [0.57, 0.33, 0.33, 0.2], [0.9, 1.4, 5.2], ["Quotes 0.9%", "Words < 14: 1.4%", "Ref/Bib 5.2%"], ["#eeaaaa", "#e6d6f0", "#c9d8ea"], "Report Content")
    table(ax, [("Quotes", "Not Excluded"), ("References/Bibliography", "Not Excluded"), ("Source: Excluded < 14 Words", "Not Excluded"), ("Excluded Source", "0 %")], 0.235, step=0.024)
    table(ax, [("Language", "English"), ("Student Papers", "Yes"), ("Journals & publishers", "Yes"), ("Internet or Web", "Yes")], 0.235, label_x=0.55, val_x=0.78, step=0.024)
    ax.text(0.1, 0.1, "Grade bands (illustrative): A 0-10%  |  B 11-40%  |  C 41-60%  |  D 61-100%    ->    this sample: A", fontsize=8.5, color=GREY)
    return fig


def page_ai() -> plt.Figure:
    fig, ax = base("AI Content Detection Report (Sample)")
    ax.text(0.1, 0.845, "Submission Information", fontsize=12, style="italic", fontweight="bold", color=BLUE)
    table(ax, [("Author Name", "A. Student (fictional)"), ("Title", "Sample Thesis Title"), ("Paper-Submission ID", "SAMPLE-0000"),
               ("Submitted By", "sample@example.org"), ("Submission Date", "2026-01-01"), ("Total [Pages,Sentences,Words]", "[96, 1,402, 27,580]"),
               ("Document type", "Research Report"), ("Language", "English")], 0.815)
    ax.text(0.1, 0.60, "Result Information", fontsize=12, style="italic", fontweight="bold", color=BLUE)
    ax.text(0.1, 0.57, "AI Text:", fontsize=11, color=RED)
    ax.text(0.2, 0.57, "2 %", fontsize=14, fontweight="bold", color="#cc0000")
    pie(fig, [0.28, 0.27, 0.44, 0.28], [2, 98], ["AI Text 2.0%", "Human Text 98.0%"], ["#1ba1e2", "#f1f4f1"])
    ax.text(0.1, 0.14, "Note: automated detectors are not always accurate; a score is an indication, not proof.", fontsize=8.5, color=GREY)
    return fig


if __name__ == "__main__":
    p1, p2 = page_similarity(), page_ai()
    for name, f in (("sample_similarity_index.pdf", p1), ("sample_plag_index.pdf", p2)):
        with PdfPages(OUT / name) as pdf:
            pdf.savefig(f)
    with PdfPages(OUT / "sample_both_pages.pdf") as pdf:
        pdf.savefig(p1); pdf.savefig(p2)
    for n, f in (("sim", p1), ("ai", p2)):
        f.savefig(OUT / f"sample_{n}_preview.png", dpi=60)
    print("done")
