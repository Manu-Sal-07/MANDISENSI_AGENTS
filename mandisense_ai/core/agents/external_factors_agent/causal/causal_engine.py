import math
import statistics
from datetime import datetime
try:
    from mandisense_ai.core.agents.external_factors_agent.config.settings import CURRENT_DATE
except ImportError:
    from mandisense_ai.config.settings import CURRENT_DATE
from causal.lag_handler import apply_lag
from causal.baseline_estimator import estimate_expected_price
from causal.window_builder import build_window
from causal.effect_estimator import estimate_effect
from causal.event_isolator import isolate_event

def generate_mock_price_series():
    # Since we don't have a native price DB, we'll emulate a steady price series
    # so baseline estimator and window builder can extract cleanly.
    dt = datetime.strptime(CURRENT_DATE, "%Y-%m-%d")
    series = {}
    base_price = 100.0
    for i in range(-40, 10):
        day = (dt + timedelta(days=i)).strftime("%Y-%m-%d")
        series[day] = base_price + (i % 5) # add minor variance
    return series

from datetime import timedelta

def compute_causal(events_for_commodity):
    # Prepare dates
    for ev in events_for_commodity:
        ev["effective_date"] = apply_lag(ev)
        
    prices = generate_mock_price_series()
    
    valid_effects = []
    
    current_dt = datetime.strptime(CURRENT_DATE, "%Y-%m-%d")
    
    for ev in events_for_commodity:
        if not ev["effective_date"]:
            continue
            
        baseline = estimate_expected_price(ev["effective_date"], prices)
        if baseline is None:
            continue
            
        window = build_window(ev["effective_date"], ev.get("event_type", ""), prices)
        if window is None:
            continue
            
        effect = estimate_effect(window, baseline)
        if effect is None:
            continue
            
        isolation_weight = isolate_event(ev, events_for_commodity)
        
        # Confidence calculation
        abs_eff = abs(effect)
        if abs_eff > 0.2:
            conf = 0.8
        elif abs_eff > 0.1:
            conf = 0.6
        else:
            conf = 0.4
            
        # Additional Filter: if window size < threshold -> reduce confidence by 0.2
        # Threshold: let's expect requested sizes in window
        actual_size = len(window["pre_prices"]) + len(window["post_prices"])
        expected_size = window["pre_expected"] + window["post_expected"]
        if actual_size < expected_size:
            conf -= 0.2
        conf = max(0.0, conf)
        
        # Recency decay
        ev_dt = datetime.strptime(ev["event_date"], "%Y-%m-%d")
        days = (current_dt - ev_dt).days
        recency = math.exp(-0.1 * max(0, days))
        
        weight = conf * recency
        weighted_effect = effect * isolation_weight # Adjust effect using attenuation
        
        valid_effects.append({
            "effect": weighted_effect,
            "weight": weight,
            "confidence": conf
        })
        
    # SAFETY GUARDS
    # 1. If <2 valid events -> skip causal
    if len(valid_effects) < 2:
        return None, None
        
    # Calculate causal score = weighted average
    total_weight = sum(v["weight"] for v in valid_effects)
    if total_weight == 0:
        return None, None
        
    causal_score = sum(v["effect"] * v["weight"] for v in valid_effects) / total_weight
    
    # 2. If variance too high -> skip
    effects_list = [v["effect"] for v in valid_effects]
    if len(effects_list) >= 2:
        variance = statistics.variance(effects_list)
        if variance > 0.5: # arbitrary high threshold
            return None, None
            
    # 3. If causal_score unstable -> fallback
    if math.isnan(causal_score):
        return None, None
        
    avg_conf = sum(v["confidence"] for v in valid_effects) / len(valid_effects)
    
    return causal_score, avg_conf
