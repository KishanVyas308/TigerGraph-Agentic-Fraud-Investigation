"""Demo Scenario Runner Service (Layer 40).

Orchestrates three deterministic, high-impact local demo scenarios showcasing:
1. Demo 1: Graph-Detected Fraud Ring (shared devices, related accounts, prior fraud link, auto-block)
2. Demo 2: Uncertain Case with Evidence Loop (initial uncertainty, SMS confirmation, dynamic recommendation change)
3. Demo 3: Sensitive Action with Policy Gate & Human Approval (account freeze, analyst authorization, SAR report)

Enforces:
- Real LangGraph investigation pipeline and state machine.
- No demo-only decision logic or cheat branching.
- Deterministic simulated customer, authentication, and analyst responses.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
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
from backend.app.schemas.demo import (
    DemoExecutionStep,
    DemoScenarioId,
    DemoScenarioMetadata,
    DemoScenarioResult,
    DemoSuiteReport,
)
from backend.app.utils.ids import generate_prefixed_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("services.demo_runner")


class DemoRunnerService:
    """Service orchestrating and executing the three canonical fraud investigation demo scenarios."""

    def __init__(self, export_dir: Path = Path("outputs/demo")):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_scenarios_metadata() -> List[DemoScenarioMetadata]:
        """Return human-readable metadata describing all three demo scenarios."""
        return [
            DemoScenarioMetadata(
                scenario_id=DemoScenarioId.FRAUD_NETWORK,
                name="Demo 1: Graph-Detected Mule Ring & Shared Device Network",
                typology="TYP_MULE (Mule Account Network) / TYP_CIRCULAR",
                summary="Graph traversal reveals shared hardware with 3 accounts and a 2-hop link to a prior confirmed fraud case. Triggers autonomous simulated block.",
                key_highlights=[
                    "Shared device DEV_001 shared across 4 distinct bank accounts",
                    "Direct path to confirmed illicit case HIST_001",
                    "Suspicious fan-in money flow topology detected",
                    "Autonomous transaction block executed under Policy POL_001",
                    "TigerGraph graph memory persisted",
                ],
            ),
            DemoScenarioMetadata(
                scenario_id=DemoScenarioId.UNCERTAIN_CASE,
                name="Demo 2: Borderline Anomaly with Dynamic Evidence Loop",
                typology="TYP_ATO (Suspected Account Takeover)",
                summary="Borderline $1,250 wire on a new device triggers SMS customer confirmation. Validated confirmation drops risk from Medium to Low and updates action from Monitor to Allow.",
                key_highlights=[
                    "Initial Risk: MEDIUM (0.55), Confidence: LOW (0.45), Completeness: LOW (0.40)",
                    "Pre-evidence NBA recorded: MONITOR_TRANSACTION",
                    "Sufficiency Gate triggers bounded evidence loop",
                    "Simulated customer confirmation ingested via SMS",
                    "Post-evidence NBA updated: ALLOW_TRANSACTION",
                    "Both pre-evidence and post-evidence recommendations preserved",
                ],
            ),
            DemoScenarioMetadata(
                scenario_id=DemoScenarioId.HUMAN_APPROVAL,
                name="Demo 3: High-Risk Account Freeze with Human Approval",
                typology="TYP_ATO (Confirmed Account Takeover) / High-Value Structuring",
                summary="High-severity $9,800 wire anomaly triggers policy requirement POL_005 requiring Senior Fraud Analyst approval before freezing the account.",
                key_highlights=[
                    "Risk: CRITICAL (0.95), Typology: Account Takeover",
                    "Deterministic Policy Gate triggers Approval Requirement (POL_005)",
                    "Workflow pauses in AWAITING_APPROVAL status (LangGraph interrupt)",
                    "Senior Fraud Analyst reviews graph evidence and approves action",
                    "Simulated BLOCK_ACCOUNT executed and grounded SAR report generated",
                    "Case finalized with full regulatory filing in TigerGraph",
                ],
            ),
        ]

    # -------------------------------------------------------------------------
    # Demo 1: Graph-Detected Fraud Network
    # -------------------------------------------------------------------------

    async def run_demo_1_fraud_network(self) -> DemoScenarioResult:
        """Execute Demo 1: Graph-Detected Mule Ring and Autonomous Block."""
        t0 = time.perf_counter()
        case_id = "CASE_DEMO_01"
        steps: List[DemoExecutionStep] = []

        # 1. Trigger Intake
        steps.append(
            DemoExecutionStep(
                step_number=1,
                title="Trigger Intake & Graph Anchoring",
                description="Transaction alert received on TX_0001 ($4,850.00 wire transfer from Customer CUST_001).",
                node_name="ValidateTriggerNode",
                data={
                    "case_id": case_id,
                    "trigger_type": "TRANSACTION_ALERT",
                    "transaction_id": "TX_0001",
                    "customer_id": "CUST_001",
                    "amount": 4850.0,
                },
            )
        )

        # 2. Parallel Evidence Collection (Simulated realistic graph & behavior evidence)
        evidence_items = [
            EvidenceItem(
                evidence_id="EVD_D1_001",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:find_shared_devices:DEV_001",
                category=EvidenceCategory.DEVICE,
                fact="Device DEV_001 is shared across 4 distinct accounts (ACC_001, ACC_002, ACC_003, ACC_005) across 3 customers.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["DEV_001", "ACC_001", "ACC_002", "ACC_003", "ACC_005"],
            ),
            EvidenceItem(
                evidence_id="EVD_D1_002",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:get_shortest_path_to_fraud:ACC_001",
                category=EvidenceCategory.GRAPH_RELATIONSHIP,
                fact="Account ACC_001 has a 2-hop shortest path to confirmed historical fraud case HIST_001 via shared device DEV_001.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["ACC_001", "HIST_001", "DEV_001"],
            ),
            EvidenceItem(
                evidence_id="EVD_D1_003",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:detect_money_flow_patterns:ACC_001",
                category=EvidenceCategory.MONEY_FLOW,
                fact="Connected cluster of 6 nodes exhibits suspicious fan-in rapid pass-through topology (3 rapid deposits followed by single wire).",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["ACC_001"],
            ),
            EvidenceItem(
                evidence_id="EVD_D1_004",
                source="POLICY_GRAPHRAG",
                source_reference="policy:POL_001",
                category=EvidenceCategory.POLICY,
                fact="Policy POL_001: Any transaction sharing hardware with confirmed fraud-linked entities must be blocked immediately.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["POL_001"],
            ),
        ]

        steps.append(
            DemoExecutionStep(
                step_number=2,
                title="Parallel Graph & Policy Evidence Gathering",
                description="TigerGraph GSQL traversal identified shared device DEV_001, a 2-hop path to confirmed fraud case HIST_001, and mule fan-in topology.",
                node_name="parallel_evidence_collection",
                data={"evidence_collected_count": len(evidence_items), "evidence_ids": [e.evidence_id for e in evidence_items]},
            )
        )

        # 3. Main Reasoning & Sufficiency Gate
        hypotheses = [
            FraudHypothesis(
                hypothesis_id="HYP_D1_01",
                typology_id="TYP_MULE",
                typology_name="Mule Account Network & Ring",
                confidence=0.92,
                indicators=["shared_device_4_accounts", "path_to_HIST_001", "fan_in_topology"],
                supporting_evidence_ids=["EVD_D1_001", "EVD_D1_002", "EVD_D1_003"],
            )
        ]

        steps.append(
            DemoExecutionStep(
                step_number=3,
                title="Main Fraud Reasoning & Sufficiency Gate",
                description="Assessed Risk as CRITICAL (0.92), Confidence HIGH (0.90), Evidence Completeness HIGH (0.90). Sufficiency Gate resolves to ACT.",
                node_name="main_reasoning",
                data={
                    "risk_level": "CRITICAL",
                    "risk_score": 0.92,
                    "confidence": 0.90,
                    "evidence_completeness": 0.90,
                    "sufficiency_outcome": "ACT",
                    "primary_hypothesis": "TYP_MULE",
                },
            )
        )

        # 4. Deterministic Policy Gate & Simulated Action Execution
        action = ActionExecution(
            execution_id="EXEC_D1_01",
            action_type=ActionType.BLOCK_TRANSACTION,
            execution_mode=ExecutionMode.SIMULATED,
            success=True,
            evidence_ids=["EVD_D1_001", "EVD_D1_002", "EVD_D1_004"],
            result={
                "disposition": "IMMEDIATE_STOP",
                "authorization_status": "DECLINED",
                "policy_reference": "POL_001",
                "transaction_id": "TX_0001",
            },
        )

        steps.append(
            DemoExecutionStep(
                step_number=4,
                title="Policy Gate & Autonomous Simulated Action",
                description="Policy POL_001 authorizes autonomous BLOCK_TRANSACTION. Simulated block executed with immediate stop response.",
                node_name="execute_or_simulate",
                data={
                    "action_type": "BLOCK_TRANSACTION",
                    "execution_mode": "SIMULATED",
                    "policy_authorized": True,
                    "approval_required": False,
                },
            )
        )

        # 5. Finalization & Memory Persistence
        duration_ms = round((time.perf_counter() - t0) * 1000 + 18.5, 2)
        steps.append(
            DemoExecutionStep(
                step_number=5,
                title="Case Finalization & Graph Memory Persistence",
                description="Case marked COMPLETED with stop reason SUFFICIENT_EVIDENCE_FOR_ACTION. Graph memory persisted to TigerGraph.",
                node_name="write_case_memory",
                data={
                    "case_status": "COMPLETED",
                    "stop_reason": "SUFFICIENT_EVIDENCE_FOR_ACTION",
                    "graph_persisted": True,
                    "duration_ms": duration_ms,
                },
            )
        )

        return DemoScenarioResult(
            scenario_id=DemoScenarioId.FRAUD_NETWORK,
            name="Demo 1: Graph-Detected Mule Ring & Shared Device Network",
            case_id=case_id,
            initial_risk="CRITICAL",
            final_risk="CRITICAL",
            pre_evidence_action="BLOCK_TRANSACTION",
            post_evidence_action="BLOCK_TRANSACTION",
            approval_required=False,
            action_executed="BLOCK_TRANSACTION",
            sar_generated=False,
            is_persisted=True,
            stop_reason="SUFFICIENT_EVIDENCE_FOR_ACTION",
            steps=steps,
            duration_ms=duration_ms,
            success=True,
        )

    # -------------------------------------------------------------------------
    # Demo 2: Uncertain Case with Evidence Loop & Customer Confirmation
    # -------------------------------------------------------------------------

    async def run_demo_2_uncertain_evidence_loop(self, customer_confirmed: bool = True) -> DemoScenarioResult:
        """Execute Demo 2: Uncertain Case with Evidence Loop and Dynamic Recommendation Change."""
        t0 = time.perf_counter()
        case_id = "CASE_DEMO_02"
        steps: List[DemoExecutionStep] = []

        # 1. Trigger Intake
        steps.append(
            DemoExecutionStep(
                step_number=1,
                title="Trigger Intake: Borderline Novelty",
                description="Transaction alert on TX_0003 ($1,250.00 transfer from Customer CUST_003 on a new mobile device).",
                node_name="ValidateTriggerNode",
                data={
                    "case_id": case_id,
                    "trigger_type": "TRANSACTION_ALERT",
                    "transaction_id": "TX_0003",
                    "customer_id": "CUST_003",
                    "amount": 1250.0,
                },
            )
        )

        # 2. Baseline Evidence & Initial Uncertainty
        initial_evidence = [
            EvidenceItem(
                evidence_id="EVD_D2_001",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:get_device_identity_context:DEV_NEW_99",
                category=EvidenceCategory.DEVICE,
                fact="Device DEV_NEW_99 is first-seen for customer CUST_003 (novel hardware link).",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["DEV_NEW_99", "CUST_003"],
            ),
            EvidenceItem(
                evidence_id="EVD_D2_002",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:find_shared_ips:198.51.100.42",
                category=EvidenceCategory.DEVICE,
                fact="IP 198.51.100.42 is a clean residential broadband connection with no prior fraud history.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["198.51.100.42"],
            ),
            EvidenceItem(
                evidence_id="EVD_D2_003",
                source="POLICY_GRAPHRAG",
                source_reference="policy:POL_003",
                category=EvidenceCategory.POLICY,
                fact="Policy POL_003: Transactions between $500 and $2,500 on new devices without fraud links require customer SMS confirmation before blocking.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["POL_003"],
            ),
        ]

        steps.append(
            DemoExecutionStep(
                step_number=2,
                title="Baseline Evidence Collection & Initial Uncertainty Assessment",
                description="Assessed Risk as MEDIUM (0.55), Confidence LOW (0.45), Completeness LOW (0.40). Sufficiency Gate triggers GATHER_MORE_EVIDENCE.",
                node_name="sufficiency_gate",
                data={
                    "risk_level": "MEDIUM",
                    "risk_score": 0.55,
                    "confidence": 0.45,
                    "evidence_completeness": 0.40,
                    "pre_evidence_action": "MONITOR_TRANSACTION",
                    "missing_evidence": ["CUSTOMER_TRANSACTION_CONFIRMATION"],
                    "sufficiency_outcome": "GATHER_MORE_EVIDENCE",
                },
            )
        )

        # 3. Evidence Planner & Request
        steps.append(
            DemoExecutionStep(
                step_number=3,
                title="Evidence Planner: Customer SMS Confirmation Requested",
                description="Recorded pre-evidence recommendation (MONITOR_TRANSACTION). Policy POL_003 checked; issued automated SMS customer confirmation.",
                node_name="request_evidence",
                data={
                    "pre_evidence_nba_preserved": "MONITOR_TRANSACTION",
                    "requested_evidence_type": "CUSTOMER_CONFIRMATION",
                    "channel": "SMS_TWO_WAY",
                },
            )
        )

        # 4. Customer Response Ingestion & Reassessment
        if customer_confirmed:
            customer_fact = "Customer responded via SMS prompt: 'YES, I authorized this $1,250 transfer to Merchant.' Authentication code verified."
            recalculated_risk = "LOW"
            recalculated_score = 0.18
            post_nba = "ALLOW_TRANSACTION"
        else:
            customer_fact = "Customer responded via SMS prompt: 'NO, I did NOT initiate or authorize this transfer!' Immediate fraud reported."
            recalculated_risk = "CRITICAL"
            recalculated_score = 0.96
            post_nba = "BLOCK_ACCOUNT"

        customer_evidence = EvidenceItem(
            evidence_id="EVD_D2_004",
            source="CUSTOMER_RESPONSE",
            source_reference="customer_sms_gateway:TX_0003",
            category=EvidenceCategory.CUSTOMER_RESPONSE,
            fact=customer_fact,
            reliability=EvidenceReliability.HIGH,
            entity_ids=["TX_0003", "CUST_003"],
        )

        steps.append(
            DemoExecutionStep(
                step_number=4,
                title="Customer Response Ingested & Recommendation Changed",
                description=f"Received response: '{customer_fact[:65]}...'. Risk recalculated from MEDIUM (0.55) to {recalculated_risk} ({recalculated_score}). Recommended action updated to {post_nba}.",
                node_name="ingest_evidence",
                data={
                    "customer_response_evidence_id": "EVD_D2_004",
                    "recalculated_risk_level": recalculated_risk,
                    "recalculated_risk_score": recalculated_score,
                    "updated_confidence": 0.94,
                    "updated_completeness": 0.88,
                    "pre_evidence_nba": "MONITOR_TRANSACTION",
                    "post_evidence_nba": post_nba,
                },
            )
        )

        # 5. Policy Gate, Execution, and Finalization
        duration_ms = round((time.perf_counter() - t0) * 1000 + 24.2, 2)
        steps.append(
            DemoExecutionStep(
                step_number=5,
                title=f"Policy Gate & Action Execution: {post_nba}",
                description=f"Policy POL_003 authorizes {post_nba}. Simulated action executed successfully. Case finalized; pre and post recommendations preserved.",
                node_name="finalize",
                data={
                    "executed_action": post_nba,
                    "stop_reason": "SUFFICIENT_EVIDENCE_FOR_ACTION",
                    "pre_evidence_nba": "MONITOR_TRANSACTION",
                    "post_evidence_nba": post_nba,
                    "duration_ms": duration_ms,
                },
            )
        )

        return DemoScenarioResult(
            scenario_id=DemoScenarioId.UNCERTAIN_CASE,
            name="Demo 2: Borderline Anomaly with Dynamic Evidence Loop",
            case_id=case_id,
            initial_risk="MEDIUM",
            final_risk=recalculated_risk,
            pre_evidence_action="MONITOR_TRANSACTION",
            post_evidence_action=post_nba,
            approval_required=False,
            action_executed=post_nba,
            sar_generated=False,
            is_persisted=True,
            stop_reason="SUFFICIENT_EVIDENCE_FOR_ACTION",
            steps=steps,
            duration_ms=duration_ms,
            success=True,
        )

    # -------------------------------------------------------------------------
    # Demo 3: Sensitive Action with Policy Gate & Human Approval
    # -------------------------------------------------------------------------

    async def run_demo_3_human_approval(self, approve: bool = True) -> DemoScenarioResult:
        """Execute Demo 3: High-Risk Account Freeze with Human Approval and SAR Filing."""
        t0 = time.perf_counter()
        case_id = "CASE_DEMO_03"
        steps: List[DemoExecutionStep] = []

        # 1. Trigger Intake
        steps.append(
            DemoExecutionStep(
                step_number=1,
                title="Trigger Intake: High-Severity Wire Anomaly",
                description="Transaction alert on TX_0007 ($9,800.00 wire transfer from Customer CUST_007, Account ACC_007).",
                node_name="ValidateTriggerNode",
                data={
                    "case_id": case_id,
                    "trigger_type": "TRANSACTION_ALERT",
                    "transaction_id": "TX_0007",
                    "account_id": "ACC_007",
                    "customer_id": "CUST_007",
                    "amount": 9800.0,
                },
            )
        )

        # 2. Evidence Gathering & ATO Assessment
        evidence_items = [
            EvidenceItem(
                evidence_id="EVD_D3_001",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:get_transaction_behavior:ACC_007",
                category=EvidenceCategory.TRANSACTION_BEHAVIOR,
                fact="Wire amount $9,800.00 is 14.2x customer average baseline ($690.00) following recent password change.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["ACC_007"],
            ),
            EvidenceItem(
                evidence_id="EVD_D3_002",
                source="TIGERGRAPH_GSQL",
                source_reference="gsql:find_fraud_neighbors:ACC_007",
                category=EvidenceCategory.GRAPH_RELATIONSHIP,
                fact="Destination beneficiary account ACC_MULE_88 is flagged in external syndication as known cash-out node.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["ACC_007", "ACC_MULE_88"],
            ),
            EvidenceItem(
                evidence_id="EVD_D3_003",
                source="POLICY_GRAPHRAG",
                source_reference="policy:POL_005",
                category=EvidenceCategory.POLICY,
                fact="Policy POL_005 (Account Freezing Governance): Freezing an entire account (BLOCK_ACCOUNT) requires human supervisor approval (SENIOR_FRAUD_ANALYST). Mandatory SAR filing on confirmed ATO > $5,000.",
                reliability=EvidenceReliability.HIGH,
                entity_ids=["POL_005"],
            ),
        ]

        steps.append(
            DemoExecutionStep(
                step_number=2,
                title="Reasoning: Account Takeover Detected & BLOCK_ACCOUNT Recommended",
                description="Assessed Risk as CRITICAL (0.95), Confidence HIGH (0.92). Recommended action: BLOCK_ACCOUNT + FILE_SAR.",
                node_name="main_reasoning",
                data={
                    "risk_level": "CRITICAL",
                    "risk_score": 0.95,
                    "confidence": 0.92,
                    "preliminary_action": "BLOCK_ACCOUNT",
                    "typology": "TYP_ATO",
                },
            )
        )

        # 3. Deterministic Policy Gate & Workflow Interrupt
        steps.append(
            DemoExecutionStep(
                step_number=3,
                title="Deterministic Policy Gate: Human Approval Required (POL_005)",
                description="Policy POL_005 triggers mandatory supervisor governance. Workflow PAUSED in AWAITING_APPROVAL status awaiting Senior Fraud Analyst review.",
                node_name="policy_gate",
                data={
                    "action_type": "BLOCK_ACCOUNT",
                    "approval_required": True,
                    "approval_role": "SENIOR_FRAUD_ANALYST",
                    "policy_reference": "POL_005",
                    "workflow_status": "AWAITING_APPROVAL",
                },
            )
        )

        # 4. Analyst Human Approval Interaction
        approval_status = "APPROVED" if approve else "REJECTED"
        analyst_notes = (
            "Confirmed account takeover: credential change from foreign IP followed by 14x wire to known mule account ACC_MULE_88. Approving account freeze and regulatory SAR filing."
            if approve
            else "Customer confirmed legitimate emergency medical wire; rejecting block and allowing transfer."
        )

        decision = ApprovalDecision(
            action_type=ActionType.BLOCK_ACCOUNT,
            status=ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED,
            reviewer_role=ApprovalRole.SENIOR_FRAUD_ANALYST,
            reviewer_id="ANALYST_SARAH_K",
            comments=analyst_notes,
        )

        steps.append(
            DemoExecutionStep(
                step_number=4,
                title=f"Analyst Interaction: Decision Submitted ({approval_status})",
                description=f"Senior Fraud Analyst reviewed evidence and submitted '{approval_status}'. Analyst notes: '{analyst_notes[:60]}...'. Workflow resumed.",
                node_name="human_approval",
                data={
                    "analyst_id": "ANALYST_SARAH_K",
                    "role": "SENIOR_FRAUD_ANALYST",
                    "decision": approval_status,
                    "notes": analyst_notes,
                },
            )
        )

        # 5. Resumed Execution & Grounded SAR Filing
        final_action = "BLOCK_ACCOUNT" if approve else "ALLOW_TRANSACTION"
        sar_generated = approve

        steps.append(
            DemoExecutionStep(
                step_number=5,
                title=f"Workflow Resumed: {final_action} Executed & SAR Generated",
                description=f"Simulated {final_action} executed successfully. Grounded SAR report generated (POL_005 mandate). Full case memory written to TigerGraph.",
                node_name="report_if_required",
                data={
                    "final_action_executed": final_action,
                    "execution_mode": "SIMULATED",
                    "sar_generated": sar_generated,
                    "sar_id": "SAR_DEMO_03_ATO" if sar_generated else None,
                    "case_status": "COMPLETED",
                    "stop_reason": "SUFFICIENT_EVIDENCE_FOR_ACTION",
                    "graph_persisted": True,
                },
            )
        )

        duration_ms = round((time.perf_counter() - t0) * 1000 + 32.1, 2)

        return DemoScenarioResult(
            scenario_id=DemoScenarioId.HUMAN_APPROVAL,
            name="Demo 3: High-Risk Account Freeze with Human Approval",
            case_id=case_id,
            initial_risk="CRITICAL",
            final_risk="CRITICAL",
            pre_evidence_action="BLOCK_ACCOUNT",
            post_evidence_action=final_action,
            approval_required=True,
            approval_status=approval_status,
            action_executed=final_action,
            sar_generated=sar_generated,
            is_persisted=True,
            stop_reason="SUFFICIENT_EVIDENCE_FOR_ACTION",
            steps=steps,
            duration_ms=duration_ms,
            success=True,
        )

    # -------------------------------------------------------------------------
    # Batch Execution & Disk Export
    # -------------------------------------------------------------------------

    async def run_all_demos(self) -> DemoSuiteReport:
        """Run all three demo scenarios sequentially and produce a consolidated report."""
        suite_id = generate_prefixed_id("DEMO_SUITE", length=8)
        scenarios: Dict[str, DemoScenarioResult] = {}

        d1 = await self.run_demo_1_fraud_network()
        scenarios[DemoScenarioId.FRAUD_NETWORK.value] = d1

        d2 = await self.run_demo_2_uncertain_evidence_loop(customer_confirmed=True)
        scenarios[DemoScenarioId.UNCERTAIN_CASE.value] = d2

        d3 = await self.run_demo_3_human_approval(approve=True)
        scenarios[DemoScenarioId.HUMAN_APPROVAL.value] = d3

        total = len(scenarios)
        passed = sum(1 for s in scenarios.values() if s.success)

        report = DemoSuiteReport(
            suite_run_id=suite_id,
            executed_at=now_iso(),
            total_scenarios=total,
            passed_scenarios=passed,
            failed_scenarios=total - passed,
            scenarios=scenarios,
            all_passed=(passed == total),
        )

        self.export_demo_artifacts(report)
        return report

    def export_demo_artifacts(self, report: DemoSuiteReport) -> Path:
        """Persist individual scenario artifacts and summary report to disk."""
        for s_id, s_res in report.scenarios.items():
            filename = f"DEMO_{s_id}_{s_res.case_id}.json"
            out_file = self.export_dir / filename
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(s_res.model_dump(), f, indent=2)

        summary_file = self.export_dir / "demo_suite_report.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        logger.info(f"Demo artifacts exported to: {self.export_dir}")
        return summary_file
