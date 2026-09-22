"""TigerGraph GraphRAG Retrieval Service.

Provides compact, grounded context to the reasoning agent by combining:
1. Policy, typology, and regulatory vector retrieval with source attribution.
2. Similar historical case precedent retrieval combining TigerGraph structural graph overlap
   and vector semantic similarity.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.graph.tigergraph_client import TigerGraphClient
from backend.app.rag.case_memory import CaseMemoryIndex
from backend.app.rag.policy_index import PolicyVectorIndex
from backend.app.utils.logging import get_logger

logger = get_logger("rag.retrieval")


class PolicyContextItem(BaseModel):
    chunk_id: str
    source_id: str
    document_type: str
    section_title: str
    text: str
    relevance_score: float
    graph_references: List[str] = Field(default_factory=list)


class PolicyContextResult(BaseModel):
    items: List[PolicyContextItem] = Field(default_factory=list)
    policies: List[PolicyContextItem] = Field(default_factory=list)
    typologies: List[PolicyContextItem] = Field(default_factory=list)
    regulations: List[PolicyContextItem] = Field(default_factory=list)
    compact_context_text: str = ""


class SimilarCaseItem(BaseModel):
    case_id: str
    outcome: str
    primary_typology: str
    summary: str
    shared_entities: List[str] = Field(default_factory=list)
    graph_overlap_score: float = 0.0
    vector_similarity_score: float = 0.0
    combined_score: float = 0.0
    retrieval_method: str = "VECTOR"  # "HYBRID", "GRAPH", or "VECTOR"


class SimilarCasesResult(BaseModel):
    cases: List[SimilarCaseItem] = Field(default_factory=list)
    fraud_confirmed_count: int = 0
    cleared_count: int = 0
    compact_precedent_text: str = ""


class GraphRAGRetrievalService:
    """Hybrid GraphRAG retrieval engine combining TigerGraph graph queries and vector indices."""

    def __init__(
        self,
        policy_index: Optional[PolicyVectorIndex] = None,
        case_memory_index: Optional[CaseMemoryIndex] = None,
        tigergraph_client: Optional[TigerGraphClient] = None,
        data_dir: Optional[Path] = None,
    ):
        settings = get_settings()
        self.data_dir = data_dir or settings.PROCESSED_DATA_DIR
        self.tg_client = tigergraph_client or TigerGraphClient()

        # Initialize or load policy index
        if policy_index is not None:
            self.policy_index = policy_index
        else:
            self.policy_index = PolicyVectorIndex()
            policy_path = self.data_dir / "policy_index.parquet"
            if policy_path.exists():
                try:
                    self.policy_index.load_from_parquet(policy_path)
                except Exception as exc:
                    logger.warning("Could not load policy index from %s: %s", policy_path, exc)

        # Initialize or load case memory index
        if case_memory_index is not None:
            self.case_memory_index = case_memory_index
        else:
            self.case_memory_index = CaseMemoryIndex()
            case_path = self.data_dir / "case_memory_index.parquet"
            if case_path.exists():
                try:
                    self.case_memory_index.load_from_parquet(case_path)
                except Exception as exc:
                    logger.warning("Could not load case memory index from %s: %s", case_path, exc)

    def retrieve_policy_context(
        self,
        query_or_context: Union[str, Dict[str, Any]],
        candidate_action: Optional[str] = None,
        fraud_hypothesis: Optional[str] = None,
        top_k: int = 4,
        threshold: float = 0.25,
    ) -> PolicyContextResult:
        """Retrieve relevant policies, typologies, and regulations.

        Grounded context retrieval without massive document dumping.
        """
        if isinstance(query_or_context, dict):
            base_query = str(query_or_context.get("query_text") or query_or_context.get("summary") or "")
            action = candidate_action or query_or_context.get("candidate_action")
            hypothesis = fraud_hypothesis or query_or_context.get("fraud_hypothesis")
        else:
            base_query = str(query_or_context)
            action = candidate_action
            hypothesis = fraud_hypothesis

        # Construct unified query string
        query_parts = [base_query]
        if action:
            query_parts.append(f"Action: {action}")
        if hypothesis:
            query_parts.append(f"Typology/Hypothesis: {hypothesis}")
        composite_query = " | ".join(part for part in query_parts if part.strip())

        raw_results = self.policy_index.search(
            query_text=composite_query,
            top_k=top_k * 2,  # Fetch wider set to allow category diversification
        )

        seen_chunks: Set[str] = set()
        items: List[PolicyContextItem] = []
        policies: List[PolicyContextItem] = []
        typologies: List[PolicyContextItem] = []
        regulations: List[PolicyContextItem] = []

        for r in raw_results:
            chunk_id = r["chunk_id"]
            score = float(r["score"])
            if chunk_id in seen_chunks or score < threshold:
                continue
            seen_chunks.add(chunk_id)

            item = PolicyContextItem(
                chunk_id=chunk_id,
                source_id=r["source_id"],
                document_type=r["document_type"],
                section_title=r["section_title"],
                text=r["text"],
                relevance_score=score,
                graph_references=r.get("graph_references", []),
            )
            items.append(item)

            if item.document_type == "POLICY":
                policies.append(item)
            elif item.document_type == "TYPOLOGY":
                typologies.append(item)
            elif item.document_type == "REGULATION":
                regulations.append(item)

            if len(items) >= top_k:
                break

        # Generate compact, token-efficient markdown context for reasoning model
        compact_text = self._format_policy_compact_text(policies, typologies, regulations)

        return PolicyContextResult(
            items=items,
            policies=policies,
            typologies=typologies,
            regulations=regulations,
            compact_context_text=compact_text,
        )

    def retrieve_similar_cases(
        self,
        case_context: Optional[Union[str, Dict[str, Any]]] = None,
        case_id: Optional[str] = None,
        entity_ids: Optional[List[str]] = None,
        query_text: Optional[str] = None,
        top_k: int = 4,
        balance_outcomes: bool = True,
    ) -> SimilarCasesResult:
        """Retrieve similar historical cases using hybrid graph overlap + vector similarity.

        Precedent retrieval is strictly isolated from benchmark cases (CASE_001 - CASE_020).
        """
        # Parse inputs
        target_case_id = case_id
        target_entities: List[str] = list(entity_ids or [])
        target_query = query_text or ""

        if isinstance(case_context, dict):
            target_case_id = target_case_id or case_context.get("case_id")
            if "entity_ids" in case_context and isinstance(case_context["entity_ids"], list):
                target_entities.extend(case_context["entity_ids"])
            if "account_id" in case_context and case_context["account_id"]:
                target_entities.append(str(case_context["account_id"]))
            if "device_id" in case_context and case_context["device_id"]:
                target_entities.append(str(case_context["device_id"]))
            if not target_query:
                target_query = str(case_context.get("summary") or case_context.get("query_text") or "")
        elif isinstance(case_context, str) and not target_query:
            target_query = case_context

        # Deduplicate entity IDs
        target_entities = list(dict.fromkeys(target_entities))

        # 1. TigerGraph Graph Overlap Search
        graph_matches: Dict[str, Dict[str, Any]] = {}
        if target_entities or target_case_id:
            try:
                tg_cases = self.tg_client.find_similar_graph_cases(
                    case_id=target_case_id,
                    entity_ids=target_entities,
                    limit=15,
                )
                for c in tg_cases:
                    cid = c.get("case_id")
                    if cid and not cid.startswith("CASE_"):
                        graph_matches[cid] = c
            except Exception as exc:
                logger.warning("Graph case retrieval fallback: %s", exc)

        # 2. Vector Semantic Similarity Search
        vector_matches: Dict[str, Dict[str, Any]] = {}
        if target_query:
            try:
                v_results = self.case_memory_index.search_similar_cases(
                    query_text=target_query,
                    top_k=20,
                )
                for r in v_results:
                    cid = r.get("case_id")
                    if cid and not cid.startswith("CASE_"):
                        vector_matches[cid] = r
            except Exception as exc:
                logger.warning("Vector case memory search fallback: %s", exc)

        # 3. Hybrid Fusion
        all_case_ids = set(graph_matches.keys()).union(vector_matches.keys())
        scored_candidates: List[SimilarCaseItem] = []

        for cid in all_case_ids:
            # Benchmark isolation: strictly exclude CASE_###
            if cid.startswith("CASE_"):
                continue

            g_data = graph_matches.get(cid)
            v_data = vector_matches.get(cid)

            graph_score = float(g_data.get("graph_overlap_score", 0.0)) if g_data else 0.0
            vector_score = float(v_data.get("score", 0.0)) if v_data else 0.0

            shared_entities = g_data.get("shared_entities", []) if g_data else []
            outcome = (g_data or v_data or {}).get("outcome", "UNKNOWN")
            typology = (g_data or v_data or {}).get("primary_typology", "GENERAL")
            summary = (g_data or v_data or {}).get("summary", "")

            if graph_score > 0 and vector_score > 0:
                combined_score = round(0.5 * graph_score + 0.5 * vector_score, 4)
                method = "HYBRID"
            elif graph_score > 0:
                combined_score = round(graph_score, 4)
                method = "GRAPH"
            else:
                combined_score = round(vector_score, 4)
                method = "VECTOR"

            scored_candidates.append(SimilarCaseItem(
                case_id=cid,
                outcome=outcome,
                primary_typology=typology,
                summary=summary,
                shared_entities=shared_entities,
                graph_overlap_score=graph_score,
                vector_similarity_score=vector_score,
                combined_score=combined_score,
                retrieval_method=method,
            ))

        # Sort by combined score descending
        scored_candidates.sort(key=lambda x: x.combined_score, reverse=True)

        # 4. Balanced Selection (Fraud Confirmed vs Cleared Precedents)
        selected_cases = self._balance_case_outcomes(
            scored_candidates, top_k=top_k, balance=balance_outcomes
        )

        fraud_count = sum(1 for c in selected_cases if c.outcome == "FRAUD_CONFIRMED")
        cleared_count = sum(1 for c in selected_cases if c.outcome == "FALSE_POSITIVE_CLEARED")

        compact_text = self._format_cases_compact_text(selected_cases)

        return SimilarCasesResult(
            cases=selected_cases,
            fraud_confirmed_count=fraud_count,
            cleared_count=cleared_count,
            compact_precedent_text=compact_text,
        )

    def _balance_case_outcomes(
        self,
        candidates: List[SimilarCaseItem],
        top_k: int,
        balance: bool,
    ) -> List[SimilarCaseItem]:
        """Ensure top precedents include both fraud-confirmed and cleared outcomes when relevant."""
        if not candidates or len(candidates) <= top_k or not balance:
            return candidates[:top_k]

        selected: List[SimilarCaseItem] = []
        fraud_candidates = [c for c in candidates if c.outcome == "FRAUD_CONFIRMED"]
        cleared_candidates = [c for c in candidates if c.outcome == "FALSE_POSITIVE_CLEARED"]

        # Ensure at least 1 cleared case if available in candidate pool, while maintaining top rank
        has_fraud = len(fraud_candidates) > 0
        has_cleared = len(cleared_candidates) > 0

        if has_fraud and has_cleared and top_k >= 2:
            first_candidate = candidates[0]
            selected.append(first_candidate)

            target_alternate = (
                "FALSE_POSITIVE_CLEARED" if first_candidate.outcome == "FRAUD_CONFIRMED" else "FRAUD_CONFIRMED"
            )
            alternates = [c for c in candidates if c.outcome == target_alternate]
            if alternates:
                selected.append(alternates[0])

            for c in candidates:
                if c.case_id not in {s.case_id for s in selected}:
                    selected.append(c)
                if len(selected) >= top_k:
                    break
            return selected

        return candidates[:top_k]

    def _format_policy_compact_text(
        self,
        policies: List[PolicyContextItem],
        typologies: List[PolicyContextItem],
        regulations: List[PolicyContextItem],
    ) -> str:
        """Render bounded, non-document-dumping markdown for reasoning agent context."""
        lines = ["### TigerGraph GraphRAG: Policy, Typology & Governance Context"]

        if policies:
            lines.append("\n**Applicable Bank Policies:**")
            for p in policies:
                snippet = p.text.strip().replace("\n", " ")[:240]
                lines.append(f"- `[{p.source_id}]` **{p.section_title}** (Relevance: {p.relevance_score:.2f}): {snippet}...")

        if typologies:
            lines.append("\n**Matched Fraud Typologies:**")
            for t in typologies:
                snippet = t.text.strip().replace("\n", " ")[:240]
                lines.append(f"- `[{t.source_id}]` **{t.section_title}** (Relevance: {t.relevance_score:.2f}): {snippet}...")

        if regulations:
            lines.append("\n**Regulatory Guidance:**")
            for r in regulations:
                snippet = r.text.strip().replace("\n", " ")[:240]
                lines.append(f"- `[{r.source_id}]` **{r.section_title}** (Relevance: {r.relevance_score:.2f}): {snippet}...")

        if len(lines) == 1:
            lines.append("\n*No high-confidence policy or regulatory constraints identified for current trigger.*")

        return "\n".join(lines)

    def _format_cases_compact_text(self, cases: List[SimilarCaseItem]) -> str:
        """Render compact historical precedents reminding LLM that precedent is not proof."""
        lines = [
            "### Historical Case Precedents (Reference Precedents — Not Conclusive Proof)",
        ]
        if not cases:
            lines.append("*No relevant historical case precedents found in memory.*")
            return "\n".join(lines)

        for c in cases:
            shared_info = f" | Shared: {', '.join(c.shared_entities)}" if c.shared_entities else ""
            summary_snippet = c.summary.strip().replace("\n", " ")[:220]
            lines.append(
                f"- `[{c.case_id}]` Outcome: **{c.outcome}** | Typology: `{c.primary_typology}` | "
                f"Match: {c.retrieval_method} (Score: {c.combined_score:.2f}){shared_info}\n"
                f"  *Summary*: {summary_snippet}..."
            )
        return "\n".join(lines)
