"""
Reading the crop, place, quantity and horizon out of a question.

Works across English, Kannada and Hindi (names and numerals in each script).
Used by the tool-driven fallback to decide what to look up, and by every mode
to carry context between turns ("and in Mulbagal?" keeps the crop).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from mandisense_ai.chat.languages import normalise_digits
from mandisense_ai.farmer import registry

# canonical id -> display names and the words people use for it
CROPS: Dict[str, Dict[str, object]] = {
    "tomato": {"en": "Tomato", "kn": "ಟೊಮೇಟೊ", "hi": "टमाटर",
               "words": ["tomato", "tomatoes", "ಟೊಮೇಟೊ", "ಟೊಮ್ಯಾಟೊ", "ಟೊಮ್ಯಾಟೋ", "ಟೊಮೆಟೊ", "टमाटर"]},
    "onion": {"en": "Onion", "kn": "ಈರುಳ್ಳಿ", "hi": "प्याज़",
              "words": ["onion", "onions", "ಈರುಳ್ಳಿ", "ಉಳ್ಳಾಗಡ್ಡಿ", "प्याज", "प्याज़"]},
    "potato": {"en": "Potato", "kn": "ಆಲೂಗಡ್ಡೆ", "hi": "आलू",
               "words": ["potato", "potatoes", "ಆಲೂಗಡ್ಡೆ", "ಆಲೂಗೆಡ್ಡೆ", "आलू"]},
    "ginger": {"en": "Ginger", "kn": "ಶುಂಠಿ", "hi": "अदरक",
               "words": ["ginger", "ಶುಂಠಿ", "अदरक"]},
    "garlic": {"en": "Garlic", "kn": "ಬೆಳ್ಳುಳ್ಳಿ", "hi": "लहसुन",
               "words": ["garlic", "ಬೆಳ್ಳುಳ್ಳಿ", "ಬೆಳ್ಳೂಳ್ಳಿ", "लहसुन"]},
    "dry_chillies": {"en": "Dry chillies", "kn": "ಒಣ ಮೆಣಸಿನಕಾಯಿ", "hi": "सूखी मिर्च",
                     "words": ["chilli", "chillies", "chili", "chilies", "ಮೆಣಸಿನಕಾಯಿ", "ಮೆಣಸು", "मिर्च"]},
}

_QTY = re.compile(
    r"(\d+(?:\.\d+)?)\s*(quintals?|qtls?|qtl|ಕ್ವಿಂಟಾಲ್|ಕ್ವಿಂಟಲ್|क्विंटल|tonnes?|tons?|ಟನ್|टन|kg|ಕೆಜಿ|किलो)",
    re.IGNORECASE,
)
_DAYS = re.compile(r"(\d+)\s*(?:-?\s*)(days?|ದಿನ|ದಿನಗಳ|दिन|दिनों)", re.IGNORECASE)


@dataclass
class Entities:
    crop: Optional[str] = None
    district: Optional[str] = None
    mandi_id: Optional[str] = None
    quantity_quintals: Optional[float] = None
    horizon_days: Optional[int] = None

    def as_dict(self) -> Dict[str, object]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def crop_name(crop: str, lang: str) -> str:
    entry = CROPS.get(crop)
    name = str(entry.get(lang) or entry["en"]) if entry else crop.replace("_", " ")
    return name.lower() if lang == "en" else name


def place_name(place_id: str, lang: str) -> str:
    return registry.display_name(place_id, lang)


def _place_names(entry) -> List[str]:
    names = []
    for n in (entry.name, entry.name_kn, entry.name_hi):
        base = n.split(" (")[0].strip()
        if base:
            names.append(base.lower())
        for inner in re.findall(r"\(([^)]+)\)", n):
            names.append(inner.strip().lower())
    return names


def extract(text: str) -> Entities:
    t = normalise_digits(text).lower()
    ent = Entities()

    for crop, entry in CROPS.items():
        if any(w.lower() in t for w in entry["words"]):  # type: ignore[union-attr]
            ent.crop = crop
            break

    # a mandi is more specific than its district, so it wins when both appear
    for m in registry.MANDIS.values():
        if any(n and n in t for n in _place_names(m)):
            ent.mandi_id, ent.district = m.id, m.district
            break
    if ent.district is None:
        for d in registry.DISTRICTS.values():
            if any(n and n in t for n in _place_names(d)):
                ent.district = d.id
                break

    q = _QTY.search(t)
    if q:
        value, unit = float(q.group(1)), q.group(2).lower()
        if unit in ("tonne", "tonnes", "ton", "tons", "ಟನ್", "टन"):
            value *= 10.0
        elif unit in ("kg", "ಕೆಜಿ", "किलो"):
            value /= 100.0
        ent.quantity_quintals = round(value, 2)

    d = _DAYS.search(t)
    if d:
        ent.horizon_days = int(d.group(1))
    return ent


def merge(current: Entities, previous: Dict[str, object], ui: Dict[str, object]) -> Entities:
    """Fill what this question did not say from the last turn, then from the page
    the user is on. A place named now always beats an older one."""
    out = Entities(**current.as_dict())
    for source in (previous or {}, ui or {}):
        out.crop = out.crop or source.get("crop")  # type: ignore[assignment]
        if out.mandi_id is None and out.district is None:
            out.mandi_id = source.get("mandi_id")  # type: ignore[assignment]
            out.district = source.get("district")  # type: ignore[assignment]
        elif out.district is None:
            out.district = source.get("district")  # type: ignore[assignment]
        out.quantity_quintals = out.quantity_quintals or source.get("quantity_quintals")  # type: ignore[assignment]
        out.horizon_days = out.horizon_days or source.get("horizon_days")  # type: ignore[assignment]
    if out.mandi_id and not out.district:
        out.district = registry.district_of(out.mandi_id)
    if out.district and not out.mandi_id:
        d = registry.DISTRICTS.get(out.district)
        out.mandi_id = d.anchor_mandi if d else None
    return out
