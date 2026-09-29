"""
Cross-commodity spillover API.

Serves the precomputed spillover matrix. Every route is a read against a
cached artifact - no estimation happens in the request path.

The routes deliberately distinguish three outcomes, because collapsing them
would let the UI present absence of evidence as evidence of absence:

    503  the artifact has not been built yet
    200 + status INSUFFICIENT_EVIDENCE   we tested and could not tell
    200 + actionable edges               we tested and found transmission
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mandisense_ai.spillover.config import SHOCK_GLUT, SHOCK_SQUEEZE
from mandisense_ai.spillover.service import get_spillover_service

router = APIRouter()

_SHOCK_TYPES = (SHOCK_SQUEEZE, SHOCK_GLUT)


class HorizonEffectResponse(BaseModel):
    horizon_periods: int = Field(..., description="Response horizon in panel periods (weeks)")
    elasticity_pct: float = Field(..., description="Expected cumulative move, percent")
    ci_low_pct: float
    ci_high_pct: float
    n_episodes: int
    status: str


class SpilloverEdgeResponse(BaseModel):
    source: str
    target: str
    shock_type: str
    status: str
    n_episodes: int
    peak_horizon_periods: Optional[int] = None
    peak_elasticity_pct: Optional[float] = None
    half_life_periods: Optional[float] = None
    direction: Optional[str] = None
    effects: List[HorizonEffectResponse] = Field(default_factory=list)
    narrative: Optional[str] = None


class SpilloverImpactResponse(BaseModel):
    source: str
    shock_type: str
    frequency: str
    available: bool
    validated: bool = Field(
        ...,
        description=(
            "True only when a permutation placebo confirmed the pipeline finds "
            "more signal than randomised shock dates would."
        ),
    )
    evidence_state: str = Field(
        ...,
        description="VALIDATED, NOT_VALIDATED, or UNVALIDATED (no placebo run)",
    )
    impacts: List[SpilloverEdgeResponse]
    caveat: str


def _require_service():
    """Fetch the service or fail with a clear, actionable 503."""
    service = get_spillover_service()
    if not service.is_available:
        status = service.status()
        raise HTTPException(
            status_code=503,
            detail=(
                "Spillover intelligence is unavailable "
                f"({status.get('reason', 'unknown')}). "
                "Run scripts/build_spillover_matrix.py to build the artifact."
            ),
        )
    return service


def _narrate(edge) -> str:
    """One plain sentence a trader can act on."""
    if edge.peak_elasticity is None or edge.peak_horizon is None:
        return (
            f"No reliable {edge.shock_type.lower()} transmission measured from "
            f"{edge.source} to {edge.target}."
        )

    move = edge.peak_elasticity * 100.0
    direction = "rise" if move >= 0 else "fall"
    weeks = edge.peak_horizon
    window = "week" if weeks == 1 else "weeks"
    return (
        f"When {edge.source} enters a {edge.shock_type.lower()}, "
        f"{edge.target} tends to {direction} about {abs(move):.1f}% "
        f"around {weeks} {window} later "
        f"(based on {edge.n_episodes} historical episodes)."
    )


def _serialize(edge) -> SpilloverEdgeResponse:
    return SpilloverEdgeResponse(
        source=edge.source,
        target=edge.target,
        shock_type=edge.shock_type,
        status=edge.status,
        n_episodes=edge.n_episodes,
        peak_horizon_periods=edge.peak_horizon,
        peak_elasticity_pct=(
            round(edge.peak_elasticity * 100.0, 2)
            if edge.peak_elasticity is not None
            else None
        ),
        half_life_periods=edge.half_life_periods,
        direction=(
            None
            if edge.peak_elasticity is None
            else ("positive" if edge.peak_elasticity >= 0 else "negative")
        ),
        effects=[
            HorizonEffectResponse(
                horizon_periods=e.horizon,
                elasticity_pct=round(e.elasticity * 100.0, 2),
                ci_low_pct=round(e.ci_low * 100.0, 2),
                ci_high_pct=round(e.ci_high * 100.0, 2),
                n_episodes=e.n_episodes,
                status=e.status,
            )
            for e in edge.effects
            if e.elasticity == e.elasticity  # drop NaN horizons
        ],
        narrative=_narrate(edge),
    )


@router.get("/status")
async def spillover_status() -> Dict[str, Any]:
    """
    Artifact availability and provenance. Never fails, so dashboards can
    always render a truthful state.
    """
    return get_spillover_service().status()


@router.post("/reload")
async def reload_spillover() -> Dict[str, Any]:
    """Hot-reload the artifact after an offline rebuild."""
    service = get_spillover_service()
    reloaded = service.reload()
    return {"reloaded": reloaded, "status": service.status()}


@router.get("/commodities")
async def spillover_commodities() -> Dict[str, Any]:
    """Commodities covered by the current artifact."""
    service = _require_service()
    return {
        "commodities": service.commodities(),
        "shock_types": list(_SHOCK_TYPES),
    }


@router.get("/matrix")
async def spillover_matrix(
    actionable_only: bool = Query(
        False,
        description="Return only edges that survived the evidence and FDR gates",
    ),
) -> Dict[str, Any]:
    """The full matrix with provenance and diagnostics."""
    service = _require_service()
    matrix = service.matrix
    edges = matrix.actionable_edges if actionable_only else matrix.edges
    return {
        "summary": matrix.summary(),
        "markets": matrix.markets,
        "edges": [_serialize(e).model_dump() for e in edges],
    }


@router.get("/impacts/{commodity}", response_model=SpilloverImpactResponse)
async def spillover_impacts(
    commodity: str,
    shock_type: str = Query(SHOCK_SQUEEZE, description="SQUEEZE or GLUT"),
    actionable_only: bool = Query(True),
) -> SpilloverImpactResponse:
    """
    What a shock in ``commodity`` implies for every other commodity.

    This is the primary read for the UI: a forward-looking, pre-positioning
    signal rather than a price forecast.
    """
    service = _require_service()

    normalized = shock_type.strip().upper()
    if normalized not in _SHOCK_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"shock_type must be one of {list(_SHOCK_TYPES)}; got {shock_type!r}",
        )

    known = service.commodities()
    resolved = commodity.strip().lower()
    if resolved not in known:
        raise HTTPException(
            status_code=404,
            detail=f"Commodity {commodity!r} is not in the spillover panel. Known: {known}",
        )

    impacts = service.get_impacts(resolved, normalized, actionable_only=actionable_only)
    matrix = service.matrix

    verdict = matrix.placebo_verdict
    if verdict == "PASS":
        evidence_state = "VALIDATED"
        caveat = (
            "Estimated from historical episodes on residual returns after "
            "removing the common market factor, and confirmed by a permutation "
            "placebo. Each commodity is sourced from a different benchmark "
            "market, so effects are national rather than local. Intervals are "
            "wide because shock episodes are rare; treat these as a lead "
            "indicator, not a price forecast."
        )
    elif verdict == "FAIL":
        evidence_state = "NOT_VALIDATED"
        caveat = (
            "No cross-commodity transmission is published for this panel. A "
            "permutation placebo found that randomising the shock dates "
            "produced as many statistically significant edges as the real "
            "dates did, so any individual edge would be indistinguishable from "
            "chance. This reflects the width of the current panel - five "
            "commodities, each from a different market, with few independent "
            "shock episodes - rather than a failure of the estimator. Adding "
            "commodities observed in the same market is what would change it."
        )
    else:
        evidence_state = "UNVALIDATED"
        caveat = (
            "Estimated from historical episodes on residual returns after "
            "removing the common market factor, but no permutation placebo has "
            "been run against this artifact. Treat these edges as provisional "
            "until it has."
        )

    return SpilloverImpactResponse(
        source=resolved,
        shock_type=normalized,
        frequency=matrix.frequency,
        available=True,
        validated=matrix.is_validated,
        evidence_state=evidence_state,
        impacts=[_serialize(e) for e in impacts],
        caveat=caveat,
    )


@router.get("/edge/{source}/{target}")
async def spillover_edge(
    source: str,
    target: str,
    shock_type: str = Query(SHOCK_SQUEEZE),
) -> Dict[str, Any]:
    """
    A single edge including its full horizon profile.

    Under-evidenced edges are returned rather than hidden, so the caller can
    show "tested, inconclusive" instead of silently nothing.
    """
    service = _require_service()
    edge = service.get_edge(source, target, shock_type)
    if edge is None:
        raise HTTPException(
            status_code=404,
            detail=f"No spillover edge for {source} -> {target} under {shock_type}",
        )
    return _serialize(edge).model_dump()
