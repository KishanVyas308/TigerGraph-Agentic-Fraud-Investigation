"""Investigation API Route Handlers (Layer 27).

Thin route handlers delegating to InvestigationService for:
- Triggering investigations
- Inspecting case status & details
- Streaming investigation progress events via SSE
- Fetching Cytoscape graph visualization data
- Fetching evidence card listings
- Ingesting supplemental evidence
- Submitting analyst approvals, rejections, and action modifications
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.api.dependencies import get_investigation_service_dep
from backend.app.models.state import ApprovalStatus
from backend.app.schemas.api import (
    ApprovalActionRequest,
    EvidenceListResponse,
    GraphVisualizationResponse,
    InvestigationResponse,
    InvestigationTraceResponse,
    ModifyActionRequest,
    SubmitEvidenceRequest,
    TriggerInvestigationRequest,
)
from backend.app.services.investigation_service import InvestigationService
from backend.app.utils.logging import get_logger

logger = get_logger("api.routes.investigations")

router = APIRouter()


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a new fraud investigation",
)
async def trigger_investigation(
    request: TriggerInvestigationRequest,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Accept a fraud trigger and initiate the complete investigation workflow."""
    logger.info("API request: start investigation for trigger %s", request.trigger_type)
    state = await service.start_investigation(request)
    return service.to_investigation_response(state)


@router.get(
    "/{case_id}",
    response_model=InvestigationResponse,
    summary="Get detailed investigation state",
)
async def get_investigation(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Retrieve the complete current state of an investigation."""
    state = service.get_case(case_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return service.to_investigation_response(state)


@router.get(
    "/{case_id}/events",
    summary="Stream investigation timeline events via SSE",
)
async def stream_investigation_events(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service_dep),
):
    """Subscribe to Server-Sent Events (SSE) streaming case milestone progression."""
    state = service.get_case(case_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )

    return StreamingResponse(
        service.stream_investigation_events(case_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{case_id}/graph",
    response_model=GraphVisualizationResponse,
    summary="Get Cytoscape.js fraud graph elements",
)
async def get_investigation_graph(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> GraphVisualizationResponse:
    """Retrieve Cytoscape.js formatted nodes and edges for fraud network visualization."""
    graph = service.get_case_graph(case_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation graph for {case_id} not found",
        )
    return graph


@router.get(
    "/{case_id}/evidence",
    response_model=EvidenceListResponse,
    summary="Get evidence cards for investigation",
)
async def get_investigation_evidence(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> EvidenceListResponse:
    """Retrieve all normalized evidence items as card models."""
    cards = service.get_case_evidence(case_id)
    if cards is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return EvidenceListResponse(
        case_id=case_id,
        evidence=cards,
        total_count=len(cards),
    )


@router.get(
    "/{case_id}/trace",
    response_model=InvestigationTraceResponse,
    summary="Get execution trace and audit spans",
)
async def get_investigation_trace(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationTraceResponse:
    """Retrieve structured audit trail spans for a case from local JSONL logs."""
    trace_res = service.get_case_traces(case_id)
    if trace_res is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return trace_res


@router.post(
    "/{case_id}/evidence",
    response_model=InvestigationResponse,
    summary="Submit supplemental evidence",
)
async def submit_investigation_evidence(
    case_id: str,
    request: SubmitEvidenceRequest,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Inject supplemental evidence or analyst note and re-evaluate reasoning."""
    state = await service.submit_additional_evidence(case_id, request)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return service.to_investigation_response(state)


@router.post(
    "/{case_id}/approve",
    response_model=InvestigationResponse,
    summary="Approve sensitive recommended action",
)
async def approve_action(
    case_id: str,
    request: ApprovalActionRequest,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Human analyst approves a sensitive recommended action to resume workflow."""
    state = await service.process_approval_decision(
        case_id=case_id,
        status=ApprovalStatus.APPROVED,
        role=request.reviewer_role,
        reviewer_id=request.reviewer_id,
        comments=request.comments,
    )
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return service.to_investigation_response(state)


@router.post(
    "/{case_id}/reject",
    response_model=InvestigationResponse,
    summary="Reject sensitive recommended action",
)
async def reject_action(
    case_id: str,
    request: ApprovalActionRequest,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Human analyst rejects a sensitive action, routing workflow to safe fallback."""
    state = await service.process_approval_decision(
        case_id=case_id,
        status=ApprovalStatus.REJECTED,
        role=request.reviewer_role,
        reviewer_id=request.reviewer_id,
        comments=request.comments,
    )
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return service.to_investigation_response(state)


@router.post(
    "/{case_id}/modify-action",
    response_model=InvestigationResponse,
    summary="Modify recommended next-best action",
)
async def modify_action(
    case_id: str,
    request: ModifyActionRequest,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Human analyst modifies recommended action and re-evaluates policy."""
    state = await service.process_approval_decision(
        case_id=case_id,
        status=ApprovalStatus.MODIFIED,
        role=request.reviewer_role,
        reviewer_id=request.reviewer_id,
        comments=request.comments or request.reasoning,
        modified_action=request.action_type,
    )
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {case_id} not found",
        )
    return service.to_investigation_response(state)
