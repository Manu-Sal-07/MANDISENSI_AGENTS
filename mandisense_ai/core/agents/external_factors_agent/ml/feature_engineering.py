from datetime import datetime
try:
    from mandisense_ai.core.agents.external_factors_agent.config.settings import CURRENT_DATE, COMMODITIES
except ImportError:
    from config.settings import CURRENT_DATE, COMMODITIES

def build_features(events):
    features_by_comm = {}
    current = datetime.strptime(CURRENT_DATE, "%Y-%m-%d")
    
    for ev in events:
        c = ev["commodity"]
        event_date = datetime.strptime(ev["event_date"], "%Y-%m-%d")
        days = (current - event_date).days
        
        if c not in features_by_comm:
            features_by_comm[c] = {
                "events_list": [],
                "days_list": []
            }
        features_by_comm[c]["events_list"].append(ev)
        features_by_comm[c]["days_list"].append(days)
        
    results = []
    present_commodities = set(features_by_comm.keys())
    
    for c in COMMODITIES:
        if c not in present_commodities:
            # Edge rules: No events -> all values = 0
            results.append({
                "commodity": c,
                "event_count_3d": 0,
                "event_count_7d": 0,
                "avg_confidence": 0.0,
                "max_impact": 0.0,
                "sum_impact": 0.0,
                "recent_event_flag": 0,
                "days_since_last_event": 0
            })
            continue
            
        data = features_by_comm[c]
        events_list = data["events_list"]
        days_list = data["days_list"]
        
        event_count_3d = sum(1 for d in days_list if 0 <= d <= 3)
        event_count_7d = sum(1 for d in days_list if 0 <= d <= 7)
        
        # No division errors allowed
        if len(events_list) > 0:
            avg_confidence = sum(e.get("confidence", 0) for e in events_list) / len(events_list)
        else:
            avg_confidence = 0.0
            
        max_impact = max((e.get("adjusted_score", 0) for e in events_list), default=0.0)
        sum_impact = sum(e.get("adjusted_score", 0) for e in events_list)
        
        min_days = min(days_list)
        recent_event_flag = 1 if min_days <= 2 else 0
        days_since_last_event = min_days
        
        results.append({
            "commodity": c,
            "event_count_3d": event_count_3d,
            "event_count_7d": event_count_7d,
            "avg_confidence": avg_confidence,
            "max_impact": max_impact,
            "sum_impact": sum_impact,
            "recent_event_flag": recent_event_flag,
            "days_since_last_event": days_since_last_event
        })
            
    return results
