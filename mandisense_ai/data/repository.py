import pandas as pd
from pathlib import Path
from typing import Optional

from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import DataIngestionError

logger = get_logger(__name__)

# Why: Abstraction separates the explicit IO (Pandas pyarrow interactions) 
# away from logical multi-agent layers. The agents strictly request DataFrames.

class DataRepository:
    """
    Globally scalable Unified Data Access Layer masking IO operations.
    """
    def __init__(self):
        self.processed_dir = Path(settings.paths.processed_data)
        logger.debug(f"DataRepository implicitly mapping requests to {self.processed_dir}")

    def get_processed_data(self, commodity: str, market: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Extrapolates securely built feature arrays for specialized analytical forecasting.
        Filters robustly by optional slice dates bridging train/validation requirements.
        """
        file_name = f"{commodity}_{market}_features.parquet".replace(" ", "_").lower()
        file_path = self.processed_dir / file_name
        
        if not file_path.exists():
            # Robust mapping attempting agnostic string case matches
            available_files = {f.name.lower(): f for f in self.processed_dir.glob("*.parquet")}
            if file_name in available_files:
                file_path = available_files[file_name]
            else:
                logger.error(f"Incomplete extraction array identified querying {commodity} within {market}")
                return pd.DataFrame()

        try:
            df = pd.read_parquet(file_path, engine='pyarrow')
            
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date)]
                
            return df.sort_values('date').reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"IO Serialization read error querying feature array {file_path}: {e}")
            raise DataIngestionError(f"Critical IO mismatch loading target {commodity}_{market}") from e

    def save_forecast(self, forecast_data: dict):
        """
        Persists unified AgentOutput aggregates permanently matching tracking timelines.
        """
        logger.info("Persisting generalized unified Agent predictions structure (Placeholder)")
        pass
