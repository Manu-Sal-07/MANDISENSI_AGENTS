import pandas as pd
import numpy as np
import os
import json
from sklearn.preprocessing import StandardScaler

# Constants
RAW_DATA_DIR = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\data\raw"
PROCESSED_DATA_DIR = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\data\processed"

# Mandi Mapping for Encoding
MANDI_MAP = {
    "kolar": 0,
    "lasalgaon": 1,
    "agra": 2,
    "guntur": 3,
    "neemuch": 4,
    "bangalore": 5,
    "unknown": 99
}

COMMODITIES = {
    "tomato": ["agmarknet_Tomato_Kolar.csv"],
    "onion": ["agmarknet_Onion_Lasalgaon.csv"],
    "potato": ["agmarknet_Potato_Agra.csv"],
    "dry_chillis": ["agmarknet_Dry_Chillies_Guntur.csv"],
    "garlic": ["agmarknet_Garlic_Neemuch.csv"]
}

def prepare_commodity_data(name, filenames):
    print(f"--- Preparing Mandi-Aware Data for {name.upper()} ---")
    
    all_data = []
    for filename in filenames:
        path = os.path.join(RAW_DATA_DIR, filename)
        df_mandi = pd.read_csv(path)
        
        # Extract mandi name from filename (e.g., "agmarknet_Tomato_Kolar.csv" -> "kolar")
        mandi_name = filename.split('_')[-1].replace('.csv', '').lower()
        df_mandi['mandi'] = mandi_name
        df_mandi['mandi_id'] = MANDI_MAP.get(mandi_name, MANDI_MAP['unknown'])
        
        # Column Alignment
        df_mandi = df_mandi[['date', 'mandi', 'mandi_id', 'modal_price', 'arrivals_tonnes']].copy()
        df_mandi.columns = ['date', 'mandi', 'mandi_id', 'price', 'arrivals']
        
        # Date Normalization
        df_mandi['date'] = pd.to_datetime(df_mandi['date'])
        df_mandi = df_mandi.sort_values('date').drop_duplicates('date').reset_index(drop=True)
        
        # Mandi-Specific Resampling (to avoid mixing dates between mandis if multiple files existed)
        df_mandi = df_mandi.set_index('date').resample('D').asfreq()
        df_mandi['mandi'] = mandi_name # Fill back categorical
        df_mandi['mandi_id'] = MANDI_MAP.get(mandi_name, MANDI_MAP['unknown'])
        
        # Missing Value Handling (Per Mandi)
        df_mandi['price'] = df_mandi['price'].ffill()
        df_mandi['arrivals'] = df_mandi['arrivals'].fillna(0)
        df_mandi = df_mandi.dropna(subset=['price'])
        
        all_data.append(df_mandi)
        
    # Combine all mandis for this commodity
    df = pd.concat(all_data).reset_index()
    
    # Mandi-Aware Feature Engineering (Grouped by mandi)
    # This prevents lag_1 for Mandi B from using Mandi A's last price
    df = df.sort_values(['mandi', 'date'])
    
    # 1. Multi-Horizon Targets
    for h in [3, 7, 30]:
        df[f'target_{h}d_pct'] = df.groupby('mandi')['price'].shift(-h)
        df[f'target_{h}d_pct'] = (df[f'target_{h}d_pct'] - df['price']) / df['price'] * 100
        df[f'target_{h}d_pct'] = df[f'target_{h}d_pct'].clip(-25, 25)
    
    # 2. Lag Features
    for lag in [1, 3, 7, 14]:
        df[f'lag_{lag}'] = df.groupby('mandi')['price'].shift(lag)
    
    # 3. Rolling Stats
    df['rolling_mean_7d'] = df.groupby('mandi')['price'].transform(lambda x: x.rolling(7).mean())
    df['rolling_std_7d'] = df.groupby('mandi')['price'].transform(lambda x: x.rolling(7).std())
    
    # 4. Arrival Deviation
    df['rolling_arrival_mean'] = df.groupby('mandi')['arrivals'].transform(lambda x: x.rolling(7).mean())
    df['arrival_dev_7d'] = (df['arrivals'] - df['rolling_arrival_mean']) / (df['rolling_arrival_mean'] + 1e-6)
    
    # Drop intermediate columns and NaNs
    df = df.drop(columns=['rolling_arrival_mean'])
    df = df.dropna().copy()
    
    # 5. Encoding
    # mandi_id is already there. We include it in feature_cols.
    
    # 6. Split (ensure temporal consistency across all mandis)
    # For simplicity, we split on date or just use the same percentage
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    # 7. Features and Targets
    target_cols = ['target_3d_pct', 'target_7d_pct', 'target_30d_pct']
    # Include mandi_id in features
    feature_cols = ['mandi_id', 'lag_1', 'lag_3', 'lag_7', 'lag_14', 'rolling_mean_7d', 'rolling_std_7d', 'arrival_dev_7d']
    
    X_train = train_df[feature_cols]
    y_train = train_df[target_cols]
    X_val = val_df[feature_cols]
    y_val = val_df[target_cols]
    
    # 8. Scaling (mandi_id is categorical but small, we can scale it or not. 
    # Usually better not to scale categorical IDs if using trees, but standard for linear.
    # We'll scale everything for simplicity and consistency with the previous pipeline.)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 9. Save
    output_dir = os.path.join(PROCESSED_DATA_DIR, name)
    os.makedirs(output_dir, exist_ok=True)
    
    pd.DataFrame(X_train_scaled, columns=feature_cols).to_csv(os.path.join(output_dir, "X_train.csv"), index=False)
    y_train.to_csv(os.path.join(output_dir, "y_train.csv"), index=False)
    pd.DataFrame(X_val_scaled, columns=feature_cols).to_csv(os.path.join(output_dir, "X_val.csv"), index=False)
    y_val.to_csv(os.path.join(output_dir, "y_val.csv"), index=False)
    
    # STL price data (we take the first mandi or an average if needed, 
    # but the seasonality agent previously took price_train.csv. 
    # We'll provide it per mandi or a representative one.)
    train_df[['date', 'mandi', 'price']].to_csv(os.path.join(output_dir, "price_train.csv"), index=False)
    
    config = {
        "commodity": name,
        "mandi_map": MANDI_MAP,
        "feature_names": feature_cols,
        "targets": target_cols,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "train_rows": len(X_train),
        "val_rows": len(X_val)
    }
    
    with open(os.path.join(output_dir, "feature_config.json"), "w") as f:
        json.dump(config, f, indent=2)
        
    print(f"[OK] {name.upper()} Mandi-Aware Data Ready: {len(df)} total rows.")

if __name__ == "__main__":
    for name, filenames in COMMODITIES.items():
        prepare_commodity_data(name, filenames)
