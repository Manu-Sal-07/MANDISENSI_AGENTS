import os
import pandas as pd
import numpy as np
import pickle
import json
from statsmodels.tsa.seasonal import STL
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\data\processed"
MODELS_ROOT = r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\mandisense_ai\models\seasonality"
COMMODITIES = ["tomato", "onion", "potato", "dry_chillis", "garlic"]
HORIZONS = [3, 7, 30]

def train_commodity_seasonality(commodity):
    logger.info(f"--- Training Seasonality Agent for {commodity.upper()} ---")
    data_dir = os.path.join(PROCESSED_DATA_DIR, commodity)
    
    # 1. Load Data
    X_train = pd.read_csv(os.path.join(data_dir, "X_train.csv"))
    y_train = pd.read_csv(os.path.join(data_dir, "y_train.csv"))
    X_val = pd.read_csv(os.path.join(data_dir, "X_val.csv"))
    y_val = pd.read_csv(os.path.join(data_dir, "y_val.csv"))
    
    # price_train now has columns [date, mandi, price]
    price_train_raw = pd.read_csv(os.path.join(data_dir, "price_train.csv"), parse_dates=['date'])
    
    with open(os.path.join(data_dir, "feature_config.json"), "r") as f:
        feature_config = json.load(f)

    # 2. STL Decomposition (on a representative mandi or per-mandi if needed)
    # For now, we pick the first mandi to get the base structural components
    first_mandi = price_train_raw['mandi'].iloc[0]
    price_train_single = price_train_raw[price_train_raw['mandi'] == first_mandi].set_index('date')['price'].resample('D').ffill()
    
    logger.info(f"  Performing STL decomposition on {first_mandi} mandi...")
    res = STL(price_train_single, period=365, robust=True).fit()
    stl_components = {
        "trend": res.trend.to_dict(),
        "seasonal": res.seasonal.to_dict(),
        "residual": res.resid.to_dict()
    }
    
    # 3. Model Training per Horizon
    horizon_models = {}
    metrics = {}
    
    for h in HORIZONS:
        target_name = f"target_{h}d_pct"
        y_train_h = y_train[target_name]
        y_val_h = y_val[target_name]
        
        logger.info(f"  Training models for {h}-day horizon...")
        
        # Define models
        models = {
            "rf": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            "xgb": XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42),
            "ridge": Ridge(alpha=1.0)
        }
        
        trained_models = {}
        for name, model in models.items():
            model.fit(X_train, y_train_h)
            preds = model.predict(X_val)
            mae = mean_absolute_error(y_val_h, preds)
            
            trained_models[name] = model
            metrics[f"{h}d_{name}_mae"] = float(mae)
            logger.info(f"    - {name}: MAE = {mae:.4f}")
            
        horizon_models[h] = trained_models

    # 4. Build Final Bundle
    bundle = {
        "version": "v1",
        "commodity": commodity,
        "models": horizon_models, # Nested: {horizon: {model_name: obj}}
        "stl_components": stl_components,
        "feature_config": feature_config,
        "horizons": HORIZONS,
        "trained_at": pd.Timestamp.now().isoformat()
    }
    
    # 5. Save Artifacts
    output_dir = os.path.join(MODELS_ROOT, commodity)
    os.makedirs(output_dir, exist_ok=True)
    
    bundle_path = os.path.join(output_dir, "bundle.pkl")
    with open(bundle_path, "wb") as f:
        pickle.dump(bundle, f)
        
    metadata = {
        "commodity": commodity,
        "models_used": ["rf", "xgb", "ridge"],
        "horizons": HORIZONS,
        "metrics": metrics,
        "trained_on": pd.Timestamp.now().strftime("%Y-%m-%d")
    }
    
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    # 6. Load Test
    logger.info(f"  Performing Load Test...")
    with open(bundle_path, "rb") as f:
        loaded_bundle = pickle.load(f)
    
    # Dummy prediction test (first row of validation)
    test_input = X_val.iloc[:1]
    for h in HORIZONS:
        test_pred = loaded_bundle["models"][h]["rf"].predict(test_input)
        assert len(test_pred) == 1
    
    logger.info(f"✅ {commodity.upper()} Training and Load Test Successful.")

if __name__ == "__main__":
    for comm in COMMODITIES:
        train_commodity_seasonality(comm)
    logger.info("\n🚀 SEASONALITY AGENT TRAINING COMPLETE")
