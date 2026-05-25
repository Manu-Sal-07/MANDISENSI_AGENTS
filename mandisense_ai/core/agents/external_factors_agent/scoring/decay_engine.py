from datetime import datetime
import math
try:
    from mandisense_ai.core.agents.external_factors_agent.config.settings import CURRENT_DATE, DECAY_LAMBDA, MAX_EVENT_AGE_DAYS
except ImportError:
    from config.settings import CURRENT_DATE, DECAY_LAMBDA, MAX_EVENT_AGE_DAYS

def apply_decay(events):
    adjusted_events = []
    current = datetime.strptime(CURRENT_DATE, "%Y-%m-%d")
    
    for ev in events:
        event_date = datetime.strptime(ev["event_date"], "%Y-%m-%d")
        days = (current - event_date).days
        
        # Rules: negative -> skip, > 30 days -> skip
        if days < 0 or days > MAX_EVENT_AGE_DAYS:
            continue
            
        impact = ev.get("impact", 0.0)
        # adjusted = impact x exp(-0.1 x days)
        ev["adjusted_score"] = impact * math.exp(-DECAY_LAMBDA * days)
        adjusted_events.append(ev)
        
    return adjusted_events
