def adjust(rule_score, ml_score, causal_score, causal_confidence):
    # Base fallback base_score
    base_score = 0.6 * rule_score + 0.4 * ml_score
    
    if causal_score is None or causal_confidence is None:
        return round(max(-1.0, min(1.0, base_score)), 2)
        
    final_score = base_score * (1 - causal_confidence) + causal_score * causal_confidence
    
    return round(max(-1.0, min(1.0, final_score)), 2)
