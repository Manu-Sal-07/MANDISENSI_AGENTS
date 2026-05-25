from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

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

from typing import Tuple

class MarketTopology:
    """
    The Structural Brain of MandiSense.
    Models the causal dependencies between mandis, commodities, and corridors.
    """
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._initialize_institutional_topology()

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

    def add_node(self, node_id: str, node_type: str, metadata: Dict[str, Any] = {}):
        self.nodes[node_id] = Node(id=node_id, type=node_type, metadata=metadata)

    def add_edge(self, source: str, target: str, rel: str, weight: float, latency: float = 0):
        self.edges.append(Edge(source=source, target=target, relationship=rel, weight=weight, latency_hours=latency))

    def get_downstream_impacts(self, source_id: str) -> List[Edge]:
        return [e for e in self.edges if e.source == source_id]

    def get_upstream_drivers(self, target_id: str) -> List[Edge]:
        return [e for e in self.edges if e.target == target_id]
