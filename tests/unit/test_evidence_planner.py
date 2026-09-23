"""Unit tests for Evidence Planner node (Layer 18)."""

import asyncio
from backend.app.agents.nodes.evidence_planner import CandidateEvidenceRequest, EvidencePlannerNode
from backend.app.models.state import (
    ActionType,
    CaseStatus,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
)


def test_candidate_evidence_request_voi_score():
    """Test Value of Information (VoI) score calculation."""
    cand = CandidateEvidenceRequest(
        evidence_type="CUSTOMER_CONFIRMATION",
        target_entity_id="TX_101",
        reason="Verify authorization",
        decision_impact=0.90,
        uncertainty_reduction=0.80,
        cost_friction=1.5,
        decision_could_change="Clear transaction",
    )
    # VoI = (0.80 * 0.90) / (1.5 + 0.1) = 0.72 / 1.6 = 0.45
    assert round(cand.voi_score, 4) == 0.45


def test_plan_evidence_request_selection():
    """Test candidate selection ranking by VoI score."""
    planner = EvidencePlannerNode()

    # Case 1: Missing customer confirmation
    state1 = FraudCaseState(
        case_id="CASE_TEST_01",
        transaction_id="TX_1001",
        missing_evidence=["Customer transaction confirmation"],
        post_evidence_next_best_action=NextBestAction(
            action_type=ActionType.BLOCK_TRANSACTION,
            reasoning="Suspicious velocity",
            confidence=0.6,
            execution_mode=ExecutionMode.SIMULATED,
        ),
    )
    request1 = planner.plan_evidence_request(state1)
    assert request1.evidence_type in ["CUSTOMER_CONFIRMATION", "STEP_UP_AUTH", "ANALYST_INFORMATION", "APPROVED_EXTERNAL_CHECK"]
    assert request1.voi_score > 0.0

    # Case 2: Missing auth / step up
    state2 = FraudCaseState(
        case_id="CASE_TEST_02",
        customer_id="CUST_202",
        missing_evidence=["Step up 2FA device auth required"],
    )
    request2 = planner.plan_evidence_request(state2)
    assert request2.evidence_type in ["STEP_UP_AUTH", "CUSTOMER_CONFIRMATION"]


def test_evidence_planner_process_patch():
    """Test processing FraudCaseState produce proper patch."""
    planner = EvidencePlannerNode()
    pre_nba = NextBestAction(
        action_type=ActionType.MONITOR_TRANSACTION,
        reasoning="Unusual location",
        confidence=0.55,
        execution_mode=ExecutionMode.SIMULATED,
    )
    state = FraudCaseState(
        case_id="CASE_TEST_03",
        transaction_id="TX_9000",
        customer_id="CUST_9000",
        iteration_count=1,
        missing_evidence=["External reputation check"],
        pre_evidence_next_best_action=pre_nba,
    )

    async def _test():
        return await planner.process(state)

    patch = asyncio.run(_test())

    assert patch["case_status"] == CaseStatus.AWAITING_EVIDENCE.value
    assert patch["iteration_count"] == 2
    assert len(patch["requested_evidence"]) == 1
    assert patch["requested_evidence"][0]["status"] == "PENDING"
    assert "pre_evidence_next_best_action" in patch
    assert patch["pre_evidence_next_best_action"]["action_type"] == ActionType.MONITOR_TRANSACTION.value
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "EVIDENCE_REQUESTED"
    assert "voi_score" in patch["timeline"][0]["details"]
