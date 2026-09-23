"""Case Finalizer Service (Layer 23).

Deterministic finalization logic for fraud investigations:
- Validates case integrity (metrics, next-best actions, approvals, SAR status).
- Enforces explicit StopReasons (never closes silently without one):
  * SUFFICIENT_EVIDENCE_FOR_ACTION
  * POLICY_MANDATED_ESCALATION
  * LOW_VALUE_OF_ADDITIONAL_EVIDENCE
  * AWAITING_HUMAN_REVIEW
  * NO_MATERIAL_FRAUD_EVIDENCE
- Preserves pre-evidence and post-evidence recommendations.
- Generates human-auditable text summaries and structured FinalCaseSummary outputs.
- Transitions lifecycle case status to COMPLETED (or pauses at AWAITING_APPROVAL).
"""

from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.state import (
    ActionType,
    CaseStatus,
    FraudCaseState,
    NextBestAction,
    StopReason,
    TimelineEvent,
)
from backend.app.schemas.case import FinalCaseSummary, ValidationResult
from backend.app.utils.ids import generate_event_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("services.finalizer")


class CaseFinalizer:
    """Deterministic investigation finalization and stop condition validator."""

    def validate_case_integrity(self, state: FraudCaseState) -> ValidationResult:
        """Validate case data completeness, action clearance, and governance invariants."""
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Action recommendation presence
        if not state.post_evidence_next_best_action and not state.pre_evidence_next_best_action:
            errors.append("Case has no recommended next-best action (pre or post evidence).")

        # 2. Sensitive action approval check
        current_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action
        if state.approval_required and not state.approval_decisions:
            if state.case_status != CaseStatus.AWAITING_APPROVAL:
                errors.append(
                    "Action requires human approval, but no approval decision was recorded "
                    "and status is not AWAITING_APPROVAL."
                )

        # 3. Metric bounds validation
        if state.risk_score is not None and not (0.0 <= state.risk_score <= 1.0):
            errors.append(f"Risk score {state.risk_score} is out of bounds [0.0, 1.0].")
        if state.confidence is not None and not (0.0 <= state.confidence <= 1.0):
            errors.append(f"Confidence {state.confidence} is out of bounds [0.0, 1.0].")
        if state.evidence_completeness is not None and not (0.0 <= state.evidence_completeness <= 1.0):
            errors.append(f"Evidence completeness {state.evidence_completeness} is out of bounds [0.0, 1.0].")

        # 4. SAR action alignment
        if current_nba and current_nba.action_type == ActionType.FILE_SAR:
            if not state.sar_reference and not state.sar_report:
                warnings.append("Action is FILE_SAR but no SAR report reference was attached.")

        # 5. Completeness warnings
        if not state.hypotheses:
            warnings.append("Case finalized without any evaluated fraud hypotheses.")
        if state.evidence_completeness is not None and state.evidence_completeness < 0.30:
            warnings.append(f"Low evidence completeness ({state.evidence_completeness:.2f}) upon finalization.")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def determine_stop_reason(
        self,
        state: FraudCaseState,
        explicit_reason: Optional[StopReason] = None,
    ) -> StopReason:
        """Deterministically resolve an explicit StopReason for the case.

        Never allows silent completion without an auditable reason.
        """
        # If explicitly passed or already present in state, validate and return
        if explicit_reason:
            return explicit_reason
        if state.stop_reason:
            if isinstance(state.stop_reason, StopReason):
                return state.stop_reason
            try:
                return StopReason(state.stop_reason)
            except ValueError:
                pass

        # 1. Awaiting human review
        if state.approval_required or state.case_status == CaseStatus.AWAITING_APPROVAL:
            return StopReason.AWAITING_HUMAN_REVIEW

        current_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action

        # 2. Policy-mandated escalation
        if current_nba and current_nba.action_type == ActionType.ESCALATE_ANALYST:
            return StopReason.POLICY_MANDATED_ESCALATION

        # 3. No material fraud evidence
        if current_nba and current_nba.action_type in [ActionType.CLOSE_CASE, ActionType.NO_ACTION]:
            if state.risk_score is None or state.risk_score <= 0.40:
                return StopReason.NO_MATERIAL_FRAUD_EVIDENCE

        # 4. Max iterations reached
        if state.iteration_count >= 5:
            return StopReason.MAX_ITERATIONS_REACHED

        # 5. Low value of additional evidence
        if (
            state.evidence_completeness is not None
            and state.evidence_completeness < 0.40
            and len(state.requested_evidence) > 0
        ):
            return StopReason.LOW_VALUE_OF_ADDITIONAL_EVIDENCE

        # 6. Default to sufficient evidence for action if actions or clear recommendations exist
        return StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION

    def generate_case_summary_text(
        self,
        state: FraudCaseState,
        stop_reason: StopReason,
    ) -> str:
        """Synthesize a concise, human-auditable text summary of the investigation."""
        current_nba = state.post_evidence_next_best_action or state.pre_evidence_next_best_action
        action_name = current_nba.action_type.value if current_nba else "NO_ACTION"
        top_hypo = state.hypotheses[0].title if state.hypotheses else "General Anomaly"
        risk_str = str(state.risk_level or "HIGH")
        score_str = f"{state.risk_score:.2f}" if state.risk_score is not None else "N/A"
        conf_str = f"{state.confidence:.2f}" if state.confidence is not None else "N/A"

        # Evidence stats
        all_ev = state.all_evidence
        ev_count = len(all_ev)

        # Executed action count
        exec_count = len(state.executed_actions)
        sar_str = (
            f"SAR Filed ({state.sar_reference})"
            if state.sar_reference
            else "No SAR Filed"
        )

        lines = [
            f"Case {state.case_id} concluded with stop reason '{stop_reason.value}'.",
            f"Trigger: {state.trigger_type.value} on Customer '{state.customer_id or 'UNKNOWN'}' (Txn: {state.transaction_id or 'UNKNOWN'}).",
            f"Assessment: Risk {risk_str} (Score: {score_str}, Confidence: {conf_str}) — Primary Typology: {top_hypo}.",
            f"Evidence: {ev_count} verified item(s) collected across graph, behavior, device, and policy domains.",
            f"Disposition: Recommended action '{action_name}'. {exec_count} action(s) executed/simulated. Regulatory Status: {sar_str}.",
        ]

        if state.pre_evidence_next_best_action and state.post_evidence_next_best_action:
            pre_name = state.pre_evidence_next_best_action.action_type
            post_name = state.post_evidence_next_best_action.action_type
            if pre_name != post_name:
                lines.append(f"Recommendation updated following additional evidence from '{pre_name}' to '{post_name}'.")

        return " ".join(lines)

    def finalize_case(
        self,
        state: FraudCaseState,
        stop_reason: Optional[StopReason] = None,
    ) -> Tuple[FinalCaseSummary, Dict[str, Any]]:
        """Finalize the investigation, validate state integrity, and produce audit summaries.

        Args:
            state: Current FraudCaseState.
            stop_reason: Optional explicit StopReason.

        Returns:
            Tuple of:
            - FinalCaseSummary structured model
            - State patch dictionary for LangGraph state reducer
        """
        # 1. Deterministically resolve stop reason
        resolved_stop_reason = self.determine_stop_reason(state, stop_reason)
        ts = now_iso()

        logger.info(
            "Finalizing case %s with stop reason '%s'",
            state.case_id,
            resolved_stop_reason.value,
        )

        # 2. Validate integrity
        val_result = self.validate_case_integrity(state)
        if not val_result.valid:
            logger.warning(
                "Case %s integrity validation flagged errors: %s",
                state.case_id,
                val_result.errors,
            )

        # 3. Determine final lifecycle status
        if resolved_stop_reason == StopReason.AWAITING_HUMAN_REVIEW:
            final_status = CaseStatus.AWAITING_APPROVAL
        elif val_result.valid:
            final_status = CaseStatus.COMPLETED
        else:
            final_status = CaseStatus.FAILED if not state.executed_actions else CaseStatus.COMPLETED

        # 4. Tally evidence categories
        all_ev = state.all_evidence
        cat_counts: Dict[str, int] = {}
        for ev in all_ev:
            cat_str = str(ev.category)
            cat_counts[cat_str] = cat_counts.get(cat_str, 0) + 1

        # 5. Synthesize summary text
        summary_text = self.generate_case_summary_text(state, resolved_stop_reason)

        # 6. Build structured FinalCaseSummary
        summary_model = FinalCaseSummary(
            case_id=state.case_id,
            status=final_status,
            stop_reason=resolved_stop_reason,
            trigger_type=state.trigger_type,
            customer_id=state.customer_id,
            transaction_id=state.transaction_id,
            account_ids=state.account_ids,
            risk_level=state.risk_level,
            risk_score=state.risk_score,
            confidence=state.confidence,
            evidence_completeness=state.evidence_completeness,
            hypotheses=[h.model_dump() for h in state.hypotheses],
            total_evidence_count=len(all_ev),
            evidence_category_counts=cat_counts,
            pre_evidence_next_best_action=(
                state.pre_evidence_next_best_action.model_dump()
                if state.pre_evidence_next_best_action
                else None
            ),
            post_evidence_next_best_action=(
                state.post_evidence_next_best_action.model_dump()
                if state.post_evidence_next_best_action
                else None
            ),
            approval_required=state.approval_required,
            approval_status=state.approval_status,
            approval_decisions=[a.model_dump() for a in state.approval_decisions],
            executed_actions=[e.model_dump() for e in state.executed_actions],
            sar_filed=bool(state.sar_reference),
            sar_reference=state.sar_reference,
            sar_report=state.sar_report,
            timeline_event_count=len(state.timeline) + 1,
            case_summary_text=summary_text,
            closed_at=ts,
        )

        # 7. Create timeline event
        timeline_event = TimelineEvent(
            event_id=generate_event_id(),
            event_type="CASE_FINALIZED",
            node_name="case_finalizer",
            description=(
                f"Investigation finalized. Stop reason: '{resolved_stop_reason.value}'. "
                f"Status: {final_status.value}."
            ),
            timestamp=ts,
            details={
                "stop_reason": resolved_stop_reason.value,
                "case_status": final_status.value,
                "risk_level": str(state.risk_level) if state.risk_level else None,
                "risk_score": state.risk_score,
                "evidence_count": len(all_ev),
                "sar_reference": state.sar_reference,
            },
        )

        patch: Dict[str, Any] = {
            "case_status": final_status.value,
            "stop_reason": resolved_stop_reason.value,
            "case_summary": summary_text,
            "final_summary": summary_model.model_dump(),
            "timeline": [timeline_event.model_dump()],
        }

        return summary_model, patch
