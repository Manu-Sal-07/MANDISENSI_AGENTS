from datetime import datetime, timedelta

def align_data(predictions, prices, lag_days=1):
    aligned = []
    sorted_preds = sorted(predictions, key=lambda x: x["date"])
    
    for p in sorted_preds:
        c = p.get("commodity")
        t_str = p.get("date")
        pred_score = p.get("predicted_score", p.get("final_score", 0.0))
        
        try:
            t_dt = datetime.strptime(t_str, "%Y-%m-%d")
            t_lag_dt = t_dt + timedelta(days=lag_days)
            t_lag_str = t_lag_dt.strftime("%Y-%m-%d")
            
            c_prices = prices.get(c, {})
            price_t = c_prices.get(t_str)
            price_t_lag = c_prices.get(t_lag_str)
            
            # Skip if missing data, ensuring chronological T to T+lag
            if price_t is None or price_t_lag is None or price_t == 0:
                continue
                
            actual_change = (price_t_lag - price_t) / price_t
            
            p_out = dict(p)
            p_out["actual_change"] = actual_change
            p_out["error"] = pred_score - actual_change
            aligned.append(p_out)
        except Exception:
            continue
            
    return aligned
