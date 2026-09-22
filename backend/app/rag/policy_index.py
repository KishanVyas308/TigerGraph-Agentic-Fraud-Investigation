"""Policy and Governance Vector Index for GraphRAG."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import polars as pl
from pydantic import BaseModel, Field

from backend.app.rag.chunking import RAGChunk
from backend.app.rag.embeddings import compute_embedding, cosine_similarity
from backend.app.utils.logging import get_logger

logger = get_logger("rag.policy_index")


class PolicyIndexRecord(BaseModel):
    chunk_id: str
    source_id: str
    section_title: str
    document_type: str
    text: str
    graph_references: List[str] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)


class PolicyVectorIndex:
    """In-memory and Parquet-backed semantic index for policies, typologies, and regulations."""

    def __init__(self):
        self._records: List[PolicyIndexRecord] = []

    def add_chunks(self, chunks: List[RAGChunk]) -> None:
        """Embed and index chunks."""
        logger.info("Indexing %d chunks into PolicyVectorIndex...", len(chunks))
        for chunk in chunks:
            emb = compute_embedding(chunk.text)
            self._records.append(PolicyIndexRecord(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                section_title=chunk.section_title,
                document_type=chunk.document_type,
                text=chunk.text,
                graph_references=chunk.graph_references,
                embedding=emb,
            ))
        logger.info("Total policy index records: %d", len(self._records))

    def search(
        self,
        query_text: str,
        top_k: int = 3,
        document_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top_k semantically relevant policy or typology chunks."""
        if not self._records:
            logger.warning("PolicyVectorIndex is empty.")
            return []

        query_vec = compute_embedding(query_text)
        candidates = [
            r for r in self._records
            if document_type is None or r.document_type == document_type
        ]

        scored: List[Tuple[float, PolicyIndexRecord]] = []
        for rec in candidates:
            score = cosine_similarity(query_vec, rec.embedding)
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[Dict[str, Any]] = []
        for score, rec in scored[:top_k]:
            results.append({
                "score": round(score, 4),
                "chunk_id": rec.chunk_id,
                "source_id": rec.source_id,
                "section_title": rec.section_title,
                "document_type": rec.document_type,
                "text": rec.text,
                "graph_references": rec.graph_references,
            })
        return results

    def save_to_parquet(self, output_path: Path) -> None:
        """Serialize index records to Parquet."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dicts = [r.model_dump() for r in self._records]
        pl.DataFrame(dicts).write_parquet(output_path)
        logger.info("Saved %d policy records to %s", len(dicts), output_path)

    def load_from_parquet(self, input_path: Path) -> None:
        """Load index records from Parquet."""
        if not input_path.exists():
            raise FileNotFoundError(f"Policy index file not found: {input_path}")
        df = pl.read_parquet(input_path)
        self._records = [PolicyIndexRecord(**r) for r in df.to_dicts()]
        logger.info("Loaded %d policy records from %s", len(self._records), input_path)
