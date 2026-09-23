"""API Request and Response Pydantic Schemas (Layer 27).

Defines typed contract models at all FastAPI application boundaries:
- Investigation lifecycle requests & responses.
- Case queue representations.
- Cytoscape.js graph visualization nodes and edges.
- Evidence card listings.
- Human analyst approval/rejection/modification inputs.
- Mock challenge requests & responses.
- Benchmark runner payloads.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionType,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    RiskLevel,
    TriggerType,
)
from backend.app.utils.time import now_iso


# ============================================================================
# Request Schemas
# ============================================================================

class TriggerInvestigationRequest(BaseModel):
    """Payload to initiate a new fraud investigation or resume an existing case."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    case_id: Optional[str] = None
    trigger_type: TriggerType = TriggerType.TRANSACTION_ALERT
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    account_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubmitEvidenceRequest(BaseModel):
    """Payload to inject analyst notes or external evidence into an open investigation."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    evidence_type: str = "MANUAL_ANALYST_NOTE"
    category: EvidenceCategory = EvidenceCategory.ANALYST_INPUT
    fact: str
    source_reference: Optional[str] = None
    reliability: float = Field(default=0.9, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalActionRequest(BaseModel):
    """Payload for human analyst approval or rejection of sensitive actions."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    reviewer_role: ApprovalRole = ApprovalRole.FRAUD_ANALYST
    reviewer_id: Optional[str] = "ANALYST_01"
    comments: Optional[str] = None


class ModifyActionRequest(BaseModel):
    """Payload for analyst modification of a recommended next-best action."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    action_type: ActionType
    reviewer_role: ApprovalRole = ApprovalRole.FRAUD_ANALYST
    reviewer_id: Optional[str] = "ANALYST_01"
    comments: Optional[str] = None
    reasoning: Optional[str] = None


class MockConfirmationRequest(BaseModel):
    """Payload to trigger simulated customer confirmation response."""

    model_config = ConfigDict(extra="ignore")

    customer_id: str
    transaction_id: str
    confirmed: Optional[bool] = None


class MockStepUpRequest(BaseModel):
    """Payload to trigger simulated step-up authentication challenge."""

    model_config = ConfigDict(extra="ignore")

    account_id: str
    challenge_type: str = "BIOMETRIC_PUSH"
    passed: Optional[bool] = None


class BenchmarkRunRequest(BaseModel):
    """Payload to trigger execution of benchmark test cases."""

    model_config = ConfigDict(extra="ignore")

    case_ids: Optional[List[str]] = None
    mode: str = "local"


# ============================================================================
# Response Schemas
# ============================================================================

class InvestigationResponse(BaseModel):
    """Full detail view of an investigation state."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    case_id: str
    case_status: str
    trigger_type: str
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    account_ids: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    evidence_completeness: Optional[float] = None
    stop_reason: Optional[str] = None
    case_summary: Optional[str] = None
    pre_evidence_action: Optional[Dict[str, Any]] = None
    requested_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    post_evidence_action: Optional[Dict[str, Any]] = None
    approval_required: bool = False
    approval_status: Optional[str] = None
    executed_actions: List[Dict[str, Any]] = Field(default_factory=list)
    sar_reference: Optional[str] = None
    is_persisted: bool = False
    is_indexed: bool = False
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    historical_ml_score: Optional[float] = None
    similar_cases: List[Dict[str, Any]] = Field(default_factory=list)
    policy_context: List[Dict[str, Any]] = Field(default_factory=list)
    timeline_event_count: int = 0
    created_at: str = Field(default_factory=now_iso)


class CaseQueueItem(BaseModel):
    """Lightweight summary item for the analyst case queue table."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    case_id: str
    trigger_type: str
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    created_at: str
    stop_reason: Optional[str] = None
    primary_action: Optional[str] = None


class CaseQueueResponse(BaseModel):
    """List response for the analyst case queue view."""

    cases: List[CaseQueueItem] = Field(default_factory=list)
    total_count: int = 0


# Cytoscape Graph Visualization Schemas
class CytoscapeElementData(BaseModel):
    """Data payload of a Cytoscape.js node or edge."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    type: str
    source: Optional[str] = None
    target: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class CytoscapeElement(BaseModel):
    """Standard Cytoscape.js graph element wrapper."""

    data: CytoscapeElementData
    classes: Optional[str] = None


class GraphVisualizationResponse(BaseModel):
    """Graph structure formatted for Cytoscape.js visualization."""

    case_id: str
    nodes: List[CytoscapeElement] = Field(default_factory=list)
    edges: List[CytoscapeElement] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)


# Evidence List Schemas
class EvidenceCard(BaseModel):
    """Single evidence card view item for analyst dashboard."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    evidence_id: str
    source: str
    source_reference: Optional[str] = None
    category: str
    fact: str
    reliability: float
    timestamp: str
    supports_hypotheses: List[str] = Field(default_factory=list)
    contradicts_hypotheses: List[str] = Field(default_factory=list)


class EvidenceListResponse(BaseModel):
    """Evidence panel response for a case."""

    case_id: str
    evidence: List[EvidenceCard] = Field(default_factory=list)
    total_count: int = 0


class BenchmarkRunResponse(BaseModel):
    """Results summary from a benchmark execution run."""

    benchmark_run_id: str
    total_cases: int
    completed_cases: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=now_iso)


# Observability and Audit Trail Schemas
class TraceSpanItem(BaseModel):
    """Audited execution span representation for API response."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    span_id: str
    case_id: str
    span_type: str
    name: str
    node_name: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    status: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class InvestigationTraceResponse(BaseModel):
    """Full audit trail trace response containing all spans for an investigation."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    case_id: str
    total_spans: int = 0
    total_duration_ms: float = 0.0
    spans: List[TraceSpanItem] = Field(default_factory=list)
    trace_file_path: Optional[str] = None

