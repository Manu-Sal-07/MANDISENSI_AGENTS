"""
/v1/notify: preview the farmer digest, list Telegram subscribers, send the digest now, and read the delivery log.
Used by the demo ("send today's bulletin" button) and by anyone checking what was sent.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from mandisense_ai.farmer import registry
from mandisense_ai.notify import digest, store

router = APIRouter(prefix="/v1/notify", tags=["Farmer notifications"])


@router.get("/preview")
def preview(district: str = "kolar", crops: str = "tomato,onion,potato", lang: str = "en"):
    if district not in registry.DISTRICTS:
        raise HTTPException(404, f"unknown district '{district}'")
    chosen = [c for c in crops.split(",") if c in digest.CROPS]
    return {"district": district, "crops": chosen, "lang": lang, "data_as_of": str(digest.data_as_of()),
            "message_html": digest.build_digest(district, chosen, lang)}


@router.get("/subscribers")
def subscribers():
    subs = store.load().values()
    return {"active": len(store.active()), "total": len(subs),
            "subscribers": [{"first_name": s.get("first_name", ""), "lang": s.get("lang"), "district": s.get("district"),
                             "crops": s.get("crops", []), "subscribed": s.get("subscribed", False)} for s in subs]}


@router.post("/send-now")
def send_now(dry_run: bool = Query(False)):
    from mandisense_ai.notify.telegram import broadcast

    try:
        return broadcast(dry_run=dry_run)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))


@router.get("/log")
def log(limit: int = 50):
    return {"entries": store.read_log(limit)}
