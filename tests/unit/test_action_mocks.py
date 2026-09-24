"""Unit tests for Mock Evidence and Action Services (Layer 35 Deliverable).

Comprehensive verification of:
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
from tests.unit.test_mock_actions import (
    test_action_executor_node_approved_action,
    test_action_executor_node_autonomous,
    test_action_executor_node_close_case_completion,
    test_action_executor_node_defers_pending_approval,
    test_ingest_mock_evidence_state_patch,
    test_mock_action_allow_transaction,
    test_mock_action_block_account,
    test_mock_action_block_transaction,
    test_mock_action_close_case,
    test_mock_action_escalate_analyst,
    test_mock_action_file_sar,
    test_mock_action_no_action,
    test_mock_action_warn_customer,
    test_mock_analyst_evidence_submission,
    test_mock_customer_confirmation_authorized,
    test_mock_customer_confirmation_denied,
    test_mock_external_reputation,
    test_mock_step_up_auth_failed,
    test_mock_step_up_auth_passed,
)


def test_simulation_disclaimer_integrity():
    """Verify that every mock action explicitly contains the non-production disclaimer."""
    service = MockActionExecutionService()
    action = NextBestAction(
        action_type=ActionType.BLOCK_ACCOUNT,
        reasoning="Suspicious activity warrants immediate containment.",
    )
    state = FraudCaseState(case_id="CASE_DISCLAIMER_CHECK", account_ids=["ACC_DISC_1"])
    execution, event, patch = service.execute(action, state)

    assert execution.execution_mode == ExecutionMode.SIMULATED.value
    assert event.details["disclaimer"] == SIMULATION_DISCLAIMER
    assert "disclaimer" in event.details
