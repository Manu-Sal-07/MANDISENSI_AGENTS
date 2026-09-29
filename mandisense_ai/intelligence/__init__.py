"""
LLM decision intelligence.

Turns the numbers the rest of the system produces — cognition directives,
scheduled forecasts, spillover evidence — into a structured decision brief a
procurement operator can act on.

The design constraint that shapes every module here: **the language model is
allowed to explain, weigh and recommend, but never to supply a number.**
Every figure in a published brief is copied from an evidence bundle assembled
before the model is called, and `grounding.py` verifies that after the fact.
A brief that cites a number not present in its evidence is rejected rather
than served.
"""

from mandisense_ai.intelligence.evidence import EvidenceBundle, build_evidence
from mandisense_ai.intelligence.schema import (
    BRIEF_TOOL_SCHEMA,
    DecisionBrief,
    brief_from_dict,
)
from mandisense_ai.intelligence.service import DecisionIntelligenceService

__all__ = [
    "BRIEF_TOOL_SCHEMA",
    "DecisionBrief",
    "DecisionIntelligenceService",
    "EvidenceBundle",
    "brief_from_dict",
    "build_evidence",
]
