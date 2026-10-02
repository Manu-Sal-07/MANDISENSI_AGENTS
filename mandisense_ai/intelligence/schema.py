"""
The decision brief contract.

A brief is a fixed shape, not free text. Free prose from a language model is
unverifiable: you cannot check that a paragraph cited the right price, and
you cannot render it consistently. A fixed schema makes both possible — every
field has a known meaning, `grounding.py` can walk the numeric fields, and
the UI can lay it out without parsing English.

The same schema is handed to the model as a tool definition, so the model
fills the structure directly instead of writing JSON into a text block that
then has to be parsed out of prose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# Actions the brief is allowed to recommend. Deliberately the same vocabulary
# the Phase 1 cognition layer already emits, so a brief never introduces a
# fifth action the rest of the product cannot render or act on.
ALLOWED_ACTIONS = ("BUY", "SELL", "HOLD", "WAIT")

# A brief that cannot be supported by its evidence must say so rather than
# soften the recommendation into a confident-sounding WAIT.
ALLOWED_CONFIDENCE = ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE")


@dataclass
class BriefFactor:
    """One weighed consideration behind the recommendation."""

    label: str
    detail: str
    direction: str  # "supports" | "opposes" | "neutral"
    evidence_ref: str
    """Which evidence key this factor rests on, e.g. `forecast.h5`. A factor
    that cannot name its source is a factor the model invented."""


@dataclass
class DecisionBrief:
    commodity: str
    mandi_id: str
    action: str
    confidence: str
    headline: str
    rationale: str
    factors: List[BriefFactor] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    watch_next: List[str] = field(default_factory=list)

    # Provenance. Populated by the service, never by the model.
    generated_by: str = "unknown"
    model_id: Optional[str] = None
    evidence_as_of: Optional[str] = None
    grounded: bool = False
    grounding_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def brief_from_dict(payload: Dict[str, Any]) -> DecisionBrief:
    """Build a brief from a model's tool input, coercing defensively.

    The model is instructed to return this shape, but a brief is served to a
    user, so nothing here assumes it did. Unknown actions and confidence
    values are normalised to the refusal states rather than passed through.
    """
    action = str(payload.get("action", "")).strip().upper()
    if action not in ALLOWED_ACTIONS:
        action = "WAIT"

    confidence = str(payload.get("confidence", "")).strip().upper()
    if confidence not in ALLOWED_CONFIDENCE:
        confidence = "INSUFFICIENT_EVIDENCE"

    factors: List[BriefFactor] = []
    for raw in payload.get("factors") or []:
        if not isinstance(raw, dict):
            continue
        direction = str(raw.get("direction", "neutral")).strip().lower()
        if direction not in ("supports", "opposes", "neutral"):
            direction = "neutral"
        factors.append(
            BriefFactor(
                label=str(raw.get("label", "")).strip(),
                detail=str(raw.get("detail", "")).strip(),
                direction=direction,
                evidence_ref=str(raw.get("evidence_ref", "")).strip(),
            )
        )

    def _strings(key: str) -> List[str]:
        return [str(v).strip() for v in (payload.get(key) or []) if str(v).strip()]

    return DecisionBrief(
        commodity=str(payload.get("commodity", "")).strip().lower(),
        mandi_id=str(payload.get("mandi_id", "")).strip().lower(),
        action=action,
        confidence=confidence,
        headline=str(payload.get("headline", "")).strip(),
        rationale=str(payload.get("rationale", "")).strip(),
        factors=factors,
        risks=_strings("risks"),
        watch_next=_strings("watch_next"),
    )


# The tool the model is asked to call. Using a tool rather than asking for
# JSON in prose means the SDK hands back a parsed dict, and `strict` makes
# the arguments schema-valid by construction.
BRIEF_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "publish_decision_brief",
    "description": (
        "Publish the procurement decision brief for the commodity and mandi "
        "described in the evidence. Call this exactly once. Every number you "
        "state must be copied from the evidence block — do not compute, "
        "round, convert or estimate any figure."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "commodity": {"type": "string"},
            "mandi_id": {"type": "string"},
            "action": {"type": "string", "enum": list(ALLOWED_ACTIONS)},
            "confidence": {
                "type": "string",
                "enum": list(ALLOWED_CONFIDENCE),
                "description": (
                    "INSUFFICIENT_EVIDENCE when the evidence does not support "
                    "any action — this is a valid and expected answer, not a "
                    "failure. Do not substitute a confident WAIT for it."
                ),
            },
            "headline": {
                "type": "string",
                "description": "One sentence, under 120 characters.",
            },
            "rationale": {
                "type": "string",
                "description": (
                    "Two to four sentences explaining the recommendation in "
                    "terms of the evidence provided."
                ),
            },
            "factors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "label": {"type": "string"},
                        "detail": {"type": "string"},
                        "direction": {
                            "type": "string",
                            "enum": ["supports", "opposes", "neutral"],
                        },
                        "evidence_ref": {
                            "type": "string",
                            "description": (
                                "The evidence key this factor rests on, "
                                "exactly as it appears in the evidence block "
                                "(for example 'forecast.h5' or "
                                "'cognition.decision')."
                            ),
                        },
                    },
                    "required": ["label", "detail", "direction", "evidence_ref"],
                },
            },
            "risks": {"type": "array", "items": {"type": "string"}},
            "watch_next": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "commodity",
            "mandi_id",
            "action",
            "confidence",
            "headline",
            "rationale",
            "factors",
            "risks",
            "watch_next",
        ],
    },
}
