"""ConvAI Innovations Laya Fast Classifier Service (Layer 14).

Provides lightweight, fast local routing and intent classification for:
1. Fraud trigger classification (`TriggerType`)
2. Customer confirmation response classification
3. Analyst response classification

STRICT SAFETY RESTRICTIONS (AGENTS.md & GEMINI.md):
- Laya MUST NOT make final fraud decisions.
- Laya MUST NOT decide policy.
- Laya MUST NOT decide whether an account is blocked.
- Laya MUST NOT vote over individual evidence items.
- Laya MUST NOT replace the main LLM reasoning model.

Features:
- Feature-flagged via `ENABLE_LAYA: bool = False`.
- Graceful deterministic pattern parsing fallback when Laya is disabled, unconfident, or unavailable.
"""

import re
from typing import Any, Dict, Generic, Optional, TypeVar, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.models.state import TriggerType
from backend.app.utils.logging import get_logger

logger = get_logger("models.laya_classifier")

T = TypeVar("T")


class LayaClassificationResult(BaseModel, Generic[T]):
    """Result payload from Laya fast classification task."""

    model_config = ConfigDict(extra="ignore")

    predicted_label: Optional[T] = Field(
        default=None,
        description="The classified label outcome or None if unclassified.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0, 1.0].",
    )
    is_enabled: bool = Field(
        default=False,
        description="Whether Laya model classification was active.",
    )
    is_fallback: bool = Field(
        default=True,
        description="Whether result fell back to deterministic rule matching.",
    )
    model_name: str = Field(
        default="DETERMINISTIC_FALLBACK",
        description="Identifier of model or mechanism used.",
    )
    explanation: str = Field(
        default="",
        description="Brief human-readable rationale for classification outcome.",
    )

    @property
    def category(self) -> str:
        """Helper property returning string representation of predicted label."""
        if self.predicted_label is not None:
            return self.predicted_label.value if hasattr(self.predicted_label, "value") else str(self.predicted_label)
        return "UNKNOWN"

    @property
    def priority(self) -> str:
        """Helper property returning suggested priority string."""
        if self.confidence >= 0.8:
            return "HIGH"
        elif self.confidence >= 0.5:
            return "MEDIUM"
        return "LOW"


class LayaClassifier:
    """ConvAI Innovations Laya local fast classifier with deterministic rule fallback."""

    def __init__(
        self,
        enable: Optional[bool] = None,
        confidence_threshold: float = 0.65,
        model_name: str = "convai-laya-fast-v1",
    ):
        settings = get_settings()
        self.enabled = enable if enable is not None else settings.ENABLE_LAYA
        self.confidence_threshold = confidence_threshold
        self.model_name = model_name

        if self.enabled:
            logger.info("Initialized Laya Fast Classifier (%s)", self.model_name)
        else:
            logger.info("Laya Fast Classifier disabled; using deterministic pattern fallback.")

    # =========================================================================
    # Strict Boundary Enforcements
    # =========================================================================

    def make_fraud_decision(self, *args, **kwargs):
        """STRICT RESTRICTION: Laya is forbidden from making final fraud decisions."""
        raise PermissionError(
            "VIOLATION: Laya classifier is strictly forbidden from making final fraud decisions! "
            "Final fraud reasoning must be performed by the main reasoning model and deterministic policy engine."
        )

    def decide_policy(self, *args, **kwargs):
        """STRICT RESTRICTION: Laya is forbidden from determining policy."""
        raise PermissionError(
            "VIOLATION: Laya classifier is strictly forbidden from making policy decisions! "
            "Policy enforcement must be executed by the deterministic Policy Engine."
        )

    # =========================================================================
    # Task 1: Trigger Classification
    # =========================================================================

    def classify_trigger(
        self,
        raw_input: Union[str, Dict[str, Any]],
    ) -> LayaClassificationResult[TriggerType]:
        """Classify fraud trigger input into standard TriggerType enum."""
        text = str(raw_input).upper() if not isinstance(raw_input, dict) else str(raw_input.get("trigger_type") or raw_input.get("summary") or "").upper()

        if self.enabled:
            # Model inference simulation / execution
            result = self._laya_classify_trigger(text)
            if result.confidence >= self.confidence_threshold and not result.is_fallback:
                return result

        # Deterministic Fallback
        return self._fallback_classify_trigger(text)

    def _laya_classify_trigger(self, text: str) -> LayaClassificationResult[TriggerType]:
        """Simulated/local Laya classification inference for triggers."""
        if "HIGH RISK" in text or "PEP" in text or "VIP" in text or "RULE" in text:
            return LayaClassificationResult(
                predicted_label=TriggerType.HIGH_RISK_RULE,
                confidence=0.92,
                is_enabled=True,
                is_fallback=False,
                model_name=self.model_name,
                explanation="Laya model classified input as HIGH_RISK_RULE trigger.",
            )
        elif "CUSTOMER" in text or "REPORT" in text or "STOLEN" in text or "VICTIM" in text:
            return LayaClassificationResult(
                predicted_label=TriggerType.CUSTOMER_REPORT,
                confidence=0.89,
                is_enabled=True,
                is_fallback=False,
                model_name=self.model_name,
                explanation="Laya model classified input as CUSTOMER_REPORT trigger.",
            )
        elif "ANALYST" in text or "REFERRAL" in text or "ESCALAT" in text:
            return LayaClassificationResult(
                predicted_label=TriggerType.ANALYST_REFERRAL,
                confidence=0.94,
                is_enabled=True,
                is_fallback=False,
                model_name=self.model_name,
                explanation="Laya model classified input as ANALYST_REFERRAL trigger.",
            )
        elif "GRAPH" in text or "ANOMALY" in text or "PASS_THROUGH" in text or "CYCLE" in text:
            return LayaClassificationResult(
                predicted_label=TriggerType.GRAPH_ANOMALY,
                confidence=0.91,
                is_enabled=True,
                is_fallback=False,
                model_name=self.model_name,
                explanation="Laya model classified input as GRAPH_ANOMALY trigger.",
            )
        elif "TRANSACTION" in text or "ALERT" in text or "AMOUNT" in text or "TXN" in text:
            return LayaClassificationResult(
                predicted_label=TriggerType.TRANSACTION_ALERT,
                confidence=0.95,
                is_enabled=True,
                is_fallback=False,
                model_name=self.model_name,
                explanation="Laya model classified input as TRANSACTION_ALERT trigger.",
            )

        return LayaClassificationResult(
            predicted_label=None,
            confidence=0.3,
            is_enabled=True,
            is_fallback=True,
            model_name=self.model_name,
            explanation="Laya model unconfident on trigger classification.",
        )

    def _fallback_classify_trigger(self, text: str) -> LayaClassificationResult[TriggerType]:
        """Deterministic pattern rule fallback for trigger classification."""
        if any(k in text for k in ["HIGH_RISK", "PEP", "SANCTION", "RULE"]):
            label = TriggerType.HIGH_RISK_RULE
        elif any(k in text for k in ["CUSTOMER_REPORT", "REPORT", "VICTIM", "STOLEN"]):
            label = TriggerType.CUSTOMER_REPORT
        elif any(k in text for k in ["ANALYST_REFERRAL", "REFERRAL", "MANUAL_ESCALATION"]):
            label = TriggerType.ANALYST_REFERRAL
        elif any(k in text for k in ["GRAPH_ANOMALY", "PASS_THROUGH", "CYCLE", "ANOMALY"]):
            label = TriggerType.GRAPH_ANOMALY
        else:
            label = TriggerType.TRANSACTION_ALERT

        return LayaClassificationResult(
            predicted_label=label,
            confidence=1.0,
            is_enabled=False,
            is_fallback=True,
            model_name="DETERMINISTIC_FALLBACK",
            explanation=f"Deterministic fallback matched trigger pattern '{label.value}'.",
        )

    # =========================================================================
    # Task 2: Customer Response Classification
    # =========================================================================

    def classify_customer_response(
        self,
        response_text: str,
    ) -> LayaClassificationResult[str]:
        """Classify customer SMS/prompt response into CONFIRMED_AUTHORIZED, DENIED_UNAUTHORIZED, or UNCERTAIN."""
        text = response_text.strip().upper()

        if self.enabled:
            if re.search(r"\b(YES|CONFIRM|AUTHORIZED|I MADE THIS|CORRECT|APPROVED|YES I DID)\b", text):
                return LayaClassificationResult(
                    predicted_label="CONFIRMED_AUTHORIZED",
                    confidence=0.96,
                    is_enabled=True,
                    is_fallback=False,
                    model_name=self.model_name,
                    explanation="Laya model classified customer response as CONFIRMED_AUTHORIZED.",
                )
            elif re.search(r"\b(NO|NOT ME|NOT MY|FRAUD|STOP|CANCEL|UNAUTHORIZED|DENY|DID NOT|HACKED)\b", text):
                return LayaClassificationResult(
                    predicted_label="DENIED_UNAUTHORIZED",
                    confidence=0.96,
                    is_enabled=True,
                    is_fallback=False,
                    model_name=self.model_name,
                    explanation="Laya model classified customer response as DENIED_UNAUTHORIZED.",
                )
            else:
                return LayaClassificationResult(
                    predicted_label="UNCERTAIN",
                    confidence=0.4,
                    is_enabled=True,
                    is_fallback=False,
                    model_name=self.model_name,
                    explanation="Laya model unconfident on customer response; marked UNCERTAIN.",
                )

        # Deterministic Fallback using token set matching
        tokens = set(text.split())
        if any(t in tokens for t in ["YES", "CONFIRM", "1", "AUTHORIZED", "APPROVED"]):
            label = "CONFIRMED_AUTHORIZED"
        elif any(t in tokens for t in ["NO", "STOP", "2", "FRAUD", "CANCEL", "UNAUTHORIZED"]):
            label = "DENIED_UNAUTHORIZED"
        elif "NOT ME" in text or "NOT MY" in text or "DID NOT" in text:
            label = "DENIED_UNAUTHORIZED"
        else:
            label = "UNCERTAIN"

        return LayaClassificationResult(
            predicted_label=label,
            confidence=0.9 if label != "UNCERTAIN" else 0.5,
            is_enabled=False,
            is_fallback=True,
            model_name="DETERMINISTIC_FALLBACK",
            explanation=f"Fallback rule classified customer response as '{label}'.",
        )

    # =========================================================================
    # Task 3: Analyst Response Classification
    # =========================================================================

    def classify_analyst_response(
        self,
        response_text: str,
    ) -> LayaClassificationResult[str]:
        """Classify analyst input text into APPROVE, REJECT, or MODIFY."""
        text = response_text.strip().upper()

        if self.enabled:
            if any(k in text for k in ["APPROVE", "ACCEPTED", "CONFIRMED", "PASSED", "PROCEED"]):
                return LayaClassificationResult(
                    predicted_label="APPROVE",
                    confidence=0.95,
                    is_enabled=True,
                    is_fallback=False,
                    model_name=self.model_name,
                    explanation="Laya model classified analyst response as APPROVE.",
                )
            elif any(k in text for k in ["REJECT", "DENIED", "BLOCK", "DECLINE"]):
                return LayaClassificationResult(
                    predicted_label="REJECT",
                    confidence=0.95,
                    is_enabled=True,
                    is_fallback=False,
                    model_name=self.model_name,
                    explanation="Laya model classified analyst response as REJECT.",
                )
            elif any(k in text for k in ["MODIFY", "CHANGE", "OVERRIDE", "ALTER"]):
                return LayaClassificationResult(
                    predicted_label="MODIFY",
                    confidence=0.92,
                    is_enabled=True,
                    is_fallback=False,
                    model_name=self.model_name,
                    explanation="Laya model classified analyst response as MODIFY.",
                )

        # Deterministic Fallback
        if any(k in text for k in ["APPROVE", "AGREE", "ACCEPT", "YES"]):
            label = "APPROVE"
        elif any(k in text for k in ["REJECT", "DENY", "DECLINE", "NO"]):
            label = "REJECT"
        elif any(k in text for k in ["MODIFY", "CHANGE", "UPDATE"]):
            label = "MODIFY"
        else:
            label = "APPROVE"  # Default assumption for positive analyst sign-off

        return LayaClassificationResult(
            predicted_label=label,
            confidence=0.85,
            is_enabled=False if not self.enabled else True,
            is_fallback=True,
            model_name="DETERMINISTIC_FALLBACK" if not self.enabled else self.model_name,
            explanation=f"Fallback rule classified analyst response as '{label}'.",
        )


# Convenient alias
LayaFastClassifier = LayaClassifier
