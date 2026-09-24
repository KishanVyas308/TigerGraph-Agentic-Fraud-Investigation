"""Main Fraud Reasoning Model Node (Layer 16).

Processes normalized evidence, deterministic graph features, risk signals, grounded policy context,
and historical case memory through the LLM Provider Router to produce structured risk assessments,
competing hypotheses, uncertainty estimations, missing evidence lists, and next-best-action recommendations.

STRICT REASONING RULES (AGENTS.md & GEMINI.md):
1. Every material assertion MUST reference evidence IDs (supporting & contradictory).
2. Ground all fraud reasoning strictly in verified evidence items (no fabricated transaction facts or graph edges).
3. Historical cases are precedent, NOT proof.
4. Risk level/score, certainty confidence, and evidence completeness MUST remain separate.
5. Preserves pre-evidence recommendation when subsequent evidence loop runs.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.app.features.engine import FraudFeatureSet, GraphFeatureEngine
from backend.app.llm.router import LLMRouter
from backend.app.models.state import (
    ActionType,
    EvidenceCategory,
    EvidenceItem,
    ExecutionMode,
    FraudCaseState,
    FraudHypothesis,
    NextBestAction,
    RiskAssessment,
    RiskLevel,
    TimelineEvent,
)
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("agents.nodes.reasoning")


class ReasoningOutputSchema(BaseModel):
    """Structured Pydantic output schema returned by the main reasoning model."""

    model_config = ConfigDict(extra="ignore")

    risk_level: RiskLevel = Field(
        description="Qualitative risk tier: LOW, MEDIUM, HIGH, or CRITICAL."
    )
    risk_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quantitative fraud risk score between 0.0 (benign) and 1.0 (definite fraud).",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="System certainty in current assessment given available evidence completeness.",
    )
    evidence_completeness: float = Field(
        ge=0.0,
        le=1.0,
        description="Assessment of whether enough evidence has been collected to make a defensible decision.",
    )
    hypotheses: List[FraudHypothesis] = Field(
        description="Competing fraud hypotheses assessed against evidence.",
    )
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of evidence items that support the primary risk/fraud conclusion.",
    )
    contradictory_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of evidence items that contradict or mitigate the fraud hypothesis.",
    )
    missing_evidence: List[str] = Field(
        default_factory=list,
        description="Explicit description of high-value missing evidence items needed if completeness is low.",
    )
    recommended_action_type: ActionType = Field(
        description="Preliminary recommended next-best action.",
    )
    recommended_action_reasoning: str = Field(
        description="Justification for recommended action grounded in evidence IDs and policy.",
    )
    explanation: str = Field(
        description="Concise, auditable explanation of overall fraud risk assessment.",
    )


class MainReasoningNode:
    """LangGraph node executing LLM reasoning over normalized investigation evidence."""

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        feature_engine: Optional[GraphFeatureEngine] = None,
    ):
        self.llm_router = llm_router or LLMRouter()
        self.feature_engine = feature_engine or GraphFeatureEngine()

    async def process(self, state: FraudCaseState) -> Dict[str, Any]:
        """Execute main fraud reasoning on FraudCaseState and return state update patch dict."""
        logger.info("Starting Main Fraud Reasoning for Case %s (Iteration: %d)", state.case_id, state.iteration_count)

        # 1. Ensure deterministic feature set is fresh and computed
        feature_set = self.feature_engine.compute_features(state=state)

        # 2. Format grounded prompt
        prompt = self._build_reasoning_prompt(state, feature_set)
        system_prompt = self._build_system_prompt()

        # 3. Call LLM Router with structured output schema validation
        llm_resp = self.llm_router.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            response_schema=ReasoningOutputSchema,
            use_fast_model=False,
            temperature=0.1,
            max_tokens=2048,
        )

        output: ReasoningOutputSchema
        # The generic router mock only proves schema plumbing; it must never make
        # a fraud decision.  In offline mode use the grounded deterministic
        # assessment below so different evidence produces different outcomes.
        if llm_resp.provider == "mock":
            output = self._fallback_reasoning(state, feature_set)
        elif llm_resp.parsed_output and isinstance(llm_resp.parsed_output, ReasoningOutputSchema):
            output = llm_resp.parsed_output
        else:
            logger.warning("LLM router returned unparsed output for Case %s; constructing default schema.", state.case_id)
            output = self._fallback_reasoning(state, feature_set)

        # 4. Construct typed NextBestAction
        nba = NextBestAction(
            action_type=output.recommended_action_type,
            reasoning=output.recommended_action_reasoning,
            evidence_ids=output.supporting_evidence_ids,
            execution_mode=ExecutionMode.SIMULATED,
        )

        # 5. Build update patch for FraudCaseState
        patch: Dict[str, Any] = {
            "hypotheses": [h.model_dump() for h in output.hypotheses],
            "risk_level": output.risk_level.value if hasattr(output.risk_level, "value") else str(output.risk_level),
            "risk_score": output.risk_score,
            "confidence": output.confidence,
            "evidence_completeness": output.evidence_completeness,
            "missing_evidence": output.missing_evidence,
            "supporting_evidence_ids": output.supporting_evidence_ids,
            "contradictory_evidence_ids": output.contradictory_evidence_ids,
            "explanation": output.explanation,
        }

        # Preserve pre vs post evidence action distinction based on iteration count
        if state.iteration_count == 0 or state.pre_evidence_next_best_action is None:
            patch["pre_evidence_next_best_action"] = nba.model_dump()
        else:
            patch["post_evidence_next_best_action"] = nba.model_dump()

        # Append timeline event
        event = TimelineEvent(
            event_type="REASONING_COMPLETED",
            node_name="main_reasoning",
            description=(
                f"Fraud reasoning completed: Risk={patch['risk_level']} (Score: {output.risk_score:.2f}), "
                f"Confidence={output.confidence:.2f}, Recommended Action={output.recommended_action_type.value}"
            ),
            details={
                "provider": llm_resp.provider,
                "model_name": llm_resp.model_name,
                "latency_ms": llm_resp.latency_ms,
                "is_fallback": llm_resp.is_fallback,
                "action": output.recommended_action_type.value,
            },
        )
        patch["timeline"] = [event.model_dump()]

        logger.info(
            "Completed reasoning for Case %s: Risk=%s, Score=%.2f, Confidence=%.2f, Action=%s",
            state.case_id,
            patch["risk_level"],
            output.risk_score,
            output.confidence,
            output.recommended_action_type.value,
        )

        return patch

    def _build_system_prompt(self) -> str:
        """Construct authoritative system prompt enforcing grounded fraud investigation principles."""
        return (
            "You are an expert financial fraud investigation AI analyst working within a bank's Special Investigations Unit (SIU).\n\n"
            "CRITICAL OPERATING RULES:\n"
            "1. GROUND ALL REASONING IN EVIDENCE: Every material claim must explicitly cite supporting or contradictory evidence IDs (e.g. EVD_TXN_..., EVD_SHR_DEV_...).\n"
            "2. DO NOT FABRICATE FACTS: Never invent transaction amounts, dates, device IDs, policy rules, or graph connections not present in the provided evidence.\n"
            "3. HISTORICAL PRECEDENT IS NOT PROOF: Historical case matches are reference precedent only. They show past analyst decisions, not absolute proof of current guilt.\n"
            "4. SEPARATE METRICS: You MUST evaluate Risk Level/Score (how suspicious), Confidence (certainty), and Evidence Completeness (sufficiency) separately.\n"
            "5. CONTRADICTORY EVIDENCE: Always represent mitigating or contradictory evidence explicitly if present.\n"
            "6. MISSING EVIDENCE: If evidence completeness is low or uncertainty is high, explicitly list what missing evidence items are required."
        )

    def _build_reasoning_prompt(self, state: FraudCaseState, features: FraudFeatureSet) -> str:
        """Construct structured prompt containing all normalized evidence, features, policy, and precedents."""
        sections = [
            f"### CASE INVESTIGATION HEADER",
            f"- Case ID: `{state.case_id}`",
            f"- Trigger Type: `{state.trigger_type.value if hasattr(state.trigger_type, 'value') else state.trigger_type}`",
            f"- Primary Transaction ID: `{state.transaction_id or 'N/A'}`",
            f"- Customer ID: `{state.customer_id or 'N/A'}`",
            f"- Linked Account IDs: {', '.join(state.account_ids) if state.account_ids else 'None'}",
            f"- Current Investigation Iteration: {state.iteration_count}",
        ]

        # 2. Risk Signals
        sections.append("\n### DETERMINISTIC RISK SIGNALS")
        bank_score_str = f"{state.bank_risk_score:.1f}" if state.bank_risk_score is not None else "Unavailable"
        ml_score_str = f"{state.historical_ml_score:.4f}" if state.historical_ml_score is not None else "Unavailable"
        sections.append(f"- Bank Rule Risk Score: {bank_score_str}")
        sections.append(f"- Historical LightGBM ML Risk Score: {ml_score_str}")

        # 3. Deterministic Graph & Behavioral Features
        sections.append("\n### CALCULATED GRAPH & BEHAVIOR FEATURES")
        if features.feature_explanations:
            for feat_key, feat_exp in features.feature_explanations.items():
                sections.append(f"- **{feat_key}**: {feat_exp}")
        else:
            sections.append("*No graph anomalies or velocity triggers identified.*")

        # 4. Normalized Evidence Bundle with explicit Evidence IDs
        sections.append("\n### NORMALIZED EVIDENCE BUNDLE")
        all_ev = state.all_evidence
        if all_ev:
            for item in all_ev:
                cat_val = item.category.value if hasattr(item.category, "value") else str(item.category)
                rel_val = item.reliability.value if hasattr(item.reliability, "value") else str(item.reliability)
                sections.append(f"- `[{item.evidence_id}]` ({cat_val} | Source: {item.source} | Reliability: {rel_val}) {item.fact}")
        else:
            sections.append("*No normalized evidence items collected yet.*")

        # 5. Grounded Policy & Typology Context
        sections.append("\n### POLICY, TYPOLOGY & REGULATORY CONTEXT")
        if state.policy_evidence:
            for p in state.policy_evidence:
                sections.append(f"- `[{p.evidence_id}]` {p.fact}")
        else:
            sections.append("*No explicit policy evidence retrieved.*")

        # 6. Similar Historical Case Precedents
        sections.append("\n### HISTORICAL CASE PRECEDENTS (Precedent Only — Not Proof)")
        if state.historical_case_evidence:
            for c in state.historical_case_evidence:
                sections.append(f"- `[{c.evidence_id}]` {c.fact}")
        else:
            sections.append("*No similar historical case precedents retrieved.*")

        sections.append(
            "\nBased on ALL the evidence above, perform your structured fraud investigation assessment and return the requested JSON schema."
        )

        return "\n".join(sections)

    def _fallback_reasoning(self, state: FraudCaseState, features: FraudFeatureSet) -> ReasoningOutputSchema:
        """Grounded deterministic assessment used when no live LLM is configured."""
        all_evidence = state.all_evidence

        bank_score = state.bank_risk_score
        if bank_score is not None and bank_score > 1.0:
            bank_score /= 100.0
        risk_score = 0.25 if bank_score is None else 0.75 * bank_score

        if (features.fraud_accounts_on_device or 0) > 0:
            risk_score += min(0.15, 0.05 * (features.fraud_accounts_on_device or 0))
        if (features.fraud_neighbors_count or 0) > 0:
            risk_score += min(0.18, 0.06 * (features.fraud_neighbors_count or 0))
        amount_ratio = features.transaction_amount_ratio_to_mean or 0.0
        if amount_ratio >= 3.0:
            risk_score += 0.15
        elif amount_ratio >= 1.8:
            risk_score += 0.08
        if features.cycle_detected:
            risk_score += 0.12
        if features.rapid_pass_through:
            risk_score += 0.12
        if features.new_device:
            risk_score += 0.03
        if features.new_ip:
            risk_score += 0.02
        if features.new_merchant:
            risk_score += 0.02
        if (features.shared_device_account_count or 0) >= 5:
            risk_score += 0.03

        contradictory = [
            item.evidence_id
            for item in all_evidence
            if item.category in (
                EvidenceCategory.CUSTOMER_RESPONSE.value,
                EvidenceCategory.AUTHENTICATION.value,
                EvidenceCategory.EXTERNAL_SIGNAL.value,
            )
            and any(token in item.fact.upper() for token in ("CLEAN", "LEGITIMATE", "PASSED", "VERIFIED"))
        ]
        if contradictory:
            risk_score -= min(0.08, 0.04 * len(contradictory))

        risk_score = round(min(0.98, max(0.02, risk_score)), 2)

        if risk_score >= 0.90:
            level = RiskLevel.CRITICAL
            action = ActionType.BLOCK_TRANSACTION
        elif risk_score >= 0.70:
            level = RiskLevel.HIGH
            action = ActionType.BLOCK_TRANSACTION
        elif risk_score >= 0.40:
            level = RiskLevel.MEDIUM
            action = ActionType.REQUEST_CUSTOMER_CONFIRMATION
        else:
            level = RiskLevel.LOW
            action = ActionType.ALLOW_TRANSACTION

        material_categories = {
            EvidenceCategory.TRANSACTION_BEHAVIOR.value,
            EvidenceCategory.GRAPH_RELATIONSHIP.value,
            EvidenceCategory.DEVICE.value,
            EvidenceCategory.IDENTITY.value,
            EvidenceCategory.MONEY_FLOW.value,
            EvidenceCategory.EXTERNAL_SIGNAL.value,
            EvidenceCategory.AUTHENTICATION.value,
            EvidenceCategory.CUSTOMER_RESPONSE.value,
        }
        supporting = [
            item.evidence_id
            for item in all_evidence
            if item.evidence_id not in contradictory and item.category in material_categories
        ][:8]

        present = {str(item.category) for item in all_evidence}
        domain_checks = [
            EvidenceCategory.TRANSACTION_BEHAVIOR.value in present,
            bool({EvidenceCategory.GRAPH_RELATIONSHIP.value, EvidenceCategory.MONEY_FLOW.value} & present),
            bool({EvidenceCategory.DEVICE.value, EvidenceCategory.IDENTITY.value} & present),
            EvidenceCategory.POLICY.value in present or EvidenceCategory.REGULATION.value in present,
            EvidenceCategory.HISTORICAL_CASE.value in present,
            bool({EvidenceCategory.EXTERNAL_SIGNAL.value, EvidenceCategory.AUTHENTICATION.value, EvidenceCategory.CUSTOMER_RESPONSE.value} & present),
        ]
        evidence_completeness = round(0.25 + 0.115 * sum(domain_checks), 2)
        high_reliability = sum(1 for item in all_evidence if str(item.reliability) == "HIGH")
        reliability_ratio = high_reliability / len(all_evidence) if all_evidence else 0.0
        confidence = round(min(0.95, 0.30 + 0.40 * evidence_completeness + 0.25 * reliability_ratio), 2)

        missing_evidence: List[str] = []
        if not domain_checks[0]:
            missing_evidence.append("Verified transaction context and behavior")
        if not domain_checks[1]:
            missing_evidence.append("Bounded graph relationship analysis")
        if not domain_checks[3]:
            missing_evidence.append("Applicable policy and approval requirements")
        if risk_score >= 0.40 and not domain_checks[5]:
            missing_evidence.append("Customer confirmation or step-up authentication result")

        hypothesis = FraudHypothesis(
            hypothesis_id="HYP_DETERMINISTIC_01",
            title="Transaction and graph anomaly",
            description=(
                f"Deterministic signals support a {level.value.lower()} risk assessment; "
                "historical cases, where present, are treated only as precedent."
            ),
            likelihood=risk_score,
            supporting_evidence_ids=supporting,
            contradictory_evidence_ids=contradictory,
        )

        return ReasoningOutputSchema(
            risk_level=level,
            risk_score=risk_score,
            confidence=confidence,
            evidence_completeness=evidence_completeness,
            hypotheses=[hypothesis],
            supporting_evidence_ids=supporting,
            contradictory_evidence_ids=contradictory,
            missing_evidence=missing_evidence,
            recommended_action_type=action,
            recommended_action_reasoning=(
                f"Offline deterministic assessment recommends {action.value} at {risk_score:.0%} risk "
                f"using evidence {', '.join(supporting) if supporting else 'none available'}."
            ),
            explanation=(
                f"Offline grounded assessment: risk {risk_score:.0%}, confidence {confidence:.0%}, "
                f"and evidence completeness {evidence_completeness:.0%}, derived from the bank signal "
                "and available deterministic graph/behavior evidence."
            ),
        )
