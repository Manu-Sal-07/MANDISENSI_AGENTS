import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
MODELS_ROOT = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/models")
DATA_V4_DIR = Path("d:/BMS COLL/PROJECT/MS-AI/MS-AI/mandisense_ai/data/processed/v4")
VERSION = "v2"

class RefinedInferenceEngine:
    def __init__(self):
        self.models = {}
        self._load_all_models()
        
    def _load_all_models(self):
        for comm_dir in MODELS_ROOT.iterdir():
            if comm_dir.is_dir():
                v2_dir = comm_dir / VERSION
                if not v2_dir.exists():
                    continue
                comm = comm_dir.name
                try:
                    self.models[comm] = {
                        "price_model": joblib.load(v2_dir / "price_model.pkl"),
                        "arrival_model": joblib.load(v2_dir / "arrival_model.pkl"),
                        "mandi_encoder": joblib.load(v2_dir / "mandi_encoder.pkl"),
                        "features": json.load(open(v2_dir / "feature_columns.json")),
                        "per_mandi_metrics": pd.read_csv(v2_dir / "per_mandi_metrics.csv")
                    }
                except Exception as e:
                    print(f"Failed to load models for {comm} v2: {e}")

    def predict(self, commodity, mandi_id):
        if commodity not in self.models:
            raise ValueError(f"No models found for commodity: {commodity}")
        
        bundle = self.models[commodity]
        
        # Load historical data
        data_path = DATA_V4_DIR / f"{commodity}.csv"
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        
        mandi_df = df[df['mandi_id'] == mandi_id].sort_values('date')
        if mandi_df.empty:
            raise ValueError(f"No data found for mandi: {mandi_id}")
            
        latest = mandi_df.iloc[-1:].copy()
        history = mandi_df.tail(14).copy()
        
        # Feature Engineering (v2)
        inf_row = latest.copy()
        inf_row['price_lag_1'] = history['price'].iloc[-1]
        inf_row['price_lag_3'] = history['price'].iloc[-3]
        inf_row['price_lag_7'] = history['price'].iloc[-7]
        inf_row['arrivals_lag_1'] = history['arrivals'].iloc[-1]
        inf_row['arrivals_lag_3'] = history['arrivals'].iloc[-3]
        inf_row['arrivals_lag_7'] = history['arrivals'].iloc[-7]
        
        inf_row['arrival_trend'] = inf_row['arrivals_lag_1'] - inf_row['arrivals_lag_3']
        inf_row['rolling_mean_7'] = history['price'].tail(7).mean()
        inf_row['volatility'] = history['price'].tail(7).std()
        
        # Volatility Regime
        # (Using local history for simple thresholding at inference)
        mandi_vol_threshold = history['price'].rolling(7).std().median()
        inf_row['volatility_regime'] = 1 if inf_row['volatility'].iloc[0] > mandi_vol_threshold else 0
        
        inf_row['month'] = latest['date'].dt.month.iloc[0]
        inf_row['day_of_week'] = latest['date'].dt.dayofweek.iloc[0]
        
        inf_row['mandi_encoded'] = bundle["mandi_encoder"].transform([mandi_id])[0]
        
        # Predict
        X = inf_row[bundle["features"]]
        pred_price = bundle["price_model"].predict(X)[0]
        pred_arrivals = bundle["arrival_model"].predict(X)[0]
        
        # STEP 4: PREDICTION CONFIDENCE
        # Simple heuristic: inverse of volatility normalized by avg price
        vol = inf_row['volatility'].iloc[0]
        avg_price = inf_row['rolling_mean_7'].iloc[0]
        confidence = 1 / (1 + (vol / (avg_price + 1e-6)))
        confidence = float(np.clip(confidence, 0.5, 0.95)) # Normalize to reasonable range
        
        # Per-mandi reliability adjustment
        m_metrics = bundle["per_mandi_metrics"]
        m_mape = m_metrics[m_metrics['mandi_id'] == mandi_id]['MAPE'].iloc[0] if mandi_id in m_metrics['mandi_id'].values else 10.0
        if m_mape > 8.0:
            confidence *= 0.8 # Penalize high-error mandis
            
        trend = "upward" if pred_price > inf_row['price_lag_1'].iloc[0] else "downward"
        vol_text = "high" if inf_row['volatility_regime'].iloc[0] == 1 else "low"

        return {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "target_date": str(latest['date'].iloc[0].date()),
            "predicted_price": float(round(pred_price, 2)),
            "predicted_arrivals": float(round(pred_arrivals, 2)),
            "confidence": float(round(confidence, 2)),
            "trend": trend,
            "volatility": vol_text,
            "explanation": f"Price is expected to {trend} in {mandi_id}. Market volatility is {vol_text}."
        }

if __name__ == "__main__":
    engine = RefinedInferenceEngine()
    print("--- MANDISENSE REFINED INFERENCE TEST ---")
    res = engine.predict("tomato", "kolar_apmc")
    import json
    print(json.dumps(res, indent=2))
