"""Case Summary Embedder LangGraph Node (Layer 25).

Orchestrates vectorizing finalized case summaries and appending them into
the GraphRAG case memory vector index within the LangGraph lifecycle:
- Synthesizes grounded case summary from verified state.
- Computes SentenceTransformer embedding vector.
- Upserts case precedent record into CaseMemoryIndex and persists to Parquet.
- Enforces strict benchmark isolation (CASE_001 to CASE_020 are quarantined).
- Emits timeline audit event and returns state patch with is_indexed and embedding_id.
"""

from typing import Any, Dict, Optional

from backend.app.models.state import FraudCaseState, TimelineEvent
from backend.app.rag.case_indexer import CaseMemoryIndexer
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.case_indexer")


class CaseSummaryEmbedderNode:
    """LangGraph node managing case summary vector embedding and case memory indexing."""

    def __init__(self, indexer: Optional[CaseMemoryIndexer] = None):
        self.indexer = indexer or CaseMemoryIndexer()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Embed case summary, update case memory index, and return state patch.

        Args:
            state: Finalized FraudCaseState.

        Returns:
            State patch dictionary with is_indexed, embedding_id, and timeline event.
        """
        logger.info("Executing case summary embedder node for case %s", state.case_id)
        receipt = self.indexer.index_case(state)

        event_type = "CASE_EMBEDDING_INDEXED" if receipt.is_indexed else "CASE_EMBEDDING_QUARANTINED"
        description = (
            f"Indexed case summary into case memory vector index (dim={receipt.embedding_dim}, chunk={receipt.chunk_id})"
            if receipt.is_indexed
            else f"Case summary quarantined from case memory: {receipt.quarantine_reason}"
        )

        timeline_event = TimelineEvent(
            event_type=event_type,
            node_name="CaseSummaryEmbedderNode",
            description=description,
            details=receipt.model_dump(),
        )

        logger.info(
            "Case summary embedder completed for %s: is_indexed=%s, quarantined=%s",
            state.case_id,
            receipt.is_indexed,
            receipt.quarantined,
        )

        return {
            "is_indexed": receipt.is_indexed,
            "embedding_id": receipt.chunk_id if receipt.is_indexed else None,
            "timeline": [timeline_event],
        }
