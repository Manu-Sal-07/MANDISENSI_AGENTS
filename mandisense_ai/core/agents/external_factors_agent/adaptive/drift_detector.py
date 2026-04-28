def detect_drift(recent_records, historical_records):
    if len(recent_records) < 10 or len(historical_records) < 20:
        return False
        
    recent_mae = sum(abs(float(r["error"])) for r in recent_records) / len(recent_records)
    hist_mae = sum(abs(float(r["error"])) for r in historical_records) / len(historical_records)
    
    if hist_mae > 0 and recent_mae > 1.5 * hist_mae:
        return True
    return False
