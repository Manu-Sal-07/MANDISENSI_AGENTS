def normalize_events(events):
    normalized = []
    valid_events = {
        "EXPORT_BAN", "IMPORT_DUTY_REDUCTION", "CROP_DAMAGE",
        "DROUGHT", "MSP_INCREASE", "FUEL_HIKE", 
        "DEMAND_SURGE", "STOCK_LIMIT", "OTHER_EVENT"
    }
    
    for ev in events:
        try:
            # lowercase commodity
            comm = str(ev.get("commodity", "")).lower()
            
            # validate event_type
            ev_type = ev.get("event_type", "")
            if ev_type not in valid_events:
                # Invalid -> drop
                continue
                
            # clamp confidence
            conf = float(ev.get("confidence", 0.0))
            conf = max(0.0, min(1.0, conf))
            
            normalized.append({
                "commodity": comm,
                "event_type": ev_type,
                "confidence": conf,
                "event_date": ev.get("event_date")
            })
        except Exception:
            continue
            
    return normalized
