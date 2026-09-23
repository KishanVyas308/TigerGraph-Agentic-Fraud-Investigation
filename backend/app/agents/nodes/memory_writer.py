"""TigerGraph Memory Writer LangGraph Node (Layer 24).

Orchestrates persisting the complete finalized investigation into TigerGraph
graph memory within the LangGraph lifecycle:
- Transforms FraudCaseState into connected vertex and edge payloads.
- Calls CaseMemoryWriter to write vertices, edges, and case update queries.
- Preserves pre-evidence and post-evidence decision history.
- Returns state patch updating is_persisted, case_memory_id, and timeline.
"""

from typing import Any, Dict, Optional

from backend.app.models.state import FraudCaseState
from backend.app.services.case_memory_writer import CaseMemoryWriter
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.memory_writer")


class MemoryWriterNode:
    """LangGraph node managing case memory persistence to TigerGraph."""

    def __init__(self, writer: Optional[CaseMemoryWriter] = None):
        self.writer = writer or CaseMemoryWriter()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Persist case memory to TigerGraph and return state patch for LangGraph.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary containing is_persisted, case_memory_id, and timeline.
        """
        logger.info("Executing memory writer node for case %s", state.case_id)
        receipt, patch = self.writer.write_case_memory(state)
        logger.info(
            "Case memory written successfully for %s (Memory ID: %s, Vertices: %d, Edges: %d)",
            state.case_id,
            receipt.case_memory_id,
            receipt.total_vertices_count,
            receipt.total_edges_count,
        )
        return patch
