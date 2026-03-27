import os
from app.config import Settings, load_settings, get_settings

def test_default_values():
    os.environ.clear()
    get_settings.cache_clear()
    settings = load_settings()
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.tool_timeout == 10
    assert settings.agent_timeout == 30
    assert settings.request_timeout == 90

def test_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("TOOL_TIMEOUT", "5")
    get_settings.cache_clear()
    settings = load_settings()
    assert settings.openai_model == "gpt-4o"
    assert settings.tool_timeout == 5