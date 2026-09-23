"""Unit and Integration Tests for Layer 27: FastAPI Application Layer."""

import pytest
from starlette.testclient import TestClient

from backend.app.main import create_app
from backend.app.models.state import (
    ActionType,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    FraudCaseState,
    RiskLevel,
    StopReason,
    TriggerType,
)
from backend.app.services.investigation_service import get_investigation_service


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_case() -> FraudCaseState:
    """Pre-populate a sample case in InvestigationService for query endpoints."""
    service = get_investigation_service()
    case = FraudCaseState(
        case_id="CASE_API_TEST_01",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TX_API_01",
        customer_id="CUST_API_01",
        account_ids=["ACC_API_01", "ACC_API_02"],
        risk_level=RiskLevel.HIGH,
        risk_score=0.82,
        confidence=0.90,
        evidence_completeness=0.85,
        case_status=CaseStatus.AWAITING_APPROVAL,
        approval_required=True,
        stop_reason=StopReason.AWAITING_HUMAN_REVIEW,
    )
    service.register_case(case)
    return case


def test_health_and_root_endpoints(client: TestClient):
    """Test /health and / endpoints return expected status and metadata."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "healthy"
    assert "TigerGraph" in data_health["app_name"]

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Welcome" in res_root.json()["message"]


def test_trigger_investigation_api(client: TestClient):
    """Test POST /api/investigations starts a new investigation and returns 201."""
    payload = {
        "trigger_type": "TRANSACTION_ALERT",
        "transaction_id": "TX_API_NEW_99",
        "customer_id": "CUST_API_NEW_99",
        "account_ids": ["ACC_API_NEW_99"],
    }
    response = client.post("/api/investigations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["case_id"] is not None
    assert data["case_status"] in ["COMPLETED", "IN_PROGRESS", "AWAITING_APPROVAL"]
    assert data["transaction_id"] == "TX_API_NEW_99"
    assert data["customer_id"] == "CUST_API_NEW_99"
    assert "timeline_event_count" in data


def test_get_investigation_api(client: TestClient, sample_case: FraudCaseState):
    """Test GET /api/investigations/{case_id} retrieves case state and handles 404."""
    # Existing case
    response = client.get(f"/api/investigations/{sample_case.case_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == sample_case.case_id
    assert data["risk_level"] == "HIGH"
    assert data["approval_required"] is True

    # Missing case
    res_404 = client.get("/api/investigations/NON_EXISTENT_CASE_999")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_get_investigation_graph_api(client: TestClient, sample_case: FraudCaseState):
    """Test GET /api/investigations/{case_id}/graph formats Cytoscape elements."""
    response = client.get(f"/api/investigations/{sample_case.case_id}/graph")
    assert response.status_code == 200
    data = response.json()

    assert data["case_id"] == sample_case.case_id
    assert "nodes" in data and len(data["nodes"]) >= 3  # Case, Customer, Account(s)
    assert "edges" in data and len(data["edges"]) >= 2
    assert "summary" in data

    # Verify node structure conforms to Cytoscape.js format
    first_node = data["nodes"][0]
    assert "data" in first_node
    assert "id" in first_node["data"]
    assert "label" in first_node["data"]
    assert "type" in first_node["data"]


def test_get_investigation_evidence_api(client: TestClient, sample_case: FraudCaseState):
    """Test GET /api/investigations/{case_id}/evidence returns evidence cards."""
    response = client.get(f"/api/investigations/{sample_case.case_id}/evidence")
    assert response.status_code == 200
    data = response.json()

    assert data["case_id"] == sample_case.case_id
    assert "evidence" in data
    assert isinstance(data["evidence"], list)


def test_submit_additional_evidence_api(client: TestClient, sample_case: FraudCaseState):
    """Test POST /api/investigations/{case_id}/evidence ingests supplemental evidence."""
    payload = {
        "evidence_type": "MANUAL_ANALYST_NOTE",
        "category": "ANALYST_INPUT",
        "fact": "Customer confirmed device change was verified via phone banking.",
        "reliability": 0.95,
    }
    response = client.post(f"/api/investigations/{sample_case.case_id}/evidence", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == sample_case.case_id


def test_approval_actions_api(client: TestClient, sample_case: FraudCaseState):
    """Test POST /approve, /reject, /modify-action update case state."""
    # 1. Approve
    res_approve = client.post(
        f"/api/investigations/{sample_case.case_id}/approve",
        json={"reviewer_role": "FRAUD_SUPERVISOR", "reviewer_id": "SUPERVISOR_01", "comments": "Approved action."},
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["approval_status"] == "APPROVED"

    # 2. Reject
    res_reject = client.post(
        f"/api/investigations/{sample_case.case_id}/reject",
        json={"reviewer_role": "FRAUD_SUPERVISOR", "reviewer_id": "SUPERVISOR_01", "comments": "Rejected action."},
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["approval_status"] == "REJECTED"

    # 3. Modify Action
    res_modify = client.post(
        f"/api/investigations/{sample_case.case_id}/modify-action",
        json={"action_type": "MONITOR_ACCOUNT", "reviewer_role": "FRAUD_SUPERVISOR", "reviewer_id": "SUPERVISOR_01", "comments": "Modified to monitor."},
    )
    assert res_modify.status_code == 200
    assert res_modify.json()["approval_status"] == "MODIFIED"


def test_case_queue_api(client: TestClient, sample_case: FraudCaseState):
    """Test GET /api/cases and /api/cases/{case_id} for queue surveillance."""
    # List all cases
    res_list = client.get("/api/cases")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "cases" in data
    assert data["total_count"] >= 1
    assert any(c["case_id"] == sample_case.case_id for c in data["cases"])

    # Filter by status
    res_filter = client.get(f"/api/cases?status={sample_case.case_status.value}")
    assert res_filter.status_code == 200
    filter_data = res_filter.json()
    assert filter_data["total_count"] >= 1

    # Individual case lookup
    res_case = client.get(f"/api/cases/{sample_case.case_id}")
    assert res_case.status_code == 200
    assert res_case.json()["case_id"] == sample_case.case_id


def test_mock_actions_api(client: TestClient):
    """Test POST /api/mock/customer-confirmation and /api/mock/step-up-auth."""
    # Customer Confirmation
    res_conf = client.post(
        "/api/mock/customer-confirmation",
        json={"customer_id": "CUST_001", "transaction_id": "TX_001"},
    )
    assert res_conf.status_code == 200
    data_conf = res_conf.json()
    assert data_conf["execution_mode"] == "SIMULATED"
    assert "confirmed" in data_conf["result"]
    assert "disclaimer" in data_conf

    # Step-Up Auth
    res_auth = client.post(
        "/api/mock/step-up-auth",
        json={"account_id": "ACC_001", "challenge_type": "BIOMETRIC_PUSH"},
    )
    assert res_auth.status_code == 200
    data_auth = res_auth.json()
    assert data_auth["execution_mode"] == "SIMULATED"
    assert "passed" in data_auth["result"]


def test_benchmark_run_api(client: TestClient):
    """Test POST /api/benchmark/run executes cases through unified pipeline."""
    res_bench = client.post(
        "/api/benchmark/run",
        json={"case_ids": ["CASE_001"]},
    )
    assert res_bench.status_code == 200
    data = res_bench.json()
    assert data["benchmark_run_id"] is not None
    assert data["total_cases"] == 1
    assert data["completed_cases"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["case_id"] == "CASE_001"


def test_events_sse_endpoint(client: TestClient, sample_case: FraudCaseState):
    """Test GET /api/investigations/{case_id}/events establishes text/event-stream."""
    response = client.get(f"/api/investigations/{sample_case.case_id}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
