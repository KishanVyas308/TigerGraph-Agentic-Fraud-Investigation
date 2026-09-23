"""Case Schemas (Layer 23).

Defines structured models for final case validation and consolidated case summaries.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ApprovalStatus,
    CaseStatus,
    RiskLevel,
    StopReason,
    TriggerType,
)
from backend.app.utils.time import now_iso


class ValidationResult(BaseModel):
    """Integrity validation report for final case state before closure."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class FinalCaseSummary(BaseModel):
    """Consolidated, structured case summary capturing all outputs of the investigation."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    case_id: str
    status: CaseStatus
    stop_reason: StopReason
    trigger_type: TriggerType
    customer_id: Optional[str] = None
    transaction_id: Optional[str] = None
    account_ids: List[str] = Field(default_factory=list)

    # Risk & Reasoning
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    evidence_completeness: Optional[float] = None
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)

    # Evidence
    total_evidence_count: int = 0
    evidence_category_counts: Dict[str, int] = Field(default_factory=dict)

    # Actions & Governance
    pre_evidence_next_best_action: Optional[Dict[str, Any]] = None
    post_evidence_next_best_action: Optional[Dict[str, Any]] = None
    approval_required: bool = False
    approval_status: Optional[ApprovalStatus] = None
    approval_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    executed_actions: List[Dict[str, Any]] = Field(default_factory=list)

    # SAR / Regulatory Reporting
    sar_filed: bool = False
    sar_reference: Optional[str] = None
    sar_report: Optional[Dict[str, Any]] = None

    # Audit & Timeline
    timeline_event_count: int = 0
    case_summary_text: str = ""
    closed_at: str = Field(default_factory=now_iso)
