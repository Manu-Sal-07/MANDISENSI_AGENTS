"""
STAGE 4: OUTLIER HANDLING

Production-grade outlier handling with two critical safeguards:
1. WINSORIZATION (capping) using expanding historical percentiles - no future data used
2. ANOMALY FLAGS - marks outliers for model attention without removing them

Design philosophy:
- DO NOT blindly remove outliers (could be real market shocks)
- Cap extreme values to prevent model domination
- Create explicit flags so models can learn outlier patterns
- All statistics computed with strictly historical data only (expanding window)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class OutlierHandler:
    """
    Handles outliers in agricultural price and arrival data using
    leak-proof expanding window statistics.

    Key features:
    - Expanding percentiles: uses all historical data up to current point
    - No future leakage: never uses future data to compute bounds
    - Creates binary anomaly flags for model awareness
    - Saves both original and winsorized versions (original for audit trail)
    """

    def __init__(self, config=config):
        self.config = config
        self.price_lower_pct = config.WINSORIZE_LOWER_PCT
        self.price_upper_pct = config.WINSORIZE_UPPER_PCT
        self.arrival_lower_pct = config.WINSORIZE_LOWER_PCT
        self.arrival_upper_pct = config.WINSORIZE_UPPER_PCT

        # Spike detection thresholds
        self.price_spike_threshold = config.PRICE_SPIKE_THRESHOLD
        self.arrival_spike_threshold = config.ARRIVAL_SPIKE_THRESHOLD

        logger.info(
            f"OutlierHandler initialized: winsorize=[{self.price_lower_pct:.2f},{self.price_upper_pct:.2f}], "
            f"price_spike_th={self.price_spike_threshold:.0%}, arrival_spike_th={self.arrival_spike_threshold:.0%}"
        )

    def _compute_expanding_percentiles(
        self,
        series: pd.Series,
        lower_pct: float,
        upper_pct: float,
        min_periods: int = 30
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Compute expanding (growing) window percentiles.
        For each row t, uses data from row 0 to t-1 (strictly historical).

        Args:
            series: Time series data
            lower_pct: Lower percentile (0-1)
            upper_pct: Upper percentile (0-1)
            min_periods: Minimum observations before applying winsorization

        Returns:
            lower_bound, upper_bound series (aligned to input index)
        """
        n = len(series)
        lower_bounds = np.full(n, np.nan, dtype='float32')
        upper_bounds = np.full(n, np.nan, dtype='float32')

        # Use expanding window - strictly historical
        for i in range(min_periods, n):
            historical = series.iloc[:i].dropna()
            if len(historical) >= min_periods:
                lower_bounds[i] = np.percentile(historical, lower_pct * 100)
                upper_bounds[i] = np.percentile(historical, upper_pct * 100)
            else:
                # Not enough history - don't winsorize yet
                lower_bounds[i] = series.iloc[i]
                upper_bounds[i] = series.iloc[i]

        return pd.Series(lower_bounds, index=series.index), pd.Series(upper_bounds, index=series.index)

    def _winsorize_series(
        self,
        series: pd.Series,
        lower_bound: pd.Series,
        upper_bound: pd.Series
    ) -> pd.Series:
        """
        Apply winsorization: cap values outside [lower_bound, upper_bound].
        Values exactly at bounds are left unchanged.
        """
        winsorized = series.copy()
        below_lower = winsorized < lower_bound
        above_upper = winsorized > upper_bound

        winsorized[below_lower] = lower_bound[below_lower]
        winsorized[above_upper] = upper_bound[above_upper]

        return winsorized

    def _detect_spikes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect sudden, extreme movements that may represent market shocks.
        These are flagged but NOT removed - models need to see them.
        """
        # Price spikes: absolute daily change > threshold
        df['price_spike_flag'] = False
        price_pct_change = df['modal_price'].pct_change().abs()
        df.loc[price_pct_change > self.price_spike_threshold, 'price_spike_flag'] = True

        # Arrival spikes: absolute log change > threshold
        df['arrival_spike_flag'] = False
        # Add small epsilon to avoid log(0)
        arrivals_safe = df['arrivals_tonnes'].replace(0, 0.001)
        arrival_log_change = np.log(arrivals_safe / arrivals_safe.shift(1)).abs()
        df.loc[arrival_log_change > self.arrival_spike_threshold, 'arrival_spike_flag'] = True

        n_price_spikes = df['price_spike_flag'].sum()
        n_arrival_spikes = df['arrival_spike_flag'].sum()
        logger.info(f"Spike detection: {n_price_spikes} price spikes, {n_arrival_spikes} arrival spikes")

        return df

    def _compute_anomaly_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create anomaly flags based on winsorization bounds.
        A value is anomalous if it falls outside the [P1, P99] range.
        """
        # Compute expanding percentiles for full series
        logger.info("Computing expanding percentile bounds for anomaly detection...")

        price_lower, price_upper = self._compute_expanding_percentiles(
            df['modal_price'],
            self.price_lower_pct,
            self.price_upper_pct,
            min_periods=60  # Need ~2 months of data before applying
        )

        arrival_lower, arrival_upper = self._compute_expanding_percentiles(
            df['arrivals_tonnes'],
            self.arrival_lower_pct,
            self.arrival_upper_pct,
            min_periods=60
        )

        # Create flags (True if original value is outside bounds)
        df['is_price_outlier'] = (
            (df['modal_price'] < price_lower) |
            (df['modal_price'] > price_upper)
        ) & price_lower.notna()  # Only flag where bounds are valid

        df['is_arrival_outlier'] = (
            (df['arrivals_tonnes'] < arrival_lower) |
            (df['arrivals_tonnes'] > arrival_upper)
        ) & arrival_lower.notna()

        n_price_outliers = df['is_price_outlier'].sum()
        n_arrival_outliers = df['is_arrival_outlier'].sum()
        logger.info(f"Anomaly flags: {n_price_outliers} price outliers, {n_arrival_outliers} arrival outliers")

        return df

    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply winsorization to price and arrivals.
        Creates new columns: modal_price_winsorized, arrivals_tonnes_winsorized
        Original values preserved for audit trail.
        """
        logger.info("Applying winsorization (expanding percentiles)...")

        # Compute expanding bounds
        price_lower, price_upper = self._compute_expanding_percentiles(
            df['modal_price'],
            self.price_lower_pct,
            self.price_upper_pct,
            min_periods=60
        )

        arrival_lower, arrival_upper = self._compute_expanding_percentiles(
            df['arrivals_tonnes'],
            self.arrival_lower_pct,
            self.arrival_upper_pct,
            min_periods=60
        )

        # Apply winsorization
        df['modal_price_original'] = df['modal_price'].copy()
        df['arrivals_tonnes_original'] = df['arrivals_tonnes'].copy()

        df['modal_price'] = self._winsorize_series(df['modal_price'], price_lower, price_upper)
        df['arrivals_tonnes'] = self._winsorize_series(df['arrivals_tonnes'], arrival_lower, arrival_upper)

        # Track how many values were capped
        price_capped = (df['modal_price_original'] != df['modal_price']).sum()
        arrival_capped = (df['arrivals_tonnes_original'] != df['arrivals_tonnes']).sum()

        logger.info(f"Winsorization applied: {price_capped} prices capped, {arrival_capped} arrivals capped")

        return df

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full outlier handling pipeline:
        1. Detect extreme spikes (flag only)
        2. Compute expanding percentile bounds
        3. Apply winsorization to extreme values
        4. Create anomaly flags

        Args:
            df: Clean DataFrame with continuous daily index

        Returns:
            DataFrame with outlier flags and winsorized values
        """
        logger.info("=" * 60)
        logger.info("STAGE 4: OUTLIER HANDLING")
        logger.info("=" * 60)

        if df.empty:
            return df

        initial_shape = df.shape

        # Ensure sorted by date
        df = df.sort_values('date').reset_index(drop=True)

        # Step 1: Detect spikes (flag only, no modification)
        df = self._detect_spikes(df)

        # Step 2: Compute anomaly flags using expanding percentiles
        df = self._compute_anomaly_flags(df)

        # Step 3: Apply winsorization
        df = self._apply_winsorization(df)

        final_shape = df.shape
        logger.info(f"Stage 4 Complete: {initial_shape} → {final_shape}")

        return df
