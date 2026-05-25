try:
    from mandisense_ai.core.agents.external_factors_agent.config.settings import COMMODITIES
except ImportError:
    from config.settings import COMMODITIES

def aggregate(events, ml_scores=None):
    if ml_scores is None:
        ml_scores = {}
        
    scores = {c: 0.0 for c in COMMODITIES}
    counts = {c: 0 for c in COMMODITIES}
    
    for ev in events:
        c = ev["commodity"]
        if c in scores:
            scores[c] += ev.get("adjusted_score", 0.0)
            counts[c] += 1
            
    results = {}
    for c in COMMODITIES:
        rule_score = scores[c]
        ml_score = ml_scores.get(c, None)
        
        # FUSION LAYER
        if ml_score is None:
            final_score = rule_score
        else:
            final_score = 0.6 * rule_score + 0.4 * ml_score
            
        # CLAMP
        final_score = round(max(-1.0, min(1.0, final_score)), 2)
        
        cl = "HIGH" if counts[c] >= 2 else "MEDIUM" if counts[c] == 1 else "LOW"
        results[c] = {
            "score": final_score,
            "rule_score": round(max(-1.0, min(1.0, rule_score)), 2),
            "ml_score": ml_score if ml_score is None else float(ml_score),
            "event_count": counts[c],
            "confidence_level": cl
        }
        
    return results
