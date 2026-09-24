"""Unit tests for Graph Feature Engine (Layer 35 Deliverable).

Comprehensive verification of:
- Deterministic feature calculations from GSQL outputs
- Feature extraction from normalized evidence items
- Feature calculation directly from FraudCaseState
- Strict preservation of None/null values when data is absent (no invented values)
- Human-readable feature explanations
"""

import pytest

from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.features.engine import FraudFeatureSet, GraphFeatureEngine
from backend.app.models.state import FraudCaseState, TriggerType

# Re-export tests from test_feature_engine
from tests.unit.test_feature_engine import (
    feature_engine,
    test_compute_features_from_fraud_case_state,
    test_compute_features_from_gsql_outputs,
    test_compute_features_from_normalized_evidence,
    test_null_preservation_when_data_unavailable,
)


def test_feature_dictionary_export(feature_engine):
    """Verify FraudFeatureSet exports clean dictionary without None collisions."""
    features = feature_engine.compute_features(
        gsql_outputs={
            "shared_devices": {
                "shared_account_count": 2,
                "shared_customer_count": 1,
            },
            "fraud_neighbors": {
                "fraud_neighbors_count": 3,
            },
        }
    )
    feature_dict = features.to_dict()
    assert feature_dict["shared_device_account_count"] == 2
    assert feature_dict["shared_device_customer_count"] == 1
    assert feature_dict["fraud_neighbors_count"] == 3
    assert feature_dict["new_merchant"] is None
    assert "shared_device_account_count" in feature_dict["feature_explanations"]
