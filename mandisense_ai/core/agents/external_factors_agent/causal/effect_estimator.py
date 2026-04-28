import statistics
import math

def estimate_effect(window, baseline):
    if not window or baseline is None:
        return None
        
    # baseline == 0 -> skip
    if baseline == 0:
        return None
        
    try:
        post_prices = window["post_prices"]
        post_avg = statistics.mean(post_prices)
        
        effect = (post_avg - baseline) / baseline
        
        # NaN -> skip
        if math.isnan(effect):
            return None
            
        # Clamp effect = max(-1, min(1, effect))
        effect = max(-1.0, min(1.0, effect))
        return effect
    except Exception:
        return None
