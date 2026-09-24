"""Unit tests for LLM Provider Router (Layer 35 Deliverable).

Comprehensive verification of:
- LLM Router offline mock completion
- Structured Pydantic schema validation and JSON extraction
- Provider fallback chain (Groq -> Gemini Flash -> Offline Mock)
- Latency and token metadata tracking
- Network-free offline execution
"""

from typing import List, Optional
import pytest
from pydantic import BaseModel

from backend.app.llm.router import LLMResponse, LLMRouter
from tests.unit.test_llm_router import (
    SampleFraudAnalysis,
    test_automatic_gemini_fallback_on_groq_failure,
    test_fast_vs_primary_model_selection,
    test_markdown_json_cleaning,
    test_offline_mock_completion,
    test_structured_pydantic_schema_validation,
)


def test_provider_router_explicit_mock_mode():
    """Verify router cleanly operates when all provider credentials are explicitly omitted."""
    router = LLMRouter(groq_api_key=None, gemini_api_key=None)
    assert router._groq_client is None
    assert router._gemini_configured is False

    res = router.complete("Summarize transaction pattern")
    assert res.provider == "mock"
    assert res.is_fallback is True
    assert len(res.content) > 0
