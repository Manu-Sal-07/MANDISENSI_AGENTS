"""
Second pass: retry the references the first pass could not match, with the author as a filter (Crossref) or by identifier (arXiv).

    python report/bib_verify2.py     ->  merges into report/generated/bib_verified.json
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bib_candidates import C  # noqa: E402
from bib_verify import OUT, get, norm, sim  # noqa: E402

ARXIV_IDS = {"vaswani2017": "1706.03762", "nie2023": "2211.14730", "oreshkin2020": "1905.10437", "das2024": "2310.10688", "bai2018": "1803.01271",
             "prokhorenkova2018": "1706.09516", "wu2021autoformer": "2106.13008", "lipton2016": "1606.04130", "xu2021": "2010.09107",
             "stankeviciute2021": "2106.07374", "gptoss2025": "2508.10925", "torres2011": None}
CROSSREF_DOI = {}  # filled when a known DOI is needed


def crossref_author(title, surname, year):
    q = {"query.title": title, "rows": 12}
    if surname:
        q["query.author"] = surname
    items = json.loads(get("https://api.crossref.org/works?" + urllib.parse.urlencode(q)))["message"]["items"]
    out = []
    for it in items:
        t = (it.get("title") or [""])[0]
        issued = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        authors = [(a.get("family", ""), a.get("given", "")) for a in it.get("author", [])]
        out.append({"src": "crossref", "title": t, "year": issued, "authors": authors, "container": (it.get("container-title") or [""])[0], "volume": it.get("volume", ""),
                    "issue": it.get("issue", ""), "pages": it.get("page", ""), "doi": it.get("DOI", ""), "type": it.get("type", ""), "publisher": it.get("publisher", ""),
                    "article": it.get("article-number", "")})
    return out


def arxiv_id(aid):
    root = ET.fromstring(get("http://export.arxiv.org/api/query?id_list=" + aid))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    e = root.find("a:entry", ns)
    t = " ".join((e.findtext("a:title", "", ns) or "").split())
    auth = []
    for a in e.findall("a:author", ns):
        n = (a.findtext("a:name", "", ns) or "").split()
        if n:
            auth.append((n[-1], " ".join(n[:-1])))
    return {"src": "arxiv", "title": t, "year": int((e.findtext("a:published", "", ns) or "0")[:4]), "authors": auth, "container": "arXiv", "arxiv": aid, "type": "preprint"}


def main():
    have = json.loads(OUT.read_text(encoding="utf-8"))
    for key, title, surname, year, venue in C:
        if key in have:
            continue
        rec = None
        try:
            if ARXIV_IDS.get(key):
                c = arxiv_id(ARXIV_IDS[key])
                if sim(title, c["title"]) >= 0.8:
                    rec = {**c, "score": round(sim(title, c["title"]), 3)}
            if rec is None:
                best = (0, None)
                for c in crossref_author(title, surname, year):
                    s = sim(title, c["title"])
                    if surname and not any(norm(surname) in norm(a[0]) for a in c["authors"][:4]):
                        continue
                    if year and c["year"] and abs(int(c["year"]) - year) > 3:
                        continue
                    if s > best[0]:
                        best = (s, c)
                if best[1] is not None and best[0] >= 0.9:
                    rec = {**best[1], "score": round(best[0], 3)}
        except Exception as exc:
            print("  error", key, exc)
        print(("OK  " if rec else "BAD ") + f"{key:18s}", (rec or {}).get("title", "")[:70], "|", (rec or {}).get("year"), "|", (rec or {}).get("container", "")[:28])
        if rec:
            rec["wanted_year"] = year
            have[key] = rec
        time.sleep(0.6)
    OUT.write_text(json.dumps(have, indent=1, ensure_ascii=False), encoding="utf-8")
    print("verified now:", len(have), "of", len(C))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
