import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.metrics import accuracy_score

# --- CONFIGURATION ---
DATA_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/processed/v4")
MODELS_ROOT = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/models")
LOG_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/logs")
V2 = "v2"
V3 = "v3"

def build_inference_features(df):
    # Same as training pipeline v2
    df = df.sort_values(['mandi_id', 'date'])
    for lag in [1, 3, 7]:
        df[f'price_lag_{lag}'] = df.groupby('mandi_id')['price'].shift(lag)
        df[f'arrivals_lag_{lag}'] = df.groupby('mandi_id')['arrivals'].shift(lag)
    df['arrival_trend'] = df['arrivals_lag_1'] - df['arrivals_lag_3']
    df['rolling_mean_7'] = df.groupby('mandi_id')['price'].transform(lambda x: x.rolling(7).mean())
    df['volatility'] = df.groupby('mandi_id')['price'].transform(lambda x: x.rolling(7).std())
    mandi_vol_thresholds = df.groupby('mandi_id')['volatility'].transform('median')
    df['volatility_regime'] = (df['volatility'] > mandi_vol_thresholds).astype(int)
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    return df.dropna()

def calibrate_commodity(comm_path):
    commodity = comm_path.stem
    print(f"--- Calibrating {commodity.upper()} ---")
    
    # Load v2 artifacts
    v2_dir = MODELS_ROOT / commodity / V2
    v3_dir = MODELS_ROOT / commodity / V3
    v3_dir.mkdir(parents=True, exist_ok=True)
    
    price_model = joblib.load(v2_dir / "price_model.pkl")
    mandi_encoder = joblib.load(v2_dir / "mandi_encoder.pkl")
    features = json.load(open(v2_dir / "feature_columns.json"))
    
    # Load and process data
    df = pd.read_csv(comm_path)
    df['date'] = pd.to_datetime(df['date'])
    df = build_inference_features(df)
    df['mandi_encoded'] = mandi_encoder.transform(df['mandi_id'])
    
    # Validation set (v2 used last window for validation)
    val_df = df[df['split'] == 'val'].copy()
    val_df['target_price'] = df.groupby('mandi_id')['price'].shift(-1)
    val_df = val_df.dropna(subset=['target_price'])
    
    # Predictions
    preds = price_model.predict(val_df[features])
    val_df['pred_price'] = preds
    val_df['error_pct'] = np.abs(val_df['target_price'] - val_df['pred_price']) / val_df['target_price']
    
    # STEP 1: CONFIDENCE CALIBRATION
    # Raw confidence heuristic (inverse volatility)
    val_df['raw_confidence'] = 1 / (1 + (val_df['volatility'] / (val_df['rolling_mean_7'] + 1e-6)))
    
    # Create buckets
    val_df['bucket'] = pd.cut(val_df['raw_confidence'], bins=np.linspace(0.5, 1.0, 6))
    calibration_map = {}
    for bucket, group in val_df.groupby('bucket'):
        if not group.empty:
            avg_error = group['error_pct'].mean()
            # Calibrated confidence = 1 - expected error
            calibration_map[str(bucket)] = float(max(0.5, 1 - avg_error))
            
    # STEP 2: DIRECTIONAL ACCURACY
    val_df['direction_pred'] = np.sign(val_df['pred_price'] - val_df['price'])
    val_df['direction_actual'] = np.sign(val_df['target_price'] - val_df['price'])
    val_df['direction_correct'] = (val_df['direction_pred'] == val_df['direction_actual']).astype(int)
    
    mandi_dir_acc = val_df.groupby('mandi_id')['direction_correct'].mean().to_dict()
    global_dir_acc = val_df['direction_correct'].mean()
    
    # STEP 6: DRIFT MONITORING (Initial baseline)
    # Just save the current MAPE as the drift baseline
    current_mape = val_df['error_pct'].mean() * 100
    
    # Save Artifacts to v3
    joblib.dump(price_model, v3_dir / "model.pkl")
    # Also save arrival model
    arrival_model = joblib.load(v2_dir / "arrival_model.pkl")
    joblib.dump(arrival_model, v3_dir / "arrival_model.pkl")
    joblib.dump(mandi_encoder, v3_dir / "mandi_encoder.pkl")
    
    with open(v3_dir / "calibrated_confidence_map.json", "w") as f:
        json.dump(calibration_map, f)
        
    with open(v3_dir / "feature_columns.json", "w") as f:
        json.dump(features, f)
        
    pd.DataFrame(list(mandi_dir_acc.items()), columns=['mandi_id', 'direction_accuracy']).to_csv(v3_dir / "directional_accuracy.csv", index=False)
    
    summary = {
        "global_mape": current_mape,
        "global_direction_accuracy": global_dir_acc,
        "calibration_buckets": len(calibration_map)
    }
    with open(v3_dir / "metrics_summary.json", "w") as f:
        json.dump(summary, f)
        
    # Copy per_mandi_metrics.csv
    pd.read_csv(v2_dir / "per_mandi_metrics.csv").to_csv(v3_dir / "per_mandi_metrics.csv", index=False)
    
    print(f"  Calibrated. Global Direction Accuracy: {global_dir_acc:.2%}")
    return {"commodity": commodity, "mape": current_mape, "dir_acc": global_dir_acc}

def run_calibration_pipeline():
    results = []
    for comm_path in DATA_DIR.glob("*.csv"):
        res = calibrate_commodity(comm_path)
        results.append(res)
    
    pd.DataFrame(results).to_csv(LOG_DIR / "model_drift_monitor.csv", index=False)
    print("\nCalibration Complete. Artifacts stored in v3.")

if __name__ == "__main__":
    run_calibration_pipeline()
