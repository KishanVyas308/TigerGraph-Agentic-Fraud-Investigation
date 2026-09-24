#!/usr/bin/env python3
"""Benchmark Output Validator CLI (Layer 38).

Validates generated benchmark answer files in outputs/benchmark/ against the authoritative
submission format specifications without mutating files or auto-correcting semantic decisions.

Usage:
    # Validate all 20 benchmark cases and run summary in default directory:
    python scripts/validate_benchmark.py --all

    # Validate a single case file:
    python scripts/validate_benchmark.py --file outputs/benchmark/CASE_001.json

    # Validate with strict checking (failing on warnings):
    python scripts/validate_benchmark.py --all --strict

    # Validate custom directory:
    python scripts/validate_benchmark.py --dir custom/outputs/ --all
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.benchmark import (
    BenchmarkValidationReport,
    BenchmarkValidationResult,
    ValidationSeverity,
)
from backend.app.services.benchmark_validator import BenchmarkValidator
from backend.app.utils.logging import get_logger, setup_logging

logger = get_logger("scripts.validate_benchmark")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the benchmark validator."""
    parser = argparse.ArgumentParser(
        description="TigerGraph Fraud Investigation Benchmark Output Validator (Layer 38)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Validate all 20 benchmark case answer files (CASE_001.json - CASE_020.json) and run summary",
    )
    group.add_argument(
        "--file",
        type=str,
        help="Path to a single benchmark answer JSON file to validate",
    )

    parser.add_argument(
        "--dir",
        type=str,
        default="outputs/benchmark",
        help="Directory containing benchmark answer files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: treat any warning as an authoritative validation failure",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Optional path to export full validation report as JSON",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def print_result_table(report: BenchmarkValidationReport) -> None:
    """Print an aligned console table summarizing file-level validation results."""
    print("=" * 80)
    print("                TIGERGRAPH BENCHMARK OUTPUT VALIDATION REPORT               ")
    print("=" * 80)
    print(f"Total Evaluated: {report.total_files} case file(s)")
    print(f"Valid Files:     {report.valid_files}")
    print(f"Invalid Files:   {report.invalid_files}")
    print(f"Total Errors:    {report.total_errors}")
    print(f"Total Warnings:  {report.total_warnings}")
    print(f"All Valid:       {'PASSED' if report.is_all_valid else 'FAILED'}")
    print("-" * 80)
    print(f"{'Target / Case':<22} | {'Status':<8} | {'Errors':<7} | {'Warnings':<9} | {'Top Diagnostic':<26}")
    print("-" * 80)

    for r in report.results:
        top_diag = "None"
        if r.issues:
            first_err = next((i for i in r.issues if i.severity == ValidationSeverity.ERROR), r.issues[0])
            top_diag = f"[{first_err.code}] {first_err.message}"[:26]

        status_str = "PASS" if r.is_valid else "FAIL"
        display_name = r.case_id or Path(r.file_path).name
        print(f"{display_name:<22} | {status_str:<8} | {r.error_count:<7} | {r.warning_count:<9} | {top_diag:<26}")

    if report.summary_validation:
        s_res = report.summary_validation
        s_status = "PASS" if s_res.is_valid else "FAIL"
        top_diag = "None"
        if s_res.issues:
            top_diag = f"[{s_res.issues[0].code}] {s_res.issues[0].message}"[:26]
        print(f"{'Run Summary':<22} | {s_status:<8} | {s_res.error_count:<7} | {s_res.warning_count:<9} | {top_diag:<26}")

    print("=" * 80)


def print_detailed_issues(results: list[BenchmarkValidationResult]) -> None:
    """Print detailed issue breakdowns for failing or warned files."""
    has_issues = any(r.issues for r in results)
    if not has_issues:
        print("\nAll verified files comply strictly with AGENTS.md §34 and dataset specifications.\n")
        return

    print("\nDetailed Diagnostic Breakdown:")
    print("-" * 80)
    for r in results:
        if not r.issues:
            continue
        print(f"\nFile: {r.file_path} (Case: {r.case_id or 'Unknown'})")
        for i in r.issues:
            prefix = "[ERROR]" if i.severity == ValidationSeverity.ERROR else "[WARN] "
            path_str = f" at '{i.field_path}'" if i.field_path else ""
            print(f"  {prefix} [{i.code}]{path_str}: {i.message}")
    print("-" * 80 + "\n")


def main() -> int:
    """Main CLI execution flow."""
    args = parse_args()
    setup_logging(level="DEBUG" if args.verbose else "INFO")

    validator = BenchmarkValidator(strict=args.strict)

    if args.file:
        file_path = Path(args.file)
        result = validator.validate_file(file_path, strict=args.strict)
        report = BenchmarkValidationReport(
            total_files=1,
            valid_files=1 if result.is_valid else 0,
            invalid_files=0 if result.is_valid else 1,
            total_errors=result.error_count,
            total_warnings=result.warning_count,
            is_all_valid=result.is_valid,
            results=[result],
        )
    else:
        # Default or --all: validate directory
        target_dir = Path(args.dir)
        report = validator.validate_directory(
            dir_path=target_dir,
            strict=args.strict,
            require_all_20=True if args.all else False,
        )

    print_result_table(report)
    print_detailed_issues(report.results + ([report.summary_validation] if report.summary_validation else []))

    if args.json_output:
        out_p = Path(args.json_output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)
        print(f"Validation report saved to: {out_p}")

    return 0 if report.is_all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
