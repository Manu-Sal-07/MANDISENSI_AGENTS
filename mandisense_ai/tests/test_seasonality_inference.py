import pandas as pd
from datetime import datetime
try:
    from mandisense_ai.core.agents.seasonality.inference import SeasonalityInferencePipeline, FEATURE_COLS
except ImportError:
    from core.agents.seasonality.inference import SeasonalityInferencePipeline, FEATURE_COLS


def test_build_inference_features_consistency():
    dates = pd.date_range(start="2023-01-01", periods=45, freq="D")
    prices = pd.Series(100 + (dates.dayofyear * 0.1)).round(2)
    df = pd.DataFrame({"date": dates, "modal_price": prices})

    pipeline = SeasonalityInferencePipeline(models_dir="test_models")
    timestamp = datetime.fromisoformat(str(dates.max().date()))
    features = pipeline.build_inference_features(df, timestamp=timestamp, feature_columns=FEATURE_COLS, mandi_name="test_mandi")

    assert list(features.columns) == FEATURE_COLS
    assert not features.iloc[-1].isna().any()
    assert features.shape[0] == 1
    assert features.loc[features.index[-1], "price_lag_7"] == df.iloc[-8]["modal_price"]


def test_build_inference_features_with_stl_components():
    dates = pd.date_range(start="2023-01-01", periods=90, freq="D")
    prices = pd.Series(100 + (dates.dayofyear * 0.15)).round(2)
    df = pd.DataFrame({"date": dates, "modal_price": prices})

    pipeline = SeasonalityInferencePipeline(models_dir="test_models")
    timestamp = datetime.fromisoformat(str(dates.max().date()))
    feature_columns = FEATURE_COLS + ["trend", "seasonal", "residual"]
    features = pipeline.build_inference_features(df, timestamp=timestamp, feature_columns=feature_columns, mandi_name="test_mandi")

    assert set(["trend", "seasonal", "residual"]).issubset(set(features.columns))
    assert not features[["trend", "seasonal", "residual"]].isna().any(axis=None)
    assert features.shape == (1, len(feature_columns))
