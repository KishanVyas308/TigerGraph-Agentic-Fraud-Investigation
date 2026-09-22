"""Unit tests for GraphRAG chunking, embeddings, policy index, and case memory."""

from pathlib import Path
import polars as pl
import pytest

from backend.app.rag.chunking import (
    RAGChunk,
    chunk_historical_cases,
    chunk_policies,
    chunk_regulatory_guidelines,
    chunk_typologies,
)
from backend.app.rag.embeddings import compute_embedding, cosine_similarity, EMBEDDING_DIM
from backend.app.rag.policy_index import PolicyVectorIndex
from backend.app.rag.case_memory import CaseMemoryIndex


@pytest.fixture
def processed_dir():
    return Path("data/processed")


def test_chunking_policies_and_typologies(processed_dir):
    """Verify policies and typologies are parsed into structured semantic chunks."""
    policies_df = pl.read_parquet(processed_dir / "policies.parquet")
    typologies_df = pl.read_parquet(processed_dir / "typologies.parquet")

    p_chunks = chunk_policies(policies_df)
    t_chunks = chunk_typologies(typologies_df)

    assert len(p_chunks) == len(policies_df)
    assert len(t_chunks) == len(typologies_df)

    p1 = p_chunks[0]
    assert p1.document_type == "POLICY"
    assert p1.source_id.startswith("POL_")
    assert len(p1.graph_references) > 0

    t1 = t_chunks[0]
    assert t1.document_type == "TYPOLOGY"
    assert t1.source_id.startswith("TYP_")


def test_chunk_regulatory_guidelines():
    """Verify standard regulatory AML/fraud guidelines are generated."""
    reg_chunks = chunk_regulatory_guidelines()
    assert len(reg_chunks) >= 3
    source_ids = [c.source_id for c in reg_chunks]
    assert "REG_FINCEN_SAR" in source_ids
    assert "REG_REG_E" in source_ids


def test_chunk_historical_cases_no_benchmark_leakage(processed_dir):
    """Verify historical cases are chunked and strictly isolate benchmark case IDs."""
    hist_df = pl.read_parquet(processed_dir / "historical_cases.parquet")
    c_chunks = chunk_historical_cases(hist_df)

    assert len(c_chunks) == len(hist_df)
    for chunk in c_chunks:
        assert chunk.source_id.startswith("HIST_")
        assert not chunk.source_id.startswith("CASE_")
        assert chunk.document_type == "HISTORICAL_CASE"


def test_embedding_generation_and_cosine_similarity():
    """Verify embedding output dimension and cosine similarity math."""
    v1 = compute_embedding("Critical account takeover risk alert")
    v2 = compute_embedding("Critical account takeover risk alert")
    v3 = compute_embedding("Routine grocery shopping transaction")

    assert len(v1) == EMBEDDING_DIM
    assert len(v2) == EMBEDDING_DIM

    sim_identical = cosine_similarity(v1, v2)
    assert abs(sim_identical - 1.0) < 1e-4

    sim_different = cosine_similarity(v1, v3)
    assert sim_different < sim_identical


def test_policy_vector_index_search(processed_dir, tmp_path):
    """Verify policy vector index matches relevant policy and saves to Parquet."""
    policies_df = pl.read_parquet(processed_dir / "policies.parquet")
    chunks = chunk_policies(policies_df)

    index = PolicyVectorIndex()
    index.add_chunks(chunks)

    results = index.search("Critical risk immediate block required", top_k=2)
    assert len(results) == 2
    assert results[0]["score"] > 0.0
    assert "source_id" in results[0]

    # Test Parquet serialization and reloading
    save_path = tmp_path / "policy_test_index.parquet"
    index.save_to_parquet(save_path)
    assert save_path.exists()

    reloaded = PolicyVectorIndex()
    reloaded.load_from_parquet(save_path)
    reloaded_results = reloaded.search("Critical risk immediate block required", top_k=2)
    assert len(reloaded_results) == 2
    assert reloaded_results[0]["chunk_id"] == results[0]["chunk_id"]


def test_case_memory_index_search(processed_dir, tmp_path):
    """Verify case memory index retrieves historical precedents and excludes benchmark IDs."""
    hist_df = pl.read_parquet(processed_dir / "historical_cases.parquet")
    chunks = chunk_historical_cases(hist_df)

    # Attempt to inject a benchmark chunk to verify filter
    leaked_chunk = RAGChunk(
        chunk_id="CHK_CASE_001",
        source_id="CASE_001",
        section_title="Benchmark Case 1",
        document_type="HISTORICAL_CASE",
        text="Benchmark test case outcome cheat",
        graph_references=["CHEAT"],
    )
    chunks_with_attempted_leak = chunks + [leaked_chunk]

    index = CaseMemoryIndex()
    index.add_cases(chunks_with_attempted_leak)

    # Benchmark ID must be dropped
    case_ids = [r.case_id for r in index._records]
    assert "CASE_001" not in case_ids

    results = index.search_similar_cases("Mule account ring pass-through", top_k=3)
    assert len(results) == 3
    assert all(r["case_id"].startswith("HIST_") for r in results)

    # Test Parquet serialization
    save_path = tmp_path / "case_memory_test.parquet"
    index.save_to_parquet(save_path)
    assert save_path.exists()

    reloaded = CaseMemoryIndex()
    reloaded.load_from_parquet(save_path)
    assert len(reloaded._records) == len(index._records)
