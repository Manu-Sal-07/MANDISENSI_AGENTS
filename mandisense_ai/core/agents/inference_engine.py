import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
MODELS_ROOT = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/models")
DATA_V4_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/processed/v4")

class InferenceEngine:
    def __init__(self):
        self.models = {}
        self._load_all_models()
        
    def _load_all_models(self):
        for comm_dir in MODELS_ROOT.iterdir():
            if comm_dir.is_dir():
                comm = comm_dir.name
                try:
                    self.models[comm] = {
                        "price_model": joblib.load(comm_dir / "price_model.pkl"),
                        "arrival_model": joblib.load(comm_dir / "arrival_model.pkl"),
                        "mandi_encoder": joblib.load(comm_dir / "mandi_encoder.pkl"),
                        "features": json.load(open(comm_dir / "feature_columns.json")),
                        "importance": json.load(open(comm_dir / "importance.json"))
                    }
                except Exception as e:
                    print(f"Failed to load models for {comm}: {e}")

    def predict(self, commodity, mandi_id, target_date=None):
        if commodity not in self.models:
            raise ValueError(f"No models found for commodity: {commodity}")
        
        bundle = self.models[commodity]
        
        # Load historical data for feature engineering
        data_path = DATA_V4_DIR / f"{commodity}.csv"
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        
        mandi_df = df[df['mandi_id'] == mandi_id].sort_values('date')
        if mandi_df.empty:
            raise ValueError(f"No data found for mandi: {mandi_id} in {commodity}")
            
        # Build features for the latest available point
        # In a real system, we'd use the provided target_date and look back
        latest = mandi_df.iloc[-1:].copy()
        
        # We need the last 7 days for rolling features
        history = mandi_df.tail(14).copy() # Extra buffer
        
        # Construct the inference row
        inf_row = latest.copy()
        
        # Manual Feature Engineering for Inference
        # (Must match build_features in training_pipeline.py)
        inf_row['price_lag_1'] = history['price'].iloc[-1]
        inf_row['price_lag_3'] = history['price'].iloc[-3]
        inf_row['price_lag_7'] = history['price'].iloc[-7]
        
        inf_row['arrivals_lag_1'] = history['arrivals'].iloc[-1]
        inf_row['arrivals_lag_3'] = history['arrivals'].iloc[-3]
        inf_row['arrivals_lag_7'] = history['arrivals'].iloc[-7]
        
        inf_row['rolling_mean_7'] = history['price'].tail(7).mean()
        inf_row['rolling_std_7'] = history['price'].tail(7).std()
        
        inf_row['month'] = latest['date'].dt.month.iloc[0]
        inf_row['day_of_week'] = latest['date'].dt.dayofweek.iloc[0]
        
        try:
            inf_row['mandi_encoded'] = bundle["mandi_encoder"].transform([mandi_id])[0]
        except ValueError:
            inf_row['mandi_encoded'] = -1 # Unknown
            
        # Predict
        features = bundle["features"]
        X = inf_row[features]
        
        pred_price = bundle["price_model"].predict(X)[0]
        pred_arrivals = bundle["arrival_model"].predict(X)[0]
        
        # Explainability
        importance = bundle["importance"]["price"]
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Simple Logic for explainability text
        price_trend = "upward" if inf_row['price_lag_1'].iloc[0] > inf_row['price_lag_3'].iloc[0] else "downward"
        arrival_trend = "declining" if inf_row['arrivals_lag_1'].iloc[0] < inf_row['arrivals_lag_3'].iloc[0] else "rising"
        
        explanation = f"In {mandi_id}, price is expected to be around {pred_price:.2f} Rs. "
        explanation += f"The recent price trend is {price_trend}, while arrivals are {arrival_trend}. "
        explanation += f"Top signals: {', '.join([f[0] for f in top_features])}."

        return {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "target_date": str(latest['date'].iloc[0].date()),
            "predicted_price": float(pred_price),
            "predicted_arrivals": float(pred_arrivals),
            "explanation": explanation,
            "confidence": 0.85 # Placeholder for now
        }

if __name__ == "__main__":
    engine = InferenceEngine()
    print("--- MANDISENSE INFERENCE TEST ---")
    res = engine.predict("tomato", "kolar_apmc")
    print(json.dumps(res, indent=2))
