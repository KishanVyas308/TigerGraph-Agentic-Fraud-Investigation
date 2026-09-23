"""Unit tests for Layer 15: LLM Provider Router."""

from typing import List, Optional
import pytest
from pydantic import BaseModel

from backend.app.llm.router import LLMResponse, LLMRouter


class SampleFraudAnalysis(BaseModel):
    summary: str
    risk_score: float
    is_suspicious: bool
    flags: List[str]


def test_offline_mock_completion():
    """Test router completion when operating in offline/mock mode (no API keys)."""
    router = LLMRouter(groq_api_key=None, gemini_api_key=None)

    response = router.complete(prompt="Analyze transaction TXN_123 for high risk behavior.")

    assert isinstance(response, LLMResponse)
    assert response.provider == "mock"
    assert response.is_fallback is True
    assert "TXN_123" in response.content
    assert response.latency_ms >= 0.0


def test_structured_pydantic_schema_validation():
    """Test structured Pydantic schema validation and automatic JSON parsing in mock mode."""
    router = LLMRouter(groq_api_key=None, gemini_api_key=None)

    response = router.complete(
        prompt="Analyze suspicious transaction",
        response_schema=SampleFraudAnalysis,
    )

    assert isinstance(response, LLMResponse)
    assert response.parsed_output is not None
    assert isinstance(response.parsed_output, SampleFraudAnalysis)
    assert isinstance(response.parsed_output.summary, str)
    assert isinstance(response.parsed_output.risk_score, float)
    assert isinstance(response.parsed_output.is_suspicious, bool)


def test_markdown_json_cleaning():
    """Test extraction and validation of raw JSON wrapped in markdown fenced codeblocks."""
    router = LLMRouter(groq_api_key=None, gemini_api_key=None)

    raw_markdown = (
        "Here is the structured analysis:\n"
        "```json\n"
        "{\n"
        '  "summary": "High risk velocity detected",\n'
        '  "risk_score": 0.92,\n'
        '  "is_suspicious": true,\n'
        '  "flags": ["RAPID_PASS_THROUGH"]\n'
        "}\n"
        "```\n"
        "End of report."
    )

    parsed = router._parse_and_validate_json(raw_markdown, SampleFraudAnalysis)

    assert parsed.summary == "High risk velocity detected"
    assert parsed.risk_score == 0.92
    assert parsed.is_suspicious is True
    assert parsed.flags == ["RAPID_PASS_THROUGH"]


def test_automatic_gemini_fallback_on_groq_failure(monkeypatch):
    """Test automatic failover to Gemini Flash when Groq provider call raises an exception."""
    router = LLMRouter(
        groq_api_key="fake-groq-key",
        gemini_api_key="fake-gemini-key",
    )

    # Mock Groq failure
    def mock_groq_fail(*args, **kwargs):
        raise RuntimeError("Groq API rate limit 429 exceeded!")

    # Mock Gemini success
    def mock_gemini_success(*args, **kwargs):
        return LLMResponse(
            content='{"summary": "Fallback summary", "risk_score": 0.8, "is_suspicious": true, "flags": []}',
            parsed_output=None,
            provider="gemini",
            model_name="gemini-1.5-flash",
            latency_ms=120.0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            is_fallback=True,
        )

    monkeypatch.setattr(router, "_call_groq", mock_groq_fail)
    monkeypatch.setattr(router, "_call_gemini", mock_gemini_success)

    response = router.complete(prompt="Run risk assessment")

    assert response.provider == "gemini"
    assert response.is_fallback is True
    assert response.model_name == "gemini-1.5-flash"


def test_fast_vs_primary_model_selection(monkeypatch):
    """Verify use_fast_model=True routes to groq_fast_model and False routes to groq_primary_model."""
    router = LLMRouter(groq_api_key="fake-key")

    captured_models = []

    def mock_call_groq(prompt, system_prompt, model_name, **kwargs):
        captured_models.append(model_name)
        return LLMResponse(
            content="Mock response",
            provider="groq",
            model_name=model_name,
        )

    monkeypatch.setattr(router, "_call_groq", mock_call_groq)

    router.complete(prompt="Deep reasoning", use_fast_model=False)
    router.complete(prompt="Fast classification", use_fast_model=True)

    assert len(captured_models) == 2
    assert captured_models[0] == "openai/gpt-oss-120b"
    assert captured_models[1] == "openai/gpt-oss-20b"
