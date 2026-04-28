import math

def calculate_metrics(records):
    if not records:
        return {}
        
    n = len(records)
    errors = [float(r["error"]) for r in records]
    
    mae = sum(abs(e) for e in errors) / n
    rmse = math.sqrt(sum(e*e for e in errors) / n)
    
    directional_matches = 0
    err_rule_sum = 0
    err_ml_sum = 0
    err_causal_sum = 0
    
    for r in records:
        final = float(r.get("final_score", 0))
        actual = float(r.get("actual_change", 0))
        
        if (final > 0 and actual > 0) or (final < 0 and actual < 0) or (final == 0 and actual == 0):
            directional_matches += 1
            
        r_sc = float(r.get("rule_score", 0))
        m_sc = float(r.get("ml_score", 0)) if r.get("ml_score") is not None else 0
        c_sc = float(r.get("causal_score", 0)) if r.get("causal_score") is not None else 0
        
        err_rule_sum += abs(r_sc - actual)
        err_ml_sum += abs(m_sc - actual)
        err_causal_sum += abs(c_sc - actual)
        
    da = (directional_matches / n) * 100
    
    return {
        "MAE": mae,
        "RMSE": rmse,
        "Directional Accuracy": da,
        "error_rule": err_rule_sum / n,
        "error_ml": err_ml_sum / n,
        "error_causal": err_causal_sum / n
    }
