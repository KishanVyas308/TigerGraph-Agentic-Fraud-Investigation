"""Case Queue and Inspection Route Handlers (Layer 27).

Provides case queue listings and detailed case lookups for the analyst dashboard.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import get_investigation_service_dep
from backend.app.schemas.api import CaseQueueResponse, InvestigationResponse
from backend.app.services.investigation_service import InvestigationService
from backend.app.utils.logging import get_logger

logger = get_logger("api.routes.cases")

router = APIRouter()


@router.get(
    "",
    response_model=CaseQueueResponse,
    summary="List cases for analyst dashboard queue",
)
async def list_cases(
    status: Optional[str] = Query(None, description="Filter by case status (OPEN, IN_PROGRESS, AWAITING_APPROVAL, COMPLETED)"),
    limit: int = Query(50, ge=1, le=200, description="Max cases to return"),
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> CaseQueueResponse:
    """Retrieve filtered case queue items for analyst triage and surveillance."""
    items = service.list_cases(status=status, limit=limit)
    return CaseQueueResponse(
        cases=items,
        total_count=len(items),
    )


@router.get(
    "/{case_id}",
    response_model=InvestigationResponse,
    summary="Get case details by ID",
)
async def get_case(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service_dep),
) -> InvestigationResponse:
    """Retrieve full detail representation for a specific case."""
    state = service.get_case(case_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )
    return service.to_investigation_response(state)
