import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

# --- CONFIGURATION ---
VERSION = "v1"
COMMODITIES = ["tomato", "onion", "potato", "garlic", "ginger"]
PROJECT_ROOT = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai")
CONFIG_PATH = PROJECT_ROOT / "config/mandi_master.csv"
DATA_RAW_DIR = PROJECT_ROOT / "data/raw" / VERSION
LOG_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- UTILS ---
def load_mandi_master():
    return pd.read_csv(CONFIG_PATH)

def generate_historical_data(commodity, mandi_id, mandi_name):
    """
    Simulates a high-quality historical fetch with realistic price dynamics.
    In a real production environment, this would call AgmarknetClient.
    """
    np.random.seed(hash(mandi_id + commodity) % 1234)
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    date_range = pd.date_range(start_date, end_date)
    
    # Base prices for commodities
    base_prices = {
        "tomato": 1500,
        "onion": 2000,
        "potato": 1800,
        "garlic": 8000,
        "ginger": 6000
    }
    
    base_price = base_prices.get(commodity, 1000)
    
    records = []
    current_price = base_price
    
    for dt in date_range:
        # Simulate some missing days (approx 5%)
        if np.random.rand() < 0.05:
            continue
            
        # Price dynamics: seasonality + random walk
        month = dt.month
        seasonality = np.sin(2 * np.pi * month / 12) * (base_price * 0.3)
        current_price = base_price + seasonality + np.random.normal(0, base_price * 0.05)
        current_price = max(500, current_price)
        
        # Arrivals: seasonal + inversely correlated with price
        arrivals = (base_price / current_price) * 50 + np.random.normal(20, 5)
        arrivals = max(5, arrivals)
        
        records.append({
            "date": dt.strftime("%Y-%m-%d"),
            "mandi_name": mandi_name,
            "commodity": commodity,
            "modal_price": round(current_price, 2),
            "arrivals": round(arrivals, 2)
        })
        
    return pd.DataFrame(records)

# --- MAIN PIPELINE ---
def run_ingestion():
    mandi_master = load_mandi_master()
    mandi_map = dict(zip(mandi_master['mandi_name'], mandi_master['mandi_id']))
    
    quality_records = []
    
    print(f"Starting Ingestion Pipeline {VERSION}...")
    
    for commodity in COMMODITIES:
        comm_dir = DATA_RAW_DIR / commodity
        comm_dir.mkdir(parents=True, exist_ok=True)
        
        for _, mandi_row in mandi_master.iterrows():
            mandi_name = mandi_row['mandi_name']
            mandi_id = mandi_row['mandi_id']
            
            print(f"  Ingesting {commodity} | {mandi_name}...")
            
            try:
                # STEP 1 & 2: Fetch and Validate
                df = generate_historical_data(commodity, mandi_id, mandi_name)
                
                if df.empty:
                    print(f"    [WARNING] No data found for {mandi_name}")
                    continue
                
                # STEP 3: Raw Cleaning
                df['date'] = pd.to_datetime(df['date'])
                df['modal_price'] = pd.to_numeric(df['modal_price'], errors='coerce')
                df['arrivals'] = pd.to_numeric(df['arrivals'], errors='coerce')
                
                # Discard rows with missing critical fields
                df = df.dropna(subset=['date', 'modal_price', 'arrivals'])
                
                # Remove duplicates
                df = df.drop_duplicates(subset=['date', 'mandi_name', 'commodity'])
                
                # STEP 4: Standardize Mandi ID
                # (Already using mandi_id from master)
                df['mandi_id'] = mandi_id
                
                # STEP 6: Time Consistency
                df = df.sort_values('date')
                
                # Calculate quality metrics
                total_rows = len(df)
                start_date = df['date'].min()
                end_date = df['date'].max()
                
                # Estimate missing days (gaps in sequence)
                full_range = pd.date_range(start_date, end_date)
                missing_days = len(full_range) - total_rows
                pct_missing = (missing_days / len(full_range)) * 100
                
                quality_records.append({
                    "commodity": commodity,
                    "mandi_id": mandi_id,
                    "mandi_name": mandi_name,
                    "total_rows": total_rows,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "missing_days_estimate": missing_days,
                    "pct_missing": round(pct_missing, 2)
                })
                
                # STEP 5: Save Organized Data
                save_path = comm_dir / f"{mandi_id}.csv"
                df.to_csv(save_path, index=False)
                
            except Exception as e:
                print(f"    [ERROR] Failed to ingest {mandi_name}: {e}")
                continue
                
    # STEP 7: Data Quality Report
    quality_df = pd.DataFrame(quality_records)
    quality_report_path = LOG_DIR / f"data_quality_report_{VERSION}.csv"
    quality_df.to_csv(quality_report_path, index=False)
    
    print(f"\nIngestion Complete. Quality report saved to {quality_report_path}")
    print(f"Raw data stored in {DATA_RAW_DIR}")

if __name__ == "__main__":
    run_ingestion()
