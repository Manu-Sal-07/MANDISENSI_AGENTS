import pandas as pd
import numpy as np
from datetime import datetime

class InstitutionalFeatureEngineer:
    """
    Advanced Feature Engineering for Structural Market Dynamics.
    Captures market behavior, not just price movement.
    """
    
    @staticmethod
    def engineer(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # 1. Seasonality & Festival Proximity
        df['month'] = df['date'].dt.month
        df['is_festival_season'] = df['month'].isin([10, 11]).astype(int) # Diwali/Dussehra
        
        # 2. Arrival Momentum & Pressure
        df['arrival_lag_1'] = df['arrivals'].shift(1)
        df['arrival_accel'] = (df['arrivals'] - df['arrival_lag_1']) / (df['arrival_lag_1'] + 1e-6)
        
        # 3. Volatility Regime Features
        df['price_std_7d'] = df['price'].rolling(7).std()
        df['volatility_spike'] = (df['price_std_7d'] > df['price_std_7d'].rolling(30).mean() * 1.5).astype(int)
        
        # 4. Inventory/Supply Pressure (Heuristic)
        # Low arrivals + high price = Supply Compression
        df['supply_compression'] = ((df['arrivals'] < df['arrivals'].rolling(30).mean() * 0.8) & 
                                   (df['price'] > df['price'].rolling(30).mean() * 1.1)).astype(int)
        
        # 5. External Shock Proxy (e.g., Rainfall)
        # We can mock this if real rainfall data isn't joined yet
        df['shock_proxy'] = (df['arrival_accel'] < -0.5).astype(int)
        
        return df.dropna()

if __name__ == "__main__":
    # Test on a small sample
    data = {
        "date": pd.date_range("2024-01-01", periods=10),
        "price": [100, 102, 105, 110, 108, 107, 115, 120, 118, 116],
        "arrivals": [50, 48, 45, 40, 42, 45, 30, 25, 28, 30]
    }
    df = pd.DataFrame(data)
    fe = InstitutionalFeatureEngineer()
    df_engineered = fe.engineer(df)
    print(df_engineered.head())
