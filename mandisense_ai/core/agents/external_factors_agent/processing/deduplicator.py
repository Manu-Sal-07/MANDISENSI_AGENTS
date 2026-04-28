from datetime import datetime
from config.settings import DEDUP_WINDOW_DAYS

def deduplicate(events):
    deduped = []
    for ev in events:
        is_dup = False
        for existing in deduped:
            # Two events duplicate if:
            # - same commodity
            # - same event_type
            if existing["commodity"] == ev["commodity"] and existing["event_type"] == ev["event_type"]:
                d1 = datetime.strptime(existing["event_date"], "%Y-%m-%d")
                d2 = datetime.strptime(ev["event_date"], "%Y-%m-%d")
                # - date difference <= 1 day (or DEDUP_WINDOW_DAYS)
                if abs((d1 - d2).days) <= DEDUP_WINDOW_DAYS:
                    is_dup = True
                    # Keep highest confidence
                    if ev["confidence"] > existing["confidence"]:
                        existing["confidence"] = ev["confidence"]
                        existing["event_date"] = ev["event_date"]
                    break
        if not is_dup:
            # Keep as copy to prevent mutation reference bugs
            deduped.append(dict(ev))
    return deduped
