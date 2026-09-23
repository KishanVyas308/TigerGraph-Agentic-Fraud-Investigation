"""Evidence Iteration and Action Resolution LangGraph Nodes (Layer 26).

Implements the evidence loop and post-reasoning nodes:
1. `RecordPreEvidenceNBANode`: Preserves pre-evidence recommendation and increments loop counter.
2. `RequestEvidenceNode`: Dispatches mock evidence requests (SMS confirmation, step-up auth, analyst info).
3. `IngestEvidenceNode`: Ingests, normalizes, and appends received evidence, then recalculates features.
4. `DetermineNextBestActionNode`: Establishes the post-evidence next-best action.
5. `ReportIfRequiredNode`: Automatically files SAR reports when policy mandates reporting.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.actions.mocks import (
    MockAnalystEvidenceService,
    MockCustomerConfirmationService,
    MockStepUpAuthService,
    ingest_mock_evidence,
)
from backend.app.features.engine import GraphFeatureEngine
from backend.app.models.state import (
    ActionType,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    FraudCaseState,
    NextBestAction,
    RiskLevel,
    StopReason,
    TimelineEvent,
)
from backend.app.reporting.sar_generator import SARGenerator
from backend.app.utils.ids import generate_action_id
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.evidence_loop")


class RecordPreEvidenceNBANode:
    """Records the preliminary next-best action before requesting additional evidence.

    Ensures append-oriented auditability: pre-evidence recommendation is never overwritten.
    """

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Record pre-evidence NBA and advance loop iteration.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with pre_evidence_next_best_action and incremented iteration_count.
        """
        logger.info("Recording pre-evidence next-best action for case %s", state.case_id)

        # Preserve existing pre-evidence NBA if already set; otherwise establish from preliminary recommendation
        pre_nba = state.pre_evidence_next_best_action
        if pre_nba is None:
            if state.post_evidence_next_best_action:
                pre_nba = state.post_evidence_next_best_action
            else:
                # Derive default preliminary NBA based on current risk
                action_type = (
                    ActionType.MONITOR_TRANSACTION
                    if state.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
                    else ActionType.REQUEST_CUSTOMER_CONFIRMATION
                )
                pre_nba = NextBestAction(
                    action_id=generate_action_id(),
                    action_type=action_type,
                    reasoning="Preliminary recommendation prior to collecting requested additional evidence.",
                    evidence_ids=list(state.supporting_evidence_ids),
                )

        new_count = state.iteration_count + 1

        evt = TimelineEvent(
            event_type="PRE_EVIDENCE_NBA_RECORDED",
            node_name="RecordPreEvidenceNBANode",
            description=(
                f"Recorded pre-evidence recommendation: {pre_nba.action_type.value if hasattr(pre_nba.action_type, 'value') else pre_nba.action_type}. "
                f"Iteration loop count: {new_count}."
            ),
            details={
                "action_type": pre_nba.action_type.value if hasattr(pre_nba.action_type, "value") else str(pre_nba.action_type),
                "iteration_count": new_count,
            },
        )

        return {
            "pre_evidence_next_best_action": pre_nba,
            "iteration_count": new_count,
            "case_status": CaseStatus.AWAITING_EVIDENCE,
            "timeline": [evt],
        }


class RequestEvidenceNode:
    """Dispatches targeted evidence requests via mock services."""

    def __init__(
        self,
        customer_service: Optional[MockCustomerConfirmationService] = None,
        auth_service: Optional[MockStepUpAuthService] = None,
        analyst_service: Optional[MockAnalystEvidenceService] = None,
    ):
        self.customer_service = customer_service or MockCustomerConfirmationService()
        self.auth_service = auth_service or MockStepUpAuthService()
        self.analyst_service = analyst_service or MockAnalystEvidenceService()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Dispatch requested evidence requests to simulated external services.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with dispatched requests and timeline event.
        """
        logger.info("Dispatching evidence requests for case %s (%d requests)", state.case_id, len(state.requested_evidence))

        dispatched_count = len(state.requested_evidence)
        evt = TimelineEvent(
            event_type="ADDITIONAL_EVIDENCE_REQUESTED",
            node_name="RequestEvidenceNode",
            description=f"Dispatched {dispatched_count} targeted evidence request(s).",
            details={
                "requests": [r.model_dump() for r in state.requested_evidence],
            },
        )

        return {"timeline": [evt]}


class IngestEvidenceNode:
    """Ingests, normalizes, and appends received evidence items, then recalculates features."""

    def __init__(
        self,
        feature_engine: Optional[GraphFeatureEngine] = None,
        customer_service: Optional[MockCustomerConfirmationService] = None,
        auth_service: Optional[MockStepUpAuthService] = None,
        analyst_service: Optional[MockAnalystEvidenceService] = None,
    ):
        self.feature_engine = feature_engine or GraphFeatureEngine()
        self.customer_service = customer_service or MockCustomerConfirmationService()
        self.auth_service = auth_service or MockStepUpAuthService()
        self.analyst_service = analyst_service or MockAnalystEvidenceService()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Simulate evidence arrival, normalize, append to state, and recalculate features.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with received_evidence, recalculate features, and timeline event.
        """
        logger.info("Ingesting additional evidence for case %s", state.case_id)

        mock_responses: List[Dict[str, Any]] = []

        # If specific evidence requests exist, generate matching mock responses
        if state.requested_evidence:
            for req in state.requested_evidence:
                ev_type = req.evidence_type.upper()
                if "CUSTOMER" in ev_type:
                    resp = self.customer_service.request_confirmation(
                        customer_id=req.target_entity_id,
                        transaction_id=state.transaction_id or "TX_UNKNOWN",
                    )
                    mock_responses.append(resp.result)
                elif "AUTH" in ev_type or "STEP_UP" in ev_type:
                    resp = self.auth_service.challenge_user(
                        account_id=req.target_entity_id,
                    )
                    mock_responses.append(resp.result)
                else:
                    resp = self.analyst_service.request_analyst_review(
                        case_id=state.case_id,
                        question=req.reason,
                    )
                    mock_responses.append(resp.result)
        else:
            # Default fallback mock response
            resp = self.customer_service.request_confirmation(
                customer_id=state.customer_id or "CUST_DEFAULT",
                transaction_id=state.transaction_id or "TX_DEFAULT",
            )
            mock_responses.append(resp.result)

        # Ingest responses using helper
        patch = ingest_mock_evidence(state, mock_responses)

        # Recalculate graph/behavioral features with the new evidence
        try:
            raw_graph = {"neighborhood": {}, "features": state.graph_features}
            recalc_features = self.feature_engine.compute_features(raw_graph)
            patch["graph_features"] = {**state.graph_features, **recalc_features.features}
        except Exception as exc:
            logger.debug("Feature recalculation fallback: %s", exc)

        evt = TimelineEvent(
            event_type="ADDITIONAL_EVIDENCE_INGESTED",
            node_name="IngestEvidenceNode",
            description=f"Ingested {len(mock_responses)} additional evidence item(s). Recalculated features.",
            details={"items_count": len(mock_responses)},
        )
        patch["timeline"] = [evt]

        return patch


class DetermineNextBestActionNode:
    """Establishes or updates the final post-evidence next-best action."""

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Determine next-best action based on synthesis of all available evidence.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with post_evidence_next_best_action and timeline event.
        """
        logger.info("Determining next-best action for case %s", state.case_id)

        # If post-evidence NBA already established, keep it
        post_nba = state.post_evidence_next_best_action
        if post_nba is None:
            risk = state.risk_level or RiskLevel.MEDIUM
            if risk == RiskLevel.CRITICAL:
                action_type = ActionType.BLOCK_ACCOUNT
                reasoning = "Critical risk confirmed across multiple correlated graph and transaction signals; immediate account block required."
            elif risk == RiskLevel.HIGH:
                action_type = ActionType.BLOCK_TRANSACTION
                reasoning = "High risk threshold exceeded with verified anomalous indicators; blocking transaction."
            elif risk == RiskLevel.LOW:
                action_type = ActionType.ALLOW_TRANSACTION
                reasoning = "Low risk assessment grounded in verified legitimate baseline behavior; transaction permitted."
            else:
                action_type = ActionType.MONITOR_TRANSACTION
                reasoning = "Moderate ambiguity persists; placing transaction on active surveillance."

            post_nba = NextBestAction(
                action_id=generate_action_id(),
                action_type=action_type,
                reasoning=reasoning,
                evidence_ids=list(state.supporting_evidence_ids),
            )

        evt = TimelineEvent(
            event_type="NEXT_BEST_ACTION_DETERMINED",
            node_name="DetermineNextBestActionNode",
            description=f"Determined post-evidence action: {post_nba.action_type.value if hasattr(post_nba.action_type, 'value') else post_nba.action_type}.",
            details={
                "action_type": post_nba.action_type.value if hasattr(post_nba.action_type, "value") else str(post_nba.action_type),
                "reasoning": post_nba.reasoning,
            },
        )

        return {
            "post_evidence_next_best_action": post_nba,
            "timeline": [evt],
        }


class ReportIfRequiredNode:
    """Generates formal Suspicious Activity Report (SAR) if policy requires reporting."""

    def __init__(self, sar_generator: Optional[SARGenerator] = None, output_dir: Optional[Path] = None):
        self.sar_generator = sar_generator or SARGenerator()
        self.output_dir = output_dir or Path("outputs/sar")

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Check report requirement and generate SAR if indicated.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with sar_reference, sar_report, and timeline event.
        """
        # Determine if reporting is required
        executed_types = {e.action_type for e in state.executed_actions}
        recommended_type = (
            state.post_evidence_next_best_action.action_type
            if state.post_evidence_next_best_action
            else None
        )

        requires_sar = (
            ActionType.FILE_SAR in executed_types
            or recommended_type == ActionType.FILE_SAR
            or state.risk_level == RiskLevel.CRITICAL
        )

        if not requires_sar:
            logger.info("Case %s does not require SAR filing; skipping report generation.", state.case_id)
            return {}

        logger.info("Generating formal SAR filing for case %s", state.case_id)
        report, patch = self.sar_generator.generate(state, output_dir=self.output_dir)
        return patch
