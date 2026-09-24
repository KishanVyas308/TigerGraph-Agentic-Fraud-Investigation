"""Base Action Execution and Simulation Interfaces (Layer 21).

Defines the core contracts, result models, and safety disclaimers for simulated
banking action execution in the TigerGraph Agentic Fraud Investigation system.
All operations are explicitly tagged as SIMULATED to ensure no real banking
systems are impacted or implied to be altered.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionExecution,
    ActionType,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
)
from backend.app.utils.ids import generate_prefixed_id
from backend.app.utils.time import now_iso

SIMULATION_DISCLAIMER: str = (
    "Simulated execution in demo environment; no real banking systems modified."
)


class SimulatedActionResult(BaseModel):
    """Result of a simulated operational action or evidence ingestion."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    execution_id: str = Field(
        default_factory=lambda: generate_prefixed_id("SIM", 8)
    )
    action_type: ActionType
    execution_mode: ExecutionMode = ExecutionMode.SIMULATED
    success: bool = True
    target_entity_id: Optional[str] = None
    target_entity_type: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = SIMULATION_DISCLAIMER
    timestamp: str = Field(default_factory=now_iso)

    @property
    def result(self) -> Dict[str, Any]:
        """Convenience alias for details payload."""
        return self.details


class BaseActionExecutor(ABC):
    """Abstract base class for simulated banking action execution."""

    disclaimer: str = SIMULATION_DISCLAIMER

    @abstractmethod
    def execute(
        self,
        action: NextBestAction,
        state: FraudCaseState,
    ) -> Tuple[ActionExecution, TimelineEvent, Dict[str, Any]]:
        """Execute or simulate the permitted action against the current case state.

        Args:
            action: The authorized next-best action to execute.
            state: The current fraud case state.

        Returns:
            Tuple containing:
            - ActionExecution audit record (execution_mode = SIMULATED)
            - TimelineEvent capturing the simulated action milestone
            - Dictionary of execution output details
        """
        pass
