"""Unit tests for GSQL queries and GraphQueryService."""

from pathlib import Path
import pytest

from backend.app.graph.queries import (
    GraphQueryService,
    TransactionContext,
    TransactionBehavior,
    SharedDeviceContext,
    SharedIPContext,
    FraudNeighborsContext,
    ShortestPathToFraud,
    MoneyFlowPattern,
    DeviceIdentityContext,
)

GSQL_QUERIES_DIR = Path("gsql/queries")

EXPECTED_QUERIES = [
    "get_transaction_context.gsql",
    "get_transaction_behavior.gsql",
    "get_entity_neighborhood.gsql",
    "find_shared_devices.gsql",
    "find_shared_ips.gsql",
    "find_fraud_neighbors.gsql",
    "get_shortest_path_to_fraud.gsql",
    "detect_money_flow_patterns.gsql",
    "get_connected_cluster.gsql",
    "get_device_identity_context.gsql",
    "find_similar_graph_cases.gsql",
    "get_case_timeline.gsql",
    "write_case_update.gsql",
]


def test_all_gsql_query_files_exist():
    """Verify that all 13 required GSQL queries exist and have valid CREATE QUERY syntax."""
    for qname in EXPECTED_QUERIES:
        qpath = GSQL_QUERIES_DIR / qname
        assert qpath.exists(), f"Missing GSQL query file: {qname}"
        content = qpath.read_text(encoding="utf-8")
        assert "CREATE QUERY" in content, f"Query {qname} missing CREATE QUERY declaration"
        assert "FOR GRAPH FraudInvestigationGraph" in content, f"Query {qname} missing graph binding"


@pytest.fixture
def query_service():
    """Fixture providing initialized GraphQueryService."""
    return GraphQueryService(processed_dir=Path("data/processed"))


def test_get_transaction_context(query_service):
    """Verify transaction context returns valid customer, account, merchant, device, and IP."""
    ctx = query_service.get_transaction_context("TX_0001")
    assert isinstance(ctx, TransactionContext)
    assert ctx.transaction_id == "TX_0001"
    assert ctx.account_id.startswith("ACC_")
    assert ctx.customer_id.startswith("CUST_")
    assert ctx.device_id.startswith("DEV_")
    assert ctx.ip_address.startswith("198.51.100.")
    assert ctx.amount > 0


def test_get_transaction_behavior(query_service):
    """Verify transaction behavior computes historical average and merchant novelty."""
    beh = query_service.get_transaction_behavior("TX_0001")
    assert isinstance(beh, TransactionBehavior)
    assert beh.target_amount > 0
    assert beh.historical_avg_amount > 0
    assert beh.amount_ratio_to_mean > 0
    assert isinstance(beh.is_new_merchant, bool)


def test_find_shared_devices(query_service):
    """Verify shared devices discovers co-occurring accounts and customers."""
    shared = query_service.find_shared_devices("DEV_001")
    assert isinstance(shared, SharedDeviceContext)
    assert shared.device_id == "DEV_001"
    assert shared.shared_account_count >= 1
    assert shared.shared_customer_count >= 1


def test_find_shared_ips(query_service):
    """Verify shared IP discovers linked accounts and geographic ASN info."""
    ip_ctx = query_service.find_shared_ips("198.51.100.1")
    assert isinstance(ip_ctx, SharedIPContext)
    assert ip_ctx.ip_address == "198.51.100.1"
    assert ip_ctx.country_code != ""
    assert ip_ctx.transaction_count >= 1


def test_find_fraud_neighbors(query_service):
    """Verify fraud neighbors query executes and returns structured result."""
    fn = query_service.find_fraud_neighbors("DEV_001")
    assert isinstance(fn, FraudNeighborsContext)
    assert fn.fraud_neighbors_count >= 0


def test_get_shortest_path_to_fraud(query_service):
    """Verify shortest path to fraud returns valid integer distance."""
    sp = query_service.get_shortest_path_to_fraud("DEV_001")
    assert isinstance(sp, ShortestPathToFraud)
    assert sp.shortest_distance_to_fraud in [-1, 1, 2, 3, 4]


def test_detect_money_flow_patterns(query_service):
    """Verify money flow patterns calculates fan-in, fan-out, and loop detection."""
    mf = query_service.detect_money_flow_patterns("ACC_001")
    assert isinstance(mf, MoneyFlowPattern)
    assert mf.account_id == "ACC_001"
    assert mf.fan_out_count >= 1
    assert mf.outbound_sum >= 0.0


def test_get_device_identity_context(query_service):
    """Verify device identity context returns device type and age."""
    dev_ctx = query_service.get_device_identity_context("DEV_001")
    assert isinstance(dev_ctx, DeviceIdentityContext)
    assert dev_ctx.device_id == "DEV_001"
    assert dev_ctx.device_type in ["MOBILE", "DESKTOP", "TABLET"]
    assert dev_ctx.linked_accounts_count >= 1
