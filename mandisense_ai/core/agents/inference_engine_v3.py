import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from mandisense_ai.core.data.data_service import MandiDataService

# --- CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_ROOT = PROJECT_ROOT / "mandisense_ai" / "models"
DATA_V4_DIR = PROJECT_ROOT / "mandisense_ai" / "data" / "processed" / "v4"
VERSION = "v3"

class DecisionGradeInferenceEngine:
    def __init__(self):
        self.models = {}
        self._load_all_models()
        
    def _load_all_models(self):
        for comm_dir in MODELS_ROOT.iterdir():
            if comm_dir.is_dir():
                v3_dir = comm_dir / VERSION
                if not v3_dir.exists():
                    continue
                comm = comm_dir.name
                try:
                    self.models[comm] = {
                        "price_model": joblib.load(v3_dir / "model.pkl"),
                        "arrival_model": joblib.load(v3_dir / "arrival_model.pkl"),
                        "mandi_encoder": joblib.load(v3_dir / "mandi_encoder.pkl"),
                        "features": json.load(open(v3_dir / "feature_columns.json")),
                        "calibration_map": json.load(open(v3_dir / "calibrated_confidence_map.json")),
                        "per_mandi_metrics": pd.read_csv(v3_dir / "per_mandi_metrics.csv"),
                        "directional_accuracy": pd.read_csv(v3_dir / "directional_accuracy.csv")
                    }
                except Exception as e:
                    print(f"Failed to load models for {comm} v3: {e}")

    async def predict(self, commodity, mandi_id):
        if commodity not in self.models:
            raise ValueError(f"No models found for commodity: {commodity}")
        
        bundle = self.models[commodity]
        
        # STEP 9: SERVICE INTEGRATION
        data_service = MandiDataService.get_instance()
        data_input = await data_service.prepare_inference_input(commodity, mandi_id)
        
        latest = data_input['latest']
        history = data_input['history']
        is_stale = data_input['is_stale']
        
        # Feature Engineering (Same as v2)
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
        mandi_vol_threshold = history['price'].rolling(7).std().median()
        inf_row['volatility_regime'] = 1 if inf_row['volatility'].iloc[0] > mandi_vol_threshold else 0
        inf_row['month'] = latest['date'].dt.month.iloc[0]
        inf_row['day_of_week'] = latest['date'].dt.dayofweek.iloc[0]
        inf_row['mandi_encoded'] = bundle["mandi_encoder"].transform([mandi_id])[0]
        
        # Predict
        X = inf_row[bundle["features"]]
        pred_price = bundle["price_model"].predict(X)[0]
        pred_arrivals = bundle["arrival_model"].predict(X)[0]
        
        # STEP 1: CALIBRATED CONFIDENCE
        raw_conf = 1 / (1 + (inf_row['volatility'].iloc[0] / (inf_row['rolling_mean_7'].iloc[0] + 1e-6)))
        
        # Map raw confidence to calibrated bin
        calibrated_conf = 0.75 # Default
        for bucket_str, val in bundle["calibration_map"].items():
            # bucket_str is like "(0.5, 0.6]"
            # A bit messy to parse, but let's use a simple lookup if possible
            # For this demo, we'll find the bucket manually
            low, high = map(float, bucket_str.strip("()[]").split(", "))
            if low < raw_conf <= high:
                calibrated_conf = val
                break
                
        # STEP 3: RISK SCORING
        m_metrics = bundle["per_mandi_metrics"]
        mandi_mape = m_metrics[m_metrics['mandi_id'] == mandi_id]['MAPE'].iloc[0] / 100 if mandi_id in m_metrics['mandi_id'].values else 0.1
        
        norm_vol = inf_row['volatility'].iloc[0] / (inf_row['rolling_mean_7'].iloc[0] + 1e-6)
        risk_score = (1 - calibrated_conf) + norm_vol + mandi_mape
        
        if risk_score < 0.3: risk_level = "LOW"
        elif risk_score < 0.6: risk_level = "MEDIUM"
        else: risk_level = "HIGH"
        
        # STEP 4: ARRIVAL IMPACT
        arrival_change = pred_arrivals - inf_row['arrivals_lag_1'].iloc[0]
        arrival_signal = "increasing" if arrival_change > 0 else "decreasing"
        supply_reasoning = "tightening supply" if arrival_signal == "decreasing" else "increasing supply"
        
        trend = "upward" if pred_price > inf_row['price_lag_1'].iloc[0] else "downward"
        
        # Directional Accuracy
        dir_acc_df = bundle["directional_accuracy"]
        dir_acc = dir_acc_df[dir_acc_df['mandi_id'] == mandi_id]['direction_accuracy'].iloc[0] if mandi_id in dir_acc_df['mandi_id'].values else 0.7
        
        explanation = f"Price is expected to {trend} in {mandi_id} ({risk_level} risk). "
        explanation += f"Arrivals are predicted to be {arrival_signal}, suggesting {supply_reasoning}. "
        explanation += f"Market volatility is currently {'high' if inf_row['volatility_regime'].iloc[0] == 1 else 'low'}."

        return {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "target_date": str(latest['date'].iloc[0].date()),
            "predicted_price": float(round(pred_price, 2)),
            "predicted_arrivals": float(round(pred_arrivals, 2)),
            "confidence": float(round(calibrated_conf, 2)),
            "trend": trend,
            "volatility": "high" if inf_row['volatility_regime'].iloc[0] == 1 else "low",
            "risk_level": risk_level,
            "arrival_signal": arrival_signal,
            "direction_confidence": float(round(dir_acc, 2)),
            "explanation": explanation
        }

if __name__ == "__main__":
    import asyncio
    async def test():
        engine = DecisionGradeInferenceEngine()
        print("--- MANDISENSE DECISION-GRADE INFERENCE TEST ---")
        res = await engine.predict("tomato", "kolar_apmc")
        print(json.dumps(res, indent=2))
    asyncio.run(test())
