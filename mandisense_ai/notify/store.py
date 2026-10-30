"""
Subscribers and the delivery log.

JSON and JSONL files beside the other farmer stores (alerts, ledger): one record per Telegram chat, and an
append-only log of every message attempted, so what was sent, to whom and whether it arrived can be shown.
Only the chat id, first name, language, district and crops are kept.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()


def _dir() -> Path:
    from mandisense_ai.config.settings import settings

    d = Path(settings.paths.processed_data).parent / "farmer"
    d.mkdir(parents=True, exist_ok=True)
    return d


def subscribers_path() -> Path:
    return _dir() / "telegram_subscribers.json"


def log_path() -> Path:
    return _dir() / "telegram_outbox.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load() -> Dict[str, Dict[str, Any]]:
    p = subscribers_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save(subs: Dict[str, Dict[str, Any]]) -> None:
    p = subscribers_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def get(chat_id: int) -> Optional[Dict[str, Any]]:
    return load().get(str(chat_id))


def upsert(chat_id: int, **fields) -> Dict[str, Any]:
    with _LOCK:
        subs = load()
        rec = subs.get(str(chat_id), {"chat_id": chat_id, "created": now(), "lang": "en", "district": None, "crops": [],
                                      "subscribed": False, "step": "lang"})
        rec.update(fields)
        rec["updated"] = now()
        subs[str(chat_id)] = rec
        save(subs)
        return rec


def active() -> List[Dict[str, Any]]:
    return [s for s in load().values() if s.get("subscribed") and s.get("district") and s.get("crops")]


def log(entry: Dict[str, Any]) -> None:
    entry = {"at": now(), **entry}
    with _LOCK, open(log_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_log(limit: int = 50) -> List[Dict[str, Any]]:
    p = log_path()
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(x) for x in lines if x.strip()]
