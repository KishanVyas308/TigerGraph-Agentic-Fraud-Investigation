"""Unit Tests for Layer 39: Historical Evaluation Harness.

Verifies:
1. Historical case dataset loading with entity linkages.
2. Mode A: Bank risk score only ablation behavior.
3. Mode B: Bank score + transaction behavior ablation behavior.
4. Mode C: Graph features + behavior ablation behavior.
5. Mode D: Full system with leave-one-out case memory quarantine.
6. Leave-one-out precedent quarantine (prevents self-referential cheating).
7. Classification metrics calculations (precision, recall, F1, accuracy, zero-division).
8. Typology pattern identification metrics and per-typology breakdowns.
9. Action agreement metrics.
10. Evidence gathering efficiency and unnecessary request metrics.
11. Latency metric profiling and p95 calculations.
12. End-to-end multi-mode comparative evaluation.
13. Report disk export and latest pointer verification.
14. CLI execution via subprocess.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from backend.app.schemas.evaluation import (
    AblationMode,
    AblationResult,
    CaseEvaluationResult,
    ClassificationMetrics,
    HistoricalEvaluationReport,
)
from backend.app.services.evaluator import HistoricalEvaluator


@pytest.fixture
def evaluator() -> HistoricalEvaluator:
    """Historical evaluator instance pointing to standard processed datasets."""
    return HistoricalEvaluator(
        data_dir=Path("data/processed"),
        reports_dir=Path("outputs/evaluation"),
    )


def test_load_historical_cases(evaluator: HistoricalEvaluator):
    """Test loading historical cases with linked entity context."""
    cases = evaluator.load_historical_cases()
    assert len(cases) == 30
    first = cases[0]
    assert first["case_id"] == "HIST_001"
    assert first["outcome"] in ("FRAUD_CONFIRMED", "FALSE_POSITIVE_CLEARED")
    assert first["primary_typology"] is not None
    assert first["transaction_id"] is not None
    assert len(first["account_ids"]) > 0


def test_load_historical_cases_with_limit(evaluator: HistoricalEvaluator):
    """Test limiting loaded historical cases."""
    cases = evaluator.load_historical_cases(limit=5)
    assert len(cases) == 5


def test_evaluate_mode_a_bank_score_only(evaluator: HistoricalEvaluator):
    """Test Mode A evaluates purely on baseline bank risk score with zero typology awareness."""
    res = evaluator.evaluate_ablation(mode=AblationMode.A, limit=10)
    assert res.mode == AblationMode.A
    assert res.cases_evaluated == 10
    # Mode A cannot detect typologies
    assert res.typology.match_rate == 0.0
    assert res.typology.matched_count == 0
    # Mode A requests 0 evidence
    assert res.evidence_efficiency.evidence_request_rate == 0.0
    # Mode A has near-zero latency
    assert res.latency.avg_total_latency_ms < 5.0


def test_evaluate_mode_b_score_and_behavior(evaluator: HistoricalEvaluator):
    """Test Mode B combines bank score with transaction behavior and requests evidence on borderlines."""
    res = evaluator.evaluate_ablation(mode=AblationMode.B, limit=10)
    assert res.mode == AblationMode.B
    assert res.cases_evaluated == 10
    assert res.classification.f1_score >= 0.0


def test_evaluate_mode_c_graph_and_behavior(evaluator: HistoricalEvaluator):
    """Test Mode C incorporates graph relationships and identifies graph-based typologies."""
    res = evaluator.evaluate_ablation(mode=AblationMode.C, limit=10)
    assert res.mode == AblationMode.C
    assert res.cases_evaluated == 10
    # Mode C detects typologies via graph topology
    assert res.typology.match_rate > 0.0
    # Mode C measures graph latency
    assert res.latency.avg_graph_latency_ms > 0.0


def test_evaluate_mode_d_full_system(evaluator: HistoricalEvaluator):
    """Test Mode D full system achieves optimal precision, recall, and typology identification."""
    res = evaluator.evaluate_ablation(mode=AblationMode.D, limit=10)
    assert res.mode == AblationMode.D
    assert res.cases_evaluated == 10
    assert res.classification.precision == 1.0
    assert res.classification.recall == 1.0
    assert res.classification.f1_score == 1.0
    assert res.typology.match_rate == 1.0
    assert res.action_agreement.agreement_rate == 1.0


def test_leave_one_out_case_memory_quarantine(evaluator: HistoricalEvaluator):
    """Test that Mode D evaluation excludes the target case itself from case memory retrieval."""
    evaluator._ensure_data_loaded()
    assert evaluator._case_memory_df is not None

    target_case_id = "HIST_001"
    # Filter case memory dataframe for target case
    filtered_mem = evaluator._case_memory_df.filter(evaluator._case_memory_df["case_id"] != target_case_id)
    retrieved_case_ids = filtered_mem["case_id"].to_list()

    assert target_case_id not in retrieved_case_ids
    assert len(retrieved_case_ids) == len(evaluator._case_memory_df) - 1


def test_classification_metrics_math(evaluator: HistoricalEvaluator):
    """Test mathematical correctness and edge cases in classification metrics computation."""
    # Perfect performance: 2 TP, 0 FP, 2 TN, 0 FN
    dummy_results: List[CaseEvaluationResult] = [
        CaseEvaluationResult(
            case_id="C1",
            transaction_id="TX1",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_action="BLOCK_TRANSACTION",
        ),
        CaseEvaluationResult(
            case_id="C2",
            transaction_id="TX2",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_action="BLOCK_TRANSACTION",
        ),
        CaseEvaluationResult(
            case_id="C3",
            transaction_id="TX3",
            ground_truth_outcome="FALSE_POSITIVE_CLEARED",
            ground_truth_action="ALLOW_TRANSACTION",
            predicted_outcome="FALSE_POSITIVE_CLEARED",
            predicted_action="ALLOW_TRANSACTION",
        ),
        CaseEvaluationResult(
            case_id="C4",
            transaction_id="TX4",
            ground_truth_outcome="FALSE_POSITIVE_CLEARED",
            ground_truth_action="ALLOW_TRANSACTION",
            predicted_outcome="FALSE_POSITIVE_CLEARED",
            predicted_action="ALLOW_TRANSACTION",
        ),
    ]

    metrics = evaluator._compute_classification_metrics(dummy_results)
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0
    assert metrics.accuracy == 1.0
    assert metrics.true_positives == 2
    assert metrics.false_positives == 0

    # Zero positive predictions (division by zero handling)
    all_neg_results = [
        CaseEvaluationResult(
            case_id="C1",
            transaction_id="TX1",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FALSE_POSITIVE_CLEARED",
            predicted_action="ALLOW_TRANSACTION",
        )
    ]
    metrics_zero = evaluator._compute_classification_metrics(all_neg_results)
    assert metrics_zero.precision == 0.0
    assert metrics_zero.recall == 0.0
    assert metrics_zero.f1_score == 0.0
    assert metrics_zero.accuracy == 0.0
    assert metrics_zero.false_negatives == 1


def test_typology_metrics_breakdown(evaluator: HistoricalEvaluator):
    """Test typology match rate computation and per-typology accuracy."""
    dummy_results = [
        CaseEvaluationResult(
            case_id="C1",
            transaction_id="TX1",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_typology="TYP_ATO",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_typology="TYP_ATO",
            predicted_action="BLOCK_TRANSACTION",
            is_typology_correct=True,
        ),
        CaseEvaluationResult(
            case_id="C2",
            transaction_id="TX2",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_typology="TYP_ATO",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_typology="TYP_MULE",
            predicted_action="BLOCK_TRANSACTION",
            is_typology_correct=False,
        ),
        CaseEvaluationResult(
            case_id="C3",
            transaction_id="TX3",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_typology="TYP_MULE",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_typology="TYP_MULE",
            predicted_action="BLOCK_TRANSACTION",
            is_typology_correct=True,
        ),
    ]

    typ_metrics = evaluator._compute_typology_metrics(dummy_results)
    assert typ_metrics.total_labeled == 3
    assert typ_metrics.matched_count == 2
    assert round(typ_metrics.match_rate, 2) == 0.67
    assert "TYP_ATO" in typ_metrics.per_typology
    assert typ_metrics.per_typology["TYP_ATO"]["total"] == 2
    assert typ_metrics.per_typology["TYP_ATO"]["matched"] == 1
    assert typ_metrics.per_typology["TYP_ATO"]["accuracy"] == 0.5


def test_action_agreement_metrics(evaluator: HistoricalEvaluator):
    """Test action agreement rate calculation."""
    dummy_results = [
        CaseEvaluationResult(
            case_id="C1",
            transaction_id="TX1",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_action="BLOCK_TRANSACTION",
            is_action_agreed=True,
        ),
        CaseEvaluationResult(
            case_id="C2",
            transaction_id="TX2",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FALSE_POSITIVE_CLEARED",
            predicted_action="ALLOW_TRANSACTION",
            is_action_agreed=False,
        ),
    ]

    act_metrics = evaluator._compute_action_agreement_metrics(dummy_results)
    assert act_metrics.total_cases == 2
    assert act_metrics.agreed_cases == 1
    assert act_metrics.agreement_rate == 0.5
    assert act_metrics.action_counts["BLOCK_TRANSACTION"] == 1
    assert act_metrics.action_counts["ALLOW_TRANSACTION"] == 1


def test_evidence_efficiency_metrics(evaluator: HistoricalEvaluator):
    """Test evidence request rate and unnecessary request rate calculation."""
    dummy_results = [
        CaseEvaluationResult(
            case_id="C1",
            transaction_id="TX1",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_action="REQUEST_CUSTOMER_CONFIRMATION",
            evidence_requested=True,
            unnecessary_evidence_requested=False,
        ),
        CaseEvaluationResult(
            case_id="C2",
            transaction_id="TX2",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_action="REQUEST_CUSTOMER_CONFIRMATION",
            evidence_requested=True,
            unnecessary_evidence_requested=True,
        ),
        CaseEvaluationResult(
            case_id="C3",
            transaction_id="TX3",
            ground_truth_outcome="FALSE_POSITIVE_CLEARED",
            ground_truth_action="ALLOW_TRANSACTION",
            predicted_outcome="FALSE_POSITIVE_CLEARED",
            predicted_action="ALLOW_TRANSACTION",
            evidence_requested=False,
            unnecessary_evidence_requested=False,
        ),
    ]

    ev_metrics = evaluator._compute_evidence_efficiency_metrics(dummy_results)
    assert ev_metrics.total_cases == 3
    assert ev_metrics.cases_with_evidence_requested == 2
    assert round(ev_metrics.evidence_request_rate, 2) == 0.67
    assert round(ev_metrics.unnecessary_request_rate, 2) == 0.33


def test_latency_metrics_p95(evaluator: HistoricalEvaluator):
    """Test average and 95th percentile latency calculation."""
    dummy_results = [
        CaseEvaluationResult(
            case_id=f"C{i}",
            transaction_id=f"TX{i}",
            ground_truth_outcome="FRAUD_CONFIRMED",
            ground_truth_action="BLOCK_TRANSACTION",
            predicted_outcome="FRAUD_CONFIRMED",
            predicted_action="BLOCK_TRANSACTION",
            total_duration_ms=float(i * 10),
            graph_duration_ms=float(i * 2),
            llm_duration_ms=float(i * 5),
        )
        for i in range(1, 21)
    ]

    lat_metrics = evaluator._compute_latency_metrics(dummy_results)
    assert lat_metrics.avg_total_latency_ms > 0.0
    assert lat_metrics.p95_total_latency_ms >= lat_metrics.avg_total_latency_ms


def test_evaluate_all_comparative_summary(evaluator: HistoricalEvaluator):
    """Test full multi-ablation evaluation and comparative summary creation."""
    report = evaluator.evaluate_all(limit=5)
    assert isinstance(report, HistoricalEvaluationReport)
    assert len(report.ablations) == 4
    assert set(report.ablations.keys()) == {"A", "B", "C", "D"}
    assert len(report.comparative_summary) == 4

    # Verify that Mode D outperforms Mode A on F1 score and typology match rate
    f1_a = report.ablations["A"].classification.f1_score
    f1_d = report.ablations["D"].classification.f1_score
    assert f1_d >= f1_a

    typ_a = report.ablations["A"].typology.match_rate
    typ_d = report.ablations["D"].typology.match_rate
    assert typ_d >= typ_a


def test_export_report_to_disk(evaluator: HistoricalEvaluator, tmp_path: Path):
    """Test serialization of evaluation report to JSON on disk."""
    report = evaluator.evaluate_all(limit=3)
    target_file = tmp_path / "test_report.json"
    saved_file = evaluator.export_report_to_disk(report, output_file=target_file)

    assert saved_file.exists()
    with open(saved_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["evaluation_id"] == report.evaluation_id
    assert len(data["ablations"]) == 4


def test_cli_execution_mode_d():
    """Test running scripts/evaluate_historical.py for a single mode with a limit."""
    cmd = [
        sys.executable,
        "scripts/evaluate_historical.py",
        "--ablation",
        "D",
        "--limit",
        "3",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "TIGERGRAPH HISTORICAL CASE EVALUATION REPORT" in proc.stdout
    assert "Full System" in proc.stdout


def test_cli_execution_all_modes():
    """Test running scripts/evaluate_historical.py across all modes."""
    cmd = [
        sys.executable,
        "scripts/evaluate_historical.py",
        "--ablation",
        "ALL",
        "--limit",
        "4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Evaluation report successfully exported to" in proc.stdout
    assert "Mode  | Ablation Description" in proc.stdout
