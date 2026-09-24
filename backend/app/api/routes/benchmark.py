"""Benchmark Runner API Route Handlers (Layer 37).

Triggers batch execution of benchmark cases through the unified LangGraph workflow
without hardcoded outcomes, benchmark leakage, or outcome branch logic.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, status

from backend.app.schemas.api import (
    BenchmarkRunRequest,
    BenchmarkRunResponse,
)
from backend.app.services.benchmark_runner import BenchmarkRunnerService
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("api.routes.benchmark")

router = APIRouter()

DEFAULT_BENCHMARK_CASES = [f"CASE_{i:03d}" for i in range(1, 21)]


@router.post(
    "/run",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run benchmark test cases through unified investigation workflow",
)
async def run_benchmark(
    request: BenchmarkRunRequest,
) -> BenchmarkRunResponse:
    """Execute benchmark cases through the authoritative benchmark runner service.

    Strict rules enforced:
    - Zero outcome leakage.
    - Zero hardcoding or branching based on benchmark case IDs.
    - Every case passes through the identical LangGraph pipeline.
    """
    target_case_ids: Optional[List[str]] = request.case_ids or DEFAULT_BENCHMARK_CASES[:3]  # Default to first 3 for fast API response

    logger.info("Starting benchmark API run for %d cases", len(target_case_ids) if target_case_ids else 0)

    runner = BenchmarkRunnerService()
    summary = await runner.run_batch(
        case_ids=target_case_ids,
        dry_run=False,
        simulate_approvals=True,
    )

    results = [
        {
            "case_id": c.case_id,
            "status": c.status,
            "stop_reason": c.stop_reason,
            "risk_level": c.risk_level,
            "risk_score": c.risk_score,
            "action": c.action_type,
            "sar_filed": c.sar_filed,
            "is_persisted": c.is_persisted,
            "duration_ms": c.duration_ms,
            "answer_file_path": c.answer_file_path,
            "error": c.error,
        }
        for c in summary.cases
    ]

    return BenchmarkRunResponse(
        benchmark_run_id=summary.benchmark_run_id,
        total_cases=summary.total_cases,
        completed_cases=summary.completed_cases,
        results=results,
        timestamp=now_iso(),
    )
