import os
import sys

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

from ml.model import get_model
from ml.dataset_builder import build_dataset

def train_model():
    print("Building dataset...")
    build_dataset()
    
    dataset_path = "data/training/dataset.csv"
    if not os.path.exists(dataset_path):
        print("Dataset missing -> skip training.")
        return
        
    df = pd.read_csv(dataset_path)
    
    # 1. Skip missing price rows, No NaN allowed
    # Convert empty strings or spaces to NaN then drop
    df['price_change'] = pd.to_numeric(df['price_change'], errors='coerce')
    df = df.dropna(subset=['price_change'])
    df = df.fillna(0)
    
    if df.empty:
        print("Dataset empty after dropping missing price rows -> skip training.")
        return
        
    # 2. Features and Target
    X = df[[
        "event_count_3d", "event_count_7d", "avg_confidence",
        "max_impact", "sum_impact", "recent_event_flag", "days_since_last_event"
    ]]
    y = df["price_change"]
    
    # 3. Split 80/20
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Train Model
    model = get_model()
    model.fit(X_train, y_train)
    
    # 5. Validation Metric
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"Validation MAE: {mae:.4f}")
    
    # 6. Save model
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/xgb_model.pkl")
    print("Model saved to models/xgb_model.pkl")

if __name__ == "__main__":
    train_model()
