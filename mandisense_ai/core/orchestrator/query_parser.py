"""
Natural-language parsing for market queries.

Replaces the substring scan that was duplicated across `QueryIntelligence`
and `QueryOrchestrator`. Three things were wrong with it:

1. **Plurals and local names missed.** "tomatoes" happened to work because
   "tomato" is a substring, but "aloo", "pyaz" and "bengaluru" did not — and
   this is a product used by Indian farmers and traders.
2. **Substring matching, not word matching.** Any commodity or mandi name
   appearing inside a longer word would match by accident.
3. **The failure was undiagnosed.** A query missing only a mandi returned the
   same "Context missing" as an empty one, so the user was never told what to
   add. That is what made otherwise reasonable questions look broken.

The parser reports *what it found and what is missing*, so the caller can give
a specific answer instead of a generic refusal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Canonical commodity -> the ways people actually write it, including plurals
# and the common Hindi/Kannada names heard at a mandi.
COMMODITY_ALIASES: Dict[str, List[str]] = {
    "tomato": ["tomato", "tomatoes", "tamatar", "tomatto"],
    "onion": ["onion", "onions", "pyaz", "pyaaz", "kanda", "eerulli"],
    "potato": ["potato", "potatoes", "aloo", "alu", "batate"],
    "garlic": ["garlic", "lehsun", "lasun", "bellulli"],
    "ginger": ["ginger", "adrak", "shunti"],
}

# Mandi aliases -> canonical mandi id.
MANDI_ALIASES: Dict[str, str] = {
    "kolar": "kolar_apmc",
    "ramanagara": "ramanagara_apmc",
    "ramanagaram": "ramanagara_apmc",
    "bangalore": "bangalore_yeshwanthpur",
    "bengaluru": "bangalore_yeshwanthpur",
    "bengalooru": "bangalore_yeshwanthpur",
    "blr": "bangalore_yeshwanthpur",
    "yeshwanthpur": "bangalore_yeshwanthpur",
    "chickballapur": "chickballapur_apmc",
    "chikkaballapur": "chickballapur_apmc",
    "hoskote": "hoskote_apmc",
    "nelamangala": "nelamangala_apmc",
    "anekal": "anekal_apmc",
    "doddaballapur": "doddaballapur_apmc",
    "malur": "malur_apmc",
    "magadi": "magadi_apmc",
    "kanakapura": "kanakapura_apmc",
    "sidlaghatta": "sidlaghatta_apmc",
    "channapatna": "channapatna_apmc",
    "kunigal": "kunigal_apmc",
    "bangarpet": "bangarpet_apmc",
}

# Phrases that carry a time horizon, longest first so "next 5 days" is not
# shadowed by a bare "day".
_HORIZON_PATTERNS = [
    (re.compile(r"\bnext\s+(\d{1,2})\s*(?:days?|din)\b"), None),
    (re.compile(r"\bin\s+(\d{1,2})\s*(?:days?|din)\b"), None),
    (re.compile(r"\b(\d{1,2})\s*(?:days?|din)\s+(?:from\s+now|ahead|later)\b"), None),
    (re.compile(r"\bnext\s+week\b"), 7),
    (re.compile(r"\bthis\s+week\b"), 7),
    (re.compile(r"\btomorrow\b"), 1),
    (re.compile(r"\btoday\b"), 1),
]

MAX_HORIZON_DAYS = 30


@dataclass
class ParsedQuery:
    """Structured reading of a user's question."""

    raw: str
    commodity: Optional[str] = None
    mandi_id: Optional[str] = None
    mandi_name: Optional[str] = None
    horizon_days: Optional[int] = None
    missing: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.commodity is not None and self.mandi_id is not None


def _contains_word(text: str, term: str) -> bool:
    """
    Word-boundary match.

    Substring matching would let a mandi or commodity name buried inside an
    unrelated word register as a hit.
    """
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _extract_horizon(text: str) -> Optional[int]:
    for pattern, fixed in _HORIZON_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if fixed is not None:
            return fixed
        try:
            days = int(match.group(1))
        except (IndexError, ValueError):
            continue
        if 1 <= days <= MAX_HORIZON_DAYS:
            return days
    return None


def parse_market_query(query_text: str) -> ParsedQuery:
    """
    Read a free-text market question.

    Returns what was understood plus an explicit list of what is missing, so
    callers can respond to the specific gap rather than refusing generically.
    """
    raw = str(query_text or "")
    text = raw.lower().strip()
    parsed = ParsedQuery(raw=raw)

    if not text:
        parsed.missing = ["commodity", "mandi"]
        return parsed

    # Longest aliases first so "chikkaballapur" is not shadowed by a shorter
    # alias that happens to be contained in it.
    for canonical, aliases in COMMODITY_ALIASES.items():
        if any(_contains_word(text, alias) for alias in sorted(aliases, key=len, reverse=True)):
            parsed.commodity = canonical
            break

    for alias in sorted(MANDI_ALIASES, key=len, reverse=True):
        if _contains_word(text, alias):
            parsed.mandi_id = MANDI_ALIASES[alias]
            parsed.mandi_name = alias.title()
            break

    parsed.horizon_days = _extract_horizon(text)

    if parsed.commodity is None:
        parsed.missing.append("commodity")
    if parsed.mandi_id is None:
        parsed.missing.append("mandi")

    return parsed


def supported_commodities() -> List[str]:
    return sorted(COMMODITY_ALIASES)


def supported_mandis() -> List[str]:
    """Distinct canonical mandi ids, in a stable order."""
    return sorted(set(MANDI_ALIASES.values()))


def describe_gap(parsed: ParsedQuery, sample_mandis: int = 4) -> str:
    """
    A specific, actionable message for an incomplete query.

    Naming what was understood matters: "I found tomato but no mandi" tells the
    user they were nearly right, where "Context missing" reads as a failure of
    the whole system.
    """
    commodities = ", ".join(supported_commodities())
    mandi_examples = ", ".join(
        m.replace("_apmc", "").replace("_", " ").title()
        for m in supported_mandis()[:sample_mandis]
    )

    if parsed.commodity and not parsed.mandi_id:
        return (
            f"I understood the commodity ({parsed.commodity}), but not which mandi. "
            f"Add a market — for example \"{parsed.commodity} in Kolar\". "
            f"Markets covered include {mandi_examples}."
        )

    if parsed.mandi_id and not parsed.commodity:
        where = parsed.mandi_name or parsed.mandi_id.replace("_apmc", "").title()
        return (
            f"I understood the mandi ({where}), but not which commodity. "
            f"Add one of: {commodities}."
        )

    return (
        "Tell me a commodity and a mandi — for example \"Should I sell tomatoes "
        f"in Kolar today?\". Commodities: {commodities}. "
        f"Markets include {mandi_examples}."
    )
