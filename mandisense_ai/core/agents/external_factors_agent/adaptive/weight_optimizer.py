import json
import os

STATE_FILE = "data/adaptive/opt_state.json"

def get_current_weights():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("weights", {"rule": 0.33, "ml": 0.33, "causal": 0.34})
        except:
            pass
    return {"rule": 0.33, "ml": 0.33, "causal": 0.34}

def optimize_weights(records):
    # Minimum samples required = 20
    if len(records) < 20:
        return get_current_weights()
        
    records = records[-100:] 
    best_mae = float('inf')
    best_w = None
    
    steps = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    for w1 in steps:
        for w2 in steps:
            w3 = round(1.0 - w1 - w2, 2)
            if 0.1 <= w3 <= 0.7:
                total_err = 0
                for r in records:
                    r_sc = float(r.get("rule_score", 0))
                    m_sc = float(r.get("ml_score", 0) or 0.0)
                    c_sc = float(r.get("causal_score", 0) or 0.0)
                    actual = float(r.get("actual_change", 0))
                    
                    pred = w1*r_sc + w2*m_sc + w3*c_sc
                    total_err += abs(pred - actual)
                    
                mae = total_err / len(records)
                if mae < best_mae:
                    best_mae = mae
                    best_w = {"rule": w1, "ml": w2, "causal": w3}
                    
    old_w = get_current_weights()
    if not best_w:
        return old_w
        
    # No update if variance too high / model unstable implies skipping
    # We enforce smooth updating rules
    new_w = {
        "rule": round(0.8 * old_w["rule"] + 0.2 * best_w["rule"], 3),
        "ml": round(0.8 * old_w["ml"] + 0.2 * best_w["ml"], 3),
        "causal": round(0.8 * old_w["causal"] + 0.2 * best_w["causal"], 3)
    }
    
    # Normalize securely to exactly 1.0
    s = sum(new_w.values())
    new_w = {k: v/s for k, v in new_w.items()}
    return new_w
    
def save_weights(weights):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        except:
            pass
    state["weights"] = weights
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
