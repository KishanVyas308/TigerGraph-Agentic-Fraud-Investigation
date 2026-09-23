"""Unit tests for Layer 25: Case Summary Embedding and Future Retrieval."""

import pytest
from pathlib import Path

from backend.app.agents.nodes.case_indexer import CaseSummaryEmbedderNode
from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskLevel,
    StopReason,
    TimelineEvent,
    TriggerType,
    merge_fraud_case_state,
)
from backend.app.rag.case_indexer import CaseIndexingReceipt, CaseMemoryIndexer
from backend.app.rag.case_memory import CaseMemoryIndex, CaseMemoryRecord, is_benchmark_case
from backend.app.rag.embeddings import compute_embedding
from backend.app.rag.retrieval import GraphRAGRetrievalService


def _create_sample_finalized_state(case_id: str = "CASE_NEW_001") -> FraudCaseState:
    """Helper to create a fully finalized case state for indexing tests."""
    return FraudCaseState(
        case_id=case_id,
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_8888",
        customer_id="CUST_042",
        account_ids=["ACC_042", "ACC_099"],
        transaction_evidence=[
            EvidenceItem(
                evidence_id="EVD_TX_01",
                source="TIGERGRAPH_GSQL",
                source_reference="TX_8888",
                category=EvidenceCategory.TRANSACTION_BEHAVIOR,
                fact="Transaction of $4,500 exceeds customer 90-day mean of $120 by 37.5x.",
                reliability=0.95,
            )
        ],
        device_evidence=[
            EvidenceItem(
                evidence_id="EVD_DEV_01",
                source="TIGERGRAPH_GSQL",
                source_reference="DEV_SHARED_99",
                category=EvidenceCategory.DEVICE,
                fact="Device DEV_SHARED_99 shared across 4 accounts with confirmed fraud links.",
                reliability=0.90,
            )
        ],
        graph_features={
            "shared_device_account_count": 4,
            "shared_ip_account_count": 2,
            "fraud_neighbors_count": 3,
            "shortest_distance_to_fraud": 1,
            "cycle_detected": False,
        },
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="HYP_01",
                typology_id="TYP_ATO",
                typology_name="Account Takeover (ATO)",
                confidence=0.88,
                indicators=["shared_device_cluster", "sudden_amount_spike"],
                supporting_evidence_ids=["EVD_TX_01", "EVD_DEV_01"],
            )
        ],
        risk_level=RiskLevel.HIGH,
        risk_score=0.85,
        confidence=0.90,
        evidence_completeness=0.95,
        supporting_evidence_ids=["EVD_TX_01", "EVD_DEV_01"],
        contradictory_evidence_ids=[],
        pre_evidence_next_best_action=NextBestAction(
            action_type=ActionType.REQUEST_STEP_UP_AUTH,
            reasoning="Pre-evidence: Require customer verification before blocking.",
        ),
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Post-evidence: Device confirmed linked to fraud ring; account block required.",
            approval_required=True,
            approval_role=ApprovalRole.FRAUD_SUPERVISOR,
        ),
        approval_decisions=[
            ApprovalDecision(
                action_type=ActionType.BLOCK_ACCOUNT,
                status=ApprovalStatus.APPROVED,
                reviewer_role=ApprovalRole.FRAUD_SUPERVISOR,
                reviewer_id="ANALYST_JANE",
                comments="Approved based on 1-hop fraud neighbor linkage.",
            )
        ],
        executed_actions=[
            ActionExecution(
                action_type=ActionType.BLOCK_ACCOUNT,
                execution_mode=ExecutionMode.SIMULATED,
                success=True,
                result={"status": "ACCOUNT_BLOCKED"},
            )
        ],
        case_status=CaseStatus.RESOLVED,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
    )


def test_grounded_case_summary_synthesis():
    """Verify case summary is grounded in verified state without ungrounded hallucinations."""
    state = _create_sample_finalized_state()
    indexer = CaseMemoryIndexer(index=CaseMemoryIndex())

    summary = indexer.build_grounded_case_summary(state)

    assert "Case CASE_NEW_001" in summary
    assert "Tx: TX_8888" in summary
    assert "Cust: CUST_042" in summary
    assert "Accounts: ACC_042, ACC_099" in summary
    assert "Shared device across 4 accounts" in summary
    assert "3 fraud-linked graph neighbors" in summary
    assert "Account Takeover (ATO)" in summary
    assert "Pre-evidence Recommendation: REQUEST_STEP_UP_AUTH" in summary
    assert "Post-evidence Recommendation: BLOCK_ACCOUNT" in summary
    assert "Analyst Review: FRAUD_SUPERVISOR APPROVED" in summary
    assert "Actions Executed: BLOCK_ACCOUNT" in summary
    assert "SUFFICIENT_EVIDENCE_FOR_ACTION" in summary
    assert "Risk: HIGH" in summary


def test_embedding_computation_vector():
    """Verify embedding vector is normalized 384-dimensional float vector."""
    text = "Account Takeover investigation involving multi-account device cluster and rapid fund transfer."
    vec = compute_embedding(text)

    assert isinstance(vec, list)
    assert len(vec) == 384
    for val in vec:
        assert isinstance(val, float)

    # L2 norm should be approximately 1.0
    norm = sum(x * x for x in vec) ** 0.5
    assert 0.95 <= norm <= 1.05


def test_case_indexing_and_parquet_persistence(tmp_path: Path):
    """Verify case is vectorized, indexed in-memory, and saved/reloaded to Parquet."""
    parquet_path = tmp_path / "case_memory_index.parquet"
    index = CaseMemoryIndex()
    indexer = CaseMemoryIndexer(index=index, data_dir=tmp_path)

    state = _create_sample_finalized_state("CASE_REC_777")
    receipt = indexer.index_case(state, persist=True, custom_index_path=parquet_path)

    assert receipt.is_indexed is True
    assert receipt.quarantined is False
    assert receipt.case_id == "CASE_REC_777"
    assert receipt.chunk_id == "CHUNK_CASE_REC_777"
    assert receipt.outcome == "FRAUD_CONFIRMED"
    assert receipt.primary_typology == "Account Takeover (ATO)"
    assert receipt.embedding_dim == 384
    assert parquet_path.exists()

    # Reload from Parquet into a new index instance
    new_index = CaseMemoryIndex()
    new_index.load_from_parquet(parquet_path)

    assert len(new_index.records) == 1
    loaded_rec = new_index.get_record("CASE_REC_777")
    assert loaded_rec is not None
    assert loaded_rec.case_id == "CASE_REC_777"
    assert loaded_rec.outcome == "FRAUD_CONFIRMED"
    assert len(loaded_rec.embedding) == 384


def test_benchmark_isolation_quarantine(tmp_path: Path):
    """Verify benchmark test cases (CASE_001 to CASE_020) are strictly quarantined from index."""
    index = CaseMemoryIndex()
    indexer = CaseMemoryIndexer(index=index, data_dir=tmp_path)

    for b_case in ["CASE_001", "CASE_007", "CASE_020"]:
        assert is_benchmark_case(b_case) is True
        state = _create_sample_finalized_state(b_case)
        receipt = indexer.index_case(state, persist=False)

        assert receipt.is_indexed is False
        assert receipt.quarantined is True
        assert "benchmark" in receipt.quarantine_reason.lower()
        assert index.get_record(b_case) is None

    # Normal runtime case is NOT benchmark
    assert is_benchmark_case("CASE_NEW_001") is False
    assert is_benchmark_case("HIST_015") is False
    assert is_benchmark_case(None) is False


def test_dynamic_precedent_retrieval(tmp_path: Path):
    """Verify newly indexed completed cases are retrievable by GraphRAGRetrievalService."""
    parquet_path = tmp_path / "case_memory_index.parquet"
    index = CaseMemoryIndex()
    indexer = CaseMemoryIndexer(index=index, data_dir=tmp_path)

    # Index two distinct cases
    case1 = _create_sample_finalized_state("CASE_CIRCULAR_101")
    case1.hypotheses[0].typology_name = "Circular Money Laundering"
    case1.case_summary = "Investigation CASE_CIRCULAR_101: Identified multi-hop rapid pass-through and circular transaction loop."

    case2 = _create_sample_finalized_state("CASE_CLEARED_102")
    case2.stop_reason = StopReason.NO_MATERIAL_FRAUD_EVIDENCE
    case2.risk_level = RiskLevel.LOW
    case2.executed_actions = [
        ActionExecution(action_type=ActionType.ALLOW_TRANSACTION, result={"status": "ALLOWED"})
    ]
    case2.case_summary = "Investigation CASE_CLEARED_102: Low novelty legitimate retail purchase confirmed via customer SMS."

    indexer.index_case(case1, persist=True, custom_index_path=parquet_path)
    indexer.index_case(case2, persist=True, custom_index_path=parquet_path)

    # Initialize GraphRAGRetrievalService with the temporary index
    service = GraphRAGRetrievalService(case_memory_index=index, data_dir=tmp_path)

    # Query for circular money movement
    result = service.retrieve_similar_cases(
        query_text="Circular fund flow pattern with rapid pass-through loops",
        top_k=5,
    )

    retrieved_ids = [c.case_id for c in result.cases]
    assert "CASE_CIRCULAR_101" in retrieved_ids
    # Confirm benchmark cases are not retrieved
    for cid in retrieved_ids:
        assert not is_benchmark_case(cid)


@pytest.mark.asyncio
async def test_case_summary_embedder_node_async(tmp_path: Path):
    """Verify CaseSummaryEmbedderNode processes state, records timeline event, and returns patch."""
    parquet_path = tmp_path / "case_memory_index.parquet"
    indexer = CaseMemoryIndexer(index=CaseMemoryIndex(), data_dir=tmp_path)
    node = CaseSummaryEmbedderNode(indexer=indexer)

    state = _create_sample_finalized_state("CASE_AGENT_999")
    patch = await node.process(state)

    assert patch["is_indexed"] is True
    assert patch["embedding_id"] == "CHUNK_CASE_AGENT_999"
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0].event_type == "CASE_EMBEDDING_INDEXED"

    # Test benchmark case quarantine in node
    benchmark_state = _create_sample_finalized_state("CASE_003")
    b_patch = await node.process(benchmark_state)

    assert b_patch["is_indexed"] is False
    assert b_patch["embedding_id"] is None
    assert b_patch["timeline"][0].event_type == "CASE_EMBEDDING_QUARANTINED"


def test_state_reducer_merges_indexing_flags():
    """Verify merge_fraud_case_state properly merges is_indexed, embedding_id, and timeline."""
    current_state = FraudCaseState(case_id="CASE_REDUCER_01", is_indexed=False)

    timeline_evt = TimelineEvent(
        event_type="CASE_EMBEDDING_INDEXED",
        node_name="CaseSummaryEmbedderNode",
        description="Indexed case into case memory",
    )

    patch = {
        "is_indexed": True,
        "embedding_id": "CHUNK_CASE_REDUCER_01",
        "timeline": [timeline_evt],
    }

    updated = merge_fraud_case_state(current_state, patch)

    assert updated.is_indexed is True
    assert updated.embedding_id == "CHUNK_CASE_REDUCER_01"
    assert len(updated.timeline) == 1
    assert updated.timeline[0].event_type == "CASE_EMBEDDING_INDEXED"
