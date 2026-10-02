"""
The Spillover Matrix artifact.

This is the durable output of the whole engine: a versioned, self-describing
table of estimated commodity-to-commodity transmission edges. Serving reads
this artifact; it never re-estimates anything at request time.

Design commitments:

* **Evidence is first-class.** Every edge carries its episode count and
  confidence interval. An edge with too little support is published with
  status ``INSUFFICIENT_EVIDENCE`` rather than omitted, so the UI can say
  "we looked and could not tell" instead of silently showing nothing.
* **Provenance is embedded.** The artifact records the config, the panel hash,
  the commodity->market mapping and the build timestamp, so any number on a
  screen can be traced to the exact inputs that produced it.
* **Forward compatible.** ``SCHEMA_VERSION`` is checked on load; an artifact
  written by a newer, incompatible engine is refused rather than
  misinterpreted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mandisense_ai.spillover.estimator import (
    STATUS_INSUFFICIENT,
    STATUS_SIGNIFICANT,
    HorizonEffect,
)
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = "1.0.0"
DEFAULT_ARTIFACT_NAME = "spillover_matrix.json"


@dataclass(frozen=True)
class SpilloverEdge:
    """One directed (source -> target) transmission edge for one shock type."""

    source: str
    target: str
    shock_type: str
    effects: List[HorizonEffect]
    peak_horizon: Optional[int]
    peak_elasticity: Optional[float]
    status: str
    n_episodes: int
    half_life_periods: Optional[float] = None

    @property
    def is_actionable(self) -> bool:
        """True only when the edge is significant and has a usable peak."""
        return self.status == STATUS_SIGNIFICANT and self.peak_horizon is not None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "shock_type": self.shock_type,
            "status": self.status,
            "n_episodes": self.n_episodes,
            "peak_horizon": self.peak_horizon,
            "peak_elasticity": (
                round(self.peak_elasticity, 6) if self.peak_elasticity is not None else None
            ),
            "half_life_periods": (
                round(self.half_life_periods, 3) if self.half_life_periods is not None else None
            ),
            "effects": [e.as_dict() for e in self.effects],
        }

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "SpilloverEdge":
        effects = [
            HorizonEffect(
                horizon=int(e["horizon"]),
                elasticity=float(e["elasticity"]),
                ci_low=float(e["ci_low"]),
                ci_high=float(e["ci_high"]),
                baseline=float(e["baseline"]),
                n_episodes=int(e["n_episodes"]),
                status=str(e["status"]),
                p_value=(
                    float("nan") if e.get("p_value") is None else float(e["p_value"])
                ),
            )
            for e in payload.get("effects", [])
        ]
        return SpilloverEdge(
            source=payload["source"],
            target=payload["target"],
            shock_type=payload["shock_type"],
            effects=effects,
            peak_horizon=payload.get("peak_horizon"),
            peak_elasticity=payload.get("peak_elasticity"),
            status=payload.get("status", STATUS_INSUFFICIENT),
            n_episodes=int(payload.get("n_episodes", 0)),
            half_life_periods=payload.get("half_life_periods"),
        )


@dataclass
class SpilloverMatrix:
    """A complete, versioned set of spillover edges plus provenance."""

    edges: List[SpilloverEdge] = field(default_factory=list)
    commodities: List[str] = field(default_factory=list)
    markets: Dict[str, str] = field(default_factory=dict)
    frequency: str = "W"
    config: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    panel_hash: str = ""
    built_at: str = ""
    schema_version: str = SCHEMA_VERSION

    # ---------------------------------------------------------------- queries

    def get_edge(self, source: str, target: str, shock_type: str) -> Optional[SpilloverEdge]:
        for edge in self.edges:
            if (
                edge.source == source
                and edge.target == target
                and edge.shock_type == shock_type
            ):
                return edge
        return None

    def downstream(
        self,
        source: str,
        shock_type: str,
        actionable_only: bool = True,
    ) -> List[SpilloverEdge]:
        """
        Edges leading away from ``source``, strongest first.

        Defaults to actionable edges only, so callers cannot accidentally
        surface an under-evidenced estimate as a recommendation.
        """
        matches = [
            e for e in self.edges if e.source == source and e.shock_type == shock_type
        ]
        if actionable_only:
            matches = [e for e in matches if e.is_actionable]
        return sorted(
            matches,
            key=lambda e: abs(e.peak_elasticity or 0.0),
            reverse=True,
        )

    @property
    def actionable_edges(self) -> List[SpilloverEdge]:
        """
        Edges fit to drive a recommendation.

        If a permutation placebo was run and failed, nothing is actionable:
        a failed placebo means the pipeline produced no more significant edges
        than randomised shock dates would, so the individual edges carry no
        information however good their intervals look.
        """
        if self.placebo_verdict == "FAIL":
            return []
        return [e for e in self.edges if e.is_actionable]

    @property
    def placebo_verdict(self) -> Optional[str]:
        """'PASS', 'FAIL', or None when no placebo has been run."""
        placebo = self.diagnostics.get("placebo") if self.diagnostics else None
        if isinstance(placebo, dict):
            return placebo.get("verdict")
        return None

    @property
    def is_validated(self) -> bool:
        return self.placebo_verdict == "PASS"

    def summary(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for edge in self.edges:
            by_status[edge.status] = by_status.get(edge.status, 0) + 1
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "panel_hash": self.panel_hash,
            "frequency": self.frequency,
            "commodities": self.commodities,
            "total_edges": len(self.edges),
            "actionable_edges": len(self.actionable_edges),
            "by_status": by_status,
            "placebo_verdict": self.placebo_verdict,
            "is_validated": self.is_validated,
            "diagnostics": self.diagnostics,
        }

    # ------------------------------------------------------------ persistence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "panel_hash": self.panel_hash,
            "frequency": self.frequency,
            "commodities": self.commodities,
            "markets": self.markets,
            "config": self.config,
            "diagnostics": self.diagnostics,
            "edges": [e.as_dict() for e in self.edges],
        }

    def save(self, path: Path) -> Path:
        """
        Write the artifact atomically.

        A temp-file-then-replace keeps a concurrently running API from ever
        observing a half-written matrix.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.built_at:
            self.built_at = datetime.now(timezone.utc).isoformat()

        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=False),
            encoding="utf-8",
        )
        temp_path.replace(path)
        logger.info("Spillover matrix written to %s (%d edges)", path, len(self.edges))
        return path

    @staticmethod
    def load(path: Path) -> "SpilloverMatrix":
        """
        Load an artifact from disk.

        Raises:
            FileNotFoundError: if the artifact is absent.
            ValueError: if the schema major version does not match this engine.
        """
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))

        found_version = str(payload.get("schema_version", "0.0.0"))
        if found_version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
            raise ValueError(
                f"Incompatible spillover artifact schema {found_version}; "
                f"this engine expects {SCHEMA_VERSION}"
            )

        return SpilloverMatrix(
            edges=[SpilloverEdge.from_dict(e) for e in payload.get("edges", [])],
            commodities=payload.get("commodities", []),
            markets=payload.get("markets", {}),
            frequency=payload.get("frequency", "W"),
            config=payload.get("config", {}),
            diagnostics=payload.get("diagnostics", {}),
            panel_hash=payload.get("panel_hash", ""),
            built_at=payload.get("built_at", ""),
            schema_version=found_version,
        )


def default_artifact_path(models_dir: Path) -> Path:
    """Canonical on-disk location of the spillover artifact."""
    return Path(models_dir) / "spillover" / DEFAULT_ARTIFACT_NAME
