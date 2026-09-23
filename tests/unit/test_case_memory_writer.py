"""Unit tests for TigerGraph Case Memory Writer Service and MemoryWriterNode (Layer 24).

Verifies:
- Graph memory payload construction conforming to fraud_schema.gsql:
  * FraudCase vertex
  * Evidence vertices with source and reliability
  * Append-oriented Decision records preserving both pre-evidence and post-evidence actions
  * Action vertices with execution modes and payloads
  * Approval vertices with reviewer role, comments, and decisions
  * Entity relationship edges (Transaction, Account, Device, IPAddress)
  * Policy citations and typology match edges
- write_case_update query dispatch and CaseMemoryReceipt generation
- Offline simulation fallback support
- MemoryWriterNode async process within LangGraph lifecycle
- State reducer merge integration for is_persisted and case_memory_id
"""

import asyncio
from backend.app.agents.nodes.memory_writer import MemoryWriterNode
from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    EvidenceReliability,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskLevel,
    StopReason,
    TriggerType,
    merge_fraud_case_state,
)
from backend.app.services.case_memory_writer import CaseMemoryReceipt, CaseMemoryWriter


def _create_sample_finalized_state() -> FraudCaseState:
    """Helper creating a rich finalized state with pre and post decisions."""
    ev1 = EvidenceItem(
        evidence_id="EVD_MEM_01",
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Transaction TX_MEM_01 for $9,200.00 via Account ACC_MEM_01",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["TX_MEM_01", "ACC_MEM_01"],
    )
    ev2 = EvidenceItem(
        evidence_id="EVD_MEM_02",
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.DEVICE,
        fact="Originated from Device DEV_MEM_99 and IP 203.0.113.5",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["DEV_MEM_99", "203.0.113.5"],
    )
    ev3 = EvidenceItem(
        evidence_id="EVD_MEM_03",
        source="POLICY_GRAPHRAG",
        category=EvidenceCategory.POLICY,
        fact="Policy POL_004 mandates SAR filing on illicit flow > $5,000",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["POL_004"],
    )

    return FraudCaseState(
        case_id="CASE_MEM_01",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        customer_id="CUST_MEM_01",
        transaction_id="TX_MEM_01",
        account_ids=["ACC_MEM_01"],
        transaction_evidence=[ev1],
        device_evidence=[ev2],
        policy_evidence=[ev3],
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="TYP_MULE",
                title="Mule Ring & Layering",
                description="Rapid pass-through network",
                likelihood=0.90,
            )
        ],
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.92,
        confidence=0.88,
        evidence_completeness=0.85,
        case_status=CaseStatus.COMPLETED,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
        case_summary="Case finalized with confirmed mule ring.",
        # Recommendation history: pre and post actions preserved
        pre_evidence_next_best_action=NextBestAction(
            action_type=ActionType.REQUEST_CUSTOMER_CONFIRMATION,
            reasoning="Uncertain before customer confirmation",
        ),
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Confirmed mule ring following confirmation denial",
            policy_reference="POL_002",
        ),
        executed_actions=[
            ActionExecution(
                action_type=ActionType.BLOCK_ACCOUNT,
                execution_mode=ExecutionMode.SIMULATED,
                success=True,
                result={"hold_status": "ADMINISTRATIVE_FREEZE"},
            )
        ],
        approval_decisions=[
            ApprovalDecision(
                action_type=ActionType.BLOCK_ACCOUNT,
                status=ApprovalStatus.APPROVED,
                reviewer_role=ApprovalRole.SENIOR_ANALYST,
                reviewer_id="SENIOR_ANALYST_01",
                comments="Approved account freeze.",
            )
        ],
        sar_reference="SAR_REF_MEM_01",
    )


def test_build_graph_memory_payload_completeness():
    """Verify build_graph_memory_payload creates all vertex and edge types."""
    writer = CaseMemoryWriter()
    state = _create_sample_finalized_state()

    payload = writer.build_graph_memory_payload(state)
    vertices = payload["vertices"]
    edges = payload["edges"]

    # 1. FraudCase vertex checks
    assert "CASE_MEM_01" in vertices["FraudCase"]
    case_v = vertices["FraudCase"]["CASE_MEM_01"]
    assert case_v["outcome"] == "FRAUD_CONFIRMED"
    assert case_v["primary_typology"] == "Mule Ring & Layering"
    assert case_v["risk_level"] == "CRITICAL"
    assert case_v["stop_reason"] == "SUFFICIENT_EVIDENCE_FOR_ACTION"

    # 2. Evidence vertices checks
    assert "EVD_MEM_01" in vertices["Evidence"]
    assert "EVD_MEM_02" in vertices["Evidence"]
    assert "EVD_MEM_03" in vertices["Evidence"]

    # 3. Decision vertices: both PRE and POST decisions are preserved
    assert "DEC_PRE_CASE_MEM_01" in vertices["Decision"]
    assert "DEC_POST_CASE_MEM_01" in vertices["Decision"]
    dec_pre = vertices["Decision"]["DEC_PRE_CASE_MEM_01"]
    dec_post = vertices["Decision"]["DEC_POST_CASE_MEM_01"]
    assert dec_pre["recommended_action"] == "REQUEST_CUSTOMER_CONFIRMATION"
    assert dec_post["recommended_action"] == "BLOCK_ACCOUNT"

    # 4. Action and Approval vertices
    assert len(vertices["Action"]) == 1
    assert len(vertices["Approval"]) == 1

    # 5. Edge checks
    assert any(e["to_id"] == "TX_MEM_01" for e in edges["CASE_INVESTIGATES_TRANSACTION"])
    assert any(e["to_id"] == "ACC_MEM_01" for e in edges["CASE_INVESTIGATES_ACCOUNT"])
    assert any(e["to_id"] == "DEV_MEM_99" for e in edges["CASE_INVESTIGATES_DEVICE"])

    # Decisions linked to case
    dec_edges = edges["CASE_HAS_DECISION"]
    assert any(e["to_id"] == "DEC_PRE_CASE_MEM_01" for e in dec_edges)
    assert any(e["to_id"] == "DEC_POST_CASE_MEM_01" for e in dec_edges)

    # Evidence linked to case and entities
    assert any(e["to_id"] == "EVD_MEM_01" for e in edges["CASE_HAS_EVIDENCE"])
    assert any(e["to_id"] == "TX_MEM_01" for e in edges["EVIDENCE_LINKED_TRANSACTION"])
    assert any(e["to_id"] == "DEV_MEM_99" for e in edges["EVIDENCE_LINKED_DEVICE"])

    # Policy and Typology edges
    assert any(e["to_id"] == "TYP_MULE" for e in edges["CASE_MATCHES_TYPOLOGY"])
    assert any(e["to_id"] == "POL_002" for e in edges["CASE_CITES_POLICY"])


def test_write_case_memory_receipt_and_patch():
    """Verify write_case_memory returns valid CaseMemoryReceipt and patch."""
    writer = CaseMemoryWriter()
    state = _create_sample_finalized_state()

    receipt, patch = writer.write_case_memory(state)

    assert receipt.case_id == "CASE_MEM_01"
    assert receipt.case_memory_id.startswith("MEM_")
    assert receipt.status == "PERSISTED_IN_GRAPH_MEMORY"
    assert receipt.pre_recommendation_persisted is True
    assert receipt.post_recommendation_persisted is True
    assert receipt.total_vertices_count > 0
    assert receipt.total_edges_count > 0

    assert patch["is_persisted"] is True
    assert patch["case_memory_id"] == receipt.case_memory_id
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "CASE_MEMORY_PERSISTED"


def test_memory_writer_node_async_process():
    """Verify MemoryWriterNode executing in async LangGraph node pattern."""
    node = MemoryWriterNode()
    state = _create_sample_finalized_state()

    patch = asyncio.run(node.process(state))

    assert patch["is_persisted"] is True
    assert "case_memory_id" in patch
    assert len(patch["timeline"]) == 1


def test_state_merge_reducer_with_memory_patch():
    """Verify merge_fraud_case_state incorporates is_persisted and case_memory_id."""
    state = _create_sample_finalized_state()
    writer = CaseMemoryWriter()
    receipt, patch = writer.write_case_memory(state)

    merged = merge_fraud_case_state(state, patch)

    assert merged.is_persisted is True
    assert merged.case_memory_id == receipt.case_memory_id
    assert any(t.event_type == "CASE_MEMORY_PERSISTED" for t in merged.timeline)
