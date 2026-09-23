"""Unit tests for Layer 11: Parallel Evidence Collection Node."""

import asyncio
from unittest.mock import MagicMock
import pytest

from backend.app.agents.nodes.evidence_collection import (
    ParallelEvidenceCollectionNode,
    parallel_evidence_collection_node,
)
from backend.app.models.state import (
    CaseStatus,
    EvidenceCategory,
    FraudCaseState,
    TriggerType,
    merge_fraud_case_state,
)


@pytest.fixture
def mock_tg_client():
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TXN_NODE_1",
        "amount": 3400.0,
        "customer_id": "CUST_NODE_1",
        "account_id": "ACC_NODE_1",
        "device_id": "DEV_NODE_1",
        "ip_address": "10.0.0.99",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TXN_NODE_1",
        "amount_to_mean_ratio": 4.2,
        "txn_count_5m": 2,
        "is_new_merchant": True,
    }
    client.find_shared_devices.return_value = {
        "device_id": "DEV_NODE_1",
        "shared_account_count": 3,
        "shared_customer_count": 2,
        "linked_fraud_cases": ["HIST_99"],
    }
    client.find_shared_ips.return_value = {
        "ip_address": "10.0.0.99",
        "shared_account_count": 4,
        "shared_customer_count": 3,
    }
    client.find_fraud_neighbors.return_value = {
        "vertex_id": "ACC_NODE_1",
        "fraud_neighbors_count": 1,
        "neighbor_case_ids": ["HIST_99"],
    }
    client.get_shortest_path_to_fraud.return_value = {
        "vertex_id": "ACC_NODE_1",
        "target_fraud_case_id": "HIST_99",
        "shortest_distance": 2,
    }
    client.detect_money_flow_patterns.return_value = {
        "account_id": "ACC_NODE_1",
        "fan_in_count": 5,
        "rapid_pass_through": True,
    }
    client.get_device_identity_context.return_value = {
        "device_id": "DEV_NODE_1",
        "is_new_device": True,
        "linked_account_count": 3,
    }
    return client


@pytest.fixture
def mock_rag_service():
    service = MagicMock()
    mock_policy_item = MagicMock()
    mock_policy_item.model_dump.return_value = {
        "chunk_id": "POL_ATO_01",
        "source_id": "POL_BANK_01",
        "document_type": "POLICY",
        "section_title": "Account Takeover Controls",
        "text": "Transactions on new devices exceeding $1,000 require verification.",
        "relevance_score": 0.88,
    }
    service.retrieve_policy_context.return_value = MagicMock(items=[mock_policy_item])

    mock_case_item = MagicMock()
    mock_case_item.model_dump.return_value = {
        "case_id": "HIST_99",
        "outcome": "FRAUD_CONFIRMED",
        "primary_typology": "ATO",
        "summary": "Shared device compromised account takeover.",
        "shared_entities": ["DEV_NODE_1"],
        "combined_score": 0.85,
        "retrieval_method": "HYBRID",
    }
    service.retrieve_similar_cases.return_value = MagicMock(cases=[mock_case_item])
    return service


def test_parallel_evidence_collection_success(mock_tg_client, mock_rag_service):
    """Test successful concurrent execution of all 6 evidence collection branches."""
    async def _test():
        node = ParallelEvidenceCollectionNode(
            tigergraph_client=mock_tg_client,
            rag_service=mock_rag_service,
        )

        state = FraudCaseState(
            case_id="CASE_TEST_NODE",
            trigger_type=TriggerType.TRANSACTION_ALERT,
            transaction_id="TXN_NODE_1",
            account_ids=["ACC_NODE_1"],
            customer_id="CUST_NODE_1",
        )

        patch = await node.execute(state)

        assert patch["case_status"] == CaseStatus.IN_PROGRESS
        assert len(patch["timeline"]) == 1
        assert patch["timeline"][0].event_type == "PARALLEL_EVIDENCE_COLLECTED"

        # Verify all evidence categories are populated
        assert len(patch["transaction_evidence"]) >= 2
        assert len(patch["graph_evidence"]) >= 3
        assert len(patch["device_evidence"]) >= 2
        assert len(patch["identity_evidence"]) >= 1
        assert len(patch["policy_evidence"]) >= 1
        assert len(patch["historical_case_evidence"]) >= 1
        assert len(patch["external_evidence"]) >= 1

        # Apply patch to state using merge_fraud_case_state
        merged = merge_fraud_case_state(state, patch)
        assert merged.case_status == CaseStatus.IN_PROGRESS
        assert len(merged.all_evidence) >= 10

    asyncio.run(_test())


def test_parallel_evidence_collection_fault_tolerance(mock_tg_client, mock_rag_service):
    """Verify that failure of an optional source (GraphRAG policy or external signal) is isolated without crashing the node."""
    async def _test():
        mock_rag_service.retrieve_policy_context.side_effect = Exception("Policy index connection timeout")

        node = ParallelEvidenceCollectionNode(
            tigergraph_client=mock_tg_client,
            rag_service=mock_rag_service,
        )

        state = FraudCaseState(
            case_id="CASE_FAULT_TOLERANT",
            trigger_type=TriggerType.TRANSACTION_ALERT,
            transaction_id="TXN_NODE_1",
            account_ids=["ACC_NODE_1"],
        )

        # Node must complete without raising exception
        patch = await node.execute(state)

        assert patch["case_status"] == CaseStatus.IN_PROGRESS
        assert len(patch["policy_evidence"]) == 0  # Policy branch failed cleanly
        assert len(patch["transaction_evidence"]) >= 2  # Graph & transaction evidence preserved intact!
        assert len(patch["graph_evidence"]) >= 3

    asyncio.run(_test())


def test_parallel_evidence_collection_entrypoint_function(mock_tg_client, mock_rag_service):
    """Test helper entrypoint function parallel_evidence_collection_node."""
    async def _test():
        node = ParallelEvidenceCollectionNode(
            tigergraph_client=mock_tg_client,
            rag_service=mock_rag_service,
        )

        state = FraudCaseState(
            case_id="CASE_ENTRYPOINT",
            transaction_id="TXN_NODE_1",
        )

        patch = await parallel_evidence_collection_node(state, node_instance=node)
        assert patch["case_status"] == CaseStatus.IN_PROGRESS
        assert len(patch["timeline"]) == 1

    asyncio.run(_test())
