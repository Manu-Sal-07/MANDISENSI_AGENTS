"""
LLM decision intelligence API.

Serves the structured decision brief: evidence assembled from the cognition,
forecasting and spillover engines, reasoned over by a provider, then verified
against that evidence before it is returned.

The verification result travels with the brief rather than gating it. A brief
whose figures could not all be traced back to the evidence is still served,
with `grounded: false` and the specific issues listed, because a caller that
can see the problem can decide what to do about it — one that receives a 500
cannot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mandisense_ai.intelligence.evidence import build_evidence
from mandisense_ai.intelligence.service import get_intelligence_service

router = APIRouter()


class FactorModel(BaseModel):
    label: str
    detail: str
    direction: str = Field(description="supports | opposes | neutral")
    evidence_ref: str = Field(description="Evidence key this factor rests on")


class BriefModel(BaseModel):
    commodity: str
    mandi_id: str
    action: str
    confidence: str
    headline: str
    rationale: str
    factors: List[FactorModel] = []
    risks: List[str] = []
    watch_next: List[str] = []

    generated_by: str
    model_id: Optional[str] = None
    evidence_as_of: Optional[str] = None
    grounded: bool
    grounding_issues: List[str] = []

    evidence: Optional[Dict[str, Any]] = None
    caveat: str


CAVEAT = (
    "This brief is generated from a fixed evidence bundle assembled before "
    "the reasoning step. Every figure it states is verified to appear in that "
    "bundle; `grounded` reports the result and `grounding_issues` lists any "
    "figure or citation that could not be traced. Forecasts come from a "
    "scheduled offline job, so the as-of date is the date the evidence "
    "describes, not the time of this request."
)


@router.get("/status")
async def intelligence_status() -> Dict[str, Any]:
    """Which provider is active and whether grounding is enforced.

    Never fails: a caller polling status needs an answer even when the
    reasoning provider is misconfigured.
    """
    try:
        return get_intelligence_service().status()
    except Exception as exc:  # pragma: no cover - defensive
        return {"available": False, "reason": str(exc)[:200]}


@router.get("/evidence/{commodity}/{mandi_id}")
async def get_evidence(commodity: str, mandi_id: str) -> Dict[str, Any]:
    """The raw evidence bundle, without any reasoning applied.

    Exposed deliberately: it is what makes the brief auditable. A reviewer
    can read exactly what the model was shown and check the brief against it
    independently of the grounding verifier.
    """
    try:
        return build_evidence(commodity, mandi_id).to_dict()
    except Exception as exc:  # pragma: no cover - build_evidence is non-raising
        raise HTTPException(status_code=500, detail=f"Evidence assembly failed: {exc}")


@router.get("/brief/{commodity}/{mandi_id}", response_model=BriefModel)
async def get_brief(
    commodity: str,
    mandi_id: str,
    include_evidence: bool = Query(
        False,
        description="Attach the evidence bundle the brief was built from.",
    ),
) -> BriefModel:
    """The decision brief for one commodity at one mandi."""
    bundle = build_evidence(commodity, mandi_id)

    if not bundle.facts:
        # Nothing known at all is different from a weak recommendation, and
        # is reported as a 404 rather than a brief full of refusals.
        raise HTTPException(
            status_code=404,
            detail=(
                f"No evidence available for {commodity} @ {mandi_id}. "
                f"Sources tried: {', '.join(sorted(bundle.unavailable)) or 'none'}."
            ),
        )

    brief = get_intelligence_service().build_brief(commodity, mandi_id, evidence=bundle)
    payload = brief.to_dict()
    payload["evidence"] = bundle.to_dict() if include_evidence else None
    payload["caveat"] = CAVEAT
    return BriefModel(**payload)
