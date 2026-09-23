"""Unit tests for Layer 12: Deterministic Fraud Feature Engine."""

import pytest

from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.features.engine import FraudFeatureSet, GraphFeatureEngine
from backend.app.models.state import FraudCaseState, TriggerType


@pytest.fixture
def feature_engine():
    return GraphFeatureEngine()


def test_compute_features_from_gsql_outputs(feature_engine):
    """Test feature calculation from raw GSQL outputs dict."""
    gsql_outputs = {
        "shared_devices": {
            "shared_account_count": 4,
            "shared_customer_count": 3,
            "linked_fraud_cases": ["HIST_001", "HIST_002"],
        },
        "shared_ips": {
            "shared_account_count": 6,
            "shared_customer_count": 5,
        },
        "fraud_neighbors": {
            "fraud_neighbors_count": 2,
        },
        "shortest_path": {
            "shortest_distance": 2,
            "target_case": "HIST_001",
        },
        "connected_cluster": {
            "connected_component_size": 12,
            "community_size": 8,
        },
        "transaction_behavior": {
            "txn_count_5m": 3,
            "txn_count_1h": 7,
            "txn_count_24h": 15,
            "amount_to_mean_ratio": 4.5,
            "amount_to_median_ratio": 5.2,
            "is_new_merchant": True,
        },
        "device_identity": {
            "is_new_device": True,
            "is_new_ip": False,
        },
        "money_flow": {
            "fan_in_count": 5,
            "fan_out_count": 2,
            "rapid_pass_through": True,
            "cycle_detected": False,
        },
    }

    features = feature_engine.compute_features(gsql_outputs=gsql_outputs)

    # Graph Relationship Features
    assert features.shared_device_account_count == 4
    assert features.shared_device_customer_count == 3
    assert features.fraud_accounts_on_device == 2
    assert features.shared_ip_account_count == 6
    assert features.shared_ip_customer_count == 5
    assert features.fraud_neighbors_count == 2
    assert features.shortest_distance_to_fraud == 2
    assert features.connected_component_size == 12
    assert features.community_size == 8

    # Velocity & Behavior Features
    assert features.transaction_count_5m == 3
    assert features.transaction_count_1h == 7
    assert features.transaction_count_24h == 15
    assert features.transaction_amount_ratio_to_mean == 4.5
    assert features.transaction_amount_ratio_to_median == 5.2
    assert features.new_merchant is True

    # Device & Identity
    assert features.new_device is True
    assert features.new_ip is False

    # Money Flow Features
    assert features.fan_in_count == 5
    assert features.fan_out_count == 2
    assert features.rapid_pass_through is True
    assert features.cycle_detected is False

    # Explanations check: every non-null feature must have a non-empty explanation!
    explanations = features.feature_explanations
    assert len(explanations) >= 15
    for feat_name, exp_text in explanations.items():
        assert len(exp_text) > 10
        assert getattr(features, feat_name) is not None


def test_null_preservation_when_data_unavailable(feature_engine):
    """Verify that missing features preserve None and are never fabricated as 0 or False."""
    features = feature_engine.compute_features(gsql_outputs={})

    # All features must be None
    assert features.shared_device_account_count is None
    assert features.shared_device_customer_count is None
    assert features.fraud_accounts_on_device is None
    assert features.shared_ip_account_count is None
    assert features.fraud_neighbors_count is None
    assert features.shortest_distance_to_fraud is None
    assert features.transaction_count_5m is None
    assert features.transaction_amount_ratio_to_mean is None
    assert features.new_device is None
    assert features.new_merchant is None
    assert features.fan_in_count is None
    assert features.rapid_pass_through is None

    # Explanations dict must be empty
    assert features.feature_explanations == {}


def test_compute_features_from_normalized_evidence(feature_engine):
    """Test feature computation from normalized EvidenceItems (Layer 10 output)."""
    normalizer = EvidenceNormalizer()

    ev_context = normalizer.normalize_transaction_context({
        "transaction_id": "TXN_777",
        "amount": 4500.0,
        "customer_id": "CUST_777",
        "account_id": "ACC_777",
        "device_id": "DEV_777",
    })

    ev_behavior = normalizer.normalize_transaction_behavior({
        "transaction_id": "TXN_777",
        "amount_to_mean_ratio": 3.8,
        "txn_count_5m": 4,
        "is_new_merchant": True,
    })

    ev_device = normalizer.normalize_shared_device({
        "device_id": "DEV_777",
        "shared_account_count": 5,
        "shared_customer_count": 3,
        "linked_fraud_cases": ["HIST_10"],
    })

    all_evidence = ev_context + ev_behavior + ev_device

    features = feature_engine.compute_features(evidence=all_evidence)

    assert features.shared_device_account_count == 5
    assert features.shared_device_customer_count == 3
    assert features.fraud_accounts_on_device == 1
    assert features.transaction_count_5m == 4
    assert features.transaction_amount_ratio_to_mean == 3.8
    assert features.new_merchant is True
    assert "shared_device_account_count" in features.feature_explanations


def test_compute_features_from_fraud_case_state(feature_engine):
    """Test feature computation directly from a FraudCaseState instance."""
    normalizer = EvidenceNormalizer()
    ev_flow = normalizer.normalize_money_flow({
        "account_id": "ACC_STATE_1",
        "fan_in_count": 8,
        "rapid_pass_through": True,
    })

    state = FraudCaseState(
        case_id="CASE_FEATURE_STATE",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_evidence=[],
        graph_evidence=ev_flow,
    )

    features = feature_engine.compute_features(state=state)

    assert features.fan_in_count == 8
    assert features.rapid_pass_through is True
    assert "rapid_pass_through" in features.feature_explanations
