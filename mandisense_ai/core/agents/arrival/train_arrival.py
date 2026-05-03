import os
import pandas as pd
import numpy as np
import pickle
import json
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import mean_absolute_error
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\data\processed"
MODELS_ROOT = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\models\arrival"
COMMODITIES = ["tomato", "onion", "potato", "dry_chillis", "garlic"]

def train_commodity_arrival(commodity):
    logger.info(f"--- Training Arrival Volume Agent for {commodity.upper()} ---")
    data_dir = os.path.join(PROCESSED_DATA_DIR, commodity)
    
    # 1. Load Data
    X_train = pd.read_csv(os.path.join(data_dir, "X_train.csv"))
    y_train = pd.read_csv(os.path.join(data_dir, "y_train.csv"))
    X_val = pd.read_csv(os.path.join(data_dir, "X_val.csv"))
    y_val = pd.read_csv(os.path.join(data_dir, "y_val.csv"))
    
    with open(os.path.join(data_dir, "feature_config.json"), "r") as f:
        feature_config = json.load(f)

    # Focus strictly on 7-day target for short-term dynamics
    target_name = "target_7d_pct"
    y_train_h = y_train[target_name]
    y_val_h = y_val[target_name]
    
    # 2. Define Model Ensemble
    models = {
        "rf": RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42),
        "xgb": XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42),
        "gb": GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42),
        "ridge": Ridge(alpha=1.0),
        "lasso": Lasso(alpha=0.1)
    }
    
    trained_models = []
    maes = []
    model_names = []
    
    # 3. Training and MAE Validation (NO MAPE)
    logger.info("  Training ensemble models...")
    for name, model in models.items():
        model.fit(X_train, y_train_h)
        preds = model.predict(X_val)
        
        # Sanity clip predictions
        preds = np.clip(preds, -25, 25)
        
        mae = mean_absolute_error(y_val_h, preds)
        
        trained_models.append(model)
        maes.append(mae)
        model_names.append(name)
        logger.info(f"    - {name}: MAE = {mae:.4f}")
        
    # 4. Ensemble Weighting (Inverse MAE)
    # Prevent divide by zero
    inv_maes = [1.0 / (m + 1e-6) for m in maes]
    total_inv = sum(inv_maes)
    raw_weights = [inv / total_inv for inv in inv_maes]
    
    # Enforce maximum weight of 0.6
    weights = []
    for w in raw_weights:
        if w > 0.6:
            weights.append(0.6)
        else:
            weights.append(w)
            
    # Renormalize after capping
    total_capped = sum(weights)
    weights = [w / total_capped for w in weights]
    
    logger.info(f"  Final Ensemble Weights: {dict(zip(model_names, [round(w, 3) for w in weights]))}")
    
    overall_mae = np.average(maes, weights=weights)
    logger.info(f"  Weighted Ensemble MAE: {overall_mae:.4f}")

    # 5. Build Final Bundle (Contract v1)
    bundle = {
        "version": "v1",
        "commodity": commodity,
        "models": trained_models, # List of objects
        "weights": weights,       # Normalized weights
        "feature_config": feature_config,
        "target": target_name,
        "trained_at": pd.Timestamp.now().isoformat()
    }
    
    # 6. Save Artifacts
    output_dir = os.path.join(MODELS_ROOT, commodity)
    os.makedirs(output_dir, exist_ok=True)
    
    bundle_path = os.path.join(output_dir, "bundle.pkl")
    with open(bundle_path, "wb") as f:
        pickle.dump(bundle, f)
        
    metrics = {
        "commodity": commodity,
        "cv_mae": float(overall_mae),
        "models_used": model_names,
        "weights": weights,
        "trained_on": pd.Timestamp.now().strftime("%Y-%m-%d")
    }
    
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
        
    # 7. Load Test (Mandatory)
    logger.info("  Performing Load Test...")
    with open(bundle_path, "rb") as f:
        loaded_bundle = pickle.load(f)
    
    assert loaded_bundle["version"] == "v1"
    
    # Dummy prediction test
    test_input = X_val.iloc[:1]
    ensemble_pred = 0
    for model, weight in zip(loaded_bundle["models"], loaded_bundle["weights"]):
        ensemble_pred += model.predict(test_input)[0] * weight
        
    assert -25 <= ensemble_pred <= 25, f"Prediction out of bounds: {ensemble_pred}"
    
    logger.info(f"✅ {commodity.upper()} Training and Load Test Successful.")

if __name__ == "__main__":
    for comm in COMMODITIES:
        train_commodity_arrival(comm)
    logger.info("\n🚀 ARRIVAL VOLUME AGENT TRAINING COMPLETE")
