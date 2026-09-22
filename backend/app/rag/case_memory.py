"""Historical Case Memory Index for GraphRAG Precedent Retrieval."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import polars as pl
from pydantic import BaseModel, Field

from backend.app.rag.chunking import RAGChunk
from backend.app.rag.embeddings import compute_embedding, cosine_similarity
from backend.app.utils.logging import get_logger

logger = get_logger("rag.case_memory")


class CaseMemoryRecord(BaseModel):
    chunk_id: str
    case_id: str
    outcome: str
    primary_typology: str
    text: str
    graph_references: List[str] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)


class CaseMemoryIndex:
    """Vector and keyword index over resolved historical fraud cases for precedent memory."""

    def __init__(self):
        self._records: List[CaseMemoryRecord] = []

    def add_cases(self, case_chunks: List[RAGChunk]) -> None:
        """Embed and index historical case chunks."""
        logger.info("Indexing %d historical case chunks into CaseMemoryIndex...", len(case_chunks))
        for chunk in case_chunks:
            # Strictly prevent benchmark leakage
            if chunk.source_id.startswith("CASE_"):
                logger.warning("Skipping benchmark case ID from case memory index: %s", chunk.source_id)
                continue

            outcome = chunk.graph_references[0] if len(chunk.graph_references) > 0 else "UNKNOWN"
            typology = chunk.graph_references[1] if len(chunk.graph_references) > 1 else "GENERAL"

            emb = compute_embedding(chunk.text)
            self._records.append(CaseMemoryRecord(
                chunk_id=chunk.chunk_id,
                case_id=chunk.source_id,
                outcome=outcome,
                primary_typology=typology,
                text=chunk.text,
                graph_references=chunk.graph_references,
                embedding=emb,
            ))
        logger.info("Total historical case memory records: %d", len(self._records))

    def search_similar_cases(
        self,
        query_text: str,
        top_k: int = 3,
        outcome_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top_k similar historical case precedents."""
        if not self._records:
            logger.warning("CaseMemoryIndex is empty.")
            return []

        query_vec = compute_embedding(query_text)
        candidates = [
            r for r in self._records
            if outcome_filter is None or r.outcome == outcome_filter
        ]

        scored: List[Tuple[float, CaseMemoryRecord]] = []
        for rec in candidates:
            score = cosine_similarity(query_vec, rec.embedding)
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[Dict[str, Any]] = []
        for score, rec in scored[:top_k]:
            results.append({
                "score": round(score, 4),
                "case_id": rec.case_id,
                "outcome": rec.outcome,
                "primary_typology": rec.primary_typology,
                "text": rec.text,
                "graph_references": rec.graph_references,
            })
        return results

    def save_to_parquet(self, output_path: Path) -> None:
        """Serialize case memory records to Parquet."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dicts = [r.model_dump() for r in self._records]
        pl.DataFrame(dicts).write_parquet(output_path)
        logger.info("Saved %d case memory records to %s", len(dicts), output_path)

    def load_from_parquet(self, input_path: Path) -> None:
        """Load case memory records from Parquet."""
        if not input_path.exists():
            raise FileNotFoundError(f"Case memory index file not found: {input_path}")
        df = pl.read_parquet(input_path)
        self._records = [CaseMemoryRecord(**r) for r in df.to_dicts()]
        logger.info("Loaded %d case memory records from %s", len(self._records), input_path)
