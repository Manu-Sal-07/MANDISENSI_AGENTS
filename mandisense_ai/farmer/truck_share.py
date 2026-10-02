"""
Village Truck Sharing.

Transport is often the single largest cost between a farmer's field and a
fair price (see `transport.py`'s per-quintal rate), and most of it is paid
for a truck that is mostly empty. This is a small board: a farmer posts a
planned trip to a mandi with spare capacity, and another farmer heading to
the same mandi on the same day can claim a seat on it.

Kept as a plain shared board (post / list / join), not a matching or pricing
engine -- the trust and negotiation belong to the two farmers, not to this
system. File-backed for the same reason as `alerts.py`: this is
low-volume, append-mostly community data, not a workload that justifies a
new database dependency.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mandisense_ai.farmer import registry
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


def _board_path() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data).parent / "farmer" / "truck_share_board.json"


def _load() -> List[Dict[str, Any]]:
    path = _board_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Truck-share board unreadable at %s: %s", path, exc)
        return []


def _save(trips: List[Dict[str, Any]]) -> None:
    path = _board_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(trips, indent=2), encoding="utf-8")
    temp.replace(path)


def post_trip(
    mandi_id: str,
    travel_date: str,
    total_capacity_quintals: float,
    posted_by_phone: str,
    posted_by_name: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_mandi = registry.resolve_place(mandi_id)
    try:
        parsed_date = str(date.fromisoformat(travel_date))
    except ValueError:
        return {"status": "ERROR", "reason": "travel_date must be YYYY-MM-DD."}

    capacity = float(total_capacity_quintals)
    if capacity <= 0:
        return {"status": "ERROR", "reason": "total_capacity_quintals must be positive."}

    trip = {
        "id": uuid.uuid4().hex[:12],
        "mandi_id": resolved_mandi,
        "mandi_name": registry.display_name(resolved_mandi),
        "travel_date": parsed_date,
        "total_capacity_quintals": capacity,
        "claimed_quintals": 0.0,
        "posted_by_phone": str(posted_by_phone).strip(),
        "posted_by_name": posted_by_name or "A farmer",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "OPEN",
        "claims": [],
    }
    trips = _load()
    trips.append(trip)
    _save(trips)
    return {"status": "OK", "trip": trip}


def list_trips(mandi_id: Optional[str] = None, on_or_after: Optional[str] = None) -> List[Dict[str, Any]]:
    trips = [t for t in _load() if t.get("status") == "OPEN"]
    if mandi_id:
        resolved = registry.resolve_place(mandi_id)
        trips = [t for t in trips if t["mandi_id"] == resolved]
    if on_or_after:
        trips = [t for t in trips if t["travel_date"] >= on_or_after]
    return sorted(trips, key=lambda t: t["travel_date"])


def join_trip(trip_id: str, quantity_quintals: float, joiner_phone: str, joiner_name: Optional[str] = None) -> Dict[str, Any]:
    trips = _load()
    trip = next((t for t in trips if t["id"] == trip_id), None)
    if trip is None:
        return {"status": "ERROR", "reason": "Trip not found."}

    quantity = float(quantity_quintals)
    remaining = trip["total_capacity_quintals"] - trip["claimed_quintals"]
    if quantity > remaining:
        return {"status": "ERROR", "reason": f"Only {remaining} quintal(s) of capacity remain on this trip."}

    trip["claimed_quintals"] += quantity
    trip["claims"].append({
        "phone": str(joiner_phone).strip(),
        "name": joiner_name or "A farmer",
        "quantity_quintals": quantity,
        "joined_at": datetime.now(timezone.utc).isoformat(),
    })
    if trip["claimed_quintals"] >= trip["total_capacity_quintals"]:
        trip["status"] = "FULL"

    _save(trips)
    return {"status": "OK", "trip": trip}
