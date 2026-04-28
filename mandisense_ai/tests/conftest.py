import pytest
from config.settings import Settings

# Why: Pytest fixtures allow sharing setup code across tests.
# Mocking the settings ensures our tests are isolated and don't accidentally mutally dependent on system environment variables.

@pytest.fixture
def mock_settings():
    """Provides a default pristine settings object for testing."""
    return Settings(
        app={"name": "TestSense", "environment": "testing", "debug": True},
        data={"commodities": ["test_onion"], "mandis": ["test_mandi"], "missing_value_tolerance": 0.5},
        logging={"level": "DEBUG", "format": "json", "file_path": "logs/test.log"},
        paths={"data_dir": "test_data", "raw_data": "test_data/raw", "processed_data": "test_data/processed", "models_dir": "test_models"},
        ensemble={"activation_threshold": 0.5, "default_weight": 0.33}
    )
