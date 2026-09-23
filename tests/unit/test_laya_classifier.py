"""Unit tests for Layer 14: ConvAI Innovations Laya Fast Classifier."""

import pytest

from backend.app.models.laya_classifier import (
    LayaClassificationResult,
    LayaClassifier,
)
from backend.app.models.state import TriggerType


def test_trigger_classification_laya_enabled():
    """Test fast trigger classification when Laya model is enabled."""
    classifier = LayaClassifier(enable=True)

    res = classifier.classify_trigger("HIGH RISK CUSTOMER WITH SANCTION MATCH")
    assert isinstance(res, LayaClassificationResult)
    assert res.predicted_label == TriggerType.HIGH_RISK_RULE
    assert res.confidence > 0.8
    assert res.is_enabled is True
    assert res.is_fallback is False

    res_device = classifier.classify_trigger("GRAPH ANOMALY MULTI HOP PASS THROUGH")
    assert res_device.predicted_label == TriggerType.GRAPH_ANOMALY


def test_trigger_classification_fallback():
    """Test deterministic pattern fallback when Laya is disabled."""
    classifier = LayaClassifier(enable=False)

    res = classifier.classify_trigger("ANALYST_REFERRAL FOR MANUAL ESCALATION")
    assert res.predicted_label == TriggerType.ANALYST_REFERRAL
    assert res.is_enabled is False
    assert res.is_fallback is True
    assert res.model_name == "DETERMINISTIC_FALLBACK"


def test_customer_response_classification():
    """Test classification of customer SMS confirmation responses."""
    classifier = LayaClassifier(enable=True)

    res_yes = classifier.classify_customer_response("Yes, I authorized this transfer")
    assert res_yes.predicted_label == "CONFIRMED_AUTHORIZED"
    assert res_yes.confidence >= 0.9

    res_no = classifier.classify_customer_response("No! I did not make this transaction! Fraud!")
    assert res_no.predicted_label == "DENIED_UNAUTHORIZED"
    assert res_no.confidence >= 0.9

    res_unknown = classifier.classify_customer_response("I am not sure what this is")
    assert res_unknown.predicted_label == "UNCERTAIN"


def test_analyst_response_classification():
    """Test classification of human analyst responses."""
    classifier = LayaClassifier(enable=False)

    res_app = classifier.classify_analyst_response("Approve action block transaction")
    assert res_app.predicted_label == "APPROVE"

    res_rej = classifier.classify_analyst_response("Reject recommendation, customer confirmed")
    assert res_rej.predicted_label == "REJECT"

    res_mod = classifier.classify_analyst_response("Modify action to step-up auth")
    assert res_mod.predicted_label == "MODIFY"


def test_strict_safety_restrictions():
    """Verify strict prohibition of Laya making final fraud decisions or policy enforcement."""
    classifier = LayaClassifier(enable=True)

    with pytest.raises(PermissionError) as exc_info:
        classifier.make_fraud_decision(case_id="CASE_123")
    assert "strictly forbidden" in str(exc_info.value).lower()

    with pytest.raises(PermissionError) as exc_info:
        classifier.decide_policy(action="BLOCK_ACCOUNT")
    assert "strictly forbidden" in str(exc_info.value).lower()
