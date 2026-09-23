"""Unit tests for Layer 17: Evidence Sufficiency Engine Gate Node."""

import asyncio
import pytest

from backend.app.agents.nodes.sufficiency_gate import (
    EvidenceSufficiencyGate,
    SufficiencyOutcome,
)
from backend.app.models.state import (
    ActionType,
    CaseStatus,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
    RiskLevel,
    StopReason,
    TriggerType,
)


@pytest.fixture
def sufficiency_gate():
    return EvidenceSufficiencyGate(
        min_completeness_threshold=0.70,
        min_confidence_threshold=0.75,
        max_iterations=2,
    )


def test_sufficiency_gather_more_evidence_outcome(sufficiency_gate):
    """Test routing to GATHER_MORE_EVIDENCE when evidence is incomplete and missing evidence exists."""
    state = FraudCaseState(
        case_id="CASE_SUFF_01",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        risk_level=RiskLevel.HIGH,
        risk_score=0.85,
        confidence=0.50,
        evidence_completeness=0.45,
        missing_evidence=["Customer transaction confirmation"],
        iteration_count=0,
    )

    result = sufficiency_gate.evaluate(state)

    assert result.outcome == SufficiencyOutcome.GATHER_MORE_EVIDENCE
    assert result.should_loop is True
    assert result.stop_reason is None
    assert "incomplete" in result.reason.lower()


def test_sufficiency_act_outcome(sufficiency_gate):
    """Test routing to ACT when evidence completeness and confidence meet thresholds."""
    nba = NextBestAction(
        action_type=ActionType.BLOCK_TRANSACTION,
        reasoning="High risk shared device with 3 linked fraud cases",
        execution_mode=ExecutionMode.SIMULATED,
    )

    state = FraudCaseState(
        case_id="CASE_SUFF_02",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        risk_level=RiskLevel.HIGH,
        risk_score=0.88,
        confidence=0.85,
        evidence_completeness=0.80,
        pre_evidence_next_best_action=nba,
        iteration_count=0,
    )

    result = sufficiency_gate.evaluate(state)

    assert result.outcome == SufficiencyOutcome.ACT
    assert result.should_loop is False
    assert result.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION


def test_sufficiency_stop_no_material_fraud_outcome(sufficiency_gate):
    """Test routing to STOP_NO_MATERIAL_FRAUD when risk is low and confidence/completeness are high."""
    state = FraudCaseState(
        case_id="CASE_SUFF_03",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        risk_level=RiskLevel.LOW,
        risk_score=0.15,
        confidence=0.90,
        evidence_completeness=0.85,
        iteration_count=0,
    )

    result = sufficiency_gate.evaluate(state)

    assert result.outcome == SufficiencyOutcome.STOP_NO_MATERIAL_FRAUD
    assert result.should_loop is False
    assert result.stop_reason == StopReason.NO_MATERIAL_FRAUD_EVIDENCE


def test_max_iterations_loop_prevention(sufficiency_gate):
    """Verify max_iterations limit prevents infinite tool loops."""
    state = FraudCaseState(
        case_id="CASE_SUFF_MAX_ITER",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        risk_level=RiskLevel.MEDIUM,
        risk_score=0.60,
        confidence=0.60,
        evidence_completeness=0.55,
        missing_evidence=["Customer verification"],
        iteration_count=2,  # Equal to max_iterations
    )

    result = sufficiency_gate.evaluate(state)

    assert result.should_loop is False
    assert result.stop_reason in [StopReason.MAX_ITERATIONS_REACHED, StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION]


def test_severe_action_escalation(sufficiency_gate):
    """Verify severe action with incomplete evidence & no missing items triggers analyst escalation."""
    nba = NextBestAction(
        action_type=ActionType.BLOCK_ACCOUNT,
        reasoning="Critical freeze request",
        execution_mode=ExecutionMode.SIMULATED,
    )

    state = FraudCaseState(
        case_id="CASE_SUFF_ESCALATE",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.95,
        confidence=0.60,
        evidence_completeness=0.50,
        missing_evidence=[],  # No specific missing items listed
        pre_evidence_next_best_action=nba,
        iteration_count=1,
    )

    result = sufficiency_gate.evaluate(state)

    assert result.outcome == SufficiencyOutcome.ESCALATE
    assert result.should_loop is False
    assert result.stop_reason == StopReason.POLICY_MANDATED_ESCALATION


def test_process_state_patch_generation(sufficiency_gate):
    """Test process() method generating valid FraudCaseState patch dictionary."""
    async def _test():
        state = FraudCaseState(
            case_id="CASE_PATCH_TEST",
            risk_level=RiskLevel.LOW,
            risk_score=0.10,
            confidence=0.90,
            evidence_completeness=0.85,
        )

        patch = await sufficiency_gate.process(state)

        assert isinstance(patch, dict)
        assert patch["sufficiency_outcome"] == SufficiencyOutcome.STOP_NO_MATERIAL_FRAUD.value
        assert patch["case_status"] == CaseStatus.COMPLETED.value
        assert patch["stop_reason"] == StopReason.NO_MATERIAL_FRAUD_EVIDENCE.value
        assert len(patch["timeline"]) == 1
        assert patch["timeline"][0]["event_type"] == "SUFFICIENCY_EVALUATED"

    asyncio.run(_test())
