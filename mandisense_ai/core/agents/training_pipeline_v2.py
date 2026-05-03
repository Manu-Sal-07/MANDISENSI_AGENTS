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
VERSION = "v2"

MODELS_ROOT.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- WALK-FORWARD WINDOWS ---
WF_WINDOWS = [
    ("2024-06-30", "2024-12-31"),
    ("2024-12-31", "2025-06-30"),
    ("2025-06-30", "2026-01-31")
]

def build_features_v2(df):
    df = df.sort_values(['mandi_id', 'date'])
    
    # Lag features
    for lag in [1, 3, 7]:
        df[f'price_lag_{lag}'] = df.groupby('mandi_id')['price'].shift(lag)
        df[f'arrivals_lag_{lag}'] = df.groupby('mandi_id')['arrivals'].shift(lag)
        
    # Arrival Trend
    df['arrival_trend'] = df['arrivals_lag_1'] - df['arrivals_lag_3']
    
    # Rolling features
    df['rolling_mean_7'] = df.groupby('mandi_id')['price'].transform(lambda x: x.rolling(7).mean())
    df['volatility'] = df.groupby('mandi_id')['price'].transform(lambda x: x.rolling(7).std())
    
    # STEP 5: Volatility Regime
    # Compute global threshold for volatility per mandi
    mandi_vol_thresholds = df.groupby('mandi_id')['volatility'].transform('median')
    df['volatility_regime'] = (df['volatility'] > mandi_vol_thresholds).astype(int)
    
    # Time features
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    
    df = df.dropna().reset_index(drop=True)
    return df

def train_refined_agents(comm_path):
    commodity = comm_path.stem
    print(f"--- Refinement Training (v2) for {commodity.upper()} ---")
    
    df = pd.read_csv(comm_path)
    df['date'] = pd.to_datetime(df['date'])
    df = build_features_v2(df)
    
    le = LabelEncoder()
    df['mandi_encoded'] = le.fit_transform(df['mandi_id'])
    
    df['target_price'] = df.groupby('mandi_id')['price'].shift(-1)
    df['target_arrivals'] = df.groupby('mandi_id')['arrivals'].shift(-1)
    df = df.dropna(subset=['target_price', 'target_arrivals'])
    
    features = [
        'mandi_encoded', 'price_lag_1', 'price_lag_3', 'price_lag_7',
        'arrivals_lag_1', 'arrivals_lag_3', 'arrivals_lag_7',
        'arrival_trend', 'rolling_mean_7', 'volatility', 'volatility_regime',
        'month', 'day_of_week', 'is_unstable', 'is_missing', 'arrivals_log'
    ]
    
    # STEP 1: WALK-FORWARD VALIDATION
    wf_results = []
    
    for i, (train_end, val_end) in enumerate(WF_WINDOWS):
        train_slice = df[df['date'] <= pd.Timestamp(train_end)]
        val_slice = df[(df['date'] > pd.Timestamp(train_end)) & (df['date'] <= pd.Timestamp(val_end))]
        
        if train_slice.empty or val_slice.empty:
            continue
            
        model = xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42)
        model.fit(train_slice[features], train_slice['target_price'], verbose=False)
        
        preds = model.predict(val_slice[features])
        mape = np.mean(np.abs((val_slice['target_price'] - preds) / val_slice['target_price'])) * 100
        rmse = np.sqrt(mean_squared_error(val_slice['target_price'], preds))
        
        wf_results.append({"window": i+1, "mape": mape, "rmse": rmse})
        print(f"  Window {i+1}: MAPE = {mape:.2f}%")

    # Final Model Training (on everything up to train/val split for inference)
    final_train_end = WF_WINDOWS[-1][0]
    final_train = df[df['date'] <= pd.Timestamp(final_train_end)]
    final_val = df[df['date'] > pd.Timestamp(final_train_end)]
    
    price_model = xgb.XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
    price_model.fit(final_train[features], final_train['target_price'],
                   eval_set=[(final_val[features], final_val['target_price'])],
                   early_stopping_rounds=20, verbose=False)
    
    arrival_model = xgb.XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
    arrival_model.fit(final_train[features], final_train['target_arrivals'],
                     eval_set=[(final_val[features], final_val['target_arrivals'])],
                     early_stopping_rounds=20, verbose=False)
    
    # STEP 2 & 3: PER-MANDI METRICS & BASELINE
    final_preds = price_model.predict(final_val[features])
    final_val = final_val.copy()
    final_val['pred_price'] = final_preds
    final_val['baseline_pred'] = final_val['price_lag_1']
    
    mandi_metrics = []
    error_diagnostics = []
    
    for mandi in final_val['mandi_id'].unique():
        m_slice = final_val[final_val['mandi_id'] == mandi]
        
        mape = np.mean(np.abs((m_slice['target_price'] - m_slice['pred_price']) / m_slice['target_price'])) * 100
        baseline_mape = np.mean(np.abs((m_slice['target_price'] - m_slice['baseline_pred']) / m_slice['target_price'])) * 100
        rmse = np.sqrt(mean_squared_error(m_slice['target_price'], m_slice['pred_price']))
        
        mandi_metrics.append({
            "commodity": commodity,
            "mandi_id": mandi,
            "MAPE": round(mape, 4),
            "baseline_MAPE": round(baseline_mape, 4),
            "RMSE": round(rmse, 4),
            "improvement_pct": round(((baseline_mape - mape) / baseline_mape) * 100, 2)
        })
        
        # Error diagnostics
        high_error = m_slice[np.abs(m_slice['target_price'] - m_slice['pred_price']) / m_slice['target_price'] > 0.15]
        for _, row in high_error.iterrows():
            error_diagnostics.append({
                "commodity": commodity,
                "date": row['date'],
                "mandi_id": mandi,
                "error_pct": round(np.abs(row['target_price'] - row['pred_price']) / row['target_price'] * 100, 2),
                "volatility": row['volatility'],
                "is_unstable": row['is_unstable']
            })

    # Save v2
    comm_v2_dir = MODELS_ROOT / commodity / VERSION
    comm_v2_dir.mkdir(parents=True, exist_ok=True)
    
    joblib.dump(price_model, comm_v2_dir / "price_model.pkl")
    joblib.dump(arrival_model, comm_v2_dir / "arrival_model.pkl")
    joblib.dump(le, comm_v2_dir / "mandi_encoder.pkl")
    
    with open(comm_v2_dir / "feature_columns.json", "w") as f:
        json.dump(features, f)
        
    summary = {
        "avg_mape": np.mean([r['mape'] for r in wf_results]),
        "avg_rmse": np.mean([r['rmse'] for r in wf_results]),
        "wf_results": wf_results,
        "baseline_improvement_avg": np.mean([m['improvement_pct'] for m in mandi_metrics])
    }
    with open(comm_v2_dir / "metrics_summary.json", "w") as f:
        json.dump(summary, f)
        
    pd.DataFrame(mandi_metrics).to_csv(comm_v2_dir / "per_mandi_metrics.csv", index=False)
    
    return mandi_metrics, error_diagnostics

def run_refinement_training():
    all_mandi_metrics = []
    all_diagnostics = []
    
    for comm_path in DATA_DIR.glob("*.csv"):
        m_metrics, diag = train_refined_agents(comm_path)
        all_mandi_metrics.extend(m_metrics)
        all_diagnostics.extend(diag)
        
    pd.DataFrame(all_mandi_metrics).to_csv(LOG_DIR / "per_mandi_metrics_v2.csv", index=False)
    pd.DataFrame(all_diagnostics).to_csv(LOG_DIR / "error_analysis_v2.csv", index=False)
    print("\nRefinement Training Complete.")

if __name__ == "__main__":
    run_refinement_training()
