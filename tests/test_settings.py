import pytest
from pydantic import ValidationError
from backend.settings import Settings


def test_settings_default_load(monkeypatch):
    # Clear env variables that might be loaded from local .env
    monkeypatch.delenv("API_SERVER_PORT", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    settings = Settings()

    # To be absolutely sure of default values, we construct Settings with no env file:
    class DefaultSettings(Settings):
        model_config = {}  # disable env file loading

    settings = DefaultSettings(_env_file=None)
    assert settings.llm_provider == "gemini"
    assert settings.port == 8001


def test_validation_fails_in_production_without_key():
    # When APP_ENV=production, llm_provider=gemini and GEMINI_API_KEY is empty, validation should fail
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", LLM_PROVIDER="gemini", GEMINI_API_KEY="")
    # When APP_ENV=production, llm_provider=deepseek and DEEPSEEK_API_KEY is empty, validation should fail
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", LLM_PROVIDER="deepseek", DEEPSEEK_API_KEY="")


def test_validation_passes_in_production_with_key():
    settings = Settings(
        APP_ENV="production", LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key"
    )
    assert settings.gemini_api_key == "test-key"

    settings_ds = Settings(
        APP_ENV="production", LLM_PROVIDER="deepseek", DEEPSEEK_API_KEY="test-key-ds"
    )
    assert settings_ds.deepseek_api_key == "test-key-ds"
