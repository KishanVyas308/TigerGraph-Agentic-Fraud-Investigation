"""Deterministic Policy Engine (Layer 19).

The Policy Engine separates LLM recommendation from policy authorization.
The LLM recommends a NextBestAction, but the Policy Engine strictly determines:
- allowed
- autonomous
- approval_required
- approval_role
- report_required
- unmet_prerequisites
- policy_reference

If a recommendation is disallowed or prerequisites are missing, the Policy Engine
rejects it, records the reason, and returns a safe, authorized fallback action.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ActionType,
    ApprovalRole,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
    RiskLevel,
)
from backend.app.policies.loader import load_policy_config
from backend.app.utils.logging import get_logger

logger = get_logger("policies.engine")


class PolicyCheckResult(BaseModel):
    """Result of evaluating a recommended action against deterministic policy rules."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    action_type: ActionType
    allowed: bool
    autonomous: bool
    approval_required: bool
    approval_role: Optional[ApprovalRole] = None
    report_required: bool = False
    unmet_prerequisites: List[str] = Field(default_factory=list)
    policy_reference: str
    rejection_reason: Optional[str] = None
    authorized_action: NextBestAction


class PolicyEngine:
    """Deterministic policy engine evaluating candidate next-best actions."""

    def __init__(self, config_path: Optional[str] = None):
        self.rules: Dict[str, Dict[str, Any]] = load_policy_config(config_path)

    def evaluate_action(
        self,
        recommended_action: NextBestAction,
        state: FraudCaseState,
    ) -> PolicyCheckResult:
        """Evaluate recommended action against deterministic policy rules."""
        action_val = (
            recommended_action.action_type.value
            if hasattr(recommended_action.action_type, "value")
            else str(recommended_action.action_type)
        )

        rule = self.rules.get(action_val)
        if not rule:
            logger.warning("Unrecognized action type '%s'. Disallowing action.", action_val)
            fallback = self._create_fallback_action(
                recommended_action,
                ActionType.ESCALATE_ANALYST,
                "Action type unrecognized by policy engine.",
                state,
            )
            return PolicyCheckResult(
                action_type=recommended_action.action_type,
                allowed=False,
                autonomous=False,
                approval_required=True,
                approval_role=ApprovalRole.ANALYST,
                report_required=False,
                unmet_prerequisites=["RECOGNIZED_ACTION_TYPE"],
                policy_reference="DEFAULT_REJECTION",
                rejection_reason=f"Action '{action_val}' is unrecognized by policy engine.",
                authorized_action=fallback,
            )

        allowed = bool(rule.get("allowed", True))
        autonomous = bool(rule.get("autonomous", False))
        approval_required = bool(rule.get("approval_required", False))

        raw_role = rule.get("approval_role", "SYSTEM_AUTOMATIC")
        try:
            approval_role = ApprovalRole(raw_role)
        except ValueError:
            approval_role = ApprovalRole.SYSTEM_AUTOMATIC

        report_required = bool(rule.get("report_required", False))
        policy_ref = str(rule.get("policy_reference", "GENERAL_POLICY"))

        unmet_prereqs: List[str] = []
        req_prereqs = rule.get("required_prerequisites", [])

        # Check entity state prerequisites
        for req in req_prereqs:
            if req == "transaction_id" and not state.transaction_id:
                unmet_prereqs.append("Missing transaction_id")
            elif req == "customer_id" and not state.customer_id:
                unmet_prereqs.append("Missing customer_id")
            elif req == "account_ids" and not state.account_ids:
                unmet_prereqs.append("Missing account_ids")
            elif req == "case_id" and not state.case_id:
                unmet_prereqs.append("Missing case_id")

        # Check risk score threshold limits
        min_risk = float(rule.get("min_risk_score", 0.0))
        max_risk = float(rule.get("max_risk_score", 1.0))
        risk_score = state.risk_score
        if risk_score is None:
            if state.risk_level in (RiskLevel.CRITICAL, "CRITICAL"):
                risk_score = 0.90
            elif state.risk_level in (RiskLevel.HIGH, "HIGH"):
                risk_score = 0.80
            elif state.risk_level in (RiskLevel.LOW, "LOW"):
                risk_score = 0.15
            else:
                risk_score = 0.50

        if risk_score > max_risk:
            unmet_prereqs.append(f"Risk score {risk_score:.2f} exceeds maximum allowed ({max_risk:.2f}) for action {action_val}")
        elif risk_score < min_risk:
            unmet_prereqs.append(f"Risk score {risk_score:.2f} is below minimum required ({min_risk:.2f}) for action {action_val}")

        rejection_reason: Optional[str] = None
        if not allowed or unmet_prereqs:
            rejection_reason = f"Policy violation for '{action_val}': " + "; ".join(unmet_prereqs or ["Action explicitly disallowed."])
            logger.info("Policy Engine REJECTED recommendation '%s': %s", action_val, rejection_reason)

            # Determine safe authorized fallback
            fallback_action_type = self._select_safe_fallback(risk_score, action_val)
            authorized = self._create_fallback_action(
                recommended_action,
                fallback_action_type,
                rejection_reason,
                state,
            )
            final_allowed = False
        else:
            # Policy check PASSED
            logger.info("Policy Engine AUTHORIZED recommendation '%s' (ref: %s)", action_val, policy_ref)
            final_allowed = True
            authorized = NextBestAction(
                action_id=recommended_action.action_id,
                action_type=recommended_action.action_type,
                target_entity_id=recommended_action.target_entity_id or state.transaction_id or state.customer_id,
                target_entity_type=recommended_action.target_entity_type or "TRANSACTION",
                reasoning=recommended_action.reasoning,
                evidence_ids=recommended_action.evidence_ids,
                policy_reference=policy_ref,
                approval_required=approval_required,
                approval_role=approval_role,
                execution_mode=ExecutionMode.SIMULATED,
            )

        return PolicyCheckResult(
            action_type=recommended_action.action_type,
            allowed=final_allowed,
            autonomous=autonomous if final_allowed else False,
            approval_required=approval_required if final_allowed else True,
            approval_role=approval_role if final_allowed else ApprovalRole.ANALYST,
            report_required=report_required if final_allowed else False,
            unmet_prerequisites=unmet_prereqs,
            policy_reference=policy_ref,
            rejection_reason=rejection_reason,
            authorized_action=authorized,
        )

    def _select_safe_fallback(self, risk_score: float, original_action: str) -> ActionType:
        """Select safe alternative action when LLM recommendation is rejected."""
        if risk_score >= 0.70:
            return ActionType.ESCALATE_ANALYST
        elif risk_score >= 0.30:
            return ActionType.MONITOR_TRANSACTION
        return ActionType.NO_ACTION

    def _create_fallback_action(
        self,
        orig: NextBestAction,
        fallback_type: ActionType,
        reason: str,
        state: FraudCaseState,
    ) -> NextBestAction:
        """Construct authorized fallback action."""
        orig_action_val = orig.action_type.value if hasattr(orig.action_type, "value") else str(orig.action_type)
        fallback_rule = self.rules.get(fallback_type.value if hasattr(fallback_type, "value") else str(fallback_type), {})
        raw_role = fallback_rule.get("approval_role", "ANALYST")
        try:
            role = ApprovalRole(raw_role)
        except ValueError:
            role = ApprovalRole.ANALYST

        return NextBestAction(
            action_type=fallback_type,
            target_entity_id=orig.target_entity_id or state.case_id or "CASE_UNKNOWN",
            target_entity_type="CASE",
            reasoning=f"[POLICY FALLBACK] Original action '{orig_action_val}' rejected: {reason}",
            evidence_ids=orig.evidence_ids,
            policy_reference=str(fallback_rule.get("policy_reference", "FALLBACK_POLICY")),
            approval_required=bool(fallback_rule.get("approval_required", True)),
            approval_role=role,
            execution_mode=ExecutionMode.SIMULATED,
        )


_policy_engine_instance: Optional[PolicyEngine] = None


def get_policy_engine(config_path: Optional[str] = None) -> PolicyEngine:
    """Return a cached or newly initialized PolicyEngine instance."""
    global _policy_engine_instance
    if _policy_engine_instance is None or config_path is not None:
        _policy_engine_instance = PolicyEngine(config_path=config_path)
    return _policy_engine_instance
