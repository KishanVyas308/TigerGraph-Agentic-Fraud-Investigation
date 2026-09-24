"""Benchmark Output Validator Service (Layer 38).

Strict, non-mutating validation harness for benchmark answer files and run summaries.
Enforces submission format specifications, grounding integrity, evidence provenance,
pre/post NBA preservation, governance, SAR requirements, stop reasons, and TigerGraph persistence.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from backend.app.models.state import (
    ActionType,
    ApprovalRole,
    ApprovalStatus,
    CaseStatus,
    RiskLevel,
    StopReason,
)
from backend.app.schemas.benchmark import (
    BenchmarkValidationIssue,
    BenchmarkValidationReport,
    BenchmarkValidationResult,
    ValidationCategory,
    ValidationSeverity,
)
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("services.benchmark_validator")

# Authoritative allowed stop reasons defined in AGENTS.md §22
ALLOWED_STOP_REASONS: Set[str] = {
    StopReason.SUFFICIENT_EVIDENCE_FOR_ACTION.value,
    StopReason.POLICY_MANDATED_ESCALATION.value,
    StopReason.LOW_VALUE_OF_ADDITIONAL_EVIDENCE.value,
    StopReason.AWAITING_HUMAN_REVIEW.value,
    StopReason.NO_MATERIAL_FRAUD_EVIDENCE.value,
}

# Authoritative allowed final case statuses
ALLOWED_STATUSES: Set[str] = {
    CaseStatus.OPEN.value,
    CaseStatus.IN_PROGRESS.value,
    CaseStatus.AWAITING_EVIDENCE.value,
    CaseStatus.AWAITING_APPROVAL.value,
    CaseStatus.APPROVED.value,
    CaseStatus.REJECTED.value,
    CaseStatus.COMPLETED.value,
    CaseStatus.RESOLVED.value,
    CaseStatus.CLOSED.value,
    CaseStatus.FAILED.value,
}

# Authoritative risk level tiers
ALLOWED_RISK_LEVELS: Set[str] = {
    RiskLevel.LOW.value,
    RiskLevel.MEDIUM.value,
    RiskLevel.HIGH.value,
    RiskLevel.CRITICAL.value,
}


class BenchmarkValidator:
    """Strict validator for benchmark case answers and run summaries.

    Validates compliance without modifying files on disk or auto-correcting semantic decisions.
    """

    def __init__(self, strict: bool = False):
        """Initialize validator.

        Args:
            strict: If True, treat any warning as a validation failure.
        """
        self.strict = strict

    def validate_file(
        self,
        file_path: Union[str, Path],
        strict: Optional[bool] = None,
    ) -> BenchmarkValidationResult:
        """Validate a single benchmark answer JSON file from disk.

        Args:
            file_path: Path to the answer JSON file.
            strict: Override default strict mode if provided.

        Returns:
            BenchmarkValidationResult containing diagnostic issues and pass/fail status.
        """
        path = Path(file_path)
        is_strict = self.strict if strict is None else strict

        if not path.exists():
            return BenchmarkValidationResult(
                file_path=str(path),
                case_id=path.stem,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=[
                    BenchmarkValidationIssue(
                        code="FILE_NOT_FOUND",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Benchmark answer file not found: {path}",
                        field_path="",
                    )
                ],
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            return BenchmarkValidationResult(
                file_path=str(path),
                case_id=path.stem,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=[
                    BenchmarkValidationIssue(
                        code="INVALID_JSON",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Corrupted or invalid JSON format: {exc.msg} (line {exc.lineno}, col {exc.colno})",
                        field_path="",
                        context={"line": exc.lineno, "column": exc.colno},
                    )
                ],
            )
        except Exception as exc:
            return BenchmarkValidationResult(
                file_path=str(path),
                case_id=path.stem,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=[
                    BenchmarkValidationIssue(
                        code="FILE_READ_ERROR",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Failed to read answer file: {str(exc)}",
                        field_path="",
                    )
                ],
            )

        return self.validate_dict(data, file_path=str(path), strict=is_strict)

    def validate_dict(
        self,
        data: Any,
        file_path: str = "<in-memory>",
        strict: Optional[bool] = None,
    ) -> BenchmarkValidationResult:
        """Validate a benchmark answer document in dictionary form.

        Args:
            data: Parsed dictionary representing the answer document.
            file_path: Source identifier or path for reporting.
            strict: Override default strict mode if provided.

        Returns:
            BenchmarkValidationResult with diagnostic issues.
        """
        is_strict = self.strict if strict is None else strict
        issues: List[BenchmarkValidationIssue] = []

        if not isinstance(data, dict):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_ROOT_TYPE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message=f"Root of answer document must be a JSON object (dict), got {type(data).__name__}",
                    field_path="",
                )
            )
            return BenchmarkValidationResult(
                file_path=file_path,
                case_id=None,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=issues,
            )

        case_id = data.get("case_id") or (data.get("case", {}) or data.get("case_details", {})).get("case_id")

        # 1. Structural / Top-Level Presence Checks
        self._validate_top_level_fields(data, issues)

        # 2. Case Details / Anchor Verification
        self._validate_case_details(data, issues)

        # 3. Evidence Bundle Integrity & Provenance
        known_evidence_ids = self._validate_evidence_bundle(data, issues)

        # 4. Evidence Grounding / Citation Cross-Referencing
        self._validate_evidence_grounding(data, known_evidence_ids, issues)

        # 5. Risk, Confidence, Completeness Bounds & Separation
        self._validate_risk_and_confidence(data, issues)

        # 6. Next-Best Action Contracts & Lifecycle Preservation
        self._validate_next_best_actions(data, known_evidence_ids, issues)

        # 7. Governance & Approval Routing
        self._validate_governance(data, issues)

        # 8. Action Execution Contract (SIMULATED mode check)
        self._validate_actions(data, issues)

        # 9. SAR / Report Requirements
        self._validate_sar_requirements(data, issues)

        # 10. Stop Condition & Final Status
        self._validate_stop_conditions(data, issues)

        # 11. TigerGraph Graph Persistence & Memory Quarantine
        self._validate_persistence_and_quarantine(data, issues)

        # Calculate error / warning counts
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)

        is_valid = error_count == 0 and (not is_strict or warning_count == 0)

        return BenchmarkValidationResult(
            file_path=file_path,
            case_id=str(case_id) if case_id else None,
            is_valid=is_valid,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
        )

    # -------------------------------------------------------------------------
    # Internal Validation Checkers
    # -------------------------------------------------------------------------

    def _validate_top_level_fields(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate presence of all required top-level sections mandated by AGENTS.md §34."""
        # Case info
        if "case" not in data and "case_details" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'case' or 'case_details'",
                    field_path="case",
                )
            )

        # Investigation record
        if "internal_investigation_record" not in data and "investigation_record" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'internal_investigation_record'",
                    field_path="internal_investigation_record",
                )
            )
        elif not isinstance(data.get("internal_investigation_record") or data.get("investigation_record"), list):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_FIELD_TYPE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="'internal_investigation_record' must be a JSON array of timeline events",
                    field_path="internal_investigation_record",
                )
            )

        # Evidence collection
        if "evidence" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'evidence'",
                    field_path="evidence",
                )
            )
        elif not isinstance(data["evidence"], list):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_FIELD_TYPE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="'evidence' must be a JSON array of normalized evidence items",
                    field_path="evidence",
                )
            )

        # Findings / Graph features
        if "findings" not in data and "graph_findings" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'findings' or 'graph_findings'",
                    field_path="findings",
                )
            )

        # Actions
        if "actions" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'actions'",
                    field_path="actions",
                )
            )
        elif not isinstance(data["actions"], list):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_FIELD_TYPE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="'actions' must be a JSON array of executed or simulated actions",
                    field_path="actions",
                )
            )

        # Status & Stop Reason
        if "final_status" not in data and "status" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'final_status' or 'status'",
                    field_path="final_status",
                )
            )

        if "stop_reason" not in data:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_FIELD",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing required top-level field: 'stop_reason'",
                    field_path="stop_reason",
                )
            )

    def _validate_case_details(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate case metadata, trigger information, and entity anchoring."""
        case_dict = data.get("case") or data.get("case_details")
        if not isinstance(case_dict, dict):
            # Already reported in top level fields if missing
            return

        case_id = case_dict.get("case_id") or data.get("case_id")
        if not case_id or not isinstance(case_id, str):
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_CASE_ID",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CASE_METADATA,
                    message="Case ID is missing, empty, or not a string",
                    field_path="case.case_id",
                )
            )

        trigger_type = case_dict.get("trigger_type")
        if not trigger_type or not isinstance(trigger_type, str):
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_TRIGGER_TYPE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CASE_METADATA,
                    message="Trigger type is missing or not a string",
                    field_path="case.trigger_type",
                )
            )

        # Entity Anchor Check: At least one anchor entity must be defined
        has_anchor = any([
            case_dict.get("trigger_entity_id"),
            case_dict.get("transaction_id"),
            case_dict.get("customer_id"),
            (case_dict.get("account_ids") and len(case_dict["account_ids"]) > 0),
        ])
        if not has_anchor:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_ENTITY_ANCHOR",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CASE_METADATA,
                    message="Case lacks any entity anchor (trigger_entity_id, transaction_id, customer_id, or account_ids)",
                    field_path="case",
                )
            )

        # Timestamp validations
        opened_at = case_dict.get("opened_at")
        if opened_at:
            try:
                datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
            except ValueError:
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_TIMESTAMP_FORMAT",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.CASE_METADATA,
                        message=f"opened_at timestamp is not valid ISO-8601: '{opened_at}'",
                        field_path="case.opened_at",
                    )
                )

        closed_at = case_dict.get("closed_at") or data.get("closed_at")
        if closed_at:
            try:
                datetime.fromisoformat(str(closed_at).replace("Z", "+00:00"))
            except ValueError:
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_TIMESTAMP_FORMAT",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.CASE_METADATA,
                        message=f"closed_at timestamp is not valid ISO-8601: '{closed_at}'",
                        field_path="case.closed_at",
                    )
                )

    def _validate_evidence_bundle(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> Set[str]:
        """Validate evidence items, strict provenance, reliability, and return set of valid evidence IDs."""
        evidence_list = data.get("evidence")
        if not isinstance(evidence_list, list):
            return set()

        if len(evidence_list) == 0:
            issues.append(
                BenchmarkValidationIssue(
                    code="EMPTY_EVIDENCE_BUNDLE",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.EVIDENCE,
                    message="Evidence collection is completely empty; investigation collected 0 evidence items",
                    field_path="evidence",
                )
            )
            return set()

        known_ids: Set[str] = set()

        for idx, item in enumerate(evidence_list):
            item_path = f"evidence[{idx}]"
            if not isinstance(item, dict):
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_EVIDENCE_ITEM",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Evidence item at index {idx} must be a JSON object, got {type(item).__name__}",
                        field_path=item_path,
                    )
                )
                continue

            eid = item.get("evidence_id")
            if not eid or not isinstance(eid, str):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_EVIDENCE_ID",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Evidence item at index {idx} is missing a non-empty string 'evidence_id'",
                        field_path=f"{item_path}.evidence_id",
                    )
                )
            elif eid in known_ids:
                issues.append(
                    BenchmarkValidationIssue(
                        code="DUPLICATE_EVIDENCE_ID",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Duplicate evidence ID detected in evidence bundle: '{eid}'",
                        field_path=f"{item_path}.evidence_id",
                        context={"duplicate_id": eid},
                    )
                )
            else:
                known_ids.add(eid)

            # Strict Provenance Requirement (AGENTS.md §11)
            source = item.get("source")
            if not source or not isinstance(source, str) or source.strip().upper() in {"", "UNKNOWN"}:
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_EVIDENCE_PROVENANCE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Evidence item '{eid or idx}' has missing, blank, or UNKNOWN source provenance",
                        field_path=f"{item_path}.source",
                    )
                )

            # Category
            category = item.get("category")
            if not category or not isinstance(category, str):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_EVIDENCE_CATEGORY",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Evidence item '{eid or idx}' is missing a valid category string",
                        field_path=f"{item_path}.category",
                    )
                )

            # Fact
            fact = item.get("fact")
            if fact is None or (isinstance(fact, str) and not fact.strip()):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_EVIDENCE_FACT",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Evidence item '{eid or idx}' is missing factual observation text",
                        field_path=f"{item_path}.fact",
                    )
                )

            # Reliability
            rel = item.get("reliability")
            if rel is None:
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_EVIDENCE_RELIABILITY",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.EVIDENCE,
                        message=f"Evidence item '{eid or idx}' is missing reliability metric or tier",
                        field_path=f"{item_path}.reliability",
                    )
                )
            elif isinstance(rel, (int, float)):
                if not (0.0 <= float(rel) <= 1.0):
                    issues.append(
                        BenchmarkValidationIssue(
                            code="INVALID_RELIABILITY_VALUE",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.EVIDENCE,
                            message=f"Numeric reliability {rel} out of valid bounds [0.0, 1.0]",
                            field_path=f"{item_path}.reliability",
                        )
                    )

        return known_ids

    def _validate_evidence_grounding(
        self,
        data: Dict[str, Any],
        known_evidence_ids: Set[str],
        issues: List[BenchmarkValidationIssue],
    ) -> None:
        """Validate that all evidence IDs cited in hypotheses, actions, and decisions exist in the bundle."""
        # 1. Hypotheses citations
        hypotheses = data.get("fraud_hypotheses", [])
        if isinstance(hypotheses, list):
            for h_idx, hyp in enumerate(hypotheses):
                if not isinstance(hyp, dict):
                    continue

                for sup_idx, eid in enumerate(hyp.get("supporting_evidence_ids", [])):
                    if eid not in known_evidence_ids:
                        issues.append(
                            BenchmarkValidationIssue(
                                code="BROKEN_EVIDENCE_ID",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.GROUNDING,
                                message=f"Hypothesis[{h_idx}] cites non-existent supporting evidence ID: '{eid}'",
                                field_path=f"fraud_hypotheses[{h_idx}].supporting_evidence_ids[{sup_idx}]",
                                context={"broken_id": eid},
                            )
                        )

                for con_idx, eid in enumerate(hyp.get("contradictory_evidence_ids", [])):
                    if eid not in known_evidence_ids:
                        issues.append(
                            BenchmarkValidationIssue(
                                code="BROKEN_EVIDENCE_ID",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.GROUNDING,
                                message=f"Hypothesis[{h_idx}] cites non-existent contradictory evidence ID: '{eid}'",
                                field_path=f"fraud_hypotheses[{h_idx}].contradictory_evidence_ids[{con_idx}]",
                                context={"broken_id": eid},
                            )
                        )

        # 2. Action citations
        actions = data.get("actions", [])
        if isinstance(actions, list):
            for a_idx, act in enumerate(actions):
                if not isinstance(act, dict):
                    continue
                for eid in act.get("evidence_ids", []):
                    if eid not in known_evidence_ids:
                        issues.append(
                            BenchmarkValidationIssue(
                                code="BROKEN_EVIDENCE_ID",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.GROUNDING,
                                message=f"Action[{a_idx}] cites non-existent evidence ID: '{eid}'",
                                field_path=f"actions[{a_idx}].evidence_ids",
                                context={"broken_id": eid},
                            )
                        )

        # 3. Next-best action citations
        for nba_key in ["pre_evidence_next_best_action", "post_evidence_next_best_action"]:
            nba = data.get(nba_key) or data.get("decisions", {}).get(nba_key)
            if isinstance(nba, dict):
                for eid in nba.get("evidence_ids", []):
                    if eid not in known_evidence_ids:
                        issues.append(
                            BenchmarkValidationIssue(
                                code="BROKEN_EVIDENCE_ID",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.GROUNDING,
                                message=f"{nba_key} cites non-existent evidence ID: '{eid}'",
                                field_path=f"{nba_key}.evidence_ids",
                                context={"broken_id": eid},
                            )
                        )

    def _validate_risk_and_confidence(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate risk level, risk score, confidence, and completeness scores (AGENTS.md §13)."""
        # Risk level
        risk_level = data.get("risk_level")
        if risk_level is None:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_RISK_LEVEL",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message="Missing 'risk_level' assessment",
                    field_path="risk_level",
                )
            )
        elif str(risk_level).upper() not in ALLOWED_RISK_LEVELS:
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_RISK_LEVEL",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message=f"Invalid risk_level '{risk_level}'. Must be one of {sorted(ALLOWED_RISK_LEVELS)}",
                    field_path="risk_level",
                )
            )

        # Risk score
        risk_score = data.get("risk_score")
        if risk_score is None:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_RISK_SCORE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message="Missing numeric 'risk_score'",
                    field_path="risk_score",
                )
            )
        elif not isinstance(risk_score, (int, float)) or not (0.0 <= float(risk_score) <= 1.0):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_RISK_SCORE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message=f"risk_score '{risk_score}' must be a float between 0.0 and 1.0",
                    field_path="risk_score",
                )
            )

        # Confidence
        confidence = data.get("confidence")
        if confidence is None:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_CONFIDENCE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message="Missing numeric 'confidence'",
                    field_path="confidence",
                )
            )
        elif not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_CONFIDENCE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message=f"confidence '{confidence}' must be a float between 0.0 and 1.0",
                    field_path="confidence",
                )
            )

        # Evidence Completeness
        completeness = data.get("evidence_completeness")
        if completeness is None:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_COMPLETENESS",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message="Missing numeric 'evidence_completeness'",
                    field_path="evidence_completeness",
                )
            )
        elif not isinstance(completeness, (int, float)) or not (0.0 <= float(completeness) <= 1.0):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_COMPLETENESS",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.METRICS,
                    message=f"evidence_completeness '{completeness}' must be a float between 0.0 and 1.0",
                    field_path="evidence_completeness",
                )
            )

    def _validate_next_best_actions(
        self,
        data: Dict[str, Any],
        known_evidence_ids: Set[str],
        issues: List[BenchmarkValidationIssue],
    ) -> None:
        """Validate pre-evidence NBA and post-evidence NBA preservation (AGENTS.md §16)."""
        pre_nba = data.get("pre_evidence_next_best_action") or data.get("decisions", {}).get("pre_evidence_next_best_action")
        post_nba = data.get("post_evidence_next_best_action") or data.get("decisions", {}).get("post_evidence_next_best_action")
        requested_ev = data.get("requested_evidence", [])

        # If requested_evidence is populated, pre_evidence NBA must NEVER be overwritten or missing
        if isinstance(requested_ev, list) and len(requested_ev) > 0:
            if not pre_nba or not isinstance(pre_nba, dict):
                issues.append(
                    BenchmarkValidationIssue(
                        code="PRE_EVIDENCE_NBA_MISSING",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.NBA,
                        message="Additional evidence was requested, but 'pre_evidence_next_best_action' was not preserved",
                        field_path="pre_evidence_next_best_action",
                    )
                )

        # Post-evidence NBA must be present (or explicit stop reason)
        if post_nba is not None:
            if not isinstance(post_nba, dict):
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_NBA_STRUCTURE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.NBA,
                        message="'post_evidence_next_best_action' must be a JSON object",
                        field_path="post_evidence_next_best_action",
                    )
                )
            else:
                action_type = post_nba.get("action_type")
                if not action_type or not isinstance(action_type, str):
                    issues.append(
                        BenchmarkValidationIssue(
                            code="MISSING_ACTION_TYPE",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.NBA,
                            message="'post_evidence_next_best_action' is missing a valid 'action_type'",
                            field_path="post_evidence_next_best_action.action_type",
                        )
                    )

                exec_mode = post_nba.get("execution_mode")
                if exec_mode and str(exec_mode).upper() != "SIMULATED":
                    issues.append(
                        BenchmarkValidationIssue(
                            code="INVALID_EXECUTION_MODE",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.NBA,
                            message=f"Benchmark execution mode must be 'SIMULATED', got '{exec_mode}'",
                            field_path="post_evidence_next_best_action.execution_mode",
                        )
                    )

    def _validate_governance(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate governance and approval route integrity."""
        route = data.get("approval_route") or data.get("decisions", {}).get("approval_route")
        if not route or not isinstance(route, dict):
            issues.append(
                BenchmarkValidationIssue(
                    code="APPROVAL_ROUTE_MISSING",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.GOVERNANCE,
                    message="Missing governance 'approval_route' object",
                    field_path="approval_route",
                )
            )
            return

        approval_required = route.get("approval_required")
        if approval_required is None or not isinstance(approval_required, bool):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_APPROVAL_REQUIRED",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.GOVERNANCE,
                    message="'approval_required' must be a boolean",
                    field_path="approval_route.approval_required",
                )
            )
        elif approval_required is True:
            role = route.get("approval_role")
            if not role or not isinstance(role, str) or role == "SYSTEM_AUTOMATIC":
                issues.append(
                    BenchmarkValidationIssue(
                        code="APPROVAL_ROLE_MISSING",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.GOVERNANCE,
                        message="Human approval is marked required, but 'approval_role' is missing or set to SYSTEM_AUTOMATIC",
                        field_path="approval_route.approval_role",
                    )
                )

    def _validate_actions(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate action records and enforce SIMULATED execution mode (AGENTS.md §20)."""
        actions = data.get("actions", [])
        if not isinstance(actions, list):
            return

        for idx, act in enumerate(actions):
            act_path = f"actions[{idx}]"
            if not isinstance(act, dict):
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_ACTION_ITEM",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.ACTIONS,
                        message=f"Action at index {idx} must be a JSON object",
                        field_path=act_path,
                    )
                )
                continue

            action_type = act.get("action_type")
            if not action_type or not isinstance(action_type, str):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_ACTION_TYPE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.ACTIONS,
                        message=f"Action at index {idx} lacks a valid 'action_type'",
                        field_path=f"{act_path}.action_type",
                    )
                )

            # Strict AGENTS.md §20 constraint: Mocks must be clearly labeled execution_mode = SIMULATED
            exec_mode = act.get("execution_mode")
            if not exec_mode or str(exec_mode).upper() != "SIMULATED":
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_EXECUTION_MODE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.ACTIONS,
                        message=f"Action at index {idx} has invalid execution_mode '{exec_mode}'. Must be 'SIMULATED'.",
                        field_path=f"{act_path}.execution_mode",
                    )
                )

            if "success" not in act or not isinstance(act["success"], bool):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_ACTION_SUCCESS",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.ACTIONS,
                        message=f"Action at index {idx} lacks a boolean 'success' indicator",
                        field_path=f"{act_path}.success",
                    )
                )

    def _validate_sar_requirements(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate SAR report requirements when SAR is filed or recommended (AGENTS.md §21)."""
        actions = data.get("actions", [])
        post_nba = data.get("post_evidence_next_best_action") or data.get("decisions", {}).get("post_evidence_next_best_action", {})
        post_action_type = post_nba.get("action_type") if isinstance(post_nba, dict) else None

        sar_recommended_or_executed = (
            post_action_type == ActionType.FILE_SAR.value
            or any(isinstance(a, dict) and a.get("action_type") == ActionType.FILE_SAR.value for a in actions)
        )

        sar_obj = data.get("sar_report") or data.get("sar")

        if sar_recommended_or_executed:
            if not sar_obj or not isinstance(sar_obj, dict):
                issues.append(
                    BenchmarkValidationIssue(
                        code="SAR_REQUIRED_OUTPUT_MISSING",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.SAR,
                        message="FILE_SAR action was executed or recommended, but no grounded SAR report was included",
                        field_path="sar_report",
                    )
                )
                return

        # If a SAR report is present, validate its fields
        if sar_obj is not None:
            if not isinstance(sar_obj, dict):
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_SAR_STRUCTURE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.SAR,
                        message="SAR report must be a JSON object",
                        field_path="sar_report",
                    )
                )
                return

            sar_id = sar_obj.get("sar_id") or sar_obj.get("report_id")
            if not sar_id or not isinstance(sar_id, str):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_SAR_ID",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.SAR,
                        message="SAR report is missing a non-empty 'sar_id' or 'report_id'",
                        field_path="sar_report.sar_id",
                    )
                )

            narrative = sar_obj.get("narrative")
            if not narrative or not isinstance(narrative, str) or len(narrative.strip()) < 15:
                issues.append(
                    BenchmarkValidationIssue(
                        code="INVALID_SAR_NARRATIVE",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.SAR,
                        message="SAR narrative is missing, empty, or too short to be grounded (<15 chars)",
                        field_path="sar_report.narrative",
                    )
                )

            typology = sar_obj.get("typology")
            if not typology or not isinstance(typology, str):
                issues.append(
                    BenchmarkValidationIssue(
                        code="MISSING_SAR_TYPOLOGY",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.SAR,
                        message="SAR report is missing a typology classification",
                        field_path="sar_report.typology",
                    )
                )

    def _validate_stop_conditions(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate stop reason and final case status (AGENTS.md §22)."""
        stop_reason = data.get("stop_reason")
        if not stop_reason:
            issues.append(
                BenchmarkValidationIssue(
                    code="STOP_REASON_MISSING",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.LIFECYCLE,
                    message="Investigation lacks an explicit stop reason",
                    field_path="stop_reason",
                )
            )
        elif str(stop_reason).upper() not in ALLOWED_STOP_REASONS:
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_STOP_REASON",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.LIFECYCLE,
                    message=f"Stop reason '{stop_reason}' is not in allowed set: {sorted(ALLOWED_STOP_REASONS)}",
                    field_path="stop_reason",
                    context={"allowed_stop_reasons": list(ALLOWED_STOP_REASONS)},
                )
            )

        status = data.get("final_status") or data.get("status")
        if status and str(status).upper() not in ALLOWED_STATUSES:
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_STATUS",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.LIFECYCLE,
                    message=f"Case status '{status}' is not in allowed statuses: {sorted(ALLOWED_STATUSES)}",
                    field_path="final_status",
                )
            )

    def _validate_persistence_and_quarantine(self, data: Dict[str, Any], issues: List[BenchmarkValidationIssue]) -> None:
        """Validate TigerGraph graph persistence verification and precedent quarantine."""
        # Layer 38: "case graph-write verification failed"
        persisted = data.get("graph_persisted")
        if persisted is not True:
            issues.append(
                BenchmarkValidationIssue(
                    code="GRAPH_PERSISTENCE_FAILED",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.PERSISTENCE,
                    message="TigerGraph case graph persistence verification failed ('graph_persisted' is False or missing)",
                    field_path="graph_persisted",
                )
            )

        # Precedent quarantine: benchmark cases should not be indexed as future precedents (vector_indexed=False)
        is_indexed = data.get("vector_indexed")
        if is_indexed is True:
            issues.append(
                BenchmarkValidationIssue(
                    code="BENCHMARK_QUARANTINE_VIOLATION",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.QUARANTINE,
                    message="Benchmark case was indexed into vector precedent memory; benchmark cases must be quarantined",
                    field_path="vector_indexed",
                )
            )

    # -------------------------------------------------------------------------
    # Batch Directory & Summary Validation
    # -------------------------------------------------------------------------

    def validate_run_summary(
        self,
        file_path: Union[str, Path],
        strict: Optional[bool] = None,
    ) -> BenchmarkValidationResult:
        """Validate a benchmark_run_summary.json report file."""
        path = Path(file_path)
        is_strict = self.strict if strict is None else strict

        if not path.exists():
            return BenchmarkValidationResult(
                file_path=str(path),
                case_id=None,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=[
                    BenchmarkValidationIssue(
                        code="SUMMARY_NOT_FOUND",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Benchmark run summary file not found: {path}",
                        field_path="",
                    )
                ],
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            return BenchmarkValidationResult(
                file_path=str(path),
                case_id=None,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=[
                    BenchmarkValidationIssue(
                        code="INVALID_SUMMARY_JSON",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Failed to parse summary JSON: {str(exc)}",
                        field_path="",
                    )
                ],
            )

        issues: List[BenchmarkValidationIssue] = []

        if not isinstance(data, dict):
            issues.append(
                BenchmarkValidationIssue(
                    code="INVALID_SUMMARY_ROOT",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Summary root must be a JSON object",
                    field_path="",
                )
            )
            return BenchmarkValidationResult(
                file_path=str(path),
                is_valid=False,
                error_count=1,
                issues=issues,
            )

        run_id = data.get("benchmark_run_id")
        if not run_id:
            issues.append(
                BenchmarkValidationIssue(
                    code="MISSING_RUN_ID",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Summary missing benchmark_run_id",
                    field_path="benchmark_run_id",
                )
            )

        total_cases = data.get("total_cases", 0)
        completed_cases = data.get("completed_cases", 0)
        failed_cases = data.get("failed_cases", 0)

        if total_cases < 20:
            issues.append(
                BenchmarkValidationIssue(
                    code="INCOMPLETE_BENCHMARK_SUITE",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.STRUCTURE,
                    message=f"Summary covers {total_cases} cases, but the benchmark suite has 20 cases",
                    field_path="total_cases",
                )
            )

        if failed_cases > 0:
            issues.append(
                BenchmarkValidationIssue(
                    code="BENCHMARK_CASES_FAILED",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.LIFECYCLE,
                    message=f"Benchmark summary reports {failed_cases} failed case(s)",
                    field_path="failed_cases",
                )
            )

        if completed_cases < total_cases:
            issues.append(
                BenchmarkValidationIssue(
                    code="UNFINISHED_CASES",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.LIFECYCLE,
                    message=f"Only {completed_cases}/{total_cases} cases completed",
                    field_path="completed_cases",
                )
            )

        quarantine_verified = data.get("quarantine_verified")
        if quarantine_verified is not True:
            issues.append(
                BenchmarkValidationIssue(
                    code="QUARANTINE_NOT_VERIFIED",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.QUARANTINE,
                    message="Summary quarantine_verified is not True",
                    field_path="quarantine_verified",
                )
            )

        # Validate individual case metrics
        cases = data.get("cases", [])
        if isinstance(cases, list):
            for idx, c in enumerate(cases):
                if not isinstance(c, dict):
                    continue
                cid = c.get("case_id")
                if c.get("status") != "COMPLETED":
                    issues.append(
                        BenchmarkValidationIssue(
                            code="CASE_NOT_COMPLETED",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.LIFECYCLE,
                            message=f"Case {cid or idx} status is '{c.get('status')}', expected 'COMPLETED'",
                            field_path=f"cases[{idx}].status",
                        )
                    )
                if c.get("is_persisted") is not True:
                    issues.append(
                        BenchmarkValidationIssue(
                            code="CASE_NOT_PERSISTED",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.PERSISTENCE,
                            message=f"Case {cid or idx} is_persisted is not True",
                            field_path=f"cases[{idx}].is_persisted",
                        )
                    )

        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        is_valid = error_count == 0 and (not is_strict or warning_count == 0)

        return BenchmarkValidationResult(
            file_path=str(path),
            case_id="SUMMARY",
            is_valid=is_valid,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
        )

    def validate_directory(
        self,
        dir_path: Union[str, Path] = "outputs/benchmark",
        strict: Optional[bool] = None,
        require_all_20: bool = True,
    ) -> BenchmarkValidationReport:
        """Validate all benchmark answer files in a directory.

        Args:
            dir_path: Target directory containing CASE_*.json files.
            strict: If True, treat any warning as failure.
            require_all_20: If True, fail if any of CASE_001.json through CASE_020.json is missing.

        Returns:
            BenchmarkValidationReport summarizing results across the entire suite.
        """
        directory = Path(dir_path)
        is_strict = self.strict if strict is None else strict
        started_at = now_iso()

        results: List[BenchmarkValidationResult] = []

        if not directory.exists() or not directory.is_dir():
            result = BenchmarkValidationResult(
                file_path=str(directory),
                case_id=None,
                is_valid=False,
                error_count=1,
                warning_count=0,
                issues=[
                    BenchmarkValidationIssue(
                        code="DIRECTORY_NOT_FOUND",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Output directory does not exist or is not a directory: {directory}",
                        field_path="",
                    )
                ],
            )
            return BenchmarkValidationReport(
                total_files=0,
                valid_files=0,
                invalid_files=1,
                total_errors=1,
                total_warnings=0,
                is_all_valid=False,
                results=[result],
                started_at=started_at,
                completed_at=now_iso(),
            )

        # If require_all_20, explicitly check for all 20 canonical cases
        target_case_files: List[Path] = []
        if require_all_20:
            for i in range(1, 21):
                case_file = directory / f"CASE_{i:03d}.json"
                target_case_files.append(case_file)
        else:
            target_case_files = sorted(directory.glob("CASE_*.json"))

        for file_path in target_case_files:
            res = self.validate_file(file_path, strict=is_strict)
            results.append(res)

        # Check summary file if present
        summary_path = directory / "benchmark_run_summary.json"
        summary_result: Optional[BenchmarkValidationResult] = None
        if summary_path.exists():
            summary_result = self.validate_run_summary(summary_path, strict=is_strict)

        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        invalid_files = total_files - valid_files
        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)

        if summary_result:
            total_errors += summary_result.error_count
            total_warnings += summary_result.warning_count

        is_all_valid = (invalid_files == 0) and (summary_result is None or summary_result.is_valid)

        return BenchmarkValidationReport(
            total_files=total_files,
            valid_files=valid_files,
            invalid_files=invalid_files,
            total_errors=total_errors,
            total_warnings=total_warnings,
            is_all_valid=is_all_valid,
            results=results,
            summary_validation=summary_result,
            started_at=started_at,
            completed_at=now_iso(),
        )
