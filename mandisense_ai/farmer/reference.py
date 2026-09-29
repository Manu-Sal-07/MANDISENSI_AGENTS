"""
Reference data for the farmer-facing feature set.

Static facts that every farmer feature needs and none of them owns:
where a mandi physically is, how long a crop keeps before it starts losing
value, and what to call a crop in the language a farmer actually reads in.
Kept in one place so a new feature does not invent its own copy of a
15-mandi coordinate list or a shelf-life guess that quietly disagrees with
another feature's guess.

Coordinates are approximate town-centre points for the real Karnataka
market towns this system already tracks (see `forecasting/config.py`
TARGET_STATES and the market list `mandisense_ai/forecasting/naming.py`
resolves onto) -- accurate enough for a straight-line distance estimate
between mandis a farmer is choosing between, not a routing API.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Dict, Optional

# ── mandi coordinates ───────────────────────────────────────────────────────
# (latitude, longitude) for each tracked Karnataka market town.
MANDI_COORDINATES: Dict[str, tuple] = {
    "bangalore_yeshwanthpur": (13.0270, 77.5540),
    "hoskote_apmc": (13.0708, 77.7975),
    "anekal_apmc": (12.7106, 77.6960),
    "kolar_apmc": (13.1372, 78.1298),
    "bangarpet_apmc": (12.9635, 78.1745),
    "ramanagara_apmc": (12.7217, 77.2812),
    "channapatna_apmc": (12.6514, 77.2065),
    "chickballapur_apmc": (13.4355, 77.7315),
    "sidlaghatta_apmc": (13.3902, 77.8676),
    "doddaballapur_apmc": (13.2925, 77.5350),
    "kanakapura_apmc": (12.5461, 77.4189),
    "kunigal_apmc": (13.0270, 77.0230),
    "magadi_apmc": (12.9575, 77.2255),
    "malur_apmc": (12.9585, 77.9345),
    "nelamangala_apmc": (13.1008, 77.3928),
}

MANDI_DISPLAY_NAMES: Dict[str, str] = {
    mandi_id: mandi_id.replace("_apmc", "").replace("_", " ").title()
    for mandi_id in MANDI_COORDINATES
}


def haversine_km(a: tuple, b: tuple) -> float:
    """Great-circle distance between two (lat, lon) points, in kilometres."""
    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def distance_between_mandis_km(mandi_a: str, mandi_b: str) -> Optional[float]:
    a, b = MANDI_COORDINATES.get(mandi_a), MANDI_COORDINATES.get(mandi_b)
    if a is None or b is None:
        return None
    return round(haversine_km(a, b), 1)


def nearest_mandis(lat: float, lon: float, limit: int = 5) -> list:
    """Tracked mandis ordered by straight-line distance from a point."""
    ranked = sorted(
        MANDI_COORDINATES.items(),
        key=lambda item: haversine_km((lat, lon), item[1]),
    )
    return [
        {
            "mandi_id": mandi_id,
            "mandi_name": MANDI_DISPLAY_NAMES[mandi_id],
            "distance_km": round(haversine_km((lat, lon), coords), 1),
        }
        for mandi_id, coords in ranked[:limit]
    ]


# ── crop perishability ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class ShelfProfile:
    """How a crop behaves in ordinary on-farm or mandi-side storage.

    `shelf_life_days` and `daily_loss_pct` are deliberately coarse (no
    cold-chain, no controlled humidity) because that is the storage a
    smallholder actually has access to -- a granary, a shaded room, or
    nothing. They exist to answer one question honestly: is waiting for a
    better price worth what the crop loses by sitting, or does it not
    survive long enough for "wait" to be a real option at all.
    """

    shelf_life_days: int
    """Days before the crop is unsellable at any price in ordinary storage."""
    daily_loss_pct: float
    """Value lost per day held, from spoilage and shrinkage alone -- before
    any price movement. A HOLD call is only worth taking if the forecast's
    expected gain clears this cost."""
    category: str


SHELF_PROFILES: Dict[str, ShelfProfile] = {
    "tomato": ShelfProfile(shelf_life_days=5, daily_loss_pct=8.0, category="highly_perishable"),
    "onion": ShelfProfile(shelf_life_days=120, daily_loss_pct=0.3, category="storable"),
    "potato": ShelfProfile(shelf_life_days=90, daily_loss_pct=0.4, category="storable"),
    "garlic": ShelfProfile(shelf_life_days=180, daily_loss_pct=0.15, category="storable"),
    "ginger": ShelfProfile(shelf_life_days=30, daily_loss_pct=1.5, category="semi_perishable"),
    "dry_chillies": ShelfProfile(shelf_life_days=270, daily_loss_pct=0.1, category="storable"),
}

DEFAULT_SHELF_PROFILE = ShelfProfile(shelf_life_days=14, daily_loss_pct=2.0, category="unknown")


def shelf_profile(commodity: str) -> ShelfProfile:
    return SHELF_PROFILES.get(commodity, DEFAULT_SHELF_PROFILE)


# ── crop names, Kannada-first ───────────────────────────────────────────────
# The tracked mandis are all in Karnataka; Kannada is the first-read language
# for the population this surface serves, and it was entirely absent from
# the frontend before this feature set (Hindi existed, Kannada did not).

CROP_NAMES_KANNADA: Dict[str, str] = {
    "tomato": "ಟೊಮೇಟೊ",
    "onion": "ಈರುಳ್ಳಿ",
    "potato": "ಆಲೂಗಡ್ಡೆ",
    "garlic": "ಬೆಳ್ಳುಳ್ಳಿ",
    "ginger": "ಶುಂಠಿ",
    "dry_chillies": "ಒಣ ಮೆಣಸಿನಕಾಯಿ",
}

UNIT_QUINTAL_KANNADA = "ಕ್ವಿಂಟಾಲ್"
