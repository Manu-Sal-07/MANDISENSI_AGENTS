import pandas as pd
import pytest

from core.agents.external_factors_agent.processing.weather_signal import (
    WeatherFeatures,
    build_weather_features,
    get_weather_signal,
    resolve_mandi_coordinates,
    weather_features_to_signal,
)


class TestMandiCoordinateResolution:
    def test_resolve_mandi_coordinates_exact(self):
        lat, lon = resolve_mandi_coordinates("kolar")
        assert (lat, lon) == (13.1377, 78.1299)

    def test_resolve_mandi_coordinates_district_fallback(self):
        lat, lon = resolve_mandi_coordinates("unknown_mandi", district="bangalore rural")
        assert (lat, lon) == (13.2847, 77.6078)

    def test_resolve_mandi_coordinates_missing(self):
        try:
            resolve_mandi_coordinates("unknown_mandi", district="unknown_district")
        except KeyError as exc:
            assert "No coordinates found" in str(exc)
        else:
            raise AssertionError("Expected KeyError for missing mandi and district")


class TestWeatherFeatureEngineering:
    def test_build_weather_features_zero_deviation(self):
        current_date = "2026-04-28"
        dates = pd.date_range("2026-03-30", "2026-04-28", freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "temperature": 25.0,
                "precipitation": 5.0,
            }
        )

        features = build_weather_features(df, current_date)
        assert isinstance(features, WeatherFeatures)
        assert features.recent_rain_7d == 35.0
        assert features.baseline_rain_30d == 5.0
        assert features.rainfall_deviation == pytest.approx(6.0)
        assert features.temp_anomaly == 0.0

    def test_weather_features_to_signal_extreme_rain_deficit(self):
        features = WeatherFeatures(
            recent_rain_7d=0.0,
            baseline_rain_30d=5.0,
            rainfall_deviation=-1.0,
            recent_temp_7d=25.0,
            baseline_temp_30d=25.0,
            temp_anomaly=0.0,
            decayed_rain_7d=0.0,
            decayed_temp_7d=25.0,
        )

        result = weather_features_to_signal(features)
        assert result["weather_signal"] == 0.49
        assert result["components"]["rain_signal"] == 0.7
        assert result["components"]["temp_signal"] == 0.0

    def test_weather_features_to_signal_extreme_heat(self):
        features = WeatherFeatures(
            recent_rain_7d=20.0,
            baseline_rain_30d=20.0,
            rainfall_deviation=0.0,
            recent_temp_7d=31.0,
            baseline_temp_30d=27.0,
            temp_anomaly=4.0,
            decayed_rain_7d=20.0,
            decayed_temp_7d=31.0,
        )

        result = weather_features_to_signal(features)
        assert result["weather_signal"] == 0.12
        assert result["components"]["rain_signal"] == 0.0
        assert result["components"]["temp_signal"] == 0.4


class TestGetWeatherSignal:
    def test_get_weather_signal_with_weather_df(self):
        current_date = "2026-04-28"
        dates = pd.date_range("2026-03-30", "2026-04-28", freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "temperature": 25.0,
                "precipitation": 0.0,
            }
        )

        output = get_weather_signal("kolar", "tomato", current_date, weather_df=df)
        assert output["weather_signal"] == 0.0
        assert output["components"]["rain_signal"] == 0.0
        assert output["components"]["temp_signal"] == 0.0
        assert output["mandi"] == "kolar"
        assert output["commodity"] == "tomato"
        assert output["date"] == current_date
        assert output["coordinates"]["latitude"] == 13.1377

    def test_get_weather_signal_invalid_date_returns_error_signal(self):
        output = get_weather_signal("kolar", "tomato", "invalid-date", weather_df=pd.DataFrame())
        assert output["weather_signal"] == 0.0
        assert output["components"]["rain_signal"] == 0.0
        assert output["components"]["temp_signal"] == 0.0
        assert "error" in output
        assert output["date"] == "invalid-date"
