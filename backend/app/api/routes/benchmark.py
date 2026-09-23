"""Benchmark Runner API Route Handlers (Layer 27).

Triggers batch execution of benchmark cases through the unified LangGraph workflow
without hardcoded outcomes, benchmark leakage, or outcome branch logic.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, status

from backend.app.api.dependencies import get_investigation_service_dep
from backend.app.models.state import TriggerType
from backend.app.schemas.api import (
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    TriggerInvestigationRequest,
)
from backend.app.services.investigation_service import InvestigationService
from backend.app.utils.ids import generate_prefixed_id
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
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> BenchmarkRunResponse:
    """Execute benchmark cases through the normal investigation workflow.

    Strict rules enforced:
    - Zero outcome leakage.
    - Zero hardcoding or branching based on benchmark case IDs.
    - Every case passes through the identical LangGraph pipeline.
    """
    run_id = generate_prefixed_id("BENCH", 8)
    target_case_ids: List[str] = request.case_ids or DEFAULT_BENCHMARK_CASES[:3]  # Default to first 3 for fast API response

    logger.info("Starting benchmark run %s for %d cases", run_id, len(target_case_ids))

    results = []
    for cid in target_case_ids:
        trigger_req = TriggerInvestigationRequest(
            case_id=cid,
            trigger_type=TriggerType.TRANSACTION_ALERT,
            transaction_id=f"TX_{cid[-3:]}",
            customer_id=f"CUST_{cid[-3:]}",
        )
        try:
            state = await service.start_investigation(trigger_req)
            results.append({
                "case_id": cid,
                "status": state.case_status.value if hasattr(state.case_status, "value") else str(state.case_status),
                "stop_reason": state.stop_reason.value if state.stop_reason else None,
                "risk_level": state.risk_level.value if state.risk_level else None,
                "action": (
                    state.post_evidence_next_best_action.action_type.value
                    if state.post_evidence_next_best_action and hasattr(state.post_evidence_next_best_action.action_type, "value")
                    else (str(state.post_evidence_next_best_action.action_type) if state.post_evidence_next_best_action else None)
                ),
            })
        except Exception as exc:
            logger.error("Benchmark case %s execution error: %s", cid, exc)
            results.append({
                "case_id": cid,
                "status": "ERROR",
                "error": str(exc),
            })

    return BenchmarkRunResponse(
        benchmark_run_id=run_id,
        total_cases=len(target_case_ids),
        completed_cases=len(results),
        results=results,
        timestamp=now_iso(),
    )
