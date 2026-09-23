"""Unit tests for Mock Evidence and Action Services (Layer 21).

Verifies:
- Mock Customer Confirmation Service (confirm / deny)
- Mock Step-Up Authentication Service (pass / fail)
- Mock Analyst Evidence Service
- Mock External Reputation Service
- Mock Action Execution across permitted ActionTypes
- Simulated mode enforcement (execution_mode = SIMULATED)
- Audit safety disclaimer inclusion
- Mock evidence ingestion and state transitions
- ActionExecutorNode execution, deferral, and completion
"""

import asyncio
import pytest

from backend.app.actions.base import SIMULATION_DISCLAIMER, SimulatedActionResult
from backend.app.actions.mocks import (
    MockActionExecutionService,
    MockAnalystEvidenceService,
    MockCustomerConfirmationService,
    MockExternalReputationService,
    MockStepUpAuthService,
    ingest_mock_evidence,
)
from backend.app.agents.nodes.action_executor import ActionExecutorNode
from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ApprovalRole,
    CaseStatus,
    EvidenceCategory,
    EvidenceReliability,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
)


# ============================================================================
# Mock Evidence Services Tests
# ============================================================================

def test_mock_customer_confirmation_authorized():
    """Verify customer confirming transaction produces normalized evidence and simulated result."""
    service = MockCustomerConfirmationService()
    result, evidence = service.confirm_transaction(
        transaction_id="TX_1001",
        customer_id="CUST_001",
        channel="SMS",
        confirmed=True,
    )

    assert result.success is True
    assert result.execution_mode == ExecutionMode.SIMULATED.value
    assert result.disclaimer == SIMULATION_DISCLAIMER
    assert result.details["confirmed_authorized"] is True
    assert result.details["status"] == "AUTHORIZED"

    assert len(evidence) == 1
    item = evidence[0]
    assert item.category == EvidenceCategory.CUSTOMER_RESPONSE.value
    assert item.source == "CUSTOMER_RESPONSE"
    assert item.reliability == EvidenceReliability.HIGH.value
    assert "CONFIRMED AUTHORIZED" in item.fact
    assert "TX_1001" in item.entity_ids


def test_mock_customer_confirmation_denied():
    """Verify customer reporting unauthorized fraud produces proper evidence flags."""
    service = MockCustomerConfirmationService()
    result, evidence = service.deny_transaction(
        transaction_id="TX_1002",
        customer_id="CUST_002",
        channel="PUSH",
    )

    assert result.success is True
    assert result.execution_mode == ExecutionMode.SIMULATED.value
    assert result.details["confirmed_authorized"] is False
    assert result.details["status"] == "UNAUTHORIZED_FRAUD_REPORTED"

    assert len(evidence) == 1
    item = evidence[0]
    assert item.category == EvidenceCategory.CUSTOMER_RESPONSE.value
    assert "DENIED / REPORTED UNAUTHORIZED" in item.fact


def test_mock_step_up_auth_passed():
    """Verify successful step-up authentication challenge."""
    service = MockStepUpAuthService()
    result, evidence = service.authenticate(
        customer_id="CUST_003",
        transaction_id="TX_1003",
        method="BIOMETRIC",
        passed=True,
        attempts=1,
    )

    assert result.success is True
    assert result.execution_mode == ExecutionMode.SIMULATED.value
    assert result.disclaimer == SIMULATION_DISCLAIMER
    assert result.details["status"] == "PASSED"

    assert len(evidence) == 1
    item = evidence[0]
    assert item.category == EvidenceCategory.AUTHENTICATION.value
    assert item.source == "AUTHENTICATION_SERVICE"
    assert "PASSED" in item.fact


def test_mock_step_up_auth_failed():
    """Verify failed step-up authentication challenge."""
    service = MockStepUpAuthService()
    result, evidence = service.fail_authentication(
        customer_id="CUST_004",
        transaction_id="TX_1004",
        method="OTP_SMS",
        attempts=3,
    )

    assert result.success is True
    assert result.execution_mode == ExecutionMode.SIMULATED.value
    assert "FAILED_3_ATTEMPTS" in result.details["status"]

    assert len(evidence) == 1
    item = evidence[0]
    assert item.category == EvidenceCategory.AUTHENTICATION.value
    assert "FAILED after 3 attempt(s)" in item.fact


def test_mock_analyst_evidence_submission():
    """Verify human analyst supplemental note submission."""
    service = MockAnalystEvidenceService()
    result, evidence = service.submit_evidence(
        case_id="CASE_SIM_01",
        analyst_id="ANALYST_77",
        note="Customer confirmed traveling in Canada during transaction window.",
    )

    assert result.success is True
    assert result.execution_mode == ExecutionMode.SIMULATED.value
    assert len(evidence) == 1
    item = evidence[0]
    assert item.category == EvidenceCategory.ANALYST_INPUT.value
    assert item.source == "ANALYST_INPUT"
    assert "traveling in Canada" in item.fact


def test_mock_external_reputation():
    """Verify external threat intelligence lookup."""
    service = MockExternalReputationService()
    result, evidence = service.check_reputation(
        entity_id="198.51.100.22",
        provider="IPQualityScore",
        signal_type="IP_REPUTATION",
        score=0.92,
        flag="DATA_CENTER_PROXY",
        details="Known VPN endpoint",
    )

    assert result.success is True
    assert result.execution_mode == ExecutionMode.SIMULATED.value
    assert len(evidence) == 1
    item = evidence[0]
    assert item.category == EvidenceCategory.EXTERNAL_SIGNAL.value
    assert item.source == "EXTERNAL_SIGNAL"
    assert "DATA_CENTER_PROXY" in item.fact


# ============================================================================
# Mock Action Execution Service Tests
# ============================================================================

def test_mock_action_allow_transaction():
    """Verify simulated ALLOW_TRANSACTION action execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_01", transaction_id="TX_ALLOW")
    action = NextBestAction(
        action_type=ActionType.ALLOW_TRANSACTION,
        target_entity_id="TX_ALLOW",
        target_entity_type="TRANSACTION",
        reasoning="Low risk score",
        policy_reference="POL_003",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.success is True
    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert exec_record.action_type == ActionType.ALLOW_TRANSACTION.value
    assert details["disclaimer"] == SIMULATION_DISCLAIMER
    assert details["processing_code"] == "00_APPROVED"
    assert timeline_event.event_type == "ACTION_EXECUTED_SIMULATED"


def test_mock_action_block_transaction():
    """Verify simulated BLOCK_TRANSACTION action execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_02", transaction_id="TX_BLOCK")
    action = NextBestAction(
        action_type=ActionType.BLOCK_TRANSACTION,
        target_entity_id="TX_BLOCK",
        reasoning="Confirmed fraud cluster linkage",
        policy_reference="POL_001",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert details["response_code"] == "59_SUSPECTED_FRAUD"
    assert details["authorization_status"] == "DECLINED"


def test_mock_action_block_account():
    """Verify simulated BLOCK_ACCOUNT action execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(
        case_id="CASE_ACT_03",
        customer_id="CUST_88",
        account_ids=["ACC_01", "ACC_02"],
    )
    action = NextBestAction(
        action_type=ActionType.BLOCK_ACCOUNT,
        target_entity_id="CUST_88",
        reasoning="Multiple mule accounts",
        policy_reference="POL_002",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert details["hold_status"] == "ADMINISTRATIVE_FREEZE"
    assert details["restriction_scope"] == "DEBIT_AND_CREDIT"
    assert "ACC_01" in details["account_ids"]


def test_mock_action_warn_customer():
    """Verify simulated WARN_CUSTOMER action execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_04", customer_id="CUST_99")
    action = NextBestAction(
        action_type=ActionType.WARN_CUSTOMER,
        target_entity_id="CUST_99",
        reasoning="Novel device access",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert details["dispatch_channel"] == "SMS_AND_EMAIL"
    assert details["delivery_status"] == "SENT_SIMULATED"


def test_mock_action_escalate_analyst():
    """Verify simulated ESCALATE_ANALYST action execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_05")
    action = NextBestAction(
        action_type=ActionType.ESCALATE_ANALYST,
        reasoning="Complex synthetic identity syndicate",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert details["queue_priority"] == "P1_URGENT"
    assert details["status"] == "ESCALATED_MANUAL_REVIEW"


def test_mock_action_file_sar():
    """Verify simulated FILE_SAR action execution creates filing reference."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_06", customer_id="CUST_SAR")
    action = NextBestAction(
        action_type=ActionType.FILE_SAR,
        reasoning="Layered illicit money flow > $10,000",
        policy_reference="POL_004",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert "SAR_REF" in details["sar_reference_id"]
    assert details["filing_status"] == "PENDING_REPORT_GENERATION"


def test_mock_action_close_case():
    """Verify simulated CLOSE_CASE action execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_07")
    action = NextBestAction(
        action_type=ActionType.CLOSE_CASE,
        reasoning="Benign activity confirmed by customer",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert details["resolution"] == "INVESTIGATION_CONCLUDED"


def test_mock_action_no_action():
    """Verify simulated NO_ACTION execution."""
    service = MockActionExecutionService()
    state = FraudCaseState(case_id="CASE_ACT_08")
    action = NextBestAction(
        action_type=ActionType.NO_ACTION,
        reasoning="No operational intervention needed",
    )

    exec_record, timeline_event, details = service.execute_action(action, state)

    assert exec_record.execution_mode == ExecutionMode.SIMULATED.value
    assert details["status"] == "NO_OPERATIONAL_CHANGE"


# ============================================================================
# Evidence Ingestion Helper Tests
# ============================================================================

def test_ingest_mock_evidence_state_patch():
    """Verify ingest_mock_evidence appends items and transitions AWAITING_EVIDENCE."""
    cust_service = MockCustomerConfirmationService()
    _, evidence = cust_service.confirm_transaction(
        transaction_id="TX_500",
        customer_id="CUST_500",
        confirmed=True,
    )

    state = FraudCaseState(
        case_id="CASE_INGEST_01",
        case_status=CaseStatus.AWAITING_EVIDENCE,
    )

    patch = ingest_mock_evidence(state, evidence)

    assert len(patch["received_evidence"]) == 1
    assert patch["case_status"] == CaseStatus.IN_PROGRESS.value
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "ADDITIONAL_EVIDENCE_INGESTED"


# ============================================================================
# ActionExecutorNode Tests
# ============================================================================

def test_action_executor_node_autonomous():
    """Verify ActionExecutorNode simulates autonomous permitted action."""
    node = ActionExecutorNode()
    state = FraudCaseState(
        case_id="CASE_NODE_01",
        transaction_id="TX_AUTO",
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.ALLOW_TRANSACTION,
            target_entity_id="TX_AUTO",
            reasoning="Low risk",
            approval_required=False,
        ),
    )

    patch = asyncio.run(node.process(state))

    assert len(patch["executed_actions"]) == 1
    exec_rec = patch["executed_actions"][0]
    assert exec_rec["action_type"] == ActionType.ALLOW_TRANSACTION.value
    assert exec_rec["execution_mode"] == ExecutionMode.SIMULATED.value
    assert len(patch["timeline"]) == 1


def test_action_executor_node_defers_pending_approval():
    """Verify ActionExecutorNode defers execution when approval is pending."""
    node = ActionExecutorNode()
    state = FraudCaseState(
        case_id="CASE_NODE_02",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            approval_required=True,
            approval_role=ApprovalRole.SENIOR_ANALYST,
            reasoning="Device cluster suspicious",
        ),
    )

    patch = asyncio.run(node.process(state))

    assert "executed_actions" not in patch
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "ACTION_EXECUTION_DEFERRED"


def test_action_executor_node_approved_action():
    """Verify ActionExecutorNode executes action once approved."""
    node = ActionExecutorNode()
    state = FraudCaseState(
        case_id="CASE_NODE_03",
        customer_id="CUST_APPR",
        account_ids=["ACC_APPR"],
        approval_required=False,
        case_status=CaseStatus.APPROVED,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Senior analyst approved block",
        ),
    )

    patch = asyncio.run(node.process(state))

    assert len(patch["executed_actions"]) == 1
    assert patch["executed_actions"][0]["action_type"] == ActionType.BLOCK_ACCOUNT.value
    assert patch["case_status"] == CaseStatus.IN_PROGRESS.value


def test_action_executor_node_close_case_completion():
    """Verify ActionExecutorNode transitions case_status to COMPLETED on CLOSE_CASE."""
    node = ActionExecutorNode()
    state = FraudCaseState(
        case_id="CASE_NODE_04",
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.CLOSE_CASE,
            reasoning="Benign activity confirmed",
        ),
    )

    patch = asyncio.run(node.process(state))

    assert patch["case_status"] == CaseStatus.COMPLETED.value
    assert len(patch["executed_actions"]) == 1
    assert patch["executed_actions"][0]["action_type"] == ActionType.CLOSE_CASE.value
