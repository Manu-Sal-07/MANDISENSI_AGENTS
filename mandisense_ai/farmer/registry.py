"""
The farmer surface's own map of the world: districts, the mandis inside them,
and the crops it serves.

Kept apart from `farmer/reference.py` on purpose. That file's mandi list is
shared with the trader analytics (arbitrage, CEDA lookups) and is keyed to a
different, older set of market ids; editing it to describe what the farmer
data actually covers would change trader behaviour. This registry describes
exactly the markets that report real prices in the farmer data set, and
nothing else, so the farmer screens can never offer a place the data cannot
speak for.

Coordinates are approximate town-centre points (good to a few kilometres),
used only for "nearest district" and straight-line distance between mandis,
never for routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Mandi:
    id: str
    name: str
    name_kn: str
    name_hi: str
    district: str
    lat: float
    lon: float
    agmarknet_market: str


@dataclass(frozen=True)
class District:
    id: str
    name: str
    name_kn: str
    name_hi: str
    agmarknet_district: str
    lat: float
    lon: float
    anchor_mandi: str


DISTRICTS: Dict[str, District] = {
    d.id: d
    for d in (
        District("bengaluru", "Bengaluru", "ಬೆಂಗಳೂರು", "बेंगलुरु", "Bengaluru", 13.0270, 77.5540, "bengaluru_apmc"),
        District("kolar", "Kolar", "ಕೋಲಾರ", "कोलार", "Kolar", 13.1372, 78.1298, "kolar_apmc"),
        District("chikkaballapur", "Chikkaballapur", "ಚಿಕ್ಕಬಳ್ಳಾಪುರ", "चिक्कबल्लापुर", "Chikkaballapur", 13.4355, 77.7315, "chikkaballapura_apmc"),
        District("bengaluru_south", "Bengaluru South (Ramanagara)", "ಬೆಂಗಳೂರು ದಕ್ಷಿಣ (ರಾಮನಗರ)", "बेंगलुरु दक्षिण (रामनगर)", "Bengaluru South", 12.7159, 77.2815, "ramanagara_apmc"),
        District("bengaluru_rural", "Bengaluru Rural", "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ", "बेंगलुरु ग्रामीण", "Bengaluru Rural", 13.2957, 77.5373, "doddaballapur_apmc"),
    )
}

MANDIS: Dict[str, Mandi] = {
    m.id: m
    for m in (
        Mandi("bengaluru_apmc", "Bengaluru (Yeshwanthpur)", "ಬೆಂಗಳೂರು (ಯಶವಂತಪುರ)", "बेंगलुरु (यशवंतपुर)", "bengaluru", 13.0270, 77.5540, "Bengaluru APMC"),
        Mandi("binny_mill_apmc", "Binny Mill, Bengaluru", "ಬಿನ್ನಿ ಮಿಲ್, ಬೆಂಗಳೂರು", "बिन्नी मिल, बेंगलुरु", "bengaluru", 12.9680, 77.5680, "Binny Mill (FF&V) Bengaluru APMC"),
        Mandi("kolar_apmc", "Kolar", "ಕೋಲಾರ", "कोलार", "kolar", 13.1372, 78.1298, "Kolar APMC"),
        Mandi("mulbagal_apmc", "Mulbagal", "ಮುಳಬಾಗಿಲು", "मुलबागल", "kolar", 13.1646, 78.3948, "Mulbagal APMC"),
        Mandi("bangarpet_apmc", "Bangarpet", "ಬಂಗಾರಪೇಟೆ", "बंगारपेट", "kolar", 12.9916, 78.1783, "Bangarpet APMC"),
        Mandi("malur_apmc", "Malur", "ಮಾಲೂರು", "मालूर", "kolar", 13.0029, 77.9390, "Malur APMC"),
        Mandi("srinivasapur_apmc", "Srinivasapur", "ಶ್ರೀನಿವಾಸಪುರ", "श्रीनिवासपुर", "kolar", 13.3356, 78.2131, "Srinivasapur APMC"),
        Mandi("chintamani_apmc", "Chintamani", "ಚಿಂತಾಮಣಿ", "चिंतामणि", "chikkaballapur", 13.4006, 78.0548, "Chintamani APMC"),
        Mandi("bagepalli_apmc", "Bagepalli", "ಬಾಗೇಪಲ್ಲಿ", "बागेपल्ली", "chikkaballapur", 13.7836, 77.7946, "Bagepalli APMC"),
        Mandi("gauribidanur_apmc", "Gauribidanur", "ಗೌರಿಬಿದನೂರು", "गौरीबिदनूर", "chikkaballapur", 13.6110, 77.5156, "Gauribidanur APMC"),
        Mandi("chikkaballapura_apmc", "Chikkaballapur", "ಚಿಕ್ಕಬಳ್ಳಾಪುರ", "चिक्कबल्लापुर", "chikkaballapur", 13.4355, 77.7315, "Chickkaballapura APMC"),
        Mandi("ramanagara_apmc", "Ramanagara", "ರಾಮನಗರ", "रामनगर", "bengaluru_south", 12.7159, 77.2815, "Ramanagara APMC"),
        Mandi("channapatna_apmc", "Channapatna", "ಚನ್ನಪಟ್ಟಣ", "चन्नपटना", "bengaluru_south", 12.6514, 77.2065, "Channapatna APMC"),
        Mandi("kanakapura_apmc", "Kanakapura", "ಕನಕಪುರ", "कनकपुरा", "bengaluru_south", 12.5489, 77.4208, "Kanakapura APMC"),
        Mandi("doddaballapur_apmc", "Doddaballapur", "ದೊಡ್ಡಬಳ್ಳಾಪುರ", "दोड्डबल्लापुर", "bengaluru_rural", 13.2957, 77.5373, "Doddaballapur APMC"),
        Mandi("hoskote_apmc", "Hoskote", "ಹೊಸಕೋಟೆ", "होसकोटे", "bengaluru_rural", 13.0708, 77.7975, "Hoskote APMC"),
    )
}

AGMARKNET_MARKET_TO_ID: Dict[str, str] = {m.agmarknet_market: m.id for m in MANDIS.values()}
AGMARKNET_DISTRICT_TO_ID: Dict[str, str] = {d.agmarknet_district: d.id for d in DISTRICTS.values()}
# The per-mandi download spells this district "Chikkaballapur"; the district
# report spells it the same way, but Agmarknet has used "Chikkaballapura" in
# other exports, so both resolve.
AGMARKNET_DISTRICT_TO_ID["Chikkaballapura"] = "chikkaballapur"

CROP_AGMARKNET: Dict[str, str] = {
    "tomato": "Tomato",
    "onion": "Onion",
    "potato": "Potato",
    "garlic": "Garlic",
    "ginger": "Ginger(Green)",
}
AGMARKNET_TO_CROP: Dict[str, str] = {v: k for k, v in CROP_AGMARKNET.items()}


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def nearest_district(lat: float, lon: float) -> Tuple[District, float]:
    best = min(DISTRICTS.values(), key=lambda d: haversine_km((lat, lon), (d.lat, d.lon)))
    return best, round(haversine_km((lat, lon), (best.lat, best.lon)), 1)


def mandis_in(district_id: str) -> List[Mandi]:
    return [m for m in MANDIS.values() if m.district == district_id]


def distance_km(mandi_a: str, mandi_b: str) -> Optional[float]:
    a, b = MANDIS.get(mandi_a), MANDIS.get(mandi_b)
    if a is None or b is None:
        return None
    return round(haversine_km((a.lat, a.lon), (b.lat, b.lon)), 1)


def is_district(place_id: str) -> bool:
    return str(place_id).strip().lower() in DISTRICTS


def resolve_place(place_id: str) -> str:
    """Lower-case a district or mandi id. Deliberately *not* the shared
    `canonical_market`, which would turn the district id `kolar` into the
    trader-side id `kolar_apmc` and point the lookup at a different series."""
    return str(place_id).strip().lower()


def district_of(place_id: str) -> str:
    """The district a place belongs to: a district is its own, a mandi maps to
    its district. Forecasts and history are kept per district."""
    place = resolve_place(place_id)
    if place in DISTRICTS:
        return place
    if place in MANDIS:
        return MANDIS[place].district
    return place


def series_place(place_id: str) -> str:
    """The id under which the forecast store keeps this place's series."""
    return district_of(place_id)


def display_name(place_id: str, lang: str = "en") -> str:
    place = resolve_place(place_id)
    entry = MANDIS.get(place) or DISTRICTS.get(place)
    if entry is None:
        return place
    return {"kn": entry.name_kn, "hi": entry.name_hi}.get(lang, entry.name)
