"""Investigation Service (Layer 27).

Coordinates application-level investigation lifecycle, graph visualization formatting,
evidence ingestion, analyst approvals, and SSE streaming.
Delegates graph state machine progression to LangGraph (`investigate_case`).
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from pydantic import BaseModel

from backend.app.actions.mocks import MockCustomerConfirmationService, MockStepUpAuthService
from backend.app.agents.graph import investigate_case
from backend.app.graph.tigergraph_client import TigerGraphClient, get_tigergraph_client
from backend.app.models.state import (
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    FraudCaseState,
    NextBestAction,
    TimelineEvent,
    TriggerType,
)
from backend.app.policies.engine import PolicyEngine, get_policy_engine
from backend.app.schemas.api import (
    ApprovalActionRequest,
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    CaseQueueItem,
    CytoscapeElement,
    CytoscapeElementData,
    EvidenceCard,
    GraphVisualizationResponse,
    InvestigationResponse,
    InvestigationTraceResponse,
    MockConfirmationRequest,
    MockStepUpRequest,
    ModifyActionRequest,
    SubmitEvidenceRequest,
    TraceSpanItem,
    TriggerInvestigationRequest,
)
from backend.app.observability.tracer import get_tracer
from backend.app.utils.ids import generate_action_id, generate_case_id, generate_evidence_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("services.investigation")


class InvestigationService:
    """Core service managing fraud investigations, graph visualization, and analyst workflows."""

    def __init__(
        self,
        tg_client: Optional[TigerGraphClient] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.tg_client = tg_client or get_tigergraph_client()
        self.policy_engine = policy_engine or get_policy_engine()
        self._cases: Dict[str, FraudCaseState] = {}
        self.customer_mock = MockCustomerConfirmationService()
        self.auth_mock = MockStepUpAuthService()

    def register_case(self, state: FraudCaseState) -> None:
        """Register or update an investigation state in the in-memory cache."""
        self._cases[state.case_id] = state

    def get_case(self, case_id: str) -> Optional[FraudCaseState]:
        """Fetch investigation state by case_id."""
        return self._cases.get(case_id)

    async def start_investigation(self, request: TriggerInvestigationRequest) -> FraudCaseState:
        """Initialize and run an investigation through the LangGraph state machine."""
        cid = request.case_id or generate_case_id()

        initial_state = FraudCaseState(
            case_id=cid,
            trigger_type=request.trigger_type,
            transaction_id=request.transaction_id,
            customer_id=request.customer_id,
            account_ids=list(request.account_ids),
        )
        self.register_case(initial_state)

        logger.info("Starting investigation %s via LangGraph workflow", cid)
        final_state = await investigate_case(initial_state)
        self.register_case(final_state)
        return final_state

    def list_cases(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[CaseQueueItem]:
        """List summary queue items for the analyst dashboard."""
        items: List[CaseQueueItem] = []
        for state in list(self._cases.values()):
            if status is not None:
                current_status = state.case_status.value if hasattr(state.case_status, "value") else str(state.case_status)
                if current_status.upper() != status.upper():
                    continue

            risk_str = state.risk_level.value if state.risk_level else None
            status_str = state.case_status.value if hasattr(state.case_status, "value") else str(state.case_status)
            stop_str = state.stop_reason.value if state.stop_reason else None
            action_str = (
                state.post_evidence_next_best_action.action_type.value
                if state.post_evidence_next_best_action and hasattr(state.post_evidence_next_best_action.action_type, "value")
                else (str(state.post_evidence_next_best_action.action_type) if state.post_evidence_next_best_action else None)
            )

            # Extract created timestamp from earliest timeline event or now
            created_at = state.timeline[0].timestamp if state.timeline else now_iso()

            items.append(
                CaseQueueItem(
                    case_id=state.case_id,
                    trigger_type=state.trigger_type.value if hasattr(state.trigger_type, "value") else str(state.trigger_type),
                    risk_level=risk_str,
                    confidence=state.confidence,
                    status=status_str,
                    created_at=created_at,
                    stop_reason=stop_str,
                    primary_action=action_str,
                )
            )
            if len(items) >= limit:
                break
        return items

    def get_case_evidence(self, case_id: str) -> Optional[List[EvidenceCard]]:
        """Retrieve all normalized evidence items formatted as evidence cards."""
        state = self.get_case(case_id)
        if not state:
            return None

        cards: List[EvidenceCard] = []
        for item in state.all_evidence:
            supports = list(item.supports_hypotheses) if hasattr(item, "supports_hypotheses") and item.supports_hypotheses else []
            contradicts = list(item.contradicts_hypotheses) if hasattr(item, "contradicts_hypotheses") and item.contradicts_hypotheses else []
            cards.append(
                EvidenceCard(
                    evidence_id=item.evidence_id,
                    source=item.source,
                    source_reference=item.source_reference,
                    category=item.category.value if hasattr(item.category, "value") else str(item.category),
                    fact=item.fact,
                    reliability=item.reliability,
                    timestamp=item.timestamp,
                    supports_hypotheses=supports,
                    contradicts_hypotheses=contradicts,
                )
            )
        return cards

    def get_case_graph(self, case_id: str) -> Optional[GraphVisualizationResponse]:
        """Generate Cytoscape.js nodes and edges representing the case fraud network."""
        state = self.get_case(case_id)
        if not state:
            return None

        nodes: List[CytoscapeElement] = []
        edges: List[CytoscapeElement] = []
        seen_node_ids: Set[str] = set()

        def add_node(nid: str, label: str, ntype: str, classes: str, props: Optional[Dict[str, Any]] = None):
            if nid not in seen_node_ids:
                seen_node_ids.add(nid)
                nodes.append(
                    CytoscapeElement(
                        data=CytoscapeElementData(
                            id=nid,
                            label=label,
                            type=ntype,
                            properties=props or {},
                        ),
                        classes=classes,
                    )
                )

        def add_edge(eid: str, src: str, tgt: str, elabel: str, classes: str):
            edges.append(
                CytoscapeElement(
                    data=CytoscapeElementData(
                        id=eid,
                        label=elabel,
                        type="EDGE",
                        source=src,
                        target=tgt,
                    ),
                    classes=classes,
                )
            )

        # 1. FraudCase Central Node
        case_nid = f"CASE_{state.case_id}"
        add_node(
            case_nid,
            f"Case {state.case_id}",
            "CASE",
            "case-node",
            {"status": str(state.case_status), "risk": str(state.risk_level)},
        )

        # 2. Customer Node
        if state.customer_id:
            cust_nid = f"CUST_{state.customer_id}"
            add_node(cust_nid, f"Cust {state.customer_id}", "CUSTOMER", "customer-node")
            add_edge(f"edge_{case_nid}_{cust_nid}", case_nid, cust_nid, "INVESTIGATES_CUSTOMER", "case-edge")

        # 3. Account Nodes & Edges
        for acc in state.account_ids:
            acc_nid = f"ACC_{acc}"
            add_node(acc_nid, f"Account {acc}", "ACCOUNT", "account-node")
            add_edge(f"edge_{case_nid}_{acc_nid}", case_nid, acc_nid, "INVESTIGATES_ACCOUNT", "case-edge")
            if state.customer_id:
                add_edge(f"edge_{cust_nid}_{acc_nid}", cust_nid, acc_nid, "OWNS_ACCOUNT", "ownership-edge")

        # 4. Transaction Node & Edges
        if state.transaction_id:
            tx_nid = f"TX_{state.transaction_id}"
            add_node(tx_nid, f"Tx {state.transaction_id}", "TRANSACTION", "transaction-node")
            add_edge(f"edge_{case_nid}_{tx_nid}", case_nid, tx_nid, "INVESTIGATES_TRANSACTION", "case-edge")
            if state.account_ids:
                first_acc = f"ACC_{state.account_ids[0]}"
                add_edge(f"edge_{first_acc}_{tx_nid}", first_acc, tx_nid, "PERFORMED_TX", "tx-edge")

        # 5. Device Nodes from Evidence
        for dev_ev in state.device_evidence:
            dev_id = dev_ev.source_reference
            if dev_id:
                dev_nid = f"DEV_{dev_id}"
                add_node(dev_nid, f"Device {dev_id}", "DEVICE", "device-node")
                if state.transaction_id:
                    add_edge(f"edge_{tx_nid}_{dev_nid}", tx_nid, dev_nid, "USED_DEVICE", "device-edge")
                add_edge(f"edge_{case_nid}_{dev_nid}", case_nid, dev_nid, "INVESTIGATES_DEVICE", "case-edge")

        # Summary counts
        summary = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "accounts_count": len(state.account_ids),
            "devices_count": len(state.device_evidence),
        }

        return GraphVisualizationResponse(
            case_id=state.case_id,
            nodes=nodes,
            edges=edges,
            summary=summary,
        )

    def get_case_traces(self, case_id: str) -> Optional[InvestigationTraceResponse]:
        """Fetch structured audit trail spans for a case from local JSONL logs."""
        state = self.get_case(case_id)
        if not state:
            return None

        tracer = get_tracer()
        spans = tracer.read_traces(case_id)
        trace_file = str(tracer.get_trace_path(case_id))

        items: List[TraceSpanItem] = [
            TraceSpanItem(
                span_id=s.span_id,
                case_id=s.case_id,
                span_type=s.span_type.value if hasattr(s.span_type, "value") else str(s.span_type),
                name=s.name,
                start_time=s.start_time,
                end_time=s.end_time,
                duration_ms=s.duration_ms,
                status=s.status,
                metadata=s.metadata,
            )
            for s in spans
        ]

        total_duration = sum(s.duration_ms for s in spans)

        return InvestigationTraceResponse(
            case_id=case_id,
            total_spans=len(items),
            total_duration_ms=round(total_duration, 2),
            spans=items,
            trace_file_path=trace_file,
        )

    async def submit_additional_evidence(
        self,
        case_id: str,
        request: SubmitEvidenceRequest,
    ) -> Optional[FraudCaseState]:
        """Ingest manual or external evidence and re-trigger investigation reasoning."""
        state = self.get_case(case_id)
        if not state:
            return None

        ev_item = EvidenceItem(
            evidence_id=generate_evidence_id(),
            source="ANALYST_INPUT",
            source_reference=request.source_reference or "MANUAL_SUBMISSION",
            category=request.category,
            fact=request.fact,
            reliability=request.reliability,
            metadata=request.metadata,
        )
        state.received_evidence.append(ev_item)
        state.timeline.append(
            TimelineEvent(
                event_type="MANUAL_EVIDENCE_SUBMITTED",
                node_name="InvestigationService",
                description=f"Analyst submitted additional evidence: {request.fact[:60]}...",
                details={"evidence_id": ev_item.evidence_id},
            )
        )

        logger.info("Resuming investigation %s after additional evidence submission", case_id)
        updated_state = await investigate_case(state)
        self.register_case(updated_state)
        return updated_state

    async def process_approval_decision(
        self,
        case_id: str,
        status: ApprovalStatus,
        role: ApprovalRole = ApprovalRole.FRAUD_ANALYST,
        reviewer_id: Optional[str] = "ANALYST_01",
        comments: Optional[str] = None,
        modified_action: Optional[ActionType] = None,
    ) -> Optional[FraudCaseState]:
        """Process analyst decision (APPROVE, REJECT, MODIFY) and resume investigation."""
        state = self.get_case(case_id)
        if not state:
            return None

        # Determine target action
        action_type = (
            state.post_evidence_next_best_action.action_type
            if state.post_evidence_next_best_action
            else ActionType.MONITOR_ACCOUNT
        )

        mod_nba: Optional[NextBestAction] = None
        if status == ApprovalStatus.MODIFIED and modified_action:
            action_type = modified_action
            mod_nba = NextBestAction(
                action_id=generate_action_id(),
                action_type=modified_action,
                reasoning=f"Modified by analyst {reviewer_id}: {comments or 'Manual override'}",
            )

        decision = ApprovalDecision(
            action_type=action_type,
            status=status,
            reviewer_role=role,
            reviewer_id=reviewer_id,
            comments=comments,
            modified_action=mod_nba,
        )

        logger.info("Resuming investigation %s with analyst decision: %s", case_id, status)
        resumed_state = await investigate_case(state, analyst_decision=decision)
        self.register_case(resumed_state)
        return resumed_state

    async def stream_investigation_events(
        self,
        case_id: str,
    ) -> AsyncGenerator[str, None]:
        """Stream Server-Sent Events (SSE) for case timeline progression."""
        state = self.get_case(case_id)
        if not state:
            yield f"event: ERROR\ndata: {json.dumps({'error': f'Case {case_id} not found'})}\n\n"
            return

        sent_events: Set[str] = set()

        # Stream existing events first
        for evt in state.timeline:
            sent_events.add(evt.event_id)
            payload = {
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "node_name": evt.node_name,
                "description": evt.description,
                "timestamp": evt.timestamp,
                "details": evt.details,
            }
            yield f"event: {evt.event_type}\ndata: {json.dumps(payload)}\n\n"

        # Check if case is still running or finished
        is_finished = state.case_status in [CaseStatus.COMPLETED, CaseStatus.RESOLVED, CaseStatus.CLOSED]
        if is_finished:
            yield f"event: INVESTIGATION_STREAM_CLOSED\ndata: {json.dumps({'case_id': case_id, 'status': str(state.case_status)})}\n\n"
            return

        # Poll for new events up to 10 seconds for active cases
        for _ in range(5):
            await asyncio.sleep(0.5)
            latest_state = self.get_case(case_id)
            if not latest_state:
                break
            for evt in latest_state.timeline:
                if evt.event_id not in sent_events:
                    sent_events.add(evt.event_id)
                    payload = {
                        "event_id": evt.event_id,
                        "event_type": evt.event_type,
                        "node_name": evt.node_name,
                        "description": evt.description,
                        "timestamp": evt.timestamp,
                        "details": evt.details,
                    }
                    yield f"event: {evt.event_type}\ndata: {json.dumps(payload)}\n\n"

            if latest_state.case_status in [CaseStatus.COMPLETED, CaseStatus.RESOLVED, CaseStatus.CLOSED]:
                yield f"event: INVESTIGATION_STREAM_CLOSED\ndata: {json.dumps({'case_id': case_id, 'status': str(latest_state.case_status)})}\n\n"
                return

    def to_investigation_response(self, state: FraudCaseState) -> InvestigationResponse:
        """Convert FraudCaseState to typed InvestigationResponse schema."""
        risk_str = state.risk_level.value if state.risk_level else None
        status_str = state.case_status.value if hasattr(state.case_status, "value") else str(state.case_status)
        stop_str = state.stop_reason.value if state.stop_reason else None

        pre_action_dict = state.pre_evidence_next_best_action.model_dump() if state.pre_evidence_next_best_action else None
        requested_ev_dicts = [r.model_dump() for r in state.requested_evidence] if state.requested_evidence else []
        post_action_dict = state.post_evidence_next_best_action.model_dump() if state.post_evidence_next_best_action else None
        executed_dicts = [e.model_dump() for e in state.executed_actions]

        hypotheses_dicts = []
        if state.hypotheses:
            hypotheses_dicts = [h.model_dump() for h in state.hypotheses]
        elif state.risk_assessment and state.risk_assessment.hypotheses:
            hypotheses_dicts = [h.model_dump() for h in state.risk_assessment.hypotheses]

        missing_ev = list(state.missing_evidence) if state.missing_evidence else (
            list(state.risk_assessment.missing_evidence) if state.risk_assessment and state.risk_assessment.missing_evidence else []
        )

        similar_cases_dicts = []
        for ev in state.historical_case_evidence:
            meta = ev.metadata or {}
            cid = meta.get("case_id") or (ev.entity_ids[0] if ev.entity_ids else "HIST_CASE")
            similar_cases_dicts.append({
                "case_id": cid,
                "outcome": meta.get("outcome") or "UNKNOWN",
                "typology": meta.get("typology") or "GENERAL",
                "summary": ev.fact,
                "similarity_score": meta.get("combined_score", 0.85),
                "retrieval_method": meta.get("retrieval_method", "VECTOR"),
                "shared_entities": [e for e in ev.entity_ids if e != cid],
                "evidence_id": ev.evidence_id,
            })

        policy_context_dicts = []
        for ev in state.policy_evidence:
            meta = ev.metadata or {}
            policy_context_dicts.append({
                "policy_id": meta.get("source_id") or ev.evidence_id,
                "title": meta.get("section_title") or "Institutional Governance Rule",
                "document_type": meta.get("document_type") or ("REGULATION" if getattr(ev.category, "value", str(ev.category)) == "REGULATION" else "POLICY"),
                "text": ev.fact,
                "relevance_score": meta.get("relevance_score", 0.9),
                "graph_references": list(ev.entity_ids) if ev.entity_ids else [],
                "evidence_id": ev.evidence_id,
            })

        return InvestigationResponse(
            case_id=state.case_id,
            case_status=status_str,
            trigger_type=state.trigger_type.value if hasattr(state.trigger_type, "value") else str(state.trigger_type),
            transaction_id=state.transaction_id,
            customer_id=state.customer_id,
            account_ids=list(state.account_ids),
            risk_level=risk_str,
            risk_score=state.risk_score,
            confidence=state.confidence,
            evidence_completeness=state.evidence_completeness,
            stop_reason=stop_str,
            case_summary=state.case_summary,
            pre_evidence_action=pre_action_dict,
            requested_evidence=requested_ev_dicts,
            post_evidence_action=post_action_dict,
            approval_required=state.approval_required,
            approval_status=state.approval_status.value if state.approval_status else None,
            executed_actions=executed_dicts,
            sar_reference=state.sar_reference,
            is_persisted=state.is_persisted,
            is_indexed=state.is_indexed,
            hypotheses=hypotheses_dicts,
            missing_evidence=missing_ev,
            historical_ml_score=state.historical_ml_score,
            similar_cases=similar_cases_dicts,
            policy_context=policy_context_dicts,
            timeline_event_count=len(state.timeline),
            created_at=state.timeline[0].timestamp if state.timeline else now_iso(),
        )


_INVESTIGATION_SERVICE_INSTANCE: Optional[InvestigationService] = None


def get_investigation_service() -> InvestigationService:
    """Singleton provider for InvestigationService."""
    global _INVESTIGATION_SERVICE_INSTANCE
    if _INVESTIGATION_SERVICE_INSTANCE is None:
        _INVESTIGATION_SERVICE_INSTANCE = InvestigationService()
    return _INVESTIGATION_SERVICE_INSTANCE
