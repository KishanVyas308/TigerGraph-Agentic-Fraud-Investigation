"""Simulated Action Execution LangGraph Node (Layer 21).

Executes authorized banking actions in simulated mode (`execution_mode = SIMULATED`).
Verifies policy clearance and human approval status before applying mock actions,
appends typed execution records to `state.executed_actions`, records timeline milestones,
and updates lifecycle case status.
"""

from typing import Any, Dict, Optional
from backend.app.actions.mocks import MockActionExecutionService
from backend.app.models.state import (
    ActionType,
    CaseStatus,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
)
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.action_executor")


class ActionExecutorNode:
    """LangGraph node orchestrating simulated banking action execution."""

    def __init__(self, service: Optional[MockActionExecutionService] = None):
        self.service = service or MockActionExecutionService()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Execute or simulate authorized next-best action for FraudCaseState.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary containing executed_actions, timeline, and updated status.
        """
        action: Optional[NextBestAction] = (
            state.post_evidence_next_best_action or state.pre_evidence_next_best_action
        )

        if not action:
            logger.warning("No action available for execution in case %s", state.case_id)
            return {}

        # If action requires approval and has not been approved, pause execution
        if state.approval_required or state.case_status == CaseStatus.AWAITING_APPROVAL:
            logger.info(
                "Action '%s' in case %s is awaiting human approval. Execution deferred.",
                action.action_type,
                state.case_id,
            )
            return {
                "timeline": [
                    TimelineEvent(
                        event_type="ACTION_EXECUTION_DEFERRED",
                        node_name="action_executor",
                        description=(
                            f"Execution of action '{action.action_type}' deferred pending "
                            f"required human approval ({action.approval_role or 'ANALYST'})."
                        ),
                        details={
                            "action_type": str(action.action_type),
                            "required_role": str(action.approval_role),
                            "case_status": CaseStatus.AWAITING_APPROVAL.value,
                        },
                    ).model_dump()
                ]
            }

        # Action is authorized (autonomous or approved) -> simulate execution
        exec_record, timeline_event, details = self.service.execute_action(action, state)

        patch: Dict[str, Any] = {
            "executed_actions": [exec_record.model_dump()],
            "timeline": [timeline_event.model_dump()],
        }

        # Lifecycle status transitions
        if action.action_type == ActionType.CLOSE_CASE:
            patch["case_status"] = CaseStatus.COMPLETED.value
        elif state.case_status == CaseStatus.APPROVED:
            # Successfully executed approved action -> return to IN_PROGRESS/FINALIZING
            patch["case_status"] = CaseStatus.IN_PROGRESS.value

        logger.info(
            "Successfully simulated action '%s' for case %s (Execution ID: %s)",
            action.action_type,
            state.case_id,
            exec_record.execution_id,
        )

        return patch
