"""Unit tests for Layer 16: Main Fraud Reasoning Model Node."""

import pytest

from backend.app.agents.nodes.reasoning import MainReasoningNode, ReasoningOutputSchema
from backend.app.evidence.normalizer import EvidenceNormalizer
from backend.app.llm.router import LLMRouter
from backend.app.models.state import (
    ActionType,
    FraudCaseState,
    NextBestAction,
    RiskLevel,
    TriggerType,
    merge_fraud_case_state,
)


@pytest.fixture
def reasoning_node():
    # Use router in mock mode (no API keys) for fast, deterministic unit testing
    router = LLMRouter(groq_api_key=None, gemini_api_key=None)
    return MainReasoningNode(llm_router=router)


@pytest.fixture
def populated_case_state():
    normalizer = EvidenceNormalizer()

    ev_ctx = normalizer.normalize_transaction_context({
        "transaction_id": "TXN_999",
        "amount": 7500.0,
        "customer_id": "CUST_999",
        "account_id": "ACC_999",
        "device_id": "DEV_999",
    })

    ev_dev = normalizer.normalize_shared_device({
        "device_id": "DEV_999",
        "shared_account_count": 6,
        "shared_customer_count": 4,
        "linked_fraud_cases": ["HIST_101", "HIST_102"],
    })

    state = FraudCaseState(
        case_id="CASE_REASONING_TEST",
        trigger_type=TriggerType.TRANSACTION_ALERT,
        transaction_id="TXN_999",
        customer_id="CUST_999",
        account_ids=["ACC_999"],
        transaction_evidence=ev_ctx,
        device_evidence=ev_dev,
        bank_risk_score=85.0,
    )
    return state


import asyncio


def test_main_reasoning_node_execution(reasoning_node, populated_case_state):
    """Test MainReasoningNode execution over populated FraudCaseState."""
    async def _test():
        patch = await reasoning_node.process(populated_case_state)

        assert isinstance(patch, dict)
        assert "risk_level" in patch
        assert "risk_score" in patch
        assert "confidence" in patch
        assert "evidence_completeness" in patch
        assert "hypotheses" in patch
        assert "pre_evidence_next_best_action" in patch
        assert "explanation" in patch
        assert "timeline" in patch

        # Metrics must remain separate
        assert 0.0 <= patch["risk_score"] <= 1.0
        assert 0.0 <= patch["confidence"] <= 1.0
        assert 0.0 <= patch["evidence_completeness"] <= 1.0

        # Timeline event check
        assert len(patch["timeline"]) == 1
        assert patch["timeline"][0]["event_type"] == "REASONING_COMPLETED"

    asyncio.run(_test())


def test_pre_vs_post_evidence_action_preservation(reasoning_node, populated_case_state):
    """Verify pre-evidence NBA is set on iteration 0, and post-evidence NBA is set on iteration 1."""
    async def _test():
        # Iteration 0 (Initial reasoning)
        populated_case_state.iteration_count = 0
        patch0 = await reasoning_node.process(populated_case_state)

        assert "pre_evidence_next_best_action" in patch0
        assert patch0["pre_evidence_next_best_action"] is not None

        # Merge patch into state
        state1 = merge_fraud_case_state(populated_case_state, patch0)
        assert state1.pre_evidence_next_best_action is not None
        pre_nba_id = state1.pre_evidence_next_best_action.action_id

        # Iteration 1 (Post-evidence loop reasoning)
        state1.iteration_count = 1
        patch1 = await reasoning_node.process(state1)

        assert "post_evidence_next_best_action" in patch1

        state2 = merge_fraud_case_state(state1, patch1)
        # Pre-evidence NBA must be preserved!
        assert state2.pre_evidence_next_best_action is not None
        assert state2.pre_evidence_next_best_action.action_id == pre_nba_id
        assert state2.post_evidence_next_best_action is not None

    asyncio.run(_test())


def test_reasoning_prompt_building(reasoning_node, populated_case_state):
    """Verify reasoning prompt includes evidence IDs and formatted features."""
    features = reasoning_node.feature_engine.compute_features(state=populated_case_state)
    prompt = reasoning_node._build_reasoning_prompt(populated_case_state, features)

    assert "CASE_REASONING_TEST" in prompt
    assert "TXN_999" in prompt
    assert "CUST_999" in prompt
    assert "EVD_TXN_" in prompt or "EVD_DEV_" in prompt
    assert "Bank Rule Risk Score: 85.0" in prompt
