"""Unit tests for Suspicious Activity Report (SAR) Generator (Layer 22).

Verifies:
- Evidence-grounded SAR generation with complete evidence
- Absence of hallucinations / proper representation of missing fields
- 5-part narrative generation citing valid evidence IDs
- JSON and Markdown file serialization to disk
- State merge integration (sar_reference, sar_report, timeline event)
- Safety and simulation disclaimers
"""

import json
from pathlib import Path

from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    EvidenceCategory,
    EvidenceItem,
    EvidenceReliability,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    RiskLevel,
    TimelineEvent,
    TriggerType,
    merge_fraud_case_state,
)
from backend.app.reporting.sar_generator import (
    SAR_AUDIT_DISCLAIMER,
    SARGenerator,
    SARReport,
    generate_case_sar,
)


def test_generate_sar_with_verified_evidence(tmp_path: Path):
    """Verify SAR generation strictly cites evidence IDs and accurately extracts amounts and entities."""
    # Construct verified evidence items
    ev_txn = EvidenceItem(
        evidence_id="EVD_TXN_999",
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Transaction TX_999 amount USD 15,250.00 via Account ACC_001 at High Risk Exchange",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["TX_999", "ACC_001", "CUST_001"],
        metadata={"raw_transaction": {"amount": 15250.00, "currency": "USD", "timestamp": "2026-09-23T12:00:00Z"}},
    )
    ev_graph = EvidenceItem(
        evidence_id="EVD_GRAPH_888",
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.GRAPH_RELATIONSHIP,
        fact="Shortest path distance to confirmed mule hub is 1 hop via shared IP 198.51.100.4",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["ACC_001", "198.51.100.4"],
    )
    ev_dev = EvidenceItem(
        evidence_id="EVD_DEV_777",
        source="TIGERGRAPH_GSQL",
        category=EvidenceCategory.DEVICE,
        fact="Transaction originated from Device DEV_EMULATOR_01 and IP 198.51.100.4",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["DEV_EMULATOR_01", "198.51.100.4"],
    )
    ev_pol = EvidenceItem(
        evidence_id="EVD_POL_004",
        source="POLICY_GRAPHRAG",
        category=EvidenceCategory.POLICY,
        fact="Policy POL_004 requires filing SAR when illicit flow exceeds $5,000 USD",
        reliability=EvidenceReliability.HIGH,
        entity_ids=["POL_004"],
    )

    state = FraudCaseState(
        case_id="CASE_SAR_01",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_999",
        customer_id="CUST_001",
        account_ids=["ACC_001"],
        transaction_evidence=[ev_txn],
        graph_evidence=[ev_graph],
        device_evidence=[ev_dev],
        policy_evidence=[ev_pol],
        graph_features={
            "fraud_neighbors_count": 3,
            "shared_device_account_count": 4,
            "shortest_distance_to_fraud": 1,
            "cycle_detected": True,
            "rapid_pass_through": True,
        },
        hypotheses=[
            FraudHypothesis(
                hypothesis_id="HYP_MULE",
                title="Mule Ring & Layering",
                description="High velocity pass-through via mule network",
                likelihood=0.92,
            )
        ],
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.95,
        confidence=0.88,
        evidence_completeness=0.90,
        executed_actions=[
            ActionExecution(
                action_type=ActionType.BLOCK_ACCOUNT,
                execution_mode=ExecutionMode.SIMULATED,
                success=True,
                result={"hold_status": "ADMINISTRATIVE_FREEZE"},
            )
        ],
        approval_decisions=[
            ApprovalDecision(
                action_type=ActionType.FILE_SAR,
                status=ApprovalStatus.APPROVED,
                reviewer_role=ApprovalRole.COMPLIANCE_OFFICER,
                reviewer_id="COMPLIANCE_OFFICER_01",
                comments="Verified mule network aggregation. Proceed with SAR filing.",
            )
        ],
    )

    generator = SARGenerator(output_dir=tmp_path)
    report, patch = generator.generate_sar(state, save_to_disk=True)

    # 1. Header & ID assertions
    assert report.report_id.startswith("SAR_")
    assert report.case_id == "CASE_SAR_01"
    assert report.filing_type == "INITIAL_SUSPICIOUS_ACTIVITY_REPORT"
    assert report.audit_disclaimer == SAR_AUDIT_DISCLAIMER
    assert report.approval_status == "APPROVED"
    assert report.compliance_reviewer_id == "COMPLIANCE_OFFICER_01"

    # 2. Subject assertions
    assert report.subject.customer_id == "CUST_001"
    assert "ACC_001" in report.subject.account_ids
    assert "DEV_EMULATOR_01" in report.subject.associated_devices
    assert "198.51.100.4" in report.subject.associated_ips

    # 3. Suspicious activity assertions
    assert report.suspicious_activity.transaction_id == "TX_999"
    assert report.suspicious_activity.amount == 15250.00
    assert report.suspicious_activity.currency == "USD"
    assert report.suspicious_activity.typology == "Mule Ring & Layering"
    assert report.suspicious_activity.risk_level == "CRITICAL"
    assert report.suspicious_activity.risk_score == 0.95
    assert any("fraud neighbor" in ind for ind in report.suspicious_activity.indicators)
    assert any("Circular money movement" in ind for ind in report.suspicious_activity.indicators)

    # 4. Citations & Narrative assertions
    assert "EVD_TXN_999" in report.cited_evidence_ids
    assert "EVD_GRAPH_888" in report.cited_evidence_ids
    assert "EVD_DEV_777" in report.cited_evidence_ids
    assert "EVD_POL_004" in report.cited_evidence_ids

    assert "PART I" in report.narrative.part_1_introduction_trigger
    assert "15,250.00" in report.narrative.part_1_introduction_trigger
    assert "EVD_GRAPH_888" in report.narrative.part_2_graph_network_findings
    assert "EVD_TXN_999" in report.narrative.part_3_behavioral_anomalies
    assert "BLOCK_ACCOUNT" in report.narrative.part_4_operational_interventions
    assert "POL_004" in report.narrative.part_5_compliance_conclusion

    # 5. File serialization assertions
    json_path = Path(report.file_path_json)
    md_path = Path(report.file_path_markdown)
    assert json_path.exists()
    assert md_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["report_id"] == report.report_id
        assert data["suspicious_activity"]["amount"] == 15250.00

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
        assert "# SUSPICIOUS ACTIVITY REPORT (SAR)" in md_text
        assert "USD 15,250.00" in md_text
        assert "EVD_TXN_999" in md_text

    # 6. State patch assertions
    assert patch["sar_reference"] == report.report_id
    assert patch["sar_report"]["report_id"] == report.report_id
    assert len(patch["timeline"]) == 1
    assert patch["timeline"][0]["event_type"] == "SAR_REPORT_GENERATED"


def test_generate_sar_sparse_evidence_no_hallucinations(tmp_path: Path):
    """Verify SAR generation without evidence does not fabricate amounts, dates, or identities."""
    state = FraudCaseState(
        case_id="CASE_SPARSE_01",
        trigger_type=TriggerType.HIGH_RISK_RULE,
    )

    generator = SARGenerator(output_dir=tmp_path)
    report, patch = generator.generate_sar(state, save_to_disk=True)

    assert report.subject.customer_id == "NOT_AVAILABLE"
    assert report.subject.account_ids == []
    assert report.subject.associated_devices == []
    assert report.subject.associated_ips == []
    assert report.suspicious_activity.transaction_id == "NOT_AVAILABLE"
    assert report.suspicious_activity.amount is None
    assert report.suspicious_activity.activity_timestamp is None
    assert "NOT_AVAILABLE" in report.narrative.part_1_introduction_trigger


def test_generate_case_sar_convenience_function(tmp_path: Path):
    """Verify generate_case_sar functional wrapper."""
    state = FraudCaseState(
        case_id="CASE_WRAPPER_01",
        customer_id="CUST_WRAP",
    )
    report, patch = generate_case_sar(state, output_dir=tmp_path)
    assert report.case_id == "CASE_WRAPPER_01"
    assert report.subject.customer_id == "CUST_WRAP"
    assert patch["sar_reference"] == report.report_id


def test_sar_state_merge_integration(tmp_path: Path):
    """Verify merge_fraud_case_state updates sar_reference and sar_report."""
    state = FraudCaseState(case_id="CASE_MERGE_01")
    generator = SARGenerator(output_dir=tmp_path)
    report, patch = generator.generate_sar(state, save_to_disk=False)

    merged = merge_fraud_case_state(state, patch)
    assert merged.sar_reference == report.report_id
    assert merged.sar_report is not None
    assert merged.sar_report["report_id"] == report.report_id
    assert any(t.event_type == "SAR_REPORT_GENERATED" for t in merged.timeline)
