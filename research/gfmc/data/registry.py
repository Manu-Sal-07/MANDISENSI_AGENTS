"""Geography: market and district coordinates, and farmer origins.

Coordinates for the 15 Bengaluru-belt APMCs and 5 district centres are taken
from the MandiSense application registry (`mandisense_ai/farmer/registry.py`),
copied here so that the research package has no dependency on the app.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Dict, Tuple

from gfmc.config import EXTRA_MARKET_COORDS

# Agmarknet market name -> (lat, lon)
MARKET_COORDS: Dict[str, Tuple[float, float]] = {
    "Bengaluru APMC": (13.0270, 77.5540),
    "Binny Mill (FF&V) Bengaluru APMC": (12.9680, 77.5680),
    "Kolar APMC": (13.1372, 78.1298),
    "Mulbagal APMC": (13.1646, 78.3948),
    "Bangarpet APMC": (12.9916, 78.1783),
    "Malur APMC": (13.0029, 77.9390),
    "Srinivasapur APMC": (13.3356, 78.2131),
    "Chintamani APMC": (13.4006, 78.0548),
    "Bagepalli APMC": (13.7836, 77.7946),
    "Gauribidanur APMC": (13.6110, 77.5156),
    "Chickkaballapura APMC": (13.4355, 77.7315),
    "Ramanagara APMC": (12.7159, 77.2815),
    "Channapatna APMC": (12.6514, 77.2065),
    "Kanakapura APMC": (12.5489, 77.4208),
    "Doddaballapur APMC": (13.2957, 77.5373),
    "Hoskote APMC": (13.0708, 77.7975),
    **EXTRA_MARKET_COORDS,
}

# Farmer origins: the five district centres of the study region.
ORIGINS: Dict[str, Tuple[float, float]] = {
    "Bengaluru": (13.0270, 77.5540),
    "Kolar": (13.1372, 78.1298),
    "Chikkaballapur": (13.4355, 77.7315),
    "Bengaluru South": (12.7159, 77.2815),
    "Bengaluru Rural": (13.2957, 77.5373),
}


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def coords(market: str) -> Tuple[float, float]:
    try:
        return MARKET_COORDS[market]
    except KeyError as exc:  # fail loudly: a silent default would corrupt distances
        raise KeyError(f"No coordinates for market '{market}'") from exc
