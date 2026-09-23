"""Unit tests for Layer 34 — Local Audit Trail and Observability Engine."""

import json
from pathlib import Path
import pytest
import tempfile
import time

from backend.app.models.state import FraudCaseState, TriggerType
from backend.app.observability.tracer import (
    InvestigationTracer,
    SpanType,
    TraceSpan,
    sanitize_sensitive_data,
)
from backend.app.services.investigation_service import InvestigationService


def test_sanitize_sensitive_data():
    """Verify secrets, passwords, tokens, and raw keys are redacted per AGENTS.md §32."""
    raw_payload = {
        "groq_api_key": "gsk_test_1234567890abcdef",
        "gemini_api_key": "AIzaSyTestApiKeySecret123",
        "tigergraph_password": "super_secret_tigergraph_pwd",
        "auth_token": "Bearer sk-some-secret-token",
        "normal_metric": 42.5,
        "nested": {
            "bearer_secret": "my-secret",
            "account_id": "ACC_1001",
        },
    }

    sanitized = sanitize_sensitive_data(raw_payload)
    assert sanitized["groq_api_key"] == "[REDACTED_SECRET]"
    assert sanitized["gemini_api_key"] == "[REDACTED_SECRET]"
    assert sanitized["tigergraph_password"] == "[REDACTED_SECRET]"
    assert sanitized["auth_token"] == "[REDACTED_SECRET]"
    assert sanitized["normal_metric"] == 42.5
    assert sanitized["nested"]["bearer_secret"] == "[REDACTED_SECRET]"
    assert sanitized["nested"]["account_id"] == "ACC_1001"


def test_tracer_records_and_reads_spans():
    """Verify tracer records JSONL lines to disk and reads them accurately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracer = InvestigationTracer(output_dir=tmpdir, enable_langfuse=False)
        case_id = "CASE_TRACE_TEST_01"

        # 1. Record manual spans
        tracer.log_node(case_id, "parallel_evidence_collection", duration_ms=45.2, metadata={"count": 12})
        tracer.log_query(case_id, "get_transaction_context", duration_ms=12.1, target_entity="TXN_999", record_count=1)
        tracer.log_llm(case_id, "groq", "gpt-oss-120b", duration_ms=250.0)
        tracer.log_policy(case_id, "BLOCK_TRANSACTION", allowed=True, approval_required=False, policy_ref="POL-01")
        tracer.log_action(case_id, "BLOCK_TRANSACTION", execution_mode="SIMULATED", success=True)

        trace_path = tracer.get_trace_path(case_id)
        assert trace_path.exists()

        # Check raw JSONL contents
        with open(trace_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) == 5
        assert lines[0]["span_type"] == "NODE_EXECUTION"
        assert lines[0]["name"] == "Node:parallel_evidence_collection"
        assert lines[0]["duration_ms"] == 45.2

        assert lines[1]["span_type"] == "GSQL_QUERY"
        assert lines[2]["span_type"] == "LLM_INVOCATION"
        assert lines[3]["span_type"] == "POLICY_DECISION"
        assert lines[4]["span_type"] == "ACTION_EXECUTION"

        # 2. Read through read_traces method
        spans = tracer.read_traces(case_id)
        assert len(spans) == 5
        assert all(isinstance(s, TraceSpan) for s in spans)
        assert spans[2].name == "LLM:groq:gpt-oss-120b"


def test_tracer_context_manager():
    """Verify synchronous and asynchronous span context managers measure elapsed time."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracer = InvestigationTracer(output_dir=tmpdir, enable_langfuse=False)
        case_id = "CASE_CM_TEST_02"

        with tracer.span(case_id, SpanType.FEATURE_CALCULATION, "calculate_features", {"feature_count": 8}) as meta:
            time.sleep(0.02)  # 20ms
            meta["status_note"] = "completed"

        spans = tracer.read_traces(case_id)
        assert len(spans) == 1
        assert spans[0].duration_ms >= 15.0  # at least ~15ms
        assert spans[0].metadata.get("feature_count") == 8
        assert spans[0].metadata.get("status_note") == "completed"


def test_investigation_service_trace_response():
    """Verify InvestigationService.get_case_traces retrieves formatted trace response."""
    service = InvestigationService()
    case_id = "CASE_SVC_TRACE_03"

    state = FraudCaseState(
        case_id=case_id,
        trigger_type=TriggerType.TRANSACTION_ALERT,
    )
    service.register_case(state)

    # Record span for this case
    tracer = InvestigationTracer(enable_langfuse=False)
    tracer.log_node(case_id, "validate_trigger", duration_ms=5.0)

    trace_resp = service.get_case_traces(case_id)
    assert trace_resp is not None
    assert trace_resp.case_id == case_id
    assert trace_resp.total_spans >= 1
    assert any(s.name == "Node:validate_trigger" for s in trace_resp.spans)
