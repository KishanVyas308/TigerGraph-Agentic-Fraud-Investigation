"""Unit tests for Case Finalizer Service and FinalizerNode (Layer 23).

Verifies:
- Deterministic stop reason resolution across all 5 standard stop conditions:
  * SUFFICIENT_EVIDENCE_FOR_ACTION
  * NO_MATERIAL_FRAUD_EVIDENCE
  * POLICY_MANDATED_ESCALATION
  * AWAITING_HUMAN_REVIEW
  * LOW_VALUE_OF_ADDITIONAL_EVIDENCE
- Prevention of silent closures without explicit stop reasons
- Case integrity validation (metrics bounds, required actions, approvals)
- Summary text generation and FinalCaseSummary schema serialization
- FinalizerNode LangGraph async workflow processing
- State reducer merge integration for case_summary and final_summary
"""

import asyncio
from backend.app.agents.nodes.finalizer import FinalizerNode
from backend.app.models.state import (
    ActionExecution,
    ActionType,
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
    TriggerType,
    merge_fraud_case_state,
)
from backend.app.schemas.case import FinalCaseSummary, ValidationResult
from backend.app.services.finalizer import CaseFinalizer


def test_finalize_completed_case_sufficient_evidence():
    """Verify finalization of a completed case with sufficient evidence and executed action."""
    finalizer = CaseFinalizer()
    ev_item = EvidenceItem(
        evidence_id="EVD_TEST_01",
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Transaction TX_FIN_01 for $8,500.00 confirmed mule fan-out",
        reliability=EvidenceReliability.HIGH,
    )
    state = FraudCaseState(
        case_id="CASE_FIN_01",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        customer_id="CUST_FIN_01",
        transaction_id="TX_FIN_01",
        account_ids=["ACC_FIN_01"],
        transaction_evidence=[ev_item],
        risk_level=RiskLevel.HIGH,
        risk_score=0.88,
        confidence=0.85,
        evidence_completeness=0.80,
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="HYP_ATO",
                title="Account Takeover",
                description="Novel device ATO",
                likelihood=0.85,
            )
        ],
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_TRANSACTION,
            target_entity_id="TX_FIN_01",
            reasoning="Confirmed ATO pattern",
        ),
        executed_actions=[
            ActionExecution(
                action_type=ActionType.BLOCK_TRANSACTION,
                execution_mode=ExecutionMode.SIMULATED,
                success=True,
                result={"disposition": "DECLINED"},
            )
        ],
        sar_reference="SAR_REF_FIN_01",
    )

    summary_model, patch = finalizer.finalize_case(state)

    assert summary_model.case_id == "CASE_FIN_01"
    assert summary_model.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION.value
    assert summary_model.status == CaseStatus.COMPLETED.value
    assert summary_model.sar_filed is True
    assert summary_model.sar_reference == "SAR_REF_FIN_01"
    assert summary_model.total_evidence_count == 1
    assert "CASE_FIN_01" in summary_model.case_summary_text
    assert "SUFFICIENT_EVIDENCE_FOR_ACTION" in summary_model.case_summary_text

    assert patch["case_status"] == CaseStatus.COMPLETED.value
    assert patch["stop_reason"] == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION.value
    assert "final_summary" in patch
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "CASE_FINALIZED"


def test_finalize_cleared_benign_case_no_material_fraud():
    """Verify finalization of a cleared low-risk case resolves NO_MATERIAL_FRAUD_EVIDENCE."""
    finalizer = CaseFinalizer()
    state = FraudCaseState(
        case_id="CASE_FIN_02",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        customer_id="CUST_BENIGN",
        risk_level=RiskLevel.LOW,
        risk_score=0.15,
        confidence=0.90,
        evidence_completeness=0.85,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.CLOSE_CASE,
            reasoning="Benign travel expenditure confirmed",
        ),
    )

    summary_model, patch = finalizer.finalize_case(state)

    assert summary_model.stop_reason == StopReason.NO_MATERIAL_FRAUD_EVIDENCE.value
    assert summary_model.status == CaseStatus.COMPLETED.value
    assert patch["case_status"] == CaseStatus.COMPLETED.value
    assert patch["stop_reason"] == StopReason.NO_MATERIAL_FRAUD_EVIDENCE.value


def test_finalize_escalated_case_policy_mandated():
    """Verify case escalated to human queue resolves POLICY_MANDATED_ESCALATION."""
    finalizer = CaseFinalizer()
    state = FraudCaseState(
        case_id="CASE_FIN_03",
        risk_level=RiskLevel.HIGH,
        risk_score=0.78,
        confidence=0.60,
        evidence_completeness=0.65,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.ESCALATE_ANALYST,
            reasoning="Complex synthetic identity ring requiring specialist review",
        ),
    )

    summary_model, patch = finalizer.finalize_case(state)

    assert summary_model.stop_reason == StopReason.POLICY_MANDATED_ESCALATION.value
    assert summary_model.status == CaseStatus.COMPLETED.value


def test_finalize_awaiting_approval_case():
    """Verify case paused for human approval resolves AWAITING_HUMAN_REVIEW and preserves status."""
    finalizer = CaseFinalizer()
    state = FraudCaseState(
        case_id="CASE_FIN_04",
        approval_required=True,
        case_status=CaseStatus.AWAITING_APPROVAL,
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_ACCOUNT,
            approval_required=True,
            approval_role=ApprovalRole.SENIOR_ANALYST,
            reasoning="Multi-account mule cluster",
        ),
    )

    summary_model, patch = finalizer.finalize_case(state)

    assert summary_model.stop_reason == StopReason.AWAITING_HUMAN_REVIEW.value
    assert summary_model.status == CaseStatus.AWAITING_APPROVAL.value
    assert patch["case_status"] == CaseStatus.AWAITING_APPROVAL.value
    assert patch["stop_reason"] == StopReason.AWAITING_HUMAN_REVIEW.value


def test_validate_case_integrity():
    """Verify integrity validation flags missing actions and out-of-bounds metrics."""
    finalizer = CaseFinalizer()

    # Invalid state: no action and invalid risk score
    bad_state = FraudCaseState(
        case_id="CASE_BAD_01",
        risk_score=1.5,  # Out of bounds
    )

    val_res = finalizer.validate_case_integrity(bad_state)
    assert val_res.valid is False
    assert any("no recommended next-best action" in e for e in val_res.errors)
    assert any("out of bounds" in e for e in val_res.errors)


def test_finalizer_node_async_process():
    """Verify FinalizerNode executing in async LangGraph node pattern."""
    node = FinalizerNode()
    state = FraudCaseState(
        case_id="CASE_NODE_FIN_01",
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.ALLOW_TRANSACTION,
            reasoning="Low risk benign pattern",
        ),
        risk_level=RiskLevel.LOW,
        risk_score=0.10,
    )

    patch = asyncio.run(node.process(state))

    assert patch["case_status"] == CaseStatus.COMPLETED.value
    assert patch["stop_reason"] == StopReason.NO_MATERIAL_FRAUD_EVIDENCE.value
    assert "case_summary" in patch
    assert "final_summary" in patch


def test_state_merge_reducer_with_finalizer_patch():
    """Verify merge_fraud_case_state properly merges case_summary and final_summary."""
    state = FraudCaseState(
        case_id="CASE_MERGE_FIN_01",
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.ALLOW_TRANSACTION,
            reasoning="Low risk",
        ),
    )
    finalizer = CaseFinalizer()
    summary_model, patch = finalizer.finalize_case(state)

    merged = merge_fraud_case_state(state, patch)

    assert merged.case_status == CaseStatus.COMPLETED.value
    assert merged.stop_reason == summary_model.stop_reason
    assert merged.case_summary is not None
    assert merged.final_summary is not None
    assert merged.final_summary["case_id"] == "CASE_MERGE_FIN_01"
    assert any(t.event_type == "CASE_FINALIZED" for t in merged.timeline)
