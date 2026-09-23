"""Evidence Sufficiency Engine Gate Node (Layer 17).

Evaluates whether an investigation has enough evidence to take a defensible action,
requires additional evidence gathering, mandates human escalation, or can close as no material fraud.

STRICT RULES (AGENTS.md & GEMINI.md):
1. Sufficiency gate MUST NOT be controlled by LLM intuition alone.
2. Uses deterministic code evaluating: risk level/score, confidence, evidence completeness, missing evidence list, action severity, policy constraints, and iteration count.
3. Bounded loops: Enforces configurable `max_iterations` to prevent infinite tool loops.
4. Possible outcomes:
   - `ACT`: Evidence is sufficient -> proceed to deterministic policy gate.
   - `GATHER_MORE_EVIDENCE`: Evidence is insufficient & missing high-value evidence -> proceed to Evidence Planner.
   - `ESCALATE`: Policy-mandated escalation or high risk with unresolved uncertainty -> route to human analyst.
   - `STOP_NO_MATERIAL_FRAUD`: Low risk + high confidence + high completeness -> close case/allow transaction.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionType,
    CaseStatus,
    FraudCaseState,
    RiskLevel,
    StopReason,
    TimelineEvent,
)
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.sufficiency_gate")


class SufficiencyOutcome(str, Enum):
    """Deterministic routing outcomes from the Evidence Sufficiency Gate."""

    ACT = "ACT"
    GATHER_MORE_EVIDENCE = "GATHER_MORE_EVIDENCE"
    ESCALATE = "ESCALATE"
    STOP_NO_MATERIAL_FRAUD = "STOP_NO_MATERIAL_FRAUD"


class SufficiencyGateResult(BaseModel):
    """Result payload from Sufficiency Gate evaluation."""

    model_config = ConfigDict(extra="ignore")

    outcome: SufficiencyOutcome = Field(
        description="Deterministic routing decision."
    )
    reason: str = Field(
        description="Auditable justification for the sufficiency decision."
    )
    stop_reason: Optional[StopReason] = Field(
        default=None,
        description="Explicit stop reason if investigation completes or pauses.",
    )
    should_loop: bool = Field(
        default=False,
        description="True if workflow should loop back for more evidence.",
    )


class EvidenceSufficiencyGate:
    """Deterministic Evidence Sufficiency Gate service."""

    def __init__(
        self,
        min_completeness_threshold: float = 0.70,
        min_confidence_threshold: float = 0.75,
        max_iterations: int = 2,
    ):
        self.min_completeness = min_completeness_threshold
        self.min_confidence = min_confidence_threshold
        self.max_iterations = max_iterations

    def evaluate(self, state: FraudCaseState) -> SufficiencyGateResult:
        """Evaluate FraudCaseState against deterministic sufficiency rules."""
        iteration = state.iteration_count
        risk_lvl = state.risk_level
        risk_score = state.risk_score or 0.5
        confidence = state.confidence if state.confidence is not None else 0.5
        completeness = state.evidence_completeness if state.evidence_completeness is not None else 0.5
        missing_evidence = state.missing_evidence or []

        candidate_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action
        action_type = candidate_nba.action_type if candidate_nba else ActionType.NO_ACTION
        action_val = action_type.value if hasattr(action_type, "value") else str(action_type)

        # Severe actions requiring high evidence completeness
        severe_actions = {
            ActionType.BLOCK_ACCOUNT.value,
            ActionType.BLOCK_TRANSACTION.value,
            ActionType.FILE_SAR.value,
        }

        # Rule 1: Bounded loop limit reached
        if iteration >= self.max_iterations:
            logger.info("Case %s reached max_iterations (%d); stopping evidence gathering loop.", state.case_id, iteration)
            if completeness < self.min_completeness and action_val in severe_actions:
                return SufficiencyGateResult(
                    outcome=SufficiencyOutcome.ESCALATE,
                    reason=f"Reached max iterations ({iteration}) with incomplete evidence for severe action '{action_val}'. Mandating analyst escalation.",
                    stop_reason=StopReason.MAX_ITERATIONS_REACHED,
                    should_loop=False,
                )
            else:
                return SufficiencyGateResult(
                    outcome=SufficiencyOutcome.ACT,
                    reason=f"Reached max iterations ({iteration}). Proceeding with current best action '{action_val}'.",
                    stop_reason=StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
                    should_loop=False,
                )

        # Rule 2: Low Risk + High Confidence + High Completeness -> Stop No Material Fraud
        is_low_risk = (risk_lvl == RiskLevel.LOW or (isinstance(risk_lvl, str) and risk_lvl == "LOW")) or risk_score < 0.35
        if is_low_risk and confidence >= self.min_confidence and completeness >= self.min_completeness:
            return SufficiencyGateResult(
                outcome=SufficiencyOutcome.STOP_NO_MATERIAL_FRAUD,
                reason=f"Low risk (score: {risk_score:.2f}) with high confidence ({confidence:.2f}) and completeness ({completeness:.2f}). No material fraud evidence.",
                stop_reason=StopReason.NO_MATERIAL_FRAUD_EVIDENCE,
                should_loop=False,
            )

        # Rule 3: Missing high-value evidence & low completeness & iteration available -> Gather More Evidence
        has_missing_reqs = len(missing_evidence) > 0
        is_incomplete = completeness < self.min_completeness or confidence < self.min_confidence

        if is_incomplete and has_missing_reqs:
            return SufficiencyGateResult(
                outcome=SufficiencyOutcome.GATHER_MORE_EVIDENCE,
                reason=(
                    f"Evidence incomplete (completeness: {completeness:.2f} < {self.min_completeness:.2f}, "
                    f"confidence: {confidence:.2f} < {self.min_confidence:.2f}). "
                    f"Missing high-value evidence: {', '.join(missing_evidence[:2])}."
                ),
                stop_reason=None,
                should_loop=True,
            )

        # Rule 4: High/Critical Risk with High Completeness & Confidence -> Act
        if completeness >= self.min_completeness and confidence >= self.min_confidence:
            return SufficiencyGateResult(
                outcome=SufficiencyOutcome.ACT,
                reason=f"Sufficient evidence completeness ({completeness:.2f}) and confidence ({confidence:.2f}) for action '{action_val}'.",
                stop_reason=StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
                should_loop=False,
            )

        # Rule 5: Severe action with insufficient evidence & no clear missing items -> Escalate
        if action_val in severe_actions and is_incomplete:
            return SufficiencyGateResult(
                outcome=SufficiencyOutcome.ESCALATE,
                reason=f"Severe action '{action_val}' requested with low confidence ({confidence:.2f})/completeness ({completeness:.2f}). Escalating to human analyst.",
                stop_reason=StopReason.POLICY_MANDATED_ESCALATION,
                should_loop=False,
            )

        # Rule 6: Default fallback -> Act with current action
        return SufficiencyGateResult(
            outcome=SufficiencyOutcome.ACT,
            reason=f"Proceeding to policy check for action '{action_val}'.",
            stop_reason=StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION,
            should_loop=False,
        )

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Execute sufficiency gate evaluation and return state patch dict."""
        result = self.evaluate(state)

        patch: Dict[str, Any] = {
            "sufficiency_outcome": result.outcome.value,
        }

        if result.stop_reason is not None:
            patch["stop_reason"] = result.stop_reason.value if hasattr(result.stop_reason, "value") else str(result.stop_reason)

        if result.outcome == SufficiencyOutcome.STOP_NO_MATERIAL_FRAUD:
            patch["case_status"] = CaseStatus.COMPLETED.value

        event = TimelineEvent(
            event_type="SUFFICIENCY_EVALUATED",
            node_name="sufficiency_gate",
            description=f"Evidence Sufficiency Gate outcome: {result.outcome.value} — {result.reason}",
            details={
                "outcome": result.outcome.value,
                "should_loop": result.should_loop,
                "stop_reason": patch.get("stop_reason"),
            },
        )
        patch["timeline"] = [event.model_dump()]

        logger.info("Sufficiency Gate for Case %s: Outcome=%s (Should Loop: %s)", state.case_id, result.outcome.value, result.should_loop)
        return patch
