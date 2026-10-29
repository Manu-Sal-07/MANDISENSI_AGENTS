"""
Write docs/LANGUAGE_REVIEW.md: every Kannada and Hindi string a farmer can see, beside its English, for a native speaker to mark.

    python scripts/language_review.py

Sources: the front-end copy tables (`frontend/src/lib/i18n/*Copy.ts`) and the explanation templates and caveats in
`mandisense_ai/intelligence/explain.py`. The file is regenerated from them, so a reviewer's marks belong in the `Verdict` and `Suggested wording`
columns of a copy that is committed; regenerating overwrites those columns, so review a frozen copy (`docs/LANGUAGE_REVIEW_<reviewer>.md`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "LANGUAGE_REVIEW.md"
KEY_LINE = re.compile(r"^  '([\w.]+)':\s*\{", re.M)
LANG = re.compile(r"\b(en|kn|hi):\s*'((?:[^'\\]|\\.)*)'", re.S)


def ts_entries(path: Path) -> List[Tuple[str, Dict[str, str]]]:
    """Entries are sliced at each key line, not by brace matching: a `{slot}` inside a string must not end an entry early."""
    text = path.read_text(encoding="utf-8")
    keys = list(KEY_LINE.finditer(text))
    out = []
    for i, m in enumerate(keys):
        body = text[m.end(): keys[i + 1].start() if i + 1 < len(keys) else len(text)]
        langs = {k: v.replace("\\'", "'") for k, v in LANG.findall(body)}
        if {"en", "kn", "hi"} <= set(langs):
            out.append((m.group(1), langs))
    return out


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def main() -> None:
    from mandisense_ai.intelligence import explain

    sections: List[Tuple[str, List[Tuple[str, Dict[str, str]]]]] = []
    for name, rel in (("Best place and day to sell", "frontend/src/lib/i18n/marketChoiceCopy.ts"), ("Supply watch and reasons panel", "frontend/src/lib/i18n/shockCopy.ts")):
        sections.append((name, ts_entries(ROOT / rel)))
    rules = [(f"rule {i + 1}: {kind} [{', '.join(keys)}]", t) for i, (kind, keys, t) in enumerate(explain.RULES)]
    caveats = [(f"caveat: {k}", v) for k, v in explain.CAVEAT_TEXT.items()]
    sections.append(("Explanation sentences (slots like {best.mandi} are filled by code with names, numbers and dates)", rules + caveats))

    total = sum(len(e) for _, e in sections)
    L = ["# Language review: Kannada and Hindi", "",
         f"{total} strings a farmer can read. English is the reference; Kannada and Hindi were written by the team and checked mechanically (script, slots, "
         "no digits where none belong) but **not yet reviewed by a native speaker**. Please mark each row: `OK`, `Fix` (with wording), or `Unclear in English`.", "",
         "What to look for: natural, respectful register for a farmer; case endings after place names (this project writes 'Kolar *mandi*' forms so endings attach to a common noun); "
         "units and months in everyday forms; and that **uncertainty is not lost**: words like *about*, *at least*, *not a promise* must survive translation, because a reviewer who "
         "smooths them away changes what the farmer is told.", ""]
    for title, entries in sections:
        L += [f"## {title}", "", "| Key | English | ಕನ್ನಡ | हिन्दी | Verdict | Suggested wording |", "|---|---|---|---|---|---|"]
        for key, t in entries:
            L.append(f"| `{cell(key)}` | {cell(t['en'])} | {cell(t['kn'])} | {cell(t['hi'])} | | |")
        L.append("")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {total} strings ({', '.join(f'{len(e)}' for _, e in sections)})")


if __name__ == "__main__":
    main()
