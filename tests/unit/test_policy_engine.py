"""Unit tests for Deterministic Policy Engine and Policy Gate Node (Layer 19)."""

import asyncio
from backend.app.agents.nodes.policy_gate import PolicyGateNode
from backend.app.models.state import (
    ActionType,
    ApprovalRole,
    CaseStatus,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
)
from backend.app.policies.engine import PolicyCheckResult, PolicyEngine
from backend.app.policies.loader import load_policy_config


def test_policy_loader():
    """Test policy config loader returns valid rule dictionary."""
    rules = load_policy_config()
    assert isinstance(rules, dict)
    assert "BLOCK_TRANSACTION" in rules
    assert "BLOCK_ACCOUNT" in rules
    assert "FILE_SAR" in rules
    assert rules["BLOCK_ACCOUNT"]["approval_role"] == "SENIOR_ANALYST"


def test_policy_engine_authorized_allow_transaction():
    """Test evaluating valid ALLOW_TRANSACTION on low risk state."""
    engine = PolicyEngine()
    state = FraudCaseState(
        case_id="CASE_001",
        risk_score=0.20,
        transaction_id="TX_100",
    )
    nba = NextBestAction(
        action_type=ActionType.ALLOW_TRANSACTION,
        reasoning="Low risk transaction",
        confidence=0.9,
    )
    res: PolicyCheckResult = engine.evaluate_action(nba, state)

    assert res.allowed is True
    assert res.autonomous is True
    assert res.approval_required is False
    assert res.authorized_action.action_type == ActionType.ALLOW_TRANSACTION
    assert res.policy_reference == "POL_003"


def test_policy_engine_rejection_risk_threshold():
    """Test policy engine rejecting ALLOW_TRANSACTION when risk score exceeds limit."""
    engine = PolicyEngine()
    state = FraudCaseState(
        case_id="CASE_002",
        risk_score=0.95,  # Exceeds ALLOW_TRANSACTION max allowed (0.70)
        transaction_id="TX_200",
    )
    nba = NextBestAction(
        action_type=ActionType.ALLOW_TRANSACTION,
        reasoning="Model incorrectly suggested allow",
        confidence=0.8,
    )
    res: PolicyCheckResult = engine.evaluate_action(nba, state)

    assert res.allowed is False
    assert res.rejection_reason is not None
    assert "exceeds maximum allowed" in res.rejection_reason
    # Safe fallback for high risk (0.95) should be ESCALATE_ANALYST
    assert res.authorized_action.action_type in [ActionType.ESCALATE_ANALYST, ActionType.MONITOR_TRANSACTION]


def test_policy_engine_governed_account_block():
    """Test BLOCK_ACCOUNT requiring SENIOR_ANALYST approval."""
    engine = PolicyEngine()
    state = FraudCaseState(
        case_id="CASE_003",
        risk_score=0.85,
        customer_id="CUST_300",
        account_ids=["ACC_300"],
    )
    nba = NextBestAction(
        action_type=ActionType.BLOCK_ACCOUNT,
        reasoning="Suspicious account cluster",
    )
    res: PolicyCheckResult = engine.evaluate_action(nba, state)

    assert res.allowed is True
    assert res.autonomous is False
    assert res.approval_required is True
    assert res.approval_role == ApprovalRole.SENIOR_ANALYST
    assert res.policy_reference == "POL_002"
    assert res.authorized_action.approval_required is True


def test_policy_engine_sar_report_required():
    """Test FILE_SAR requiring COMPLIANCE_OFFICER and report_required=True."""
    engine = PolicyEngine()
    state = FraudCaseState(
        case_id="CASE_004",
        risk_score=0.90,
        customer_id="CUST_400",
    )
    nba = NextBestAction(
        action_type=ActionType.FILE_SAR,
        reasoning="Illicit flow threshold breached",
    )
    res: PolicyCheckResult = engine.evaluate_action(nba, state)

    assert res.allowed is True
    assert res.report_required is True
    assert res.approval_role == ApprovalRole.COMPLIANCE_OFFICER
    assert res.policy_reference == "POL_004"


def test_policy_engine_missing_prerequisites():
    """Test disallowing action when required entity prerequisites are missing."""
    engine = PolicyEngine()
    # Missing transaction_id for BLOCK_TRANSACTION
    state = FraudCaseState(
        case_id="CASE_005",
        risk_score=0.80,
    )
    nba = NextBestAction(
        action_type=ActionType.BLOCK_TRANSACTION,
        reasoning="Block transaction",
    )
    res: PolicyCheckResult = engine.evaluate_action(nba, state)

    assert res.allowed is False
    assert "Missing transaction_id" in res.unmet_prerequisites


def test_policy_gate_node_process():
    """Test PolicyGateNode processing FraudCaseState patch generation."""
    gate = PolicyGateNode()
    state = FraudCaseState(
        case_id="CASE_006",
        risk_score=0.85,
        customer_id="CUST_600",
        account_ids=["ACC_600"],
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Freeze compromised account",
        ),
    )

    async def _test():
        return await gate.process(state)

    patch = asyncio.run(_test())

    assert patch["case_status"] == CaseStatus.AWAITING_APPROVAL.value
    assert "post_evidence_next_best_action" in patch
    assert patch["post_evidence_next_best_action"]["approval_required"] is True
    assert patch["post_evidence_next_best_action"]["approval_role"] == ApprovalRole.SENIOR_ANALYST.value
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "POLICY_GATE_EVALUATED"
