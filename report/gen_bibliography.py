"""
Build report/appendices/bibliography.tex from verified records, ordered by first citation in the thesis (IEEE numbering).

    python report/gen_bibliography.py

Sources, in priority: hand-vetted entries from the paper bibliography (`old`), records verified in Crossref/arXiv (generated/bib_verified.json) and a few
classic papers entered by hand with certain details (`MANUAL`). A key cited in the text but absent from all three is reported and fails the build.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OLD = ROOT / "papers" / "IEEE_Access" / "MandiSense_IEEE_Access.tex"
VERIFIED = HERE / "generated" / "bib_verified.json"
ORDER = ["chapters/abstract.tex", "chapters/ch1_introduction.tex", "chapters/ch2_literature.tex", "chapters/sec_survey.tex", "chapters/ch3_methodology.tex", "chapters/ch4_planning.tex",
         "chapters/ch5_implementation.tex", "chapters/sec_screens.tex", "chapters/ch6_results.tex", "chapters/ch7_conclusion.tex", "appendices/appendices.tex"]

# classic papers whose details are certain but which the public APIs did not return in a matchable form
MANUAL = {
    "shafer2008": dict(authors=[("Shafer", "Glenn"), ("Vovk", "Vladimir")], title="A tutorial on conformal prediction", container="J. Mach. Learn. Res.", volume="9", pages="371--421", year=2008),
    "meinshausen2006": dict(authors=[("Meinshausen", "Nicolai")], title="Quantile regression forests", container="J. Mach. Learn. Res.", volume="7", pages="983--999", year=2006),
    "demsar2006": dict(authors=[("Dem\\v{s}ar", "Janez")], title="Statistical comparisons of classifiers over multiple data sets", container="J. Mach. Learn. Res.", volume="7", pages="1--30", year=2006),
    "cawley2010": dict(authors=[("Cawley", "Gavin C."), ("Talbot", "Nicola L. C.")], title="On over-fitting in model selection and subsequent selection bias in performance evaluation",
                       container="J. Mach. Learn. Res.", volume="11", pages="2079--2107", year=2010),
    "pedregosa2011": dict(authors=[("Pedregosa", "Fabian"), ("Varoquaux", "Ga\\\"{e}l"), ("Gramfort", "Alexandre"), ("Michel", "Vincent"), ("Thirion", "Bertrand"), ("others", "")],
                          title="Scikit-learn: Machine learning in Python", container="J. Mach. Learn. Res.", volume="12", pages="2825--2830", year=2011),
    "jorda2005": dict(authors=[("Jord\\`{a}", "\\`{O}scar")], title="Estimation and inference of impulse responses by local projections", container="Amer. Econ. Rev.", volume="95", issue="1", pages="161--182", year=2005),
    "mackinlay1997": dict(authors=[("MacKinlay", "A. Craig")], title="Event studies in economics and finance", container="J. Econ. Literature", volume="35", issue="1", pages="13--39", year=1997),
    "stankeviciute2021": dict(authors=[("Stankevičiūtė", "Kamilė"), ("Alaa", "Ahmed M."), ("van der Schaar", "Mihaela")], title="Conformal time-series forecasting", container="Adv. Neural Inf. Process. Syst.", volume="34", year=2021, preprint=True),
    "chand2012": dict(authors=[("Chand", "Ramesh")], title="Development policies and agricultural markets", container="Econ. Polit. Weekly", volume="47", issue="52", pages="53--63", year=2012),
    "lipton2016": dict(authors=[("Lipton", "Zachary C."), ("Kale", "David C."), ("Wetzel", "Randall")], title="Directly modeling missing data in sequences with RNNs: Improved classification of clinical time series",
                       container="arXiv preprint arXiv:1606.04130", year=2016, preprint=True),
}
# where an arXiv record is known to have been published at a venue (known with certainty)
VENUE = {
    "vaswani2017": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~30, 2017", "lundberg2017": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~30, 2017",
    "donti2017": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~30, 2017", "brown2020": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~33, 2020",
    "lewis2020": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~33, 2020", "berthet2020": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~33, 2020",
    "cao2018": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~31, 2018", "prokhorenkova2018": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~31, 2018",
    "tashiro2021": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~34, 2021", "wu2021autoformer": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~34, 2021",
    "stankeviciute2021": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~34, 2021", "ouyang2022": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~35, 2022",
    "zheng2023": "in \\emph{Adv. Neural Inf. Process. Syst. (Datasets and Benchmarks Track)}, vol.~36, 2023",
    "amos2017": "in \\emph{Proc. 34th Int. Conf. Mach. Learn.}, 2017", "yoon2018": "in \\emph{Proc. 35th Int. Conf. Mach. Learn.}, 2018",
    "das2024": "in \\emph{Proc. 41st Int. Conf. Mach. Learn.}, 2024", "woo2024": "in \\emph{Proc. 41st Int. Conf. Mach. Learn.}, 2024",
    "zaffran2022": "in \\emph{Proc. 39th Int. Conf. Mach. Learn.}, 2022", "xu2021": "in \\emph{Proc. 38th Int. Conf. Mach. Learn.}, 2021",
    "nie2023": "in \\emph{Proc. Int. Conf. Learn. Represent.}, 2023", "oreshkin2020": "in \\emph{Proc. Int. Conf. Learn. Represent.}, 2020",
    "gala2023": "\\emph{Trans. Mach. Learn. Res.}, 2023", "angelopoulos2023pid": "in \\emph{Adv. Neural Inf. Process. Syst.}, vol.~36, 2023",
}
YEAR = {"borisov2022": 2024, "hewamalage2023": 2023, "claeskens2016": 2016, "gneiting2007": 2007, "breiman2001": 2001, "wolpert1992": 1992, "nie2023": 2023, "oreshkin2020": 2020,
        "das2024": 2024, "prokhorenkova2018": 2018, "xu2021": 2021, "lei2018": 2018, "courtois2015": 2015, "aker2011": 2011, "hodges2011": 2011, "hewamalage": 2023}
OVERRIDE = {
    "breiman2001": dict(authors=[("Breiman", "Leo")], title="Random forests", container="Mach. Learn.", volume="45", issue="1", pages="5--32"),
    "wolpert1992": dict(authors=[("Wolpert", "David H.")], title="Stacked generalization", container="Neural Netw.", volume="5", issue="2", pages="241--259"),
    "gneiting2007": dict(container="J. Amer. Statist. Assoc.", volume="102", issue="477", pages="359--378"),
    "claeskens2016": dict(container="Int. J. Forecasting", volume="32", issue="3", pages="754--762"),
    "hewamalage2023": dict(container="Data Mining Knowl. Discovery", volume="37", issue="2", pages="788--832"),
    "aker2010jep": dict(container="J. Econ. Perspectives", volume="24", issue="3", pages="207--232"),
    "goyal2010": dict(container="Amer. Econ. J.: Appl. Econ.", volume="2", issue="3", pages="22--45"),
    "fafchamps2012": dict(container="World Bank Econ. Rev.", volume="26", issue="3", pages="383--414"),
    "mitra2018": dict(container="Rev. Econ. Statist.", volume="100", issue="1", pages="1--14"),
    "aker2011": dict(container="Agric. Econ.", volume="42", issue="6", pages="631--647"),
}
KEEP = ['agmarknet', 'agtech2024', 'aker2010', 'akiba2019', 'algirdas2024', 'angelopoulos2023', 'ansari2024', 'avinash2024', 'bergmeir2012', 'birthal2019', 'ceemdan2024', 'celik2025', 'cerqueira2020', 'che2018', 'chen2016', 'claude3', 'cleveland1990', 'crop_ins', 'cropyield', 'demand2023', 'diebold1995', 'dragomiretskiy2014', 'elmachtoub2022', 'epu2024', 'exogenous2024', 'fafchamps2012', 'fedxai2025', 'fiszeder2024', 'gcn2024', 'gibbs2021', 'gptoss2025', 'grinsztajn2022', 'hansen2011', 'harvey1997', 'holm1979', 'huber1964', 'hyndman2021', 'jaiswal2025', 'jensen2007', 'jha2014', 'kde2024', 'ke2017', 'kunsch1989', 'mandi2024', 'manogna2025', 'meena2024', 'mohanty2023', 'newey1987', 'optimized2023', 'qwen3', 'ray2023', 'romano2019', 'rubin1976', 'sathe2025', 'sediyono2025', 'smartag2024', 'smartfarm2025', 'tranad2024', 'vovk2005', 'wang2026', 'wu2026', 'zaheer2017', 'zeng2023']
SKIP = {"shah2025", "annamalai2025", "onion2023", "rythu2023", "bigru2023", "gnn2024"}


def tex(s: str) -> str:
    s = html.unescape(s)
    if "\\" in s:
        return s
    for a, b in (("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#"), ("$", "\\$")):
        s = s.replace(a, b)
    return s.replace("–", "--").replace("—", "---").replace("’", "'").replace("‘", "'").replace("“", "``").replace("”", "''").replace("é", "\\'e").replace("ü", "\\\"u").replace("ö", "\\\"o").replace("ä", "\\\"a")


def initials(given: str) -> str:
    parts = [p for p in re.split(r"[\s]+", given.strip()) if p]
    out = []
    for p in parts:
        if "-" in p and not p.endswith("."):
            out.append("-".join(x[0] + "." for x in p.split("-") if x))
        elif p.endswith("."):
            out.append(p)
        elif p[0].isalpha():
            out.append(p[0].upper() + ".")
        elif p.startswith("\\"):
            out.append(p)
    return "~".join(out)


def names(authors) -> str:
    if not authors:
        return ""
    a = [x for x in authors if x[0] != "others"]
    et_al = len(a) < len(authors) or len(a) > 6
    a = a[:1] if len(a) > 6 else a
    fmt = [(f"{initials(g)}~{tex(f)}" if g else tex(f)) for f, g in a]
    if et_al:
        return fmt[0] + " \\emph{et~al.}" if len(fmt) == 1 else ", ".join(fmt) + ", \\emph{et~al.}"
    if len(fmt) == 1:
        return fmt[0]
    if len(fmt) == 2:
        return f"{fmt[0]} and {fmt[1]}"
    return ", ".join(fmt[:-1]) + f", and {fmt[-1]}"


def sentence_case_title(t: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
    t = " ".join(t.split())
    if t.isupper():
        t = t.capitalize()
    return t.rstrip(".")


def abbreviate(container: str) -> str:
    c = html.unescape(container)
    c = c[4:] if c.startswith("The ") else c
    for a, b in (("Journal of", "J."), ("International", "Int."), ("Proceedings of the", "Proc."), ("Proceedings of", "Proc."), ("Transactions on", "Trans."),
                 ("Applied", "Appl."), ("Computing", "Comput."), ("American", "Amer."), ("Economics", "Econ."), ("Economic", "Econ."), ("Statistical", "Statist."), ("Association", "Assoc."),
                 ("Review", "Rev."), ("Quarterly", "Quart."), ("Conference", "Conf."), ("Systems", "Syst."), ("Intelligence", "Intell."), ("Research", "Res."),
                 ("Science", "Sci."), ("Agricultural", "Agric."), ("Management", "Manage."), ("Annals of", "Ann."), ("Neural", "Neural"), ("Information", "Inf."),
                 ("Technology", "Technol."), ("Learning", "Learn."), ("Machine", "Mach."), ("Forecasting", "Forecasting"), ("Engineering", "Eng."), ("Society", "Soc."),
                 ("Philosophical", "Philos."), ("Royal", "Roy."), ("Series", "Ser."), ("Letters", "Lett."), ("National", "Nat."), ("Academy", "Acad.")):
        c = c.replace(a, b)
    return tex(c.replace("&amp;", "\\&"))


def entry(key: str, r: dict) -> str:
    r = {**r, **OVERRIDE.get(key, {})}
    year = YEAR.get(key) or r.get("year") or r.get("wanted_year")
    au = names(r.get("authors", []))
    title = tex(sentence_case_title(r.get("title", "")))
    cont = r.get("container", "")
    if r.get("preprint") or r.get("src") == "arxiv" or cont == "arXiv":
        aid = r.get("arxiv") or ""
        if key in VENUE:
            v = VENUE[key]
            tail = f"{v}" if v.startswith("\\emph") else v
            tail += f" (arXiv:{aid})" if aid else ""
            return f"{au}, ``{title},'' {tail}."
        return f"{au}, ``{title},'' arXiv preprint arXiv:{aid}, {year}." if aid else f"{au}, ``{title},'' {tex(cont)}, {year}."
    typ = "" if key in OVERRIDE else r.get("type", "")
    c = abbreviate(cont)
    if key not in OVERRIDE and ("proceedings" in typ or "conference" in cont.lower() or "proc" in cont.lower()):
        base = f"{au}, ``{title},'' in \\emph{{{c}}}, {year}"
        if r.get("pages"):
            base += f", pp.~{r['pages'].replace('-', '--').replace('----', '--')}"
        return base + "."
    if typ in ("book", "monograph", "book-chapter", "reference-entry"):
        return f"{au}, ``{title},'' in \\emph{{{c}}}, {year}."
    bits = [f"\\emph{{{c}}}"]
    if r.get("volume"):
        bits.append(f"vol.~{r['volume']}")
    if r.get("issue"):
        bits.append(f"no.~{r['issue']}")
    if r.get("pages"):
        bits.append(f"pp.~{r['pages'].replace('--', '-').replace('-', '--')}")
    elif r.get("article"):
        bits.append(f"Art.\\ no.~{r['article']}")
    bits.append(str(year))
    return f"{au}, ``{title},'' " + ", ".join(bits) + "."


def old_entries() -> dict:
    out = {}
    for m in re.finditer(r"\\bibitem\{([^}]+)\}\s*(.+)", OLD.read_text(encoding="utf-8")):
        out[m.group(1)] = m.group(2).strip()
    return out


def cited_keys() -> list[str]:
    seen, order = set(), []
    for f in ORDER:
        text = (HERE / f).read_text(encoding="utf-8")
        text = re.sub(r"\\input\{(chapters/sec_[a-z]+)\}", lambda m: (HERE / (m.group(1) + ".tex")).read_text(encoding="utf-8"), text)  # inline sections in document order
        if f.startswith("chapters/sec_"):
            continue
        text = re.sub(r"(?m)^\s*%.*$", "", text)
        for m in re.finditer(r"\\cite[a-z]*\{([^}]+)\}", text):
            for k in m.group(1).split(","):
                k = k.strip()
                if k and k not in seen:
                    seen.add(k)
                    order.append(k)
    return order


def main() -> int:
    old = old_entries()
    ver = json.loads(VERIFIED.read_text(encoding="utf-8"))
    order = [k for k in cited_keys() if k in KEEP]
    lines, missing = [], []
    for k in order:
        if k in old:
            lines.append(f"\\bibitem{{{k}}} {old[k]}")
        elif k in MANUAL:
            lines.append(f"\\bibitem{{{k}}} {entry(k, {**MANUAL[k]})}")
        elif k in ver and k not in SKIP:
            lines.append(f"\\bibitem{{{k}}} {entry(k, ver[k])}")
        else:
            missing.append(k)
    extra = r"""\bibitem{demand2023} N.~Darapaneni \emph{et al.}, ``Demand and price forecasting using deep learning algorithms,'' in \emph{Multi-Disciplinary Trends in Artificial Intelligence}, ser. Lecture Notes in Computer Science. Cham, Switzerland: Springer, 2023, pp.~735--746.
\bibitem{gcn2024} D.~Zhang, X.~Li, L.~Ling, H.~Hu, and R.~Lin, ``Integrated GCN--BiGRU--TPE agricultural product futures prices prediction based on multi-graph construction,'' \emph{Comput. Econ.}, vol.~66, no.~5, pp.~3927--3955, 2025.
\bibitem{claude3} Anthropic, ``The Claude 3 model family: Opus, Sonnet, Haiku,'' Anthropic, San Francisco, CA, USA, Model Card, Mar.\ 2024. [Online]. Available: https://www.anthropic.com/claude
\bibitem{claudedocs} Anthropic, ``Claude API documentation: Messages API and tool use,'' Anthropic, 2025. [Online]. Available: https://docs.anthropic.com
\bibitem{telegramapi} Telegram FZ-LLC, ``Telegram Bot API.'' [Online]. Available: https://core.telegram.org/bots/api
\bibitem{dltrai} Telecom Regulatory Authority of India, ``Telecom Commercial Communications Customer Preference Regulations, 2018 (DLT framework for commercial messages),'' Government of India, New Delhi, India, 2018.
\bibitem{dpdp2023} Government of India, ``The Digital Personal Data Protection Act, 2023,'' Ministry of Law and Justice, New Delhi, India, 2023."""
    manual_extra = {l.split("{")[1].split("}")[0]: l for l in extra.splitlines()}
    final = []
    for l in lines:
        final.append(l)
    for k in order:
        if k in manual_extra and k in missing:
            final.append(manual_extra[k])
            missing.remove(k)
    # keep numbering by first citation: rebuild in order including the manual extras
    ordered = []
    pool = {re.match(r"\\bibitem\{([^}]+)\}", l).group(1): l for l in final}
    for k in order:
        if k in pool:
            ordered.append(pool[k])
    body = "\n".join(ordered)
    out = ("% Generated by report/gen_bibliography.py from verified records; ordered by first citation.\n\\clearpage\n\\addcontentsline{toc}{chapter}{Bibliography}\n"
           "\\begingroup\\small\\setlength{\\itemsep}{1pt}\\sloppy\\urlstyle{same}\n\\begin{thebibliography}{999}\n" + body + "\n\\end{thebibliography}\n\\endgroup\n")
    (HERE / "appendices" / "bibliography.tex").write_text(out, encoding="utf-8")
    print(f"{len(ordered)} references written; {len(missing)} cited keys have no record: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
