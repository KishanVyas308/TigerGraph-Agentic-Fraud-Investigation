"""Human Approval Service (Layer 20).

Manages analyst approval workflows for governed actions (e.g. BLOCK_ACCOUNT, FILE_SAR).
Handles analyst decision options:
- APPROVE: Proceed with authorized recommendation.
- REJECT: Cancel action and return to safe fallback/monitoring.
- MODIFY: Re-evaluate analyst modified action through PolicyEngine.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
)
from backend.app.policies.engine import PolicyCheckResult, PolicyEngine
from backend.app.utils.ids import generate_prefixed_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("actions.approval")


class ApprovalRequest(BaseModel):
    """Pending approval request presented to human fraud analyst."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    request_id: str = Field(default_factory=lambda: generate_prefixed_id("APPREQ", 8))
    case_id: str
    action: NextBestAction
    required_role: ApprovalRole
    reasoning: str
    created_at: str = Field(default_factory=now_iso)
    details: Dict[str, Any] = Field(default_factory=dict)


def process_analyst_decision(
    state: FraudCaseState,
    decision: ApprovalDecision,
    policy_engine: Optional[PolicyEngine] = None,
) -> Dict[str, Any]:
    """Apply human analyst decision (APPROVE, REJECT, MODIFY) to FraudCaseState."""
    engine = policy_engine or PolicyEngine()
    current_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action

    status_val = (
        decision.status.value
        if hasattr(decision.status, "value")
        else str(decision.status)
    )

    patch: Dict[str, Any] = {
        "approval_decisions": [decision.model_dump()],
        "approval_status": status_val,
    }

    if status_val == ApprovalStatus.APPROVED.value:
        logger.info(
            "Analyst APPROVED action for case %s (Reviewer: %s, Role: %s)",
            state.case_id,
            decision.reviewer_id or "ANONYMOUS",
            decision.reviewer_role,
        )
        patch["approval_required"] = False
        patch["case_status"] = CaseStatus.APPROVED.value
        if current_nba:
            # Set authorized NBA execution mode
            auth_nba = current_nba.model_copy()
            patch["post_evidence_next_best_action"] = auth_nba.model_dump()

        patch["timeline"] = [
            TimelineEvent(
                event_type="HUMAN_APPROVAL_GRANTED",
                node_name="human_approval",
                description=(
                    f"Analyst ({decision.reviewer_id or 'ANALYST'}) APPROVED action "
                    f"'{current_nba.action_type if current_nba else 'UNKNOWN'}'. Comments: {decision.comments or 'None'}"
                ),
                details={
                    "reviewer_id": decision.reviewer_id,
                    "reviewer_role": str(decision.reviewer_role),
                    "action_type": str(current_nba.action_type) if current_nba else None,
                    "comments": decision.comments,
                },
            ).model_dump()
        ]

    elif status_val == ApprovalStatus.REJECTED.value:
        logger.info(
            "Analyst REJECTED action for case %s (Reviewer: %s). Reason: %s",
            state.case_id,
            decision.reviewer_id or "ANONYMOUS",
            decision.comments,
        )
        patch["approval_required"] = False
        patch["case_status"] = CaseStatus.IN_PROGRESS.value

        # Construct safe fallback action on rejection
        fallback_action = NextBestAction(
            action_type=ActionType.MONITOR_TRANSACTION,
            target_entity_id=state.transaction_id or state.case_id,
            target_entity_type="TRANSACTION",
            reasoning=f"[ANALYST REJECTED] Rejection reason: {decision.comments or 'Action rejected by reviewer.'}",
            policy_reference="REJECTED_FALLBACK_MONITOR",
            approval_required=False,
            execution_mode=ExecutionMode.SIMULATED,
        )
        patch["post_evidence_next_best_action"] = fallback_action.model_dump()

        patch["timeline"] = [
            TimelineEvent(
                event_type="HUMAN_APPROVAL_REJECTED",
                node_name="human_approval",
                description=(
                    f"Analyst ({decision.reviewer_id or 'ANALYST'}) REJECTED action. "
                    f"Fallback set to MONITOR_TRANSACTION. Comments: {decision.comments or 'None'}"
                ),
                details={
                    "reviewer_id": decision.reviewer_id,
                    "reviewer_role": str(decision.reviewer_role),
                    "rejection_comments": decision.comments,
                    "fallback_action": ActionType.MONITOR_TRANSACTION.value,
                },
            ).model_dump()
        ]

    elif status_val == ApprovalStatus.MODIFIED.value:
        logger.info("Analyst MODIFIED action for case %s", state.case_id)
        modified = decision.modified_action
        if not modified:
            logger.error("Decision status is MODIFIED but no modified_action provided. Falling back to MONITOR.")
            modified = NextBestAction(
                action_type=ActionType.MONITOR_TRANSACTION,
                reasoning="Analyst modified action missing; defaulted to monitoring.",
            )

        # Re-run modified action through PolicyEngine
        policy_res: PolicyCheckResult = engine.evaluate_action(modified, state)
        authorized_modified = policy_res.authorized_action

        if policy_res.allowed:
            patch["approval_required"] = policy_res.approval_required
            patch["case_status"] = (
                CaseStatus.AWAITING_APPROVAL.value
                if policy_res.approval_required
                else CaseStatus.APPROVED.value
            )
        else:
            patch["approval_required"] = True
            patch["case_status"] = CaseStatus.AWAITING_APPROVAL.value

        patch["post_evidence_next_best_action"] = authorized_modified.model_dump()

        patch["timeline"] = [
            TimelineEvent(
                event_type="HUMAN_APPROVAL_MODIFIED",
                node_name="human_approval",
                description=(
                    f"Analyst MODIFIED action to '{authorized_modified.action_type}'. "
                    f"Policy check status: allowed={policy_res.allowed}. Comments: {decision.comments or 'None'}"
                ),
                details={
                    "reviewer_id": decision.reviewer_id,
                    "reviewer_role": str(decision.reviewer_role),
                    "modified_action": str(authorized_modified.action_type),
                    "policy_allowed": policy_res.allowed,
                    "policy_reference": policy_res.policy_reference,
                    "comments": decision.comments,
                },
            ).model_dump()
        ]

    return patch
