import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("MarketTopology")

class Node(BaseModel):
    id: str
    type: str # "mandi", "commodity", "corridor"
    metadata: Dict[str, Any] = {}

class Edge(BaseModel):
    source: str
    target: str
    relationship: str # "influences", "sources_to", "substitutes"
    weight: float # 0.0 to 1.0 (Strength of causality)
    latency_hours: float = 0.0 # Time for shock propagation
    origin: str = "declared" # "declared" (hand-specified) or "learned" (estimated)
    direction: Optional[str] = None # Sign of the effect for learned edges
    evidence: Dict[str, Any] = Field(default_factory=dict) # Provenance for learned edges

class MarketRegistry:
    """
    Institutional Market Identity Infrastructure.
    Normalizes aliases and resolves geospatial coordinates with fallback.
    """
    MANDI_COORDS = {
        "kolar_apmc": (13.1377, 78.1299),
        "bangalore_apmc": (12.9716, 77.5946),
        "bangalore_rural": (13.2847, 77.6078),
        "mumbai_apmc": (19.0760, 72.8777),
        "nashik_apmc": (20.0110, 73.7903),
        "delhi_azadpur": (28.7161, 77.1723),
        "bengaluru": (12.9716, 77.5946) # Legacy alias
    }
    
    DISTRICT_MAPPINGS = {
        "kolar": "kolar_apmc",
        "bangalore": "bangalore_apmc",
        "mumbai": "mumbai_apmc",
        "nashik": "nashik_apmc",
        "delhi": "delhi_azadpur"
    }

    @classmethod
    def resolve_coordinates(cls, mandi_id: str) -> Optional[Tuple[float, float]]:
        key = mandi_id.lower().replace(" ", "_")
        if key in cls.MANDI_COORDS:
            return cls.MANDI_COORDS[key]
        
        # Try district fallback
        for dist, canon in cls.DISTRICT_MAPPINGS.items():
            if dist in key:
                return cls.MANDI_COORDS[canon]
        
        return None


class MarketTopology:
    """
    The Structural Brain of MandiSense.
    Models the causal dependencies between mandis, commodities, and corridors.
    """
    def __init__(self, load_learned_spillover: bool = True):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.spillover_source: str = "declared"
        self._initialize_institutional_topology()
        if load_learned_spillover:
            self._load_learned_spillover_edges()

    def _initialize_institutional_topology(self):
        """
        Hardcoded institutional topology for core agricultural corridors.
        """
        # --- Core Mandis ---
        self.add_node("kolar_apmc", "mandi", {"region": "Karnataka", "type": "production_hub"})
        self.add_node("bangalore_apmc", "mandi", {"region": "Karnataka", "type": "consumption_center"})
        self.add_node("mumbai_apmc", "mandi", {"region": "Maharashtra", "type": "terminal_market"})
        self.add_node("nashik_apmc", "mandi", {"region": "Maharashtra", "type": "production_hub"})
        self.add_node("delhi_azadpur", "mandi", {"region": "Delhi", "type": "national_hub"})

        # --- Causal Edges (Shock Propagation Corridors) ---
        # Kolar -> Bangalore (High influence, low latency)
        self.add_edge("kolar_apmc", "bangalore_apmc", "influences", 0.9, 12)
        # Nashik -> Mumbai
        self.add_edge("nashik_apmc", "mumbai_apmc", "influences", 0.85, 18)
        # Kolar -> Delhi (National supply chain)
        self.add_edge("kolar_apmc", "delhi_azadpur", "influences", 0.4, 48)
        
        # --- Commodity Dependencies (Substitution) ---
        self.add_node("tomato", "commodity")
        self.add_node("onion", "commodity")
        self.add_node("potato", "commodity")
        
        # Cross-commodity substitution
        self.add_edge("tomato", "onion", "substitutes", 0.3, 24)

    def _load_learned_spillover_edges(self) -> None:
        """
        Replace the hand-declared substitution edges with estimated ones.

        The declared ``substitutes`` edges above are placeholders: their weights
        and latencies were chosen by hand, not measured. When a spillover
        artifact is available its edges supersede them, carrying real
        elasticities, measured lags and the evidence behind each number.

        This is intentionally best-effort. If the artifact is missing, stale or
        unreadable the declared topology stands unchanged, because a market
        graph that fails to construct would take the whole cognition engine
        down with it. ``spillover_source`` records which path was taken.
        """
        try:
            from mandisense_ai.spillover.service import get_spillover_service

            service = get_spillover_service()
            if not service.is_available:
                return

            matrix = service.matrix
            if matrix is None:
                return

            # Must go through the matrix-level accessor, not the per-edge flag:
            # only the matrix applies the permutation-placebo gate, and an edge
            # can look individually significant in an artifact whose pipeline as
            # a whole failed validation.
            learned = matrix.actionable_edges
            if not learned:
                # An artifact with no actionable edges is a legitimate outcome
                # (the evidence simply did not support any). Keep the declared
                # graph rather than silently stripping substitution entirely.
                return

            periods_to_hours = 24.0 * 7.0 if matrix.frequency == "W" else 24.0

            self.edges = [e for e in self.edges if e.relationship != "substitutes"]

            for edge in learned:
                for node_id in (edge.source, edge.target):
                    if node_id not in self.nodes:
                        self.add_node(node_id, "commodity")

                self.edges.append(
                    Edge(
                        source=edge.source,
                        target=edge.target,
                        relationship="substitutes",
                        # Magnitude only: propagation strength is unsigned, and
                        # the sign is preserved separately in `direction`.
                        weight=min(1.0, abs(edge.peak_elasticity or 0.0)),
                        latency_hours=(edge.peak_horizon or 0) * periods_to_hours,
                        origin="learned",
                        direction="positive" if (edge.peak_elasticity or 0.0) >= 0 else "negative",
                        evidence={
                            "shock_type": edge.shock_type,
                            "elasticity": edge.peak_elasticity,
                            "horizon_periods": edge.peak_horizon,
                            "n_episodes": edge.n_episodes,
                            "status": edge.status,
                            "panel_hash": matrix.panel_hash,
                            "built_at": matrix.built_at,
                        },
                    )
                )

            self.spillover_source = "learned"
        except Exception as exc:  # never let topology construction fail
            logger.warning("Could not load learned spillover edges: %s", exc)

    def get_substitution_edges(self, commodity: str) -> List[Edge]:
        """Substitution edges leading away from a commodity, strongest first."""
        matches = [
            e for e in self.edges
            if e.relationship == "substitutes" and e.source == commodity
        ]
        return sorted(matches, key=lambda e: e.weight, reverse=True)

    def add_node(self, node_id: str, node_type: str, metadata: Dict[str, Any] = {}):
        self.nodes[node_id] = Node(id=node_id, type=node_type, metadata=metadata)

    def add_edge(self, source: str, target: str, rel: str, weight: float, latency: float = 0):
        self.edges.append(Edge(source=source, target=target, relationship=rel, weight=weight, latency_hours=latency))

    def get_downstream_impacts(self, source_id: str) -> List[Edge]:
        return [e for e in self.edges if e.source == source_id]

    def get_upstream_drivers(self, target_id: str) -> List[Edge]:
        return [e for e in self.edges if e.target == target_id]
