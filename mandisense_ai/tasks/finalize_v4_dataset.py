import pandas as pd
import numpy as np
from pathlib import Path

# --- CONFIGURATION ---
V3_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/raw/v3")
V4_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/processed/v4")
LOG_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/logs")

V4_DIR.mkdir(parents=True, exist_ok=True)

# --- FINAL SCHEMA (LOCKED) ---
FINAL_SCHEMA = [
    "date", "mandi_id", "commodity", "price", "arrivals", 
    "arrivals_log", "is_missing", "is_unstable", 
    "is_valid_training", "split"
]

STRICT_TYPES = {
    "mandi_id": "string",
    "commodity": "string",
    "price": "float64",
    "arrivals": "float64",
    "arrivals_log": "float64",
    "is_missing": "int64",
    "is_unstable": "int64",
    "is_valid_training": "int64",
    "split": "string"
}

def finalize_v4():
    commodities = [d.name for d in V3_DIR.iterdir() if d.is_dir()]
    final_quality_records = []
    
    print("--- STARTING FINAL DATASET LOCK (v4) ---")
    
    for comm in commodities:
        print(f"Processing {comm}...")
        comm_v3_dir = V3_DIR / comm
        comm_data = []
        
        for csv_file in comm_v3_dir.glob("*.csv"):
            df = pd.read_csv(csv_file)
            df['date'] = pd.to_datetime(df['date'])
            
            # STEP 1: Rename Column & Ensure Type
            df = df.rename(columns={"modal_price": "price"})
            
            # STEP 2: Training Validity Mask
            df['is_valid_training'] = ((df['is_missing'] == 0) & (df['split'] == "train")).astype(int)
            
            # STEP 3: Arrival Scale Normalization
            df['arrivals_log'] = np.log1p(df['arrivals'].fillna(0))
            
            # STEP 6: Integrity Check
            # Remove negative prices or arrivals (if any)
            df.loc[df['price'] < 0, 'price'] = np.nan
            df.loc[df['arrivals'] < 0, 'arrivals'] = np.nan
            
            comm_data.append(df)
            
        # Combine all mandis for this commodity
        combined_df = pd.concat(comm_data, ignore_index=True)
        
        # STEP 5: Sorting Guarantee
        combined_df = combined_df.sort_values(['mandi_id', 'date']).reset_index(drop=True)
        
        # STEP 6: Duplicate Check
        duplicate_count = combined_df.duplicated(subset=['date', 'mandi_id', 'commodity']).sum()
        if duplicate_count > 0:
            print(f"  [WARNING] Removing {duplicate_count} duplicates for {comm}")
            combined_df = combined_df.drop_duplicates(subset=['date', 'mandi_id', 'commodity'])
            
        # STEP 4: Data Type Enforcement
        for col, dtype in STRICT_TYPES.items():
            combined_df[col] = combined_df[col].astype(dtype)
            
        # Final Column Order
        combined_df = combined_df[FINAL_SCHEMA]
        
        # STEP 7: Dataset Segregation
        save_path = V4_DIR / f"{comm}.csv"
        combined_df.to_csv(save_path, index=False)
        
        # STEP 9: Final Quality Report per mandi/commodity
        for mandi_id in combined_df['mandi_id'].unique():
            m_df = combined_df[combined_df['mandi_id'] == mandi_id]
            final_quality_records.append({
                "commodity": comm,
                "mandi_id": mandi_id,
                "total_rows": len(m_df),
                "training_rows": m_df['is_valid_training'].sum(),
                "missing_ratio": round(m_df['is_missing'].mean(), 4),
                "instability_flag": m_df['is_unstable'].iloc[0],
                "avg_price": round(m_df['price'].mean(), 2),
                "avg_arrivals": round(m_df['arrivals'].mean(), 2)
            })
            
    # Save Quality Report
    pd.DataFrame(final_quality_records).to_csv(LOG_DIR / "final_dataset_report.csv", index=False)
    
    print(f"\n--- DATASET FREEZE COMPLETE ---")
    print(f"VERSION = v4")
    print(f"STATUS = FINAL")
    print(f"Location: {V4_DIR}")

if __name__ == "__main__":
    finalize_v4()
