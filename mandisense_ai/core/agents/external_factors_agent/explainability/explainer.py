def explain(events, rule_score, ml_score, causal_score, final_score, weights):
    # Safe float parsing guarantees numerical stability
    r_score = float(rule_score) if rule_score is not None else 0.0
    m_score = float(ml_score) if ml_score is not None else 0.0
    c_score = float(causal_score) if causal_score is not None else 0.0
    f_score = float(final_score) if final_score is not None else 0.0
    
    w1 = weights.get("rule", 0.0)
    w2 = weights.get("ml", 0.0)
    w3 = weights.get("causal", 0.0)
    
    # 1. Contributions calculation matching final_score weights
    contributions = {
        "rule": round(w1 * r_score, 2),
        "ml": round(w2 * m_score, 2),
        "causal": round(w3 * c_score, 2)
    }

    # 2. Extract deterministic reasons linked to events
    reasons = []
    
    # Expose ML history dynamically
    if abs(m_score) > 0.2:
        reasons.append(f"Historical pattern modeling pushes score by {round(m_score, 2)}")
        
    for ev in events:
        impact = float(ev.get("adjusted_score", ev.get("impact", 0.0)))
        event_type = ev.get("event_type", "EVENT")
        eff_date = ev.get("event_date", "recent")
        
        if abs(impact) > 0.05:
            direction = "positive" if impact > 0 else "negative"
            reasons.append(f"{event_type} on {eff_date} has {direction} impact.")
            
    # Protect against duplicate news elements
    reasons = list( dict.fromkeys(reasons) )[:4]
    
    # 3. Dynamic trend validation
    if f_score > 0.3:
        trend = "UP"
    elif f_score < -0.3:
        trend = "DOWN"
    else:
        trend = "NEUTRAL"
        
    # 4. Strict safety alerts
    alert = "NONE"
    if f_score > 0.7:
        alert = "HIGH_PRICE_RISK"
    elif f_score < -0.7:
        alert = "PRICE_CRASH_RISK"
    elif abs(c_score) > 0.5:
        alert = "ANOMALY_DETECTED"
        
    # 5. Pipeline integrity evaluation proxy
    confidence = 0.4
    if ml_score is not None and causal_score is not None:
        confidence = 0.9
    elif ml_score is not None or causal_score is not None:
        confidence = 0.6
        
    return {
        "trend": trend,
        "reasons": reasons,
        "contributions": contributions,
        "alert": alert,
        "confidence": confidence
    }
