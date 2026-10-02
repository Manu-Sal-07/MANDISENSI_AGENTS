"""
Checking that the numbers in a reply came from somewhere.

The brief layer already verifies that every figure a decision brief states is in
its evidence bundle; this is the same idea for chat. A reply's numbers must be
found in what the tools returned, in the user's own message, or in the page
context. A figure that cannot be traced is reported, so the UI can warn rather
than present an invented price as fact.

Small whole numbers (counts, days, dates) are not checked: they are rarely the
claim and are often the user's own words restated.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Set

from mandisense_ai.chat.languages import normalise_digits

_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")
_THRESHOLD = 20.0  # numbers below this are not checked
_CONSTANTS = {90.0, 95.0, 99.0, 100.0}  # confidence levels and percentages quoted as such, not data claims


def numbers_in(text: str) -> List[float]:
    out = []
    for m in _NUM.finditer(normalise_digits(str(text))):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return out


def _leaves(obj: Any) -> Iterable[float]:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, str):
        yield from numbers_in(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _leaves(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _leaves(v)


def evidence_numbers(*sources: Any) -> Set[float]:
    pool: Set[float] = set()
    for s in sources:
        pool.update(_leaves(s))
    pool.update({abs(v) for v in pool})  # a reply says "fell 12%" where the tool says -12
    return pool


def _matches(value: float, pool: Set[float]) -> bool:
    for e in pool:
        if abs(value - e) <= max(0.51, abs(e) * 0.011):  # rounding to a whole unit, or 1%
            return True
        # same figure in different units (rupees <-> lakhs, quintals <-> tonnes)
        for scale in (10.0, 100.0, 1000.0, 100000.0):
            if e and abs(value - e / scale) <= max(0.06, abs(e / scale) * 0.011):
                return True
            if abs(value - e * scale) <= max(0.51, abs(e * scale) * 0.011):
                return True
    return False


def check(reply: str, tool_outputs: List[Any], user_texts: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
    """Return {grounded, ungrounded: [numbers...]} for `reply`."""
    pool = evidence_numbers(tool_outputs, context)
    for t in user_texts:
        pool.update(numbers_in(t))
    # a reply can also restate calendar years and percentages derived by the tools
    bad = []
    for v in numbers_in(reply):
        if v < _THRESHOLD or (1990 <= v <= 2100) or v in _CONSTANTS:
            continue
        if not _matches(v, pool):
            bad.append(v)
    return {"grounded": not bad, "ungrounded": sorted(set(bad))[:8]}
