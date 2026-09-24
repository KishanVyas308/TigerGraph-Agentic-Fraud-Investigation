"""Evaluation Schemas (Layer 39).

Defines typed Pydantic models for historical case evaluation, ablation modes,
classification performance metrics, typology match rates, action agreement,
evidence efficiency, and latency profiling.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.utils.time import now_iso


class AblationMode(str, Enum):
    """Authoritative ablation modes defined in Layer 39 specifications."""

    A = "A"  # Bank risk score only
    B = "B"  # Bank risk score + transaction behavior
    C = "C"  # Graph features + transaction behavior
    D = "D"  # Full system: Graph + behavior + case memory + policy GraphRAG


class ClassificationMetrics(BaseModel):
    """Binary fraud vs. cleared classification performance metrics."""

    model_config = ConfigDict(extra="ignore")

    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0


class TypologyMetrics(BaseModel):
    """Typology pattern identification accuracy and match rates."""

    model_config = ConfigDict(extra="ignore")

    match_rate: float = 0.0
    total_labeled: int = 0
    matched_count: int = 0
    per_typology: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ActionAgreementMetrics(BaseModel):
    """Agreement between recommended actions and historical bank/analyst actions."""

    model_config = ConfigDict(extra="ignore")

    agreement_rate: float = 0.0
    total_cases: int = 0
    agreed_cases: int = 0
    action_counts: Dict[str, int] = Field(default_factory=dict)


class EvidenceEfficiencyMetrics(BaseModel):
    """Evidence gathering behavior and unnecessary evidence request rates."""

    model_config = ConfigDict(extra="ignore")

    evidence_request_rate: float = 0.0
    total_cases: int = 0
    cases_with_evidence_requested: int = 0
    unnecessary_request_rate: float = 0.0
    avg_evidence_count: float = 0.0


class LatencyMetrics(BaseModel):
    """Latency profile across graph queries, LLM reasoning, and end-to-end execution."""

    model_config = ConfigDict(extra="ignore")

    avg_total_latency_ms: float = 0.0
    avg_graph_latency_ms: float = 0.0
    avg_llm_latency_ms: float = 0.0
    p95_total_latency_ms: float = 0.0


class CaseEvaluationResult(BaseModel):
    """Detailed evaluation result for an individual historical case under an ablation mode."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    transaction_id: str
    ground_truth_outcome: str  # FRAUD_CONFIRMED or FALSE_POSITIVE_CLEARED
    ground_truth_typology: Optional[str] = None
    ground_truth_action: str
    predicted_outcome: str
    predicted_typology: Optional[str] = None
    predicted_action: str
    risk_score: float = 0.0
    risk_level: str = "LOW"
    confidence: float = 0.0
    evidence_completeness: float = 0.0
    is_outcome_correct: bool = False
    is_typology_correct: bool = False
    is_action_agreed: bool = False
    evidence_requested: bool = False
    unnecessary_evidence_requested: bool = False
    total_duration_ms: float = 0.0
    graph_duration_ms: float = 0.0
    llm_duration_ms: float = 0.0


class AblationResult(BaseModel):
    """Aggregated evaluation results for a single ablation configuration."""

    model_config = ConfigDict(extra="ignore")

    mode: AblationMode
    mode_name: str
    description: str
    cases_evaluated: int
    classification: ClassificationMetrics
    typology: TypologyMetrics
    action_agreement: ActionAgreementMetrics
    evidence_efficiency: EvidenceEfficiencyMetrics
    latency: LatencyMetrics
    case_results: List[CaseEvaluationResult] = Field(default_factory=list)


class HistoricalEvaluationReport(BaseModel):
    """Comprehensive evaluation report covering all selected ablation modes."""

    model_config = ConfigDict(extra="ignore")

    evaluation_id: str
    evaluated_at: str = Field(default_factory=now_iso)
    dataset_file: str
    total_cases_available: int
    limit_applied: Optional[int] = None
    ablations: Dict[str, AblationResult] = Field(default_factory=dict)
    comparative_summary: List[Dict[str, Any]] = Field(default_factory=list)
