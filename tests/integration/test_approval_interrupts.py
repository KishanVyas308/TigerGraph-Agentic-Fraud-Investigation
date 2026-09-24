"""Integration Tests for Layer 36: Human Approval Interrupts & Resume (Scenario 4).

Validates Scenario 4 defined in AGENTS.md §19 & §33:
1. Sensitive action (e.g. BLOCK_ACCOUNT requiring SENIOR_ANALYST authorization) triggers LangGraph interrupt:
   - Workflow pauses in AWAITING_APPROVAL status.
   - Persisted graph write is deferred.
   - Stop reason is set to AWAITING_HUMAN_REVIEW.
2. Resume on APPROVE:
   - Analyst grants approval.
   - Workflow resumes, executes authorized action in SIMULATED mode.
   - Complete timeline preserves APPROVAL_REQUIRED and HUMAN_APPROVAL_GRANTED events.
   - Case successfully finalizes (COMPLETED) and persists to TigerGraph case memory.
3. Resume on REJECT:
   - Analyst rejects sensitive action with justification.
   - Workflow resumes, substitutes safe fallback action (MONITOR_TRANSACTION).
   - Rejected action is NOT executed; timeline captures HUMAN_APPROVAL_REJECTED.
   - Investigation completes without unauthorized account blocking.
4. Resume on MODIFY:
   - Analyst modifies proposed action (e.g., downgrades BLOCK_ACCOUNT to WARN_CUSTOMER).
   - Policy engine re-evaluates modified action.
   - Modified action executes in SIMULATED mode; timeline records HUMAN_APPROVAL_MODIFIED.
"""

from typing import Any, Dict
from unittest.mock import MagicMock
import pytest

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
    create_investigation_graph,
    investigate_case,
)
from backend.app.agents.nodes.evidence_collection import ParallelEvidenceCollectionNode
from backend.app.models.state import (
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    EvidenceReliability,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskLevel,
    StopReason,
    TimelineEvent,
    TriggerType,
)


class SensitiveAccountReasoningNode:
    """Reasoning node recommending sensitive BLOCK_ACCOUNT requiring human supervisor approval."""

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        nba = NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            reasoning="Multi-account device compromise cluster detected; account restriction recommended.",
            execution_mode=ExecutionMode.SIMULATED,
            approval_required=True,
            approval_role=ApprovalRole.SENIOR_ANALYST,
        )
        return {
            "hypotheses": [
                FraudHypothesis(
                    hypothesis_id="HYP_ATO_001",
                    typology_id="TYP_ATO",
                    typology_name="Account Takeover",
                    confidence=0.92,
                    indicators=["shared_emulator_device", "multiple_failed_logins"],
                )
            ],
            "risk_level": RiskLevel.HIGH.value,
            "risk_score": 0.88,
            "confidence": 0.90,
            "evidence_completeness": 0.90,
            "pre_evidence_next_best_action": nba.model_dump(),
            "post_evidence_next_best_action": nba.model_dump(),
            "timeline": [
                TimelineEvent(
                    event_type="REASONING_COMPLETED",
                    node_name="SensitiveAccountReasoningNode",
                    description="Assessed risk as HIGH; recommended BLOCK_ACCOUNT.",
                ).model_dump()
            ],
        }


@pytest.fixture
def mock_tg_client():
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TX_SENSITIVE_101",
        "amount": 4200.0,
        "currency": "USD",
        "customer_id": "CUST_SENSITIVE_101",
        "account_id": "ACC_SENSITIVE_101",
        "device_id": "DEV_SENSITIVE_101",
        "ip_address": "198.51.100.22",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TX_SENSITIVE_101",
        "amount_to_mean_ratio": 4.5,
        "txn_count_5m": 2,
        "is_new_merchant": True,
    }
    client.find_shared_devices.return_value = {
        "device_id": "DEV_SENSITIVE_101",
        "shared_account_count": 4,
        "shared_customer_count": 3,
        "linked_fraud_cases": [],
    }
    client.find_shared_ips.return_value = {
        "ip_address": "198.51.100.22",
        "shared_account_count": 3,
        "shared_customer_count": 2,
    }
    client.find_fraud_neighbors.return_value = {
        "vertex_id": "ACC_SENSITIVE_101",
        "fraud_neighbors_count": 2,
        "neighbor_case_ids": ["HIST_CASE_77"],
    }
    client.get_shortest_path_to_fraud.return_value = {
        "vertex_id": "ACC_SENSITIVE_101",
        "target_fraud_case_id": "HIST_CASE_77",
        "shortest_distance": 2,
    }
    client.detect_money_flow_patterns.return_value = {
        "account_id": "ACC_SENSITIVE_101",
        "fan_in_count": 3,
        "fan_out_count": 1,
        "rapid_pass_through": False,
        "cycle_detected": False,
    }
    client.get_device_identity_context.return_value = {
        "device_id": "DEV_SENSITIVE_101",
        "is_new_device": True,
        "linked_account_count": 4,
    }
    return client


@pytest.fixture
def mock_rag_service():
    service = MagicMock()
    mock_policy = MagicMock()
    mock_policy.model_dump.return_value = {
        "chunk_id": "POL_ATO_002",
        "source_id": "POL_002",
        "document_type": "POLICY",
        "section_title": "Account Restriction Policy",
        "text": "Account restrictions require senior analyst authorization before freezing.",
        "relevance_score": 0.95,
    }
    service.retrieve_policy_context.return_value = MagicMock(items=[mock_policy])
    service.retrieve_similar_cases.return_value = MagicMock(cases=[])
    return service


# ============================================================================
# Scenario 4A — Interrupt and Resume with APPROVE
# ============================================================================

@pytest.mark.asyncio
async def test_human_approval_interrupt_and_resume_approve(mock_tg_client, mock_rag_service):
    """Test pause at AWAITING_APPROVAL and resumption upon analyst APPROVE decision."""
    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client,
        rag_service=mock_rag_service,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=SensitiveAccountReasoningNode(),
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_APPROVE_401",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_SENSITIVE_101",
        customer_id="CUST_SENSITIVE_101",
        account_ids=["ACC_SENSITIVE_101"],
    )

    # Step 1: Initial invocation halts at approval gate
    interrupted_state = await workflow.ainvoke(trigger_state)

    assert interrupted_state.case_status == CaseStatus.AWAITING_APPROVAL
    assert interrupted_state.stop_reason == StopReason.AWAITING_HUMAN_REVIEW
    assert interrupted_state.approval_required is True
    assert interrupted_state.approval_status is None
    assert interrupted_state.is_persisted is False  # Persistence is deferred

    timeline_types_interrupted = [t.event_type for t in interrupted_state.timeline]
    assert "APPROVAL_REQUIRED" in timeline_types_interrupted

    # Step 2: Analyst reviews and grants approval
    analyst_decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.APPROVED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="ANALYST_SARAH_07",
        comments="Confirmed suspicious device cluster with prior ATO incident history.",
    )

    resumed_state = await investigate_case(
        trigger_or_state=interrupted_state,
        workflow=workflow,
        analyst_decision=analyst_decision,
    )

    # Step 3: Resumed investigation completes execution and finalization
    assert resumed_state.case_status == CaseStatus.COMPLETED
    assert resumed_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION
    assert resumed_state.approval_status == ApprovalStatus.APPROVED
    assert resumed_state.is_persisted is True
    assert resumed_state.is_indexed is True

    # Verify executed action
    executed_types = [e.action_type for e in resumed_state.executed_actions]
    assert ActionType.BLOCK_ACCOUNT in executed_types

    # Verify timeline progression
    resumed_timeline = [t.event_type for t in resumed_state.timeline]
    assert "APPROVAL_REQUIRED" in resumed_timeline
    assert "HUMAN_APPROVAL_GRANTED" in resumed_timeline
    assert "ACTION_EXECUTED_SIMULATED" in resumed_timeline
    assert "CASE_FINALIZED" in resumed_timeline
    assert "CASE_MEMORY_PERSISTED" in resumed_timeline


# ============================================================================
# Scenario 4B — Interrupt and Resume with REJECT
# ============================================================================

@pytest.mark.asyncio
async def test_human_approval_interrupt_and_resume_reject(mock_tg_client, mock_rag_service):
    """Test resumption upon analyst REJECT decision substitutes safe monitoring action."""
    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client,
        rag_service=mock_rag_service,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=SensitiveAccountReasoningNode(),
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_REJECT_402",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_SENSITIVE_101",
        customer_id="CUST_SENSITIVE_101",
        account_ids=["ACC_SENSITIVE_101"],
    )

    # Step 1: Halts at approval gate
    interrupted_state = await workflow.ainvoke(trigger_state)
    assert interrupted_state.case_status == CaseStatus.AWAITING_APPROVAL

    # Step 2: Analyst rejects the sensitive account block
    analyst_decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.REJECTED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="SUPERVISOR_DAVID_12",
        comments="Device verified as company executive tablet; legitimate activity. Disallow account block.",
    )

    resumed_state = await investigate_case(
        trigger_or_state=interrupted_state,
        workflow=workflow,
        analyst_decision=analyst_decision,
    )

    # Step 3: Investigation completes safely without executing BLOCK_ACCOUNT
    assert resumed_state.case_status == CaseStatus.COMPLETED
    assert resumed_state.approval_status == ApprovalStatus.REJECTED

    executed_types = [e.action_type for e in resumed_state.executed_actions]
    assert ActionType.BLOCK_ACCOUNT not in executed_types
    assert ActionType.MONITOR_TRANSACTION in executed_types  # Safe fallback action executed

    resumed_timeline = [t.event_type for t in resumed_state.timeline]
    assert "HUMAN_APPROVAL_REJECTED" in resumed_timeline
    assert "ACTION_EXECUTED_SIMULATED" in resumed_timeline
    assert "CASE_FINALIZED" in resumed_timeline


# ============================================================================
# Scenario 4C — Interrupt and Resume with MODIFY
# ============================================================================

@pytest.mark.asyncio
async def test_human_approval_interrupt_and_resume_modify(mock_tg_client, mock_rag_service):
    """Test resumption upon analyst MODIFY decision re-evaluates policy and executes modified action."""
    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client,
        rag_service=mock_rag_service,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=SensitiveAccountReasoningNode(),
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_MODIFY_403",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_SENSITIVE_101",
        customer_id="CUST_SENSITIVE_101",
        account_ids=["ACC_SENSITIVE_101"],
    )

    # Step 1: Halts at approval gate
    interrupted_state = await workflow.ainvoke(trigger_state)
    assert interrupted_state.case_status == CaseStatus.AWAITING_APPROVAL

    # Step 2: Analyst modifies action from BLOCK_ACCOUNT to MONITOR_ACCOUNT (allowed up to 0.90 risk)
    modified_nba = NextBestAction(
        action_type=ActionType.MONITOR_ACCOUNT,
        reasoning="Downgrade full block to enhanced 72-hour account monitoring under active surveillance.",
        execution_mode=ExecutionMode.SIMULATED,
    )

    analyst_decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.MODIFIED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="SUPERVISOR_DAVID_12",
        comments="Downgrade to account monitoring; investigation ongoing.",
        modified_action=modified_nba,
    )

    resumed_state = await investigate_case(
        trigger_or_state=interrupted_state,
        workflow=workflow,
        analyst_decision=analyst_decision,
    )

    # Step 3: Investigation executes policy-authorized modified MONITOR_ACCOUNT action
    assert resumed_state.case_status == CaseStatus.COMPLETED
    assert resumed_state.approval_status == ApprovalStatus.MODIFIED

    executed_types = [e.action_type for e in resumed_state.executed_actions]
    assert ActionType.BLOCK_ACCOUNT not in executed_types
    assert ActionType.MONITOR_ACCOUNT in executed_types

    resumed_timeline = [t.event_type for t in resumed_state.timeline]
    assert "HUMAN_APPROVAL_MODIFIED" in resumed_timeline
    assert "ACTION_EXECUTED_SIMULATED" in resumed_timeline
    assert "CASE_FINALIZED" in resumed_timeline


# ============================================================================
# Scenario 4D — Disallowed Modification Remains Interrupted
# ============================================================================

@pytest.mark.asyncio
async def test_human_approval_disallowed_modification_remains_interrupted(mock_tg_client, mock_rag_service):
    """Test that modifying an action to a policy-violating action (e.g. WARN_CUSTOMER for 0.88 risk) is blocked."""
    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client,
        rag_service=mock_rag_service,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=SensitiveAccountReasoningNode(),
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_DISALLOWED_404",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_SENSITIVE_101",
        customer_id="CUST_SENSITIVE_101",
        account_ids=["ACC_SENSITIVE_101"],
    )

    # Initial halt
    interrupted_state = await workflow.ainvoke(trigger_state)
    assert interrupted_state.case_status == CaseStatus.AWAITING_APPROVAL

    # Analyst attempts to modify to WARN_CUSTOMER (which policy caps at max_risk_score 0.75; state risk is 0.88)
    disallowed_nba = NextBestAction(
        action_type=ActionType.WARN_CUSTOMER,
        reasoning="Attempting warning on high risk activity.",
    )

    disallowed_decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.MODIFIED,
        reviewer_role=ApprovalRole.SENIOR_ANALYST,
        reviewer_id="ANALYST_RECKLESS",
        comments="Trying to clear with a simple warning.",
        modified_action=disallowed_nba,
    )

    resumed_state = await investigate_case(
        trigger_or_state=interrupted_state,
        workflow=workflow,
        analyst_decision=disallowed_decision,
    )

    # Policy engine rejects modification: case remains AWAITING_APPROVAL and does NOT execute WARN_CUSTOMER
    assert resumed_state.case_status == CaseStatus.AWAITING_APPROVAL
    assert resumed_state.is_persisted is False
    assert len(resumed_state.executed_actions) == 0
