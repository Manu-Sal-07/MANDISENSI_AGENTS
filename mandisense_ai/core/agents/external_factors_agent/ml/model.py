import xgboost as xgb

def get_model():
    # XGBoost Regressor with fixed required parameters
    return xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42
    )
