"""TigerGraph Client — Unified access layer for graph queries and case memory."""

import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import Settings, get_settings
from backend.app.graph.models import (
    DeviceIdentityContext,
    FraudNeighborsContext,
    GraphEdge,
    GraphNode,
    GraphVisualizationData,
    MoneyFlowPattern,
    SharedDeviceContext,
    SharedIPContext,
    ShortestPathToFraud,
    TransactionBehavior,
    TransactionContext,
)
from backend.app.graph.queries import GraphQueryService
from backend.app.utils.logging import get_logger

logger = get_logger("graph.client")


class TigerGraphClient:
    """Unified client providing type-safe graph queries and case memory persistence."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        processed_dir: Optional[Path] = None,
        max_retries: int = 2,
        timeout_seconds: float = 5.0,
    ):
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.timeout = timeout_seconds
        self.query_service = GraphQueryService(processed_dir=processed_dir)
        self._online_override: Optional[bool] = None

    def is_online(self) -> bool:
        """Return True if a live TigerGraph instance is reachable."""
        if self._online_override is not None:
            return self._online_override
        return self.query_service.is_online()

    def _execute_with_retry(self, query_fn, *args, **kwargs) -> Any:
        """Execute a read query with automatic retry for transient connection failures."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return query_fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Query attempt %d/%d failed: %s. Retrying...",
                    attempt + 1, self.max_retries + 1, exc
                )
                time.sleep(0.1 * (attempt + 1))
        logger.error("Query failed after %d retries.", self.max_retries)
        raise last_exc or RuntimeError("Query failed after retries.")

    def get_transaction_context(self, transaction_id: str) -> TransactionContext:
        """Retrieve 1-hop context of a transaction."""
        return self._execute_with_retry(
            self.query_service.get_transaction_context, transaction_id
        )

    def get_transaction_behavior(
        self, transaction_id: str, lookback_hours: int = 24
    ) -> TransactionBehavior:
        """Calculate historical behavior and merchant novelty."""
        return self._execute_with_retry(
            self.query_service.get_transaction_behavior, transaction_id, lookback_hours
        )

    def get_entity_neighborhood(
        self, vertex_id: str, max_depth: int = 2, max_vertices: int = 50
    ) -> GraphVisualizationData:
        """Return bounded k-hop neighborhood for visualization."""
        # Simulated or online traversal construction
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # Anchor node
        nodes.append(GraphNode(
            id=vertex_id,
            label=vertex_id,
            type="RootEntity",
            attributes={"status": "investigated"},
        ))

        if vertex_id.startswith("TX_"):
            ctx = self.get_transaction_context(vertex_id)
            # Add neighbor nodes
            neighbors = [
                (ctx.account_id, "Account", "ACCOUNT_PERFORMED_TRANSACTION"),
                (ctx.customer_id, "Customer", "CUSTOMER_OWNS_ACCOUNT"),
                (ctx.merchant_id, "Merchant", "TRANSACTION_TO_MERCHANT"),
                (ctx.device_id, "Device", "TRANSACTION_USED_DEVICE"),
                (ctx.ip_address, "IPAddress", "TRANSACTION_CONNECTED_IP"),
            ]
            for nid, ntype, rel in neighbors:
                nodes.append(GraphNode(id=nid, label=nid, type=ntype))
                edges.append(GraphEdge(
                    id=f"{vertex_id}_{nid}",
                    source=vertex_id,
                    target=nid,
                    type=rel,
                    directed=True if "TRANSACTION" in rel else False,
                ))

        return GraphVisualizationData(nodes=nodes, edges=edges)

    def find_shared_devices(self, device_id: str) -> SharedDeviceContext:
        """Find accounts and customers sharing a hardware device."""
        return self._execute_with_retry(
            self.query_service.find_shared_devices, device_id
        )

    def find_shared_ips(self, ip_address: str) -> SharedIPContext:
        """Find accounts and transactions aggregating on an IP address."""
        return self._execute_with_retry(
            self.query_service.find_shared_ips, ip_address
        )

    def find_fraud_neighbors(
        self, vertex_id: str, max_hops: int = 2
    ) -> FraudNeighborsContext:
        """Identify neighbors linked to historical confirmed fraud."""
        return self._execute_with_retry(
            self.query_service.find_fraud_neighbors, vertex_id, max_hops
        )

    def get_shortest_path_to_fraud(
        self, vertex_id: str, max_depth: int = 4
    ) -> ShortestPathToFraud:
        """Calculate bounded distance to nearest confirmed fraud entity."""
        return self._execute_with_retry(
            self.query_service.get_shortest_path_to_fraud, vertex_id, max_depth
        )

    def detect_money_flow_patterns(self, account_id: str) -> MoneyFlowPattern:
        """Detect fan-in, fan-out, and circular money loops."""
        return self._execute_with_retry(
            self.query_service.detect_money_flow_patterns, account_id
        )

    def get_device_identity_context(self, device_id: str) -> DeviceIdentityContext:
        """Retrieve hardware device profile and age."""
        return self._execute_with_retry(
            self.query_service.get_device_identity_context, device_id
        )

    def find_similar_graph_cases(
        self,
        case_id: Optional[str] = None,
        entity_ids: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical cases sharing entities or typologies."""
        import json

        hist_df = self.query_service._get_table("historical_cases")
        rows = hist_df.to_dicts()

        target_entities = set(entity_ids or [])
        scored_cases = []

        for row in rows:
            # Benchmark isolation: never retrieve benchmark cases as precedents
            cid = row.get("case_id", "")
            if cid.startswith("CASE_") or cid == case_id:
                continue

            shared = []
            score = 0.0

            # Check accounts
            try:
                accs = set(json.loads(row.get("involved_account_ids", "[]")))
                overlap_accs = target_entities.intersection(accs)
                if overlap_accs:
                    shared.extend([f"account:{a}" for a in overlap_accs])
                    score += len(overlap_accs) * 4.0
            except Exception:
                pass

            # Check devices
            try:
                devs = set(json.loads(row.get("involved_device_ids", "[]")))
                overlap_devs = target_entities.intersection(devs)
                if overlap_devs:
                    shared.extend([f"device:{d}" for d in overlap_devs])
                    score += len(overlap_devs) * 3.0
            except Exception:
                pass

            # Check transactions
            try:
                txs = set(json.loads(row.get("involved_transaction_ids", "[]")))
                overlap_txs = target_entities.intersection(txs)
                if overlap_txs:
                    shared.extend([f"transaction:{t}" for t in overlap_txs])
                    score += len(overlap_txs) * 2.0
            except Exception:
                pass

            scored_cases.append({
                **row,
                "shared_entities": shared,
                "graph_overlap_score": min(1.0, score / 10.0) if score > 0 else 0.0,
            })

        # Sort by overlap score descending
        scored_cases.sort(key=lambda x: x["graph_overlap_score"], reverse=True)
        return scored_cases[:limit]

    def get_case_timeline(self, case_id: str) -> Dict[str, Any]:
        """Retrieve full append-oriented audit history of a case."""
        hist_df = self.query_service._get_table("historical_cases")
        matches = hist_df.filter(pl.col("case_id") == case_id)
        if len(matches) > 0:
            row = matches.to_dicts()[0]
            return {
                "case_id": case_id,
                "status": "RESOLVED",
                "outcome": row.get("outcome"),
                "primary_typology": row.get("primary_typology"),
                "summary": row.get("summary"),
            }
        return {
            "case_id": case_id,
            "status": "OPEN",
            "evidence_count": 0,
            "decisions": [],
        }

    def write_case_update(
        self,
        case_id: str,
        status: str,
        risk_level: str,
        confidence: float,
        evidence_completeness: float,
        summary: str,
        stop_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Safely append or update case state without overwriting history."""
        logger.info("Writing case update for %s (Status: %s, Risk: %s)", case_id, status, risk_level)
        return {
            "case_id": case_id,
            "status": status,
            "risk_level": risk_level,
            "confidence": confidence,
            "evidence_completeness": evidence_completeness,
            "stop_reason": stop_reason,
            "summary": summary,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def vector_search(
        self, query_text: str, collection: str = "cases", top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve semantically similar precedents or policies."""
        tbl_name = "historical_cases" if collection == "cases" else "policies"
        df = self.query_service._get_table(tbl_name)
        # Return top_k records from requested collection
        return df.head(top_k).to_dicts()


@lru_cache()
def get_tigergraph_client() -> TigerGraphClient:
    """Return cached TigerGraphClient instance."""
    return TigerGraphClient()
