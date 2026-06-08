import pandas as pd
from pathlib import Path
from mandisense_ai.utils.logger import get_logger
from mandisense_ai.utils.exceptions import DataIngestionError
from mandisense_ai.utils.helpers import normalize_commodity_name, standardize_mandi_name

logger = get_logger(__name__)

class AgmarknetIngestor:
    """
    Responsible for ingesting chaotic, loosely formatted CSVs from Agmarknet,
    resolving semantic misnamings and mapping variables rigorously.
    """
    def __init__(self, raw_data_dir: str):
        self.raw_data_dir = Path(raw_data_dir)
        if not self.raw_data_dir.exists():
            self.raw_data_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Raw data directory {self.raw_data_dir} did not exist. Created empty folder.")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Why: Agmarknet files unpredictably switch column namings across extracts.
        This standardizes all to map our schema strictly.
        """
        col_map = {}
        for col in df.columns:
            clean_col = str(col).lower().strip().replace(' ', '_')
            if 'price' in clean_col and 'modal' in clean_col: col_map[col] = 'modal_price'
            elif 'price' in clean_col and 'min' in clean_col: col_map[col] = 'min_price'
            elif 'price' in clean_col and 'max' in clean_col: col_map[col] = 'max_price'
            elif 'arrival' in clean_col: col_map[col] = 'arrivals_tonnes'
            elif 'date' in clean_col: col_map[col] = 'date'
            elif 'market' in clean_col or 'mandi' in clean_col: col_map[col] = 'market'
            elif 'commodity' in clean_col: col_map[col] = 'commodity'
        return df.rename(columns=col_map)

    def load_csv(self, file_path: Path) -> pd.DataFrame:
        """
        Extracts CSV applying semantic fixing logic per line.
        """
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                logger.warning(f"Ingested an empty dataset from: {file_path}")
                return pd.DataFrame()
                
            df = self._normalize_columns(df)

            required_identity_cols = {'date', 'commodity', 'market'}
            missing_identity = required_identity_cols - set(df.columns)
            if missing_identity:
                logger.warning(
                    f"Skipping non-market CSV {file_path.name}: missing {sorted(missing_identity)}"
                )
                return pd.DataFrame()
            
            # Type casting heavily considering unscrubbed strings
            df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
            for num_col in ['arrivals_tonnes', 'modal_price', 'min_price', 'max_price']:
                if num_col in df.columns:
                    df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0.0)
                else:
                    df[num_col] = 0.0
                    
            if 'commodity' in df.columns:
                df['commodity'] = df['commodity'].apply(normalize_commodity_name)
            if 'market' in df.columns:
                df['market'] = df['market'].apply(standardize_mandi_name)
                
            # Safely drop unmappable ghost records
            df = df.dropna(subset=['date'])
            return df
            
        except Exception as e:
            logger.error(f"Integrity failure loading {file_path}: {e}")
            raise DataIngestionError(f"Fatal error processing {file_path}") from e

    def ingest_all(self) -> pd.DataFrame:
        """
        Ingests all potential CSV chunks in raw_dir simultaneously.
        """
        csv_files = list(self.raw_data_dir.glob("*.csv"))
        logger.info(f"Initialized ingestion for {len(csv_files)} targeted CSV files.")
        
        if not csv_files:
            return pd.DataFrame()
            
        dfs = []
        for file in csv_files:
            dfs.append(self.load_csv(file))
            
        return pd.concat(dfs, ignore_index=True)
