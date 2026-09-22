"""Unit tests for configuration loading and validation."""

import os
from backend.app.config import Settings, get_settings


def test_default_settings():
    """Verify default settings values when no environment variables are set."""
    settings = Settings()
    assert settings.APP_NAME == "TigerGraph Agentic Fraud Investigation"
    assert settings.TIGERGRAPH_HOST == "http://127.0.0.1:9000"
    assert settings.TIGERGRAPH_GRAPH == "FraudInvestigation"
    assert settings.GROQ_PRIMARY_MODEL == "openai/gpt-oss-120b"
    assert settings.GROQ_FAST_MODEL == "openai/gpt-oss-20b"
    assert settings.GEMINI_FALLBACK_MODEL == "gemini-2.0-flash"
    assert settings.ENABLE_LAYA is False
    assert settings.ENABLE_LIGHTGBM is False
    assert settings.ENABLE_LANGFUSE is False


def test_environment_override(monkeypatch):
    """Verify settings can be overridden via environment variables."""
    monkeypatch.setenv("TIGERGRAPH_GRAPH", "CustomFraudGraph")
    monkeypatch.setenv("ENABLE_LAYA", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()
    assert settings.TIGERGRAPH_GRAPH == "CustomFraudGraph"
    assert settings.ENABLE_LAYA is True
    assert settings.LOG_LEVEL == "DEBUG"


def test_cached_get_settings():
    """Verify get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
