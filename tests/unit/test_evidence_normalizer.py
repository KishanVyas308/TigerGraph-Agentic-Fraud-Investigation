"""Unit tests for Layer 10: Evidence Model and Evidence Normalizer."""

import pytest

from pydantic import BaseModel, Field

from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.models.state import EvidenceCategory, EvidenceItem, EvidenceReliability


class MockPolicyContextItem(BaseModel):
    chunk_id: str
    source_id: str
    document_type: str
    section_title: str
    text: str
    relevance_score: float
    graph_references: list = Field(default_factory=list)


class MockPolicyContextResult(BaseModel):
    items: list = Field(default_factory=list)


class MockSimilarCaseItem(BaseModel):
    case_id: str
    outcome: str
    primary_typology: str
    summary: str
    shared_entities: list = Field(default_factory=list)
    combined_score: float = 0.0
    retrieval_method: str = "HYBRID"


class MockSimilarCasesResult(BaseModel):
    cases: list = Field(default_factory=list)


@pytest.fixture
def normalizer():
    return EvidenceNormalizer()


def test_normalize_transaction_context(normalizer):
    """Test GSQL transaction context query normalization."""
    raw_ctx = {
        "transaction_id": "TXN_1001",
        "amount": 2500.50,
        "currency": "USD",
        "merchant_id": "MCH_999",
        "merchant_category": "ELECTRONICS",
        "customer_id": "CUST_501",
        "account_id": "ACC_101",
        "device_id": "DEV_701",
        "ip_address": "192.168.1.50",
        "channel": "MOBILE_APP",
        "location": "New York, USA",
        "timestamp": "2026-09-23T12:00:00Z",
    }

    items = normalizer.normalize_transaction_context(raw_ctx)
    assert len(items) == 3

    # Check Core Transaction Fact
    txn_ev = next(i for i in items if i.category == EvidenceCategory.TRANSACTION_BEHAVIOR.value)
    assert "TXN_1001" in txn_ev.fact
    assert "2,500.50" in txn_ev.fact
    assert txn_ev.source == "TIGERGRAPH_GSQL"
    assert txn_ev.reliability == EvidenceReliability.HIGH.value
    assert "ACC_101" in txn_ev.entity_ids

    # Check Device Fact
    dev_ev = next(i for i in items if i.category == EvidenceCategory.DEVICE.value)
    assert "DEV_701" in dev_ev.fact
    assert "192.168.1.50" in dev_ev.fact
    assert dev_ev.source == "TIGERGRAPH_GSQL"

    # Check Identity Fact
    idn_ev = next(i for i in items if i.category == EvidenceCategory.IDENTITY.value)
    assert "CUST_501" in idn_ev.fact
    assert "ACC_101" in idn_ev.fact


def test_normalize_transaction_behavior(normalizer):
    """Test GSQL transaction behavior normalization."""
    raw_bhv = {
        "transaction_id": "TXN_1001",
        "historical_mean_amount": 500.0,
        "amount_to_mean_ratio": 5.0,
        "historical_median_amount": 400.0,
        "amount_to_median_ratio": 6.25,
        "txn_count_5m": 3,
        "txn_count_1h": 7,
        "txn_count_24h": 12,
        "is_new_merchant": True,
    }

    items = normalizer.normalize_transaction_behavior(raw_bhv)
    assert len(items) == 3

    # Amount deviation
    amt_ev = items[0]
    assert "5.0x historical mean" in amt_ev.fact
    assert amt_ev.source == "TIGERGRAPH_GSQL"

    # Velocity
    vel_ev = items[1]
    assert "3 in 5m" in vel_ev.fact
    assert "7 in 1h" in vel_ev.fact

    # Merchant novelty
    mch_ev = items[2]
    assert "NEW merchant" in mch_ev.fact


def test_normalize_shared_device_and_ip(normalizer):
    """Test GSQL shared device and IP normalization."""
    raw_dev = {
        "device_id": "DEV_SHARED_1",
        "shared_account_count": 5,
        "shared_customer_count": 4,
        "linked_fraud_cases": ["HIST_CASE_01", "HIST_CASE_02"],
    }

    dev_items = normalizer.normalize_shared_device(raw_dev)
    assert len(dev_items) == 2

    # Device sharing
    dev_share_ev = dev_items[0]
    assert dev_share_ev.category == EvidenceCategory.DEVICE.value
    assert "shared across 5 accounts" in dev_share_ev.fact

    # Fraud case connection
    dev_frd_ev = dev_items[1]
    assert dev_frd_ev.category == EvidenceCategory.GRAPH_RELATIONSHIP.value
    assert "HIST_CASE_01" in dev_frd_ev.fact

    raw_ip = {
        "ip_address": "10.0.0.1",
        "shared_account_count": 8,
        "shared_customer_count": 6,
        "linked_fraud_cases": [],
    }
    ip_items = normalizer.normalize_shared_ip(raw_ip)
    assert len(ip_items) == 1
    assert "shared across 8 accounts" in ip_items[0].fact


def test_normalize_graph_relationships_and_money_flow(normalizer):
    """Test GSQL graph relationships, shortest path, and money flow normalization."""
    raw_nbr = {
        "vertex_id": "ACC_101",
        "fraud_neighbors_count": 2,
        "neighbor_case_ids": ["HIST_001", "HIST_002"],
    }
    nbr_items = normalizer.normalize_fraud_neighbors(raw_nbr)
    assert len(nbr_items) == 1
    assert "2 fraud-linked neighbors" in nbr_items[0].fact
    assert nbr_items[0].category == EvidenceCategory.GRAPH_RELATIONSHIP.value

    raw_pth = {
        "vertex_id": "ACC_101",
        "target_fraud_case_id": "HIST_005",
        "shortest_distance": 2,
        "path_nodes": ["ACC_101", "DEV_99", "HIST_005"],
    }
    pth_items = normalizer.normalize_shortest_path(raw_pth)
    assert len(pth_items) == 1
    assert "is 2 hop(s)" in pth_items[0].fact

    raw_flow = {
        "account_id": "ACC_101",
        "fan_in_count": 6,
        "fan_out_count": 4,
        "rapid_pass_through": True,
        "cycle_detected": False,
    }
    flow_items = normalizer.normalize_money_flow(raw_flow)
    assert len(flow_items) == 1
    assert flow_items[0].category == EvidenceCategory.MONEY_FLOW.value
    assert "Rapid fund pass-through" in flow_items[0].fact


def test_normalize_graphrag_policy(normalizer):
    """Test GraphRAG policy retrieval output normalization."""
    policy_res = MockPolicyContextResult(
        items=[
            MockPolicyContextItem(
                chunk_id="POL_ATO_01",
                source_id="POL_BANK_01",
                document_type="POLICY",
                section_title="Account Takeover Controls",
                text="High risk transactions on new device exceeding $1,000 require step-up authentication.",
                relevance_score=0.89,
            ),
            MockPolicyContextItem(
                chunk_id="TYP_CARD_02",
                source_id="TYP_002",
                document_type="TYPOLOGY",
                section_title="Card Testing Pattern",
                text="Rapid low-value transactions followed by maximum amount transfer.",
                relevance_score=0.82,
            ),
        ]
    )

    items = normalizer.normalize_graphrag_policy(policy_res)
    assert len(items) == 2

    assert items[0].source == "POLICY_GRAPHRAG"
    assert items[0].category == EvidenceCategory.POLICY.value
    assert "[POL_BANK_01] Account Takeover Controls" in items[0].fact

    assert items[1].source == "POLICY_GRAPHRAG"
    assert items[1].category == EvidenceCategory.POLICY.value
    assert "[TYP_002] Card Testing Pattern" in items[1].fact


def test_normalize_graphrag_cases(normalizer):
    """Test GraphRAG historical case precedent retrieval normalization."""
    cases_res = MockSimilarCasesResult(
        cases=[
            MockSimilarCaseItem(
                case_id="HIST_CASE_100",
                outcome="FRAUD_CONFIRMED",
                primary_typology="ACCOUNT_TAKEOVER",
                summary="Victim account compromised via credential stuffing; funds transferred out via shared device.",
                shared_entities=["DEV_701"],
                combined_score=0.88,
                retrieval_method="HYBRID",
            ),
            MockSimilarCaseItem(
                case_id="HIST_CASE_200",
                outcome="FALSE_POSITIVE_CLEARED",
                primary_typology="TRAVEL_ANOMALY",
                summary="Customer initiated legitimate transaction while traveling internationally.",
                shared_entities=[],
                combined_score=0.75,
                retrieval_method="VECTOR",
            ),
        ]
    )

    items = normalizer.normalize_graphrag_cases(cases_res)
    assert len(items) == 2

    assert items[0].source == "CASE_MEMORY"
    assert items[0].category == EvidenceCategory.HISTORICAL_CASE.value
    assert "HIST_CASE_100" in items[0].fact
    assert "FRAUD_CONFIRMED" in items[0].fact
    assert "DEV_701" in items[0].entity_ids

    assert items[1].source == "CASE_MEMORY"
    assert "FALSE_POSITIVE_CLEARED" in items[1].fact


def test_normalize_external_and_response_sources(normalizer):
    """Test normalization of customer response, auth result, analyst input, and external signal."""
    # Customer response
    cust_ev = normalizer.normalize_customer_response({
        "transaction_id": "TXN_1001",
        "confirmed_authorized": False,
        "channel": "SMS",
    })
    assert len(cust_ev) == 1
    assert cust_ev[0].source == "CUSTOMER_RESPONSE"
    assert cust_ev[0].category == EvidenceCategory.CUSTOMER_RESPONSE.value
    assert "DENIED / REPORTED UNAUTHORIZED" in cust_ev[0].fact

    # Step-up auth result
    auth_ev = normalizer.normalize_authentication_result({
        "customer_id": "CUST_501",
        "method": "SMS_OTP",
        "verified": True,
    })
    assert len(auth_ev) == 1
    assert auth_ev[0].source == "AUTHENTICATION_SERVICE"
    assert auth_ev[0].category == EvidenceCategory.AUTHENTICATION.value
    assert "PASSED" in auth_ev[0].fact

    # Analyst input
    anl_ev = normalizer.normalize_analyst_input({
        "analyst_id": "A101",
        "case_id": "CASE_99",
        "note": "Spoke to customer via phone call; customer confirmed card was stolen.",
    })
    assert len(anl_ev) == 1
    assert anl_ev[0].source == "ANALYST_INPUT"
    assert "A101" in anl_ev[0].fact

    # External signal
    ext_ev = normalizer.normalize_external_signal({
        "provider": "IPQualityScore",
        "entity_id": "192.168.1.50",
        "signal_type": "IP_REPUTATION",
        "score": 92,
        "flag": "TOR_EXIT_NODE",
    })
    assert len(ext_ev) == 1
    assert ext_ev[0].source == "EXTERNAL_SIGNAL"
    assert ext_ev[0].category == EvidenceCategory.EXTERNAL_SIGNAL.value
    assert "TOR_EXIT_NODE" in ext_ev[0].fact


def test_deduplicate_evidence(normalizer):
    """Test evidence deduplication by ID and fact text."""
    ev1 = EvidenceItem(
        evidence_id="EVD_DUP_1",
        source="GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Fact string 1",
    )
    ev2 = EvidenceItem(
        evidence_id="EVD_DUP_1",  # Same evidence ID
        source="GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Fact string 1 different",
    )
    ev3 = EvidenceItem(
        evidence_id="EVD_DUP_3",
        source="GSQL",
        category=EvidenceCategory.TRANSACTION_BEHAVIOR,
        fact="Fact string 1",  # Duplicate fact text
    )

    deduped = normalizer.deduplicate([ev1, ev2, ev3])
    assert len(deduped) == 1
    assert deduped[0].evidence_id == "EVD_DUP_1"


def test_normalize_bundle(normalizer):
    """Test full heterogeneous tool output bundle normalization."""
    bundle = {
        "transaction_context": {
            "transaction_id": "TXN_888",
            "amount": 5000.0,
            "account_id": "ACC_888",
            "customer_id": "CUST_888",
            "device_id": "DEV_888",
        },
        "transaction_behavior": {
            "transaction_id": "TXN_888",
            "amount_to_mean_ratio": 4.5,
            "is_new_merchant": True,
        },
        "customer_response": {
            "transaction_id": "TXN_888",
            "confirmed_authorized": False,
            "channel": "PUSH_NOTIFICATION",
        },
    }

    items = normalizer.normalize_bundle(bundle)
    assert len(items) >= 4  # 2 from context + 2 from behavior + 1 from response

    sources = {i.source for i in items}
    assert "TIGERGRAPH_GSQL" in sources
    assert "CUSTOMER_RESPONSE" in sources
