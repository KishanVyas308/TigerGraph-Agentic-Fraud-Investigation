"""Unit tests for TigerGraphClient and TigerGraphMCPAdapter."""

from pathlib import Path
import pytest

from backend.app.graph.models import (
    GraphVisualizationData,
    ToolPermission,
    TransactionBehavior,
    TransactionContext,
)
from backend.app.graph.mcp_client import TigerGraphMCPAdapter
from backend.app.graph.tigergraph_client import TigerGraphClient


@pytest.fixture
def tg_client():
    """Fixture providing TigerGraphClient configured with processed parquet tables."""
    return TigerGraphClient(processed_dir=Path("data/processed"))


@pytest.fixture
def mcp_adapter(tg_client):
    """Fixture providing TigerGraphMCPAdapter."""
    return TigerGraphMCPAdapter(client=tg_client)


def test_client_transaction_context(tg_client):
    """Verify TigerGraphClient retrieves transaction context."""
    ctx = tg_client.get_transaction_context("TX_0001")
    assert isinstance(ctx, TransactionContext)
    assert ctx.transaction_id == "TX_0001"
    assert ctx.customer_id.startswith("CUST_")


def test_client_entity_neighborhood(tg_client):
    """Verify entity neighborhood returns nodes and edges for Cytoscape."""
    graph_data = tg_client.get_entity_neighborhood("TX_0001", max_depth=2, max_vertices=10)
    assert isinstance(graph_data, GraphVisualizationData)
    assert len(graph_data.nodes) >= 2
    assert len(graph_data.edges) >= 1
    root = next(n for n in graph_data.nodes if n.id == "TX_0001")
    assert root is not None


def test_client_write_case_update(tg_client):
    """Verify safe append case update returns formatted confirmation."""
    res = tg_client.write_case_update(
        case_id="CASE_001",
        status="IN_PROGRESS",
        risk_level="HIGH",
        confidence=0.88,
        evidence_completeness=0.75,
        summary="Investigating shared device cluster with 8 accounts",
        stop_reason=None,
    )
    assert res["case_id"] == "CASE_001"
    assert res["status"] == "IN_PROGRESS"
    assert res["risk_level"] == "HIGH"
    assert "updated_at" in res


def test_client_vector_search(tg_client):
    """Verify vector search retrieves top historical cases and policies."""
    cases = tg_client.vector_search("Account takeover with new device", collection="cases", top_k=2)
    assert len(cases) == 2

    policies = tg_client.vector_search("Immediate block on critical risk", collection="policies", top_k=2)
    assert len(policies) == 2


def test_client_retry_logic(tg_client):
    """Verify _execute_with_retry successfully retries after transient exception."""
    attempts = 0

    def flaky_query():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("Temporary connection timeout")
        return "success"

    result = tg_client._execute_with_retry(flaky_query)
    assert result == "success"
    assert attempts == 2


def test_mcp_list_tools(mcp_adapter):
    """Verify MCP adapter registers all approved tools."""
    tools = mcp_adapter.list_tools()
    tool_names = [t.name for t in tools]

    expected = [
        "get_transaction_context",
        "get_transaction_behavior",
        "get_entity_neighborhood",
        "find_shared_devices",
        "find_shared_ips",
        "find_fraud_neighbors",
        "get_shortest_path_to_fraud",
        "detect_money_flow_patterns",
        "get_device_identity_context",
        "find_similar_graph_cases",
        "get_case_timeline",
        "write_case_update",
        "vector_search",
    ]
    for exp in expected:
        assert exp in tool_names

    write_tool = mcp_adapter.get_tool_definition("write_case_update")
    assert write_tool.permission == ToolPermission.APPEND_ONLY

    read_tool = mcp_adapter.get_tool_definition("get_transaction_context")
    assert read_tool.permission == ToolPermission.READ_ONLY


def test_mcp_call_tool_success(mcp_adapter):
    """Verify executing an allowed tool returns structured result."""
    res = mcp_adapter.call_tool("get_transaction_context", {"transaction_id": "TX_0001"})
    assert res["status"] == "success"
    assert res["tool"] == "get_transaction_context"
    assert res["data"]["transaction_id"] == "TX_0001"


def test_mcp_call_forbidden_tool(mcp_adapter):
    """Verify calling an unregistered/forbidden tool returns an error."""
    res = mcp_adapter.call_tool("drop_graph", {"graph_name": "FraudInvestigationGraph"})
    assert "error" in res
    assert "not allowed" in res["error"]
