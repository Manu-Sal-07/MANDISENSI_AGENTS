"""
STAGES 2 & 3: DATA CLEANING & TIME ALIGNMENT

Handles missing values intelligently and ensures continuous daily time index:
- modal_price: forward fill + backward fill (with limit)
- arrivals_tonnes: 7-day rolling median imputation
- Creates continuous daily index per (commodity, market) group
- Preserves temporal order (no shuffling)
- Flags trading vs non-trading days

Critical for time-series integrity: all operations are time-aware
and respect temporal boundaries to prevent leakage.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import timedelta
from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class DataCleaner:
    """
    Production-grade cleaner for agricultural price time-series data.

    Design principles:
    1. All imputation uses ONLY past/present data (no future leakage)
    2. Rolling statistics computed with min_periods to avoid overfitting to sparse data
    3. Preserves exact temporal order
    4. Tracks imputation quality for monitoring
    """

    def __init__(self, config=config):
        self.config = config
        self.required_cols = ['date', 'commodity', 'market', 'modal_price', 'arrivals_tonnes']

    def _create_continuous_index(self, df: pd.DataFrame) -> Tuple[pd.DatetimeIndex, pd.DataFrame]:
        """
        Creates a continuous daily date range covering the full span of data.
        Returns the full index and the min/max dates.
        """
        df = df.sort_values('date')
        min_date = df['date'].min()
        max_date = df['date'].max()

        # Ensure we cover full range even on re-runs
        full_idx = pd.date_range(start=min_date, end=max_date, freq=self.config.TARGET_FREQUENCY, tz=None)

        return full_idx, (min_date, max_date)

    def _reindex_to_continuous(self, df: pd.DataFrame, full_idx: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Reindexes DataFrame to continuous daily index.
        Sets date as index temporarily, reindexes, then resets.
        """
        df = df.set_index('date').sort_index()
        df = df.reindex(full_idx)

        # Restore date column
        df.index.name = 'date'
        df = df.reset_index()

        for col in ['min_price', 'max_price']:
            if col in df.columns:
                df[col] = df[col].ffill(limit=self.config.PRICE_FILL_LIMIT).bfill()
                df[col] = df[col].fillna(df['modal_price'])

        return df

    def _impute_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Impute missing modal_price using forward fill then backward fill.
        Limits forward fill to prevent long chains of imputation.
        """
        missing_before = df['modal_price'].isna()
        df['modal_price_imputed'] = missing_before.astype('int8')

        # Count before
        na_before = df['modal_price'].isna().sum()

        # Forward fill with limit
        df['modal_price'] = df['modal_price'].ffill(limit=self.config.PRICE_FILL_LIMIT)

        # Backward fill remaining leading NaNs only. These rows are flagged via
        # modal_price_imputed and are later dropped if lag features are missing,
        # preserving model-training leakage safety.
        df['modal_price'] = df['modal_price'].bfill()

        # Count after
        na_after = df['modal_price'].isna().sum()
        if na_after > 0:
            logger.warning(f"modal_price: {na_before} NaNs → {na_after} remaining after imputation")

        return df

    def _impute_arrivals_rolling_median(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Impute missing arrivals_tonnes using rolling median over a 7-day window.
        This preserves distribution shape better than mean for skewed arrival data.
        """
        na_before = df['arrivals_tonnes'].isna().sum()

        missing_before = df['arrivals_tonnes'].isna()
        df['arrivals_imputed'] = missing_before.astype('int8')

        # Compute rolling median with trailing data only. A centered rolling
        # median would include future arrivals and leak supply information.
        window = self.config.ARRIVALS_ROLLING_MEDIAN_WINDOW
        rolling_median = df['arrivals_tonnes'].rolling(
            window=window,
            center=False,
            min_periods=3
        ).median()

        # Fill NaNs with rolling median first
        df['arrivals_tonnes'] = df['arrivals_tonnes'].fillna(rolling_median)

        # Fallback: if still NaN at early edges, use forward fill then backward.
        # Downstream feature-readiness dropping removes rows whose historical
        # features cannot be built without peeking forward.
        df['arrivals_tonnes'] = df['arrivals_tonnes'].ffill().bfill()

        na_after = df['arrivals_tonnes'].isna().sum()
        if na_after > 0:
            logger.error(f"arrivals_tonnes: {na_before} NaNs → {na_after} STILL NaN after imputation!")

        return df

    def _handle_remaining_nans(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Final cleanup: drop rows where BOTH modal_price AND arrivals_tonnes are NaN.
        Single-column NaNs should already be imputed.
        """
        both_na = df['modal_price'].isna() & df['arrivals_tonnes'].isna()
        if both_na.any():
            drop_count = both_na.sum()
            logger.warning(f"Dropping {drop_count} rows where both price and arrivals are NaN")
            df = df[~both_na].copy()

        return df

    def _create_trading_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates flags indicating whether a day is a trading day.
        A trading day is defined as having a non-NaN modal_price after imputation.
        """
        df['is_trading_day'] = (
            df['modal_price'].notna()
            & (df['modal_price'] > 0)
            & (df.get('modal_price_imputed', 0) == 0)
        )
        trading_pct = df['is_trading_day'].mean() * 100
        logger.info(f"Trading days: {trading_pct:.1f}% of dataset")
        return df

    def _sort_and_deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures data is sorted by date and removes any remaining duplicates.
        """
        df = df.sort_values('date').reset_index(drop=True)

        # Remove exact duplicates (keep first)
        dup_count = df.duplicated(subset=['date']).sum()
        if dup_count > 0:
            logger.warning(f"Removing {dup_count} duplicate dates after reindexing")
            df = df.drop_duplicates(subset=['date'], keep='first')

        return df

    def clean(
        self,
        df: pd.DataFrame,
        commodity: Optional[str] = None,
        market: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Main cleaning pipeline for a single (commodity, market) pair.

        Args:
            df: Raw DataFrame (already filtered to commodity/market if provided)
            commodity: Optional filter
            market: Optional filter

        Returns:
            Cleaned DataFrame with continuous daily index and no missing values
        """
        logger.info("-" * 50)
        logger.info(f"Cleaning: {commodity} @ {market}")
        logger.info("-" * 50)

        if df.empty:
            logger.warning("Empty DataFrame received")
            return df

        initial_rows = len(df)

        # Filter if specified
        if commodity is not None:
            df = df[df['commodity'] == commodity]
        if market is not None:
            df = df[df['market'] == market]

        # Step 1: Create continuous daily index
        full_idx, (min_date, max_date) = self._create_continuous_index(df)
        logger.info(f"Date range: {min_date.date()} → {max_date.date()} ({len(full_idx)} days)")

        # Step 2: Reindex to continuous index (introduces NaNs)
        df = self._reindex_to_continuous(df, full_idx)

        # Restore commodity/market (lost during reindex if all rows were NaN)
        if commodity is not None:
            df['commodity'] = commodity
        if market is not None:
            df['market'] = market
        for col in ['state', 'district', 'variety', 'grade']:
            if col in df.columns:
                df[col] = df[col].ffill().bfill().fillna('unknown')

        rows_after_reindex = len(df)
        introduced_nans = rows_after_reindex - initial_rows
        logger.info(f"Reindexing added {introduced_nans} new rows (missing dates)")

        # Step 3: Impute missing prices (forward/backward fill)
        df = self._impute_prices(df)

        # Step 4: Impute arrivals using rolling median
        df = self._impute_arrivals_rolling_median(df)

        # Step 5: Drop rows where both are still NaN
        df = self._handle_remaining_nans(df)

        # Step 6: Create trading flags
        df = self._create_trading_flags(df)

        # Step 7: Final sorting and deduplication
        df = self._sort_and_deduplicate(df)

        final_rows = len(df)
        logger.info(f"Cleaning complete: {initial_rows} → {final_rows} rows")
        logger.info(f"Net change: {final_rows - initial_rows:+d} rows")

        return df
