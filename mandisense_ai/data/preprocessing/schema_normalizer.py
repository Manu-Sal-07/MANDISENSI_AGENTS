"""
STAGE 1: SCHEMA NORMALIZATION

Ensures strict, consistent schema across all raw Agmarknet CSV variants:
- Standardizes column names (lowercase, snake_case)
- Enforces required data types
- Removes duplicates (date + commodity + market)
- Sorts chronologically
- Validates schema integrity

This stage is the foundation for all downstream processing - any failure here
propagates errors through the entire pipeline.
"""

import pandas as pd
import numpy as np

from mandisense_ai.utils.logger import get_logger
from .config import config

logger = get_logger(__name__)


class SchemaNormalizer:
    """
    Normalizes raw Agmarknet data to a strict, production-ready schema.

    Key guarantees:
    - All column names are lowercase snake_case
    - Required columns present: date, commodity, market, modal_price, arrivals_tonnes
    - Data types: date→datetime64[ns], numeric→float32
    - No duplicate (date, commodity, market) records
    - Chronologically sorted
    """

    # Canonical column mapping - all variations map here
    COLUMN_MAP = {
        'mandi': 'market',
        'arrival': 'arrivals_tonnes',
        'arrivals': 'arrivals_tonnes',
        'arrival_tonnes': 'arrivals_tonnes',
        'modal_price': 'modal_price',
        'modalprice': 'modal_price',
        'min_price': 'min_price',
        'minprice': 'min_price',
        'max_price': 'max_price',
        'maxprice': 'max_price',
        'date': 'date',
        'commodity': 'commodity',
        'market': 'market',
        'state': 'state',
        'district': 'district'
    }

    def __init__(self, config=config):
        self.config = config
        self.required_cols = ['date', 'commodity', 'market', 'modal_price', 'arrivals_tonnes']

    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardizes all column names to lowercase snake_case.
        Handles Agmarknet's inconsistent column naming across extracts.
        """
        rename_map = {}
        unmapped = []

        for col in df.columns:
            clean_col = (
                str(col)
                .lower()
                .strip()
                .replace(' ', '_')
                .replace('-', '_')
                .replace('/', '_')
            )

            # Check direct mapping
            if clean_col in self.COLUMN_MAP:
                rename_map[col] = self.COLUMN_MAP[clean_col]
            elif 'price' in clean_col and 'modal' in clean_col:
                rename_map[col] = 'modal_price'
            elif 'price' in clean_col and 'min' in clean_col:
                rename_map[col] = 'min_price'
            elif 'price' in clean_col and 'max' in clean_col:
                rename_map[col] = 'max_price'
            elif 'arrival' in clean_col:
                rename_map[col] = 'arrivals_tonnes'
            elif 'date' in clean_col:
                rename_map[col] = 'date'
            elif 'market' in clean_col or 'mandi' in clean_col:
                rename_map[col] = 'market'
            elif 'commodity' in clean_col:
                rename_map[col] = 'commodity'
            else:
                unmapped.append(col)

        if unmapped:
            logger.warning(f"Unmapped columns (will be dropped): {unmapped}")

        df = df.rename(columns=rename_map)
        keep_cols = [
            'date', 'commodity', 'market', 'modal_price', 'arrivals_tonnes',
            'min_price', 'max_price', 'state', 'district', 'variety', 'grade'
        ]
        df = df[[c for c in keep_cols if c in df.columns]]
        logger.info(f"Column normalization: {len(rename_map)} columns mapped")
        return df

    def enforce_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enforces strict schema:
        - Ensures all required columns exist
        - Sets correct data types
        - Creates missing columns with defaults
        """
        # Check required columns
        missing = [col for col in self.required_cols if col not in df.columns]
        if missing:
            logger.error(f"Missing required columns after normalization: {missing}")
            raise ValueError(f"Schema violation: missing columns {missing}")

        # Enforce dtypes
        df = df.copy()

        # Date column - must be datetime64[ns]
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
            logger.debug("Converted 'date' to datetime64[ns]")

        # Numeric columns - cast to float32 for memory efficiency. Keep missing
        # values as NaN here; imputation belongs to the cleaning stage.
        numeric_cols = ['modal_price', 'arrivals_tonnes', 'min_price', 'max_price']
        for col in numeric_cols:
            if col in df.columns:
                cleaned = (
                    df[col]
                    .astype(str)
                    .str.replace(',', '', regex=False)
                    .str.strip()
                    .replace({'': np.nan, 'nan': np.nan, 'None': np.nan})
                )
                df[col] = pd.to_numeric(cleaned, errors='coerce').astype('float32')
                df.loc[df[col] < 0, col] = np.nan
            else:
                df[col] = np.nan

        # String columns
        for col in ['commodity', 'market']:
            df[col] = df[col].astype(str).str.lower().str.strip()

        df = df.dropna(subset=['date', 'commodity', 'market']).copy()

        logger.info("Schema enforcement complete")
        return df

    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Removes duplicate records on (date, commodity, market).
        If duplicates exist, aggregates them:
        - Price columns: mean
        - Arrivals: sum
        """
        initial_count = len(df)

        # Check for duplicates
        dup_mask = df.duplicated(subset=['date', 'commodity', 'market'], keep=False)
        if dup_mask.any():
            logger.warning(f"Found {dup_mask.sum()} duplicate rows. Aggregating...")

            # Define aggregation rules
            agg_rules = {
                'arrivals_tonnes': 'sum',
                'modal_price': 'mean',
                'min_price': 'mean',
                'max_price': 'mean',
                'state': 'first',
                'district': 'first',
                'variety': 'first',
                'grade': 'first'
            }

            # Keep only columns that exist
            agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}

            df = df.groupby(['date', 'commodity', 'market'], as_index=False).agg(agg_rules)
            logger.info(f"Deduplication: {initial_count} → {len(df)} rows")

        return df

    def sort_chronologically(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sorts data by date ascending within each commodity-market group."""
        df = df.sort_values(['commodity', 'market', 'date']).reset_index(drop=True)
        logger.debug("Data sorted chronologically")
        return df

    def validate_schema(self, df: pd.DataFrame) -> None:
        """
        Validates that the normalized DataFrame meets all schema requirements.
        Raises assertion errors if validation fails.
        """
        # Check required columns exist
        for col in self.required_cols:
            assert col in df.columns, f"Missing required column: {col}"

        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(df['date']), "date column must be datetime64"
        assert pd.api.types.is_numeric_dtype(df['modal_price']), "modal_price must be numeric"
        assert pd.api.types.is_numeric_dtype(df['arrivals_tonnes']), "arrivals_tonnes must be numeric"

        # Check for negative prices or arrivals, ignoring missing values that
        # the cleaning stage is responsible for imputing.
        assert (df['modal_price'].dropna() >= 0).all(), "Negative modal prices detected"
        assert (df['arrivals_tonnes'].dropna() >= 0).all(), "Negative arrivals detected"

        # Check date range is reasonable
        year_range = df['date'].dt.year.max() - df['date'].dt.year.min()
        assert 0 <= year_range <= 30, f"Date range suspicious: {year_range} years"

        logger.info("Schema validation passed ✓")
        return True

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full Stage 1 transformation pipeline.
        Returns normalized, deduplicated, sorted DataFrame.
        """
        logger.info("=" * 60)
        logger.info("STAGE 1: SCHEMA NORMALIZATION")
        logger.info("=" * 60)

        initial_shape = df.shape

        # Step 1: Normalize column names
        df = self.normalize_column_names(df)

        # Step 2: Enforce strict schema
        df = self.enforce_schema(df)

        # Step 3: Remove duplicates
        df = self.remove_duplicates(df)

        # Step 4: Sort chronologically
        df = self.sort_chronologically(df)

        # Step 5: Validate
        try:
            self.validate_schema(df)
        except AssertionError as e:
            logger.error(f"Schema validation failed: {e}")
            raise

        final_shape = df.shape
        logger.info(f"Stage 1 Complete: {initial_shape} → {final_shape}")
        logger.info(f"Columns: {list(df.columns)}")

        return df
