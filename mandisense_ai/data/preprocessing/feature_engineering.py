import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

class FeatureEngineer:
    """
    Transforms clean, time-series uniform datasets into robust statistical features 
    required heavily by arrival volumes and seasonality predictors.
    """
    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        df = df.sort_values('date').copy()
        
        logger.info("Injecting Temporal Metadata")
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
        
        # Placeholder heuristic handling missing festival JSON mapping logic initially 
        df['is_festival_season'] = df['month'].isin([10, 11]).astype(int)
        
        logger.info("Computing Time-Lags")
        for lag in [1, 3, 7, 14]:
            df[f'price_lag_{lag}'] = df['modal_price'].shift(lag)
            
        logger.info("Simulating Exponential Rolling Statistics")
        for window in [7, 14, 28]:
            df[f'price_roll_mean_{window}'] = df['modal_price'].rolling(window=window).mean()
        
        df['price_roll_std_7'] = df['modal_price'].rolling(window=7).std()
        df['volatility_proxy_14'] = df['modal_price'].rolling(window=14).std() / df['price_roll_mean_14']
        
        logger.info("Encoding Momentum Metrics")
        df['momentum_7'] = (df['modal_price'] / df['price_lag_7']) - 1.0
        
        # Evict initial temporal NaN holes correctly to maintain absolute predictive constraints
        df.dropna(subset=['price_lag_14', 'price_roll_mean_28'], inplace=True)
        
        return df
