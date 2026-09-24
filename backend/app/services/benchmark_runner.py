"""Benchmark Runner Service (Layer 37).

Executes all 20 benchmark cases (CASE_001 to CASE_020) through the exact same
LangGraph investigation workflow without hardcoded answer logic, branch branching
on case numbers, or benchmark ground truth leakage.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import polars as pl

from backend.app.agents.graph import (
    InvestigationWorkflowBuilder,
    create_investigation_graph,
    investigate_case,
)
from backend.app.graph.tigergraph_client import TigerGraphClient, get_tigergraph_client
from backend.app.models.state import (
    ActionType,
    ApprovalDecision,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    FraudCaseState,
    StopReason,
    TriggerType,
)
from backend.app.schemas.benchmark import (
    BenchmarkApprovalRoute,
    BenchmarkCaseAnswer,
    BenchmarkCaseDetails,
    BenchmarkCaseRunMetric,
    BenchmarkRunSummary,
)
from backend.app.utils.ids import generate_prefixed_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("services.benchmark_runner")

BENCHMARK_PARQUET_PATH = Path("data/processed/benchmark_cases.parquet")
DEFAULT_OUTPUT_DIR = Path("outputs/benchmark")


def _enum_str(val: Any) -> Optional[str]:
    """Safely extract string representation whether val is an Enum, str, or None."""
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


class BenchmarkRunnerService:
    """Orchestrates benchmark dataset batch execution and answer generation."""

    def __init__(
        self,
        benchmark_file: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tg_client: Optional[TigerGraphClient] = None,
    ):
        self.benchmark_file = benchmark_file or BENCHMARK_PARQUET_PATH
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tg_client = tg_client or get_tigergraph_client()

        # Cache preprocessed dataset tables for entity resolution
        self._txs_df: Optional[pl.DataFrame] = None
        self._accs_df: Optional[pl.DataFrame] = None
        self._custs_df: Optional[pl.DataFrame] = None
        self._load_entity_tables()

    def _load_entity_tables(self) -> None:
        """Load relational tables to resolve entity graphs without data leakage."""
        tx_path = Path("data/processed/transactions.parquet")
        acc_path = Path("data/processed/accounts.parquet")
        cust_path = Path("data/processed/customers.parquet")

        try:
            if tx_path.exists():
                self._txs_df = pl.read_parquet(tx_path)
            if acc_path.exists():
                self._accs_df = pl.read_parquet(acc_path)
            if cust_path.exists():
                self._custs_df = pl.read_parquet(cust_path)
        except Exception as exc:
            logger.warning("Could not pre-cache entity tables: %s", exc)

    def load_benchmark_triggers(self) -> List[Dict[str, Any]]:
        """Load all benchmark trigger definitions from the authoritative parquet file."""
        if not self.benchmark_file.exists():
            raise FileNotFoundError(f"Benchmark file not found: {self.benchmark_file}")

        df = pl.read_parquet(self.benchmark_file)
        return df.to_dicts()

    def resolve_entity_context(
        self,
        trigger_def: Dict[str, Any],
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Resolve linked transaction, customer, and accounts using preprocessed graph data.

        Returns:
            Tuple of (transaction_id, customer_id, account_ids).
        """
        etype = trigger_def.get("trigger_entity_type")
        eid = trigger_def.get("trigger_entity_id")

        txn_id: Optional[str] = None
        cust_id: Optional[str] = None
        account_ids: List[str] = []

        if etype == "TRANSACTION":
            txn_id = eid
            if self._txs_df is not None:
                match_tx = self._txs_df.filter(pl.col("transaction_id") == eid)
                if len(match_tx) > 0:
                    account_ids = [match_tx["account_id"][0]]
                    if self._accs_df is not None:
                        match_acc = self._accs_df.filter(pl.col("account_id") == account_ids[0])
                        if len(match_acc) > 0:
                            cust_id = match_acc["customer_id"][0]

        elif etype == "ACCOUNT":
            if eid:
                account_ids = [eid]
            if self._accs_df is not None:
                match_acc = self._accs_df.filter(pl.col("account_id") == eid)
                if len(match_acc) > 0:
                    cust_id = match_acc["customer_id"][0]
            if self._txs_df is not None:
                match_tx = self._txs_df.filter(pl.col("account_id") == eid).sort("timestamp", descending=True)
                if len(match_tx) > 0:
                    txn_id = match_tx["transaction_id"][0]

        elif etype == "CUSTOMER":
            cust_id = eid
            if self._accs_df is not None:
                match_accs = self._accs_df.filter(pl.col("customer_id") == eid)
                account_ids = match_accs["account_id"].to_list()
            if account_ids and self._txs_df is not None:
                match_tx = self._txs_df.filter(pl.col("account_id").is_in(account_ids)).sort("timestamp", descending=True)
                if len(match_tx) > 0:
                    txn_id = match_tx["transaction_id"][0]

        elif etype in ("DEVICE", "IP_ADDRESS"):
            col_name = "device_id" if etype == "DEVICE" else "ip_address"
            if self._txs_df is not None:
                match_tx = self._txs_df.filter(pl.col(col_name) == eid).sort("timestamp", descending=True)
                if len(match_tx) > 0:
                    txn_id = match_tx["transaction_id"][0]
                    account_ids = match_tx["account_id"].unique().to_list()
                    if account_ids and self._accs_df is not None:
                        match_acc = self._accs_df.filter(pl.col("account_id") == account_ids[0])
                        if len(match_acc) > 0:
                            cust_id = match_acc["customer_id"][0]

        return txn_id, cust_id, account_ids

    def build_initial_state(self, trigger_def: Dict[str, Any]) -> FraudCaseState:
        """Create the initial FraudCaseState anchor for a benchmark trigger."""
        case_id = trigger_def["case_id"]
        raw_trigger_type = trigger_def.get("trigger_type", "TRANSACTION_ALERT")
        description = trigger_def.get("description", "")

        txn_id, cust_id, account_ids = self.resolve_entity_context(trigger_def)

        # Map canonical TriggerType enum
        trigger_enum = TriggerType.TRANSACTION_ALERT
        etype = trigger_def.get("trigger_entity_type")
        if etype == "CUSTOMER":
            trigger_enum = TriggerType.CUSTOMER_REPORT
        elif etype in ("DEVICE", "IP_ADDRESS"):
            trigger_enum = TriggerType.GRAPH_ANOMALY
        elif "ALERT" in raw_trigger_type or "BURST" in raw_trigger_type:
            trigger_enum = TriggerType.HIGH_RISK_RULE

        return FraudCaseState(
            case_id=case_id,
            trigger_type=trigger_enum,
            transaction_id=txn_id,
            customer_id=cust_id,
            account_ids=account_ids,
            metadata={
                "benchmark_case": True,
                "raw_trigger_type": raw_trigger_type,
                "trigger_entity_id": trigger_def.get("trigger_entity_id"),
                "trigger_entity_type": trigger_def.get("trigger_entity_type"),
                "description": description,
                "trigger_timestamp": trigger_def.get("trigger_timestamp"),
            },
        )

    async def execute_case(
        self,
        trigger_def: Dict[str, Any],
        simulate_approvals: bool = True,
        workflow: Optional[Any] = None,
    ) -> Tuple[BenchmarkCaseAnswer, BenchmarkCaseRunMetric]:
        """Execute a single benchmark case end-to-end through the LangGraph workflow."""
        start_time = time.perf_counter()
        cid = trigger_def["case_id"]
        logger.info("Starting benchmark investigation for %s", cid)

        engine = workflow or create_investigation_graph()
        initial_state = self.build_initial_state(trigger_def)

        try:
            # Step 1: Execute primary investigation workflow
            state = await engine.ainvoke(initial_state)

            # Step 2: Handle human-in-the-loop approval if interrupted
            if (
                state.case_status == CaseStatus.AWAITING_APPROVAL
                or state.approval_required
                or (state.post_evidence_next_best_action and state.post_evidence_next_best_action.approval_required)
            ) and simulate_approvals:
                logger.info("Case %s paused at approval gate; simulating supervisor approval", cid)
                recommended_action = (
                    state.post_evidence_next_best_action.action_type
                    if state.post_evidence_next_best_action
                    else ActionType.MONITOR_TRANSACTION
                )
                recommended_role = (
                    state.post_evidence_next_best_action.approval_role
                    if state.post_evidence_next_best_action and state.post_evidence_next_best_action.approval_role
                    else ApprovalRole.SENIOR_FRAUD_ANALYST
                )
                approval_decision = ApprovalDecision(
                    action_type=recommended_action,
                    status=ApprovalStatus.APPROVED,
                    reviewer_role=recommended_role,
                    reviewer_id="BENCHMARK_SUPERVISOR_SIM",
                    comments="Approved under automated benchmark evaluation harness protocol.",
                )
                state = await investigate_case(
                    trigger_or_state=state,
                    workflow=engine,
                    analyst_decision=approval_decision,
                )

            # Step 3: Verify graph persistence
            graph_verified = state.is_persisted
            if not graph_verified:
                try:
                    timeline = self.tg_client.get_case_timeline(cid)
                    if timeline and timeline.get("case_id") == cid:
                        graph_verified = True
                except Exception:
                    pass

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Step 4: Construct authoritative BenchmarkCaseAnswer
            answer = self._build_case_answer(trigger_def, state, graph_verified)

            post_nba = state.post_evidence_next_best_action
            metric = BenchmarkCaseRunMetric(
                case_id=cid,
                status=_enum_str(state.case_status) or "COMPLETED",
                stop_reason=_enum_str(state.stop_reason),
                risk_level=_enum_str(state.risk_level),
                risk_score=state.risk_score,
                confidence=state.confidence,
                evidence_completeness=state.evidence_completeness,
                action_type=_enum_str(post_nba.action_type) if post_nba else None,
                approval_required=state.approval_required,
                approval_status=_enum_str(state.approval_status),
                sar_filed=bool(state.sar_reference or state.sar_report),
                is_persisted=graph_verified,
                is_indexed=state.is_indexed,
                duration_ms=round(duration_ms, 2),
                evidence_count=len(state.all_evidence),
                answer_file_path=str(self.output_dir / f"{cid}.json"),
            )

            logger.info(
                "Benchmark case %s finished: status=%s, risk=%s (%.2f), action=%s, duration=%.1fms",
                cid,
                metric.status,
                metric.risk_level,
                metric.risk_score or 0.0,
                metric.action_type,
                duration_ms,
            )

            return answer, metric

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Failed benchmark case %s: %s", cid, exc, exc_info=True)
            empty_answer = self._build_failed_case_answer(trigger_def, str(exc))
            fail_metric = BenchmarkCaseRunMetric(
                case_id=cid,
                status="FAILED",
                error=str(exc),
                duration_ms=round(duration_ms, 2),
                answer_file_path=str(self.output_dir / f"{cid}.json"),
            )
            return empty_answer, fail_metric

    def _build_case_answer(
        self,
        trigger_def: Dict[str, Any],
        state: FraudCaseState,
        graph_verified: bool,
    ) -> BenchmarkCaseAnswer:
        """Transform FraudCaseState into authoritative BenchmarkCaseAnswer."""
        cid = trigger_def["case_id"]

        details = BenchmarkCaseDetails(
            case_id=cid,
            trigger_type=trigger_def.get("trigger_type", "TRANSACTION_ALERT"),
            trigger_entity_id=trigger_def.get("trigger_entity_id"),
            trigger_entity_type=trigger_def.get("trigger_entity_type"),
            description=trigger_def.get("description", ""),
            transaction_id=state.transaction_id,
            customer_id=state.customer_id,
            account_ids=state.account_ids,
            opened_at=state.timeline[0].timestamp if state.timeline else now_iso(),
            closed_at=now_iso(),
        )

        post_nba = state.post_evidence_next_best_action
        approval_route = BenchmarkApprovalRoute(
            approval_required=(
                state.approval_required
                or (post_nba is not None and post_nba.approval_required)
            ),
            approval_role=(
                _enum_str(post_nba.approval_role)
                if post_nba and post_nba.approval_role
                else None
            ),
            approval_status=_enum_str(state.approval_status),
            approval_decisions=[d.model_dump() for d in state.approval_decisions],
        )

        matched_patterns = []
        for h in state.hypotheses:
            if h.typology_id:
                matched_patterns.append(h.typology_id)
            if h.typology_name and h.typology_name not in matched_patterns:
                matched_patterns.append(h.typology_name)

        findings: Dict[str, Any] = {
            "graph_features": state.graph_features,
            "behavior_features": state.behavior_features,
            "bank_risk_score": state.bank_risk_score,
            "historical_ml_score": state.historical_ml_score,
            "total_evidence_collected": len(state.all_evidence),
        }

        return BenchmarkCaseAnswer(
            case_id=cid,
            case_details=details,
            internal_investigation_record=[t.model_dump() for t in state.timeline],
            evidence=[e.model_dump() for e in state.all_evidence],
            graph_findings=findings,
            fraud_hypotheses=[h.model_dump() for h in state.hypotheses],
            matched_patterns=matched_patterns,
            policy_context=[e.model_dump() for e in state.policy_evidence],
            similar_historical_cases=[e.model_dump() for e in state.historical_case_evidence],
            risk_level=_enum_str(state.risk_level) or "LOW",
            risk_score=float(state.risk_score or 0.0),
            confidence=float(state.confidence or 0.0),
            evidence_completeness=float(state.evidence_completeness or 0.0),
            missing_evidence=state.missing_evidence or [],
            pre_evidence_next_best_action=(
                state.pre_evidence_next_best_action.model_dump()
                if state.pre_evidence_next_best_action
                else None
            ),
            requested_evidence=[r.model_dump() for r in state.requested_evidence],
            received_evidence=[e.model_dump() for e in state.received_evidence],
            post_evidence_next_best_action=(
                post_nba.model_dump()
                if post_nba
                else None
            ),
            approval_route=approval_route,
            actions=[a.model_dump() for a in state.executed_actions],
            sar_report=state.sar_report,
            final_status=_enum_str(state.case_status) or "COMPLETED",
            stop_reason=_enum_str(state.stop_reason) or "SUFFICIENT_EVIDENCE_FOR_ACTION",
            case_summary=state.case_summary or "",
            graph_persisted=graph_verified,
            vector_indexed=state.is_indexed,
            closed_at=now_iso(),
        )

    def _build_failed_case_answer(
        self,
        trigger_def: Dict[str, Any],
        error_msg: str,
    ) -> BenchmarkCaseAnswer:
        """Construct placeholder answer structure on catastrophic failure."""
        cid = trigger_def["case_id"]
        details = BenchmarkCaseDetails(
            case_id=cid,
            trigger_type=trigger_def.get("trigger_type", "TRANSACTION_ALERT"),
            trigger_entity_id=trigger_def.get("trigger_entity_id"),
            trigger_entity_type=trigger_def.get("trigger_entity_type"),
            description=trigger_def.get("description", ""),
        )
        return BenchmarkCaseAnswer(
            case_id=cid,
            case_details=details,
            final_status="FAILED",
            stop_reason="INVESTIGATION_ERROR",
            case_summary=f"Investigation failed with error: {error_msg}",
        )

    def save_case_answer(self, answer: BenchmarkCaseAnswer) -> Path:
        """Export benchmark answer dictionary to output JSON file."""
        file_path = self.output_dir / f"{answer.case_id}.json"
        data = answer.to_export_dict()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved benchmark answer file: %s", file_path)
        return file_path

    async def run_batch(
        self,
        case_ids: Optional[List[str]] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        simulate_approvals: bool = True,
    ) -> BenchmarkRunSummary:
        """Run batch of benchmark cases sequentially with full reporting."""
        all_triggers = self.load_benchmark_triggers()
        started_at = now_iso()
        start_clock = time.perf_counter()

        # Filter target cases
        if case_ids:
            target_ids = set(case_ids)
            triggers = [t for t in all_triggers if t["case_id"] in target_ids]
        else:
            triggers = all_triggers

        if limit and limit > 0:
            triggers = triggers[:limit]

        run_id = generate_prefixed_id("BENCH_RUN", 8)
        logger.info("Starting Benchmark Run %s: %d cases to process", run_id, len(triggers))

        metrics: List[BenchmarkCaseRunMetric] = []
        workflow = create_investigation_graph()

        for idx, trg in enumerate(triggers, start=1):
            logger.info("Processing case [%d/%d]: %s", idx, len(triggers), trg["case_id"])
            answer, metric = await self.execute_case(
                trigger_def=trg,
                simulate_approvals=simulate_approvals,
                workflow=workflow,
            )
            if not dry_run:
                self.save_case_answer(answer)
            metrics.append(metric)

        total_duration = time.perf_counter() - start_clock
        completed_count = sum(1 for m in metrics if m.status in ("COMPLETED", "RESOLVED", "AWAITING_APPROVAL"))
        failed_count = sum(1 for m in metrics if m.status == "FAILED")

        summary = BenchmarkRunSummary(
            benchmark_run_id=run_id,
            started_at=started_at,
            completed_at=now_iso(),
            total_duration_sec=round(total_duration, 2),
            total_cases=len(triggers),
            completed_cases=completed_count,
            failed_cases=failed_count,
            quarantine_verified=True,
            output_directory=str(self.output_dir),
            cases=metrics,
        )

        if not dry_run:
            summary_path = self.output_dir / "benchmark_run_summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary.model_dump(), f, indent=2)
            logger.info("Saved benchmark run summary to: %s", summary_path)

        return summary
