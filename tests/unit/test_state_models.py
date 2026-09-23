"""Unit tests for Layer 9: Fraud Investigation State Models."""

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


def test_enums_definition():
    """Verify all domain enums have expected string values."""
    assert TriggerType.TRANSACTION_ALERT.value == "TRANSACTION_ALERT"
    assert RiskLevel.HIGH.value == "HIGH"
    assert EvidenceCategory.GRAPH_RELATIONSHIP.value == "GRAPH_RELATIONSHIP"
    assert EvidenceReliability.HIGH.value == "HIGH"
    assert ActionType.BLOCK_ACCOUNT.value == "BLOCK_ACCOUNT"
    assert ApprovalStatus.APPROVED.value == "APPROVED"
    assert ApprovalRole.FRAUD_MANAGER.value == "FRAUD_MANAGER"
    assert StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION.value == "SUFFICIENT_EVIDENCE_FOR_ACTION"
    assert CaseStatus.IN_PROGRESS.value == "IN_PROGRESS"
    assert ExecutionMode.SIMULATED.value == "SIMULATED"


def test_evidence_item_validation():
    """Test EvidenceItem validation rules and defaults."""
    item = EvidenceItem(
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Transaction amount $15,000 exceeds 30-day historical mean by 5.2x",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["TXN_101", "ACC_001"],
    )

    assert item.evidence_id.startswith("EVD_")
    assert item.category == "TRANSACTION_BEHAVIOR"
    assert len(item.timestamp) > 0
    assert item.reliability == "HIGH"

    # Test validation failures for empty strings
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="",
            source="TIGERGRAPH_GSQL",
            category=EvidenceCategory.TRANSACTION_BEHAVIOR,
            fact="Valid fact",
        )

    with pytest.raises(ValidationError):
        EvidenceItem(
            source="TIGERGRAPH_GSQL",
            category=EvidenceCategory.TRANSACTION_BEHAVIOR,
            fact="   ",
        )


def test_fraud_hypothesis_and_metric_scaling():
    """Verify hypothesis likelihood scaling and validation."""
    hyp1 = FraudHypothesis(
        hypothesis_id="HYP_ATO",
        title="Account Takeover",
        description="Account compromised via credential stuffing",
        likelihood=0.85,
    )
    assert hyp1.likelihood == 0.85

    # Percentage auto-scaling (85 -> 0.85)
    hyp2 = FraudHypothesis(
        hypothesis_id="HYP_ATO_2",
        title="Account Takeover",
        description="Account compromised",
        likelihood=85.0,
    )
    assert hyp2.likelihood == 0.85


def test_risk_assessment_separation():
    """Verify risk, confidence, and completeness remain strictly separate."""
    assessment = RiskAssessment(
        risk_level=RiskLevel.HIGH,
        risk_score=0.88,
        confidence=0.92,
        evidence_completeness=0.75,
        missing_evidence=["CUSTOMER_DEVICE_CONFIRMATION"],
        explanation="High structural graph anomaly detected with unresolved device context.",
    )

    assert assessment.risk_level == "HIGH"
    assert assessment.risk_score == 0.88
    assert assessment.confidence == 0.92
    assert assessment.evidence_completeness == 0.75
    assert assessment.risk_score != assessment.confidence
    assert assessment.confidence != assessment.evidence_completeness


def test_fraud_case_state_initialization_and_categories():
    """Verify main FraudCaseState initialization across all 6 categories."""
    state = FraudCaseState(
        case_id="CASE_TEST001",
        trigger_type=TriggerType.HIGH_RISK_RULE,
        transaction_id="TXN_999",
        customer_id="CUST_123",
        account_ids=["ACC_001", "ACC_002"],
    )

    # 1. Identity
    assert state.case_id == "CASE_TEST001"
    assert state.trigger_type == "HIGH_RISK_RULE"
    assert state.transaction_id == "TXN_999"

    # 2. Evidence sub-lists
    assert len(state.transaction_evidence) == 0
    assert len(state.graph_evidence) == 0

    # 3. Features
    assert state.graph_features == {}
    assert state.behavior_features == {}

    # 4. Reasoning
    assert state.risk_level is None

    # 5. Actions
    assert state.pre_evidence_next_best_action is None
    assert state.post_evidence_next_best_action is None
    assert state.approval_required is False

    # 6. Case Control
    assert state.case_status == "OPEN"
    assert state.iteration_count == 0


def test_add_evidence_routing_and_all_evidence_property():
    """Verify add_evidence routes by category and all_evidence deduplicates."""
    state = FraudCaseState(case_id="CASE_ROUTING")

    ev1 = EvidenceItem(
        evidence_id="EVD_001",
        source="GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="High velocity transaction",
    )
    ev2 = EvidenceItem(
        evidence_id="EVD_002",
        source="GSQL",
        category=EvidenceCategory.GRAPH_RELATIONSHIP,
        fact="Connected to fraud cluster",
    )
    ev3 = EvidenceItem(
        evidence_id="EVD_003",
        source="GraphRAG",
        category=EvidenceCategory.POLICY,
        fact="Policy POL-ATO requires account hold for ATO score > 0.8",
    )

    state.add_evidence(ev1)
    state.add_evidence(ev2)
    state.add_evidence(ev3)

    assert len(state.transaction_evidence) == 1
    assert len(state.graph_evidence) == 1
    assert len(state.policy_evidence) == 1

    all_ev = state.all_evidence
    assert len(all_ev) == 3
    assert {e.evidence_id for e in all_ev} == {"EVD_001", "EVD_002", "EVD_003"}

    # Duplicate evidence item addition should be ignored
    state.add_evidence(ev1)
    assert len(state.transaction_evidence) == 1
    assert len(state.all_evidence) == 3


def test_timeline_event_addition():
    """Test timeline event creation helper."""
    state = FraudCaseState(case_id="CASE_TIMELINE")
    event = state.add_timeline_event(
        event_type="CASE_STARTED",
        description="Case initiated by high risk transaction trigger",
        node_name="validate_trigger",
        details={"rule_id": "RULE_ATO_01"},
    )

    assert event.event_id.startswith("EVT_")
    assert event.event_type == "CASE_STARTED"
    assert event.node_name == "validate_trigger"
    assert len(state.timeline) == 1
    assert state.timeline[0].details["rule_id"] == "RULE_ATO_01"


def test_to_dict_json_serialization():
    """Test full model JSON serialization."""
    state = FraudCaseState(
        case_id="CASE_SERIALIZE",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.95,
        confidence=0.90,
        evidence_completeness=0.85,
    )

    state.add_timeline_event("TEST_EVENT", "Testing serialization")

    d = state.to_dict()
    assert isinstance(d, dict)
    assert d["case_id"] == "CASE_SERIALIZE"
    assert d["trigger_type"] == "TRANSACTION_ALERT"
    assert d["risk_level"] == "CRITICAL"
    assert d["risk_score"] == 0.95
    assert len(d["timeline"]) == 1
    assert d["timeline"][0]["description"] == "Testing serialization"


def test_merge_fraud_case_state_reducer():
    """Test LangGraph reducer merging patches into FraudCaseState."""
    initial_state = FraudCaseState(
        case_id="CASE_REDUCER",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        case_status=CaseStatus.OPEN,
    )

    # Patch 1: Evidence and feature calculation
    patch_1 = {
        "graph_features": {"shared_device_count": 3, "fraud_neighbors": 1},
        "transaction_evidence": [
            {
                "evidence_id": "EVD_PATCH1",
                "source": "GSQL",
                "category": "TRANSACTION_BEHAVIOR",
                "fact": "Transaction velocity 4 in 10m",
            }
        ],
        "timeline": [
            {
                "event_type": "EVIDENCE_COLLECTED",
                "node_name": "parallel_evidence_collection",
                "description": "Collected GSQL evidence",
            }
        ],
        "case_status": "IN_PROGRESS",
    }

    state_after_1 = merge_fraud_case_state(initial_state, patch_1)
    assert state_after_1.case_status == "IN_PROGRESS"
    assert state_after_1.graph_features["shared_device_count"] == 3
    assert len(state_after_1.transaction_evidence) == 1
    assert len(state_after_1.timeline) == 1

    # Patch 2: Reasoning & Pre-Evidence Recommendation
    pre_nba = NextBestAction(
        action_type=ActionType.REQUEST_STEP_UP_AUTH,
        target_entity_id="CUST_001",
        reasoning="Uncertainty high; step-up auth requested",
        approval_required=False,
    )

    patch_2 = {
        "risk_level": RiskLevel.HIGH,
        "risk_score": 0.82,
        "confidence": 0.55,
        "evidence_completeness": 0.50,
        "pre_evidence_next_best_action": pre_nba,
        "requested_evidence": [
            {
                "request_id": "REQ_001",
                "evidence_type": "STEP_UP_AUTH",
                "target_entity_id": "CUST_001",
                "reason": "Verify customer identity",
            }
        ],
        "case_status": "AWAITING_EVIDENCE",
    }

    state_after_2 = merge_fraud_case_state(state_after_1, patch_2)
    assert state_after_2.case_status == "AWAITING_EVIDENCE"
    assert state_after_2.risk_level == "HIGH"
    assert state_after_2.confidence == 0.55
    assert state_after_2.pre_evidence_next_best_action.action_type == "REQUEST_STEP_UP_AUTH"
    assert len(state_after_2.requested_evidence) == 1

    # Patch 3: Ingest step-up auth evidence & Post-Evidence Recommendation
    post_nba = NextBestAction(
        action_type=ActionType.ALLOW_TRANSACTION,
        target_entity_id="TXN_999",
        reasoning="Step-up authentication succeeded; low residual fraud risk",
        approval_required=False,
    )

    patch_3 = {
        "received_evidence": [
            {
                "evidence_id": "EVD_STEPUP",
                "source": "AUTHENTICATION_SERVICE",
                "category": "AUTHENTICATION",
                "fact": "Step-up SMS OTP verified successfully",
            }
        ],
        "post_evidence_next_best_action": post_nba,
        "confidence": 0.95,
        "evidence_completeness": 0.90,
        "stop_reason": StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
        "case_status": "COMPLETED",
    }

    state_after_3 = merge_fraud_case_state(state_after_2, patch_3)
    assert state_after_3.case_status == "COMPLETED"
    assert state_after_3.stop_reason == "SUFFICIENT_EVIDENCE_FOR_ACTION"
    assert state_after_3.confidence == 0.95

    # Verify both pre-evidence and post-evidence recommendations are preserved!
    assert state_after_3.pre_evidence_next_best_action is not None
    assert state_after_3.pre_evidence_next_best_action.action_type == "REQUEST_STEP_UP_AUTH"
    assert state_after_3.post_evidence_next_best_action is not None
    assert state_after_3.post_evidence_next_best_action.action_type == "ALLOW_TRANSACTION"
