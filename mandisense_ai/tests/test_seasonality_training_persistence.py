import joblib
import numpy as np
import pandas as pd

from core.agents.seasonality.training.train_seasonality import (
    align_features,
    build_features,
    load_seasonality_bundle,
    predict_with_ensemble,
    train_seasonality_models,
)
from core.agents.seasonality.multi_horizon import FEATURE_COLS


def test_train_seasonality_models_saves_bundle(tmp_path):
    dates = pd.date_range(start="2022-01-01", periods=150, freq="D")
    prices = 100 + np.sin(np.linspace(0, 4 * np.pi, len(dates))) * 5 + np.linspace(0, 10, len(dates))
    df = pd.DataFrame({"date": dates, "modal_price": prices})
    df["price_lag_1"] = df["modal_price"].shift(1)
    df["price_lag_7"] = df["modal_price"].shift(7)
    df["price_lag_14"] = df["modal_price"].shift(14)
    df["price_mean_7"] = df["modal_price"].shift(1).rolling(7, min_periods=4).mean()
    df["price_std_7"] = df["modal_price"].shift(1).rolling(7, min_periods=4).std()
    df["price_mean_30"] = df["modal_price"].shift(1).rolling(30, min_periods=10).mean()
    df["price_std_30"] = df["modal_price"].shift(1).rolling(30, min_periods=10).std()
    df["month"] = df["date"].dt.month.astype(float)
    df["day_of_week"] = df["date"].dt.dayofweek.astype(float)

    models_dir = tmp_path / "models"
    bundle = train_seasonality_models(
        df,
        commodity="tomato",
        mandi="kolar",
        models_dir=str(models_dir),
    )

    assert "models" in bundle and bundle["models"]
    assert "weights" in bundle and bundle["weights"]
    assert bundle["feature_columns"] == FEATURE_COLS
    assert bundle["metadata"]["model_names"] == list(bundle["models"].keys())
    assert bundle["metadata"]["n_samples"] >= 80

    bundle_path = models_dir / "tomato_kolar" / "seasonality" / "bundle.pkl"
    assert bundle_path.exists()

    loaded_bundle = joblib.load(bundle_path)
    assert loaded_bundle["feature_columns"] == bundle["feature_columns"]
    assert set(loaded_bundle["models"].keys()) == set(bundle["models"].keys())
    assert loaded_bundle["metadata"]["cv_scores"] == bundle["metadata"]["cv_scores"]


def test_load_seasonality_bundle_and_predict(tmp_path):
    dates = pd.date_range(start="2022-01-01", periods=150, freq="D")
    prices = 100 + np.sin(np.linspace(0, 4 * np.pi, len(dates))) * 5 + np.linspace(0, 10, len(dates))
    df = pd.DataFrame({"date": dates, "modal_price": prices})
    df["price_lag_1"] = df["modal_price"].shift(1)
    df["price_lag_7"] = df["modal_price"].shift(7)
    df["price_lag_14"] = df["modal_price"].shift(14)
    df["price_mean_7"] = df["modal_price"].shift(1).rolling(7, min_periods=4).mean()
    df["price_std_7"] = df["modal_price"].shift(1).rolling(7, min_periods=4).std()
    df["price_mean_30"] = df["modal_price"].shift(1).rolling(30, min_periods=10).mean()
    df["price_std_30"] = df["modal_price"].shift(1).rolling(30, min_periods=10).std()
    df["month"] = df["date"].dt.month.astype(float)
    df["day_of_week"] = df["date"].dt.dayofweek.astype(float)

    models_dir = tmp_path / "models"
    train_seasonality_models(
        df,
        commodity="tomato",
        mandi="kolar",
        models_dir=str(models_dir),
    )

    bundle = load_seasonality_bundle(
        commodity="tomato",
        mandi="kolar",
        models_dir=str(models_dir),
    )
    assert bundle["weights"]
    assert bundle["feature_columns"] == FEATURE_COLS
    assert bundle["metadata"]["model_names"] == list(bundle["models"].keys())

    inference_features = build_features(df)
    aligned = align_features(inference_features, bundle["feature_columns"])
    assert list(aligned.columns) == bundle["feature_columns"]

    prediction = predict_with_ensemble(bundle, aligned)
    assert "prediction" in prediction
    assert "confidence" in prediction
    assert 0.05 <= prediction["confidence"] <= 0.95
    assert "stable_prediction" in prediction
    assert "ensemble_prediction" in prediction
    assert prediction["model_breakdown"]
    assert prediction["metadata"]["n_models_used"] == len(bundle["models"])
    assert prediction["metadata"]["prediction_std"] >= 0.0
