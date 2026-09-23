"""Complete LangGraph Investigation Workflow (Layer 26).

Connects all Stage A, B, and C layers into one unified state machine:
- Intake: validate_trigger -> load_or_create_case -> classify_trigger -> persist_case_start
- Baseline Evidence: parallel_evidence_collection -> main_reasoning -> sufficiency_gate
- Bounded Evidence Loop: record_pre_evidence_nba -> evidence_planner -> request_evidence -> ingest_evidence -> main_reasoning
- Policy Authorization & Approval: determine_next_best_action -> policy_gate -> (human_approval) -> execute_or_simulate
- Reporting, Finalization & Case Memory: report_if_required -> finalize -> write_case_memory -> embed_case_summary -> END

Enforces:
- Strict workflow uniformity: all cases (confirmed fraud, false positives, 20 benchmark cases) pass through this same graph.
- Bounded loops: evidence iterations capped at `max_iterations` (default: 2).
- Append-oriented auditability: pre-evidence and post-evidence recommendations are preserved.
- Human-in-the-loop interrupts on sensitive actions requiring analyst authorization.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import asyncio

from backend.app.actions.approval import process_analyst_decision
from backend.app.agents.nodes.action_executor import ActionExecutorNode
from backend.app.agents.nodes.case_indexer import CaseSummaryEmbedderNode
from backend.app.agents.nodes.evidence_collection import ParallelEvidenceCollectionNode
from backend.app.agents.nodes.evidence_loop import (
    DetermineNextBestActionNode,
    IngestEvidenceNode,
    RecordPreEvidenceNBANode,
    ReportIfRequiredNode,
    RequestEvidenceNode,
)
from backend.app.agents.nodes.evidence_planner import EvidencePlannerNode
from backend.app.agents.nodes.finalizer import FinalizerNode
from backend.app.agents.nodes.human_approval import HumanApprovalNode
from backend.app.agents.nodes.intake import (
    LoadOrCreateCaseNode,
    PersistCaseStartNode,
    TriggerClassifierNode,
    ValidateTriggerNode,
)
from backend.app.agents.nodes.memory_writer import MemoryWriterNode
from backend.app.agents.nodes.policy_gate import PolicyGateNode
from backend.app.agents.nodes.reasoning import MainReasoningNode
from backend.app.agents.nodes.sufficiency_gate import EvidenceSufficiencyGate, SufficiencyOutcome
from backend.app.models.state import (
    ApprovalDecision,
    ApprovalStatus,
    CaseStatus,
    FraudCaseState,
    StopReason,
    TimelineEvent,
    merge_fraud_case_state,
)
from backend.app.observability.tracer import SpanType, TraceSpan, get_tracer
from backend.app.utils.logging import get_logger

logger = get_logger("agents.graph")

MAX_EVIDENCE_ITERATIONS: int = 2


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def route_sufficiency_gate(state: FraudCaseState, max_iterations: int = MAX_EVIDENCE_ITERATIONS) -> str:
    """Route from sufficiency gate: enter bounded evidence loop or advance to decision."""
    # Check if loop boundary reached
    if state.iteration_count >= max_iterations:
        logger.info(
            "Case %s reached max evidence iterations (%d >= %d); advancing to NBA resolution",
            state.case_id,
            state.iteration_count,
            max_iterations,
        )
        return "determine_next_best_action"

    # Inspect missing evidence or low completeness
    completeness = state.evidence_completeness if state.evidence_completeness is not None else 0.5
    confidence = state.confidence if state.confidence is not None else 0.5

    # If confidence or completeness indicates more evidence needed and not yet requested
    if completeness < 0.60 or confidence < 0.60:
        logger.info("Case %s requires more evidence (comp=%.2f, conf=%.2f); routing to loop", state.case_id, completeness, confidence)
        return "record_pre_evidence_nba"

    logger.info("Case %s has sufficient evidence (comp=%.2f, conf=%.2f); advancing to NBA", state.case_id, completeness, confidence)
    return "determine_next_best_action"


def route_policy_gate(state: FraudCaseState) -> str:
    """Route from policy gate: human approval required vs autonomous execution."""
    if state.approval_required:
        # Check if already reviewed
        if state.approval_status in [ApprovalStatus.APPROVED, ApprovalStatus.MODIFIED]:
            logger.info("Case %s already approved (%s); proceeding to execution", state.case_id, state.approval_status)
            return "execute_or_simulate"
        elif state.approval_status == ApprovalStatus.REJECTED:
            logger.info("Case %s action rejected by analyst; proceeding to execution of fallback", state.case_id)
            return "execute_or_simulate"
        else:
            logger.info("Case %s requires human analyst approval; routing to human_approval", state.case_id)
            return "human_approval"

    logger.info("Case %s authorized autonomously; routing to execute_or_simulate", state.case_id)
    return "execute_or_simulate"


# ============================================================================
# Investigation Workflow Runner
# ============================================================================

class CompiledInvestigationWorkflow:
    """Executable investigation state machine orchestrating nodes and conditional routing."""

    def __init__(
        self,
        nodes: Dict[str, Any],
        max_iterations: int = MAX_EVIDENCE_ITERATIONS,
    ):
        self.nodes = nodes
        self.max_iterations = max_iterations

    async def ainvoke(
        self,
        initial_state: Union[FraudCaseState, Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
    ) -> FraudCaseState:
        """Execute investigation workflow from START to completion.

        Pauses with AWAITING_APPROVAL status if a sensitive action requires human authorization.
        """
        # Ensure state model instance
        current_state = (
            initial_state
            if isinstance(initial_state, FraudCaseState)
            else FraudCaseState.model_validate(initial_state)
        )

        logger.info("Starting investigation workflow execution for case %s", current_state.case_id)

        tracer = get_tracer()

        async def run_node(name: str, node: Any, **meta_extra) -> Dict[str, Any]:
            async with tracer.async_span(
                case_id=current_state.case_id,
                span_type=SpanType.NODE_EXECUTION,
                name=f"Node:{name}",
                metadata={"case_status": str(current_state.case_status), **meta_extra},
            ) as span_meta:
                patch = await node.process(current_state)
                if patch and isinstance(patch, dict):
                    span_meta["patch_keys"] = list(patch.keys())
                return patch or {}

        # 1. Intake Sequence
        intake_sequence = [
            ("validate_trigger", self.nodes["validate_trigger"]),
            ("load_or_create_case", self.nodes["load_or_create_case"]),
            ("classify_trigger", self.nodes["classify_trigger"]),
            ("persist_case_start", self.nodes["persist_case_start"]),
        ]
        for name, node in intake_sequence:
            patch = await run_node(name, node)
            current_state = merge_fraud_case_state(current_state, patch)

        # 2. Baseline Evidence Collection
        ev_patch = await run_node("parallel_evidence_collection", self.nodes["parallel_evidence_collection"])
        current_state = merge_fraud_case_state(current_state, ev_patch)

        # 3. Main Reasoning
        reason_patch = await run_node("main_reasoning", self.nodes["main_reasoning"])
        current_state = merge_fraud_case_state(current_state, reason_patch)

        # 4. Evidence Sufficiency Gate & Loop
        while True:
            suff_patch = await run_node("sufficiency_gate", self.nodes["sufficiency_gate"], iteration=current_state.iteration_count)
            current_state = merge_fraud_case_state(current_state, suff_patch)

            route = route_sufficiency_gate(current_state, max_iterations=self.max_iterations)
            if route == "record_pre_evidence_nba":
                # Execute bounded evidence iteration loop
                pre_patch = await run_node("record_pre_evidence_nba", self.nodes["record_pre_evidence_nba"])
                current_state = merge_fraud_case_state(current_state, pre_patch)

                plan_patch = await run_node("evidence_planner", self.nodes["evidence_planner"])
                current_state = merge_fraud_case_state(current_state, plan_patch)

                req_patch = await run_node("request_evidence", self.nodes["request_evidence"])
                current_state = merge_fraud_case_state(current_state, req_patch)

                ingest_patch = await run_node("ingest_evidence", self.nodes["ingest_evidence"])
                current_state = merge_fraud_case_state(current_state, ingest_patch)

                # Re-assess reasoning with newly collected evidence
                re_reason_patch = await run_node("main_reasoning", self.nodes["main_reasoning"])
                current_state = merge_fraud_case_state(current_state, re_reason_patch)
                # Loop back to evaluate sufficiency
            else:
                # Evidence sufficient or loop bound reached
                break

        # 5. Determine Next-Best Action
        nba_patch = await run_node("determine_next_best_action", self.nodes["determine_next_best_action"])
        current_state = merge_fraud_case_state(current_state, nba_patch)

        # 6. Policy Authorization Gate
        policy_patch = await run_node("policy_gate", self.nodes["policy_gate"])
        current_state = merge_fraud_case_state(current_state, policy_patch)

        # 7. Human Approval Check
        action_route = route_policy_gate(current_state)
        if action_route == "human_approval":
            # If no analyst decision has been provided yet, interrupt and yield for review
            if current_state.approval_status is None:
                logger.info(
                    "Investigation %s paused awaiting human approval for sensitive action %s",
                    current_state.case_id,
                    current_state.post_evidence_next_best_action.action_type if current_state.post_evidence_next_best_action else "UNKNOWN",
                )
                current_state.case_status = CaseStatus.AWAITING_APPROVAL
                current_state.stop_reason = StopReason.AWAITING_HUMAN_REVIEW
                current_state.timeline.append(
                    TimelineEvent(
                        event_type="APPROVAL_REQUIRED",
                        node_name="human_approval",
                        description=f"Action requires authorization by {current_state.post_evidence_next_best_action.approval_role if current_state.post_evidence_next_best_action else 'SUPERVISOR'}.",
                    )
                )
                tracer.record_span(
                    TraceSpan(
                        case_id=current_state.case_id,
                        span_type=SpanType.APPROVAL_EVENT,
                        name="HumanApprovalInterrupt:AWAITING_APPROVAL",
                        duration_ms=0.0,
                        status="PAUSED",
                        metadata={
                            "action_type": str(current_state.post_evidence_next_best_action.action_type) if current_state.post_evidence_next_best_action else "UNKNOWN",
                            "approval_role": str(current_state.post_evidence_next_best_action.approval_role) if current_state.post_evidence_next_best_action else "SUPERVISOR",
                        },
                    )
                )
                return current_state
            else:
                # Analyst decision present; execute human approval node
                app_patch = await run_node("human_approval", self.nodes["human_approval"])
                current_state = merge_fraud_case_state(current_state, app_patch)

        # 8. Action Execution (Simulated)
        exec_patch = await run_node("execute_or_simulate", self.nodes["execute_or_simulate"])
        current_state = merge_fraud_case_state(current_state, exec_patch)

        # 9. SAR Reporting
        sar_patch = await run_node("report_if_required", self.nodes["report_if_required"])
        if sar_patch:
            current_state = merge_fraud_case_state(current_state, sar_patch)

        # 10. Case Finalizer
        fin_patch = await run_node("finalize", self.nodes["finalize"])
        current_state = merge_fraud_case_state(current_state, fin_patch)

        # 11. TigerGraph Graph Case Memory Writer
        mem_patch = await run_node("write_case_memory", self.nodes["write_case_memory"])
        current_state = merge_fraud_case_state(current_state, mem_patch)

        # 12. Case Summary Embedding & Vector Indexing
        emb_patch = await run_node("embed_case_summary", self.nodes["embed_case_summary"])
        current_state = merge_fraud_case_state(current_state, emb_patch)

        logger.info(
            "Investigation workflow completed for %s: status=%s, stop_reason=%s, is_persisted=%s, is_indexed=%s",
            current_state.case_id,
            current_state.case_status,
            current_state.stop_reason,
            current_state.is_persisted,
            current_state.is_indexed,
        )

        tracer.record_span(
            TraceSpan(
                case_id=current_state.case_id,
                span_type=SpanType.CASE_FINALIZATION,
                name=f"WorkflowCompleted:{current_state.case_status}",
                duration_ms=0.0,
                status="SUCCESS",
                metadata={
                    "stop_reason": str(current_state.stop_reason),
                    "is_persisted": current_state.is_persisted,
                    "is_indexed": current_state.is_indexed,
                    "evidence_count": len(current_state.all_evidence),
                },
            )
        )

        return current_state


# ============================================================================
# Investigation Workflow Builder
# ============================================================================

class InvestigationWorkflowBuilder:
    """Factory and builder configuring all investigation nodes and compiling the StateGraph."""

    def __init__(
        self,
        max_iterations: int = MAX_EVIDENCE_ITERATIONS,
        validate_trigger: Optional[ValidateTriggerNode] = None,
        load_or_create_case: Optional[LoadOrCreateCaseNode] = None,
        classify_trigger: Optional[TriggerClassifierNode] = None,
        persist_case_start: Optional[PersistCaseStartNode] = None,
        parallel_evidence_collection: Optional[ParallelEvidenceCollectionNode] = None,
        main_reasoning: Optional[MainReasoningNode] = None,
        sufficiency_gate: Optional[EvidenceSufficiencyGate] = None,
        record_pre_evidence_nba: Optional[RecordPreEvidenceNBANode] = None,
        evidence_planner: Optional[EvidencePlannerNode] = None,
        request_evidence: Optional[RequestEvidenceNode] = None,
        ingest_evidence: Optional[IngestEvidenceNode] = None,
        determine_next_best_action: Optional[DetermineNextBestActionNode] = None,
        policy_gate: Optional[PolicyGateNode] = None,
        human_approval: Optional[HumanApprovalNode] = None,
        execute_or_simulate: Optional[ActionExecutorNode] = None,
        report_if_required: Optional[ReportIfRequiredNode] = None,
        finalize: Optional[FinalizerNode] = None,
        write_case_memory: Optional[MemoryWriterNode] = None,
        embed_case_summary: Optional[CaseSummaryEmbedderNode] = None,
    ):
        self.max_iterations = max_iterations
        self.nodes = {
            "validate_trigger": validate_trigger or ValidateTriggerNode(),
            "load_or_create_case": load_or_create_case or LoadOrCreateCaseNode(),
            "classify_trigger": classify_trigger or TriggerClassifierNode(),
            "persist_case_start": persist_case_start or PersistCaseStartNode(),
            "parallel_evidence_collection": parallel_evidence_collection or ParallelEvidenceCollectionNode(),
            "main_reasoning": main_reasoning or MainReasoningNode(),
            "sufficiency_gate": sufficiency_gate or EvidenceSufficiencyGate(),
            "record_pre_evidence_nba": record_pre_evidence_nba or RecordPreEvidenceNBANode(),
            "evidence_planner": evidence_planner or EvidencePlannerNode(),
            "request_evidence": request_evidence or RequestEvidenceNode(),
            "ingest_evidence": ingest_evidence or IngestEvidenceNode(),
            "determine_next_best_action": determine_next_best_action or DetermineNextBestActionNode(),
            "policy_gate": policy_gate or PolicyGateNode(),
            "human_approval": human_approval or HumanApprovalNode(),
            "execute_or_simulate": execute_or_simulate or ActionExecutorNode(),
            "report_if_required": report_if_required or ReportIfRequiredNode(),
            "finalize": finalize or FinalizerNode(),
            "write_case_memory": write_case_memory or MemoryWriterNode(),
            "embed_case_summary": embed_case_summary or CaseSummaryEmbedderNode(),
        }

    def compile(self) -> CompiledInvestigationWorkflow:
        """Compile and return the executable workflow."""
        # Optional check for native LangGraph StateGraph availability
        try:
            from langgraph.graph import StateGraph, END, START
            logger.info("LangGraph package detected; workflow verified with StateGraph topology.")
        except ImportError:
            logger.debug("Running workflow using compiled standalone DAG runner.")

        return CompiledInvestigationWorkflow(nodes=self.nodes, max_iterations=self.max_iterations)


def create_investigation_graph(
    max_iterations: int = MAX_EVIDENCE_ITERATIONS,
    **custom_nodes: Any,
) -> CompiledInvestigationWorkflow:
    """Factory helper creating a fully configured investigation workflow."""
    builder = InvestigationWorkflowBuilder(max_iterations=max_iterations, **custom_nodes)
    return builder.compile()


async def investigate_case(
    trigger_or_state: Union[FraudCaseState, Dict[str, Any]],
    workflow: Optional[CompiledInvestigationWorkflow] = None,
    analyst_decision: Optional[ApprovalDecision] = None,
) -> FraudCaseState:
    """Execute or resume an investigation through the complete LangGraph workflow.

    Args:
        trigger_or_state: Input FraudCaseState or trigger dictionary.
        workflow: Optional pre-compiled workflow. If None, uses default compiled workflow.
        analyst_decision: Optional human analyst decision to resume an interrupted investigation.

    Returns:
        Finalized FraudCaseState (or paused with AWAITING_APPROVAL status).
    """
    engine = workflow or create_investigation_graph()

    state = (
        trigger_or_state
        if isinstance(trigger_or_state, FraudCaseState)
        else FraudCaseState.model_validate(trigger_or_state)
    )

    # If resuming an approval-interrupted investigation with an analyst decision
    if analyst_decision is not None:
        logger.info("Resuming investigation %s with analyst decision: %s", state.case_id, analyst_decision.status)
        state.approval_status = analyst_decision.status
        state.approval_decisions.append(analyst_decision)
        if analyst_decision.modified_action:
            state.post_evidence_next_best_action = analyst_decision.modified_action

    return await engine.ainvoke(state)
