"""Unit Tests for Layer 37: Benchmark Runner.

Verifies:
1. Benchmark trigger loading from parquet (all 20 cases).
2. Entity context resolution across TRANSACTION, ACCOUNT, CUSTOMER, DEVICE, and IP_ADDRESS triggers.
3. Initial FraudCaseState anchor construction.
4. BenchmarkCaseAnswer schema validation, property aliases, and export dictionary.
5. End-to-end benchmark case execution with graph persistence and precedent quarantine.
6. Batch execution with run summary generation.
7. Benchmark runner CLI execution.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from backend.app.agents.graph import InvestigationWorkflowBuilder
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
from backend.app.schemas.benchmark import (
    BenchmarkApprovalRoute,
    BenchmarkCaseAnswer,
    BenchmarkCaseDetails,
    BenchmarkCaseRunMetric,
    BenchmarkRunSummary,
)
from backend.app.services.benchmark_runner import BenchmarkRunnerService


class MockBenchmarkReasoningNode:
    """Deterministic fast reasoning node for benchmark testing."""

    async def process(self, state: FraudCaseState) -> dict:
        nba = NextBestAction(
            action_type=ActionType.BLOCK_TRANSACTION,
            reasoning="High velocity and anomaly score detected on benchmark entity.",
            execution_mode=ExecutionMode.SIMULATED,
        )
        return {
            "risk_level": RiskLevel.HIGH.value,
            "risk_score": 0.82,
            "confidence": 0.88,
            "evidence_completeness": 0.85,
            "hypotheses": [
                FraudHypothesis(
                    hypothesis_id="HYP_BENCH_01",
                    typology_id="TYP_VELOCITY_BURST",
                    typology_name="Velocity Burst",
                    confidence=0.88,
                    indicators=["rapid_tx_count"],
                ).model_dump()
            ],
            "pre_evidence_next_best_action": nba.model_dump(),
            "post_evidence_next_best_action": nba.model_dump(),
            "timeline": [
                TimelineEvent(
                    event_type="REASONING_COMPLETED",
                    node_name="MockBenchmarkReasoningNode",
                    description="Assessed benchmark case as HIGH risk.",
                ).model_dump()
            ],
        }


def test_benchmark_trigger_loading():
    """Verify that all 20 benchmark case triggers load from parquet."""
    runner = BenchmarkRunnerService()
    triggers = runner.load_benchmark_triggers()

    assert len(triggers) == 20
    case_ids = [t["case_id"] for t in triggers]
    for i in range(1, 21):
        expected_id = f"CASE_{i:03d}"
        assert expected_id in case_ids

    # Validate schema of triggers
    for t in triggers:
        assert "case_id" in t
        assert "trigger_type" in t
        assert "trigger_timestamp" in t
        assert "trigger_entity_id" in t
        assert "trigger_entity_type" in t
        assert "description" in t


def test_entity_context_resolution():
    """Verify entity graph resolution across distinct trigger entity types."""
    runner = BenchmarkRunnerService()

    # Case 1: TRANSACTION trigger
    trg_tx = {
        "case_id": "CASE_001",
        "trigger_entity_type": "TRANSACTION",
        "trigger_entity_id": "TX_0001",
    }
    txn_id, cust_id, acc_ids = runner.resolve_entity_context(trg_tx)
    assert txn_id == "TX_0001"
    assert len(acc_ids) > 0
    assert cust_id is not None

    # Case 2: ACCOUNT trigger
    trg_acc = {
        "case_id": "CASE_002",
        "trigger_entity_type": "ACCOUNT",
        "trigger_entity_id": "ACC_003",
    }
    txn_id, cust_id, acc_ids = runner.resolve_entity_context(trg_acc)
    assert "ACC_003" in acc_ids
    assert cust_id is not None

    # Case 3: DEVICE trigger
    trg_dev = {
        "case_id": "CASE_003",
        "trigger_entity_type": "DEVICE",
        "trigger_entity_id": "DEV_004",
    }
    txn_id, cust_id, acc_ids = runner.resolve_entity_context(trg_dev)
    assert len(acc_ids) > 0

    # Case 4: IP_ADDRESS trigger
    trg_ip = {
        "case_id": "CASE_004",
        "trigger_entity_type": "IP_ADDRESS",
        "trigger_entity_id": "198.51.100.5",
    }
    txn_id, cust_id, acc_ids = runner.resolve_entity_context(trg_ip)
    assert len(acc_ids) > 0


def test_initial_state_construction():
    """Verify initial FraudCaseState anchor is properly populated."""
    runner = BenchmarkRunnerService()
    trigger = {
        "case_id": "CASE_005",
        "trigger_type": "ACCOUNT_TAKEOVER_ALERT",
        "trigger_entity_type": "ACCOUNT",
        "trigger_entity_id": "ACC_006",
        "description": "Password reset followed by high draw",
        "trigger_timestamp": "2026-09-21T10:00:00+00:00",
    }

    state = runner.build_initial_state(trigger)
    assert state.case_id == "CASE_005"
    assert "ACC_006" in state.account_ids
    assert state.customer_id is not None
    assert state.metadata["benchmark_case"] is True
    assert state.metadata["raw_trigger_type"] == "ACCOUNT_TAKEOVER_ALERT"


def test_benchmark_case_answer_serialization(tmp_path):
    """Verify BenchmarkCaseAnswer schema, aliases, and JSON export."""
    details = BenchmarkCaseDetails(
        case_id="CASE_TEST_001",
        trigger_type="HIGH_AMOUNT_ANOMALY",
        trigger_entity_id="TX_TEST_01",
        trigger_entity_type="TRANSACTION",
        description="Wire anomaly test",
        transaction_id="TX_TEST_01",
        customer_id="CUST_TEST_01",
        account_ids=["ACC_TEST_01"],
    )

    answer = BenchmarkCaseAnswer(
        case_id="CASE_TEST_001",
        case_details=details,
        risk_level="HIGH",
        risk_score=0.88,
        confidence=0.92,
        evidence_completeness=0.90,
        missing_evidence=[],
        matched_patterns=["TYP_MULE"],
        final_status="COMPLETED",
        stop_reason="SUFFICIENT_EVIDENCE_FOR_ACTION",
        graph_persisted=True,
        vector_indexed=False,
    )

    # Validate aliases
    assert answer.case["case_id"] == "CASE_TEST_001"
    assert answer.status == "COMPLETED"
    assert "pre_evidence_next_best_action" in answer.decisions

    # Test export dictionary
    export_dict = answer.to_export_dict()
    assert export_dict["case_id"] == "CASE_TEST_001"
    assert export_dict["case"]["trigger_type"] == "HIGH_AMOUNT_ANOMALY"
    assert export_dict["findings"] == {}
    assert export_dict["status"] == "COMPLETED"

    # Test JSON dump
    out_file = tmp_path / "test_answer.json"
    with open(out_file, "w") as f:
        json.dump(export_dict, f)

    assert out_file.exists()
    with open(out_file, "r") as f:
        loaded = json.load(f)
    assert loaded["case_id"] == "CASE_TEST_001"


@pytest.mark.asyncio
async def test_benchmark_case_execution_and_quarantine(tmp_path):
    """Verify single benchmark case execution through workflow with quarantine."""
    runner = BenchmarkRunnerService(output_dir=tmp_path)
    triggers = runner.load_benchmark_triggers()
    first_trigger = triggers[0]  # CASE_001

    custom_workflow = InvestigationWorkflowBuilder(
        main_reasoning=MockBenchmarkReasoningNode(),
    ).compile()

    answer, metric = await runner.execute_case(
        trigger_def=first_trigger,
        simulate_approvals=True,
        workflow=custom_workflow,
    )

    assert answer.case_id == "CASE_001"
    assert metric.status == "COMPLETED"
    assert metric.stop_reason == "SUFFICIENT_EVIDENCE_FOR_ACTION"
    assert metric.risk_level == "HIGH"
    assert metric.action_type == "BLOCK_TRANSACTION"
    assert metric.is_persisted is True
    # Benchmark case must be quarantined from vector index
    assert metric.is_indexed is False

    # Save answer to disk and check file
    saved_path = runner.save_case_answer(answer)
    assert saved_path.exists()
    with open(saved_path, "r") as f:
        saved_data = json.load(f)
    assert saved_data["case_id"] == "CASE_001"
    assert saved_data["graph_persisted"] is True


@pytest.mark.asyncio
async def test_benchmark_batch_run_with_summary(tmp_path):
    """Verify batch runner execution with limit=2 producing summary report."""
    runner = BenchmarkRunnerService(output_dir=tmp_path)

    custom_workflow = InvestigationWorkflowBuilder(
        main_reasoning=MockBenchmarkReasoningNode(),
    ).compile()

    summary = await runner.run_batch(
        limit=2,
        dry_run=False,
        simulate_approvals=True,
    )

    assert summary.total_cases == 2
    assert summary.completed_cases == 2
    assert summary.failed_cases == 0
    assert summary.quarantine_verified is True
    assert len(summary.cases) == 2

    # Check that individual answer files exist
    assert (tmp_path / "CASE_001.json").exists()
    assert (tmp_path / "CASE_002.json").exists()

    # Check that benchmark_run_summary.json exists
    summary_file = tmp_path / "benchmark_run_summary.json"
    assert summary_file.exists()
    with open(summary_file, "r") as f:
        summary_data = json.load(f)
    assert summary_data["total_cases"] == 2
    assert summary_data["completed_cases"] == 2


def test_cli_runner_execution():
    """Verify that scripts/run_benchmark.py CLI runs with --limit 1 --dry-run."""
    cmd = [
        sys.executable,
        "scripts/run_benchmark.py",
        "--limit",
        "1",
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "TIGERGRAPH FRAUD INVESTIGATION BENCHMARK RUNNER" in res.stdout
    assert "BENCHMARK EXECUTION SUMMARY" in res.stdout
    assert "CASE_001" in res.stdout
    assert "COMPLETED" in res.stdout
