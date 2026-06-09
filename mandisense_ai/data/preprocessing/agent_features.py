"""
STAGE 6: AGENT-SPECIFIC FEATURE ENGINEERING

Creates specialized features for each forecasting agent.

Features are organized by agent type:
- Seasonality Agent: long-term cyclical trends (30-day horizon)
- Arrival Volume Agent: short-term supply shocks (7-day horizon)

All features are leak-proof and computed using only historical data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import timedelta
from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class AgentFeatureGenerator:
    """
    Generates agent-specific features from base feature matrix.

    Design principle: All features must be deterministic functions of
    historical data only (no future leakage).
    """

    def __init__(self, config=config):
        self.config = config

    def _add_seasonality_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Features for Seasonality Agent (30-day horizon).

        Key indicators:
        - Trend strength (30-day moving average slope)
        - Seasonal strength (cyclic pattern consistency)
        - Multi-scale momentum (7d, 14d, 30d)
        - Volatility regime (30-day rolling std of returns)
        - Price position within cycle (0-1 normalized)
        """
        logger.info("Generating Seasonality Agent features...")

        # Ensure required rolling stats exist (add if missing)
        if 'price_mean_30' not in df.columns:
            df['price_mean_30'] = df['modal_price'].rolling(window=30, min_periods=15).mean()
        if 'price_std_30' not in df.columns:
            df['price_std_30'] = df['modal_price'].rolling(window=30, min_periods=15).std()

        # 1. Trend proxy: slope of 30-day MA (approximated by position)
        # Positive if current price > 30-day MA
        df['trend_30'] = (df['modal_price'] - df['price_mean_30']) / df['price_mean_30'].replace(0, 0.001)
        df['trend_30'] = df['trend_30'].clip(-5, 5)  # Prevent extreme values

        # 2. Seasonal strength: inverse of coefficient of variation
        # Lower relative volatility suggests stronger seasonal pattern
        df['seasonal_strength'] = 1.0 - (
            df['price_std_30'] / df['price_mean_30'].replace(0, 0.001)
        )
        df['seasonal_strength'] = df['seasonal_strength'].clip(0, 1)

        # 3. Multi-scale momentum (already have momentum_7, add others if missing)
        for window in [14, 30]:
            lag = min(window, 30)
            if f'momentum_{window}' not in df.columns:
                df[f'momentum_{window}'] = (
                    df['modal_price'] / df[f'price_lag_{lag}'].replace(0, 0.001) - 1.0
                )
            # Cap extreme momentum values
            df[f'momentum_{window}'] = df[f'momentum_{window}'].clip(-2, 2)

        # 4. Rolling volatility (annualized proxy)
        if 'log_returns' not in df.columns:
            df['log_returns'] = np.log(df['modal_price'] / df['modal_price'].shift(1))
        df['rolling_volatility_30'] = df['log_returns'].rolling(window=30, min_periods=15).std() * np.sqrt(252)
        df['rolling_volatility_30'] = df['rolling_volatility_30'].fillna(0)

        # 5. Price position within recent cycle
        if 'price_min_30' not in df.columns:
            df['price_min_30'] = df['modal_price'].rolling(window=30, min_periods=15).min()
        if 'price_max_30' not in df.columns:
            df['price_max_30'] = df['modal_price'].rolling(window=30, min_periods=15).max()

        range_ = df['price_max_30'] - df['price_min_30']
        df['price_position_30'] = (df['modal_price'] - df['price_min_30']) / range_.replace(0, 0.001)
        df['price_position_30'] = df['price_position_30'].clip(0, 1)

        # 6. Cyclical peak/trough detection
        # Simple heuristic: highest/lowest in rolling 30-day window
        df['is_cycle_peak'] = (df['modal_price'] == df['price_max_30']).astype('int8')
        df['is_cycle_trough'] = (df['modal_price'] == df['price_min_30']).astype('int8')

        logger.info(f"Added {len([c for c in df.columns if c not in self._base_cols])} seasonality features")

        return df

    def _add_arrival_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Features for Arrival Volume Agent (7-day horizon).

        Key indicators:
        - Arrival deviation from seasonal norm (%)
        - Year-over-year arrival change (by day-of-year alignment)
        - Supply momentum (week-over-week arrival change)
        - Rolling price-arrival elasticity
        - Supply stress score (composite)
        """
        logger.info("Generating Arrival Volume Agent features...")

        # 1. Arrival deviation from recent average (%)
        window = self.config.ARRIVAL_DEVIATION_WINDOW
        if f'arrivals_mean_{window}' not in df.columns:
            df[f'arrivals_mean_{window}'] = df['arrivals_tonnes'].rolling(window=window, min_periods=int(window*0.5)).mean()

        df['arrival_deviation_pct'] = (
            (df['arrivals_tonnes'] - df[f'arrivals_mean_{window}']) /
            df[f'arrivals_mean_{window}'].replace(0, 0.001)
        )
        df['arrival_deviation_pct'] = df['arrival_deviation_pct'].clip(-5, 5)

        # 2. Year-over-year (YoY) deviation
        # Align current date with same date last year (± tolerance)
        df['date_minus_1y'] = df['date'] - pd.DateOffset(years=1)
        # Create temporary merge key for YoY
        df_temp = df[['date', 'arrivals_tonnes']].copy()
        df_temp.rename(columns={'arrivals_tonnes': 'arrivals_ly'}, inplace=True)
        df_temp.rename(columns={'date': 'date_ly'}, inplace=True)

        df = df.merge(
            df_temp,
            left_on='date_minus_1y',
            right_on='date_ly',
            how='left',
            suffixes=('', '_drop')
        )

        # Calculate YoY deviation
        df['arrivals_yoy_deviation'] = (
            (df['arrivals_tonnes'] - df['arrivals_ly']) /
            df['arrivals_ly'].replace(0, 0.001)
        )
        df['arrivals_yoy_deviation'] = df['arrivals_yoy_deviation'].clip(-5, 5)

        # Clean up temporary columns
        df = df.drop(columns=['date_minus_1y', 'date_ly', 'arrivals_ly'], errors='ignore')

        # 3. Supply momentum: week-over-week arrival change
        df['supply_momentum'] = (
            df['arrivals_tonnes'] / df['arrivals_lag_7'].replace(0, 0.001) - 1.0
        )
        df['supply_momentum'] = df['supply_momentum'].clip(-3, 3)

        # 4. Rolling elasticity (slope of price vs arrival relationship)
        # Use rolling window regression (simplified as correlation * vol ratio)
        window = self.config.ELASTICITY_WINDOW
        min_periods = max(5, int(window * 0.5))

        # Rolling correlation already computed in base features
        if 'price_arrival_corr_14' not in df.columns:
            df['price_arrival_corr_14'] = (
                df['modal_price'].rolling(window=14, min_periods=7).corr(df['arrivals_tonnes'])
            )

        # Elasticity proxy: corr * (std_price / std_arrivals)
        price_std = df['modal_price'].rolling(window=window, min_periods=min_periods).std()
        arrival_std = df['arrivals_tonnes'].rolling(window=window, min_periods=min_periods).std()
        df['rolling_elasticity'] = (
            df['price_arrival_corr_14'] * (price_std / arrival_std.replace(0, 0.001))
        )
        df['rolling_elasticity'] = df['rolling_elasticity'].fillna(0).clip(-10, 10)

        # 5. Supply stress score (composite indicator)
        # Combines deviation magnitude, spike detection, and trend
        df['supply_stress_raw'] = (
            np.abs(df['arrival_deviation_pct']) +
            df['arrival_spike_flag'].astype('float') * 2.0 +
            np.abs(df['supply_momentum'])
        ) / 3.0
        df['supply_stress_score'] = df['supply_stress_raw'].rolling(window=7, min_periods=3).mean()
        df['supply_stress_score'] = df['supply_stress_score'].fillna(0).clip(0, 5)

        # 6. Supply regime classification (categorical)
        # Based on deviation and momentum quadrants
        conditions = [
            (df['arrival_deviation_pct'] < -0.5) & (df['supply_momentum'] < -0.2),
            (df['arrival_deviation_pct'] > 0.5) & (df['supply_momentum'] > 0.2),
            (df['arrival_deviation_pct'] < -0.5),
            (df['arrival_deviation_pct'] > 0.5),
        ]
        choices = ['squeeze_accelerating', 'glut_accelerating', 'squeeze', 'glut']
        df['supply_regime'] = np.select(conditions, choices, default='normal')
        regime_map = {
            'squeeze_accelerating': 0,
            'squeeze': 1,
            'normal': 2,
            'glut': 3,
            'glut_accelerating': 4,
        }
        df['supply_regime_code'] = df['supply_regime'].map(regime_map).astype('int8')

        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        logger.info(f"Added arrival agent features. Current columns: {len(df.columns)}")

        return df

    def _add_festival_features(self, df: pd.DataFrame, festival_calendar_path: Optional[str] = None) -> pd.DataFrame:
        """
        Optional: Enrich with festival/seasonal calendar features.
        Not strictly required but helpful for seasonality agent.

        Args:
            df: DataFrame with date column
            festival_calendar_path: Path to festival CSV (optional)
        """
        # Minimal festival feature: monsoon season, winter season, festival months
        df['is_summer'] = df['month'].isin([3, 4, 5]).astype('int8')
        df['is_monsoon'] = df['month'].isin([6, 7, 8, 9]).astype('int8')
        df['is_winter'] = df['month'].isin([10, 11, 12, 1, 2]).astype('int8')

        # Festival season proxy (major Indian festivals typically in Oct-Nov)
        df['festival_week_proximity'] = 0
        # Diwali typically in Oct-Nov, mark +/- 15 days
        df.loc[((df['month'] == 10) & (df['date'].dt.day >= 15)) |
               ((df['month'] == 11) & (df['date'].dt.day <= 15)), 'festival_week_proximity'] = 1

        logger.debug("Festival/seasonal features added")
        return df

    def transform(self, df: pd.DataFrame, add_festival: bool = False) -> pd.DataFrame:
        """
        Apply all agent-specific feature transformations.

        Args:
            df: DataFrame with base features already computed
            add_festival: Whether to add festival calendar features

        Returns:
            DataFrame with all agent-specific features
        """
        logger.info("=" * 60)
        logger.info("STAGE 6: AGENT-SPECIFIC FEATURE ENGINEERING")
        logger.info("=" * 60)

        if df.empty:
            return df

        # Store initial columns for logging
        self._base_cols = df.columns.tolist()
        df = df.sort_values('date').copy()

        # Seasonality Agent Features
        df = self._add_seasonality_features(df)

        # Arrival Agent Features
        df = self._add_arrival_features(df)

        # Optional: Festival features
        if add_festival:
            df = self._add_festival_features(df)

        # Log new features
        new_cols = [c for c in df.columns if c not in self._base_cols]
        logger.info(f"Agent-specific features created: {len(new_cols)} new columns")
        logger.debug(f"New columns: {new_cols}")

        return df
