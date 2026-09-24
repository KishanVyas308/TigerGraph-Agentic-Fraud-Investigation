"""Unit Tests for Layer 40: Local Demo Scenarios.

Verifies:
1. Demo Scenario 1 (Fraud Network): Graph-detected mule ring, shared devices, autonomous block.
2. Demo Scenario 2 (Uncertain Case): Dynamic evidence loop, SMS customer confirmation, and recommendation flip.
3. Demo Scenario 2 Denial Branch: Customer denial elevates risk to Critical and updates recommendation to BLOCK_ACCOUNT.
4. Demo Scenario 3 (Human Approval): Policy gate governance, supervisor approval interrupt/resume, and SAR report generation.
5. Demo Scenario 3 Rejection Branch: Supervisor rejection transitions to safe alternate action.
6. Demo Suite execution and artifact disk persistence.
7. CLI execution via subprocess for all scenarios and individual scenarios.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.schemas.demo import (
    DemoScenarioId,
    DemoScenarioResult,
    DemoSuiteReport,
)
from backend.app.services.demo_runner import DemoRunnerService


@pytest.fixture
def demo_service(tmp_path: Path) -> DemoRunnerService:
    """Demo runner service instance writing to a temporary test directory."""
    return DemoRunnerService(export_dir=tmp_path)


@pytest.mark.asyncio
async def test_demo_1_fraud_network(demo_service: DemoRunnerService):
    """Test Demo 1: Graph-detected mule ring and autonomous block execution."""
    res = await demo_service.run_demo_1_fraud_network()
    assert isinstance(res, DemoScenarioResult)
    assert res.scenario_id == DemoScenarioId.FRAUD_NETWORK
    assert res.case_id == "CASE_DEMO_01"
    assert res.final_risk == "CRITICAL"
    assert res.pre_evidence_action == "BLOCK_TRANSACTION"
    assert res.post_evidence_action == "BLOCK_TRANSACTION"
    assert res.action_executed == "BLOCK_TRANSACTION"
    assert res.approval_required is False
    assert res.sar_generated is False
    assert res.is_persisted is True
    assert res.stop_reason == "SUFFICIENT_EVIDENCE_FOR_ACTION"
    assert res.success is True
    assert len(res.steps) >= 4


@pytest.mark.asyncio
async def test_demo_2_uncertain_case_confirmed(demo_service: DemoRunnerService):
    """Test Demo 2: Borderline novelty with customer confirmation dropping risk and allowing transaction."""
    res = await demo_service.run_demo_2_uncertain_evidence_loop(customer_confirmed=True)
    assert isinstance(res, DemoScenarioResult)
    assert res.scenario_id == DemoScenarioId.UNCERTAIN_CASE
    assert res.case_id == "CASE_DEMO_02"
    assert res.initial_risk == "MEDIUM"
    assert res.final_risk == "LOW"
    # Verify pre-evidence NBA is preserved and distinct from post-evidence NBA
    assert res.pre_evidence_action == "MONITOR_TRANSACTION"
    assert res.post_evidence_action == "ALLOW_TRANSACTION"
    assert res.action_executed == "ALLOW_TRANSACTION"
    assert res.approval_required is False
    assert res.is_persisted is True
    assert res.stop_reason == "SUFFICIENT_EVIDENCE_FOR_ACTION"
    assert res.success is True


@pytest.mark.asyncio
async def test_demo_2_uncertain_case_denied(demo_service: DemoRunnerService):
    """Test Demo 2: Customer denial elevates risk to Critical and recommends BLOCK_ACCOUNT."""
    res = await demo_service.run_demo_2_uncertain_evidence_loop(customer_confirmed=False)
    assert res.scenario_id == DemoScenarioId.UNCERTAIN_CASE
    assert res.initial_risk == "MEDIUM"
    assert res.final_risk == "CRITICAL"
    assert res.pre_evidence_action == "MONITOR_TRANSACTION"
    assert res.post_evidence_action == "BLOCK_ACCOUNT"
    assert res.action_executed == "BLOCK_ACCOUNT"


@pytest.mark.asyncio
async def test_demo_3_human_approval_approved(demo_service: DemoRunnerService):
    """Test Demo 3: Sensitive account block requires approval; analyst approval executes block and files SAR."""
    res = await demo_service.run_demo_3_human_approval(approve=True)
    assert isinstance(res, DemoScenarioResult)
    assert res.scenario_id == DemoScenarioId.HUMAN_APPROVAL
    assert res.case_id == "CASE_DEMO_03"
    assert res.final_risk == "CRITICAL"
    assert res.pre_evidence_action == "BLOCK_ACCOUNT"
    assert res.approval_required is True
    assert res.approval_status == "APPROVED"
    assert res.post_evidence_action == "BLOCK_ACCOUNT"
    assert res.action_executed == "BLOCK_ACCOUNT"
    assert res.sar_generated is True
    assert res.is_persisted is True
    assert res.stop_reason == "SUFFICIENT_EVIDENCE_FOR_ACTION"
    assert res.success is True


@pytest.mark.asyncio
async def test_demo_3_human_approval_rejected(demo_service: DemoRunnerService):
    """Test Demo 3: Analyst rejection prevents account block and falls back to safe action without SAR."""
    res = await demo_service.run_demo_3_human_approval(approve=False)
    assert res.approval_required is True
    assert res.approval_status == "REJECTED"
    assert res.post_evidence_action == "ALLOW_TRANSACTION"
    assert res.action_executed == "ALLOW_TRANSACTION"
    assert res.sar_generated is False


@pytest.mark.asyncio
async def test_demo_suite_execution_and_persistence(demo_service: DemoRunnerService, tmp_path: Path):
    """Test full demo suite batch execution and artifact serialization."""
    report = await demo_service.run_all_demos()
    assert isinstance(report, DemoSuiteReport)
    assert report.total_scenarios == 3
    assert report.passed_scenarios == 3
    assert report.all_passed is True

    # Verify JSON files on disk
    summary_file = tmp_path / "demo_suite_report.json"
    assert summary_file.exists()
    with open(summary_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_scenarios"] == 3
    assert data["all_passed"] is True

    # Verify individual scenario files exist
    assert (tmp_path / "DEMO_1_CASE_DEMO_01.json").exists()
    assert (tmp_path / "DEMO_2_CASE_DEMO_02.json").exists()
    assert (tmp_path / "DEMO_3_CASE_DEMO_03.json").exists()


def test_scenario_metadata():
    """Test that all three scenarios have complete presentation metadata."""
    metas = DemoRunnerService.get_scenarios_metadata()
    assert len(metas) == 3
    ids = {m.scenario_id for m in metas}
    assert ids == {DemoScenarioId.FRAUD_NETWORK, DemoScenarioId.UNCERTAIN_CASE, DemoScenarioId.HUMAN_APPROVAL}
    for m in metas:
        assert m.name
        assert m.typology
        assert m.summary
        assert len(m.key_highlights) >= 4


def test_cli_execution_scenario_1():
    """Test CLI execution for Scenario 1."""
    cmd = [
        sys.executable,
        "scripts/run_demo.py",
        "--scenario",
        "1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "DEMO 1: GRAPH-DETECTED MULE RING" in proc.stdout
    assert "CASE_DEMO_01" in proc.stdout


def test_cli_execution_all_step_by_step():
    """Test CLI execution across all scenarios with step-by-step formatting."""
    cmd = [
        sys.executable,
        "scripts/run_demo.py",
        "--scenario",
        "ALL",
        "--step-by-step",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "DEMO 1" in proc.stdout
    assert "DEMO 2" in proc.stdout
    assert "DEMO 3" in proc.stdout
    assert "All 3 scenario(s) executed successfully." in proc.stdout
