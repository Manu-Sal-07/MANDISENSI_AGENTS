import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config.settings import settings
from utils.logger import get_logger
from data.schemas import IngestionMetadata
from data.ingestion.agmarknet_ingestor import AgmarknetIngestor
from data.preprocessing.cleaner import DataCleaner
from data.preprocessing.feature_engineering import FeatureEngineer

logger = get_logger(__name__)

class DataPipeline:
    """
    Central orchestration controller executing full ingestion mappings, cleaning pipelines, 
    and feature processing continuously exporting optimal Parquet formats.
    """
    def __init__(self):
        self.ingestor = AgmarknetIngestor(settings.paths.raw_data)
        self.cleaner = DataCleaner()
        self.engineer = FeatureEngineer()
        self.processed_dir = Path(settings.paths.processed_data)
        
        if not self.processed_dir.exists():
            self.processed_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        """
        Executes unified transformation processing returning operational analytics metadata.
        """
        logger.info("Bootstrapping Pipeline Execution Cycle...")
        
        raw_df = self.ingestor.ingest_all()
        if raw_df.empty:
            logger.warning("No unmapped CSVs tracked in processing bucket `data/raw/`.")
            return {}

        results = {}
        pairs = raw_df[['commodity', 'market']].drop_duplicates().values
        
        for commodity, market in pairs:
            if not commodity or not market:
                continue
                
            logger.info(f"Targeting logic structure for subset -> {commodity} | {market}")
            
            pair_raw_count = len(raw_df[(raw_df['commodity'] == commodity) & (raw_df['market'] == market)])
            
            # Step 1: Fix gaps and anomalies
            clean_df = self.cleaner.clean(raw_df, commodity, market)
            if clean_df.empty:
                continue
                
            total_processed = len(clean_df)
            trading_days_pct = clean_df['is_trading_day'].mean() * 100
            missing_imputations = total_processed - clean_df['is_trading_day'].sum()
            spikes_count = clean_df['price_spike_flag'].sum()
            start_dt = clean_df['date'].min().date()
            end_dt = clean_df['date'].max().date()

            # Step 2: Extrapolate modeling features
            feature_df = self.engineer.generate_features(clean_df)
            
            # Step 3: Serialize out logic structure efficiently preventing CSV float drift
            save_name = f"{commodity}_{market}_features.parquet".replace(" ", "_")
            save_path = self.processed_dir / save_name
            
            # High compression Parquet via pyarrow engine mappings
            feature_df.to_parquet(save_path, index=False, engine='pyarrow')
            
            meta = IngestionMetadata(
                processed_at=datetime.utcnow(),
                commodity=commodity,
                market=market,
                total_raw_records=pair_raw_count,
                total_processed_records=total_processed,
                trading_days_percentage=round(trading_days_pct, 2),
                missing_imputations=int(missing_imputations),
                spikes_flagged=int(spikes_count),
                start_date=start_dt,
                end_date=end_dt
            )
            
            results[f"{commodity}_{market}"] = meta.model_dump()
            logger.info(f"Deployed optimally tuned dataset -> {save_path}")
            
        logger.info(f"Processing cycles closed. Total entity matrix structures resolved: {len(results)}")
        return results
