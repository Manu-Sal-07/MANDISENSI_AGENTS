import math
from typing import Any, Dict, List

REQUIRED_FIELDS = {"name", "price", "arrival", "lat", "lon"}


def _is_finite_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def validate_mandi_data(data: List[Dict[str, Any]]) -> bool:
    if not isinstance(data, list) or not data:
        return False

    for record in data:
        if not isinstance(record, dict):
            return False

        if not REQUIRED_FIELDS.issubset(record.keys()):
            return False

        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            return False

        if not _is_finite_number(record.get("price")):
            return False
        if not _is_finite_number(record.get("arrival")):
            return False
        if not _is_finite_number(record.get("lat")):
            return False
        if not _is_finite_number(record.get("lon")):
            return False

        price = float(record["price"])
        arrival = float(record["arrival"])

        if price <= 0:
            return False
        if arrival < 0:
            return False

    return True
