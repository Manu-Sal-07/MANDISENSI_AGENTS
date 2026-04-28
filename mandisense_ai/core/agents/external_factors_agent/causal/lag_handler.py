from datetime import datetime, timedelta
import math

def apply_lag(event):
    event_type = event.get("event_type", "")
    date_str = event.get("event_date")
    
    # Defaults
    lag_days = 1
    
    if event_type == "EXPORT_BAN":
        lag_days = 1
    elif event_type == "MSP_INCREASE":
        lag_days = 2
    elif event_type == "DROUGHT":
        lag_days = 3
    elif event_type in ("CROP_DAMAGE", "HEAVY_RAIN"):
        lag_days = 2
        
    if not date_str:
        return None
        
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        effective_dt = dt + timedelta(days=lag_days)
        return effective_dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str
