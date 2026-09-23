"""Policy Gate Node (Layer 19).

The Policy Gate node intercepts LLM-recommended next-best actions in FraudCaseState,
evaluates them against the deterministic PolicyEngine, updates the action authorization,
and sets case_status accordingly (e.g. AWAITING_APPROVAL if human approval is required).
"""

from typing import Any, Dict, Optional
from backend.app.models.state import (
    CaseStatus,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
)
from backend.app.policies.engine import PolicyCheckResult, PolicyEngine
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.policy_gate")


class PolicyGateNode:
    """LangGraph node enforcing deterministic policy authorization on recommended actions."""

    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        self.policy_engine = policy_engine or PolicyEngine()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Process FraudCaseState through PolicyEngine and produce state update patch."""
        # Retrieve candidate NBA from state (post_evidence_next_best_action or pre_evidence_next_best_action)
        recommended_nba = (
            state.post_evidence_next_best_action
            or state.pre_evidence_next_best_action
        )

        if not recommended_nba:
            logger.warning("No recommended next-best action found in state for case %s.", state.case_id)
            return {
                "case_status": CaseStatus.IN_PROGRESS.value,
                "timeline": [
                    TimelineEvent(
                        event_type="POLICY_CHECK_SKIPPED",
                        node_name="policy_gate",
                        description="Policy check skipped: No recommended next-best action present.",
                        details={"case_id": state.case_id},
                    ).model_dump()
                ],
            }

        # Evaluate through deterministic PolicyEngine
        result: PolicyCheckResult = self.policy_engine.evaluate_action(recommended_nba, state)

        # Update next-best action with authorized action
        authorized_nba: NextBestAction = result.authorized_action

        # Determine target case status based on approval and policy requirements
        if result.approval_required:
            target_status = CaseStatus.AWAITING_APPROVAL.value
        elif not result.allowed:
            target_status = CaseStatus.AWAITING_APPROVAL.value
        else:
            target_status = CaseStatus.APPROVED.value

        # Construct patch dictionary
        patch: Dict[str, Any] = {
            "post_evidence_next_best_action": authorized_nba.model_dump(),
            "case_status": target_status,
        }

        rec_action_val = (
            recommended_nba.action_type.value
            if hasattr(recommended_nba.action_type, "value")
            else str(recommended_nba.action_type)
        )
        auth_action_val = (
            authorized_nba.action_type.value
            if hasattr(authorized_nba.action_type, "value")
            else str(authorized_nba.action_type)
        )
        role_val = (
            result.approval_role.value
            if hasattr(result.approval_role, "value")
            else str(result.approval_role)
        ) if result.approval_role else "NONE"

        # Add timeline event with provenance
        event = TimelineEvent(
            event_type="POLICY_GATE_EVALUATED",
            node_name="policy_gate",
            description=(
                f"Policy Gate evaluated '{rec_action_val}'. "
                f"Allowed: {result.allowed}, Approval Required: {result.approval_required} "
                f"({role_val}). Ref: {result.policy_reference}"
            ),
            details={
                "original_action": rec_action_val,
                "authorized_action": auth_action_val,
                "allowed": result.allowed,
                "autonomous": result.autonomous,
                "approval_required": result.approval_required,
                "approval_role": role_val if result.approval_role else None,
                "report_required": result.report_required,
                "policy_reference": result.policy_reference,
                "rejection_reason": result.rejection_reason,
                "unmet_prerequisites": result.unmet_prerequisites,
            },
        )
        patch["timeline"] = [event.model_dump()]

        logger.info(
            "PolicyGateNode completed for case %s: %s -> %s (Status: %s)",
            state.case_id,
            rec_action_val,
            auth_action_val,
            target_status,
        )

        return patch
