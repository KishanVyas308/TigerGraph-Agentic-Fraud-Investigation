"""Finalizer LangGraph Node (Layer 23).

Coordinates the finalization stage of a fraud investigation in the LangGraph workflow:
- Validates case integrity and governance invariants.
- Resolves an explicit StopReason (never closes silently).
- Consolidates final risk, confidence, evidence, and SAR reporting states.
- Generates human-auditable text summaries and structured FinalCaseSummary data.
- Transitions lifecycle case status to COMPLETED or paused at AWAITING_APPROVAL.
"""

from typing import Any, Dict, Optional

from backend.app.models.state import FraudCaseState, StopReason
from backend.app.services.finalizer import CaseFinalizer
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.finalizer")


class FinalizerNode:
    """LangGraph node managing case finalization and stop condition enforcement."""

    def __init__(self, finalizer: Optional[CaseFinalizer] = None):
        self.finalizer = finalizer or CaseFinalizer()

    async def process(
        self,
        state: FraudCaseState,
        explicit_stop_reason: Optional[StopReason] = None,
    ) -> Dict[str, Any]:
        """Execute finalization logic and return state patch for LangGraph.

        Args:
            state: Current FraudCaseState.
            explicit_stop_reason: Optional explicit StopReason override.

        Returns:
            State patch dictionary containing updated status, stop reason, summaries,
            and timeline event.
        """
        logger.info("Executing finalizer node for case %s", state.case_id)
        summary_model, patch = self.finalizer.finalize_case(
            state,
            stop_reason=explicit_stop_reason,
        )
        return patch
