import json
import sys
sys.path.append('.')
from mandisense_ai.ensemble.meta_ensemble import SeasonalityInput, ArrivalInput, ExternalInput, fuse

f = open('data/ensemble/meta_predictions.jsonl', 'r')
records = [json.loads(line) for line in f]
f.close()

regimes = {
    "Stable": [],
    "Volatile": [],
    "Supply Shock": [],
    "Festival Demand Spike": []
}

for rec in records:
    # 1. Inputs
    s_in = SeasonalityInput(
        prediction_30d=rec["seasonality_pred_30d"],
        confidence=rec["seasonality_confidence"],
        volatility=rec["seasonality_volatility"],
        regime=rec["seasonality_regime"]
    )
    a_in = ArrivalInput(
        prediction_7d=rec["arrival_pred_7d"],
        confidence=rec["arrival_confidence"],
        supply_stress=rec["arrival_supply_stress"],
        regime=rec["arrival_regime"]
    )
    e_in = ExternalInput(
        impact_score=rec["external_impact"],
        confidence=rec["external_confidence"]
    )
    
    # 2. Fuse
    output = fuse(s_in, a_in, e_in)
    w_s = output.debug["w_s_final"]
    w_a = output.debug["w_a_final"]
    ext_bias = output.debug["external_bias"]
    
    # 3. Classify regime based on input features
    if rec["arrival_regime"] == "Oversupply" or rec["arrival_supply_stress"] > 0.5:
        regime = "Supply Shock"
    elif rec["external_confidence"] > 0.4 or rec["external_impact"] > 0.2:
        regime = "Festival Demand Spike"
    elif rec["seasonality_volatility"] > 0.15 or (rec["seasonality_confidence"] > 0.3 and rec["seasonality_volatility"] > 0.05):
        regime = "Volatile"
    else:
        regime = "Stable"
        
    regimes[regime].append({
        "w_s": w_s,
        "w_a": w_a,
        "ext_bias": ext_bias,
        "attr": output.attribution,
        "rec": rec
    })

for name, items in regimes.items():
    print(f"Regime: {name}, count: {len(items)}")
    if items:
        # print sample
        sample = items[0]
        print(f"  Sample weights: w_s={sample['w_s']:.3f}, w_a={sample['w_a']:.3f}, ext_bias={sample['ext_bias']:.3f}")
        print(f"  Sample attribution: {sample['attr']}")
