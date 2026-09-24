"""Unit Tests for Layer 38: Benchmark Output Validator.

Verifies:
1. All 20 generated benchmark answers pass validation.
2. Benchmark run summary passes validation.
3. Detection of missing required top-level fields (case, evidence, findings, actions, stop_reason).
4. Detection of missing case ID, trigger type, and entity anchors.
5. Detection of broken evidence IDs in hypotheses, actions, and decisions.
6. Detection of duplicate evidence IDs.
7. Detection of invalid evidence provenance (blank or UNKNOWN source).
8. Detection of pre-evidence NBA preservation violations.
9. Enforcement of SIMULATED execution mode for benchmark actions.
10. Enforcement of governance approval role when approval is required.
11. Enforcement of grounded SAR narrative when FILE_SAR is recommended/executed.
12. Detection of invalid stop reasons.
13. Detection of TigerGraph graph persistence failures.
14. Handling of missing and corrupted files.
15. Strict mode behavior on warnings.
16. Directory validation and report aggregation.
17. CLI execution via subprocess.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from backend.app.schemas.benchmark import (
    BenchmarkValidationReport,
    BenchmarkValidationResult,
    ValidationCategory,
    ValidationSeverity,
)
from backend.app.services.benchmark_validator import BenchmarkValidator


@pytest.fixture
def validator() -> BenchmarkValidator:
    """Validator instance with default settings."""
    return BenchmarkValidator(strict=False)


@pytest.fixture
def strict_validator() -> BenchmarkValidator:
    """Validator instance in strict mode."""
    return BenchmarkValidator(strict=True)


@pytest.fixture
def minimal_valid_case_dict() -> Dict[str, Any]:
    """A minimal, compliant benchmark answer dictionary."""
    return {
        "case_id": "CASE_999",
        "case_details": {
            "case_id": "CASE_999",
            "trigger_type": "TRANSACTION_ALERT",
            "trigger_entity_id": "TX_999",
            "trigger_entity_type": "TRANSACTION",
            "transaction_id": "TX_999",
            "customer_id": "CUST_999",
            "account_ids": ["ACC_999"],
            "opened_at": "2026-09-24T05:00:00+00:00",
            "closed_at": "2026-09-24T05:01:00+00:00",
        },
        "internal_investigation_record": [
            {
                "event_id": "EVT_001",
                "event_type": "TRIGGER_VALIDATED",
                "node_name": "ValidateTriggerNode",
                "timestamp": "2026-09-24T05:00:00+00:00",
            }
        ],
        "evidence": [
            {
                "evidence_id": "EVD_001",
                "source": "TIGERGRAPH_GSQL",
                "category": "TRANSACTION_BEHAVIOR",
                "fact": "Velocity count is 8 transactions in 10 minutes",
                "reliability": 0.95,
                "timestamp": "2026-09-24T05:00:05+00:00",
            },
            {
                "evidence_id": "EVD_002",
                "source": "POLICY_GRAPHRAG",
                "category": "POLICY",
                "fact": "Rule POL_001 mandates immediate block on velocity > 5",
                "reliability": 1.0,
                "timestamp": "2026-09-24T05:00:06+00:00",
            },
        ],
        "graph_findings": {
            "transaction_count_10m": 8,
            "shared_device_account_count": 0,
        },
        "fraud_hypotheses": [
            {
                "hypothesis": "Rapid automated cashout attack",
                "supporting_evidence_ids": ["EVD_001", "EVD_002"],
                "contradictory_evidence_ids": [],
            }
        ],
        "matched_patterns": ["TYP_RAPID_VELOCITY"],
        "policy_context": [{"policy_id": "POL_001", "name": "Velocity Cap"}],
        "similar_historical_cases": [],
        "risk_level": "HIGH",
        "risk_score": 0.88,
        "confidence": 0.92,
        "evidence_completeness": 0.85,
        "missing_evidence": [],
        "pre_evidence_next_best_action": {
            "action_type": "BLOCK_TRANSACTION",
            "execution_mode": "SIMULATED",
            "evidence_ids": ["EVD_001"],
        },
        "requested_evidence": [],
        "received_evidence": [],
        "post_evidence_next_best_action": {
            "action_type": "BLOCK_TRANSACTION",
            "execution_mode": "SIMULATED",
            "evidence_ids": ["EVD_001", "EVD_002"],
        },
        "approval_route": {
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
        },
        "actions": [
            {
                "action_type": "BLOCK_TRANSACTION",
                "execution_mode": "SIMULATED",
                "success": True,
                "evidence_ids": ["EVD_001"],
            }
        ],
        "sar_report": None,
        "final_status": "COMPLETED",
        "stop_reason": "SUFFICIENT_EVIDENCE_FOR_ACTION",
        "graph_persisted": True,
        "vector_indexed": False,
    }


def test_validate_minimal_valid_dict(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test that a compliant dictionary passes validation with zero errors."""
    res = validator.validate_dict(minimal_valid_case_dict)
    assert res.is_valid is True
    assert res.error_count == 0
    assert res.warning_count == 0
    assert len(res.issues) == 0


def test_validate_all_20_generated_benchmark_cases(validator: BenchmarkValidator):
    """Test that all 20 actual benchmark answer files in outputs/benchmark/ pass validation."""
    benchmark_dir = Path("outputs/benchmark")
    if not benchmark_dir.exists():
        pytest.skip("outputs/benchmark directory does not exist yet")

    report = validator.validate_directory(benchmark_dir, require_all_20=True)
    assert report.total_files == 20
    assert report.invalid_files == 0
    assert report.total_errors == 0
    assert report.is_all_valid is True


def test_validate_run_summary(validator: BenchmarkValidator):
    """Test that benchmark_run_summary.json passes validation."""
    summary_path = Path("outputs/benchmark/benchmark_run_summary.json")
    if not summary_path.exists():
        pytest.skip("benchmark_run_summary.json does not exist yet")

    res = validator.validate_run_summary(summary_path)
    assert res.is_valid is True
    assert res.error_count == 0


def test_missing_required_top_level_fields(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of missing required top-level fields."""
    for field in ["internal_investigation_record", "evidence", "actions", "stop_reason"]:
        corrupted = dict(minimal_valid_case_dict)
        del corrupted[field]
        res = validator.validate_dict(corrupted)
        assert res.is_valid is False
        assert any(i.code == "MISSING_FIELD" and i.field_path == field for i in res.issues)

    # Test missing case / case_details
    corrupted_case = dict(minimal_valid_case_dict)
    del corrupted_case["case_details"]
    res_case = validator.validate_dict(corrupted_case)
    assert res_case.is_valid is False
    assert any(i.code == "MISSING_FIELD" and i.field_path == "case" for i in res_case.issues)


def test_missing_case_id_and_trigger_type(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of missing case ID and trigger type."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["case_details"] = dict(corrupted["case_details"])
    corrupted["case_id"] = ""
    corrupted["case_details"]["case_id"] = ""
    corrupted["case_details"]["trigger_type"] = ""

    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "MISSING_CASE_ID" for i in res.issues)
    assert any(i.code == "MISSING_TRIGGER_TYPE" for i in res.issues)


def test_missing_entity_anchors(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of cases lacking any anchor entity."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["case_details"] = {
        "case_id": "CASE_NO_ANCHORS",
        "trigger_type": "GENERIC_ALERT",
        "trigger_entity_id": None,
        "transaction_id": None,
        "customer_id": None,
        "account_ids": [],
    }
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "MISSING_ENTITY_ANCHOR" for i in res.issues)


def test_broken_evidence_id_in_hypotheses(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of broken evidence ID cited in fraud hypotheses."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["fraud_hypotheses"] = [
        {
            "hypothesis": "Compromised account",
            "supporting_evidence_ids": ["EVD_001", "EVD_NON_EXISTENT_999"],
            "contradictory_evidence_ids": [],
        }
    ]
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    broken_issues = [i for i in res.issues if i.code == "BROKEN_EVIDENCE_ID"]
    assert len(broken_issues) >= 1
    assert "EVD_NON_EXISTENT_999" in broken_issues[0].message


def test_broken_evidence_id_in_actions(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of broken evidence ID cited in actions."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["actions"] = [
        {
            "action_type": "BLOCK_TRANSACTION",
            "execution_mode": "SIMULATED",
            "evidence_ids": ["EVD_GHOST_ACTION"],
        }
    ]
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "BROKEN_EVIDENCE_ID" and "EVD_GHOST_ACTION" in i.message for i in res.issues)


def test_duplicate_evidence_ids(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of duplicate evidence IDs within the evidence bundle."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["evidence"] = [
        {
            "evidence_id": "EVD_DUPE",
            "source": "TIGERGRAPH_GSQL",
            "category": "TRANSACTION_BEHAVIOR",
            "fact": "Fact 1",
            "reliability": 0.9,
        },
        {
            "evidence_id": "EVD_DUPE",
            "source": "TIGERGRAPH_GSQL",
            "category": "TRANSACTION_BEHAVIOR",
            "fact": "Fact 2 duplicate ID",
            "reliability": 0.8,
        },
    ]
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "DUPLICATE_EVIDENCE_ID" for i in res.issues)


def test_unknown_evidence_provenance(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of UNKNOWN or blank evidence source provenance."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["evidence"] = [
        {
            "evidence_id": "EVD_UNKNOWN_SRC",
            "source": "UNKNOWN",
            "category": "EXTERNAL_SIGNAL",
            "fact": "Some fact from nowhere",
            "reliability": 0.5,
        }
    ]
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "INVALID_EVIDENCE_PROVENANCE" for i in res.issues)


def test_pre_evidence_nba_preservation_violation(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test that pre-evidence NBA must be preserved when requested evidence is non-empty."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["requested_evidence"] = [{"evidence_type": "CUSTOMER_CONFIRMATION"}]
    corrupted["pre_evidence_next_best_action"] = None
    corrupted["decisions"] = {"pre_evidence_next_best_action": None}

    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "PRE_EVIDENCE_NBA_MISSING" for i in res.issues)


def test_non_simulated_execution_mode(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test rejection of non-simulated execution mode in actions for benchmark runs."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["actions"] = [
        {
            "action_type": "BLOCK_TRANSACTION",
            "execution_mode": "LIVE",  # Forbidden in benchmark/local development
            "success": True,
        }
    ]
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "INVALID_EXECUTION_MODE" for i in res.issues)


def test_missing_approval_role_when_required(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test detection of missing approval role when governance requires approval."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["approval_route"] = {
        "approval_required": True,
        "approval_role": None,  # Missing required role
    }
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "APPROVAL_ROLE_MISSING" for i in res.issues)


def test_sar_required_output_missing(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test error when FILE_SAR action is executed or recommended without a SAR report."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["actions"] = [
        {
            "action_type": "FILE_SAR",
            "execution_mode": "SIMULATED",
            "success": True,
        }
    ]
    corrupted["sar_report"] = None
    corrupted["sar"] = None

    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "SAR_REQUIRED_OUTPUT_MISSING" for i in res.issues)


def test_valid_sar_report_passes(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test that a complete grounded SAR report passes validation."""
    case_with_sar = dict(minimal_valid_case_dict)
    case_with_sar["actions"] = [
        {
            "action_type": "FILE_SAR",
            "execution_mode": "SIMULATED",
            "success": True,
        }
    ]
    case_with_sar["sar_report"] = {
        "sar_id": "SAR_2026_001",
        "subject_id": "CUST_999",
        "typology": "TYP_MULE_RAPID_MOVEMENT",
        "narrative": "Detailed grounded narrative describing structuring across multiple accounts exceeding limits.",
        "created_at": "2026-09-24T05:00:50+00:00",
    }
    res = validator.validate_dict(case_with_sar)
    assert res.is_valid is True
    assert res.error_count == 0


def test_invalid_stop_reason(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test rejection of non-authoritative stop reasons."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["stop_reason"] = "UNKNOWN_REASON_JUST_STOPPED"
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "INVALID_STOP_REASON" for i in res.issues)


def test_graph_persistence_failed(validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test rejection when TigerGraph graph persistence verification is False."""
    corrupted = dict(minimal_valid_case_dict)
    corrupted["graph_persisted"] = False
    res = validator.validate_dict(corrupted)
    assert res.is_valid is False
    assert any(i.code == "GRAPH_PERSISTENCE_FAILED" for i in res.issues)


def test_file_not_found(validator: BenchmarkValidator):
    """Test validation of a non-existent file."""
    res = validator.validate_file("outputs/benchmark/DOES_NOT_EXIST.json")
    assert res.is_valid is False
    assert any(i.code == "FILE_NOT_FOUND" for i in res.issues)


def test_corrupted_json_file(validator: BenchmarkValidator, tmp_path: Path):
    """Test validation of a corrupted, non-JSON file."""
    corrupt_file = tmp_path / "corrupted.json"
    corrupt_file.write_text("{ this is not valid json ...")
    res = validator.validate_file(corrupt_file)
    assert res.is_valid is False
    assert any(i.code == "INVALID_JSON" for i in res.issues)


def test_strict_mode_on_warnings(validator: BenchmarkValidator, strict_validator: BenchmarkValidator, minimal_valid_case_dict: Dict[str, Any]):
    """Test that warnings (like empty evidence) are allowed in normal mode but fail in strict mode."""
    warn_case = dict(minimal_valid_case_dict)
    warn_case["evidence"] = []  # Triggers EMPTY_EVIDENCE_BUNDLE warning
    warn_case["fraud_hypotheses"] = []
    warn_case["actions"] = [
        {
            "action_type": "BLOCK_TRANSACTION",
            "execution_mode": "SIMULATED",
            "evidence_ids": [],
        }
    ]
    warn_case["pre_evidence_next_best_action"] = {
        "action_type": "BLOCK_TRANSACTION",
        "execution_mode": "SIMULATED",
        "evidence_ids": [],
    }
    warn_case["post_evidence_next_best_action"] = {
        "action_type": "BLOCK_TRANSACTION",
        "execution_mode": "SIMULATED",
        "evidence_ids": [],
    }

    # Normal mode -> Passes with warning
    res_normal = validator.validate_dict(warn_case)
    assert res_normal.warning_count >= 1
    assert res_normal.error_count == 0
    assert res_normal.is_valid is True

    # Strict mode -> Fails because of warning
    res_strict = strict_validator.validate_dict(warn_case)
    assert res_strict.is_valid is False
    assert res_strict.warning_count >= 1


def test_cli_execution_all():
    """Test CLI execution using scripts/validate_benchmark.py --all."""
    cmd = [
        sys.executable,
        "scripts/validate_benchmark.py",
        "--all",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "TIGERGRAPH BENCHMARK OUTPUT VALIDATION REPORT" in proc.stdout
    assert "All Valid:       PASSED" in proc.stdout
    assert "CASE_001" in proc.stdout
    assert "CASE_020" in proc.stdout


def test_cli_execution_single_file():
    """Test CLI execution using scripts/validate_benchmark.py --file."""
    cmd = [
        sys.executable,
        "scripts/validate_benchmark.py",
        "--file",
        "outputs/benchmark/CASE_001.json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "CASE_001" in proc.stdout
    assert "PASS" in proc.stdout
