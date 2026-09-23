"""FastAPI route dependency injection providers (Layer 27)."""

from backend.app.graph.tigergraph_client import TigerGraphClient, get_tigergraph_client
from backend.app.policies.engine import PolicyEngine, get_policy_engine
from backend.app.services.investigation_service import (
    InvestigationService,
    get_investigation_service,
)


def get_investigation_service_dep() -> InvestigationService:
    """Dependency providing singleton InvestigationService."""
    return get_investigation_service()


def get_tigergraph_client_dep() -> TigerGraphClient:
    """Dependency providing TigerGraphClient."""
    return get_tigergraph_client()


def get_policy_engine_dep() -> PolicyEngine:
    """Dependency providing PolicyEngine."""
    return get_policy_engine()
