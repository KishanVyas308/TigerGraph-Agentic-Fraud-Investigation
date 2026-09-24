"""Benchmark Schemas (Layer 37).

Defines typed Pydantic models for authoritative benchmark case answer artifacts
and benchmark run summaries in strict compliance with AGENTS.md §34 and dataset specifications.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionType,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    RiskLevel,
    StopReason,
    TriggerType,
)
from backend.app.utils.time import now_iso


class BenchmarkCaseDetails(BaseModel):
    """Detailed trigger and entity anchor metadata for a benchmark case."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    trigger_type: str
    trigger_entity_id: Optional[str] = None
    trigger_entity_type: Optional[str] = None
    description: str = ""
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    account_ids: List[str] = Field(default_factory=list)
    opened_at: str = Field(default_factory=now_iso)
    closed_at: Optional[str] = None


class BenchmarkApprovalRoute(BaseModel):
    """Governance and approval routing audit block."""

    model_config = ConfigDict(extra="ignore")

    approval_required: bool = False
    approval_role: Optional[str] = None
    approval_status: Optional[str] = None
    approval_decisions: List[Dict[str, Any]] = Field(default_factory=list)


class BenchmarkCaseAnswer(BaseModel):
    """Complete authoritative answer document for a single benchmark case.

    Includes all fields mandated by AGENTS.md §34 and dataset README:
    - case details
    - internal investigation record
    - evidence
    - graph findings
    - fraud hypotheses
    - matched patterns
    - policy context
    - similar historical cases
    - risk (level & score)
    - confidence
    - evidence completeness
    - missing evidence
    - pre-evidence next-best action
    - requested evidence
    - received evidence
    - post-evidence next-best action
    - approval route
    - actions
    - SAR report where required
    - final status
    - stop reason
    """

    model_config = ConfigDict(extra="ignore")

    case_id: str
    case_details: BenchmarkCaseDetails
    internal_investigation_record: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological timeline events capturing every state transition and node execution.",
    )
    evidence: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All normalized evidence items with strict provenance, category, and reliability tier.",
    )
    graph_findings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Deterministic graph features, behavioral summaries, and topology findings.",
    )
    fraud_hypotheses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Competing fraud hypotheses assessed with supporting/contradicting evidence citations.",
    )
    matched_patterns: List[str] = Field(
        default_factory=list,
        description="Typology identifiers and fraud patterns matched against case evidence.",
    )
    policy_context: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant fraud policy rules, regulatory guidelines, and action restrictions.",
    )
    similar_historical_cases: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top historical case precedents retrieved via hybrid graph/vector matching.",
    )
    risk_level: str = "LOW"
    risk_score: float = 0.0
    confidence: float = 0.0
    evidence_completeness: float = 0.0
    missing_evidence: List[str] = Field(default_factory=list)

    # Pre/Post NBA Preservation
    pre_evidence_next_best_action: Optional[Dict[str, Any]] = None
    requested_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    received_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    post_evidence_next_best_action: Optional[Dict[str, Any]] = None

    # Governance & Execution
    approval_route: BenchmarkApprovalRoute = Field(default_factory=BenchmarkApprovalRoute)
    actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions executed or simulated with execution_mode=SIMULATED.",
    )
    sar_report: Optional[Dict[str, Any]] = None

    # Lifecycle & Audit
    final_status: str = "COMPLETED"
    stop_reason: str = "SUFFICIENT_EVIDENCE_FOR_ACTION"
    case_summary: str = ""
    graph_persisted: bool = False
    vector_indexed: bool = False
    closed_at: str = Field(default_factory=now_iso)

    # Shorthand property aliases for compatibility across validator conventions
    @property
    def case(self) -> Dict[str, Any]:
        return self.case_details.model_dump()

    @property
    def findings(self) -> Dict[str, Any]:
        return self.graph_findings

    @property
    def decisions(self) -> Dict[str, Any]:
        return {
            "pre_evidence_next_best_action": self.pre_evidence_next_best_action,
            "post_evidence_next_best_action": self.post_evidence_next_best_action,
            "approval_route": self.approval_route.model_dump(),
        }

    @property
    def status(self) -> str:
        return self.final_status

    @property
    def sar(self) -> Optional[Dict[str, Any]]:
        return self.sar_report

    def to_export_dict(self) -> Dict[str, Any]:
        """Produce standard dictionary for JSON disk serialization including aliases."""
        data = self.model_dump()
        data["case"] = self.case
        data["findings"] = self.findings
        data["decisions"] = self.decisions
        data["status"] = self.status
        data["sar"] = self.sar
        return data


class BenchmarkCaseRunMetric(BaseModel):
    """Execution performance metrics and verification for a single benchmark case."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    status: str
    stop_reason: Optional[str] = None
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    evidence_completeness: Optional[float] = None
    action_type: Optional[str] = None
    approval_required: bool = False
    approval_status: Optional[str] = None
    sar_filed: bool = False
    is_persisted: bool = False
    is_indexed: bool = False
    duration_ms: float = 0.0
    evidence_count: int = 0
    answer_file_path: Optional[str] = None
    error: Optional[str] = None


class BenchmarkRunSummary(BaseModel):
    """Consolidated report produced after running a batch of benchmark cases."""

    model_config = ConfigDict(extra="ignore")

    benchmark_run_id: str
    started_at: str
    completed_at: str
    total_duration_sec: float
    total_cases: int
    completed_cases: int
    failed_cases: int
    quarantine_verified: bool = True
    output_directory: str
    cases: List[BenchmarkCaseRunMetric] = Field(default_factory=list)


class ValidationSeverity(str, Enum):
    """Severity tier for a benchmark validation issue."""

    ERROR = "ERROR"
    WARNING = "WARNING"


class ValidationCategory(str, Enum):
    """Functional category for a benchmark validation rule."""

    STRUCTURE = "STRUCTURE"
    CASE_METADATA = "CASE_METADATA"
    EVIDENCE = "EVIDENCE"
    GROUNDING = "GROUNDING"
    METRICS = "METRICS"
    NBA = "NBA"
    GOVERNANCE = "GOVERNANCE"
    ACTIONS = "ACTIONS"
    SAR = "SAR"
    PERSISTENCE = "PERSISTENCE"
    LIFECYCLE = "LIFECYCLE"
    QUARANTINE = "QUARANTINE"


class BenchmarkValidationIssue(BaseModel):
    """Detailed validation issue identified in a benchmark answer file."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(description="Machine-readable rule violation code, e.g. MISSING_FIELD, BROKEN_EVIDENCE_ID")
    severity: ValidationSeverity = ValidationSeverity.ERROR
    category: ValidationCategory = ValidationCategory.STRUCTURE
    message: str = Field(description="Clear human-readable diagnostic description of the failure.")
    field_path: str = Field(description="Exact JSON path or field location of the issue.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Supplementary debugging context.")


class BenchmarkValidationResult(BaseModel):
    """Validation report for a single benchmark answer file."""

    model_config = ConfigDict(extra="ignore")

    file_path: str
    case_id: Optional[str] = None
    is_valid: bool = True
    error_count: int = 0
    warning_count: int = 0
    issues: List[BenchmarkValidationIssue] = Field(default_factory=list)
    validated_at: str = Field(default_factory=now_iso)


class BenchmarkValidationReport(BaseModel):
    """Consolidated validation report covering an entire benchmark suite."""

    model_config = ConfigDict(extra="ignore")

    total_files: int = 0
    valid_files: int = 0
    invalid_files: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    is_all_valid: bool = True
    results: List[BenchmarkValidationResult] = Field(default_factory=list)
    summary_validation: Optional[BenchmarkValidationResult] = None
    started_at: str = Field(default_factory=now_iso)
    completed_at: str = Field(default_factory=now_iso)
