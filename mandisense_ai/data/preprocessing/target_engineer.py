"""
STAGE 7: TARGET ENGINEERING (STRICT NO-LEAKAGE)

Creates forward-looking target variables for model training.

Targets:
- target_7d: (price[t+7] - price[t]) / price[t]
- target_30d: (price[t+30] - price[t]) / price[t]
"""

from typing import List

import numpy as np
import pandas as pd

from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class TargetEngineer:
    """
    Creates leak-proof forward-looking targets for time-series forecasting.

    At time t, all feature columns describe information available at or before
    t. The target is produced with a negative shift so the future outcome is
    aligned onto the row used for training.
    """

    def __init__(self, config=config):
        self.config = config
        self.horizons: List[int] = config.TARGET_HORIZONS
        self.prefix = config.TARGET_COLUMN_PREFIX

    def _create_target_for_horizon(self, df: pd.DataFrame, horizon: int) -> pd.Series:
        current_price = df["modal_price"].astype("float64")
        future_price = df["modal_price"].shift(-horizon).astype("float64")
        target = (future_price - current_price) / current_price.replace(0, np.nan)
        target.name = f"{self.prefix}{horizon}d"
        return target.replace([np.inf, -np.inf], np.nan)

    def _validate_target(self, target: pd.Series, horizon: int) -> pd.Series:
        nan_count = int(target.isna().sum())
        if nan_count:
            logger.info(f"Target {horizon}d: {nan_count} NaN values before final horizon drop")

        max_abs = target.dropna().abs().max()
        if pd.notna(max_abs) and max_abs > 5:
            logger.warning(f"Target {horizon}d: extreme values detected (max={max_abs:.2f})")

        return target.clip(-10, 10)

    def create_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("=" * 60)
        logger.info("STAGE 7: TARGET ENGINEERING (NO LEAKAGE)")
        logger.info("=" * 60)

        if df.empty:
            logger.warning("Empty DataFrame received")
            return df

        df = df.sort_values("date").copy()
        assert "modal_price" in df.columns, "modal_price column required for target creation"
        assert df["modal_price"].notna().all(), "modal_price contains NaN values"

        logger.info(f"Creating targets for horizons: {self.horizons} days")
        for horizon in self.horizons:
            col = f"{self.prefix}{horizon}d"
            target = self._create_target_for_horizon(df, horizon)
            df[col] = self._validate_target(target, horizon)

            valid = df[col].dropna()
            if not valid.empty:
                logger.info(
                    f"{col}: mean={valid.mean():.4f}, std={valid.std():.4f}, "
                    f"min={valid.min():.4f}, max={valid.max():.4f}"
                )

        return df

    def drop_future_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        target_cols = [f"{self.prefix}{h}d" for h in self.horizons]
        before = len(df)
        df = df.dropna(subset=target_cols).copy()
        dropped = before - len(df)
        logger.info(
            f"Dropped {dropped} rows with NaN targets "
            f"(last {max(self.horizons)} days per commodity-market group)"
        )

        remaining = int(df[target_cols].isna().sum().sum())
        assert remaining == 0, f"Target creation failed: {remaining} NaN targets remain"
        return df

    def drop_unusable_feature_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop rows whose historical feature vector is incomplete.

        Early lag, rolling, YoY, and elasticity features need sufficient past
        context. Dropping these rows is safer than filling unavailable history.
        """
        before = len(df)
        df = df.replace([np.inf, -np.inf], np.nan)
        required_history_cols = [
            c for c in df.columns
            if c.startswith("price_lag_")
            or c.startswith("arrivals_lag_")
            or c in {
                "daily_returns",
                "log_returns",
                "returns_3d",
                "returns_7d",
                "returns_14d",
                "momentum_7",
                "momentum_14",
                "momentum_30",
                "arrival_deviation_pct",
                "arrivals_yoy_deviation",
                "supply_momentum",
            }
        ]

        df = df.dropna(subset=required_history_cols).copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        object_cols = df.select_dtypes(exclude=[np.number, "datetime64[ns]"]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        for col in object_cols:
            df[col] = df[col].fillna("unknown")

        dropped = before - len(df)
        if dropped:
            logger.info(f"Dropped {dropped} rows without complete historical feature context")
        logger.info(f"Final dataset size: {len(df)} rows")
        return df

    def transform(self, df: pd.DataFrame, drop_future: bool = True) -> pd.DataFrame:
        df = self.create_targets(df)

        if drop_future:
            df = self.drop_future_rows(df)
            df = self.drop_unusable_feature_rows(df)

        logger.info("Target engineering complete")
        return df
