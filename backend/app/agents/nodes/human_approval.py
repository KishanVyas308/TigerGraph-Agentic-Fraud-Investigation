"""Human Approval LangGraph Node (Layer 20).

Handles LangGraph interrupt/resume semantics for human analyst approval.
Pauses case execution when case_status is AWAITING_APPROVAL, and resumes workflow
once an analyst decision (APPROVE, REJECT, MODIFY) is received.
"""

from typing import Any, Dict, Optional
from backend.app.actions.approval import process_analyst_decision
from backend.app.models.state import (
    ApprovalDecision,
    ApprovalRole,
    CaseStatus,
    FraudCaseState,
    TimelineEvent,
)
from backend.app.policies.engine import PolicyEngine
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.human_approval")


class HumanApprovalNode:
    """LangGraph node managing human analyst approval pause and resume transitions."""

    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        self.policy_engine = policy_engine or PolicyEngine()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Process human approval gate for FraudCaseState."""
        current_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action

        # Check if analyst decision is already attached in state
        latest_decision: Optional[ApprovalDecision] = (
            state.approval_decisions[-1] if state.approval_decisions else None
        )

        if latest_decision:
            logger.info("Processing existing analyst decision for case %s", state.case_id)
            return process_analyst_decision(state, latest_decision, self.policy_engine)

        # If no decision yet, check if approval is required
        if state.case_status == CaseStatus.AWAITING_APPROVAL or state.approval_required:
            logger.info(
                "Case %s requires human approval (Role: %s). Interrupting workflow.",
                state.case_id,
                current_nba.approval_role if current_nba else ApprovalRole.ANALYST,
            )
            req_role = (
                str(current_nba.approval_role)
                if current_nba and current_nba.approval_role
                else ApprovalRole.ANALYST.value
            )

            patch: Dict[str, Any] = {
                "case_status": CaseStatus.AWAITING_APPROVAL.value,
                "approval_required": True,
                "timeline": [
                    TimelineEvent(
                        event_type="HUMAN_APPROVAL_PENDING",
                        node_name="human_approval",
                        description=(
                            f"Workflow paused awaiting analyst approval ({req_role}) "
                            f"for action '{current_nba.action_type if current_nba else 'UNKNOWN'}'."
                        ),
                        details={
                            "case_id": state.case_id,
                            "required_role": req_role,
                            "action_type": str(current_nba.action_type) if current_nba else None,
                        },
                    ).model_dump()
                ],
            }
            return patch

        # Approval not required
        logger.info("Human approval not required for case %s. Continuing workflow.", state.case_id)
        return {
            "case_status": CaseStatus.APPROVED.value,
            "approval_required": False,
        }
