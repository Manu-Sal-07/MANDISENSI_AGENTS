def get_bucket(val):
    if val < -0.5: return "[-1,-0.5]"
    elif val < 0: return "[-0.5,0]"
    elif val <= 0.5: return "[0,0.5]"
    else: return "[0.5,1]"

def calibrate(records):
    buckets = {
        "[-1,-0.5]": {"p": [], "a": []},
        "[-0.5,0]": {"p": [], "a": []},
        "[0,0.5]": {"p": [], "a": []},
        "[0.5,1]": {"p": [], "a": []}
    }
    
    for r in records:
        pred = float(r.get("predicted_score", r.get("final_score", 0)))
        actual = float(r.get("actual_change", 0))
        b = get_bucket(pred)
        buckets[b]["p"].append(pred)
        buckets[b]["a"].append(actual)
        
    factors = {}
    for b, data in buckets.items():
        if len(data["p"]) > 0:
            avg_p = sum(data["p"]) / len(data["p"])
            avg_a = sum(data["a"]) / len(data["a"])
            factor = (avg_a / avg_p) if avg_p != 0 else 1.0
        else:
            factor = 1.0
            
        # Ensure sign parity to prevent flip, then clamp magnitude
        factor = max(0.5, min(1.5, abs(factor)))
        factors[b] = factor
        
    return factors

def apply_calibration(score, factors):
    if not factors:
        return score
    b = get_bucket(score)
    return score * factors.get(b, 1.0)
