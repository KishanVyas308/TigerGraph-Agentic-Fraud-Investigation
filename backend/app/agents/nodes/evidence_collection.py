"""Parallel Evidence Collection Node (Layer 11).

Concurrently gathers independent baseline evidence branches using asyncio.gather():
1. Branch A: GSQL Transaction Analysis
2. Branch B: GSQL Graph Relationship Analysis
3. Branch C: GraphRAG Policy & Governance Retrieval
4. Branch D: GraphRAG Historical Case Precedent Retrieval
5. Branch E: Device & Identity Context Analysis
6. Branch F: Optional Internal / External Signals

All branch results are normalized into canonical `EvidenceItem` objects with fault isolation.
"""

import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.graph.tigergraph_client import TigerGraphClient
from backend.app.models.state import (
    CaseStatus,
    EvidenceCategory,
    EvidenceItem,
    FraudCaseState,
    TimelineEvent,
)
from backend.app.rag.retrieval import GraphRAGRetrievalService
from backend.app.utils.logging import get_logger

logger = get_logger("agents.nodes.evidence_collection")


class ParallelEvidenceCollectionNode:
    """LangGraph node executing 6 parallel baseline evidence branches with error isolation."""

    def __init__(
        self,
        tigergraph_client: Optional[TigerGraphClient] = None,
        rag_service: Optional[GraphRAGRetrievalService] = None,
        normalizer: Optional[EvidenceNormalizer] = None,
    ):
        self.tg_client = tigergraph_client or TigerGraphClient()
        self.rag_service = rag_service or GraphRAGRetrievalService(tigergraph_client=self.tg_client)
        self.normalizer = normalizer or EvidenceNormalizer()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """LangGraph node execution entry point."""
        return await self.execute(state)

    async def execute(self, state: FraudCaseState) -> Dict[str, Any]:
        """Execute all baseline evidence collection branches concurrently."""
        txn_id = state.transaction_id
        account_ids = state.account_ids or []
        customer_id = state.customer_id
        case_id = state.case_id

        logger.info("Starting parallel evidence collection for Case %s (Txn: %s)", case_id, txn_id)

        # Launch all 6 branches concurrently using asyncio.gather with return_exceptions=True
        results = await asyncio.gather(
            self._run_branch_a_transaction_analysis(txn_id),
            self._run_branch_b_graph_relationships(account_ids, txn_id),
            self._run_branch_c_policy_graphrag(state, txn_id),
            self._run_branch_d_case_memory(state),
            self._run_branch_e_device_identity(account_ids, txn_id),
            self._run_branch_f_external_signals(txn_id, customer_id),
            return_exceptions=True,
        )

        branch_names = [
            "transaction_analysis",
            "graph_relationships",
            "policy_graphrag",
            "case_memory",
            "device_identity",
            "external_signals",
        ]

        collected_items: List[EvidenceItem] = []
        branch_counts: Dict[str, int] = {}

        for name, res in zip(branch_names, results):
            if isinstance(res, Exception):
                logger.warning("Branch '%s' failed with error (isolated): %s", name, res)
                branch_counts[name] = 0
            elif isinstance(res, list):
                collected_items.extend(res)
                branch_counts[name] = len(res)
            else:
                branch_counts[name] = 0

        # Deduplicate all collected evidence items deterministically
        deduped_items = self.normalizer.deduplicate(collected_items)

        # Categorize evidence into specific lists for state merge
        txn_ev = [i for i in deduped_items if i.category == EvidenceCategory.TRANSACTION_BEHAVIOR.value]
        grp_ev = [i for i in deduped_items if i.category in (EvidenceCategory.GRAPH_RELATIONSHIP.value, EvidenceCategory.MONEY_FLOW.value)]
        dev_ev = [i for i in deduped_items if i.category == EvidenceCategory.DEVICE.value]
        idn_ev = [i for i in deduped_items if i.category == EvidenceCategory.IDENTITY.value]
        pol_ev = [i for i in deduped_items if i.category in (EvidenceCategory.POLICY.value, EvidenceCategory.REGULATION.value)]
        hst_ev = [i for i in deduped_items if i.category == EvidenceCategory.HISTORICAL_CASE.value]
        ext_ev = [i for i in deduped_items if i.category in (
            EvidenceCategory.CUSTOMER_RESPONSE.value,
            EvidenceCategory.AUTHENTICATION.value,
            EvidenceCategory.ANALYST_INPUT.value,
            EvidenceCategory.EXTERNAL_SIGNAL.value,
        )]

        timeline_event = TimelineEvent(
            event_type="EVIDENCE_COLLECTION_COMPLETED",
            node_name="parallel_evidence_collection",
            description=f"Collected {len(deduped_items)} baseline evidence items across 6 parallel branches.",
            details={
                "branch_counts": branch_counts,
                "total_evidence_count": len(deduped_items),
            },
        )

        logger.info("Parallel evidence collection finished. Total items: %d", len(deduped_items))

        return {
            "transaction_evidence": txn_ev,
            "graph_evidence": grp_ev,
            "device_evidence": dev_ev,
            "identity_evidence": idn_ev,
            "policy_evidence": pol_ev,
            "historical_case_evidence": hst_ev,
            "external_evidence": ext_ev,
            "bank_risk_score": self._extract_bank_risk_score(txn_ev),
            "timeline": [timeline_event],
            "case_status": CaseStatus.IN_PROGRESS,
        }

    # =========================================================================
    # Branch Implementation Helpers
    # =========================================================================

    async def _run_branch_a_transaction_analysis(self, txn_id: Optional[str]) -> List[EvidenceItem]:
        """Branch A: GSQL Transaction Context and Behavior Analysis."""
        if not txn_id:
            return []

        items: List[EvidenceItem] = []

        # Run context and behavior queries in parallel
        try:
            ctx, bhv = await asyncio.gather(
                self._async_call(self.tg_client.get_transaction_context, txn_id),
                self._async_call(self.tg_client.get_transaction_behavior, txn_id),
                return_exceptions=True,
            )

            if not isinstance(ctx, Exception) and ctx:
                items.extend(self.normalizer.normalize_transaction_context(ctx))
            if not isinstance(bhv, Exception) and bhv:
                items.extend(self.normalizer.normalize_transaction_behavior(bhv))
        except Exception as exc:
            logger.warning("Branch A error: %s", exc)

        return items

    async def _run_branch_b_graph_relationships(
        self, account_ids: List[str], txn_id: Optional[str]
    ) -> List[EvidenceItem]:
        """Branch B: GSQL Graph Relationship & Topology Analysis."""
        items: List[EvidenceItem] = []
        target_account = account_ids[0] if account_ids else (txn_id or "ACC_001")
        device_id: Optional[str] = None
        ip_address: Optional[str] = None

        if txn_id:
            try:
                context = await self._async_call(self.tg_client.get_transaction_context, txn_id)
                context_data = context if isinstance(context, dict) else context.model_dump()
                target_account = context_data.get("account_id") or target_account
                device_id = context_data.get("device_id")
                ip_address = context_data.get("ip_address")
            except Exception as exc:
                logger.warning("Could not resolve graph anchors for %s: %s", txn_id, exc)

        try:
            shared_dev, shared_ip, nbrs, shortest, flow = await asyncio.gather(
                self._async_call(self.tg_client.find_shared_devices, device_id) if device_id else asyncio.sleep(0, result=None),
                self._async_call(self.tg_client.find_shared_ips, ip_address) if ip_address else asyncio.sleep(0, result=None),
                self._async_call(self.tg_client.find_fraud_neighbors, target_account),
                self._async_call(self.tg_client.get_shortest_path_to_fraud, target_account),
                self._async_call(self.tg_client.detect_money_flow_patterns, target_account),
                return_exceptions=True,
            )

            if not isinstance(shared_dev, Exception) and shared_dev:
                items.extend(self.normalizer.normalize_shared_device(shared_dev))
            if not isinstance(shared_ip, Exception) and shared_ip:
                items.extend(self.normalizer.normalize_shared_ip(shared_ip))
            if not isinstance(nbrs, Exception) and nbrs:
                items.extend(self.normalizer.normalize_fraud_neighbors(nbrs))
            if not isinstance(shortest, Exception) and shortest:
                items.extend(self.normalizer.normalize_shortest_path(shortest))
            if not isinstance(flow, Exception) and flow:
                items.extend(self.normalizer.normalize_money_flow(flow))
        except Exception as exc:
            logger.warning("Branch B error: %s", exc)

        return items

    async def _run_branch_c_policy_graphrag(
        self, state: FraudCaseState, txn_id: Optional[str]
    ) -> List[EvidenceItem]:
        """Branch C: GraphRAG Policy, Typology, and Regulatory Context Retrieval."""
        try:
            query_str = f"Transaction alert trigger investigation {txn_id or state.case_id} {state.trigger_type}"
            policy_res = await self._async_call(
                self.rag_service.retrieve_policy_context,
                query_or_context=query_str,
                top_k=4,
            )
            if policy_res:
                return self.normalizer.normalize_graphrag_policy(policy_res)
        except Exception as exc:
            logger.warning("Branch C error: %s", exc)
        return []

    async def _run_branch_d_case_memory(self, state: FraudCaseState) -> List[EvidenceItem]:
        """Branch D: GraphRAG Historical Case Precedent Retrieval."""
        try:
            cases_res = await self._async_call(
                self.rag_service.retrieve_similar_cases,
                case_id=state.case_id,
                entity_ids=state.account_ids,
                query_text=f"Fraud trigger {state.trigger_type} account investigation",
                top_k=4,
            )
            if cases_res:
                return self.normalizer.normalize_graphrag_cases(cases_res)
        except Exception as exc:
            logger.warning("Branch D error: %s", exc)
        return []

    async def _run_branch_e_device_identity(
        self, account_ids: List[str], txn_id: Optional[str]
    ) -> List[EvidenceItem]:
        """Branch E: Device & Identity Context Analysis."""
        target: Optional[str] = None
        if txn_id:
            try:
                context = await self._async_call(self.tg_client.get_transaction_context, txn_id)
                context_data = context if isinstance(context, dict) else context.model_dump()
                target = context_data.get("device_id")
            except Exception as exc:
                logger.warning("Could not resolve device for %s: %s", txn_id, exc)
        if target is None:
            return []
        try:
            dev_idn = await self._async_call(self.tg_client.get_device_identity_context, target)
            if dev_idn:
                return self.normalizer.normalize_device_identity(dev_idn)
        except Exception as exc:
            logger.warning("Branch E error: %s", exc)
        return []

    @staticmethod
    def _extract_bank_risk_score(items: List[EvidenceItem]) -> Optional[float]:
        """Read the bank signal from its verified transaction evidence payload."""
        for item in items:
            raw = item.metadata.get("raw_transaction")
            if isinstance(raw, dict) and raw.get("bank_risk_score") is not None:
                return float(raw["bank_risk_score"])
        return None

    async def _run_branch_f_external_signals(
        self, txn_id: Optional[str], customer_id: Optional[str]
    ) -> List[EvidenceItem]:
        """Branch F: Optional Internal / External Signals (Mock/Reputation/CRM)."""
        # Baseline mock external signal for demo / verification
        items: List[EvidenceItem] = []
        if txn_id or customer_id:
            items.extend(self.normalizer.normalize_external_signal({
                "provider": "MockIPReputationService",
                "entity_id": customer_id or txn_id or "UNKNOWN",
                "signal_type": "IP_RISK_SCORE",
                "score": 15,
                "flag": "CLEAN_RESIDENTIAL_IP",
            }))
        return items

    @staticmethod
    async def _async_call(func: Any, *args: Any, **kwargs: Any) -> Any:
        """Helper executing sync functions in asyncio thread pool if needed."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return await asyncio.to_thread(func, *args, **kwargs)


async def parallel_evidence_collection_node(
    state: FraudCaseState,
    node_instance: Optional[ParallelEvidenceCollectionNode] = None,
) -> Dict[str, Any]:
    """LangGraph node entrypoint function."""
    node = node_instance or ParallelEvidenceCollectionNode()
    return await node.execute(state)
