from datetime import datetime, timedelta

def get_window_rules(event_type):
    if event_type == "EXPORT_BAN":
        return 3, 5
    elif event_type == "MSP_INCREASE":
        return 3, 7
    elif event_type == "DROUGHT":
        return 5, 7
    elif event_type in ("CROP_DAMAGE", "HEAVY_RAIN"):
        return 3, 5
    return 3, 3

def build_window(event_date, event_type, price_series):
    pre_days, post_days = get_window_rules(event_type)
    pre_prices = []
    post_prices = []
    
    try:
        dt = datetime.strptime(event_date, "%Y-%m-%d")
        
        for i in range(1, pre_days + 1):
            day_str = (dt - timedelta(days=i)).strftime("%Y-%m-%d")
            if day_str in price_series:
                pre_prices.append(price_series[day_str])
                
        for i in range(0, post_days + 1):
            day_str = (dt + timedelta(days=i)).strftime("%Y-%m-%d")
            if day_str in price_series:
                post_prices.append(price_series[day_str])
                
        # Rules: missing values -> drop event. Min 2 values per window.
        if len(pre_prices) < 2 or len(post_prices) < 2:
            return None
        return {
            "pre_prices": pre_prices,
            "post_prices": post_prices,
            "pre_expected": pre_days,
            "post_expected": post_days + 1
        }
    except Exception:
        return None
