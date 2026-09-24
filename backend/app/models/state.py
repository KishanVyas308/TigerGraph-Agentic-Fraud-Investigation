"""Fraud Investigation State Models for LangGraph Orchestration (Layer 9).

This module defines all Pydantic v2 typed state models, domain enums, sub-models,
timeline events, and state reducer/merge logic for the TigerGraph Agentic Fraud
Investigation system.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from backend.app.utils.ids import (
    generate_action_id,
    generate_case_id,
    generate_event_id,
    generate_evidence_id,
    generate_prefixed_id,
)
from backend.app.utils.time import now_iso


# ============================================================================
# Enums
# ============================================================================

class TriggerType(str, Enum):
    """Categorization of what initiated the fraud investigation."""
    TRANSACTION_ALERT = "TRANSACTION_ALERT"
    HIGH_RISK_RULE = "HIGH_RISK_RULE"
    CUSTOMER_REPORT = "CUSTOMER_REPORT"
    ANALYST_REFERRAL = "ANALYST_REFERRAL"
    GRAPH_ANOMALY = "GRAPH_ANOMALY"


class RiskLevel(str, Enum):
    """Overall qualitative risk assessment level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceCategory(str, Enum):
    """Functional category of an evidence item."""
    TRANSACTION_BEHAVIOR = "TRANSACTION_BEHAVIOR"
    GRAPH_RELATIONSHIP = "GRAPH_RELATIONSHIP"
    DEVICE = "DEVICE"
    IDENTITY = "IDENTITY"
    MONEY_FLOW = "MONEY_FLOW"
    HISTORICAL_CASE = "HISTORICAL_CASE"
    POLICY = "POLICY"
    REGULATION = "REGULATION"
    CUSTOMER_RESPONSE = "CUSTOMER_RESPONSE"
    AUTHENTICATION = "AUTHENTICATION"
    ANALYST_INPUT = "ANALYST_INPUT"
    EXTERNAL_SIGNAL = "EXTERNAL_SIGNAL"


class EvidenceReliability(str, Enum):
    """Reliability tier of the evidence source."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"


class ActionType(str, Enum):
    """Supported candidate and final actions."""
    ALLOW_TRANSACTION = "ALLOW_TRANSACTION"
    BLOCK_TRANSACTION = "BLOCK_TRANSACTION"
    MONITOR_TRANSACTION = "MONITOR_TRANSACTION"
    MONITOR_ACCOUNT = "MONITOR_ACCOUNT"
    BLOCK_ACCOUNT = "BLOCK_ACCOUNT"
    WARN_CUSTOMER = "WARN_CUSTOMER"
    REQUEST_CUSTOMER_CONFIRMATION = "REQUEST_CUSTOMER_CONFIRMATION"
    REQUEST_STEP_UP_AUTH = "REQUEST_STEP_UP_AUTH"
    REQUEST_ANALYST_EVIDENCE = "REQUEST_ANALYST_EVIDENCE"
    ESCALATE_ANALYST = "ESCALATE_ANALYST"
    FILE_SAR = "FILE_SAR"
    CLOSE_CASE = "CLOSE_CASE"
    NO_ACTION = "NO_ACTION"


class ApprovalStatus(str, Enum):
    """Status of human approval workflow."""
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"


class ApprovalRole(str, Enum):
    """Required approval role for governed actions."""
    ANALYST = "ANALYST"
    FRAUD_ANALYST = "FRAUD_ANALYST"
    SENIOR_ANALYST = "SENIOR_ANALYST"
    SENIOR_FRAUD_ANALYST = "SENIOR_FRAUD_ANALYST"
    FRAUD_MANAGER = "FRAUD_MANAGER"
    FRAUD_SUPERVISOR = "FRAUD_SUPERVISOR"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    SYSTEM_AUTOMATIC = "SYSTEM_AUTOMATIC"


class StopReason(str, Enum):
    """Explicit reason why investigation terminated or paused."""
    SUFFICIENT_EVIDENCE_FOR_ACTION = "SUFFICIENT_EVIDENCE_FOR_ACTION"
    POLICY_MANDATED_ESCALATION = "POLICY_MANDATED_ESCALATION"
    LOW_VALUE_OF_ADDITIONAL_EVIDENCE = "LOW_VALUE_OF_ADDITIONAL_EVIDENCE"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    NO_MATERIAL_FRAUD_EVIDENCE = "NO_MATERIAL_FRAUD_EVIDENCE"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    INVESTIGATION_ERROR = "INVESTIGATION_ERROR"


class CaseStatus(str, Enum):
    """High-level status of the fraud case lifecycle."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class ExecutionMode(str, Enum):
    """Whether an action is simulated or live."""
    SIMULATED = "SIMULATED"
    LIVE = "LIVE"


# ============================================================================
# Sub-Models
# ============================================================================

class EvidenceItem(BaseModel):
    """Normalized evidence item with strict provenance tracking."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    evidence_id: str = Field(default_factory=generate_evidence_id)
    source: str
    source_reference: Optional[str] = None
    category: EvidenceCategory
    fact: str
    reliability: EvidenceReliability = EvidenceReliability.MEDIUM
    timestamp: str = Field(default_factory=now_iso)
    entity_ids: List[str] = Field(default_factory=list)
    supports_hypotheses: List[str] = Field(default_factory=list)
    contradicts_hypotheses: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("evidence_id cannot be empty")
        return v.strip()

    @field_validator("fact")
    @classmethod
    def validate_fact(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("fact cannot be empty")
        return v.strip()

    @field_validator("reliability", mode="before")
    @classmethod
    def validate_reliability(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            if v >= 0.8:
                return EvidenceReliability.HIGH
            elif v >= 0.5:
                return EvidenceReliability.MEDIUM
            else:
                return EvidenceReliability.LOW
        return v


class FraudHypothesis(BaseModel):
    """Competing fraud hypothesis assessed by the reasoning engine."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    hypothesis_id: str
    title: str = Field(default="")
    description: str = Field(default="")
    likelihood: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(default_factory=list)

    # Optional typology metadata attributes
    typology_id: Optional[str] = None
    typology_name: Optional[str] = None
    confidence: Optional[float] = None
    indicators: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "title" not in data and "typology_name" in data:
                data["title"] = data["typology_name"]
            elif "title" not in data and "typology_id" in data:
                data["title"] = data["typology_id"]
            if "description" not in data:
                data["description"] = data.get("title", "")
            if "likelihood" not in data and "confidence" in data:
                data["likelihood"] = data["confidence"]
        return data

    @field_validator("likelihood", mode="before")
    @classmethod
    def scale_percentage(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            if 1.0 < v <= 100.0:
                return float(v) / 100.0
            return float(v)
        return float(v)


class RiskAssessment(BaseModel):
    """Structured assessment keeping risk, confidence, and completeness separate."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    risk_level: RiskLevel
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_completeness: float = Field(ge=0.0, le=1.0)
    hypotheses: List[FraudHypothesis] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(default_factory=list)
    explanation: str = ""

    @field_validator("risk_score", "confidence", "evidence_completeness", mode="before")
    @classmethod
    def scale_metric(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            if 1.0 < v <= 100.0:
                return float(v) / 100.0
            return float(v)
        return float(v)


class EvidenceRequest(BaseModel):
    """Targeted evidence request generated by the Evidence Planner."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    request_id: str = Field(default_factory=lambda: generate_prefixed_id("REQ", 8))
    evidence_type: str
    target_entity_id: str
    reason: str
    expected_uncertainty_reduction: float = Field(default=0.5, ge=0.0, le=1.0)
    status: str = "PENDING"


class NextBestAction(BaseModel):
    """Recommended action with policy grounding and approval requirements."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    action_id: str = Field(default_factory=generate_action_id)
    action_type: ActionType
    target_entity_id: Optional[str] = None
    target_entity_type: Optional[str] = None
    reasoning: str
    evidence_ids: List[str] = Field(default_factory=list)
    policy_reference: Optional[str] = None
    approval_required: bool = False
    approval_role: Optional[ApprovalRole] = None
    execution_mode: ExecutionMode = ExecutionMode.SIMULATED


class ApprovalDecision(BaseModel):
    """Human analyst decision on sensitive actions."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    approval_id: str = Field(default_factory=lambda: generate_prefixed_id("APP", 8))
    action_type: ActionType
    status: ApprovalStatus
    reviewer_role: ApprovalRole
    reviewer_id: Optional[str] = None
    comments: Optional[str] = None
    timestamp: str = Field(default_factory=now_iso)
    modified_action: Optional[NextBestAction] = None


class ActionExecution(BaseModel):
    """Audit log entry for an executed or simulated action."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    execution_id: str = Field(default_factory=lambda: generate_prefixed_id("EXEC", 8))
    action_type: ActionType
    execution_mode: ExecutionMode = ExecutionMode.SIMULATED
    success: bool = True
    result: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=now_iso)


class TimelineEvent(BaseModel):
    """Timeline event capturing a state transition or material milestone."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    event_id: str = Field(default_factory=generate_event_id)
    event_type: str
    node_name: Optional[str] = None
    description: str
    timestamp: str = Field(default_factory=now_iso)
    details: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Main Model
# ============================================================================

class FraudCaseState(BaseModel):
    """Comprehensive state model for a fraud investigation case in LangGraph.

    Contains 6 functional categories:
    1. Identity (case_id, trigger_type, transaction_id, customer_id, account_ids)
    2. Evidence (transaction, graph, device, identity, policy, historical, external)
    3. Features (graph_features, behavior_features, bank_risk_score, historical_ml_score)
    4. Reasoning Output (hypotheses, risk_level, risk_score, confidence, completeness, etc.)
    5. Actions (pre/post evidence recommendations, requested/received evidence, approvals, executions)
    6. Case Control (status, iteration_count, stop_reason, timeline)
    """
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    # 1. Identity
    case_id: str = Field(default_factory=generate_case_id)
    trigger_type: TriggerType = TriggerType.TRANSACTION_ALERT
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    account_ids: List[str] = Field(default_factory=list)

    # 2. Evidence
    transaction_evidence: List[EvidenceItem] = Field(default_factory=list)
    graph_evidence: List[EvidenceItem] = Field(default_factory=list)
    device_evidence: List[EvidenceItem] = Field(default_factory=list)
    identity_evidence: List[EvidenceItem] = Field(default_factory=list)
    policy_evidence: List[EvidenceItem] = Field(default_factory=list)
    historical_case_evidence: List[EvidenceItem] = Field(default_factory=list)
    external_evidence: List[EvidenceItem] = Field(default_factory=list)

    # 3. Features
    graph_features: Dict[str, Any] = Field(default_factory=dict)
    behavior_features: Dict[str, Any] = Field(default_factory=dict)
    bank_risk_score: Optional[float] = None
    historical_ml_score: Optional[float] = None

    # 4. Reasoning Output
    hypotheses: List[FraudHypothesis] = Field(default_factory=list)
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    evidence_completeness: Optional[float] = Field(default=None)
    missing_evidence: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None

    # 5. Actions
    pre_evidence_next_best_action: Optional[NextBestAction] = None
    requested_evidence: List[EvidenceRequest] = Field(default_factory=list)
    received_evidence: List[EvidenceItem] = Field(default_factory=list)
    post_evidence_next_best_action: Optional[NextBestAction] = None
    approval_required: bool = False
    approval_status: Optional[ApprovalStatus] = None
    approval_decisions: List[ApprovalDecision] = Field(default_factory=list)
    executed_actions: List[ActionExecution] = Field(default_factory=list)
    sar_reference: Optional[str] = None
    sar_report: Optional[Dict[str, Any]] = None

    # 6. Case Control
    case_status: CaseStatus = CaseStatus.OPEN
    iteration_count: int = 0
    stop_reason: Optional[StopReason] = None
    case_summary: Optional[str] = None
    final_summary: Optional[Dict[str, Any]] = None
    is_persisted: bool = False
    case_memory_id: Optional[str] = None
    is_indexed: bool = False
    embedding_id: Optional[str] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("risk_score", "confidence", "evidence_completeness", mode="before")
    @classmethod
    def scale_state_metrics(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            if 5.0 <= v <= 100.0:
                return float(v) / 100.0
            return float(v)
        return float(v)

    @property
    def all_evidence(self) -> List[EvidenceItem]:
        """Combine all evidence items across all categories with deduplication by evidence_id."""
        seen: Set[str] = set()
        result: List[EvidenceItem] = []

        categories = [
            self.transaction_evidence,
            self.graph_evidence,
            self.device_evidence,
            self.identity_evidence,
            self.policy_evidence,
            self.historical_case_evidence,
            self.external_evidence,
            self.received_evidence,
        ]

        for cat_list in categories:
            for item in cat_list:
                if item.evidence_id not in seen:
                    seen.add(item.evidence_id)
                    result.append(item)

        return result

    def add_evidence(self, item: EvidenceItem) -> None:
        """Add an evidence item to the appropriate sub-list based on its category."""
        category_map = {
            EvidenceCategory.TRANSACTION_BEHAVIOR: self.transaction_evidence,
            EvidenceCategory.GRAPH_RELATIONSHIP: self.graph_evidence,
            EvidenceCategory.MONEY_FLOW: self.graph_evidence,
            EvidenceCategory.DEVICE: self.device_evidence,
            EvidenceCategory.IDENTITY: self.identity_evidence,
            EvidenceCategory.POLICY: self.policy_evidence,
            EvidenceCategory.REGULATION: self.policy_evidence,
            EvidenceCategory.HISTORICAL_CASE: self.historical_case_evidence,
            EvidenceCategory.CUSTOMER_RESPONSE: self.external_evidence,
            EvidenceCategory.AUTHENTICATION: self.external_evidence,
            EvidenceCategory.ANALYST_INPUT: self.external_evidence,
            EvidenceCategory.EXTERNAL_SIGNAL: self.external_evidence,
        }

        # Value can be Enum or str string value
        cat_enum = item.category
        if isinstance(cat_enum, str):
            try:
                cat_enum = EvidenceCategory(cat_enum)
            except ValueError:
                cat_enum = EvidenceCategory.EXTERNAL_SIGNAL

        target_list = category_map.get(cat_enum, self.external_evidence)

        # Check for duplicate by evidence_id
        if not any(e.evidence_id == item.evidence_id for e in target_list):
            target_list.append(item)

    def add_timeline_event(
        self,
        event_type: str,
        description: str,
        node_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> TimelineEvent:
        """Create and append a new TimelineEvent."""
        event = TimelineEvent(
            event_type=event_type,
            node_name=node_name,
            description=description,
            details=details or {},
        )
        self.timeline.append(event)
        return event

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serializable dictionary representation."""
        return self.model_dump(mode="json")


# ============================================================================
# State Reducer / Merge Semantics
# ============================================================================

def merge_fraud_case_state(
    current_state: FraudCaseState,
    patch: Union[Dict[str, Any], FraudCaseState],
) -> FraudCaseState:
    """LangGraph state reducer: merges node update patch into current FraudCaseState.

    Rules:
    - Lists of evidence items are deduplicated and categorized.
    - Lists of events (timeline), requests, decisions, executions are appended with deduplication.
    - Feature dictionaries are merged key-by-key.
    - Scalar fields (risk_level, confidence, status, actions) are updated when non-None.
    """
    if isinstance(patch, FraudCaseState):
        patch_dict = patch.model_dump(mode="python")
    else:
        patch_dict = patch

    # Create shallow copy of current state
    updated_state = current_state.model_copy(deep=True)

    # 1. Update identity fields if provided
    for field in ["transaction_id", "customer_id"]:
        if patch_dict.get(field) is not None:
            setattr(updated_state, field, patch_dict[field])

    if "account_ids" in patch_dict and patch_dict["account_ids"]:
        existing = set(updated_state.account_ids)
        for acc in patch_dict["account_ids"]:
            if acc not in existing:
                updated_state.account_ids.append(acc)
                existing.add(acc)

    # 2. Add evidence items
    evidence_fields = [
        "transaction_evidence",
        "graph_evidence",
        "device_evidence",
        "identity_evidence",
        "policy_evidence",
        "historical_case_evidence",
        "external_evidence",
    ]

    for ev_field in evidence_fields:
        if ev_field in patch_dict and patch_dict[ev_field]:
            for item_raw in patch_dict[ev_field]:
                if isinstance(item_raw, dict):
                    ev_item = EvidenceItem.model_validate(item_raw)
                else:
                    ev_item = item_raw
                updated_state.add_evidence(ev_item)

    # Ingest received_evidence items
    if "received_evidence" in patch_dict and patch_dict["received_evidence"]:
        existing_rec_ids = {e.evidence_id for e in updated_state.received_evidence}
        for item_raw in patch_dict["received_evidence"]:
            ev_item = (
                item_raw
                if isinstance(item_raw, EvidenceItem)
                else EvidenceItem.model_validate(item_raw)
            )
            if ev_item.evidence_id not in existing_rec_ids:
                updated_state.received_evidence.append(ev_item)
                existing_rec_ids.add(ev_item.evidence_id)
            updated_state.add_evidence(ev_item)

    # If general 'new_evidence' list supplied in patch
    if "new_evidence" in patch_dict and patch_dict["new_evidence"]:
        for item_raw in patch_dict["new_evidence"]:
            if isinstance(item_raw, dict):
                ev_item = EvidenceItem.model_validate(item_raw)
            else:
                ev_item = item_raw
            updated_state.add_evidence(ev_item)

    # 3. Features merging
    if "graph_features" in patch_dict and patch_dict["graph_features"]:
        updated_state.graph_features.update(patch_dict["graph_features"])

    if "behavior_features" in patch_dict and patch_dict["behavior_features"]:
        updated_state.behavior_features.update(patch_dict["behavior_features"])

    if patch_dict.get("bank_risk_score") is not None:
        updated_state.bank_risk_score = patch_dict["bank_risk_score"]

    if patch_dict.get("historical_ml_score") is not None:
        updated_state.historical_ml_score = patch_dict["historical_ml_score"]

    # 4. Reasoning Output updates
    if "hypotheses" in patch_dict and patch_dict["hypotheses"] is not None:
        raw_hyp = patch_dict["hypotheses"]
        updated_state.hypotheses = [
            h if isinstance(h, FraudHypothesis) else FraudHypothesis.model_validate(h)
            for h in raw_hyp
        ]

    for scalar_reasoning in [
        "risk_level",
        "risk_score",
        "confidence",
        "evidence_completeness",
        "explanation",
    ]:
        if patch_dict.get(scalar_reasoning) is not None:
            setattr(updated_state, scalar_reasoning, patch_dict[scalar_reasoning])

    if updated_state.risk_score is None and updated_state.risk_level is not None:
        lvl = updated_state.risk_level.value if hasattr(updated_state.risk_level, "value") else str(updated_state.risk_level)
        defaults = {"CRITICAL": 0.90, "HIGH": 0.80, "MEDIUM": 0.50, "LOW": 0.15}
        if lvl in defaults:
            updated_state.risk_score = defaults[lvl]

    for list_reasoning in ["missing_evidence", "supporting_evidence_ids", "contradictory_evidence_ids"]:
        if list_reasoning in patch_dict and patch_dict[list_reasoning] is not None:
            setattr(updated_state, list_reasoning, patch_dict[list_reasoning])

    # 5. Actions updates
    if patch_dict.get("pre_evidence_next_best_action") is not None:
        raw_act = patch_dict["pre_evidence_next_best_action"]
        updated_state.pre_evidence_next_best_action = (
            raw_act if isinstance(raw_act, NextBestAction) else NextBestAction.model_validate(raw_act)
        )

    if patch_dict.get("post_evidence_next_best_action") is not None:
        raw_act = patch_dict["post_evidence_next_best_action"]
        updated_state.post_evidence_next_best_action = (
            raw_act if isinstance(raw_act, NextBestAction) else NextBestAction.model_validate(raw_act)
        )

    if patch_dict.get("approval_required") is not None:
        updated_state.approval_required = bool(patch_dict["approval_required"])

    if patch_dict.get("approval_status") is not None:
        updated_state.approval_status = patch_dict["approval_status"]

    if "requested_evidence" in patch_dict and patch_dict["requested_evidence"]:
        existing_req_ids = {r.request_id for r in updated_state.requested_evidence}
        for req_raw in patch_dict["requested_evidence"]:
            req_item = req_raw if isinstance(req_raw, EvidenceRequest) else EvidenceRequest.model_validate(req_raw)
            if req_item.request_id not in existing_req_ids:
                updated_state.requested_evidence.append(req_item)
                existing_req_ids.add(req_item.request_id)

    if "approval_decisions" in patch_dict and patch_dict["approval_decisions"]:
        existing_app_ids = {a.approval_id for a in updated_state.approval_decisions}
        for app_raw in patch_dict["approval_decisions"]:
            app_item = app_raw if isinstance(app_raw, ApprovalDecision) else ApprovalDecision.model_validate(app_raw)
            if app_item.approval_id not in existing_app_ids:
                updated_state.approval_decisions.append(app_item)
                existing_app_ids.add(app_item.approval_id)

    if "executed_actions" in patch_dict and patch_dict["executed_actions"]:
        existing_exec_ids = {e.execution_id for e in updated_state.executed_actions}
        for exec_raw in patch_dict["executed_actions"]:
            exec_item = exec_raw if isinstance(exec_raw, ActionExecution) else ActionExecution.model_validate(exec_raw)
            if exec_item.execution_id not in existing_exec_ids:
                updated_state.executed_actions.append(exec_item)
                existing_exec_ids.add(exec_item.execution_id)

    if patch_dict.get("sar_reference") is not None:
        updated_state.sar_reference = patch_dict["sar_reference"]

    if patch_dict.get("sar_report") is not None:
        updated_state.sar_report = patch_dict["sar_report"]

    # 6. Case Control updates
    if patch_dict.get("case_status") is not None:
        updated_state.case_status = patch_dict["case_status"]

    if patch_dict.get("iteration_count") is not None:
        updated_state.iteration_count = patch_dict["iteration_count"]

    if patch_dict.get("stop_reason") is not None:
        updated_state.stop_reason = patch_dict["stop_reason"]

    if patch_dict.get("case_summary") is not None:
        updated_state.case_summary = patch_dict["case_summary"]

    if patch_dict.get("final_summary") is not None:
        updated_state.final_summary = patch_dict["final_summary"]

    if patch_dict.get("is_persisted") is not None:
        updated_state.is_persisted = bool(patch_dict["is_persisted"])

    if patch_dict.get("case_memory_id") is not None:
        updated_state.case_memory_id = patch_dict["case_memory_id"]

    if patch_dict.get("is_indexed") is not None:
        updated_state.is_indexed = bool(patch_dict["is_indexed"])

    if patch_dict.get("embedding_id") is not None:
        updated_state.embedding_id = patch_dict["embedding_id"]

    if "timeline" in patch_dict and patch_dict["timeline"]:
        existing_evt_ids = {t.event_id for t in updated_state.timeline}
        for evt_raw in patch_dict["timeline"]:
            evt_item = evt_raw if isinstance(evt_raw, TimelineEvent) else TimelineEvent.model_validate(evt_raw)
            if evt_item.event_id not in existing_evt_ids:
                updated_state.timeline.append(evt_item)
                existing_evt_ids.add(evt_item.event_id)

    if "metadata" in patch_dict and patch_dict["metadata"]:
        updated_state.metadata.update(patch_dict["metadata"])

    return updated_state
