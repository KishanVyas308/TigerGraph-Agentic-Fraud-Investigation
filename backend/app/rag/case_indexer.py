"""Case Memory Indexer Service (Layer 25).

Synthesizes grounded case summaries from finalized investigation state,
generates SentenceTransformer embedding vectors, and persists case precedents
into the GraphRAG case memory vector index.

Strictly quarantines benchmark test cases (CASE_001 to CASE_020) to prevent
benchmark outcome leakage into precedent memory.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.models.state import (
    ActionType,
    ApprovalStatus,
    FraudCaseState,
    RiskLevel,
    StopReason,
)
from backend.app.rag.case_memory import (
    CaseMemoryIndex,
    CaseMemoryRecord,
    is_benchmark_case,
)
from backend.app.rag.embeddings import compute_embedding
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("rag.case_indexer")


class CaseIndexingReceipt(BaseModel):
    """Receipt documenting case summary vectorization and indexing into case memory."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    case_id: str
    chunk_id: Optional[str] = None
    outcome: str
    primary_typology: str
    summary_text: str = ""
    summary_length: int = 0
    embedding_dim: int = 0
    is_indexed: bool = False
    quarantined: bool = False
    quarantine_reason: Optional[str] = None
    index_path: Optional[str] = None
    timestamp: str = Field(default_factory=now_iso)


class CaseMemoryIndexer:
    """Service to vectorize and index finalized investigations into reusable case memory."""

    def __init__(
        self,
        index: Optional[CaseMemoryIndex] = None,
        data_dir: Optional[Path] = None,
    ):
        settings = get_settings()
        self.data_dir = data_dir or settings.PROCESSED_DATA_DIR
        if index is not None:
            self.index = index
        else:
            self.index = CaseMemoryIndex()
            case_path = self.data_dir / "case_memory_index.parquet"
            if case_path.exists():
                try:
                    self.index.load_from_parquet(case_path)
                except Exception as exc:
                    logger.warning("Could not load case memory index from %s: %s", case_path, exc)

    def build_grounded_case_summary(self, state: FraudCaseState) -> str:
        """Synthesize a concise, factual summary text grounded entirely in verified state."""
        # 1. Identity & Trigger
        sections: List[str] = [
            f"Case {state.case_id} [Trigger: {state.trigger_type.value if hasattr(state.trigger_type, 'value') else state.trigger_type}]."
        ]

        # 2. Investigated Entities
        entities: List[str] = []
        if state.transaction_id:
            entities.append(f"Tx: {state.transaction_id}")
        if state.customer_id:
            entities.append(f"Cust: {state.customer_id}")
        if state.account_ids:
            entities.append(f"Accounts: {', '.join(state.account_ids)}")
        if entities:
            sections.append(f"Investigated Entities: {'; '.join(entities)}.")

        # 3. Graph Signals
        graph_facts: List[str] = []
        gf = state.graph_features or {}
        if gf.get("shared_device_account_count", 0) > 1:
            graph_facts.append(f"Shared device across {gf['shared_device_account_count']} accounts")
        if gf.get("shared_ip_account_count", 0) > 1:
            graph_facts.append(f"Shared IP across {gf['shared_ip_account_count']} accounts")
        if gf.get("fraud_neighbors_count", 0) > 0:
            graph_facts.append(f"{gf['fraud_neighbors_count']} fraud-linked graph neighbors")
        if gf.get("shortest_distance_to_fraud") is not None:
            graph_facts.append(f"Shortest distance to confirmed fraud: {gf['shortest_distance_to_fraud']}")
        if gf.get("cycle_detected"):
            graph_facts.append("Circular fund movement pattern detected")
        if graph_facts:
            sections.append(f"Graph Structure: {'; '.join(graph_facts)}.")

        # 4. Primary Hypotheses
        if state.hypotheses:
            top_hyp = state.hypotheses[0]
            typology_name = top_hyp.typology_name or top_hyp.title or "GENERAL"
            hypothesis_confidence = (
                top_hyp.confidence
                if top_hyp.confidence is not None
                else top_hyp.likelihood
            )
            sections.append(
                f"Primary Typology: {typology_name} (Confidence: {hypothesis_confidence:.2f}, Indicators: {', '.join(top_hyp.indicators[:3])})."
            )

        # 5. Evidence Highlights
        ev_count = len(state.all_evidence)
        sections.append(
            f"Evidence: {ev_count} items evaluated ({len(state.supporting_evidence_ids)} supporting, {len(state.contradictory_evidence_ids)} contradictory)."
        )

        # 6. Recommendation Evolution (Strictly Append-Oriented)
        if state.pre_evidence_next_best_action:
            pre_act = state.pre_evidence_next_best_action.action_type
            sections.append(f"Pre-evidence Recommendation: {pre_act.value if hasattr(pre_act, 'value') else pre_act}.")
        if state.post_evidence_next_best_action:
            post_act = state.post_evidence_next_best_action.action_type
            sections.append(f"Post-evidence Recommendation: {post_act.value if hasattr(post_act, 'value') else post_act}.")

        # 7. Approvals & Executions
        if state.approval_decisions:
            latest_app = state.approval_decisions[-1]
            sections.append(f"Analyst Review: {latest_app.reviewer_role} {latest_app.status}.")
        if state.executed_actions:
            exec_acts = [e.action_type.value if hasattr(e.action_type, "value") else str(e.action_type) for e in state.executed_actions]
            sections.append(f"Actions Executed: {', '.join(exec_acts)}.")

        # 8. Outcome & Assessment
        risk_str = state.risk_level.value if hasattr(state.risk_level, "value") else str(state.risk_level or "UNKNOWN")
        conf_val = f"{state.confidence:.2f}" if state.confidence is not None else "N/A"
        stop_str = state.stop_reason.value if hasattr(state.stop_reason, "value") else str(state.stop_reason or "FINALIZED")
        sections.append(f"Outcome: {stop_str} (Risk: {risk_str}, Confidence: {conf_val}).")

        return " ".join(sections)

    def determine_case_outcome(self, state: FraudCaseState) -> str:
        """Derive standard outcome label (FRAUD_CONFIRMED, FALSE_POSITIVE_CLEARED, or stop reason)."""
        # Check executed actions
        executed_types = {e.action_type for e in state.executed_actions}
        if any(
            t in [ActionType.BLOCK_TRANSACTION, ActionType.BLOCK_ACCOUNT, ActionType.FILE_SAR]
            for t in executed_types
        ):
            return "FRAUD_CONFIRMED"

        if state.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return "FRAUD_CONFIRMED"

        if state.stop_reason == StopReason.NO_MATERIAL_FRAUD_EVIDENCE:
            return "FALSE_POSITIVE_CLEARED"

        if any(t in [ActionType.ALLOW_TRANSACTION, ActionType.NO_ACTION] for t in executed_types):
            return "FALSE_POSITIVE_CLEARED"

        if state.stop_reason is not None:
            return state.stop_reason.value if hasattr(state.stop_reason, "value") else str(state.stop_reason)

        return "RESOLVED"

    def extract_graph_references(self, state: FraudCaseState) -> List[str]:
        """Extract entity identifiers linked to this case for graph precedent overlap."""
        refs: List[str] = []
        if state.transaction_id:
            refs.append(f"TX:{state.transaction_id}")
        if state.customer_id:
            refs.append(f"CUST:{state.customer_id}")
        for acc in state.account_ids:
            refs.append(f"ACC:{acc}")

        for dev in state.device_evidence:
            if dev.source_reference and dev.source_reference not in refs:
                refs.append(f"DEV:{dev.source_reference}")

        for hyp in state.hypotheses:
            if hyp.typology_id and f"TYP:{hyp.typology_id}" not in refs:
                refs.append(f"TYP:{hyp.typology_id}")

        return refs

    def index_case(
        self,
        state: FraudCaseState,
        persist: bool = True,
        custom_index_path: Optional[Path] = None,
    ) -> CaseIndexingReceipt:
        """Vectorize case summary and index as reusable precedent memory.

        Enforces benchmark isolation: Refuses to index CASE_001 to CASE_020.
        """
        # 1. Benchmark Isolation Gate
        if is_benchmark_case(state.case_id):
            logger.warning(
                "Benchmark Isolation: Case %s is a benchmark case. Quarantined from precedent index.",
                state.case_id,
            )
            return CaseIndexingReceipt(
                case_id=state.case_id,
                chunk_id=None,
                outcome="QUARANTINED",
                primary_typology="BENCHMARK",
                summary_text="",
                summary_length=0,
                embedding_dim=0,
                is_indexed=False,
                quarantined=True,
                quarantine_reason=f"Strict benchmark isolation: {state.case_id} cannot be indexed as precedent memory.",
                timestamp=now_iso(),
            )

        # 2. Build grounded summary
        summary_text = state.case_summary or self.build_grounded_case_summary(state)

        # 3. Compute local SentenceTransformer embedding vector
        embedding = compute_embedding(summary_text)

        # 4. Determine outcome & typology
        outcome = self.determine_case_outcome(state)
        primary_typology = (
            state.hypotheses[0].typology_name
            or state.hypotheses[0].title
            or "GENERAL"
            if state.hypotheses
            else "GENERAL"
        )
        graph_refs = self.extract_graph_references(state)
        chunk_id = f"CHUNK_{state.case_id}"

        # 5. Create CaseMemoryRecord
        record = CaseMemoryRecord(
            chunk_id=chunk_id,
            case_id=state.case_id,
            outcome=outcome,
            primary_typology=primary_typology,
            text=summary_text,
            graph_references=graph_refs,
            embedding=embedding,
        )

        # 6. Upsert into active in-memory index
        success = self.index.upsert_record(record)
        if not success:
            logger.error("Failed to upsert case %s into case memory index", state.case_id)
            return CaseIndexingReceipt(
                case_id=state.case_id,
                chunk_id=chunk_id,
                outcome=outcome,
                primary_typology=primary_typology,
                summary_text=summary_text,
                summary_length=len(summary_text),
                embedding_dim=len(embedding),
                is_indexed=False,
                quarantined=True,
                quarantine_reason="Index upsert rejected by quarantine policy",
                timestamp=now_iso(),
            )

        # 7. Persist to Parquet if requested
        saved_path: Optional[str] = None
        if persist:
            target_path = custom_index_path or (self.data_dir / "case_memory_index.parquet")
            try:
                self.index.save_to_parquet(target_path)
                saved_path = str(target_path)
                logger.info("Persisted updated case memory index to %s", target_path)
            except Exception as exc:
                logger.warning("Could not persist case memory index to %s: %s", target_path, exc)

        logger.info(
            "Successfully indexed case %s into case memory (dim=%d, outcome=%s, typology=%s)",
            state.case_id,
            len(embedding),
            outcome,
            primary_typology,
        )

        return CaseIndexingReceipt(
            case_id=state.case_id,
            chunk_id=chunk_id,
            outcome=outcome,
            primary_typology=primary_typology,
            summary_text=summary_text,
            summary_length=len(summary_text),
            embedding_dim=len(embedding),
            is_indexed=True,
            quarantined=False,
            index_path=saved_path,
            timestamp=now_iso(),
        )
