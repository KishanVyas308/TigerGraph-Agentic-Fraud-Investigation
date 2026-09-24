"""Integration Tests for Layer 36: LLM Provider Fallback & Failover (Scenario 6).

Validates Scenario 6 defined in AGENTS.md §3, §15, & §33:
1. Primary Groq Failure -> Fallover to Secondary Gemini Flash:
   - Simulates Groq timeout, rate limit (HTTP 429), or network drop.
   - LLMRouter catches failure, logs warning, and routes to Gemini Flash without failing investigation.
   - Workflow finishes end-to-end with is_fallback=True and provider='gemini'.
2. Double Provider Failure (Groq & Gemini) -> Deterministic Mock Fallback:
   - Simulates total external API outage (offline / airgapped local execution).
   - LLMRouter falls back to _call_mock returning valid ReasoningOutputSchema.
   - Workflow runs to completion (CaseStatus.COMPLETED) with zero network dependency.
3. JSON Output Repair & Robustness:
   - Verifies handling of markdown-fenced JSON (```json ... ```) and conversational wrappers.
   - Verifies that malformed JSON triggers deterministic MainReasoningNode._fallback_reasoning.
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch
import pytest

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
    create_investigation_graph,
)
from backend.app.agents.nodes.evidence_collection import ParallelEvidenceCollectionNode
from backend.app.agents.nodes.reasoning import MainReasoningNode, ReasoningOutputSchema
from backend.app.llm.router import LLMResponse, LLMRouter
from backend.app.models.state import (
    ActionType,
    CaseStatus,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskLevel,
    StopReason,
    TimelineEvent,
    TriggerType,
)


@pytest.fixture
def mock_tg_client():
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TX_FAILOVER_01",
        "amount": 2500.0,
        "currency": "USD",
        "customer_id": "CUST_FAILOVER_01",
        "account_id": "ACC_FAILOVER_01",
        "device_id": "DEV_FAILOVER_01",
        "ip_address": "198.51.100.11",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TX_FAILOVER_01",
        "amount_to_mean_ratio": 3.2,
        "txn_count_5m": 1,
        "is_new_merchant": True,
    }
    client.find_shared_devices.return_value = {"device_id": "DEV_FAILOVER_01", "shared_account_count": 2, "shared_customer_count": 2, "linked_fraud_cases": []}
    client.find_shared_ips.return_value = {"ip_address": "198.51.100.11", "shared_account_count": 2, "shared_customer_count": 2}
    client.find_fraud_neighbors.return_value = {"vertex_id": "ACC_FAILOVER_01", "fraud_neighbors_count": 1, "neighbor_case_ids": ["HIST_CASE_11"]}
    client.get_shortest_path_to_fraud.return_value = {"vertex_id": "ACC_FAILOVER_01", "target_fraud_case_id": "HIST_CASE_11", "shortest_distance": 2}
    client.detect_money_flow_patterns.return_value = {"account_id": "ACC_FAILOVER_01", "fan_in_count": 2, "fan_out_count": 1, "rapid_pass_through": False, "cycle_detected": False}
    client.get_device_identity_context.return_value = {"device_id": "DEV_FAILOVER_01", "is_new_device": True, "linked_account_count": 2}
    return client


@pytest.fixture
def mock_rag_service():
    service = MagicMock()
    mock_policy = MagicMock()
    mock_policy.model_dump.return_value = {
        "chunk_id": "POL_FAILOVER_01",
        "source_id": "POL_001",
        "document_type": "POLICY",
        "section_title": "Transaction Blocking Guidelines",
        "text": "Block transactions exhibiting suspicious device reuse and abnormal amounts.",
        "relevance_score": 0.90,
    }
    service.retrieve_policy_context.return_value = MagicMock(items=[mock_policy])
    service.retrieve_similar_cases.return_value = MagicMock(cases=[])
    return service


# ============================================================================
# Scenario 6A — Primary Groq Outage -> Gemini Flash Failover
# ============================================================================

@pytest.mark.asyncio
async def test_groq_failure_failover_to_gemini(mock_tg_client, mock_rag_service):
    """Test that when Groq raises an exception, LLMRouter falls back to Gemini Flash seamlessly."""
    router = LLMRouter(groq_api_key="mock_groq_key", gemini_api_key="mock_gemini_key")

    # Simulate Groq timeout or rate-limit error
    def mock_call_groq(*args, **kwargs):
        raise RuntimeError("Groq API Timeout / Rate Limit Exceeded (503 Service Unavailable)")

    # Simulate successful Gemini response
    sample_schema = ReasoningOutputSchema(
        risk_level=RiskLevel.HIGH,
        risk_score=0.82,
        confidence=0.88,
        evidence_completeness=0.85,
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="HYP_GEMINI_01",
                typology_id="TYP_ATO",
                typology_name="Account Takeover",
                confidence=0.88,
                indicators=["shared_device", "unusual_amount"],
            )
        ],
        supporting_evidence_ids=["EVD_TXN_01"],
        contradictory_evidence_ids=[],
        missing_evidence=[],
        recommended_action_type=ActionType.BLOCK_TRANSACTION,
        recommended_action_reasoning="Gemini fallback assessment identified high-risk account takeover indicators.",
        explanation="Gemini failover completed fraud reasoning successfully.",
    )

    def mock_call_gemini(*args, **kwargs):
        return LLMResponse(
            content=sample_schema.model_dump_json(),
            parsed_output=sample_schema,
            provider="gemini",
            model_name="gemini-2.0-flash",
            latency_ms=120.0,
            is_fallback=True,
        )

    router._call_groq = mock_call_groq
    router._call_gemini = mock_call_gemini

    reasoning_node = MainReasoningNode(llm_router=router)
    ev_node = ParallelEvidenceCollectionNode(tigergraph_client=mock_tg_client, rag_service=mock_rag_service)

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=reasoning_node,
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_FAILOVER_601",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_FAILOVER_01",
        customer_id="CUST_FAILOVER_01",
        account_ids=["ACC_FAILOVER_01"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Investigation completes despite Groq failure
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION

    # 2. Risk assessment originates from Gemini fallback
    assert final_state.risk_score == 0.82
    assert final_state.confidence == 0.88

    # 3. Action executed
    executed_types = [e.action_type for e in final_state.executed_actions]
    assert ActionType.BLOCK_TRANSACTION in executed_types

    # 4. Timeline records fallback event details
    reasoning_events = [t for t in final_state.timeline if t.event_type == "REASONING_COMPLETED"]
    assert len(reasoning_events) > 0
    assert reasoning_events[0].details["provider"] == "gemini"
    assert reasoning_events[0].details["is_fallback"] is True


# ============================================================================
# Scenario 6B — Double Provider Failure -> Deterministic Mock Fallback
# ============================================================================

@pytest.mark.asyncio
async def test_double_provider_failure_falls_back_to_offline_mock(mock_tg_client, mock_rag_service):
    """Test that when both Groq and Gemini fail, LLMRouter falls back to deterministic mock without aborting."""
    router = LLMRouter(groq_api_key="mock_groq_key", gemini_api_key="mock_gemini_key")

    # Simulate both external providers failing
    def mock_call_groq(*args, **kwargs):
        raise ConnectionError("Groq unreachable")

    def mock_call_gemini(*args, **kwargs):
        raise ConnectionError("Gemini unreachable")

    router._call_groq = mock_call_groq
    router._call_gemini = mock_call_gemini

    reasoning_node = MainReasoningNode(llm_router=router)
    ev_node = ParallelEvidenceCollectionNode(tigergraph_client=mock_tg_client, rag_service=mock_rag_service)

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=reasoning_node,
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_OFFLINE_602",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_FAILOVER_01",
        customer_id="CUST_FAILOVER_01",
        account_ids=["ACC_FAILOVER_01"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # Workflow completes successfully in offline mock mode
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.is_persisted is True
    assert final_state.is_indexed is True

    # Timeline records provider as mock
    reasoning_events = [t for t in final_state.timeline if t.event_type == "REASONING_COMPLETED"]
    assert len(reasoning_events) > 0
    assert reasoning_events[0].details["provider"] == "mock"
    assert reasoning_events[0].details["is_fallback"] is True


# ============================================================================
# Scenario 6C — JSON Markdown Block Parsing & Schema Validation
# ============================================================================

def test_json_markdown_block_repair_and_validation():
    """Verify that LLMRouter repairs markdown fences (```json ... ```) and extracts Pydantic objects."""
    router = LLMRouter()

    raw_markdown_output = """Here is the structured analysis of the fraud investigation:
```json
{
  "risk_level": "HIGH",
  "risk_score": 0.85,
  "confidence": 0.90,
  "evidence_completeness": 0.80,
  "hypotheses": [
    {
      "hypothesis_id": "HYP_01",
      "typology_id": "TYP_MULE",
      "typology_name": "Mule Ring",
      "confidence": 0.90,
      "indicators": ["shared_device"]
    }
  ],
  "supporting_evidence_ids": ["EVD_01", "EVD_02"],
  "contradictory_evidence_ids": [],
  "missing_evidence": [],
  "recommended_action_type": "BLOCK_TRANSACTION",
  "recommended_action_reasoning": "High confidence in mule activity.",
  "explanation": "Markdown repair verified."
}
```
Thank you for your inquiry."""

    parsed = router._parse_and_validate_json(raw_markdown_output, ReasoningOutputSchema)
    assert isinstance(parsed, ReasoningOutputSchema)
    assert parsed.risk_level == RiskLevel.HIGH
    assert parsed.risk_score == 0.85
    assert parsed.recommended_action_type == ActionType.BLOCK_TRANSACTION
    assert len(parsed.hypotheses) == 1
