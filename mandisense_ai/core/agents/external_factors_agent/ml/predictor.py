import os
import joblib
import pandas as pd

MODEL_PATH = "models/xgb_model.pkl"
_model = None

def load_model():
    global _model
    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception:
            _model = None

def predict(features):
    # If model missing -> return None
    # No crash allowed
    if _model is None:
        load_model()
        
    if _model is None:
        return None
        
    try:
        df = pd.DataFrame([features])
        X = df[[
            "event_count_3d", "event_count_7d", "avg_confidence",
            "max_impact", "sum_impact", "recent_event_flag", "days_since_last_event"
        ]]
        preds = _model.predict(X)
        return float(preds[0])
    except Exception:
        # Fallback empty handling
        return None
