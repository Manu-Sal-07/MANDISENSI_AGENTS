import pandas as pd
import numpy as np
from pathlib import Path

# --- CONFIGURATION ---
V2_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/raw/v2")
V3_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/raw/v3")
METADATA_PATH = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/config/mandi_metadata.csv")
STABILITY_PATH = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/logs/missing_day_analysis.csv")
LOG_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/logs")

V3_DIR.mkdir(parents=True, exist_ok=True)

# --- SPLIT DEFINITIONS ---
TRAIN_END = "2025-06-30"
VAL_END = "2026-01-31"

def get_split(dt):
    if dt <= pd.Timestamp(TRAIN_END):
        return "train"
    elif dt <= pd.Timestamp(VAL_END):
        return "val"
    else:
        return "test"

# --- MAIN PASS ---
def finalize_data():
    # Load reliability weights
    weights_df = pd.read_csv(METADATA_PATH)
    weights_map = dict(zip(weights_df['mandi_id'], weights_df['mandi_weight']))
    
    # Load stability flags
    stability_df = pd.read_csv(STABILITY_PATH)
    stability_map = {}
    for _, row in stability_df.iterrows():
        stability_map[(row['commodity'], row['mandi_id'])] = row['is_unstable']
        
    commodities = [d.name for d in V2_DIR.iterdir() if d.is_dir()]
    quality_records = []
    
    for comm in commodities:
        comm_v2_dir = V2_DIR / comm
        comm_v3_dir = V3_DIR / comm
        comm_v3_dir.mkdir(parents=True, exist_ok=True)
        
        # Standardize commodity name
        standard_comm = comm.lower().strip()
        
        for csv_file in comm_v2_dir.glob("*.csv"):
            mandi_id = csv_file.stem
            df = pd.read_csv(csv_file)
            df['date'] = pd.to_datetime(df['date'])
            
            # STEP 1: Missing Data Flag
            df['is_missing'] = df['modal_price'].isna().astype(int)
            
            # STEP 3: Commodity Standardization Lock
            df['commodity'] = standard_comm
            
            # STEP 4: Leakage-Safe Splits
            df['split'] = df['date'].apply(get_split)
            
            # STEP 5: Stability Flag Propagation
            is_unstable = stability_map.get((comm, mandi_id), False)
            df['is_unstable'] = 1 if is_unstable else 0
            
            # STEP 6: Final Version (v3) Schema
            final_cols = [
                "date", "mandi_id", "commodity", "modal_price", "arrivals", 
                "is_missing", "split", "is_unstable"
            ]
            df = df[final_cols]
            
            # Save v3
            df.to_csv(comm_v3_dir / f"{mandi_id}.csv", index=False)
            
            # Audit for quality report
            total_records = len(df)
            missing_days = df['is_missing'].sum()
            
            # Get original stats from v2 report for continuity if needed
            # For simplicity, we re-calculate some basics
            quality_records.append({
                "commodity": standard_comm,
                "mandi_id": mandi_id,
                "total_records": total_records,
                "missing_days": missing_days,
                "continuity": round(((total_records - missing_days) / total_records) * 100, 2),
                "is_unstable": is_unstable,
                "mandi_weight": weights_map.get(mandi_id, 0.7)
            })

    # STEP 7: Final Quality Report
    pd.DataFrame(quality_records).to_csv(LOG_DIR / "data_quality_report_v3.csv", index=False)
    print(f"Finalization Complete. v3 data saved to {V3_DIR}")

if __name__ == "__main__":
    finalize_data()
