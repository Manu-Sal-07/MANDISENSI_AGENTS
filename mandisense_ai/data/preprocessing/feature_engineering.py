"""
STAGE 5: BASE FEATURE ENGINEERING

Creates the foundation feature set shared by all agents.
All features are strictly leak-proof (no future information used).

Base features include:
- Temporal components (day_of_week, month, quarter, day_of_year, is_month_start/end)
- Lag features for price and arrivals
- Rolling statistics (mean, std, min, max)
- Returns and momentum
- Price-derived features (range, median)
- Rolling correlations between price and arrivals

All rolling/lag operations respect temporal ordering.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class BaseFeatureEngineer:
    """
    Generates base time-series features from cleaned price and arrival data.

    Critical constraint: All features must be computable using only information
    available at time t or earlier. No peeking into the future.
    """

    def __init__(self, config=config):
        self.config = config
        self.price_lags = config.PRICE_LAGS
        self.arrivals_lags = config.ARRIVALS_LAGS
        self.rolling_windows = config.ROLLING_WINDOWS
        self.min_periods_ratio = config.MIN_PERIODS_RATIO

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add calendar-based temporal features.
        These are deterministic and leak-proof by definition.
        """
        date_series = df['date']

        df['day_of_week'] = date_series.dt.dayofweek  # 0=Monday
        df['month'] = date_series.dt.month
        df['quarter'] = date_series.dt.quarter
        df['day_of_year'] = date_series.dt.dayofyear
        df['week_of_year'] = date_series.dt.isocalendar().week.astype('int16')

        df['is_month_start'] = date_series.dt.is_month_start.astype('int8')
        df['is_month_end'] = date_series.dt.is_month_end.astype('int8')

        logger.debug("Temporal features added")
        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add lagged values of price and arrivals.
        Lags are purely historical shifts - no leakage.
        """
        # Price lags
        for lag in self.price_lags:
            df[f'price_lag_{lag}'] = df['modal_price'].shift(lag)

        # Arrivals lags
        for lag in self.arrivals_lags:
            df[f'arrivals_lag_{lag}'] = df['arrivals_tonnes'].shift(lag)

        logger.debug(f"Lag features added: price lags {self.price_lags}, arrivals lags {self.arrivals_lags}")
        return df

    def _add_rolling_statistics(
        self,
        df: pd.DataFrame,
        column: str,
        prefix: str,
        windows: List[int]
    ) -> pd.DataFrame:
        """
        Generic rolling statistics generator.
        Applies rolling mean, std, min, max for given windows.
        Uses min_periods to ensure sufficient data before computing.
        """
        for window in windows:
            min_periods = max(1, int(window * self.min_periods_ratio))

            # Rolling mean
            df[f'{prefix}_mean_{window}'] = (
                df[column].rolling(window=window, min_periods=min_periods).mean()
            )

            # Rolling std
            df[f'{prefix}_std_{window}'] = (
                df[column].rolling(window=window, min_periods=min_periods).std()
            )

            # Rolling min/max (only for smaller windows to save memory)
            if window <= 30:
                df[f'{prefix}_min_{window}'] = (
                    df[column].rolling(window=window, min_periods=min_periods).min()
                )
                df[f'{prefix}_max_{window}'] = (
                    df[column].rolling(window=window, min_periods=min_periods).max()
                )

        return df

    def _add_daily_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add daily return features (percentage and log returns).
        """
        # Simple daily return
        df['daily_returns'] = df['modal_price'].pct_change()

        # Log return (more stable for statistical properties)
        df['log_returns'] = np.log(df['modal_price'] / df['modal_price'].shift(1))

        # Multi-day returns (forward-looking would be leakage, so we use past returns)
        for days in [3, 7, 14]:
            df[f'returns_{days}d'] = (
                df['modal_price'] / df['modal_price'].shift(days) - 1
            )

        logger.debug("Return features added")
        return df

    def _add_price_range_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add features based on price range and relative position.
        """
        # Daily price range (already have min/max from raw, but add normalized)
        if 'min_price' in df.columns and 'max_price' in df.columns:
            df['price_range'] = df['max_price'] - df['min_price']
            df['price_range_pct'] = df['price_range'] / df['modal_price'].replace(0, 0.001)

        # Price position within recent range
        if 'price_min_30' in df.columns and 'price_max_30' in df.columns:
            range_ = df['price_max_30'] - df['price_min_30']
            df['price_position_30'] = (df['modal_price'] - df['price_min_30']) / range_.replace(0, 0.001)

        logger.debug("Price range features added")
        return df

    def _add_rolling_correlations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute rolling correlation between price and arrivals.
        This captures the price-arrival relationship elasticity over time.
        """
        window = 14
        min_periods = max(5, int(window * 0.5))

        # Compute rolling correlation
        df['price_arrival_corr_14'] = (
            df['modal_price'].rolling(window=window, min_periods=min_periods)
            .corr(df['arrivals_tonnes'])
        )

        logger.debug("Rolling correlation added")
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all base feature engineering transformations.

        Args:
            df: Cleaned DataFrame with continuous daily index

        Returns:
            DataFrame with all base features added
        """
        logger.info("=" * 60)
        logger.info("STAGE 5: BASE FEATURE ENGINEERING")
        logger.info("=" * 60)

        if df.empty:
            logger.warning("Empty DataFrame received")
            return df

        initial_cols = df.columns.tolist()
        df = df.sort_values('date').copy()

        # Step 1: Temporal features
        df = self._add_temporal_features(df)

        # Step 2: Lag features
        df = self._add_lag_features(df)

        # Step 3: Rolling statistics for price
        df = self._add_rolling_statistics(df, 'modal_price', 'price', self.rolling_windows)

        # Step 4: Rolling statistics for arrivals
        df = self._add_rolling_statistics(df, 'arrivals_tonnes', 'arrivals', self.rolling_windows[:3])  # Limit to 30d for memory

        # Step 5: Daily returns
        df = self._add_daily_returns(df)

        # Required by the seasonality agent: current 7-day momentum, computed
        # from the already-created historical lag.
        if 'price_lag_7' in df.columns:
            df['momentum_7'] = (
                df['modal_price'] / df['price_lag_7'].replace(0, np.nan) - 1.0
            ).clip(-2, 2)

        # Step 6: Price range features
        df = self._add_price_range_features(df)

        # Step 7: Rolling correlation
        df = self._add_rolling_correlations(df)

        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Log new features
        new_cols = [c for c in df.columns if c not in initial_cols]
        logger.info(f"Base features created: {len(new_cols)} new columns")
        logger.debug(f"New features: {new_cols}")

        return df
