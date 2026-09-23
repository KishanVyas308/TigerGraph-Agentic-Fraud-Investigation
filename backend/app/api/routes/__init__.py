"""API Routes package initialization."""

from backend.app.api.routes.benchmark import router as benchmark_router
from backend.app.api.routes.cases import router as cases_router
from backend.app.api.routes.investigations import router as investigations_router
from backend.app.api.routes.mock_actions import router as mock_router

__all__ = [
    "investigations_router",
    "cases_router",
    "mock_router",
    "benchmark_router",
]
