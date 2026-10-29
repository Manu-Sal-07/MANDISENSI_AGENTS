import pytest
try:
    from mandisense_ai.config.settings import Settings
except ImportError:
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


@pytest.fixture(autouse=True)
def _no_hosted_model_by_default(monkeypatch):
    """Tests must not depend on whether a developer's `.env` holds an LLM key: chat runs its keyless tool-driven path unless a test
    passes a provider explicitly (the explanation tests stub the model call themselves)."""
    monkeypatch.setenv("CHAT_PROVIDER", "none")
    monkeypatch.setenv("MANDISENSE_LLM_PROVIDER", "deterministic")
    # `select_provider()` re-reads `.env` on every call, which would put a developer's key back after a test removed it.
    monkeypatch.setattr("mandisense_ai.intelligence.providers.load_env", lambda: None)
