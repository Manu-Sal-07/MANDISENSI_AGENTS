import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import json
from pathlib import Path

# --- CONFIGURATION ---
DATA_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/processed/v4")
MODELS_ROOT = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/models")
LOG_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/logs")

MODELS_ROOT.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- FEATURE ENGINEERING ---
def build_features(df):
    # Group by mandi_id for lag and rolling features
    df = df.sort_values(['mandi_id', 'date'])
    
    # Lag features
    for lag in [1, 3, 7]:
        df[f'price_lag_{lag}'] = df.groupby('mandi_id')['price'].shift(lag)
        df[f'arrivals_lag_{lag}'] = df.groupby('mandi_id')['arrivals'].shift(lag)
        
    # Rolling features
    df['rolling_mean_7'] = df.groupby('mandi_id')['price'].transform(lambda x: x.rolling(7).mean())
    df['rolling_std_7'] = df.groupby('mandi_id')['price'].transform(lambda x: x.rolling(7).std())
    
    # Time features
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    
    # Drop rows with NaNs from lags/rolling
    df = df.dropna().reset_index(drop=True)
    
    return df

# --- TRAINING PIPELINE ---
def train_agents_for_commodity(comm_path):
    commodity = comm_path.stem
    print(f"--- Training Agents for {commodity.upper()} ---")
    
    # Load full dataset for lag calculation
    df = pd.read_csv(comm_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Feature Engineering (Done on full set to avoid edge artifacts)
    df = build_features(df)
    
    # Mandi Encoding
    le = LabelEncoder()
    df['mandi_encoded'] = le.fit_transform(df['mandi_id'])
    
    # Targets
    df['target_price'] = df.groupby('mandi_id')['price'].shift(-1)
    df['target_arrivals'] = df.groupby('mandi_id')['arrivals'].shift(-1)
    
    # Drop rows where target is NaN (last row of each mandi)
    df = df.dropna(subset=['target_price', 'target_arrivals'])
    
    # Split using the 'split' column
    # Step 1 logic: We can train on all is_valid_training == 1
    # But we validate on split == "val"
    train_df = df[df['is_valid_training'] == 1]
    val_df = df[df['split'] == 'val']
    
    if train_df.empty or val_df.empty:
        print(f"  [ERROR] Insufficient data for {commodity}. Train: {len(train_df)}, Val: {len(val_df)}")
        return None
    
    features = [
        'mandi_encoded', 'price_lag_1', 'price_lag_3', 'price_lag_7',
        'arrivals_lag_1', 'arrivals_lag_3', 'arrivals_lag_7',
        'rolling_mean_7', 'rolling_std_7', 'month', 'day_of_week',
        'is_unstable', 'is_missing', 'arrivals_log'
    ]
    
    # 1. Price Model
    print(f"  Training Price Model...")
    price_model = xgb.XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
    price_model.fit(train_df[features], train_df['target_price'], 
                   eval_set=[(val_df[features], val_df['target_price'])],
                   early_stopping_rounds=20, verbose=False)
    
    # 2. Arrival Model
    print(f"  Training Arrival Model...")
    arrival_model = xgb.XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
    arrival_model.fit(train_df[features], train_df['target_arrivals'],
                     eval_set=[(val_df[features], val_df['target_arrivals'])],
                     early_stopping_rounds=20, verbose=False)
    
    # Evaluation
    val_pred_price = price_model.predict(val_df[features])
    val_pred_arrivals = arrival_model.predict(val_df[features])
    
    metrics = {
        "price": {
            "mae": mean_absolute_error(val_df['target_price'], val_pred_price),
            "rmse": np.sqrt(mean_squared_error(val_df['target_price'], val_pred_price)),
            "mape": np.mean(np.abs((val_df['target_price'] - val_pred_price) / val_df['target_price'])) * 100
        },
        "arrivals": {
            "mae": mean_absolute_error(val_df['target_arrivals'], val_pred_arrivals),
            "rmse": np.sqrt(mean_squared_error(val_df['target_arrivals'], val_pred_arrivals))
        }
    }
    
    # Save Artifacts
    comm_model_dir = MODELS_ROOT / commodity
    comm_model_dir.mkdir(parents=True, exist_ok=True)
    
    joblib.dump(price_model, comm_model_dir / "price_model.pkl")
    joblib.dump(arrival_model, comm_model_dir / "arrival_model.pkl")
    joblib.dump(le, comm_model_dir / "mandi_encoder.pkl")
    
    with open(comm_model_dir / "feature_columns.json", "w") as f:
        json.dump(features, f)
        
    with open(comm_model_dir / "metrics.json", "w") as f:
        json.dump(metrics, f)
        
    # Explainability: Feature Importance
    importance = {
        "price": price_model.get_booster().get_score(importance_type='weight'),
        "arrivals": arrival_model.get_booster().get_score(importance_type='weight')
    }
    with open(comm_model_dir / "importance.json", "w") as f:
        json.dump(importance, f)
        
    print(f"  Completed. Price MAPE: {metrics['price']['mape']:.2f}%")
    return metrics

def run_all_training():
    all_metrics = {}
    for comm_path in DATA_DIR.glob("*.csv"):
        m = train_agents_for_commodity(comm_path)
        all_metrics[comm_path.stem] = m
        
    # Final Report
    report_rows = []
    for comm, m in all_metrics.items():
        report_rows.append({
            "commodity": comm,
            "price_mae": m["price"]["mae"],
            "price_mape": m["price"]["mape"],
            "arrival_mae": m["arrivals"]["mae"]
        })
    pd.DataFrame(report_rows).to_csv(LOG_DIR / "agent_training_report.csv", index=False)

if __name__ == "__main__":
    run_all_training()
