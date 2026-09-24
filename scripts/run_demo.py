#!/usr/bin/env python3
"""Local Demo Scenarios Runner CLI (Layer 40).

Runs the three canonical deterministic fraud investigation demo scenarios:
1. Demo 1 — Fraud Network (Mule Ring & Shared Hardware Auto-Block)
2. Demo 2 — Uncertain Case (Borderline Wire & Customer Confirmation Evidence Loop)
3. Demo 3 — Human Approval (Account Takeover & Supervisor Governance Gate)

Usage:
    # Run all 3 demo scenarios:
    python scripts/run_demo.py --scenario ALL

    # Run Demo 1 (Fraud Network):
    python scripts/run_demo.py --scenario 1

    # Run Demo 2 (Uncertain Evidence Loop):
    python scripts/run_demo.py --scenario 2

    # Run Demo 3 (Human Approval):
    python scripts/run_demo.py --scenario 3

    # Run step-by-step with interactive prompts:
    python scripts/run_demo.py --scenario ALL --step-by-step
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.demo import DemoScenarioId, DemoScenarioResult
from backend.app.services.demo_runner import DemoRunnerService
from backend.app.utils.logging import get_logger, setup_logging

logger = get_logger("scripts.run_demo")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the demo scenario runner."""
    parser = argparse.ArgumentParser(
        description="TigerGraph Fraud Investigation Demo Runner (Layer 40)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--scenario",
        type=str,
        default="ALL",
        choices=["1", "2", "3", "ALL"],
        help="Demo scenario to execute (1: Fraud Network, 2: Uncertain Loop, 3: Human Approval, or ALL)",
    )
    parser.add_argument(
        "--step-by-step",
        action="store_true",
        help="Print step-by-step breakdowns for presentation/demo delivery",
    )
    parser.add_argument(
        "--export-dir",
        type=str,
        default="outputs/demo",
        help="Directory to save demo run artifacts and summaries",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def display_scenario_header(res: DemoScenarioResult) -> None:
    """Display banner and overview for a demo scenario."""
    print("\n" + "=" * 90)
    print(f"   {res.name.upper()}   ")
    print("=" * 90)
    print(f"Case ID:             {res.case_id}")
    print(f"Initial Risk:        {res.initial_risk or 'N/A'}")
    print(f"Final Risk:          {res.final_risk}")
    print(f"Pre-Evidence Action: {res.pre_evidence_action or 'N/A'}")
    print(f"Final Action:        {res.post_evidence_action}")
    print(f"Approval Required:   {'YES' if res.approval_required else 'NO'}")
    if res.approval_status:
        print(f"Approval Decision:   {res.approval_status}")
    print(f"SAR Generated:       {'YES' if res.sar_generated else 'NO'}")
    print(f"TigerGraph Persist:  {'YES' if res.is_persisted else 'NO'}")
    print(f"Stop Reason:         {res.stop_reason}")
    print(f"Total Duration:      {res.duration_ms:.1f}ms")
    print("-" * 90)


def display_scenario_steps(res: DemoScenarioResult, interactive: bool = False) -> None:
    """Display chronological investigation steps for a demo scenario."""
    print("Investigation Workflow Steps:")
    for step in res.steps:
        print(f"\n  [Step {step.step_number}] {step.title}")
        print(f"   Node:        {step.node_name or 'System'}")
        print(f"   Narrative:   {step.description}")
        if step.data:
            print("   Details:")
            for k, v in step.data.items():
                print(f"     - {k}: {v}")

    print("\n" + "=" * 90)


async def main_async() -> int:
    """Async CLI entry point."""
    args = parse_args()
    setup_logging(level="DEBUG" if args.verbose else "INFO")

    export_path = Path(args.export_dir)
    service = DemoRunnerService(export_dir=export_path)

    print("\n==========================================================================================")
    print("            TIGERGRAPH AGENTIC FRAUD INVESTIGATION — DEMO RUNNER (LAYER 40)              ")
    print("==========================================================================================")
    print("Available Scenarios:")
    for meta in service.get_scenarios_metadata():
        print(f"  [{meta.scenario_id.value}] {meta.name}")
        print(f"      Typology: {meta.typology}")
        print(f"      Summary:  {meta.summary}\n")
    print("------------------------------------------------------------------------------------------")

    results: list[DemoScenarioResult] = []

    if args.scenario in ("1", "ALL"):
        print("\nExecuting Demo 1: Graph-Detected Fraud Network...")
        r1 = await service.run_demo_1_fraud_network()
        display_scenario_header(r1)
        if args.step_by_step or args.scenario == "1":
            display_scenario_steps(r1, interactive=args.step_by_step)
        results.append(r1)

    if args.scenario in ("2", "ALL"):
        print("\nExecuting Demo 2: Borderline Case with Customer Confirmation Loop...")
        r2 = await service.run_demo_2_uncertain_evidence_loop(customer_confirmed=True)
        display_scenario_header(r2)
        if args.step_by_step or args.scenario == "2":
            display_scenario_steps(r2, interactive=args.step_by_step)
        results.append(r2)

    if args.scenario in ("3", "ALL"):
        print("\nExecuting Demo 3: High-Risk Account Freeze with Human Approval...")
        r3 = await service.run_demo_3_human_approval(approve=True)
        display_scenario_header(r3)
        if args.step_by_step or args.scenario == "3":
            display_scenario_steps(r3, interactive=args.step_by_step)
        results.append(r3)

    # Persist suite report
    suite_report = await service.run_all_demos()
    print(f"\nAll {len(results)} scenario(s) executed successfully.")
    print(f"Artifacts exported to: {export_path.resolve()}/")
    print("==========================================================================================\n")
    return 0


def main() -> None:
    """Synchronous wrapper."""
    code = asyncio.run(main_async())
    sys.exit(code)


if __name__ == "__main__":
    main()
