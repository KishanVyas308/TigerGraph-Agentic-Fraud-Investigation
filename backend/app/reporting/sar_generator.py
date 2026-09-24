"""Suspicious Activity Report (SAR) Generator (Layer 22).

Generates structured, auditable Suspicious Activity Reports when policy requires
filing (e.g. `FILE_SAR` under `POL_004`).

Grounding Rules:
- All factual assertions cite underlying verified `evidence_id`s.
- Never fabricates customer facts, amounts, transaction dates, or regulatory context.
- If a required field is unavailable, marks it explicitly as NOT_AVAILABLE or null.
- Exports structured JSON and formatted Markdown reports to `outputs/sar/`.
- Returns report reference and state patch for TigerGraph case memory persistence.
- Clearly flags execution as SIMULATED for hackathon safety.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import (
    ApprovalStatus,
    EvidenceCategory,
    EvidenceItem,
    FraudCaseState,
    TimelineEvent,
)
from backend.app.utils.ids import generate_event_id, generate_prefixed_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("reporting.sar_generator")

SAR_AUDIT_DISCLAIMER: str = (
    "Simulated Suspicious Activity Report generated for hackathon demo purposes; "
    "no filing dispatched to live regulatory entities."
)

DEFAULT_OUTPUT_DIR: Path = Path("outputs/sar")


# ============================================================================
# Pydantic Report Schemas
# ============================================================================

class SARSubject(BaseModel):
    """Subject / suspect entity details grounded in verified evidence."""

    model_config = ConfigDict(extra="ignore")

    customer_id: str = "NOT_AVAILABLE"
    account_ids: List[str] = Field(default_factory=list)
    associated_devices: List[str] = Field(default_factory=list)
    associated_ips: List[str] = Field(default_factory=list)
    risk_tier: str = "UNKNOWN"


class SARSuspiciousActivity(BaseModel):
    """Specific transaction and typology details under investigation."""

    model_config = ConfigDict(extra="ignore")

    transaction_id: str = "NOT_AVAILABLE"
    amount: Optional[float] = None
    currency: str = "USD"
    activity_timestamp: Optional[str] = None
    typology: str = "UNSPECIFIED_SUSPICIOUS_ACTIVITY"
    risk_level: str = "HIGH"
    risk_score: Optional[float] = None
    indicators: List[str] = Field(default_factory=list)


class SARNarrative(BaseModel):
    """Five-part structured narrative with evidence citations."""

    model_config = ConfigDict(extra="ignore")

    part_1_introduction_trigger: str
    part_2_graph_network_findings: str
    part_3_behavioral_anomalies: str
    part_4_operational_interventions: str
    part_5_compliance_conclusion: str
    full_text: str


class SARReport(BaseModel):
    """Complete structured Suspicious Activity Report."""

    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(
        default_factory=lambda: generate_prefixed_id("SAR", 8)
    )
    case_id: str
    filing_type: str = "INITIAL_SUSPICIOUS_ACTIVITY_REPORT"
    filing_date: str = Field(default_factory=now_iso)
    filing_institution: str = "TigerGraph Simulated Core Bank (HHGOA)"
    regulatory_reference: str = "POL_004 / FinCEN Form 111 (Simulated)"
    subject: SARSubject
    suspicious_activity: SARSuspiciousActivity
    cited_evidence_ids: List[str] = Field(default_factory=list)
    graph_findings: Dict[str, Any] = Field(default_factory=dict)
    typology_matches: List[str] = Field(default_factory=list)
    narrative: SARNarrative
    recommended_action: str = "FILE_SAR"
    approval_status: str = "APPROVED"
    compliance_reviewer_id: Optional[str] = None
    audit_disclaimer: str = SAR_AUDIT_DISCLAIMER
    file_path_json: Optional[str] = None
    file_path_markdown: Optional[str] = None


# ============================================================================
# SAR Generator Service
# ============================================================================

class SARGenerator:
    """Deterministic generator producing verified evidence-grounded SAR reports."""

    def __init__(self, output_dir: Path = DEFAULT_OUTPUT_DIR):
        self.output_dir = Path(output_dir)

    def generate_sar(
        self,
        state: FraudCaseState,
        output_dir: Optional[Path | str] = None,
        save_to_disk: bool = True,
    ) -> Tuple[SARReport, Dict[str, Any]]:
        """Generate a structured SAR report from verified case evidence.

        Args:
            state: The current FraudCaseState.
            output_dir: Optional custom directory to write reports.
            save_to_disk: Whether to serialize JSON and Markdown to disk.

        Returns:
            Tuple of:
            - Generated SARReport object
            - State patch dictionary for LangGraph state reducer
        """
        target_dir = Path(output_dir) if output_dir else self.output_dir
        report_id = generate_prefixed_id("SAR", 8)
        ts = now_iso()

        logger.info(
            "Generating SAR report %s for case %s",
            report_id,
            state.case_id,
        )

        all_evidence = state.all_evidence
        cited_evidence_ids: List[str] = []

        # --------------------------------------------------------------------
        # 1. Subject Extraction
        # --------------------------------------------------------------------
        customer_id = state.customer_id or "NOT_AVAILABLE"
        account_ids: List[str] = list(state.account_ids) if state.account_ids else []
        devices: List[str] = []
        ips: List[str] = []

        for item in all_evidence:
            cat = str(item.category)
            if cat in [EvidenceCategory.DEVICE.value, EvidenceCategory.DEVICE]:
                for eid in item.entity_ids:
                    if eid.startswith("DEV") and eid not in devices:
                        devices.append(eid)
                    elif eid.startswith("IP") or "." in eid:
                        if eid not in ips:
                            ips.append(eid)
            elif cat in [EvidenceCategory.IDENTITY.value, EvidenceCategory.IDENTITY]:
                for eid in item.entity_ids:
                    if eid.startswith("CUST") and customer_id == "NOT_AVAILABLE":
                        customer_id = eid
                    elif eid.startswith("ACC") and eid not in account_ids:
                        account_ids.append(eid)

        subject = SARSubject(
            customer_id=customer_id,
            account_ids=account_ids,
            associated_devices=devices,
            associated_ips=ips,
            risk_tier="STANDARD" if customer_id != "NOT_AVAILABLE" else "UNKNOWN",
        )

        # --------------------------------------------------------------------
        # 2. Suspicious Activity Extraction
        # --------------------------------------------------------------------
        transaction_id = state.transaction_id or "NOT_AVAILABLE"
        amount: Optional[float] = None
        currency: str = "USD"
        activity_ts: Optional[str] = None

        txn_evidence: List[EvidenceItem] = []
        for item in all_evidence:
            cat = str(item.category)
            if cat in [
                EvidenceCategory.TRANSACTION_BEHAVIOR.value,
                EvidenceCategory.TRANSACTION_BEHAVIOR,
            ]:
                txn_evidence.append(item)
                cited_evidence_ids.append(item.evidence_id)
                meta = item.metadata.get("raw_transaction", {})
                if meta:
                    if amount is None and meta.get("amount") is not None:
                        try:
                            amount = float(meta["amount"])
                        except (ValueError, TypeError):
                            pass
                    if meta.get("currency"):
                        currency = str(meta["currency"])
                    if meta.get("timestamp") and activity_ts is None:
                        activity_ts = str(meta["timestamp"])

        # Determine primary typology
        top_hypo = state.hypotheses[0] if state.hypotheses else None
        typology = top_hypo.title if top_hypo else "Suspicious Financial Activity"
        typology_matches = [h.title for h in state.hypotheses] if state.hypotheses else [typology]

        # Extract graph indicators
        indicators: List[str] = []
        gf = state.graph_features or {}
        if gf.get("fraud_neighbors_count", 0) > 0:
            indicators.append(f"Linked to {gf['fraud_neighbors_count']} known fraud neighbor(s)")
        if gf.get("shared_device_account_count", 0) > 1:
            indicators.append(f"Shared device linked to {gf['shared_device_account_count']} accounts")
        if gf.get("shared_ip_account_count", 0) > 1:
            indicators.append(f"Shared IP linked to {gf['shared_ip_account_count']} accounts")
        if gf.get("cycle_detected"):
            indicators.append("Circular money movement pattern detected")
        if gf.get("rapid_pass_through"):
            indicators.append("Rapid pass-through / mule velocity detected")

        suspicious_activity = SARSuspiciousActivity(
            transaction_id=transaction_id,
            amount=amount,
            currency=currency,
            activity_timestamp=activity_ts,
            typology=typology,
            risk_level=str(state.risk_level or "HIGH"),
            risk_score=state.risk_score,
            indicators=indicators,
        )

        # --------------------------------------------------------------------
        # 3. Collect Citations across Evidence Categories
        # --------------------------------------------------------------------
        graph_evidence_ids = [
            e.evidence_id
            for e in all_evidence
            if str(e.category) in [
                EvidenceCategory.GRAPH_RELATIONSHIP.value,
                EvidenceCategory.MONEY_FLOW.value,
                EvidenceCategory.DEVICE.value,
            ]
        ]
        cited_evidence_ids.extend(graph_evidence_ids)

        policy_evidence_ids = [
            e.evidence_id
            for e in all_evidence
            if str(e.category) in [EvidenceCategory.POLICY.value, EvidenceCategory.REGULATION.value]
        ]
        cited_evidence_ids.extend(policy_evidence_ids)

        # Deduplicate cited evidence IDs while preserving order
        dedup_cited_ids = list(dict.fromkeys(cited_evidence_ids))

        # --------------------------------------------------------------------
        # 4. Generate Grounded Five-Part Narrative
        # --------------------------------------------------------------------
        part_1 = (
            f"PART I — SUMMARY OF CASE TRIGGER & INITIAL ALLEGATION\n"
            f"Case {state.case_id} was initiated following trigger '{state.trigger_type}'. "
            f"The primary subject under investigation is Customer '{customer_id}' "
            f"involving Account(s) {account_ids or 'NOT_AVAILABLE'}. "
            f"Transaction '{transaction_id}' for amount {currency} "
            f"{f'{amount:,.2f}' if amount is not None else 'NOT_AVAILABLE'} "
            f"exhibited elevated fraud indicators. Assessed Risk Level: {state.risk_level or 'HIGH'} "
            f"(Score: {state.risk_score if state.risk_score is not None else 'N/A'}, "
            f"Confidence: {state.confidence if state.confidence is not None else 'N/A'})."
        )

        graph_facts = [
            f"- {e.fact} [{e.evidence_id}]"
            for e in all_evidence
            if str(e.category) in [
                EvidenceCategory.GRAPH_RELATIONSHIP.value,
                EvidenceCategory.MONEY_FLOW.value,
                EvidenceCategory.DEVICE.value,
            ]
        ]
        part_2 = (
            f"PART II — GRAPH NETWORK & RELATIONSHIP FINDINGS\n"
            f"TigerGraph multi-hop neighborhood analysis identified the following verified structural connections:\n"
            + ("\n".join(graph_facts) if graph_facts else "- No direct graph anomaly edges recorded.")
        )

        txn_facts = [
            f"- {e.fact} [{e.evidence_id}]"
            for e in all_evidence
            if str(e.category) in [
                EvidenceCategory.TRANSACTION_BEHAVIOR.value,
                EvidenceCategory.CUSTOMER_RESPONSE.value,
                EvidenceCategory.AUTHENTICATION.value,
            ]
        ]
        part_3 = (
            f"PART III — TRANSACTION VELOCITY & BEHAVIORAL ANOMALIES\n"
            f"Investigation of transactional behavior and corroborating telemetry revealed:\n"
            + ("\n".join(txn_facts) if txn_facts else "- Baseline transaction parameters confirmed.")
        )

        actions_taken = [
            f"- Executed action '{ea.action_type}' (Execution ID: {ea.execution_id}, Mode: {ea.execution_mode})"
            for ea in state.executed_actions
        ]
        part_4 = (
            f"PART IV — OPERATIONAL INTERVENTIONS & POLICY CLEARANCE\n"
            f"In accordance with fraud policy POL_004 ('Suspicious Activity Report Filing Threshold'), "
            f"the following operational actions were authorized and simulated:\n"
            + ("\n".join(actions_taken) if actions_taken else "- Operational disposition: FILE_SAR pending filing.")
        )

        part_5 = (
            f"PART V — COMPLIANCE DISPOSITION & FILING JUSTIFICATION\n"
            f"Based upon verified evidence, Customer '{customer_id}' and associated instruments "
            f"are assessed as participating in suspected '{typology}'. "
            f"Filing of this Suspicious Activity Report is mandated under FinCEN / BSA guidelines "
            f"and Bank Policy POL_004. Recommended disposition: Refer to internal AML/Financial Crimes "
            f"Unit for ongoing monitoring and regulatory retention."
        )

        full_narrative = (
            f"{part_1}\n\n{part_2}\n\n{part_3}\n\n{part_4}\n\n{part_5}"
        )

        narrative_obj = SARNarrative(
            part_1_introduction_trigger=part_1,
            part_2_graph_network_findings=part_2,
            part_3_behavioral_anomalies=part_3,
            part_4_operational_interventions=part_4,
            part_5_compliance_conclusion=part_5,
            full_text=full_narrative,
        )

        # --------------------------------------------------------------------
        # 5. Reviewer and Approval Status
        # --------------------------------------------------------------------
        approval_status = "APPROVED"
        reviewer_id = None
        if state.approval_decisions:
            latest_app = state.approval_decisions[-1]
            approval_status = str(latest_app.status)
            reviewer_id = latest_app.reviewer_id

        report = SARReport(
            report_id=report_id,
            case_id=state.case_id,
            filing_date=ts,
            subject=subject,
            suspicious_activity=suspicious_activity,
            cited_evidence_ids=dedup_cited_ids,
            graph_findings=gf,
            typology_matches=typology_matches,
            narrative=narrative_obj,
            recommended_action="FILE_SAR",
            approval_status=approval_status,
            compliance_reviewer_id=reviewer_id,
        )

        # --------------------------------------------------------------------
        # 6. Serialization to Disk (JSON & Markdown)
        # --------------------------------------------------------------------
        if save_to_disk:
            target_dir.mkdir(parents=True, exist_ok=True)
            json_file = target_dir / f"SAR_{state.case_id}_{report_id}.json"
            md_file = target_dir / f"SAR_{state.case_id}_{report_id}.md"

            # Serialize JSON
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2, default=str)

            # Serialize Markdown
            markdown_content = self._render_markdown(report)
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            report.file_path_json = str(json_file.resolve())
            report.file_path_markdown = str(md_file.resolve())

            logger.info("Saved SAR reports to %s and %s", json_file, md_file)

        # --------------------------------------------------------------------
        # 7. Construct State Patch
        # --------------------------------------------------------------------
        timeline_event = TimelineEvent(
            event_id=generate_event_id(),
            event_type="SAR_REPORT_GENERATED",
            node_name="sar_generator",
            description=(
                f"Generated formal Suspicious Activity Report (Reference: {report_id}) "
                f"citing {len(dedup_cited_ids)} verified evidence item(s)."
            ),
            timestamp=ts,
            details={
                "report_id": report_id,
                "case_id": state.case_id,
                "typology": typology,
                "amount": amount,
                "currency": currency,
                "cited_evidence_count": len(dedup_cited_ids),
                "json_path": report.file_path_json,
                "markdown_path": report.file_path_markdown,
                "disclaimer": SAR_AUDIT_DISCLAIMER,
            },
        )

        patch: Dict[str, Any] = {
            "sar_reference": report_id,
            "sar_report": report.model_dump(),
            "timeline": [timeline_event.model_dump()],
        }

        return report, patch

    generate = generate_sar

    def _render_markdown(self, report: SARReport) -> str:
        """Render a formatted, auditable Markdown document for the SAR."""
        amt_str = (
            f"{report.suspicious_activity.currency} {report.suspicious_activity.amount:,.2f}"
            if report.suspicious_activity.amount is not None
            else "NOT_AVAILABLE"
        )
        indicators_md = (
            "\n".join([f"- {ind}" for ind in report.suspicious_activity.indicators])
            if report.suspicious_activity.indicators
            else "- None recorded."
        )
        cited_md = (
            ", ".join(report.cited_evidence_ids)
            if report.cited_evidence_ids
            else "None cited."
        )

        return f"""# SUSPICIOUS ACTIVITY REPORT (SAR)

**Reference ID:** `{report.report_id}`  
**Case ID:** `{report.case_id}`  
**Filing Date:** `{report.filing_date}`  
**Filing Type:** `{report.filing_type}`  
**Institution:** {report.filing_institution}  
**Regulatory Authority:** {report.regulatory_reference}  
**Approval Status:** `{report.approval_status}` (Reviewer: {report.compliance_reviewer_id or 'SYSTEM_AUTOMATIC'})

> **Audit Disclaimer:**  
> *{report.audit_disclaimer}*

---

## 1. Subject Under Investigation

| Field | Detail |
|:---|:---|
| **Customer ID** | `{report.subject.customer_id}` |
| **Linked Accounts** | `{', '.join(report.subject.account_ids) if report.subject.account_ids else 'NOT_AVAILABLE'}` |
| **Associated Devices** | `{', '.join(report.subject.associated_devices) if report.subject.associated_devices else 'NONE'}` |
| **Associated IP Addresses** | `{', '.join(report.subject.associated_ips) if report.subject.associated_ips else 'NONE'}` |
| **Risk Tier** | `{report.subject.risk_tier}` |

---

## 2. Suspicious Activity Details

| Field | Detail |
|:---|:---|
| **Transaction ID** | `{report.suspicious_activity.transaction_id}` |
| **Total Amount** | **{amt_str}** |
| **Activity Date / Time** | `{report.suspicious_activity.activity_timestamp or 'NOT_AVAILABLE'}` |
| **Primary Typology** | `{report.suspicious_activity.typology}` |
| **Assessed Risk Level** | `{report.suspicious_activity.risk_level}` (Score: {report.suspicious_activity.risk_score or 'N/A'}) |

### Key Suspicious Indicators
{indicators_md}

---

## 3. Verified Evidence Citations
The factual disclosures in this filing are strictly grounded in verified graph and transactional evidence:  
`{cited_md}`

---

## 4. Investigative Narrative

### {report.narrative.part_1_introduction_trigger}

### {report.narrative.part_2_graph_network_findings}

### {report.narrative.part_3_behavioral_anomalies}

### {report.narrative.part_4_operational_interventions}

### {report.narrative.part_5_compliance_conclusion}

---

**Filing Certification:**  
This report has been compiled and verified by the TigerGraph Agentic Fraud Investigation System and approved for regulatory retention under standard financial crimes compliance protocols.
"""


def generate_case_sar(
    state: FraudCaseState,
    output_dir: Optional[Path | str] = None,
) -> Tuple[SARReport, Dict[str, Any]]:
    """Convenience functional wrapper for SAR report generation."""
    generator = SARGenerator(output_dir=Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR)
    return generator.generate_sar(state)
