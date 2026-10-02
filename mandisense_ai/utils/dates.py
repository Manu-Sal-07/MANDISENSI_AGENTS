"""
Canonical date parsing for market data.

Why this module exists
----------------------
Agmarknet extracts arrive in mixed date formats. A previous implementation
passed ``dayfirst=True`` to ``pandas.to_datetime`` for *all* inputs, which
silently corrupted ISO-8601 sources in two compounding ways:

  * ``2019-09-10`` was reinterpreted as 9 October 2019 (day/month transposed).
  * ``2019-09-13`` became ``NaT`` because day 13 cannot be a month, and the
    row was then dropped by downstream ``dropna(subset=['date'])`` calls.

The net effect was that ~63% of genuine observations disappeared and the
survivors were filed under wrong dates, which invalidates every lag-based
computation (returns, rolling windows, lead/lag analysis).

Strategy
--------
Parse in strictly decreasing order of confidence and never guess when the
evidence is ambiguous:

  1. ISO-8601 (``YYYY-MM-DD``) - unambiguous, tried first and strictly.
  2. Explicit unambiguous day-first / month-first formats.
  3. A dayfirst inference based on observed evidence: if any value has a
     first component > 12, the source must be day-first; if any has a second
     component > 12, it must be month-first. Only then is a heuristic applied.

This function is deterministic and side-effect free.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

__all__ = ["parse_market_dates", "DateParseReport"]


# Formats attempted in order. ISO first: it is the format the bundled
# Agmarknet extracts actually use and it admits no day/month ambiguity.
_EXPLICIT_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d-%B-%Y",
    "%m/%d/%Y",
)


class DateParseReport:
    """Diagnostics for a parse run. Purely informational."""

    __slots__ = ("total", "parsed", "failed", "strategy")

    def __init__(self, total: int, parsed: int, strategy: str) -> None:
        self.total = total
        self.parsed = parsed
        self.failed = total - parsed
        self.strategy = strategy

    @property
    def parse_rate(self) -> float:
        return (self.parsed / self.total) if self.total else 1.0

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "parsed": self.parsed,
            "failed": self.failed,
            "strategy": self.strategy,
            "parse_rate": round(self.parse_rate, 6),
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<DateParseReport {self.as_dict()}>"


def _infer_dayfirst(raw: pd.Series) -> Optional[bool]:
    """
    Decide day-first vs month-first from evidence, or return None if the
    source gives no basis to decide.

    A component > 12 can only be a day, so it pins the ordering. If both
    positions show values > 12 the source is internally inconsistent and we
    refuse to guess.
    """
    parts = (
        raw.astype(str)
        .str.strip()
        .str.split(r"[-/.]", n=2, regex=True)
    )
    usable = parts[parts.map(lambda p: isinstance(p, list) and len(p) == 3)]
    if usable.empty:
        return None

    def _numeric_at(index: int) -> pd.Series:
        return pd.to_numeric(usable.map(lambda p: p[index]), errors="coerce")

    first, second = _numeric_at(0), _numeric_at(1)

    # A 4-digit leading component means the layout is year-first, so the
    # day/month question does not arise here.
    if (first > 31).any():
        return None

    first_over_12 = bool((first > 12).any())
    second_over_12 = bool((second > 12).any())

    if first_over_12 and not second_over_12:
        return True
    if second_over_12 and not first_over_12:
        return False
    return None


def parse_market_dates(
    values: pd.Series,
    *,
    report: Optional[list] = None,
) -> pd.Series:
    """
    Parse a Series of market dates into ``datetime64[ns]``.

    Args:
        values: Raw date values (strings, datetimes, or a mix).
        report: Optional list; a :class:`DateParseReport` is appended to it.

    Returns:
        A ``datetime64[ns]`` Series aligned to the input index. Values that
        cannot be parsed become ``NaT`` rather than being silently shifted to
        a plausible-but-wrong date.
    """
    if values is None or len(values) == 0:
        result = pd.to_datetime(pd.Series([], dtype="object"), errors="coerce")
        if report is not None:
            report.append(DateParseReport(0, 0, "empty"))
        return result

    if pd.api.types.is_datetime64_any_dtype(values):
        if report is not None:
            report.append(DateParseReport(len(values), int(values.notna().sum()), "passthrough"))
        return values

    raw = values.astype(str).str.strip()
    non_null_mask = raw.notna() & (raw != "") & (raw.str.lower() != "nan")
    target = int(non_null_mask.sum())

    best: Optional[pd.Series] = None
    best_hits = -1
    best_strategy = "unparsed"

    for fmt in _EXPLICIT_FORMATS:
        attempt = pd.to_datetime(raw, format=fmt, errors="coerce")
        hits = int(attempt.notna().sum())
        if hits > best_hits:
            best, best_hits, best_strategy = attempt, hits, f"format={fmt}"
        # Every non-null value parsed under an unambiguous explicit format:
        # no reason to keep searching.
        if hits >= target:
            break

    # Fall back to inference only if an explicit format left rows unparsed.
    if best_hits < target:
        dayfirst = _infer_dayfirst(raw)
        attempt = pd.to_datetime(
            raw,
            errors="coerce",
            dayfirst=bool(dayfirst) if dayfirst is not None else False,
        )
        hits = int(attempt.notna().sum())
        if hits > best_hits:
            best, best_hits = attempt, hits
            best_strategy = f"inferred(dayfirst={dayfirst})"

    assert best is not None  # at least one branch always assigns
    if report is not None:
        report.append(DateParseReport(len(values), best_hits, best_strategy))

    return best
