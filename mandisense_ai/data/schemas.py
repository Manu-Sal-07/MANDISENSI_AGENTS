from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import numpy as np

# Why: Centralized models define exact contracts for data inputs/outputs.
# This prevents pandas-level schema deviations as data flows through the pipelines.
# Updated to include production-grade preprocessing outputs and validation schemas.


class RawAgmarknetRecord(BaseModel):
    """
    Represents a single raw row from an Agmarknet CSV.
    Fields match standard Agmarknet CSV exports.
    """
    model_config = ConfigDict(coerce_numbers_to_str=False)

    date: date
    commodity: str
    market: str
    arrivals_tonnes: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    modal_price: float = 0.0
    state: Optional[str] = None
    district: Optional[str] = None
    variety: Optional[str] = None
    grade: Optional[str] = None


class ProcessedPriceRecord(BaseModel):
    """
    Represents a cleaned, standardized record with continuous daily index.
    Post Stage 2-3 output before feature engineering.
    """
    date: date
    commodity: str
    market: str
    arrivals_tonnes: float
    min_price: float
    max_price: float
    modal_price: float
    is_trading_day: bool
    price_spike_flag: bool
    # Outlier handling flags (Stage 4)
    arrivals_spike_flag: Optional[bool] = None
    is_price_outlier: Optional[bool] = None
    is_arrival_outlier: Optional[bool] = None
    # Winsorized values
    modal_price_original: Optional[float] = None
    arrivals_tonnes_original: Optional[float] = None


class BaseFeatures(BaseModel):
    """
    Base feature set (Stage 5) shared across all agents.
    """
    # Temporal features
    day_of_week: int = Field(ge=0, le=6)
    month: int = Field(ge=1, le=12)
    quarter: int = Field(ge=1, le=4)
    day_of_year: int = Field(ge=1, le=366)
    week_of_year: int = Field(ge=1, le=53)
    is_month_start: int = Field(ge=0, le=1)
    is_month_end: int = Field(ge=0, le=1)

    # Lag features (price)
    price_lag_1: Optional[float] = None
    price_lag_7: Optional[float] = None
    price_lag_14: Optional[float] = None
    price_lag_30: Optional[float] = None

    # Lag features (arrivals)
    arrivals_lag_1: Optional[float] = None
    arrivals_lag_7: Optional[float] = None
    arrivals_lag_14: Optional[float] = None
    arrivals_lag_30: Optional[float] = None

    # Rolling statistics (price)
    price_mean_7: Optional[float] = None
    price_std_7: Optional[float] = None
    price_mean_14: Optional[float] = None
    price_mean_30: Optional[float] = None
    price_std_14: Optional[float] = None
    price_std_30: Optional[float] = None
    price_min_30: Optional[float] = None
    price_max_30: Optional[float] = None

    # Rolling statistics (arrivals)
    arrivals_mean_7: Optional[float] = None
    arrivals_mean_14: Optional[float] = None
    arrivals_mean_30: Optional[float] = None
    arrivals_std_7: Optional[float] = None

    # Returns and momentum
    daily_returns: Optional[float] = None
    log_returns: Optional[float] = None
    returns_3d: Optional[float] = None
    returns_7d: Optional[float] = None
    returns_14d: Optional[float] = None
    momentum_7: Optional[float] = None
    momentum_14: Optional[float] = None
    momentum_30: Optional[float] = None

    # Price range features
    price_range: Optional[float] = None
    price_range_pct: Optional[float] = None
    price_position_30: Optional[float] = None

    # Correlation
    price_arrival_corr_14: Optional[float] = None


class SeasonalityFeatures(BaseModel):
    """
    Specialized features for the Seasonality Agent (30-day horizon).
    Extends BaseFeatures with cycle-specific indicators.
    """
    # Trend components
    trend_30: Optional[float] = None

    # Seasonal strength (inverse of coefficient of variation)
    seasonal_strength: Optional[float] = Field(None, ge=0, le=1)

    # Volatility
    rolling_volatility_30: Optional[float] = None

    # Cycle position
    is_cycle_peak: Optional[int] = Field(None, ge=0, le=1)
    is_cycle_trough: Optional[int] = Field(None, ge=0, le=1)


class ArrivalFeatures(BaseModel):
    """
    Specialized features for the Arrival Volume Agent (7-day horizon).
    """
    # Deviation metrics
    arrival_deviation_pct: Optional[float] = None
    arrivals_yoy_deviation: Optional[float] = None

    # Momentum
    supply_momentum: Optional[float] = None

    # Elasticity
    rolling_elasticity: Optional[float] = None

    # Stress indicators
    supply_stress_score: Optional[float] = Field(None, ge=0)

    # Regime (categorical)
    supply_regime: Optional[str] = None


class FinalFeatureSet(BaseModel):
    """
    Complete feature matrix ready for model training.
    Combines base + agent-specific features.
    """
    # Core identifiers
    date: date
    commodity: str
    market: str

    # Price and arrival (targets will be added separately)
    modal_price: float
    arrivals_tonnes: float

    # All features from BaseFeatures, SeasonalityFeatures, ArrivalFeatures
    # Included via composition at runtime - schema just documents completeness


class TargetSet(BaseModel):
    """
    Forward-looking target variables (strictly NO LEAKAGE).
    """
    target_7d: float = Field(description="7-day ahead percentage change")
    target_30d: float = Field(description="30-day ahead percentage change")


class ProcessedBatch(BaseModel):
    """
    Complete processed output for a single commodity-market pair.
    Combines features + targets + metadata.
    """
    commodity: str
    market: str
    features: List[Dict[str, Any]]
    targets: List[Dict[str, Any]]
    feature_columns: List[str]
    target_columns: List[str]
    metadata: Dict[str, Any]


class IngestionMetadata(BaseModel):
    """
    Quality monitoring metadata output after complete pipeline execution.
    """
    processed_at: datetime
    commodity: str
    market: str
    total_raw_records: int
    total_processed_records: int
    trading_days_percentage: float
    missing_imputations: int
    spikes_flagged: int
    start_date: date
    end_date: date
    outlier_flags: Optional[Dict[str, int]] = None
    feature_count: Optional[int] = None
    target_horizons: Optional[List[int]] = None


class ValidationReport(BaseModel):
    """
    Comprehensive data validation report.
    """
    overall_status: str  # PASS, WARNING, FAIL
    checks: Dict[str, Dict[str, Any]]
    critical_failures: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    dataset_hash: Optional[str] = None


class PipelineConfig(BaseModel):
    """
    Complete configuration for the preprocessing pipeline.
    Can be serialized to YAML/JSON for reproducibility.
    """
    version: str = "1.0.0"
    description: str = "Production-grade preprocessing pipeline for MandiSense AI"
    stages: List[str] = Field(
        default_factory=lambda: [
            "schema_normalization",
            "cleaning",
            "outlier_handling",
            "base_features",
            "agent_features",
            "target_engineering",
            "validation",
            "storage"
        ]
    )
    data: Any  # Config from config.py
    paths: Any
    preprocessing: Any
