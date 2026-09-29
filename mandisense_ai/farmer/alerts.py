"""
Price alerts.

Farmers live on WhatsApp and SMS, not inside a web app they have to remember
to reopen -- so the useful form of every other feature here is "tell me the
moment it's true," not "come back and check." This is the subscription
half of that: a farmer registers a rule, and a nightly job (wired from
`forecasting/pipeline.run_nightly`, not yet built here) evaluates it against
the freshly published forecast and enqueues a notification.

No WhatsApp or SMS credential exists in this deployment yet, so nothing here
claims to send one. Notifications go to an append-only outbox file instead:
a real, inspectable record of exactly what *would* have been sent and to
whom, which is what makes wiring in a real provider later a matter of
reading this file rather than trusting an unverified new code path.

Storage is a JSON file rather than a database, matching every other
farmer-facing store in this system (the forecast ledger, the quarantine
store) -- appropriate at this scale, and it means no new infrastructure
dependency for a feature whose whole job is to notice a threshold was
crossed once a day.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

ALERT_TYPES = ("PRICE_ABOVE", "PRICE_BELOW", "DECISION_SELL", "DECISION_HOLD")


def _alerts_path() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data).parent / "farmer" / "price_alerts.json"


def _outbox_path() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data).parent / "farmer" / "notifications_outbox.jsonl"


def _load() -> List[Dict[str, Any]]:
    path = _alerts_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Alerts store unreadable at %s: %s", path, exc)
        return []


def _save(alerts: List[Dict[str, Any]]) -> None:
    path = _alerts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(alerts, indent=2), encoding="utf-8")
    temp.replace(path)


def create_alert(
    phone: str,
    commodity: str,
    mandi_id: str,
    alert_type: str,
    threshold: Optional[float] = None,
) -> Dict[str, Any]:
    if alert_type not in ALERT_TYPES:
        return {"status": "ERROR", "reason": f"alert_type must be one of {ALERT_TYPES}"}
    if alert_type in ("PRICE_ABOVE", "PRICE_BELOW") and threshold is None:
        return {"status": "ERROR", "reason": f"{alert_type} requires a threshold price"}

    resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
    resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()

    alert = {
        "id": uuid.uuid4().hex[:12],
        "phone": str(phone).strip(),
        "commodity": resolved_commodity,
        "mandi_id": resolved_mandi,
        "alert_type": alert_type,
        "threshold": float(threshold) if threshold is not None else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "last_triggered_at": None,
    }
    alerts = _load()
    alerts.append(alert)
    _save(alerts)
    return {"status": "OK", "alert": alert}


def list_alerts(phone: str) -> List[Dict[str, Any]]:
    phone = str(phone).strip()
    return [a for a in _load() if a.get("phone") == phone and a.get("active", True)]


def delete_alert(phone: str, alert_id: str) -> Dict[str, Any]:
    alerts = _load()
    phone = str(phone).strip()
    remaining = [a for a in alerts if not (a.get("id") == alert_id and a.get("phone") == phone)]
    if len(remaining) == len(alerts):
        return {"status": "ERROR", "reason": "Alert not found for this phone number."}
    _save(remaining)
    return {"status": "OK"}


def _write_outbox(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        return
    path = _outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def evaluate_alerts() -> Dict[str, int]:
    """
    Check every active alert against the currently published forecast store
    and enqueue a notification for each one that now fires.

    Meant to be called once per nightly run, after `run_forecast` publishes
    (mirrors how `ledger.record_publication` is wired into the pipeline).
    Never fails the caller: an evaluation error is logged and reported, not
    raised, because a broken alert check must not be allowed to take down
    the forecast publish it depends on.
    """
    alerts = _load()
    active = [a for a in alerts if a.get("active", True)]
    if not active:
        return {"checked": 0, "triggered": 0}

    try:
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
    except Exception as exc:
        logger.error("Alert evaluation: forecast service unavailable: %s", exc)
        return {"checked": len(active), "triggered": 0, "error": str(exc)}

    triggered_entries = []
    now = datetime.now(timezone.utc).isoformat()

    for alert in active:
        if not service.is_available:
            continue
        curve = service.get_curve(alert["commodity"], alert["mandi_id"])
        row = next((r for r in curve if r.get("horizon_days") == 1 and r.get("status") == "OK"), None)
        if row is None:
            continue

        fires = False
        reason = None
        price = row.get("forecast_price")
        decision = row.get("decision")

        if alert["alert_type"] == "PRICE_ABOVE" and price is not None and price >= alert["threshold"]:
            fires, reason = True, f"forecast price {price} >= threshold {alert['threshold']}"
        elif alert["alert_type"] == "PRICE_BELOW" and price is not None and price <= alert["threshold"]:
            fires, reason = True, f"forecast price {price} <= threshold {alert['threshold']}"
        elif alert["alert_type"] == "DECISION_SELL" and decision == "SELL":
            fires, reason = True, "SELL decision published"
        elif alert["alert_type"] == "DECISION_HOLD" and decision == "HOLD":
            fires, reason = True, "HOLD decision published"

        if fires:
            alert["last_triggered_at"] = now
            triggered_entries.append({
                "queued_at": now,
                "phone": alert["phone"],
                "commodity": alert["commodity"],
                "mandi_id": alert["mandi_id"],
                "alert_type": alert["alert_type"],
                "reason": reason,
                "forecast_price": price,
                "decision": decision,
                "delivery_status": "QUEUED_NO_PROVIDER_CONFIGURED",
            })

    if triggered_entries:
        _save(alerts)
        _write_outbox(triggered_entries)

    return {"checked": len(active), "triggered": len(triggered_entries)}
