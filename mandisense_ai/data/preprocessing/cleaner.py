import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

class DataCleaner:
    """
    Cleans structural dataframe arrays mapping missing records,
    resolving duplicates inherently found in Agmarknet dumps.
    """
    def clean(self, df: pd.DataFrame, commodity: str, market: str) -> pd.DataFrame:
        if df.empty:
            return df
            
        logger.info(f"Executing deep cleaning mechanics for {commodity} across {market}")
        
        # 1. Scope explicitly
        pair_df = df[(df['commodity'] == commodity) & (df['market'] == market)].copy()
        if pair_df.empty:
            return pair_df

        # 2. Duplicate collapsing
        # Resolves conflicting single-day entries (e.g., duplicate CSV extracts resolving to True means)
        pair_df = pair_df.groupby('date', as_index=False).agg({
            'arrivals_tonnes': 'sum',
            'modal_price': 'mean',
            'min_price': 'mean',
            'max_price': 'mean',
            'commodity': 'first',
            'market': 'first'
        })
        
        # 3. Create full daily index
        min_date, max_date = pair_df['date'].min(), pair_df['date'].max()
        full_idx = pd.date_range(start=min_date, end=max_date, freq='D')
        
        pair_df.set_index('date', inplace=True)
        pair_df = pair_df.reindex(full_idx)
        pair_df.index.name = 'date'
        pair_df.reset_index(inplace=True)
        
        # Track trading viability metadata
        pair_df['is_trading_day'] = pair_df['modal_price'].notna()
        
        # 4. Re-Imputation Physics
        pair_df['arrivals_tonnes'] = pair_df['arrivals_tonnes'].fillna(0.0)
        
        pair_df['modal_price'] = pair_df['modal_price'].ffill()
        pair_df['min_price'] = pair_df['min_price'].ffill()
        pair_df['max_price'] = pair_df['max_price'].ffill()
        
        pair_df['modal_price'] = pair_df['modal_price'].bfill()
        pair_df['min_price'] = pair_df['min_price'].bfill()
        pair_df['max_price'] = pair_df['max_price'].bfill()

        # Reassert categorical logic overriding NaNs from reindex
        pair_df['commodity'] = commodity
        pair_df['market'] = market
        
        # 5. Volatility Shock Identification
        # Flag structural outliers (+50% movement)
        pct_change = pair_df['modal_price'].pct_change().abs()
        pair_df['price_spike_flag'] = (pct_change > 0.5)

        return pair_df
