from adaptive.weight_optimizer import get_current_weights
from adaptive.confidence_calibrator import apply_calibration

def adaptive_predict(rule_score, ml_score, causal_score, calibration_factors, weights=None):
    if weights is None:
        weights = get_current_weights()
        
    w1 = weights.get("rule", 0.33)
    w2 = weights.get("ml", 0.33)
    w3 = weights.get("causal", 0.34)
    
    if causal_score is None:
        # Protect against failures organically
        base_score = 0.6 * rule_score + 0.4 * (ml_score or 0)
    else:
        base_score = w1 * rule_score + w2 * (ml_score or 0.0) + w3 * causal_score
        
    final_score = base_score
    if calibration_factors:
        final_score = apply_calibration(base_score, calibration_factors)
        
    return round(max(-1.0, min(1.0, final_score)), 2)
