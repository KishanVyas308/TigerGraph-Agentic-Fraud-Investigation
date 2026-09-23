"""Evidence Planner / Value of Information Node (Layer 18).

When evidence is evaluated as insufficient by the Sufficiency Gate, the Evidence Planner
selects the smallest, highest-value evidence request using an explainable Value of Information (VoI)
approximation: `(expected_uncertainty_reduction * expected_decision_impact) / (cost_friction + 0.1)`.

STRICT RULES (AGENTS.md & GEMINI.md):
1. Select the smallest useful evidence request (CUSTOMER_CONFIRMATION, STEP_UP_AUTH, ANALYST_INFORMATION, APPROVED_EXTERNAL_CHECK).
2. Preserves the current pre-evidence recommendation in `state.pre_evidence_next_best_action`.
3. Records why evidence is insufficient, what evidence is being requested, and what decision the evidence could change.
4. Increments `iteration_count` and updates `case_status = AWAITING_EVIDENCE`.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionType,
    CaseStatus,
    EvidenceRequest,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
)
from backend.app.utils.ids import generate_prefixed_id
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.evidence_planner")


class CandidateEvidenceRequest(BaseModel):
    """Candidate evidence request evaluated by the Value of Information model."""

    model_config = ConfigDict(extra="ignore")

    evidence_type: str = Field(description="Type: CUSTOMER_CONFIRMATION, STEP_UP_AUTH, ANALYST_INFORMATION, APPROVED_EXTERNAL_CHECK.")
    target_entity_id: str
    target_entity_type: str = "TRANSACTION"
    reason: str
    decision_impact: float = Field(ge=0.0, le=1.0, description="Expected decision impact [0.0, 1.0].")
    uncertainty_reduction: float = Field(ge=0.0, le=1.0, description="Expected uncertainty reduction [0.0, 1.0].")
    cost_friction: float = Field(ge=0.01, le=10.0, description="Customer friction / latency cost weight.")
    decision_could_change: str = Field(description="What action change this evidence could trigger.")

    @property
    def voi_score(self) -> float:
        """Calculate Value of Information (VoI) score."""
        return (self.uncertainty_reduction * self.decision_impact) / (self.cost_friction + 0.1)


class EvidencePlannerNode:
    """Evidence Planner selecting highest VoI evidence request."""

    def __init__(self, default_cost_friction: float = 1.0):
        self.default_cost_friction = default_cost_friction

    def plan_evidence_request(self, state: FraudCaseState) -> CandidateEvidenceRequest:
        """Select highest VoI evidence request based on state missing_evidence and NBA."""
        missing_items = state.missing_evidence or []
        missing_text = " ".join(missing_items).upper()

        current_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action
        nba_action = current_nba.action_type if current_nba else ActionType.NO_ACTION
        nba_val = nba_action.value if hasattr(nba_action, "value") else str(nba_action)

        target_entity = state.transaction_id or state.customer_id or (state.account_ids[0] if state.account_ids else "UNKNOWN")

        candidates: List[CandidateEvidenceRequest] = []

        # Candidate 1: Customer Confirmation (SMS/Push verification)
        if "CUSTOMER" in missing_text or "CONFIRM" in missing_text or "AUTHORIZ" in missing_text or nba_val in ["BLOCK_TRANSACTION", "MONITOR_TRANSACTION"]:
            candidates.append(CandidateEvidenceRequest(
                evidence_type="CUSTOMER_CONFIRMATION",
                target_entity_id=target_entity,
                target_entity_type="TRANSACTION",
                reason="Request explicit customer confirmation to verify if transaction was authorized.",
                decision_impact=0.90,
                uncertainty_reduction=0.85,
                cost_friction=1.5,  # Low-medium friction (SMS response)
                decision_could_change="Clear transaction to ALLOW_TRANSACTION if confirmed, or BLOCK_ACCOUNT if denied.",
            ))

        # Candidate 2: Step-Up Authentication (2FA / Biometrics)
        if "AUTH" in missing_text or "STEP_UP" in missing_text or "DEVICE" in missing_text:
            candidates.append(CandidateEvidenceRequest(
                evidence_type="STEP_UP_AUTH",
                target_entity_id=state.customer_id or target_entity,
                target_entity_type="CUSTOMER",
                reason="Request step-up 2FA/biometric authentication for unverified device or identity.",
                decision_impact=0.85,
                uncertainty_reduction=0.80,
                cost_friction=2.0,  # Medium customer friction
                decision_could_change="Allow transaction if 2FA passes, or block account if 2FA fails.",
            ))

        # Candidate 3: External Approved Check (CRM / IP / Device Reputation)
        if "EXTERNAL" in missing_text or "REPUTATION" in missing_text or "CRM" in missing_text:
            candidates.append(CandidateEvidenceRequest(
                evidence_type="APPROVED_EXTERNAL_CHECK",
                target_entity_id=target_entity,
                target_entity_type="EXTERNAL_SERVICE",
                reason="Query internal CRM history and approved external reputation services.",
                decision_impact=0.70,
                uncertainty_reduction=0.60,
                cost_friction=0.5,  # Low friction (automated API call)
                decision_could_change="Adjust historical risk confidence without customer interaction.",
            ))

        # Candidate 4: Analyst Information / Manual Verification
        if "ANALYST" in missing_text or "MANUAL" in missing_text or nba_val in ["BLOCK_ACCOUNT", "FILE_SAR"]:
            candidates.append(CandidateEvidenceRequest(
                evidence_type="ANALYST_INFORMATION",
                target_entity_id=state.case_id,
                target_entity_type="CASE",
                reason="Request manual analyst check of customer documentation and out-of-band context.",
                decision_impact=0.95,
                uncertainty_reduction=0.90,
                cost_friction=4.0,  # High friction (human analyst time)
                decision_could_change="Confirm account block or override to clear case.",
            ))

        # Fallback Candidate if no specific candidate matched
        if not candidates:
            candidates.append(CandidateEvidenceRequest(
                evidence_type="CUSTOMER_CONFIRMATION",
                target_entity_id=target_entity,
                target_entity_type="TRANSACTION",
                reason="Request customer confirmation as primary uncertainty reduction step.",
                decision_impact=0.80,
                uncertainty_reduction=0.75,
                cost_friction=1.5,
                decision_could_change="Confirm authorization or escalate fraud investigation.",
            ))

        # Sort candidates by VoI score descending and pick best candidate
        candidates.sort(key=lambda c: c.voi_score, reverse=True)
        best = candidates[0]

        logger.info(
            "Evidence Planner selected request type '%s' (VoI score: %.2f) for target %s",
            best.evidence_type,
            best.voi_score,
            best.target_entity_id,
        )

        return best

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Execute Evidence Planner node, producing state update patch dictionary."""
        plan = self.plan_evidence_request(state)

        # Create structured EvidenceRequest
        req_id = generate_prefixed_id("REQ", 8)
        ev_request = EvidenceRequest(
            request_id=req_id,
            evidence_type=plan.evidence_type,
            target_entity_id=plan.target_entity_id,
            reason=plan.reason,
            expected_uncertainty_reduction=plan.uncertainty_reduction,
            status="PENDING",
        )

        # Build update patch
        patch: Dict[str, Any] = {
            "requested_evidence": [ev_request.model_dump()],
            "case_status": CaseStatus.AWAITING_EVIDENCE.value,
            "iteration_count": state.iteration_count + 1,
        }

        # Explicitly preserve pre-evidence recommendation if not set
        if state.pre_evidence_next_best_action is not None and state.pre_evidence_next_best_action:
            patch["pre_evidence_next_best_action"] = state.pre_evidence_next_best_action.model_dump()

        # Add timeline event with provenance
        event = TimelineEvent(
            event_type="EVIDENCE_REQUESTED",
            node_name="evidence_planner",
            description=(
                f"Requested evidence '{plan.evidence_type}' for target '{plan.target_entity_id}' "
                f"(VoI score: {plan.voi_score:.2f}). Reason: {plan.reason}"
            ),
            details={
                "request_id": req_id,
                "evidence_type": plan.evidence_type,
                "target_entity_id": plan.target_entity_id,
                "voi_score": round(plan.voi_score, 4),
                "decision_impact": plan.decision_impact,
                "uncertainty_reduction": plan.uncertainty_reduction,
                "cost_friction": plan.cost_friction,
                "decision_could_change": plan.decision_could_change,
            },
        )
        patch["timeline"] = [event.model_dump()]

        logger.info(
            "Evidence Planner node generated request %s (%s) for Case %s. Iteration updated to %d.",
            req_id,
            plan.evidence_type,
            state.case_id,
            patch["iteration_count"],
        )

        return patch
