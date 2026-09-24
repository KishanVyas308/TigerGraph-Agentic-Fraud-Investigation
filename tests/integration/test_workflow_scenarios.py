"""Integration Tests for Layer 36: Core Workflow Scenarios (Scenarios 1, 2, and 3).

Validates complete multi-node LangGraph investigation workflows across:
1. Scenario 1 — Clear High-Risk Fraud:
   - High velocity, multi-account device sharing, rapid pass-through.
   - Immediate block + SAR filing, high confidence/completeness, no loop needed.
   - Finalized with StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION, persisted to graph memory and vector index.
2. Scenario 2 — High-Risk Uncertain Fraud (Evidence Loop):
   - Ambiguous initial signals -> low completeness -> bounded VoI evidence loop.
   - Pre-evidence NBA preserved, customer confirmation ingested, features recalculated.
   - Post-evidence NBA determined (pre is not overwritten).
3. Scenario 3 — Legitimate / Cleared Benign Activity:
   - False positive alert on benign behavior -> low risk, high confidence.
   - Autonomously allowed, no SAR filing, stop reason NO_MATERIAL_FRAUD_EVIDENCE.
   - Persisted as cleared precedent for future investigations.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock
import pytest

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
    create_investigation_graph,
    investigate_case,
)
from backend.app.agents.nodes.evidence_collection import ParallelEvidenceCollectionNode
from backend.app.agents.nodes.reasoning import MainReasoningNode
from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.features.engine import GraphFeatureEngine
from backend.app.llm.router import LLMResponse, LLMRouter
from backend.app.models.state import (
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
    TimelineEvent,
    TriggerType,
)
from backend.app.reporting.sar_generator import SARGenerator


class ScenarioReasoningNode:
    """Configurable reasoning node producing deterministic structured outputs for integration scenarios."""

    def __init__(
        self,
        risk_level: RiskLevel,
        risk_score: float,
        confidence: float,
        evidence_completeness: float,
        preliminary_action: ActionType,
        hypotheses: list[FraudHypothesis],
        missing_evidence: list[str] = None,
    ):
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.confidence = confidence
        self.evidence_completeness = evidence_completeness
        self.preliminary_action = preliminary_action
        self.hypotheses = hypotheses
        self.missing_evidence = missing_evidence or []

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        supporting_ids = [e.evidence_id for e in state.all_evidence[:3]]
        contradicting_ids = [e.evidence_id for e in state.all_evidence if "CLEAN" in e.fact or "LEGIT" in e.fact]

        nba = NextBestAction(
            action_type=self.preliminary_action,
            reasoning=f"Reasoning evaluated risk as {self.risk_level.value} with confidence {self.confidence:.2f}.",
            evidence_ids=supporting_ids,
            execution_mode=ExecutionMode.SIMULATED,
        )

        patch: Dict[str, Any] = {
            "hypotheses": [h.model_dump() for h in self.hypotheses],
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "evidence_completeness": self.evidence_completeness,
            "missing_evidence": self.missing_evidence,
            "supporting_evidence_ids": supporting_ids,
            "contradictory_evidence_ids": contradicting_ids,
            "explanation": f"Automated integration reasoning: risk={self.risk_level.value}, confidence={self.confidence:.2f}.",
            "timeline": [
                TimelineEvent(
                    event_type="REASONING_COMPLETED",
                    node_name="ScenarioReasoningNode",
                    description=f"Assessed risk: {self.risk_level.value}, Action: {self.preliminary_action.value}",
                    details={
                        "risk_score": self.risk_score,
                        "confidence": self.confidence,
                        "completeness": self.evidence_completeness,
                    },
                ).model_dump()
            ],
        }

        if state.iteration_count == 0 or state.pre_evidence_next_best_action is None:
            patch["pre_evidence_next_best_action"] = nba.model_dump()
        else:
            patch["post_evidence_next_best_action"] = nba.model_dump()

        return patch


@pytest.fixture
def mock_tg_client_fraud():
    """Mock TigerGraph client returning confirmed high-risk fraud cluster patterns."""
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TX_FRAUD_901",
        "amount": 18500.0,
        "currency": "USD",
        "customer_id": "CUST_FRAUD_100",
        "account_id": "ACC_FRAUD_100",
        "device_id": "DEV_EMULATOR_99",
        "ip_address": "198.51.100.77",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TX_FRAUD_901",
        "amount_to_mean_ratio": 7.5,
        "txn_count_5m": 4,
        "is_new_merchant": True,
    }
    client.find_shared_devices.return_value = {
        "device_id": "DEV_EMULATOR_99",
        "shared_account_count": 5,
        "shared_customer_count": 4,
        "linked_fraud_cases": ["HIST_CASE_MULE_01"],
    }
    client.find_shared_ips.return_value = {
        "ip_address": "198.51.100.77",
        "shared_account_count": 6,
        "shared_customer_count": 5,
    }
    client.find_fraud_neighbors.return_value = {
        "vertex_id": "ACC_FRAUD_100",
        "fraud_neighbors_count": 3,
        "neighbor_case_ids": ["HIST_CASE_MULE_01", "HIST_CASE_MULE_02"],
    }
    client.get_shortest_path_to_fraud.return_value = {
        "vertex_id": "ACC_FRAUD_100",
        "target_fraud_case_id": "HIST_CASE_MULE_01",
        "shortest_distance": 1,
    }
    client.detect_money_flow_patterns.return_value = {
        "account_id": "ACC_FRAUD_100",
        "fan_in_count": 7,
        "fan_out_count": 1,
        "rapid_pass_through": True,
        "cycle_detected": True,
    }
    client.get_device_identity_context.return_value = {
        "device_id": "DEV_EMULATOR_99",
        "is_new_device": True,
        "linked_account_count": 5,
    }
    return client


@pytest.fixture
def mock_tg_client_benign():
    """Mock TigerGraph client returning clean, benign transaction baseline."""
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TX_BENIGN_902",
        "amount": 45.0,
        "currency": "USD",
        "customer_id": "CUST_BENIGN_200",
        "account_id": "ACC_BENIGN_200",
        "device_id": "DEV_TRUSTED_IPHONE",
        "ip_address": "192.168.1.50",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TX_BENIGN_902",
        "amount_to_mean_ratio": 1.05,
        "txn_count_5m": 0,
        "is_new_merchant": False,
    }
    client.find_shared_devices.return_value = {
        "device_id": "DEV_TRUSTED_IPHONE",
        "shared_account_count": 1,
        "shared_customer_count": 1,
        "linked_fraud_cases": [],
    }
    client.find_shared_ips.return_value = {
        "ip_address": "192.168.1.50",
        "shared_account_count": 1,
        "shared_customer_count": 1,
    }
    client.find_fraud_neighbors.return_value = {
        "vertex_id": "ACC_BENIGN_200",
        "fraud_neighbors_count": 0,
        "neighbor_case_ids": [],
    }
    client.get_shortest_path_to_fraud.return_value = {
        "vertex_id": "ACC_BENIGN_200",
        "target_fraud_case_id": None,
        "shortest_distance": None,
    }
    client.detect_money_flow_patterns.return_value = {
        "account_id": "ACC_BENIGN_200",
        "fan_in_count": 0,
        "fan_out_count": 0,
        "rapid_pass_through": False,
        "cycle_detected": False,
    }
    client.get_device_identity_context.return_value = {
        "device_id": "DEV_TRUSTED_IPHONE",
        "is_new_device": False,
        "linked_account_count": 1,
    }
    return client


@pytest.fixture
def mock_rag_service():
    """Mock GraphRAG service returning AML policy context and historical precedents."""
    service = MagicMock()
    mock_policy = MagicMock()
    mock_policy.model_dump.return_value = {
        "chunk_id": "POL_AML_004",
        "source_id": "POL_004",
        "document_type": "POLICY",
        "section_title": "SAR Mandatory Reporting Thresholds",
        "text": "Mandatory SAR filing required on confirmed mule operations exceeding $5,000 USD.",
        "relevance_score": 0.95,
    }
    service.retrieve_policy_context.return_value = MagicMock(items=[mock_policy])

    mock_precedent = MagicMock()
    mock_precedent.model_dump.return_value = {
        "case_id": "HIST_CASE_MULE_01",
        "outcome": "FRAUD_CONFIRMED",
        "primary_typology": "MULE_RING",
        "summary": "Coordinated rapid pass-through via shared emulator device.",
        "shared_entities": ["DEV_EMULATOR_99"],
        "combined_score": 0.92,
        "retrieval_method": "HYBRID",
    }
    service.retrieve_similar_cases.return_value = MagicMock(cases=[mock_precedent])
    return service


# ============================================================================
# Scenario 1 — Clear High-Risk Fraud
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_1_clear_high_risk_fraud(mock_tg_client_fraud, mock_rag_service, tmp_path: Path):
    """Scenario 1: Confirmed fraud cluster -> immediate block + SAR -> finalized + indexed."""
    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client_fraud,
        rag_service=mock_rag_service,
    )

    reasoning_node = ScenarioReasoningNode(
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.96,
        confidence=0.94,
        evidence_completeness=0.92,
        preliminary_action=ActionType.BLOCK_TRANSACTION,
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="HYP_INT_01",
                typology_id="TYP_MULE",
                typology_name="Mule Network Layering",
                confidence=0.95,
                indicators=["shared_emulator_device", "rapid_pass_through", "high_velocity"],
            )
        ],
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=reasoning_node,
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_FRAUD_001",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_FRAUD_901",
        customer_id="CUST_FRAUD_100",
        account_ids=["ACC_FRAUD_100"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. State integrity and status
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION
    assert final_state.iteration_count == 0  # No loop needed for clear evidence

    # 2. Risk and confidence assertions
    assert final_state.risk_level == RiskLevel.CRITICAL.value or final_state.risk_level == RiskLevel.CRITICAL
    assert final_state.risk_score >= 0.90
    assert final_state.confidence >= 0.90
    assert final_state.evidence_completeness >= 0.90

    # 3. Action execution in simulated mode
    assert len(final_state.executed_actions) > 0
    executed_types = [e.action_type for e in final_state.executed_actions]
    assert ActionType.BLOCK_TRANSACTION in executed_types
    for e in final_state.executed_actions:
        assert e.execution_mode == ExecutionMode.SIMULATED

    # 4. Mandatory SAR generation on critical risk
    assert final_state.sar_reference is not None
    assert final_state.sar_report is not None

    # 5. Case memory persistence and indexing
    assert final_state.is_persisted is True
    assert final_state.case_memory_id is not None
    assert final_state.is_indexed is True
    assert final_state.embedding_id is not None

    # 6. Complete timeline event provenance
    timeline_types = [t.event_type for t in final_state.timeline]
    assert "TRIGGER_VALIDATED" in timeline_types
    assert "EVIDENCE_COLLECTION_COMPLETED" in timeline_types
    assert "REASONING_COMPLETED" in timeline_types
    assert "ACTION_EXECUTED_SIMULATED" in timeline_types
    assert "SAR_REPORT_GENERATED" in timeline_types
    assert "CASE_FINALIZED" in timeline_types
    assert "CASE_MEMORY_PERSISTED" in timeline_types
    assert "CASE_EMBEDDING_INDEXED" in timeline_types


# ============================================================================
# Scenario 2 — High-Risk Uncertain Case with Evidence Loop
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_2_high_risk_uncertain_case_with_evidence_loop(mock_tg_client_fraud, mock_rag_service):
    """Scenario 2: Uncertain evidence -> loop requests customer confirmation -> post-evidence block."""
    class DynamicUncertainReasoningNode:
        async def process(self, state: FraudCaseState) -> Dict[str, Any]:
            if state.iteration_count == 0:
                # Initial uncertain evaluation: low completeness, requires customer confirmation
                nba = NextBestAction(
                    action_type=ActionType.REQUEST_CUSTOMER_CONFIRMATION,
                    reasoning="Uncertain fraud risk requires customer transaction confirmation.",
                    execution_mode=ExecutionMode.SIMULATED,
                )
                return {
                    "risk_level": RiskLevel.HIGH.value,
                    "risk_score": 0.72,
                    "confidence": 0.45,
                    "evidence_completeness": 0.35,
                    "missing_evidence": ["customer_confirmation_of_intent"],
                    "pre_evidence_next_best_action": nba.model_dump(),
                    "post_evidence_next_best_action": nba.model_dump(),
                    "timeline": [
                        TimelineEvent(
                            event_type="REASONING_COMPLETED",
                            node_name="DynamicUncertainReasoningNode",
                            description="Initial assessment: High risk but low completeness.",
                        ).model_dump()
                    ],
                }
            else:
                # Post-evidence evaluation: customer responded that transaction was unauthorized
                nba = NextBestAction(
                    action_type=ActionType.BLOCK_TRANSACTION,
                    reasoning="Customer confirmed transaction was unrecognized; blocking transaction.",
                    execution_mode=ExecutionMode.SIMULATED,
                )
                return {
                    "risk_level": RiskLevel.HIGH.value,
                    "risk_score": 0.93,
                    "confidence": 0.92,
                    "evidence_completeness": 0.90,
                    "missing_evidence": [],
                    "post_evidence_next_best_action": nba.model_dump(),
                    "timeline": [
                        TimelineEvent(
                            event_type="REASONING_COMPLETED",
                            node_name="DynamicUncertainReasoningNode",
                            description="Updated assessment: Customer confirmation confirmed fraud.",
                        ).model_dump()
                    ],
                }

    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client_fraud,
        rag_service=mock_rag_service,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=DynamicUncertainReasoningNode(),
        max_iterations=2,
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_UNCERTAIN_002",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_FRAUD_901",
        customer_id="CUST_FRAUD_100",
        account_ids=["ACC_FRAUD_100"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Bounded evidence loop ran exactly 1 iteration
    assert final_state.iteration_count == 1
    assert len(final_state.received_evidence) > 0

    # 2. Strict recommendation history preservation: pre-evidence NBA is NEVER overwritten
    assert final_state.pre_evidence_next_best_action is not None
    assert final_state.pre_evidence_next_best_action.action_type == ActionType.REQUEST_CUSTOMER_CONFIRMATION
    assert final_state.post_evidence_next_best_action is not None
    assert final_state.post_evidence_next_best_action.action_type == ActionType.BLOCK_TRANSACTION

    # 3. Final state completion
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION
    assert final_state.is_persisted is True
    assert final_state.is_indexed is True

    # 4. Timeline audit verifying evidence loop sequence
    timeline_types = [t.event_type for t in final_state.timeline]
    assert "PRE_EVIDENCE_NBA_RECORDED" in timeline_types
    assert "EVIDENCE_REQUESTED" in timeline_types
    assert "ADDITIONAL_EVIDENCE_REQUESTED" in timeline_types
    assert "ADDITIONAL_EVIDENCE_INGESTED" in timeline_types


# ============================================================================
# Scenario 3 — Legitimate / Cleared Benign False Positive
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_3_legitimate_cleared_case(mock_tg_client_benign, mock_rag_service):
    """Scenario 3: Benign transaction -> allow transaction, no SAR, stop reason NO_MATERIAL_FRAUD_EVIDENCE."""
    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client_benign,
        rag_service=mock_rag_service,
    )

    reasoning_node = ScenarioReasoningNode(
        risk_level=RiskLevel.LOW,
        risk_score=0.10,
        confidence=0.96,
        evidence_completeness=0.95,
        preliminary_action=ActionType.ALLOW_TRANSACTION,
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="HYP_BENIGN_01",
                typology_id="TYP_BENIGN",
                typology_name="Legitimate Customer Routine",
                confidence=0.95,
                indicators=["trusted_device", "typical_amount"],
            )
        ],
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=reasoning_node,
    )
    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_BENIGN_003",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_BENIGN_902",
        customer_id="CUST_BENIGN_200",
        account_ids=["ACC_BENIGN_200"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Status and stop reason
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.NO_MATERIAL_FRAUD_EVIDENCE

    # 2. Risk metrics
    assert final_state.risk_level == RiskLevel.LOW.value or final_state.risk_level == RiskLevel.LOW
    assert final_state.risk_score <= 0.25

    # 3. Action execution: ALLOW_TRANSACTION
    assert len(final_state.executed_actions) > 0
    executed_types = [e.action_type for e in final_state.executed_actions]
    assert ActionType.ALLOW_TRANSACTION in executed_types

    # 4. Mandatory no SAR filing
    assert final_state.sar_reference is None
    assert final_state.sar_report is None

    # 5. Persisted as cleared memory precedent
    assert final_state.is_persisted is True
    assert final_state.is_indexed is True
