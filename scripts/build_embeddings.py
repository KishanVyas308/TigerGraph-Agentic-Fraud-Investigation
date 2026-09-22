#!/usr/bin/env python3
"""Build and serialize GraphRAG knowledge indices for policies and case memory."""

import argparse
from pathlib import Path
import polars as pl

from backend.app.rag.chunking import (
    chunk_historical_cases,
    chunk_policies,
    chunk_regulatory_guidelines,
    chunk_typologies,
)
from backend.app.rag.case_memory import CaseMemoryIndex
from backend.app.rag.policy_index import PolicyVectorIndex
from backend.app.utils.logging import get_logger, setup_logging

setup_logging("INFO")
logger = get_logger("scripts.build_embeddings")


def build_knowledge_indices(processed_dir: Path) -> None:
    """Read processed tables, generate embeddings, and serialize indices."""
    logger.info("Building GraphRAG knowledge indices from %s...", processed_dir)

    policies_pq = processed_dir / "policies.parquet"
    typologies_pq = processed_dir / "typologies.parquet"
    cases_pq = processed_dir / "historical_cases.parquet"

    if not (policies_pq.exists() and typologies_pq.exists() and cases_pq.exists()):
        raise FileNotFoundError("Required Parquet tables missing in processed directory.")

    policies_df = pl.read_parquet(policies_pq)
    typologies_df = pl.read_parquet(typologies_pq)
    cases_df = pl.read_parquet(cases_pq)

    # 1. Chunk policies, typologies, regulations
    policy_chunks = chunk_policies(policies_df)
    typology_chunks = chunk_typologies(typologies_df)
    reg_chunks = chunk_regulatory_guidelines()

    all_policy_chunks = policy_chunks + typology_chunks + reg_chunks

    # Build and save Policy Vector Index
    policy_index = PolicyVectorIndex()
    policy_index.add_chunks(all_policy_chunks)
    policy_index_path = processed_dir / "policy_index.parquet"
    policy_index.save_to_parquet(policy_index_path)

    # 2. Chunk and build Case Memory Index
    case_chunks = chunk_historical_cases(cases_df)
    case_memory_index = CaseMemoryIndex()
    case_memory_index.add_cases(case_chunks)
    case_memory_path = processed_dir / "case_memory_index.parquet"
    case_memory_index.save_to_parquet(case_memory_path)

    logger.info("Successfully built and serialized all GraphRAG knowledge indices!")
    print("\n--- GraphRAG Knowledge Build Summary ---")
    print(f"Policy / Typology / Regulation chunks: {len(all_policy_chunks)} -> {policy_index_path.name}")
    print(f"Historical Case Precedent chunks: {len(case_chunks)} -> {case_memory_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GraphRAG embeddings indices.")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Path to processed data directory",
    )
    args = parser.parse_args()
    build_knowledge_indices(args.processed_dir)


if __name__ == "__main__":
    main()
