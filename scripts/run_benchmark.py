#!/usr/bin/env python3
"""Benchmark Runner CLI (Layer 37).

Runs all 20 benchmark cases (or selected subsets) through the exact same
LangGraph investigation workflow without hardcoded answer logic or ground truth leakage.

Usage:
    # Run all 20 benchmark cases:
    python scripts/run_benchmark.py --all

    # Run a single case:
    python scripts/run_benchmark.py --case CASE_001

    # Run first 3 cases in dry-run mode:
    python scripts/run_benchmark.py --limit 3 --dry-run
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.benchmark_runner import BenchmarkRunnerService
from backend.app.utils.logging import get_logger, setup_logging

logger = get_logger("scripts.run_benchmark")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for the benchmark runner."""
    parser = argparse.ArgumentParser(
        description="TigerGraph Fraud Investigation Benchmark Runner (Layer 37)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all 20 benchmark cases sequentially",
    )
    group.add_argument(
        "--case",
        type=str,
        help="Specific benchmark case ID to run (e.g. CASE_001)",
    )
    group.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N benchmark cases",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/benchmark",
        help="Output directory for JSON answer files and run summary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute investigations without exporting answer files to disk",
    )
    parser.add_argument(
        "--no-simulate-approvals",
        action="store_true",
        help="Do not simulate approvals on sensitive actions (cases remain paused at AWAITING_APPROVAL)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )

    return parser.parse_args()


async def main_async() -> int:
    """Async entrypoint for benchmark batch execution."""
    args = parse_args()

    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)

    out_dir = Path(args.output_dir)
    service = BenchmarkRunnerService(output_dir=out_dir)

    case_ids = [args.case] if args.case else None
    limit = args.limit
    if not args.case and not args.limit and not args.all:
        # Default to first case if neither --all, --case, nor --limit provided
        print("Notice: Neither --all, --case, nor --limit specified. Defaulting to first 3 cases for quick validation.")
        print("To run all 20 benchmark cases, use: python scripts/run_benchmark.py --all\n")
        limit = 3

    print(f"=================================================================")
    print(f"   TIGERGRAPH FRAUD INVESTIGATION BENCHMARK RUNNER (LAYER 37)   ")
    print(f"=================================================================")
    print(f"Target: {'All 20 cases' if args.all else (args.case or f'First {limit} cases')}")
    print(f"Output Directory: {out_dir}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Simulate Approvals: {not args.no_simulate_approvals}")
    print(f"-----------------------------------------------------------------\n")

    summary = await service.run_batch(
        case_ids=case_ids,
        limit=limit,
        dry_run=args.dry_run,
        simulate_approvals=not args.no_simulate_approvals,
    )

    print(f"\n=================================================================")
    print(f"                   BENCHMARK EXECUTION SUMMARY                   ")
    print(f"=================================================================")
    print(f"Run ID:            {summary.benchmark_run_id}")
    print(f"Total Cases:       {summary.total_cases}")
    print(f"Completed Cases:   {summary.completed_cases}")
    print(f"Failed Cases:      {summary.failed_cases}")
    print(f"Total Duration:    {summary.total_duration_sec:.2f}s")
    print(f"Quarantine Safe:   {summary.quarantine_verified}")
    print(f"Output Directory:  {summary.output_directory}")
    print(f"-----------------------------------------------------------------")
    print(f"{'Case ID':<10} | {'Status':<12} | {'Risk':<10} | {'Score':<6} | {'Action':<22} | {'SAR':<5} | {'Persisted':<10}")
    print(f"-----------------------------------------------------------------")
    for c in summary.cases:
        print(
            f"{c.case_id:<10} | "
            f"{c.status:<12} | "
            f"{(c.risk_level or 'N/A'):<10} | "
            f"{(f'{c.risk_score:.2f}' if c.risk_score is not None else 'N/A'):<6} | "
            f"{(c.action_type or 'N/A')[:22]:<22} | "
            f"{('YES' if c.sar_filed else 'NO'):<5} | "
            f"{('YES' if c.is_persisted else 'NO'):<10}"
        )
    print(f"=================================================================\n")

    return 0 if summary.failed_cases == 0 else 1


def main() -> None:
    """Synchronous wrapper."""
    code = asyncio.run(main_async())
    sys.exit(code)


if __name__ == "__main__":
    main()
