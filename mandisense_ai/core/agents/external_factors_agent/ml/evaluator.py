def evaluate(real_prices, model_preds, rule_preds):
    """
    Evaluator module
    Calculates MAE between combinations
    """
    try:
        import numpy as np
        
        keys = set(real_prices.keys()).intersection(model_preds.keys())
        if not keys:
            return {}
            
        real = np.array([real_prices[k] for k in keys])
        model_p = np.array([model_preds[k] for k in keys])
        rule_p = np.array([rule_preds[k] for k in keys])
        
        mae_ml = np.mean(np.abs(real - model_p))
        mae_rule = np.mean(np.abs(real - rule_p))
        
        return {
            "mae_ml": mae_ml,
            "mae_rule": mae_rule
        }
    except Exception:
        pass
    return {}
