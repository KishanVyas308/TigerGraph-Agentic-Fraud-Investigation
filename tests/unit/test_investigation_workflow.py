"""Unit and Integration Tests for Layer 26: Complete LangGraph Investigation Workflow."""

import pytest
from pathlib import Path
from typing import Any, Dict

from backend.app.agents.graph import (
    CompiledInvestigationWorkflow,
    InvestigationWorkflowBuilder,
    create_investigation_graph,
    investigate_case,
    route_policy_gate,
    route_sufficiency_gate,
)
from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskLevel,
    StopReason,
    TimelineEvent,
    TriggerType,
)


class MockReasoningNode:
    """Mock reasoning node allowing deterministic testing of various investigation scenarios."""

    def __init__(
        self,
        risk_level: RiskLevel = RiskLevel.HIGH,
        risk_score: float = 0.85,
        confidence: float = 0.90,
        completeness: float = 0.90,
        preliminary_action: ActionType = ActionType.BLOCK_TRANSACTION,
    ):
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.confidence = confidence
        self.completeness = completeness
        self.preliminary_action = preliminary_action

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        hyp = FraudHypothesis(
            hypothesis_id="HYP_001",
            typology_id="TYP_ATO",
            typology_name="Account Takeover (ATO)",
            confidence=self.confidence,
            indicators=["shared_device", "novel_ip"],
        )
        return {
            "hypotheses": [hyp],
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "evidence_completeness": self.completeness,
            "post_evidence_next_best_action": NextBestAction(
                action_type=self.preliminary_action,
                reasoning="Mock reasoning test decision.",
            ),
            "timeline": [
                TimelineEvent(
                    event_type="REASONING_COMPLETED",
                    node_name="MockReasoningNode",
                    description=f"Assessed risk: {self.risk_level.value}.",
                )
            ],
        }


@pytest.mark.asyncio
async def test_confirmed_fraud_investigation_end_to_end(tmp_path: Path):
    """Test full pipeline for confirmed fraud: intake -> evidence -> reasoning -> block -> SAR -> memory -> embed."""
    mock_reasoning = MockReasoningNode(
        risk_level=RiskLevel.HIGH,
        risk_score=0.88,
        confidence=0.92,
        completeness=0.95,
        preliminary_action=ActionType.BLOCK_TRANSACTION,
    )

    builder = InvestigationWorkflowBuilder(main_reasoning=mock_reasoning)
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_FRAUD_701",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_9001",
        customer_id="CUST_100",
        account_ids=["ACC_100"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Verification of Status & Stop Reason
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION

    # 2. Verification of Executed Action
    assert len(final_state.executed_actions) > 0
    executed_types = [e.action_type for e in final_state.executed_actions]
    assert ActionType.BLOCK_TRANSACTION in executed_types
    for e in final_state.executed_actions:
        assert e.execution_mode == ExecutionMode.SIMULATED

    # 3. Verification of Persistence & Indexing
    assert final_state.is_persisted is True
    assert final_state.case_memory_id is not None
    assert final_state.is_indexed is True
    assert final_state.embedding_id is not None

    # 4. Verification of Auditable Timeline Events
    event_types = [t.event_type for t in final_state.timeline]
    assert "TRIGGER_VALIDATED" in event_types
    assert "CASE_INITIALIZED" in event_types
    assert "EVIDENCE_COLLECTION_COMPLETED" in event_types
    assert "CASE_FINALIZED" in event_types
    assert "CASE_MEMORY_PERSISTED" in event_types
    assert "CASE_EMBEDDING_INDEXED" in event_types


@pytest.mark.asyncio
async def test_benign_cleared_false_positive_investigation(tmp_path: Path):
    """Test full pipeline for benign/cleared case: intake -> evidence -> reasoning -> allow -> no SAR -> finalize."""
    mock_reasoning = MockReasoningNode(
        risk_level=RiskLevel.LOW,
        risk_score=0.15,
        confidence=0.95,
        completeness=0.90,
        preliminary_action=ActionType.ALLOW_TRANSACTION,
    )

    builder = InvestigationWorkflowBuilder(main_reasoning=mock_reasoning)
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_BENIGN_702",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_9002",
        customer_id="CUST_101",
        account_ids=["ACC_101"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Verification of Status & Stop Reason
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.NO_MATERIAL_FRAUD_EVIDENCE

    # 2. Verification of Allowed Action
    assert len(final_state.executed_actions) > 0
    executed_types = [e.action_type for e in final_state.executed_actions]
    assert ActionType.ALLOW_TRANSACTION in executed_types

    # 3. Verification of No SAR Filing
    assert final_state.sar_reference is None

    # 4. Verification of Case Memory Persisted & Indexed
    assert final_state.is_persisted is True
    assert final_state.is_indexed is True


@pytest.mark.asyncio
async def test_evidence_gathering_loop_until_sufficient():
    """Test evidence iteration loop: starts with low completeness, requests evidence, ingests, reassesses."""
    # State tracking reasoning node: low completeness on iteration 0, high completeness on iteration 1
    class DynamicReasoningNode:
        async def process(self, state: FraudCaseState) -> Dict[str, Any]:
            if state.iteration_count == 0:
                return {
                    "risk_level": RiskLevel.HIGH,
                    "confidence": 0.40,
                    "evidence_completeness": 0.35,
                    "post_evidence_next_best_action": NextBestAction(
                        action_type=ActionType.REQUEST_CUSTOMER_CONFIRMATION,
                        reasoning="Initial uncertainty requires customer confirmation.",
                    ),
                }
            else:
                return {
                    "risk_level": RiskLevel.HIGH,
                    "confidence": 0.88,
                    "evidence_completeness": 0.90,
                    "post_evidence_next_best_action": NextBestAction(
                        action_type=ActionType.BLOCK_TRANSACTION,
                        reasoning="Customer confirmation confirmed unrecognized transaction.",
                    ),
                }

    builder = InvestigationWorkflowBuilder(main_reasoning=DynamicReasoningNode())
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_LOOP_703",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_9003",
        customer_id="CUST_102",
        account_ids=["ACC_102"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Verification of Loop Progression
    assert final_state.iteration_count >= 1
    assert len(final_state.received_evidence) > 0

    # 2. Recommendation History Preservation (Pre-evidence and Post-evidence)
    assert final_state.pre_evidence_next_best_action is not None
    assert final_state.pre_evidence_next_best_action.action_type == ActionType.REQUEST_CUSTOMER_CONFIRMATION
    assert final_state.post_evidence_next_best_action is not None
    assert final_state.post_evidence_next_best_action.action_type == ActionType.BLOCK_TRANSACTION

    # 3. Finalization after Loop
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION


@pytest.mark.asyncio
async def test_bounded_evidence_loop_terminates_at_max_iterations():
    """Test that evidence gathering terminates deterministically when max_iterations is reached."""
    # Stubborn low confidence reasoning
    stubborn_reasoning = MockReasoningNode(
        risk_level=RiskLevel.MEDIUM,
        confidence=0.30,
        completeness=0.30,
        preliminary_action=ActionType.MONITOR_TRANSACTION,
    )

    # Set strict loop boundary of 2
    builder = InvestigationWorkflowBuilder(
        main_reasoning=stubborn_reasoning,
        max_iterations=2,
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_BOUNDED_704",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_9004",
        customer_id="CUST_103",
        account_ids=["ACC_103"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # Loop must not exceed max_iterations
    assert final_state.iteration_count <= 2
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason in [
        StopReason.LOW_VALUE_OF_ADDITIONAL_EVIDENCE,
        StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
        StopReason.NO_MATERIAL_FRAUD_EVIDENCE,
    ]


@pytest.mark.asyncio
async def test_human_approval_interrupt_and_resume():
    """Test human-in-the-loop: sensitive action interrupts with AWAITING_APPROVAL, then resumes upon analyst approval."""
    # Mock reasoning recommending BLOCK_ACCOUNT which requires senior supervisor approval under POL_002
    class SensitiveReasoningNode:
        async def process(self, state: FraudCaseState) -> Dict[str, Any]:
            return {
                "risk_level": RiskLevel.HIGH,
                "confidence": 0.90,
                "evidence_completeness": 0.90,
                "post_evidence_next_best_action": NextBestAction(
                    action_type=ActionType.BLOCK_ACCOUNT,
                    reasoning="High-risk ATO cluster requires account freeze.",
                    approval_required=True,
                    approval_role=ApprovalRole.FRAUD_SUPERVISOR,
                ),
            }

    builder = InvestigationWorkflowBuilder(main_reasoning=SensitiveReasoningNode())
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_APPROVAL_705",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_9005",
        customer_id="CUST_104",
        account_ids=["ACC_104"],
        graph_features={"shared_device_account_count": 6},  # POL_002 threshold trigger
    )

    # 1. First Execution: Should halt awaiting analyst review
    interrupted_state = await workflow.ainvoke(trigger_state)

    assert interrupted_state.case_status == CaseStatus.AWAITING_APPROVAL
    assert interrupted_state.stop_reason == StopReason.AWAITING_HUMAN_REVIEW
    assert interrupted_state.approval_required is True
    assert interrupted_state.approval_status is None
    assert interrupted_state.is_persisted is False  # Not yet finalized

    # 2. Resume Execution with Analyst Approval Decision
    analyst_decision = ApprovalDecision(
        action_type=ActionType.BLOCK_ACCOUNT,
        status=ApprovalStatus.APPROVED,
        reviewer_role=ApprovalRole.FRAUD_SUPERVISOR,
        reviewer_id="SUPERVISOR_SARAH",
        comments="Confirmed account compromise via multi-device graph cluster.",
    )

    resumed_state = await investigate_case(
        trigger_or_state=interrupted_state,
        workflow=workflow,
        analyst_decision=analyst_decision,
    )

    # 3. Verify Completion Post-Approval
    assert resumed_state.case_status == CaseStatus.COMPLETED
    assert resumed_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION
    assert resumed_state.approval_status == ApprovalStatus.APPROVED
    assert len(resumed_state.executed_actions) > 0
    assert resumed_state.is_persisted is True
    assert resumed_state.is_indexed is True


def test_routing_helpers():
    """Verify conditional edge routing functions produce deterministic branch names."""
    state = FraudCaseState(case_id="CASE_ROUTE_01")

    # Sufficiency Gate Routing
    state.evidence_completeness = 0.3
    state.confidence = 0.4
    state.iteration_count = 0
    assert route_sufficiency_gate(state, max_iterations=2) == "record_pre_evidence_nba"

    state.iteration_count = 2
    assert route_sufficiency_gate(state, max_iterations=2) == "determine_next_best_action"

    state.iteration_count = 0
    state.evidence_completeness = 0.85
    state.confidence = 0.90
    assert route_sufficiency_gate(state, max_iterations=2) == "determine_next_best_action"

    # Policy Gate Routing
    state.approval_required = False
    assert route_policy_gate(state) == "execute_or_simulate"

    state.approval_required = True
    state.approval_status = None
    assert route_policy_gate(state) == "human_approval"

    state.approval_status = ApprovalStatus.APPROVED
    assert route_policy_gate(state) == "execute_or_simulate"
