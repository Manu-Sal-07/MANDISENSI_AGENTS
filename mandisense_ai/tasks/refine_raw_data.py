import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
V1_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/raw/v1")
V2_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/raw/v2")
CONFIG_PATH = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/config/mandi_master.csv")
LOG_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/logs")

V2_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- STEP 1: MANDI ID REFINEMENT ---
def refine_mandi_master():
    df = pd.read_csv(CONFIG_PATH)
    
    def get_specific_id(row):
        base_id = row['mandi_id']
        if base_id == "bangalore":
            return "bangalore_yeshwanthpur"
        return f"{base_id}_apmc"
    
    df['old_mandi_id'] = df['mandi_id']
    df['mandi_id'] = df.apply(get_specific_id, axis=1)
    
    # Save refined master
    df.to_csv(CONFIG_PATH, index=False)
    print(f"Refined mandi_master.csv with specific identifiers.")
    return df

# --- STEP 5: SCHEMA ENFORCEMENT ---
STRICT_SCHEMA = {
    "date": "datetime64[ns]",
    "mandi_id": "string",
    "commodity": "string",
    "modal_price": "float64",
    "arrivals": "float64"
}

def refine_datasets(mandi_master):
    mandi_id_map = dict(zip(mandi_master['old_mandi_id'], mandi_master['mandi_id']))
    commodities = [d.name for d in V1_DIR.iterdir() if d.is_dir()]
    
    quality_records = []
    removal_log = []
    
    # Compute global window for temporal alignment
    all_start_dates = []
    all_end_dates = []
    
    # First pass: collect dates and validate basics
    temp_dfs = {} # (comm, old_id) -> df
    
    for comm in commodities:
        comm_v1_dir = V1_DIR / comm
        for csv_file in comm_v1_dir.glob("*.csv"):
            old_mandi_id = csv_file.stem
            if old_mandi_id not in mandi_id_map:
                continue
                
            df = pd.read_csv(csv_file)
            
            # Basic validation
            if df.empty:
                removal_log.append({"commodity": comm, "mandi_id": old_mandi_id, "reason": "Empty file"})
                continue
            
            # Enforce Schema
            try:
                df['date'] = pd.to_datetime(df['date'])
                df['mandi_id'] = mandi_id_map[old_mandi_id]
                df['commodity'] = comm
                df['modal_price'] = pd.to_numeric(df['modal_price'], errors='coerce')
                df['arrivals'] = pd.to_numeric(df['arrivals'], errors='coerce')
                
                df = df.dropna(subset=['date', 'modal_price', 'arrivals'])
                df = df[list(STRICT_SCHEMA.keys())] # Enforce column order
                
                # Deduplicate
                df = df.drop_duplicates(subset=['date'])
                df = df.sort_values('date')
                
                total_records = len(df)
                start_date = df['date'].min()
                end_date = df['date'].max()
                
                # STEP 2: DENSITY FILTER
                full_range = pd.date_range(start_date, end_date)
                continuity = (total_records / len(full_range)) * 100
                
                if total_records < 300 or continuity < 90:
                    removal_log.append({
                        "commodity": comm, 
                        "mandi_id": mandi_id_map[old_mandi_id], 
                        "reason": f"Density below threshold (Records: {total_records}, Continuity: {continuity:.1f}%)"
                    })
                    continue
                
                # STEP 3: MISSING DAY ANALYSIS
                gaps = df['date'].diff().dt.days - 1
                max_gap = gaps.max() if not gaps.dropna().empty else 0
                
                is_unstable = max_gap > 3
                
                temp_dfs[(comm, old_mandi_id)] = {
                    "df": df,
                    "max_gap": max_gap,
                    "continuity": continuity,
                    "is_unstable": is_unstable
                }
                
                all_start_dates.append(start_date)
                all_end_dates.append(end_date)
                
            except Exception as e:
                removal_log.append({"commodity": comm, "mandi_id": old_mandi_id, "reason": f"Schema error: {e}"})

    if not all_start_dates:
        print("No valid data found after filtering.")
        return

    # STEP 4: TEMPORAL ALIGNMENT
    global_start = max(all_start_dates)
    global_end = min(all_end_dates)
    global_range = pd.date_range(global_start, global_end)
    
    print(f"Global alignment window: {global_start.date()} to {global_end.date()}")
    
    # Second pass: Reindex and Save v2
    for (comm, old_id), info in temp_dfs.items():
        df = info["df"]
        new_id = mandi_id_map[old_id]
        
        # Reindex to full global range
        df = df.set_index('date')
        df = df.reindex(global_range)
        
        # Re-populate metadata columns that were lost in reindex (for rows that existed)
        df['mandi_id'] = new_id
        df['commodity'] = comm
        
        df = df.reset_index().rename(columns={'index': 'date'})
        
        # Save v2
        comm_v2_dir = V2_DIR / comm
        comm_v2_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(comm_v2_dir / f"{new_id}.csv", index=False)
        
        # Quality records
        missing_days = df['modal_price'].isna().sum()
        quality_records.append({
            "commodity": comm,
            "mandi_id": new_id,
            "total_records": len(df) - missing_days,
            "start_date": global_start.strftime("%Y-%m-%d"),
            "end_date": global_end.strftime("%Y-%m-%d"),
            "missing_days": missing_days,
            "max_gap": info["max_gap"],
            "continuity": info["continuity"],
            "is_unstable": info["is_unstable"]
        })

    # Save reports
    pd.DataFrame(quality_records).to_csv(LOG_DIR / "data_quality_report_v2.csv", index=False)
    pd.DataFrame(removal_log).to_csv(LOG_DIR / "removed_pairs_log.csv", index=False)
    
    # STEP 3: MISSING DAY REPORT (Specific version)
    missing_day_report = pd.DataFrame(quality_records)[["commodity", "mandi_id", "missing_days", "max_gap", "is_unstable"]]
    missing_day_report.to_csv(LOG_DIR / "missing_day_analysis.csv", index=False)

    print(f"Refinement Complete. v2 data saved to {V2_DIR}")

if __name__ == "__main__":
    master_df = refine_mandi_master()
    refine_datasets(master_df)
