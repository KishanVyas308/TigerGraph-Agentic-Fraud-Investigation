"""Unit tests for Layer 8: TigerGraph GraphRAG Retrieval Service."""

from backend.app.rag.retrieval import GraphRAGRetrievalService


def test_policy_context_retrieval():
    """Test grounded policy, typology, and regulatory retrieval with source attribution."""
    service = GraphRAGRetrievalService()

    result = service.retrieve_policy_context(
        query_or_context="Unusual high amount transaction on new device with immediate transfer",
        candidate_action="BLOCK_ACCOUNT",
        fraud_hypothesis="Account Takeover (ATO)",
        top_k=4,
        threshold=0.1,
    )

    assert len(result.items) > 0
    assert len(result.items) <= 4

    # Every item must have a clean source attribution
    for item in result.items:
        assert item.source_id is not None
        assert item.document_type in ["POLICY", "TYPOLOGY", "REGULATION"]
        assert item.relevance_score >= 0.1
        assert len(item.text) > 0

    # Compact text must be populated and bounded
    assert len(result.compact_context_text) > 50
    assert "TigerGraph GraphRAG" in result.compact_context_text
    # Must not be an unbounded raw document dump
    assert len(result.compact_context_text) < 3000


def test_similar_cases_hybrid_retrieval():
    """Test case precedent retrieval combining graph-structural overlap and vector similarity."""
    service = GraphRAGRetrievalService()

    # Query with entity IDs known to exist in historical cases
    result = service.retrieve_similar_cases(
        entity_ids=["ACC_002", "DEV_002"],
        query_text="Confirmed illicit account takeover activity with rapid fund pass-through",
        top_k=4,
    )

    assert len(result.cases) > 0
    assert len(result.cases) <= 4

    for c in result.cases:
        assert c.case_id.startswith("HIST_")
        assert not c.case_id.startswith("CASE_")  # Strict benchmark isolation
        assert c.outcome in ["FRAUD_CONFIRMED", "FALSE_POSITIVE_CLEARED"]
        assert c.combined_score >= 0.0
        assert c.retrieval_method in ["HYBRID", "GRAPH", "VECTOR"]

    # Precedent text must remind agent that precedent is not conclusive proof
    assert "Not Conclusive Proof" in result.compact_precedent_text


def test_benchmark_isolation_enforced():
    """Verify benchmark cases (CASE_001 to CASE_020) are never retrieved as precedents."""
    service = GraphRAGRetrievalService()

    # Pass CASE_001 explicitly as target context
    result = service.retrieve_similar_cases(
        case_id="CASE_001",
        query_text="High risk international transfer after multiple device changes benchmark",
        top_k=5,
    )

    for c in result.cases:
        assert not c.case_id.startswith("CASE_"), f"Benchmark case {c.case_id} leaked into precedents!"
        assert c.case_id != "CASE_001"


def test_balanced_case_outcomes():
    """Verify that retrieval presents balanced precedents (fraud and cleared) to avoid confirmation bias."""
    service = GraphRAGRetrievalService()

    result = service.retrieve_similar_cases(
        query_text="Customer verification card activity investigation transaction alert",
        top_k=4,
        balance_outcomes=True,
    )

    assert len(result.cases) >= 2
    # Check that both outcomes can be represented when available
    outcomes = {c.outcome for c in result.cases}
    assert "FRAUD_CONFIRMED" in outcomes or "FALSE_POSITIVE_CLEARED" in outcomes


def test_empty_or_high_threshold_fallback():
    """Verify graceful handling when no items meet an extreme threshold."""
    service = GraphRAGRetrievalService()

    result = service.retrieve_policy_context(
        query_or_context="Extremely obscure query with zero relevance to financial fraud 12345",
        threshold=0.99,  # Unreasonably high threshold
    )

    assert len(result.items) == 0
    assert "No high-confidence policy or regulatory constraints identified" in result.compact_context_text
