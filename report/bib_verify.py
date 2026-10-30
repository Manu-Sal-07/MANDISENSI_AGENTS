"""
Look every candidate reference up in Crossref and arXiv and keep only records whose title matches.

    python report/bib_verify.py            ->  report/generated/bib_verified.json and a printed summary

A reference enters the bibliography only if a public record with a near-identical title (and, where known, the right first author and
year) was found. Nothing is filled in from memory. Records that fail are listed so they can be fixed or dropped.
"""

from __future__ import annotations

import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bib_candidates import C  # noqa: E402

OUT = Path(__file__).resolve().parent / "generated" / "bib_verified.json"
UA = {"User-Agent": "MandiSense-thesis-bibliography/1.0 (mailto:7enzomen7@gmail.com)"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"<[^>]+>", "", s.lower().replace("-", " ").replace(":", " "))).strip()


def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def crossref(title: str):
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5})
    items = json.loads(get(f"https://api.crossref.org/works?{q}"))["message"]["items"]
    out = []
    for it in items:
        t = (it.get("title") or [""])[0]
        issued = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        authors = [(a.get("family", ""), a.get("given", "")) for a in it.get("author", [])]
        out.append({"src": "crossref", "title": re.sub(r"<[^>]+>", "", t), "year": issued, "authors": authors, "container": (it.get("container-title") or [""])[0],
                    "volume": it.get("volume", ""), "issue": it.get("issue", ""), "pages": it.get("page", ""), "doi": it.get("DOI", ""), "type": it.get("type", ""),
                    "publisher": it.get("publisher", ""), "article": it.get("article-number", "")})
    return out


def arxiv(title: str):
    q = urllib.parse.urlencode({"search_query": f'ti:"{title}"', "max_results": 3})
    root = ET.fromstring(get(f"http://export.arxiv.org/api/query?{q}"))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        t = " ".join((e.findtext("a:title", "", ns) or "").split())
        auth = []
        for a in e.findall("a:author", ns):
            name = (a.findtext("a:name", "", ns) or "").split()
            if name:
                auth.append((name[-1], " ".join(name[:-1])))
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        year = int((e.findtext("a:published", "", ns) or "0")[:4] or 0)
        out.append({"src": "arxiv", "title": t, "year": year, "authors": auth, "container": "arXiv", "arxiv": re.sub(r"v\d+$", "", aid), "type": "preprint"})
    return out


def best(key, title, author, year, venue):
    cands = []
    try:
        cands += crossref(title)
    except Exception as exc:
        print("  crossref error", exc)
    if any(w in venue.lower() for w in ("arxiv", "icassp", "neurips", "aaai")) or not cands:
        try:
            time.sleep(1.0)
            cands += arxiv(title)
        except Exception as exc:
            print("  arxiv error", exc)
    scored = []
    for c in cands:
        s = sim(title, c["title"])
        if author and c["authors"] and norm(author) not in norm(" ".join(a[0] for a in c["authors"][:3])):
            s -= 0.15
        if year and c["year"] and abs(int(c["year"]) - year) > 2 and c["src"] == "crossref":
            s -= 0.1
        scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    return scored[0] if scored else (0, None)


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    res, bad = {}, []
    for key, title, author, year, venue in C:
        s, c = best(key, title, author, year, venue)
        ok = c is not None and s >= 0.86
        # for conference papers that also exist as journal/preprint records prefer the arXiv/publisher record with the best score
        print(f"{'OK ' if ok else 'BAD'} {s:.2f} {key:18s} {(c or {}).get('title', '')[:70]} | {(c or {}).get('year')} | {(c or {}).get('container', '')[:30]}")
        if ok:
            res[key] = {**c, "score": round(s, 3), "wanted_year": year}
        else:
            bad.append((key, title, s))
        time.sleep(0.4)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nverified {len(res)} of {len(C)}; failed {len(bad)}")
    for k, t, s in bad:
        print("  FAILED", k, f"{s:.2f}", t[:90])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
