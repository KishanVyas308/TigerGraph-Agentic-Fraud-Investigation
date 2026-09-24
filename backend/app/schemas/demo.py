"""Demo Schemas (Layer 40).

Defines typed Pydantic models for deterministic local demo scenarios:
- Demo 1: Graph-Detected Fraud Ring
- Demo 2: Uncertain Case with Evidence Loop & Customer Confirmation
- Demo 3: Sensitive Action with Policy Gate & Human Approval
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.utils.time import now_iso


class DemoScenarioId(str, Enum):
    """Identifier for the 3 canonical local demo scenarios."""

    FRAUD_NETWORK = "1"
    UNCERTAIN_CASE = "2"
    HUMAN_APPROVAL = "3"


class DemoScenarioMetadata(BaseModel):
    """Metadata describing a demo scenario for UI selection and logging."""

    model_config = ConfigDict(extra="ignore")

    scenario_id: DemoScenarioId
    name: str
    typology: str
    summary: str
    key_highlights: List[str] = Field(default_factory=list)


class DemoExecutionStep(BaseModel):
    """Single step in a demo scenario execution flow."""

    model_config = ConfigDict(extra="ignore")

    step_number: int
    title: str
    description: str
    node_name: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class DemoScenarioResult(BaseModel):
    """Execution results and timeline for a single completed demo scenario."""

    model_config = ConfigDict(extra="ignore")

    scenario_id: DemoScenarioId
    name: str
    case_id: str
    initial_risk: Optional[str] = None
    final_risk: str
    pre_evidence_action: Optional[str] = None
    post_evidence_action: str
    approval_required: bool = False
    approval_status: Optional[str] = None
    action_executed: Optional[str] = None
    sar_generated: bool = False
    is_persisted: bool = True
    stop_reason: str
    steps: List[DemoExecutionStep] = Field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = True


class DemoSuiteReport(BaseModel):
    """Consolidated summary report after executing all local demo scenarios."""

    model_config = ConfigDict(extra="ignore")

    suite_run_id: str
    executed_at: str = Field(default_factory=now_iso)
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    scenarios: Dict[str, DemoScenarioResult] = Field(default_factory=dict)
    all_passed: bool = True
