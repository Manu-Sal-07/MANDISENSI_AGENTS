"""
Write docs/CONTRIBUTIONS.md from the git history: who changed what, measured, not asserted.

    python scripts/contributions.py

Counts only hand-written source (code, tests, docs, LaTeX), not generated artefacts such as parquet panels, model files or result tables, so a
bulk data commit does not look like authorship. Identities are merged by `.mailmap`. Team members and USNs come from the TEAM table below;
a member with no commits under any identity is shown as such rather than omitted.
"""

from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "CONTRIBUTIONS.md"
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".css", ".md", ".tex", ".yml", ".yaml", ".toml", ".html", ".sql", ".sh", ".ps1"}
GENERATED_PARTS = ("research/results/", "papers/", "frontend/public/", "mandisense_ai/models/", "mandisense_ai/data/", "datasets/", "package-lock.json")

# name as printed in the project report, USN, and the name the member's commits appear under after .mailmap
TEAM = [
    ("Srijan C Vachadmath", "1BM23CD060", "Srijan C Vachadmath"),
    ("Manohara Salmani", "1BM23CD035", "Manohara Salmani"),
    ("Shreejith Shah", "1BM23CD057", "Shreejith Shah"),
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout


def main() -> None:
    log = git("log", "--no-merges", "--numstat", "--date=short", "--format=@@%aN|%ad|%s")
    commits, added, removed = Counter(), Counter(), Counter()
    first, last = {}, {}
    areas: dict = defaultdict(Counter)
    for block in log.split("@@")[1:]:
        head, *rows = block.strip("\n").split("\n")
        author, date, _ = head.split("|", 2)
        commits[author] += 1
        first[author] = min(first.get(author, date), date)
        last[author] = max(last.get(author, date), date)
        for row in rows:
            parts = row.split("\t")
            if len(parts) != 3 or parts[0] == "-":
                continue
            a, r, path = int(parts[0]), int(parts[1]), parts[2]
            if Path(path).suffix.lower() not in SOURCE_SUFFIXES or any(g in path for g in GENERATED_PARTS):
                continue
            added[author] += a
            removed[author] += r
            areas[author][path.split("/")[0] if "/" in path else "(root)"] += a + r

    names = {t[2] for t in TEAM}
    L = ["# Contribution record", "", f"Generated {datetime.now():%Y-%m-%d} by `scripts/contributions.py` from `git log --no-merges`. Only hand-written source, tests, "
         "documentation and LaTeX are counted; generated artefacts (data panels, trained models, result tables, figures) are excluded. Identities are merged by `.mailmap`.", "",
         "## Team", "", "| Member | USN | Commits | Lines added | Lines removed | First | Last | Main areas (by lines changed) |", "|---|---|---|---|---|---|---|---|"]
    for name, usn, key in TEAM:
        top = ", ".join(f"`{a}` {n}" for a, n in areas[key].most_common(4)) or "—"
        L.append(f"| {name} | {usn} | {commits[key]} | {added[key]} | {removed[key]} | {first.get(key, '—')} | {last.get(key, '—')} | {top} |")
    others = sorted(a for a in commits if a not in names)
    for a in others:
        L.append(f"| *{a}* (unmatched identity) | — | {commits[a]} | {added[a]} | {removed[a]} | {first[a]} | {last[a]} | " + (", ".join(f"`{x}` {n}" for x, n in areas[a].most_common(4)) or "—") + " |")
    silent = [name for name, _, key in TEAM if commits[key] == 0]
    L += ["", "## Reading this record", ""]
    if silent:
        L.append("**No commits are recorded for " + ", ".join(silent) + " in this repository.** Evaluators may adjust the implementation mark of a member whose contribution is not "
                 "evident. Work done on another machine or fork counts only if it is committed here under that member's own identity (`git config user.name` / `user.email`), "
                 "for example by fetching the member's fork (`git remote add <name> <url>`, `git fetch`) and merging or cherry-picking their commits, which keeps authorship.")
    L += ["", "## Responsibilities", "",
          "Each work package has one primary owner; the table is maintained by the team and is the same as the responsibility matrix in the project plan. "
          "It is deliberately not filled in by the tooling, because ownership is a decision, not a measurement.", "",
          "| Work package | Primary owner | Supporting |", "|---|---|---|", "| *(to be completed by the team)* | | |", "",
          "## Method", "",
          "- `git log --no-merges --numstat`; lines counted per author for files with a source suffix, excluding generated paths.",
          "- Commit count is a weak measure of effort; it is shown with lines and areas so that one large generated commit cannot stand in for authorship."]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for name, _, key in TEAM:
        print(f"  {name:22s} {commits[key]:3d} commits  +{added[key]} -{removed[key]}")


if __name__ == "__main__":
    main()
