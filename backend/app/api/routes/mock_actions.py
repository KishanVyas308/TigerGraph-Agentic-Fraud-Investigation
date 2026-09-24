"""Mock Service Route Handlers (Layer 27).

Simulates external banking and customer challenge actions for local hackathon testing:
- Customer SMS/push confirmation responses.
- Biometric/OTP step-up authentication challenges.
All endpoints are explicitly labeled as SIMULATED.
"""

from typing import Any, Dict
from fastapi import APIRouter, status

from backend.app.actions.mocks import (
    MockCustomerConfirmationService,
    MockStepUpAuthService,
)
from backend.app.schemas.api import MockConfirmationRequest, MockStepUpRequest
from backend.app.utils.logging import get_logger

logger = get_logger("api.routes.mock_actions")

router = APIRouter()

customer_service = MockCustomerConfirmationService()
auth_service = MockStepUpAuthService()


@router.post(
    "/customer-confirmation",
    status_code=status.HTTP_200_OK,
    summary="Simulate customer SMS transaction confirmation",
)
async def mock_customer_confirmation(
    request: MockConfirmationRequest,
) -> Dict[str, Any]:
    """Simulate customer response to an SMS/push confirmation alert."""
    logger.info("Mock API: customer confirmation for %s / %s", request.customer_id, request.transaction_id)
    res = customer_service.request_confirmation(
        customer_id=request.customer_id,
        transaction_id=request.transaction_id,
        confirmed=request.confirmed if request.confirmed is not None else True,
    )
    result = res[0] if isinstance(res, tuple) else res
    exec_mode = result.execution_mode.value if hasattr(result.execution_mode, "value") else str(result.execution_mode)
    return {
        "execution_mode": exec_mode,
        "success": result.success,
        "result": result.result,
        "disclaimer": result.disclaimer,
    }


@router.post(
    "/step-up-auth",
    status_code=status.HTTP_200_OK,
    summary="Simulate biometric/OTP step-up authentication challenge",
)
async def mock_step_up_auth(
    request: MockStepUpRequest,
) -> Dict[str, Any]:
    """Simulate user response to a step-up authentication challenge."""
    logger.info("Mock API: step-up authentication for %s", request.account_id)
    res = auth_service.challenge_user(
        account_id=request.account_id,
        method=request.challenge_type or "BIOMETRIC",
        passed=request.passed if request.passed is not None else True,
    )
    result = res[0] if isinstance(res, tuple) else res
    exec_mode = result.execution_mode.value if hasattr(result.execution_mode, "value") else str(result.execution_mode)
    return {
        "execution_mode": exec_mode,
        "success": result.success,
        "result": result.result,
        "disclaimer": result.disclaimer,
    }
