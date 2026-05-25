import pandas as pd
import numpy as np
import joblib
import json
import logging
from pathlib import Path
from mandisense_ai.core.data.data_service import MandiDataService

logger = logging.getLogger("InferenceEngineV3")

# --- CONFIGURATION ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_ROOT = PROJECT_ROOT / "mandisense_ai" / "models"
DATA_V4_DIR = PROJECT_ROOT / "mandisense_ai" / "data" / "processed" / "v4"
VERSION = "v3"

class DecisionGradeInferenceEngine:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DecisionGradeInferenceEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.models = {}
        self._load_all_models()
        self._initialized = True
        
    def _load_all_models(self):
        from mandisense_ai.cognition.registry import VALID_COMMODITIES
        
        for comm in VALID_COMMODITIES:
            comm_dir = MODELS_ROOT / comm
            if comm_dir.is_dir():
                v3_dir = comm_dir / VERSION
                if not v3_dir.exists():
                    logger.warning(f"No v3 models found for canonical commodity: {comm}")
                    continue
                    
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
                    logger.info(f"Successfully loaded institutional artifacts for {comm}")
                except Exception as e:
                    logger.error(f"Failed to load models for {comm} v3: {e}")

    async def predict(self, commodity, mandi_id):
        if commodity not in self.models:
            raise ValueError(f"No models found for commodity: {commodity}")
        
        bundle = self.models[commodity]
        
        # STEP 9: SERVICE INTEGRATION
        data_service = MandiDataService.get_instance()
        data_input = await data_service.prepare_inference_input(commodity, mandi_id)
        
        latest = data_input.get('latest')
        if latest is None or latest.empty:
            logger.warning(f"No recent data for {commodity} @ {mandi_id}. Using historical fallbacks.")
            # Mocking a fallback if latest is missing during replay
            latest = pd.Series({'price': 0, 'arrivals': 0})
            
        history = data_input.get('history', pd.DataFrame())
        is_stale = data_input.get('is_stale', True)
        
        # Ensure latest is a proper Series (single row)
        if isinstance(latest, pd.DataFrame):
            latest = latest.iloc[0]
        
        # Feature Engineering
        inf_row = pd.Series(dtype=object)
        # Copy scalar values from latest
        for col in latest.index:
            try:
                inf_row[col] = latest[col]
            except Exception:
                pass
        
        if not history.empty and 'price' in history.columns and len(history) >= 7:
            inf_row['price_lag_1'] = history['price'].iloc[-1]
            inf_row['price_lag_3'] = history['price'].iloc[-3]
            inf_row['price_lag_7'] = history['price'].iloc[-7]
            inf_row['arrivals_lag_1'] = history['arrivals'].iloc[-1]
            inf_row['arrivals_lag_3'] = history['arrivals'].iloc[-3]
            inf_row['arrivals_lag_7'] = history['arrivals'].iloc[-7]
            inf_row['arrival_trend'] = inf_row['arrivals_lag_1'] - inf_row['arrivals_lag_3']
            inf_row['rolling_mean_7'] = history['price'].tail(7).mean()
            inf_row['volatility'] = float(history['price'].tail(7).std())
            mandi_vol_threshold = float(history['price'].rolling(7).std().median())
            inf_row['volatility_regime'] = 1 if inf_row['volatility'] > mandi_vol_threshold else 0
        else:
            for col in ['price_lag_1', 'price_lag_3', 'price_lag_7', 'arrivals_lag_1', 'arrivals_lag_3', 'arrivals_lag_7']:
                inf_row[col] = 0
            inf_row['arrival_trend'] = 0
            inf_row['rolling_mean_7'] = 0
            inf_row['volatility'] = 0
            inf_row['volatility_regime'] = 0
        # Date-based features
        try:
            date_val = latest.get('date', None) if hasattr(latest, 'get') else (latest['date'] if 'date' in latest.index else None)
            if date_val is not None:
                import datetime
                if hasattr(date_val, 'month'):
                    inf_row['month'] = date_val.month
                    inf_row['day_of_week'] = date_val.dayofweek if hasattr(date_val, 'dayofweek') else date_val.weekday()
                else:
                    now = pd.Timestamp.now()
                    inf_row['month'] = now.month
                    inf_row['day_of_week'] = now.dayofweek
            else:
                now = pd.Timestamp.now()
                inf_row['month'] = now.month
                inf_row['day_of_week'] = now.dayofweek
        except Exception:
            now = pd.Timestamp.now()
            inf_row['month'] = now.month
            inf_row['day_of_week'] = now.dayofweek
        
        try:
            inf_row['mandi_encoded'] = bundle["mandi_encoder"].transform([mandi_id])[0]
        except Exception:
            inf_row['mandi_encoded'] = 0
        
        # Predict
        try:
            X_df = pd.DataFrame([inf_row])
            for feature in bundle["features"]:
                if feature not in X_df.columns:
                    X_df[feature] = 0
            X_df = X_df[bundle["features"]]
            pred_price = float(bundle["price_model"].predict(X_df)[0])
            pred_arrivals = float(bundle["arrival_model"].predict(X_df)[0])
        except Exception as e:
            logger.error(f"Model predict failed: {e}")
            pred_price = float(inf_row.get('price', 0) or 0)
            pred_arrivals = float(inf_row.get('arrivals', 0) or 0)
        
        # STEP 1: CALIBRATED CONFIDENCE
        vol_val = float(inf_row.get('volatility', 0) or 0)
        roll_mean_val = float(inf_row.get('rolling_mean_7', 1) or 1)
        raw_conf = 1 / (1 + (vol_val / (roll_mean_val + 1e-6)))
        
        # Map raw confidence to calibrated bin
        calibrated_conf = 0.75 # Default
        for bucket_str, val in bundle["calibration_map"].items():
            try:
                low, high = map(float, bucket_str.strip("()[]").split(", "))
                if low < raw_conf <= high:
                    calibrated_conf = val
                    break
            except Exception:
                pass
                 
        # STEP 3: RISK SCORING
        m_metrics = bundle["per_mandi_metrics"]
        try:
            mape_rows = m_metrics[m_metrics['mandi_id'] == mandi_id]['MAPE']
            mandi_mape = float(mape_rows.iloc[0]) / 100 if not mape_rows.empty else 0.1
        except Exception:
            mandi_mape = 0.1
        
        norm_vol = vol_val / (roll_mean_val + 1e-6)
        risk_score = (1 - calibrated_conf) + norm_vol + mandi_mape
        
        if risk_score < 0.3: risk_level = "LOW"
        elif risk_score < 0.6: risk_level = "MEDIUM"
        else: risk_level = "HIGH"
        
        # STEP 4: ARRIVAL IMPACT
        arrivals_lag_1 = float(inf_row.get('arrivals_lag_1', 0) or 0)
        price_lag_1 = float(inf_row.get('price_lag_1', pred_price) or pred_price)
        vol_regime = int(inf_row.get('volatility_regime', 0) or 0)
        arrival_change = pred_arrivals - arrivals_lag_1
        arrival_signal = "increasing" if arrival_change > 0 else "decreasing"
        supply_reasoning = "tightening supply" if arrival_signal == "decreasing" else "increasing supply"
        
        trend = "upward" if pred_price > price_lag_1 else "downward"
        
        # Directional Accuracy
        dir_acc_df = bundle["directional_accuracy"]
        try:
            dir_rows = dir_acc_df[dir_acc_df['mandi_id'] == mandi_id]['direction_accuracy']
            dir_acc = float(dir_rows.iloc[0]) if not dir_rows.empty else 0.7
        except Exception:
            dir_acc = 0.7
        
        # Get date for response
        try:
            date_val = latest.get('date', None) if hasattr(latest, 'get') else (latest['date'] if 'date' in latest.index else None)
            target_date = str(pd.Timestamp(date_val).date()) if date_val is not None else str(pd.Timestamp.now().date())
        except Exception:
            target_date = str(pd.Timestamp.now().date())

        explanation = f"Price is expected to {trend} in {mandi_id} ({risk_level} risk). "
        explanation += f"Arrivals are predicted to be {arrival_signal}, suggesting {supply_reasoning}. "
        explanation += f"Market volatility is currently {'high' if vol_regime == 1 else 'low'}."

        return {
            "commodity": commodity,
            "mandi_id": mandi_id,
            "target_date": target_date,
            "predicted_price": round(pred_price, 2),
            "predicted_arrivals": round(pred_arrivals, 2),
            "confidence": round(calibrated_conf, 2),
            "trend": trend,
            "volatility": "high" if vol_regime == 1 else "low",
            "risk_level": risk_level,
            "arrival_signal": arrival_signal,
            "direction_confidence": round(dir_acc, 2),
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
