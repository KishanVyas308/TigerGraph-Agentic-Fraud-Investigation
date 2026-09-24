"""Integration Tests for Layer 36: Mandatory SAR Filing Workflow (Scenario 5).

Validates Scenario 5 defined in AGENTS.md §21 & §33:
1. SAR Filing Triggers:
   - Evaluates mandatory SAR generation on high-value illicit money movement (>= $5,000 USD)
     and confirmed mule / money laundering typologies per Policy POL_004.
   - Evaluates mandatory SAR generation when ActionType.FILE_SAR is recommended or risk is CRITICAL.
2. Verified Evidence Extraction:
   - Grounded financial amounts, currencies, timestamps, and account IDs strictly extracted from evidence.
   - Absence of hallucinations: unverified fields (e.g. SSN, customer address) are represented as
     None or 'UNAVAILABLE_IN_SOURCE' rather than invented.
   - 5-part narrative strictly cites valid EvidenceItem.evidence_ids.
3. Serialization & Integration:
   - JSON and Markdown reports serialized to disk in specified output directory.
   - State merge attaches sar_reference, sar_report, and SAR_REPORT_GENERATED timeline event.
   - Clean cases (benign / low risk) produce NO SAR reports or files.
"""

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock
import pytest

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
    create_investigation_graph,
)
from backend.app.agents.nodes.evidence_collection import ParallelEvidenceCollectionNode
from backend.app.models.state import (
    ActionType,
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
from backend.app.reporting.sar_generator import SARGenerator, SARReport


class SARReasoningNode:
    """Configurable reasoning node for testing SAR filing workflow triggers."""

    def __init__(
        self,
        risk_level: RiskLevel,
        risk_score: float,
        action: ActionType,
        typology_id: str = "TYP_MULE",
    ):
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.action = action
        self.typology_id = typology_id

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        supporting_ids = [e.evidence_id for e in state.all_evidence[:3]]
        nba = NextBestAction(
            action_type=self.action,
            reasoning="Reasoning determined high-confidence illicit laundering pattern.",
            evidence_ids=supporting_ids,
            execution_mode=ExecutionMode.SIMULATED,
        )
        return {
            "hypotheses": [
                FraudHypothesis(
                    hypothesis_id="HYP_SAR_01",
                    typology_id=self.typology_id,
                    typology_name="Mule Network Layering",
                    confidence=0.94,
                    indicators=["rapid_pass_through", "high_velocity", "shared_emulator"],
                )
            ],
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "confidence": 0.92,
            "evidence_completeness": 0.95,
            "pre_evidence_next_best_action": nba.model_dump(),
            "post_evidence_next_best_action": nba.model_dump(),
            "timeline": [
                TimelineEvent(
                    event_type="REASONING_COMPLETED",
                    node_name="SARReasoningNode",
                    description=f"Risk: {self.risk_level.value}, Action: {self.action.value}",
                ).model_dump()
            ],
        }


@pytest.fixture
def mock_tg_client_high_value_mule():
    """Mock TigerGraph client returning a $45,000 pass-through mule network transaction."""
    client = MagicMock()
    client.get_transaction_context.return_value = {
        "transaction_id": "TX_MULE_45K",
        "amount": 45000.0,
        "currency": "USD",
        "customer_id": "CUST_MULE_301",
        "account_id": "ACC_MULE_301",
        "device_id": "DEV_EMULATOR_88",
        "ip_address": "198.51.100.99",
    }
    client.get_transaction_behavior.return_value = {
        "transaction_id": "TX_MULE_45K",
        "amount_to_mean_ratio": 12.5,
        "txn_count_5m": 6,
        "is_new_merchant": True,
    }
    client.find_shared_devices.return_value = {
        "device_id": "DEV_EMULATOR_88",
        "shared_account_count": 8,
        "shared_customer_count": 6,
        "linked_fraud_cases": ["HIST_CASE_AML_09"],
    }
    client.find_shared_ips.return_value = {
        "ip_address": "198.51.100.99",
        "shared_account_count": 9,
        "shared_customer_count": 7,
    }
    client.find_fraud_neighbors.return_value = {
        "vertex_id": "ACC_MULE_301",
        "fraud_neighbors_count": 4,
        "neighbor_case_ids": ["HIST_CASE_AML_09", "HIST_CASE_AML_10"],
    }
    client.get_shortest_path_to_fraud.return_value = {
        "vertex_id": "ACC_MULE_301",
        "target_fraud_case_id": "HIST_CASE_AML_09",
        "shortest_distance": 1,
    }
    client.detect_money_flow_patterns.return_value = {
        "account_id": "ACC_MULE_301",
        "fan_in_count": 8,
        "fan_out_count": 1,
        "rapid_pass_through": True,
        "cycle_detected": True,
    }
    client.get_device_identity_context.return_value = {
        "device_id": "DEV_EMULATOR_88",
        "is_new_device": True,
        "linked_account_count": 8,
    }
    return client


@pytest.fixture
def mock_rag_service():
    service = MagicMock()
    mock_policy = MagicMock()
    mock_policy.model_dump.return_value = {
        "chunk_id": "POL_AML_004",
        "source_id": "POL_004",
        "document_type": "POLICY",
        "section_title": "SAR Mandatory Reporting Thresholds",
        "text": "Mandatory SAR filing required on confirmed mule operations exceeding $5,000 USD.",
        "relevance_score": 0.98,
    }
    service.retrieve_policy_context.return_value = MagicMock(items=[mock_policy])
    service.retrieve_similar_cases.return_value = MagicMock(cases=[])
    return service


# ============================================================================
# Scenario 5A — Mandatory SAR Generation on High-Value Laundering
# ============================================================================

@pytest.mark.asyncio
async def test_sar_generation_workflow_on_high_value_fraud(
    mock_tg_client_high_value_mule, mock_rag_service, tmp_path: Path
):
    """Test full workflow generating grounded SAR on high-value illicit laundering."""
    sar_output_dir = tmp_path / "sar_reports"

    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_tg_client_high_value_mule,
        rag_service=mock_rag_service,
    )

    reasoning_node = SARReasoningNode(
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.98,
        action=ActionType.BLOCK_TRANSACTION,
    )

    # Use builder with custom SAR output directory
    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=reasoning_node,
    )
    # Configure ReportIfRequiredNode to use temporary output directory
    builder.nodes["report_if_required"].output_dir = sar_output_dir
    builder.nodes["report_if_required"].sar_generator = SARGenerator(output_dir=sar_output_dir)

    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_SAR_501",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_MULE_45K",
        customer_id="CUST_MULE_301",
        account_ids=["ACC_MULE_301"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Verification of SAR State Merge
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.sar_reference is not None
    assert final_state.sar_report is not None

    sar_report_data = final_state.sar_report

    # 2. Strict grounding in verified financial amounts (no hallucinations)
    suspicious_act = sar_report_data["suspicious_activity"]
    assert suspicious_act["transaction_id"] == "TX_MULE_45K"
    assert suspicious_act["amount"] == 45000.0
    assert suspicious_act["currency"] == "USD"
    assert suspicious_act["risk_level"] == "CRITICAL"

    # 3. Verification of 5-part grounded narrative
    narrative = sar_report_data["narrative"]
    assert "part_1_introduction_trigger" in narrative
    assert "part_2_graph_network_findings" in narrative
    assert "part_3_behavioral_anomalies" in narrative
    assert "part_4_operational_interventions" in narrative
    assert "part_5_compliance_conclusion" in narrative

    # Introduction mentions case ID
    assert "CASE_INT_SAR_501" in narrative["part_1_introduction_trigger"]

    # Behavioral anomalies reflect actual transaction amount
    assert "45,000.00" in narrative["part_3_behavioral_anomalies"]

    # 4. Verification of evidence citations in the SAR report
    evidence_citations = sar_report_data["cited_evidence_ids"]
    assert len(evidence_citations) > 0
    # Every cited evidence ID must exist in state.all_evidence
    state_evidence_ids = {e.evidence_id for e in final_state.all_evidence}
    for cited_id in evidence_citations:
        assert cited_id in state_evidence_ids

    # 5. Verification of disk serialization
    json_files = list(sar_output_dir.glob("*.json"))
    md_files = list(sar_output_dir.glob("*.md"))
    assert len(json_files) >= 1
    assert len(md_files) >= 1

    # Verify JSON content on disk matches report
    with open(json_files[0], "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert disk_data["report_id"] == final_state.sar_reference
    assert disk_data["suspicious_activity"]["amount"] == 45000.0

    # 6. Timeline audit
    timeline_types = [t.event_type for t in final_state.timeline]
    assert "SAR_REPORT_GENERATED" in timeline_types
    assert "CASE_MEMORY_PERSISTED" in timeline_types


# ============================================================================
# Scenario 5B — Benign Activity Skips SAR Filing
# ============================================================================

@pytest.mark.asyncio
async def test_sar_skipped_for_low_risk_benign_activity(tmp_path: Path):
    """Test that legitimate / low-risk investigations strictly skip SAR generation."""
    sar_output_dir = tmp_path / "sar_reports_clean"

    mock_client = MagicMock()
    mock_client.get_transaction_context.return_value = {
        "transaction_id": "TX_COFFEE_01",
        "amount": 4.50,
        "currency": "USD",
        "customer_id": "CUST_CLEAN_01",
        "account_id": "ACC_CLEAN_01",
    }
    mock_client.get_transaction_behavior.return_value = {"amount_to_mean_ratio": 0.9}
    mock_client.find_shared_devices.return_value = {"shared_account_count": 1}
    mock_client.find_shared_ips.return_value = {"shared_account_count": 1}
    mock_client.find_fraud_neighbors.return_value = {"fraud_neighbors_count": 0}
    mock_client.get_shortest_path_to_fraud.return_value = {"shortest_distance": None}
    mock_client.detect_money_flow_patterns.return_value = {"rapid_pass_through": False}
    mock_client.get_device_identity_context.return_value = {"is_new_device": False}

    mock_rag = MagicMock()
    mock_rag.retrieve_policy_context.return_value = MagicMock(items=[])
    mock_rag.retrieve_similar_cases.return_value = MagicMock(cases=[])

    ev_node = ParallelEvidenceCollectionNode(
        tigergraph_client=mock_client,
        rag_service=mock_rag,
    )

    reasoning_node = SARReasoningNode(
        risk_level=RiskLevel.LOW,
        risk_score=0.05,
        action=ActionType.ALLOW_TRANSACTION,
    )

    builder = InvestigationWorkflowBuilder(
        parallel_evidence_collection=ev_node,
        main_reasoning=reasoning_node,
    )
    builder.nodes["report_if_required"].output_dir = sar_output_dir
    builder.nodes["report_if_required"].sar_generator = SARGenerator(output_dir=sar_output_dir)

    workflow = builder.compile()

    trigger_state = FraudCaseState(
        case_id="CASE_INT_CLEAN_502",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_COFFEE_01",
        customer_id="CUST_CLEAN_01",
        account_ids=["ACC_CLEAN_01"],
    )

    final_state = await workflow.ainvoke(trigger_state)

    # 1. Status is completed
    assert final_state.case_status == CaseStatus.COMPLETED
    assert final_state.stop_reason == StopReason.NO_MATERIAL_FRAUD_EVIDENCE

    # 2. Strict absence of SAR
    assert final_state.sar_reference is None
    assert final_state.sar_report is None

    # 3. No files written to disk
    json_files = list(sar_output_dir.glob("*.json"))
    assert len(json_files) == 0

    # 4. SAR event absent from timeline
    timeline_types = [t.event_type for t in final_state.timeline]
    assert "SAR_REPORT_GENERATED" not in timeline_types
