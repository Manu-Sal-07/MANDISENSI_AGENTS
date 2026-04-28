from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional

# Why: Centralized models define exact contracts for data inputs/outputs.
# This prevents pandas-level schema deviations as data flows through the pipelines.

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
    Represents a cleaned, standardized record devoid of missing days.
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

class FeatureSet(BaseModel):
    """
    The finalized feature matrix fed securely into forecasting agents.
    """
    date: date
    commodity: str
    market: str
    modal_price: float
    arrivals_tonnes: float
    
    # Temporal Components
    day_of_week: int
    month: int
    is_month_end: bool
    is_festival_season: bool
    
    # Lags
    price_lag_1: Optional[float] = None
    price_lag_3: Optional[float] = None
    price_lag_7: Optional[float] = None
    price_lag_14: Optional[float] = None
    
    # Rolling Statistics
    price_roll_mean_7: Optional[float] = None
    price_roll_std_7: Optional[float] = None
    price_roll_mean_14: Optional[float] = None
    price_roll_mean_28: Optional[float] = None
    
    # Signal Proxies
    momentum_7: Optional[float] = None
    volatility_proxy_14: Optional[float] = None

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
