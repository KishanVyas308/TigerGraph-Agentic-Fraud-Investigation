"""Mock Evidence and Action Services (Layer 21).

Simulates external banking operations and evidence ingestion for hackathon demo:
- Mock Evidence Services:
  * Customer transaction confirmation (confirm / deny via SMS/Push)
  * Step-up authentication (pass / fail for 2FA biometric/OTP)
  * Analyst evidence submission (notes and supplemental findings)
  * External reputation signals (IP/device reputation check)
- Mock Action Services for all 13 permitted ActionTypes:
  * ALLOW_TRANSACTION
  * BLOCK_TRANSACTION
  * MONITOR_TRANSACTION
  * MONITOR_ACCOUNT
  * BLOCK_ACCOUNT
  * WARN_CUSTOMER
  * REQUEST_CUSTOMER_CONFIRMATION
  * REQUEST_STEP_UP_AUTH
  * REQUEST_ANALYST_EVIDENCE
  * ESCALATE_ANALYST
  * FILE_SAR
  * CLOSE_CASE
  * NO_ACTION

All operations strictly execute in SIMULATED mode (execution_mode = SIMULATED)
and produce auditable timeline events without altering real bank systems.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.actions.base import (
    BaseActionExecutor,
    SIMULATION_DISCLAIMER,
    SimulatedActionResult,
)
from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.models.state import (
    ActionExecution,
    ActionType,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    ExecutionMode,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
)
from backend.app.utils.ids import generate_event_id, generate_prefixed_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("actions.mocks")


# ============================================================================
# Mock Evidence Services
# ============================================================================

class MockCustomerConfirmationService:
    """Simulated service for customer transaction authorization confirmations."""

    def __init__(self, normalizer: Optional[EvidenceNormalizer] = None):
        self.normalizer = normalizer or EvidenceNormalizer()

    def confirm_transaction(
        self,
        transaction_id: str,
        customer_id: Optional[str] = None,
        channel: str = "SMS",
        confirmed: bool = True,
        timestamp: Optional[str] = None,
    ) -> Tuple[SimulatedActionResult, List[EvidenceItem]]:
        """Simulate customer confirming or denying transaction legitimacy."""
        ts = timestamp or now_iso()
        norm_items = self.normalizer.normalize_customer_response({
            "transaction_id": transaction_id,
            "customer_id": customer_id,
            "channel": channel,
            "confirmed_authorized": confirmed,
            "timestamp": ts,
        })

        action_type = ActionType.REQUEST_CUSTOMER_CONFIRMATION
        status_str = "AUTHORIZED" if confirmed else "UNAUTHORIZED_FRAUD_REPORTED"
        logger.info(
            "Simulated customer response for %s: %s via %s",
            transaction_id,
            status_str,
            channel,
        )

        result = SimulatedActionResult(
            action_type=action_type,
            target_entity_id=transaction_id,
            target_entity_type="TRANSACTION",
            details={
                "transaction_id": transaction_id,
                "customer_id": customer_id,
                "confirmed_authorized": confirmed,
                "channel": channel,
                "status": status_str,
                "evidence_count": len(norm_items),
            },
            disclaimer=SIMULATION_DISCLAIMER,
        )
        return result, norm_items

    def deny_transaction(
        self,
        transaction_id: str,
        customer_id: Optional[str] = None,
        channel: str = "SMS",
        timestamp: Optional[str] = None,
    ) -> Tuple[SimulatedActionResult, List[EvidenceItem]]:
        """Convenience method for customer reporting transaction as unauthorized."""
        return self.confirm_transaction(
            transaction_id=transaction_id,
            customer_id=customer_id,
            channel=channel,
            confirmed=False,
            timestamp=timestamp,
        )


class MockStepUpAuthService:
    """Simulated service for 2FA biometric or OTP challenge results."""

    def __init__(self, normalizer: Optional[EvidenceNormalizer] = None):
        self.normalizer = normalizer or EvidenceNormalizer()

    def authenticate(
        self,
        customer_id: str,
        transaction_id: Optional[str] = None,
        method: str = "BIOMETRIC",
        passed: bool = True,
        attempts: int = 1,
        timestamp: Optional[str] = None,
    ) -> Tuple[SimulatedActionResult, List[EvidenceItem]]:
        """Simulate step-up authentication challenge outcome."""
        ts = timestamp or now_iso()
        norm_items = self.normalizer.normalize_authentication_result({
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "method": method,
            "verified": passed,
            "attempts": attempts,
            "timestamp": ts,
        })

        status_str = "PASSED" if passed else f"FAILED_{attempts}_ATTEMPTS"
        logger.info(
            "Simulated step-up auth for customer %s (%s): %s",
            customer_id,
            method,
            status_str,
        )

        result = SimulatedActionResult(
            action_type=ActionType.REQUEST_STEP_UP_AUTH,
            target_entity_id=customer_id,
            target_entity_type="CUSTOMER",
            details={
                "customer_id": customer_id,
                "transaction_id": transaction_id,
                "method": method,
                "verified": passed,
                "attempts": attempts,
                "status": status_str,
                "evidence_count": len(norm_items),
            },
            disclaimer=SIMULATION_DISCLAIMER,
        )
        return result, norm_items

    def fail_authentication(
        self,
        customer_id: str,
        transaction_id: Optional[str] = None,
        method: str = "BIOMETRIC",
        attempts: int = 3,
        timestamp: Optional[str] = None,
    ) -> Tuple[SimulatedActionResult, List[EvidenceItem]]:
        """Convenience method for failed step-up authentication challenge."""
        return self.authenticate(
            customer_id=customer_id,
            transaction_id=transaction_id,
            method=method,
            passed=False,
            attempts=attempts,
            timestamp=timestamp,
        )


class MockAnalystEvidenceService:
    """Simulated service for human analyst supplemental evidence and findings."""

    def __init__(self, normalizer: Optional[EvidenceNormalizer] = None):
        self.normalizer = normalizer or EvidenceNormalizer()

    def submit_evidence(
        self,
        case_id: str,
        analyst_id: str = "ANALYST_01",
        note: str = "",
        timestamp: Optional[str] = None,
    ) -> Tuple[SimulatedActionResult, List[EvidenceItem]]:
        """Simulate analyst submitting manual investigation findings."""
        ts = timestamp or now_iso()
        norm_items = self.normalizer.normalize_analyst_input({
            "case_id": case_id,
            "analyst_id": analyst_id,
            "note": note,
            "timestamp": ts,
        })

        logger.info(
            "Simulated analyst evidence for case %s by %s",
            case_id,
            analyst_id,
        )

        result = SimulatedActionResult(
            action_type=ActionType.REQUEST_ANALYST_EVIDENCE,
            target_entity_id=case_id,
            target_entity_type="FRAUD_CASE",
            details={
                "case_id": case_id,
                "analyst_id": analyst_id,
                "note_preview": note[:60] + "..." if len(note) > 60 else note,
                "evidence_count": len(norm_items),
            },
            disclaimer=SIMULATION_DISCLAIMER,
        )
        return result, norm_items


class MockExternalReputationService:
    """Simulated service for external IP, device, and entity reputation checks."""

    def __init__(self, normalizer: Optional[EvidenceNormalizer] = None):
        self.normalizer = normalizer or EvidenceNormalizer()

    def check_reputation(
        self,
        entity_id: str,
        provider: str = "IPQualityScore",
        signal_type: str = "IP_REPUTATION",
        score: Optional[float] = None,
        flag: Optional[str] = None,
        details: str = "",
    ) -> Tuple[SimulatedActionResult, List[EvidenceItem]]:
        """Simulate external threat intelligence lookup."""
        norm_items = self.normalizer.normalize_external_signal({
            "provider": provider,
            "entity_id": entity_id,
            "signal_type": signal_type,
            "score": score,
            "flag": flag,
            "details": details,
        })

        logger.info(
            "Simulated external reputation for %s via %s (score=%s, flag=%s)",
            entity_id,
            provider,
            score,
            flag,
        )

        result = SimulatedActionResult(
            action_type=ActionType.MONITOR_TRANSACTION,
            target_entity_id=entity_id,
            target_entity_type="EXTERNAL_ENTITY",
            details={
                "entity_id": entity_id,
                "provider": provider,
                "signal_type": signal_type,
                "score": score,
                "flag": flag,
                "evidence_count": len(norm_items),
            },
            disclaimer=SIMULATION_DISCLAIMER,
        )
        return result, norm_items


# ============================================================================
# Mock Action Execution Service
# ============================================================================

class MockActionExecutionService(BaseActionExecutor):
    """Executes simulated banking actions across all 13 supported ActionTypes."""

    def execute(
        self,
        action: NextBestAction,
        state: FraudCaseState,
    ) -> Tuple[ActionExecution, TimelineEvent, Dict[str, Any]]:
        """Simulate permitted action execution with typed audit logs."""
        return self.execute_action(action, state)

    def execute_action(
        self,
        action: NextBestAction,
        state: FraudCaseState,
    ) -> Tuple[ActionExecution, TimelineEvent, Dict[str, Any]]:
        """Simulate execution of an authorized next-best action."""
        action_type = (
            action.action_type.value
            if hasattr(action.action_type, "value")
            else str(action.action_type)
        )
        target_id = action.target_entity_id or state.transaction_id or state.case_id
        target_type = action.target_entity_type or "ENTITY"
        exec_id = generate_prefixed_id("EXEC_SIM", 8)
        ts = now_iso()

        logger.info(
            "Simulating action '%s' for target %s in case %s",
            action_type,
            target_id,
            state.case_id,
        )

        # Dispatch simulated execution logic per ActionType
        details: Dict[str, Any] = {
            "disclaimer": SIMULATION_DISCLAIMER,
            "simulated_execution_id": exec_id,
            "policy_reference": action.policy_reference,
            "reasoning": action.reasoning,
        }

        if action_type == ActionType.ALLOW_TRANSACTION.value:
            details.update({
                "transaction_id": target_id,
                "processing_code": "00_APPROVED",
                "core_banking_status": "POSTED",
                "settlement_status": "QUEUED_FOR_CLEARING",
            })
            desc = f"Simulated ALLOW_TRANSACTION for {target_id}: Cleared through core banking switch."

        elif action_type == ActionType.BLOCK_TRANSACTION.value:
            details.update({
                "transaction_id": target_id,
                "response_code": "59_SUSPECTED_FRAUD",
                "authorization_status": "DECLINED",
                "disposition": "IMMEDIATE_STOP",
            })
            desc = f"Simulated BLOCK_TRANSACTION for {target_id}: Declined with code 59_SUSPECTED_FRAUD."

        elif action_type == ActionType.MONITOR_TRANSACTION.value:
            details.update({
                "transaction_id": target_id,
                "watch_window_hours": 24,
                "alert_threshold": "HIGH_FREQUENCY",
                "monitoring_queue": "WATCHLIST_ACTIVE",
            })
            desc = f"Simulated MONITOR_TRANSACTION for {target_id}: Placed under 24-hour high-frequency telemetry watch."

        elif action_type == ActionType.MONITOR_ACCOUNT.value:
            accounts = state.account_ids or ([target_id] if target_id else [])
            details.update({
                "account_ids": accounts,
                "surveillance_window_hours": 72,
                "enhanced_monitoring": True,
                "surveillance_level": "TIER_2_ENHANCED",
            })
            desc = f"Simulated MONITOR_ACCOUNT for {accounts}: Initiated 72-hour enhanced account surveillance."

        elif action_type == ActionType.BLOCK_ACCOUNT.value:
            accounts = state.account_ids or ([target_id] if target_id else [])
            cust_id = state.customer_id or "UNKNOWN_CUSTOMER"
            details.update({
                "customer_id": cust_id,
                "account_ids": accounts,
                "hold_status": "ADMINISTRATIVE_FREEZE",
                "restriction_scope": "DEBIT_AND_CREDIT",
                "compliance_lock": True,
            })
            desc = f"Simulated BLOCK_ACCOUNT for {accounts} (Customer {cust_id}): Administrative freeze placed."

        elif action_type == ActionType.WARN_CUSTOMER.value:
            cust_id = state.customer_id or target_id
            details.update({
                "customer_id": cust_id,
                "notification_id": generate_prefixed_id("NOTIF", 8),
                "dispatch_channel": "SMS_AND_EMAIL",
                "template": "SUSPICIOUS_ACTIVITY_ALERT",
                "delivery_status": "SENT_SIMULATED",
            })
            desc = f"Simulated WARN_CUSTOMER for {cust_id}: Dispatched security alert via SMS and Email."

        elif action_type == ActionType.REQUEST_CUSTOMER_CONFIRMATION.value:
            cust_id = state.customer_id or "CUSTOMER"
            details.update({
                "customer_id": cust_id,
                "transaction_id": target_id,
                "verification_token": generate_prefixed_id("VERIF", 8),
                "dispatch_channel": "SMS_PUSH",
                "status": "PROMPT_DELIVERED",
            })
            desc = f"Simulated REQUEST_CUSTOMER_CONFIRMATION for {target_id}: Interactive verification prompt dispatched."

        elif action_type == ActionType.REQUEST_STEP_UP_AUTH.value:
            cust_id = state.customer_id or target_id
            details.update({
                "customer_id": cust_id,
                "challenge_id": generate_prefixed_id("CHAL", 8),
                "challenge_type": "BIOMETRIC_OR_OTP",
                "status": "CHALLENGE_ISSUED",
            })
            desc = f"Simulated REQUEST_STEP_UP_AUTH for {cust_id}: Step-up 2FA biometric challenge issued."

        elif action_type == ActionType.REQUEST_ANALYST_EVIDENCE.value:
            details.update({
                "case_id": state.case_id,
                "queue_priority": "P2_REVIEW",
                "task_id": generate_prefixed_id("TASK", 8),
                "status": "ROUTED_TO_ANALYST_QUEUE",
            })
            desc = f"Simulated REQUEST_ANALYST_EVIDENCE on Case {state.case_id}: Routed to analyst investigation queue."

        elif action_type == ActionType.ESCALATE_ANALYST.value:
            details.update({
                "case_id": state.case_id,
                "queue_priority": "P1_URGENT",
                "escalation_ticket_id": generate_prefixed_id("ESC", 8),
                "status": "ESCALATED_MANUAL_REVIEW",
            })
            desc = f"Simulated ESCALATE_ANALYST on Case {state.case_id}: Escalated to human fraud analyst queue (P1_URGENT)."

        elif action_type == ActionType.FILE_SAR.value:
            cust_id = state.customer_id or "UNKNOWN"
            sar_ref = generate_prefixed_id("SAR_REF", 10)
            details.update({
                "case_id": state.case_id,
                "customer_id": cust_id,
                "sar_reference_id": sar_ref,
                "filing_status": "PENDING_REPORT_GENERATION",
                "regulatory_body": "FinCEN_MOCK",
            })
            desc = f"Simulated FILE_SAR for Case {state.case_id}: Created preliminary SAR reference {sar_ref}."

        elif action_type == ActionType.CLOSE_CASE.value:
            details.update({
                "case_id": state.case_id,
                "resolution": "INVESTIGATION_CONCLUDED",
                "closed_at": ts,
            })
            desc = f"Simulated CLOSE_CASE on Case {state.case_id}: Investigation marked concluded."

        elif action_type == ActionType.NO_ACTION.value:
            details.update({
                "case_id": state.case_id,
                "status": "NO_OPERATIONAL_CHANGE",
            })
            desc = f"Simulated NO_ACTION on Case {state.case_id}: No operational intervention taken."

        else:
            details.update({
                "action": action_type,
                "target_id": target_id,
                "status": "EXECUTED_DEFAULT",
            })
            desc = f"Simulated action '{action_type}' for {target_id}."

        execution_record = ActionExecution(
            execution_id=exec_id,
            action_type=action.action_type,
            execution_mode=ExecutionMode.SIMULATED,
            success=True,
            result=details,
            timestamp=ts,
        )

        timeline_event = TimelineEvent(
            event_id=generate_event_id(),
            event_type="ACTION_EXECUTED_SIMULATED",
            node_name="mock_action_service",
            description=desc,
            timestamp=ts,
            details={
                "action_type": action_type,
                "execution_mode": ExecutionMode.SIMULATED.value,
                "target_id": target_id,
                "target_type": target_type,
                "execution_id": exec_id,
                "disclaimer": SIMULATION_DISCLAIMER,
            },
        )

        return execution_record, timeline_event, details


# ============================================================================
# Evidence Ingestion Helper
# ============================================================================

def ingest_mock_evidence(
    state: FraudCaseState,
    evidence_items: List[EvidenceItem],
) -> Dict[str, Any]:
    """Ingest simulated evidence items into FraudCaseState and record timeline events.

    Args:
        state: Current FraudCaseState.
        evidence_items: List of normalized EvidenceItems to append.

    Returns:
        State patch dictionary for LangGraph state reducer.
    """
    if not evidence_items:
        logger.warning("ingest_mock_evidence called with empty evidence list.")
        return {}

    ts = now_iso()
    raw_dicts = [e.model_dump() for e in evidence_items]

    patch: Dict[str, Any] = {
        "received_evidence": raw_dicts,
    }

    # Transition case_status from AWAITING_EVIDENCE back to IN_PROGRESS
    if state.case_status == CaseStatus.AWAITING_EVIDENCE:
        patch["case_status"] = CaseStatus.IN_PROGRESS.value

    # Create timeline event for evidence arrival
    cat_summary = list({str(e.category) for e in evidence_items})
    timeline_event = TimelineEvent(
        event_id=generate_event_id(),
        event_type="ADDITIONAL_EVIDENCE_INGESTED",
        node_name="mock_evidence_service",
        description=(
            f"Ingested {len(evidence_items)} simulated evidence item(s) "
            f"across categories: {cat_summary}."
        ),
        timestamp=ts,
        details={
            "evidence_count": len(evidence_items),
            "evidence_ids": [e.evidence_id for e in evidence_items],
            "categories": cat_summary,
            "disclaimer": SIMULATION_DISCLAIMER,
        },
    )
    patch["timeline"] = [timeline_event.model_dump()]

    logger.info(
        "Ingested %d simulated evidence item(s) for case %s",
        len(evidence_items),
        state.case_id,
    )
    return patch
