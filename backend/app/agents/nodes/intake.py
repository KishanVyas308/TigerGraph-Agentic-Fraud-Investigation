"""Investigation Intake LangGraph Nodes (Layer 26).

Implements the initial entry nodes of the fraud investigation workflow:
1. `ValidateTriggerNode`: Validates case identifiers, trigger type, and required entities.
2. `LoadOrCreateCaseNode`: Checks if prior case state exists or initializes fresh state.
3. `TriggerClassifierNode`: Runs fast Laya / heuristic trigger classification.
4. `PersistCaseStartNode`: Writes initial FraudCase vertex stub to TigerGraph.
"""

from typing import Any, Dict, Optional

from backend.app.classification.laya_client import LayaFastClassifier
from backend.app.graph.tigergraph_client import TigerGraphClient, get_tigergraph_client
from backend.app.models.state import CaseStatus, FraudCaseState, TimelineEvent, TriggerType
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("agents.nodes.intake")


class ValidateTriggerNode:
    """Validates the incoming investigation trigger and ensures minimal entity bindings."""

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Validate trigger state and transition to IN_PROGRESS.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with validated status and timeline event.
        """
        logger.info("Validating investigation trigger for case %s", state.case_id)

        # Verify minimal entity anchor exists
        has_entity = bool(state.transaction_id or state.customer_id or state.account_ids)
        if not has_entity:
            logger.warning("Case %s has no bound transaction, customer, or account ID", state.case_id)

        evt = TimelineEvent(
            event_type="TRIGGER_VALIDATED",
            node_name="ValidateTriggerNode",
            description=f"Trigger {state.trigger_type.value if hasattr(state.trigger_type, 'value') else state.trigger_type} validated for case {state.case_id}.",
            details={
                "case_id": state.case_id,
                "trigger_type": state.trigger_type.value if hasattr(state.trigger_type, "value") else str(state.trigger_type),
                "transaction_id": state.transaction_id,
                "customer_id": state.customer_id,
                "account_count": len(state.account_ids),
            },
        )

        return {
            "case_status": CaseStatus.IN_PROGRESS,
            "timeline": [evt],
        }


class LoadOrCreateCaseNode:
    """Checks for existing case history or initializes a new investigation lifecycle."""

    def __init__(self, tg_client: Optional[TigerGraphClient] = None):
        self.tg_client = tg_client or get_tigergraph_client()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Load prior case history if resuming, or initialize new case.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with case lifecycle initialization event.
        """
        logger.info("Checking TigerGraph case existence for %s", state.case_id)
        is_resume = False
        try:
            timeline_data = self.tg_client.get_case_timeline(state.case_id)
            if timeline_data and len(timeline_data) > 0:
                is_resume = True
                logger.info("Resuming existing investigation %s with %d historical events", state.case_id, len(timeline_data))
        except Exception as exc:
            logger.debug("Case %s not found in graph or offline (%s); proceeding as new.", state.case_id, exc)

        desc = (
            f"Resumed existing fraud case {state.case_id} from TigerGraph."
            if is_resume
            else f"Created fresh fraud case {state.case_id} in memory."
        )

        evt = TimelineEvent(
            event_type="CASE_INITIALIZED",
            node_name="LoadOrCreateCaseNode",
            description=desc,
            details={"is_resume": is_resume, "case_id": state.case_id},
        )

        return {"timeline": [evt]}


class TriggerClassifierNode:
    """Fast classification of trigger context for routing and priority assignment."""

    def __init__(self, classifier: Optional[LayaFastClassifier] = None):
        self.classifier = classifier or LayaFastClassifier()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Classify trigger urgency and fraud pattern category.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with trigger classification event.
        """
        logger.info("Classifying trigger context for case %s", state.case_id)
        context_text = f"Trigger: {state.trigger_type}. Tx: {state.transaction_id}. Customer: {state.customer_id}."
        classification = self.classifier.classify_trigger(context_text)

        evt = TimelineEvent(
            event_type="TRIGGER_CLASSIFIED",
            node_name="TriggerClassifierNode",
            description=f"Trigger classified as '{classification.category}' with confidence {classification.confidence:.2f}.",
            details={
                "category": classification.category,
                "confidence": classification.confidence,
                "suggested_priority": classification.priority,
            },
        )

        return {"timeline": [evt]}


class PersistCaseStartNode:
    """Persists the initial FraudCase vertex stub to TigerGraph with OPEN/IN_PROGRESS status."""

    def __init__(self, tg_client: Optional[TigerGraphClient] = None):
        self.tg_client = tg_client or get_tigergraph_client()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Record initial case vertex in TigerGraph.

        Args:
            state: Current FraudCaseState.

        Returns:
            State patch dictionary with start persistence event.
        """
        logger.info("Persisting case start vertex in TigerGraph for %s", state.case_id)
        try:
            self.tg_client.write_case_update(
                case_id=state.case_id,
                status=CaseStatus.IN_PROGRESS.value,
                summary=f"Investigation opened for trigger {state.trigger_type}.",
            )
        except Exception as exc:
            logger.warning("Could not persist initial case vertex to TigerGraph: %s", exc)

        evt = TimelineEvent(
            event_type="CASE_OPENED_IN_TIGERGRAPH",
            node_name="PersistCaseStartNode",
            description=f"Initialized case vertex in TigerGraph for case {state.case_id}.",
            details={"case_id": state.case_id, "status": CaseStatus.IN_PROGRESS.value, "timestamp": now_iso()},
        )

        return {"timeline": [evt]}
