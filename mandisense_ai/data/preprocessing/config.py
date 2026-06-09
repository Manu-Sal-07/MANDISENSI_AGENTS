"""
Configuration for the agricultural price forecasting preprocessing pipeline.

All parameters are tuned for 10+ years of daily Agmarknet data across multiple commodities.
This configuration ensures leak-proof feature engineering and production-ready outputs.
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class PreprocessingConfig:
    """Centralized configuration for all preprocessing stages."""

    # ========== STAGE 1: SCHEMA NORMALIZATION ==========
    REQUIRED_COLUMNS: List[str] = field(
        default_factory=lambda: ['date', 'commodity', 'market', 'modal_price', 'arrivals_tonnes']
    )
    COLUMN_NAME_MAPPINGS: Dict[str, str] = field(
        default_factory=lambda: {
            'mandi': 'market',
            'arrival': 'arrivals_tonnes',
            'arrivals': 'arrivals_tonnes',
            'modal_price': 'modal_price',
            'min_price': 'min_price',
            'max_price': 'max_price'
        }
    )

    # ========== STAGE 2: DATA CLEANING ==========
    # Forward fill + backward fill for prices
    PRICE_FILL_LIMIT: int = 3  # Max consecutive days to fill (prevents over-imputation)
    ARRIVALS_ROLLING_MEDIAN_WINDOW: int = 7  # Rolling median for arrivals

    # ========== STAGE 3: TIME ALIGNMENT ==========
    TARGET_FREQUENCY: str = 'D'  # Daily frequency
    DATE_COLUMN: str = 'date'

    # ========== STAGE 4: OUTLIER HANDLING ==========
    # Winsorization bounds (percentiles) - applied using expanding historical window
    WINSORIZE_LOWER_PCT: float = 0.01  # 1st percentile
    WINSORIZE_UPPER_PCT: float = 0.99  # 99th percentile
    # Spike detection threshold (for flagging, not removal)
    PRICE_SPIKE_THRESHOLD: float = 0.30  # 30% single-day change
    ARRIVAL_SPIKE_THRESHOLD: float = 1.0  # 100% change (log scale)

    # ========== STAGE 5: BASE FEATURE ENGINEERING ==========
    # Temporal features
    TEMPORAL_FEATURES: List[str] = field(
        default_factory=lambda: ['day_of_week', 'month', 'quarter', 'is_month_end', 'is_month_start']
    )

    # Lag features (in days)
    PRICE_LAGS: List[int] = field(default_factory=lambda: [1, 7, 14, 30])
    ARRIVALS_LAGS: List[int] = field(default_factory=lambda: [1, 7, 14, 30])

    # Rolling statistics windows (in days)
    ROLLING_WINDOWS: List[int] = field(default_factory=lambda: [7, 14, 30, 60])

    # Minimum periods for rolling calculations (avoids early NaNs)
    MIN_PERIODS_RATIO: float = 0.5  # At least 50% of window size required

    # ========== STAGE 6: AGENT-SPECIFIC FEATURES ==========
    # Seasonality Agent features
    SEASONALITY_TREND_WINDOW: int = 30
    SEASONALITY_MOMENTUM_WINDOWS: List[int] = field(default_factory=lambda: [7, 14, 30])
    SEASONALITY_VOLATILITY_WINDOW: int = 30

    # Arrival Agent features
    ARRIVAL_DEVIATION_WINDOW: int = 30
    YOY_ALIGNMENT_TOLERANCE_DAYS: int = 7  # Allow ±7 days for same-date last year
    ARRIVAL_MOMENTUM_WINDOW: int = 7
    ELASTICITY_WINDOW: int = 14  # Rolling window for price-arrival correlation

    # ========== STAGE 7: TARGET ENGINEERING ==========
    # Prediction horizons (strictly no leakage)
    TARGET_HORIZONS: List[int] = field(default_factory=lambda: [7, 30])
    TARGET_COLUMN_PREFIX: str = 'target_'

    # ========== STAGE 8: VALIDATION ==========
    MAX_NAN_THRESHOLD: float = 0.01  # Max 1% NaN allowed after processing
    MAX_INF_THRESHOLD: float = 0.001  # Max 0.1% infinite values
    VALIDATE_NO_LEAKAGE: bool = True
    CHECK_TIME_MONOTONIC: bool = True

    # ========== STAGE 9: STORAGE ==========
    OUTPUT_DIR: str = 'data/processed'
    OUTPUT_FORMAT: str = 'parquet'
    OUTPUT_COMPRESSION: str = 'snappy'
    FILENAME_PATTERN: str = '{commodity}_{market}.{format}'
    VERSION: str = '1.1.0'

    # ========== PERFORMANCE & MEMORY ==========
    CHUNK_SIZE: int = 100000  # For large datasets
    DTYPE_OPTIMIZATION: bool = True
    FLOAT_PRECISION: str = 'float32'

    # ========== LOGGING & MONITORING ==========
    LOG_PROCESSED_GROUPS: bool = True
    LOG_DROPPED_ROWS: bool = True
    SAMPLE_METADATA: bool = True


# Global configuration instance - can be overridden via environment or YAML
config = PreprocessingConfig()
