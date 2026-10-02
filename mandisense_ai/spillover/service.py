"""
Runtime access to the spillover artifact.

Contract with the rest of the system:

* **Read-only.** No estimation, no pandas, no disk scanning per request. The
  artifact is loaded once and cached.
* **Never raises into a request path.** Every public method degrades to an
  empty/unavailable result. A missing or corrupt artifact must not be able to
  take down prediction, cognition, or health endpoints - spillover is an
  enrichment, not a dependency.
* **Hot-reloadable.** ``reload()`` picks up a freshly built artifact without a
  process restart, so a rebuild does not require redeployment.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from mandisense_ai.spillover.config import SHOCK_GLUT, SHOCK_SQUEEZE
from mandisense_ai.spillover.matrix import (
    SpilloverEdge,
    SpilloverMatrix,
    default_artifact_path,
)
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_VALID_SHOCK_TYPES = frozenset({SHOCK_SQUEEZE, SHOCK_GLUT})


class SpilloverService:
    """
    Process-wide cached accessor for the spillover matrix.

    Thread-safe: loading is guarded by a lock so concurrent first requests
    cannot race to parse the artifact twice.
    """

    def __init__(self, artifact_path: Optional[Path] = None) -> None:
        self._artifact_path = Path(artifact_path) if artifact_path else None
        self._matrix: Optional[SpilloverMatrix] = None
        self._load_error: Optional[str] = None
        self._loaded = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------- lifecycle

    def _resolve_path(self) -> Path:
        if self._artifact_path is not None:
            return self._artifact_path
        from mandisense_ai.config.settings import settings

        return default_artifact_path(Path(settings.paths.models_dir))

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:  # another thread won the race
                return
            path = self._resolve_path()
            try:
                self._matrix = SpilloverMatrix.load(path)
                self._load_error = None
                logger.info(
                    "Spillover matrix loaded from %s (%d edges, %d actionable)",
                    path,
                    len(self._matrix.edges),
                    len(self._matrix.actionable_edges),
                )
            except FileNotFoundError:
                self._matrix = None
                self._load_error = "artifact_not_built"
                logger.warning(
                    "Spillover artifact not found at %s; feature will report "
                    "as unavailable until it is built",
                    path,
                )
            except Exception as exc:  # corrupt JSON, schema mismatch, ...
                self._matrix = None
                self._load_error = f"artifact_unreadable: {exc}"
                logger.error("Failed to load spillover artifact from %s: %s", path, exc)
            finally:
                self._loaded = True

    def reload(self) -> bool:
        """Drop the cache and reload. Returns True if a matrix is now available."""
        with self._lock:
            self._loaded = False
            self._matrix = None
            self._load_error = None
        self._ensure_loaded()
        return self._matrix is not None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._matrix is not None

    @property
    def matrix(self) -> Optional[SpilloverMatrix]:
        self._ensure_loaded()
        return self._matrix

    # --------------------------------------------------------------- queries

    def status(self) -> Dict[str, Any]:
        """Health/diagnostic payload. Always safe to call."""
        self._ensure_loaded()
        if self._matrix is None:
            return {
                "available": False,
                "reason": self._load_error or "unknown",
                "artifact_path": str(self._resolve_path()),
            }
        payload = self._matrix.summary()
        payload["available"] = True
        payload["artifact_path"] = str(self._resolve_path())
        return payload

    def get_impacts(
        self,
        source: str,
        shock_type: str,
        actionable_only: bool = True,
    ) -> List[SpilloverEdge]:
        """
        Edges transmitting away from ``source`` under ``shock_type``.

        Returns an empty list - never raises - when the artifact is
        unavailable or the arguments do not match anything.
        """
        self._ensure_loaded()
        if self._matrix is None:
            return []

        normalized_shock = str(shock_type or "").strip().upper()
        if normalized_shock not in _VALID_SHOCK_TYPES:
            logger.debug("Unknown shock type requested: %r", shock_type)
            return []

        # A failed placebo invalidates the pipeline, not just individual edges,
        # so no edge may be served as actionable regardless of its own interval.
        if actionable_only and self._matrix.placebo_verdict == "FAIL":
            return []

        normalized_source = str(source or "").strip().lower()
        try:
            return self._matrix.downstream(
                normalized_source, normalized_shock, actionable_only=actionable_only
            )
        except Exception as exc:  # defensive: query must never break a request
            logger.error("Spillover query failed for %s/%s: %s", source, shock_type, exc)
            return []

    def get_edge(
        self,
        source: str,
        target: str,
        shock_type: str,
    ) -> Optional[SpilloverEdge]:
        """A single edge, including under-evidenced ones, or None."""
        self._ensure_loaded()
        if self._matrix is None:
            return None
        try:
            return self._matrix.get_edge(
                str(source).strip().lower(),
                str(target).strip().lower(),
                str(shock_type).strip().upper(),
            )
        except Exception as exc:
            logger.error("Spillover edge lookup failed: %s", exc)
            return None

    def commodities(self) -> List[str]:
        self._ensure_loaded()
        return list(self._matrix.commodities) if self._matrix else []


_SERVICE: Optional[SpilloverService] = None
_SERVICE_LOCK = threading.Lock()


def get_spillover_service() -> SpilloverService:
    """Process-wide singleton accessor."""
    global _SERVICE
    if _SERVICE is None:
        with _SERVICE_LOCK:
            if _SERVICE is None:
                _SERVICE = SpilloverService()
    return _SERVICE
