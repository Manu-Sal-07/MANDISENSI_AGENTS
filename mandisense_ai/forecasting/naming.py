"""
Canonical naming for markets and commodities.

The upstream feed writes market names as free text ("Binny Mill (FF&V)
Bengaluru APMC", "Bangarpet APMC"), while every model, encoder and snapshot in
this codebase keys on slugs ("bangarpet_apmc"). Getting this mapping wrong is
not a cosmetic problem: an unmapped name silently becomes a *new* series with
no history, so it never accumulates enough data to be forecast, and a
mis-mapped name corrupts a real series with another market's prices.

The rules here are deliberately conservative — normalise confidently, alias
explicitly, and otherwise emit a clean slug rather than guessing at a match.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from mandisense_ai.forecasting.config import COMMODITY_ALIASES

# Explicit aliases for upstream names whose slug would not match the canonical
# id. Keys are normalised (lowercase, punctuation stripped) upstream names.
MARKET_ALIASES: Dict[str, str] = {
    "binny mill ff v bengaluru apmc": "bangalore_yeshwanthpur",
    "binny mill bengaluru apmc": "bangalore_yeshwanthpur",
    "bengaluru apmc": "bangalore_yeshwanthpur",
    "bangalore apmc": "bangalore_yeshwanthpur",
    "yeshwanthpur apmc": "bangalore_yeshwanthpur",
    "kolar": "kolar_apmc",
    "lasalgaon": "lasalgaon_apmc",
    "agra": "agra_apmc",
    "neemuch": "neemuch_apmc",
    "guntur": "guntur_apmc",
}

# Every id the alias table resolves to. Treated as already-canonical on input
# so that re-normalising an id is a no-op rather than a rename.
_CANONICAL_MARKET_IDS = frozenset(MARKET_ALIASES.values())

_PUNCT = re.compile(r"[^a-z0-9\s]+")
_SPACES = re.compile(r"\s+")

# The upstream feed writes the market-type marker inconsistently — sometimes
# leading ("APMC Akola"), sometimes trailing ("Bangarpet APMC"), sometimes not
# at all. Normalising both ends prevents the same physical market arriving as
# two different series ids, which would split its history in half.
_LEADING_MARKERS = ("apmc ", "apmc-", "rmc ", "mandi ")
_TRAILING_MARKERS = ("apmc", "mandi", "market", "yard")


def _normalise(value: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = str(value or "").strip().lower()
    text = _PUNCT.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def _strip_market_markers(text: str) -> str:
    """Remove a leading APMC/mandi marker so it is not duplicated on the slug."""
    for marker in _LEADING_MARKERS:
        normalised_marker = _normalise(marker) + " "
        if text.startswith(normalised_marker):
            return text[len(normalised_marker):].strip()
    return text


def canonical_market(raw_name: str) -> Optional[str]:
    """
    Map an upstream market name to a canonical mandi id.

    Returns None for empty input rather than inventing an id, so callers can
    drop the row instead of creating a phantom series.
    """
    normalised = _normalise(raw_name)
    if not normalised:
        return None

    if normalised in MARKET_ALIASES:
        return MARKET_ALIASES[normalised]

    stripped = _strip_market_markers(normalised)
    if stripped in MARKET_ALIASES:
        return MARKET_ALIASES[stripped]
    if not stripped:
        return None

    slug = stripped.replace(" ", "_")

    # An id this module already emits is returned untouched, so the function
    # is idempotent: canonical_market(canonical_market(x)) == canonical_market(x).
    # Without this, a canonical id that happens not to end in a market-type
    # word — `bangalore_yeshwanthpur` is the one in this dataset — gets `_apmc`
    # appended on a second pass and silently becomes a *different* series from
    # the one the rest of the product keys on. Callers legitimately re-normalise
    # ids that are already canonical (a request path parameter, a backfill
    # reading a processed dataset), so this has to hold.
    if slug in _CANONICAL_MARKET_IDS:
        return slug

    # A name that already ends in a market-type word keeps its own ending;
    # appending another would produce ids like `mumbai_onion_market_apmc`.
    if slug.endswith(tuple(f"_{marker}" for marker in _TRAILING_MARKERS)):
        return slug

    return f"{slug}_apmc"


# Alias keys are written in their natural form above; they are normalised once
# here so that lookup compares like with like. Without this, "Ginger(Green)"
# normalises to "ginger green", misses the "ginger(green)" key, and becomes a
# separate `ginger_green` series that never links to ginger's history.
_NORMALISED_COMMODITY_ALIASES = {
    _normalise(alias).replace(" ", ""): canonical
    for alias, canonical in COMMODITY_ALIASES.items()
}


def canonical_commodity(raw_name: str) -> Optional[str]:
    """Map an upstream commodity name to a canonical commodity id."""
    normalised = _normalise(raw_name)
    if not normalised:
        return None

    collapsed = normalised.replace(" ", "")
    if collapsed in _NORMALISED_COMMODITY_ALIASES:
        return _NORMALISED_COMMODITY_ALIASES[collapsed]

    return normalised.replace(" ", "_")


def series_key(commodity: str, mandi_id: str) -> str:
    return f"{commodity}::{mandi_id}"
