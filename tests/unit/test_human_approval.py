"""Unit tests for Human Approval Service and HumanApprovalNode (Layer 20)."""

import asyncio
from backend.app.actions.approval import ApprovalRequest, process_analyst_decision
from backend.app.agents.nodes.human_approval import HumanApprovalNode
from backend.app.models.state import (
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
)


def test_process_analyst_decision_approve():
    """Test analyst APPROVE decision processing."""
    state = FraudCaseState(
        case_id="CASE_APP_01",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Device cluster suspicious",
            approval_required=True,
            approval_role=ApprovalRole.SENIOR_ANALYST,
        ),
    )
    decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.APPROVED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="ANALYST_42",
        comments="Approved after phone verification.",
    )

    patch = process_analyst_decision(state, decision)

    assert patch["approval_required"] is False
    assert patch["case_status"] == CaseStatus.APPROVED.value
    assert len(patch["approval_decisions"]) == 1
    assert patch["approval_decisions"][0]["status"] == ApprovalStatus.APPROVED.value
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "HUMAN_APPROVAL_GRANTED"


def test_process_analyst_decision_reject():
    """Test analyst REJECT decision processing."""
    state = FraudCaseState(
        case_id="CASE_APP_02",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Device cluster suspicious",
        ),
    )
    decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.REJECTED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="ANALYST_99",
        comments="Known corporate shared tablet.",
    )

    patch = process_analyst_decision(state, decision)

    assert patch["approval_required"] is False
    assert patch["case_status"] == CaseStatus.IN_PROGRESS.value
    assert patch["post_evidence_next_best_action"]["action_type"] == ActionType.MONITOR_TRANSACTION.value
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "HUMAN_APPROVAL_REJECTED"


def test_process_analyst_decision_modify():
    """Test analyst MODIFY decision processing."""
    state = FraudCaseState(
        case_id="CASE_APP_03",
        transaction_id="TX_333",
        customer_id="CUST_333",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Device cluster suspicious",
        ),
    )
    modified_nba = NextBestAction(
        action_type=ActionType.WARN_CUSTOMER,
        reasoning="Downgraded block account to customer warning.",
    )
    decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.MODIFIED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="ANALYST_101",
        comments="Downgrading to customer warning.",
        modified_action=modified_nba,
    )

    patch = process_analyst_decision(state, decision)

    assert patch["case_status"] in [CaseStatus.APPROVED.value, CaseStatus.AWAITING_APPROVAL.value]
    assert patch["post_evidence_next_best_action"]["action_type"] == ActionType.WARN_CUSTOMER.value
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "HUMAN_APPROVAL_MODIFIED"


def test_human_approval_node_pending():
    """Test HumanApprovalNode interrupting when approval is pending."""
    node = HumanApprovalNode()
    state = FraudCaseState(
        case_id="CASE_APP_04",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.FILE_SAR,
            reasoning="High illicit flow",
            approval_role=ApprovalRole.COMPLIANCE_OFFICER,
        ),
    )

    async def _test():
        return await node.process(state)

    patch = asyncio.run(_test())

    assert patch["case_status"] == CaseStatus.AWAITING_APPROVAL.value
    assert patch["approval_required"] is True
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "HUMAN_APPROVAL_PENDING"


def test_human_approval_node_resume_with_decision():
    """Test HumanApprovalNode resuming workflow when decision is present in state."""
    node = HumanApprovalNode()
    decision = ApprovalDecision(
        action_type=ActionType.FILE_SAR,
        status=ApprovalStatus.APPROVED,
        reviewer_role=ApprovalRole.COMPLIANCE_OFFICER,
        reviewer_id="OFFICER_07",
        comments="SAR filing approved.",
    )
    state = FraudCaseState(
        case_id="CASE_APP_05",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        approval_decisions=[decision],
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.FILE_SAR,
            reasoning="High illicit flow",
        ),
    )

    async def _test():
        return await node.process(state)

    patch = asyncio.run(_test())

    assert patch["case_status"] == CaseStatus.APPROVED.value
    assert patch["approval_required"] is False
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "HUMAN_APPROVAL_GRANTED"
