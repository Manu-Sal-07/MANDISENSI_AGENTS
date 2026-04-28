from datetime import datetime

def isolate_event(target_event, all_events):
    date_str = target_event.get("effective_date")
    if not date_str:
        return 1.0 # default weight
        
    try:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
        overlap_count = 0
        
        for ev in all_events:
            ev_date_str = ev.get("effective_date")
            if not ev_date_str:
                continue
            ev_dt = datetime.strptime(ev_date_str, "%Y-%m-%d")
            diff = abs((target_dt - ev_dt).days)
            if diff <= 2:
                overlap_count += 1
                
        # attenuation_factor = 1 / number_of_events
        # overlap_count includes target_event itself so minimum is 1
        return 1.0 / max(1, overlap_count)
    except Exception:
        return 1.0
