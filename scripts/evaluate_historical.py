#!/usr/bin/env python3
"""Historical Case Evaluation CLI (Layer 39).

Measures investigation quality, fraud/cleared performance, typology detection,
action agreement, evidence request rates, and latency profiles across the 4 ablation modes:
    A: Bank risk score only
    B: Bank score + transaction behavior
    C: Graph features + transaction behavior
    D: Full system (Graph + behavior + case memory + policy GraphRAG)

Usage:
    # Run full evaluation across all 4 ablation modes on all 30 historical cases:
    python scripts/evaluate_historical.py --ablation ALL

    # Run specific ablation mode (e.g. Mode D - Full System):
    python scripts/evaluate_historical.py --ablation D

    # Run quick evaluation on first 5 cases:
    python scripts/evaluate_historical.py --limit 5

    # Export report to specific path:
    python scripts/evaluate_historical.py --output outputs/evaluation/custom_report.json
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.evaluation import AblationMode, HistoricalEvaluationReport
from backend.app.services.evaluator import HistoricalEvaluator
from backend.app.utils.logging import get_logger, setup_logging

logger = get_logger("scripts.evaluate_historical")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the historical evaluator."""
    parser = argparse.ArgumentParser(
        description="TigerGraph Fraud Investigation Historical Evaluator (Layer 39)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--ablation",
        type=str,
        default="ALL",
        choices=["A", "B", "C", "D", "ALL"],
        help="Ablation mode to evaluate (A, B, C, D, or ALL)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of historical cases to evaluate per mode",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/processed",
        help="Path to preprocessed parquet directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom file path for the output JSON evaluation report",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def print_comparative_table(report: HistoricalEvaluationReport) -> None:
    """Print an aligned console table comparing all evaluated ablation modes."""
    print("\n" + "=" * 105)
    print("                TIGERGRAPH HISTORICAL CASE EVALUATION REPORT (LAYER 39)               ")
    print("=" * 105)
    print(f"Evaluation ID:         {report.evaluation_id}")
    print(f"Dataset File:          {report.dataset_file}")
    print(f"Evaluated At:          {report.evaluated_at}")
    print(f"Total Available Cases: {report.total_cases_available} historical cases")
    if report.limit_applied:
        print(f"Limit Applied:         First {report.limit_applied} cases")
    print("-" * 105)
    print(
        f"{'Mode':<5} | {'Ablation Description':<24} | {'Cases':<5} | "
        f"{'Prec':<6} | {'Recall':<6} | {'F1':<6} | {'Acc':<6} | "
        f"{'Typology':<8} | {'Agree':<6} | {'EvidReq':<7} | {'Latency':<7}"
    )
    print("-" * 105)

    for row in report.comparative_summary:
        typ_rate = row["typology_match_rate"]
        typ_str = f"{typ_rate:.1%}" if typ_rate > 0 else "N/A"
        print(
            f"{row['mode']:<5} | "
            f"{row['mode_name'][:24]:<24} | "
            f"{row['cases_evaluated']:<5} | "
            f"{row['precision']:.3f}  | "
            f"{row['recall']:.3f}  | "
            f"{row['f1_score']:.3f}  | "
            f"{row['accuracy']:.3f}  | "
            f"{typ_str:<8} | "
            f"{row['action_agreement_rate']:.1%}  | "
            f"{row['evidence_request_rate']:.1%}   | "
            f"{row['avg_total_latency_ms']:.1f}ms"
        )

    print("=" * 105)


def print_detailed_breakdowns(report: HistoricalEvaluationReport) -> None:
    """Print breakdown of typology accuracy and confusion matrix for Mode D and C."""
    for mode_key in ["C", "D"]:
        if mode_key in report.ablations:
            res = report.ablations[mode_key]
            print(f"\n--- {res.mode_name} (Mode {res.mode.value}) Typology Pattern Breakdown ---")
            print(f"Overall Typology Match Rate: {res.typology.match_rate:.1%} ({res.typology.matched_count}/{res.typology.total_labeled})")
            if res.typology.per_typology:
                print(f"{'Typology Code':<20} | {'Cases':<6} | {'Matched':<7} | {'Accuracy':<8}")
                print("-" * 50)
                for typ, s in res.typology.per_typology.items():
                    print(f"{typ:<20} | {s['total']:<6} | {s['matched']:<7} | {s['accuracy']:.1%}")

            print(f"\nClassification Confusion Matrix (Mode {mode_key}):")
            cm = res.classification
            print(f"  True Positives (TP):  {cm.true_positives}")
            print(f"  False Positives (FP): {cm.false_positives}")
            print(f"  True Negatives (TN):  {cm.true_negatives}")
            print(f"  False Negatives (FN): {cm.false_negatives}")
            print(f"  Precision: {cm.precision:.3f} | Recall: {cm.recall:.3f} | F1: {cm.f1_score:.3f}")


def main() -> int:
    """CLI execution entry point."""
    args = parse_args()
    setup_logging(level="DEBUG" if args.verbose else "INFO")

    evaluator = HistoricalEvaluator(data_dir=Path(args.data_dir))

    if args.ablation.upper() == "ALL":
        modes = [AblationMode.A, AblationMode.B, AblationMode.C, AblationMode.D]
    else:
        modes = [AblationMode(args.ablation.upper())]

    print(f"Starting Historical Case Evaluation across modes: {[m.value for m in modes]}...")
    report = evaluator.evaluate_all(limit=args.limit, modes=modes)

    print_comparative_table(report)
    if "D" in report.ablations or "C" in report.ablations:
        print_detailed_breakdowns(report)

    output_path = Path(args.output) if args.output else None
    saved_path = evaluator.export_report_to_disk(report, output_file=output_path)
    print(f"\nEvaluation report successfully exported to: {saved_path}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
