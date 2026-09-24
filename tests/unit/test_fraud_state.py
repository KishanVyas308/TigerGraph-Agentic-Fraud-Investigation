"""Unit tests for Fraud Case State Models (Layer 35 Deliverable).

Comprehensive verification of:
- All domain enums (TriggerType, RiskLevel, EvidenceCategory, ActionType, StopReason, CaseStatus)
- State model validation and constraints
- LangGraph state reducer / merge_fraud_case_state behavior
- Deduplication across evidence, events, and action executions
- Metric scaling and safe handling of scalar metrics
"""

import pytest
from pydantic import ValidationError

from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    EvidenceReliability,
    EvidenceRequest,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskAssessment,
    RiskLevel,
    StopReason,
    TimelineEvent,
    TriggerType,
    merge_fraud_case_state,
)
from tests.unit.test_state_models import (
    test_add_evidence_routing_and_all_evidence_property,
    test_enums_definition,
    test_evidence_item_validation,
    test_fraud_case_state_initialization_and_categories,
    test_fraud_hypothesis_and_metric_scaling,
    test_merge_fraud_case_state_reducer,
    test_risk_assessment_separation,
    test_timeline_event_addition,
    test_to_dict_json_serialization,
)


def test_state_status_transitions():
    """Verify state transitions and stop reason tracking."""
    state = FraudCaseState(
        case_id="CASE_TRANSITION_TEST",
        case_status=CaseStatus.OPEN,
    )
    assert state.case_status == "OPEN"

    patch = {
        "case_status": CaseStatus.IN_PROGRESS.value,
        "risk_level": RiskLevel.HIGH.value,
    }
    updated = merge_fraud_case_state(state, patch)
    assert updated.case_status == "IN_PROGRESS"
    assert updated.risk_level == "HIGH"
    assert updated.risk_score == 0.80  # derived automatically
