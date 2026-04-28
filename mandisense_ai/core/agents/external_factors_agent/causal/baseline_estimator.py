import statistics

def estimate_expected_price(date_str, price_series):
    """
    price_series: dict of { "YYYY-MM-DD": float }
    date_str: "YYYY-MM-DD"
    """
    from datetime import datetime, timedelta
    
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        past_prices = []
        for i in range(1, 4):
            day_dt = dt - timedelta(days=i)
            day_str = day_dt.strftime("%Y-%m-%d")
            if day_str in price_series:
                past_prices.append(price_series[day_str])
                
        # If <3 past values -> skip event
        if len(past_prices) < 3:
            return None
            
        # If missing -> skip
        if any(p is None for p in past_prices):
            return None
            
        return statistics.mean(past_prices)
    except Exception:
        return None
