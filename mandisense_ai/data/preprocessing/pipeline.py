"""
STAGE 9: PIPELINE ORCHESTRATION

Central orchestrator that executes all preprocessing stages in sequence:
1. Schema Normalization
2. Data Cleaning & Time Alignment
3. Outlier Handling (winsorization + flags)
4. Base Feature Engineering
5. Agent-Specific Features
6. Target Engineering
7. Data Validation
8. Storage (Parquet)

Processes each (commodity, market) pair independently to prevent leakage.
Outputs production-ready datasets ready for model training.

Design principles:
- Single source of truth for all agents
- Deterministic outputs (fixed seeds, deterministic operations)
- Comprehensive logging and metadata collection
- Fault tolerance (continues on per-group failures)
- Scalable to large datasets (10+ years, multiple commodities)
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import hashlib
import json

from mandisense_ai.utils.logger import get_logger
from mandisense_ai.data.schemas import IngestionMetadata
from mandisense_ai.data.ingestion.agmarknet_ingestor import AgmarknetIngestor

# Import new pipeline stages
from .schema_normalizer import SchemaNormalizer
from .enhanced_cleaner import DataCleaner
from .outlier_handler import OutlierHandler
from .feature_engineering import BaseFeatureEngineer
from .agent_features import AgentFeatureGenerator
from .target_engineer import TargetEngineer
from .validator import DataValidator, DataValidationError
from .config import config

logger = get_logger(__name__)


class PipelineStage(Enum):
    """Pipeline stage identifiers for tracking."""
    INGESTION = "ingestion"
    SCHEMA_NORMALIZATION = "schema_normalization"
    CLEANING = "cleaning"
    OUTLIER_HANDLING = "outlier_handling"
    BASE_FEATURES = "base_features"
    AGENT_FEATURES = "agent_features"
    TARGET_ENGINEERING = "target_engineering"
    VALIDATION = "validation"
    STORAGE = "storage"


class PreprocessingPipeline:
    """
    Production-grade end-to-end preprocessing pipeline.

    Executes all 9 stages in order, ensuring leak-proof feature engineering.
    Processes each commodity-market pair independently.
    """

    def __init__(
        self,
        raw_data_dir: Optional[str] = None,
        processed_dir: Optional[str] = None,
        config_override: Optional[Any] = None
    ):
        """
        Initialize the pipeline with configuration.

        Args:
            raw_data_dir: Path to raw CSV files (default: from settings)
            processed_dir: Path for output Parquet files (default: from settings)
            config_override: Optional custom configuration
        """
        from mandisense_ai.config.settings import settings

        self.raw_data_dir = Path(raw_data_dir or settings.paths.raw_data)
        self.processed_dir = Path(processed_dir or settings.paths.processed_data)
        self.config = config_override or config

        # Ensure output directory exists
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # Initialize pipeline components
        logger.info("Initializing Preprocessing Pipeline components...")
        self.ingestor = AgmarknetIngestor(str(self.raw_data_dir))
        self.schema_normalizer = SchemaNormalizer(self.config)
        self.cleaner = DataCleaner(self.config)
        self.outlier_handler = OutlierHandler(self.config)
        self.base_feature_engineer = BaseFeatureEngineer(self.config)
        self.agent_feature_generator = AgentFeatureGenerator(self.config)
        self.target_engineer = TargetEngineer(self.config)
        self.validator = DataValidator(self.config)

        logger.info("Pipeline initialized successfully ✓")

    def _process_single_group(
        self,
        df: pd.DataFrame,
        commodity: str,
        market: str
    ) -> Optional[pd.DataFrame]:
        """
        Process a single (commodity, market) group through all pipeline stages.

        Args:
            df: Raw data already filtered to this group
            commodity: Commodity name
            market: Market/mandi name

        Returns:
            Fully processed DataFrame ready for model training, or None if failed
        """
        try:
            logger.info(f"{'=' * 60}")
            logger.info(f"Processing: {commodity.upper()} @ {market.upper()}")
            logger.info(f"{'=' * 60}")

            initial_rows = len(df)

            # Stage 1: Schema Normalization
            logger.info(f"[{PipelineStage.SCHEMA_NORMALIZATION.value}] Normalizing schema...")
            df = self.schema_normalizer.transform(df)
            if df.empty:
                logger.warning(f"Empty after schema normalization for {commodity}/{market}")
                return None

            # Stages 2-3: Cleaning & Time Alignment
            logger.info(f"[{PipelineStage.CLEANING.value}] Cleaning data...")
            df = self.cleaner.clean(df, commodity=commodity, market=market)
            if df.empty:
                logger.warning(f"Empty after cleaning for {commodity}/{market}")
                return None

            # Stage 4: Outlier Handling
            logger.info(f"[{PipelineStage.OUTLIER_HANDLING.value}] Handling outliers...")
            df = self.outlier_handler.process(df)

            # Stage 5: Base Feature Engineering
            logger.info(f"[{PipelineStage.BASE_FEATURES.value}] Creating base features...")
            df = self.base_feature_engineer.transform(df)

            # Stage 6: Agent-Specific Features
            logger.info(f"[{PipelineStage.AGENT_FEATURES.value}] Creating agent features...")
            df = self.agent_feature_generator.transform(df, add_festival=False)

            # Stage 7: Target Engineering (with drop_future=True)
            logger.info(f"[{PipelineStage.TARGET_ENGINEERING.value}] Creating targets...")
            df = self.target_engineer.transform(df, drop_future=True)
            if df.empty:
                logger.warning(f"Empty after target creation for {commodity}/{market}")
                return None

            # Stage 8: Data Validation
            logger.info(f"[{PipelineStage.VALIDATION.value}] Validating data...")
            self.validator.validate(df, group_cols=None)  # Already single group

            if 'mandi' not in df.columns:
                df['mandi'] = df['market']

            final_rows = len(df)
            logger.info(
                f"{commodity}/{market} processing complete: "
                f"{initial_rows} raw → {final_rows} processed rows "
                f"({(final_rows/initial_rows*100):.1f}% retention)"
            )

            return df

        except Exception as e:
            logger.error(f"Failed to process {commodity}/{market}: {e}", exc_info=True)
            return None

    def _save_output(
        self,
        df: pd.DataFrame,
        commodity: str,
        market: str,
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Save processed DataFrame to Parquet format.

        Filename pattern: {commodity}_{market}_processed.parquet

        Args:
            df: Processed DataFrame
            commodity: Commodity name
            market: Market name
            metadata: Optional metadata dict to embed in filename

        Returns:
            Path to saved file
        """
        # Sanitize names for filesystem
        safe_commodity = commodity.lower().replace(' ', '_').replace('/', '-')
        safe_market = market.lower().replace(' ', '_').replace('/', '-')

        filename = self.config.FILENAME_PATTERN.format(
            commodity=safe_commodity,
            market=safe_market,
            format=self.config.OUTPUT_FORMAT
        )

        output_path = self.processed_dir / filename

        df = df.copy()
        if 'mandi' not in df.columns and 'market' in df.columns:
            df['mandi'] = df['market']

        # Stable ordering helps deterministic artifacts and version diffs.
        id_cols = [c for c in ['date', 'commodity', 'market', 'mandi'] if c in df.columns]
        other_cols = [c for c in df.columns if c not in id_cols]
        df = df[id_cols + other_cols]

        df.to_parquet(output_path, index=False, engine='pyarrow', compression=self.config.OUTPUT_COMPRESSION)

        dataset_hash = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values).hexdigest()
        sidecar_metadata = {
            'pipeline_version': getattr(self.config, 'VERSION', 'unknown'),
            'created_at_utc': datetime.utcnow().isoformat() + 'Z',
            'commodity': commodity,
            'market': market,
            'mandi': market,
            'rows': int(len(df)),
            'columns': list(df.columns),
            'target_horizons': list(self.config.TARGET_HORIZONS),
            'dataset_hash': dataset_hash,
        }
        if metadata:
            sidecar_metadata.update(metadata)

        metadata_path = output_path.with_suffix('.metadata.json')
        metadata_path.write_text(json.dumps(sidecar_metadata, indent=2, default=str), encoding='utf-8')

        # Compatibility artifact for older agents/scripts that look for
        # {commodity}_{market}_features.parquet.
        compatibility_path = self.processed_dir / f"{safe_commodity}_{safe_market}_features.parquet"
        if compatibility_path != output_path:
            df.to_parquet(
                compatibility_path,
                index=False,
                engine='pyarrow',
                compression=self.config.OUTPUT_COMPRESSION
            )

        logger.info(f"Saved {len(df)} rows to {output_path}")

        return output_path

    def run(self) -> Dict[str, Any]:
        """
        Execute the full preprocessing pipeline across all commodity-market pairs.

        Returns:
            Dictionary mapping group keys to processing metadata
        """
        logger.info("=" * 60)
        logger.info("STARTING PREPROCESSING PIPELINE")
        logger.info("=" * 60)

        # Stage 1: Ingest all raw data
        logger.info(f"[{PipelineStage.INGESTION.value}] Ingesting raw CSVs from {self.raw_data_dir}...")
        raw_df = self.ingestor.ingest_all()

        if raw_df.empty:
            logger.warning("No raw data found to process")
            return {}

        logger.info(f"Ingested {len(raw_df)} total records")

        # Check required columns after ingestion
        required_cols = ['date', 'commodity', 'market', 'modal_price', 'arrivals_tonnes']
        missing_cols = [c for c in required_cols if c not in raw_df.columns]
        if missing_cols:
            raise ValueError(f"Raw data missing required columns: {missing_cols}")

        # Get unique commodity-market pairs
        pairs = raw_df[['commodity', 'market']].drop_duplicates().values
        logger.info(f"Found {len(pairs)} commodity-market pairs to process")

        results = {}
        failures = []

        for commodity, market in pairs:
            # Filter to this group
            group_df = raw_df[
                (raw_df['commodity'] == commodity) &
                (raw_df['market'] == market)
            ].copy()

            if len(group_df) < 10:
                logger.warning(f"Skipping {commodity}/{market}: only {len(group_df)} rows (insufficient)")
                continue

            try:
                # Process through all stages
                processed_df = self._process_single_group(group_df, commodity, market)

                if processed_df is not None and not processed_df.empty:
                    # Save output
                    output_path = self._save_output(processed_df, commodity, market)

                    # Create metadata
                    metadata = IngestionMetadata(
                        processed_at=datetime.utcnow(),
                        commodity=commodity,
                        market=market,
                        total_raw_records=len(group_df),
                        total_processed_records=len(processed_df),
                        trading_days_percentage=float(processed_df['is_trading_day'].mean() * 100),
                        missing_imputations=int(len(processed_df) - processed_df['is_trading_day'].sum()),
                        spikes_flagged=int(processed_df['price_spike_flag'].sum()),
                        start_date=processed_df['date'].min().date(),
                        end_date=processed_df['date'].max().date()
                    )

                    results[f"{commodity}_{market}"] = {
                        'metadata': metadata.model_dump(),
                        'output_path': str(output_path),
                        'feature_count': len(processed_df.columns),
                        'target_columns': [c for c in processed_df.columns if c.startswith('target_')]
                    }

                    logger.info(f"✓ {commodity}/{market} completed successfully")

            except Exception as e:
                logger.error(f"✗ {commodity}/{market} failed: {e}", exc_info=True)
                failures.append((commodity, market, str(e)))
                continue

        # Summary
        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total pairs processed: {len(pairs)}")
        logger.info(f"Successful: {len(results)}")
        logger.info(f"Failed: {len(failures)}")

        if failures:
            logger.error("FAILURES:")
            for commodity, market, error in failures:
                logger.error(f"  - {commodity}/{market}: {error}")

        success_rate = (len(results) / len(pairs)) * 100 if len(pairs) > 0 else 0
        logger.info(f"Success rate: {success_rate:.1f}%")

        return results

    def run_single(self, commodity: str, market: str) -> Optional[Dict[str, Any]]:
        """
        Process a single commodity-market pair from raw data.

        Args:
            commodity: Commodity name
            market: Market name

        Returns:
            Metadata dict if successful, None otherwise
        """
        logger.info(f"Running single group: {commodity}/{market}")

        # Load raw data
        raw_df = self.ingestor.ingest_all()

        if raw_df.empty:
            logger.error("No raw data available")
            return None

        # Filter to specific group
        group_df = raw_df[
            (raw_df['commodity'] == commodity) &
            (raw_df['market'] == market)
        ].copy()

        if len(group_df) < 10:
            logger.error(f"Insufficient data for {commodity}/{market}: {len(group_df)} rows")
            return None

        # Process
        processed_df = self._process_single_group(group_df, commodity, market)

        if processed_df is None or processed_df.empty:
            logger.error(f"Processing failed for {commodity}/{market}")
            return None

        # Save
        output_path = self._save_output(processed_df, commodity, market)

        metadata = IngestionMetadata(
            processed_at=datetime.utcnow(),
            commodity=commodity,
            market=market,
            total_raw_records=len(group_df),
            total_processed_records=len(processed_df),
            trading_days_percentage=float(processed_df['is_trading_day'].mean() * 100),
            missing_imputations=int(len(processed_df) - processed_df['is_trading_day'].sum()),
            spikes_flagged=int(processed_df['price_spike_flag'].sum()),
            start_date=processed_df['date'].min().date(),
            end_date=processed_df['date'].max().date()
        )

        result = {
            'metadata': metadata.model_dump(),
            'output_path': str(output_path),
            'feature_count': len(processed_df.columns),
            'target_columns': [c for c in processed_df.columns if c.startswith('target_')]
        }

        logger.info(f"Single group processing complete: {output_path}")
        return result


# Convenience function for quick execution
def run_pipeline() -> Dict[str, Any]:
    """
    Quick entry point to run the full pipeline with default configuration.
    """
    pipeline = PreprocessingPipeline()
    return pipeline.run()


def run_single(commodity: str, market: str) -> Optional[Dict[str, Any]]:
    """
    Quick entry point to process a single commodity-market pair.
    """
    pipeline = PreprocessingPipeline()
    return pipeline.run_single(commodity, market)
