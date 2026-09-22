"""Domain models and schemas for TigerGraph client and MCP tool integration."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Re-export core query output models
from backend.app.graph.queries import (
    TransactionContext,
    TransactionBehavior,
    SharedDeviceContext,
    SharedIPContext,
    FraudNeighborsContext,
    ShortestPathToFraud,
    MoneyFlowPattern,
    DeviceIdentityContext,
)


class ToolPermission(str, Enum):
    """Permission level for graph operations."""
    READ_ONLY = "READ_ONLY"
    APPEND_ONLY = "APPEND_ONLY"
    FORBIDDEN = "FORBIDDEN"


# --- MCP Tool Input Parameters ---

class TransactionContextParams(BaseModel):
    transaction_id: str = Field(..., description="Target transaction identifier (e.g., TX_0001)")


class TransactionBehaviorParams(BaseModel):
    transaction_id: str = Field(..., description="Target transaction identifier")
    lookback_hours: int = Field(default=24, ge=1, le=720, description="Hours of historical lookback")


class EntityNeighborhoodParams(BaseModel):
    vertex_id: str = Field(..., description="Starting vertex identifier")
    max_depth: int = Field(default=2, ge=1, le=3, description="Maximum traversal depth (hops)")
    max_vertices: int = Field(default=50, ge=5, le=200, description="Maximum vertices to return")


class SharedDeviceParams(BaseModel):
    device_id: str = Field(..., description="Target device identifier (e.g., DEV_001)")


class SharedIPParams(BaseModel):
    ip_address: str = Field(..., description="Target client IP address")


class FraudNeighborsParams(BaseModel):
    vertex_id: str = Field(..., description="Starting vertex identifier (account or device)")
    max_hops: int = Field(default=2, ge=1, le=2, description="Maximum search hops")


class ShortestPathParams(BaseModel):
    vertex_id: str = Field(..., description="Starting vertex identifier")
    max_depth: int = Field(default=4, ge=1, le=5, description="Maximum search depth")


class MoneyFlowPatternParams(BaseModel):
    account_id: str = Field(..., description="Target account identifier (e.g., ACC_001)")


class DeviceIdentityParams(BaseModel):
    device_id: str = Field(..., description="Target device identifier")


class SimilarGraphCasesParams(BaseModel):
    case_id: str = Field(..., description="Target case identifier")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum similar cases to return")


class CaseTimelineParams(BaseModel):
    case_id: str = Field(..., description="Target case identifier")


class CaseUpdateParams(BaseModel):
    case_id: str = Field(..., description="Target case identifier to update")
    status: str = Field(..., description="Case status (e.g., IN_PROGRESS, AWAITING_APPROVAL, CLOSED)")
    risk_level: str = Field(..., description="Assessed risk level (LOW, MEDIUM, HIGH, CRITICAL)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence_completeness: float = Field(..., ge=0.0, le=1.0, description="Completeness score 0.0 to 1.0")
    stop_reason: Optional[str] = Field(default=None, description="Explicit reason if investigation stopped")
    summary: str = Field(..., description="Concise investigation synthesis summary")


class VectorSearchParams(BaseModel):
    query_text: str = Field(..., description="Query text to search for semantically similar precedents/policies")
    collection: str = Field(default="cases", description="Target collection: 'cases' or 'policies'")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of results to retrieve")


# --- Graph Visualization Models ---

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    directed: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GraphVisualizationData(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
