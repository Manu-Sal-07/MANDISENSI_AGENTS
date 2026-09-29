"""
Grounding verification.

A language model asked about prices will produce prices. Most will be right,
some will be plausible and wrong, and nothing in the text distinguishes the
two. In a procurement tool a wrong number is worse than no number, because
it is acted on.

So the model's output is checked before it is served: every figure in the
brief must appear in the evidence bundle the model was given, and every
factor must cite an evidence key that exists. A brief that fails is not
discarded — it is served with `grounded: false` and the specific issues
listed, so the failure is visible rather than silent.

This is a verifier, not a filter. It cannot make a model honest; it makes
dishonesty detectable, which is what allows the feature to ship at all.
"""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple

from mandisense_ai.intelligence.schema import DecisionBrief

# Numbers as they appear in prose: 1,234.56 / 1234 / -2.13 / 8%
_NUMBER = re.compile(r"-?\d[\d,]*\.?\d*")

# Relative tolerance when matching a stated figure against the evidence. The
# model is told to copy figures verbatim, but it legitimately rounds ₹1768.24
# to ₹1768 in prose, and rejecting that would make the check useless noise.
_REL_TOLERANCE = 0.01

# Small integers are ordinary English ("3 days", "the 2 risks") and carry no
# claim about market data, so requiring them to appear in the evidence would
# produce constant false positives.
_IGNORE_BELOW = 32


# Things that look like figures but are not claims about market data, and
# would otherwise produce constant false positives:
#   - ISO dates and timestamps ("2026-05-02", "2026-09-16T13:54:03")
#   - the band's own label ("90% interval", "the 90% band")
#   - ordinals attached to horizons ("5-day", "h5")
_DATELIKE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ][\d:.+\-]+)?")
_BAND_LABEL = re.compile(r"\b(?:50|90|95)\s*%")


def _strip_non_claims(text: str) -> str:
    text = _DATELIKE.sub(" ", text or "")
    return _BAND_LABEL.sub(" ", text)


def _parse_numbers(text: str) -> List[float]:
    out: List[float] = []
    for raw in _NUMBER.findall(_strip_non_claims(text)):
        cleaned = raw.replace(",", "").rstrip(".")
        if not cleaned or cleaned in {"-", "."}:
            continue
        try:
            out.append(float(cleaned))
        except ValueError:
            continue
    return out


def _matches_any(value: float, allowed: Sequence[float]) -> bool:
    for candidate in allowed:
        if candidate == value:
            return True
        scale = max(abs(candidate), abs(value), 1e-9)
        if abs(candidate - value) / scale <= _REL_TOLERANCE:
            return True
        # A percentage may be stated either as 0.0572 or as 5.72.
        if abs(abs(candidate) * 100 - abs(value)) / max(abs(value), 1e-9) <= _REL_TOLERANCE:
            return True
    return False


def verify_grounding(
    brief: DecisionBrief,
    allowed_numbers: Sequence[float],
    allowed_keys: Sequence[str],
) -> Tuple[bool, List[str]]:
    """Check a brief against the evidence it was built from.

    Returns `(grounded, issues)`. `issues` is empty exactly when grounded.
    """
    issues: List[str] = []

    prose = " ".join(
        [brief.headline, brief.rationale]
        + [f.detail for f in brief.factors]
        + list(brief.risks)
        + list(brief.watch_next)
    )

    for value in _parse_numbers(prose):
        if abs(value) < _IGNORE_BELOW:
            continue
        if not _matches_any(value, allowed_numbers):
            issues.append(
                f"figure {value:g} does not appear in the evidence bundle"
            )

    known = set(allowed_keys)
    for factor in brief.factors:
        ref = factor.evidence_ref
        if not ref:
            issues.append(f"factor '{factor.label}' cites no evidence key")
        elif ref not in known:
            issues.append(
                f"factor '{factor.label}' cites unknown evidence key '{ref}'"
            )

    # De-duplicate while preserving order; the same invented figure repeated
    # in three places is one problem, not three.
    seen = set()
    unique = [i for i in issues if not (i in seen or seen.add(i))]
    return (not unique), unique
