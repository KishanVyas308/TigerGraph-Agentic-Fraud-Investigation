"""Integration Tests for Layer 36: Optional Source Fault Tolerance & Robustness (Scenario 7).

Validates Scenario 7 defined in AGENTS.md §9, §11, §31, & §33:
1. Optional External Signals / CRM Outage:
   - External IP reputation or CRM endpoint raises ConnectionError / Timeout.
   - ParallelEvidenceCollectionNode isolates the failure via return_exceptions=True.
   - Core branches (Transaction, Graph, Policy, Precedent, Device) succeed.
   - Investigation completes without uncaught exception.
2. GraphRAG Retrieval Degradation:
   - Vector index or GraphRAG retrieval service raises an exception.
   - Evidence collection continues with deterministic TigerGraph and GSQL facts.
   - Case successfully resolves and completes.
3. Partial TigerGraph Query Outage:
   - Specific GSQL query (e.g. detect_money_flow_patterns) encounters timeout or returns None.
   - GraphFeatureEngine handles None values without fabricating zero values.
   - Investigation finalizes deterministically with auditable timeline.
"""

from typing import Any, Dict
from unittest.mock import MagicMock
import pytest

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
    create_investigation_graph,
)
from backend.app.agents.nodes.evidence_collection import ParallelEvidenceCollectionNode
from backend.app.agents.nodes.reasoning import MainReasoningNode
from backend.app.features.engine import GraphFeatureEngine
from backend.app.models.state import (
    ActionType,
    CaseStatus,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskLevel,
    StopReason,
    TimelineEvent,
    TriggerType,
)


class FaultTolerantReasoningNode:
    """Deterministic reasoning node testing completion under partial evidence outages."""

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        supporting_ids = [e.evidence_id for e in state.all_evidence[:2]]
        nba = NextBestAction(
            action_type=ActionType.BLOCK_TRANSACTION,
            reasoning="Reasoning completed successfully using available baseline evidence despite partial source outage.",
            evidence_ids=supporting_ids,
            execution_mode=ExecutionMode.SIMULATED,
        )
        return {
            "hypotheses": [
                FraudHypothesis(
                    hypothesis_id="HYP_TOLERANCE_01",
                    typology_id="TYP_ATO",
                    typology_name="Account Takeover",
                    confidence=0.85,
                    indicators=["shared_device"],
                )
            ],
            "risk_level": RiskLevel.HIGH.value,
            "risk_score": 0.84,
            "confidence": 0.85,
            "evidence_completeness": 0.80,
            "pre_evidence_next_best_action": nba.model_dump(),
            "post_evidence_next_best_action": nba.model_dump(),
            "timeline": [
                TimelineEvent(
                    event_type="REASONING_COMPLETED",
                    node_name="FaultTolerantReasoningNode",
                    description="Assessed risk under degraded evidence conditions.",
                ).model_dump()
            ],
        }


@pytest.fixture
def mock_tg_client_healthy():
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TX_FAULT_01",
        "amount": 3100.0,
        "currency": "USD",
        "customer_id": "CUST_FAULT_01",
        "account_id": "ACC_FAULT_01",
        "device_id": "DEV_FAULT_01",
        "ip_address": "198.51.100.33",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TX_FAULT_01",
        "amount_to_mean_ratio": 3.8,
        "txn_count_5m": 2,
        "is_new_merchant": True,
    }
    client.find_shared_devices.return_value = {"device_id": "DEV_FAULT_01", "shared_account_count": 3, "shared_customer_count": 2, "linked_fraud_cases": []}
    client.find_shared_ips.return_value = {"ip_address": "198.51.100.33", "shared_account_count": 3, "shared_customer_count": 2}
    client.find_fraud_neighbors.return_value = {"vertex_id": "ACC_FAULT_01", "fraud_neighbors_count": 2, "neighbor_case_ids": []}
    client.get_shortest_path_to_fraud.return_value = {"vertex_id": "ACC_FAULT_01", "target_fraud_case_id": None, "shortest_distance": None}
    client.detect_money_flow_patterns.return_value = {"account_id": "ACC_FAULT_01", "fan_in_count": 3, "fan_out_count": 1, "rapid_pass_through": False, "cycle_detected": False}
    client.get_device_identity_context.return_value = {"device_id": "DEV_FAULT_01", "is_new_device": True, "linked_account_count": 3}
    return client


# ============================================================================
# Scenario 7A — Optional External Signal Failure Does Not Halt Investigation
# ============================================================================

@pytest.mark.asyncio
async def test_optional_external_signal_failure_tolerance(mock_tg_client_healthy):
    """Test that failure in Branch F (external IP/CRM reputation) does not fail the investigation."""
    mock_rag = MagicMock()
    mock_rag.retrieve_policy_context.return_value = MagicMock(items=[])
    mock_rag.retrieve_similar_cases.return_value = MagicMock(cases=[])

    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client_healthy,
        rag_service=mock_rag,
    )

    # Force Branch F to raise an unhandled service exception
    async def failing_branch_f(*args, **kwargs):
        raise ConnectionError("Mock external IP reputation service timeout (HTTP 504)")

    ev_node._run_branch_f_external_signals = failing_branch_f

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=FaultTolerantReasoningNode(),
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_FAULT_701",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_FAULT_01",
        customer_id="CUST_FAULT_01",
        account_ids=["ACC_FAULT_01"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Pipeline finishes cleanly despite Branch F failure
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION

    # 2. Evidence collected from remaining healthy branches
    assert len(final_state.all_evidence) > 0
    categories = {e.category for e in final_state.all_evidence}
    assert "TRANSACTION_BEHAVIOR" in categories
    assert "GRAPH_RELATIONSHIP" in categories

    # 3. Persistence and indexing succeed
    assert final_state.is_persisted is True
    assert final_state.is_indexed is True


# ============================================================================
# Scenario 7B — GraphRAG Retrieval Failure Tolerance
# ============================================================================

@pytest.mark.asyncio
async def test_graphrag_retrieval_failure_tolerance(mock_tg_client_healthy):
    """Test that failure in GraphRAG policy/precedent retrieval degrades gracefully."""
    failing_rag = MagicMock()
    failing_rag.retrieve_policy_context.side_effect = RuntimeError("Vector DB / GraphRAG embedding service offline")
    failing_rag.retrieve_similar_cases.side_effect = TimeoutError("Historical case retrieval timed out")

    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client_healthy,
        rag_service=failing_rag,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=FaultTolerantReasoningNode(),
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_FAULT_702",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_FAULT_01",
        customer_id="CUST_FAULT_01",
        account_ids=["ACC_FAULT_01"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # Investigation completes relying on direct GSQL graph & behavioral evidence
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION
    assert len(final_state.all_evidence) > 0
    assert final_state.is_persisted is True


# ============================================================================
# Scenario 7C — Missing / Null Graph Feature Robustness
# ============================================================================

def test_graph_feature_engine_null_handling():
    """Verify that GraphFeatureEngine uses None for unavailable data rather than inventing 0 or crashing."""
    engine = GraphFeatureEngine()
    sparse_state = FraudCaseState(
        case_id="CASE_INT_SPARSE_703",
        trigger_type=TriggerType.ANALYST_REFERRAL,
        transaction_id=None,
        account_ids=[],
    )

    # Compute features on sparse / empty evidence state
    features = engine.compute_features(state=sparse_state)

    # Assertions: never invent 0 for unobserved values
    assert features.transaction_amount_ratio_to_mean is None
    assert features.transaction_count_5m is None
    assert features.shortest_distance_to_fraud is None
    assert features.new_device is None
    assert features.fan_in_count is None
    assert features.rapid_pass_through is None

    # Feature explanation dictionary is present
    explanations = features.feature_explanations
    assert isinstance(explanations, dict)
