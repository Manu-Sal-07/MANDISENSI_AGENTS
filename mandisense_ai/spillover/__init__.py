"""
Cross-commodity spillover engine.

Estimates how a supply shock in one commodity transmits to the prices of
others, after removing the common market factor that would otherwise make
shared shocks look like transmission.

Public surface:
    build_spillover_matrix - offline artifact build
    SpilloverMatrix        - the artifact
    SpilloverService       - fail-safe runtime accessor
"""

from mandisense_ai.spillover.config import (
    DEFAULT_CONFIG,
    SHOCK_GLUT,
    SHOCK_SQUEEZE,
    SpilloverConfig,
)
from mandisense_ai.spillover.matrix import (
    SCHEMA_VERSION,
    SpilloverEdge,
    SpilloverMatrix,
    default_artifact_path,
)

__all__ = [
    "DEFAULT_CONFIG",
    "SHOCK_GLUT",
    "SHOCK_SQUEEZE",
    "SCHEMA_VERSION",
    "SpilloverConfig",
    "SpilloverEdge",
    "SpilloverMatrix",
    "default_artifact_path",
    "build_spillover_matrix",
    "SpilloverService",
    "get_spillover_service",
]


def __getattr__(name):
    # Deferred imports keep ``import mandisense_ai.spillover`` cheap and free of
    # pandas/numpy cost for callers that only need the constants.
    if name == "build_spillover_matrix":
        from mandisense_ai.spillover.build import build_spillover_matrix

        return build_spillover_matrix
    if name in ("SpilloverService", "get_spillover_service"):
        from mandisense_ai.spillover import service

        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
