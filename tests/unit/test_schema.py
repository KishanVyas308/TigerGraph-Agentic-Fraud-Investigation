"""Unit tests for TigerGraph GSQL graph schema definition."""

from pathlib import Path
import re
import pytest

SCHEMA_PATH = Path("gsql/schema/fraud_schema.gsql")


def test_schema_file_exists():
    """Verify that the GSQL schema file exists and is non-empty."""
    assert SCHEMA_PATH.exists()
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "CREATE GRAPH FraudInvestigationGraph" in content


def test_required_vertex_types_exist():
    """Verify all domain and case-memory vertex types are defined."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    expected_vertices = [
        "Customer",
        "Account",
        "Transaction",
        "Device",
        "IPAddress",
        "Merchant",
        "FraudCase",
        "Evidence",
        "Decision",
        "Action",
        "Approval",
        "Policy",
        "Typology",
    ]
    for vertex in expected_vertices:
        pattern = rf"CREATE\s+VERTEX\s+{vertex}\s*\("
        assert re.search(pattern, content) is not None, f"Missing vertex definition: {vertex}"


def test_required_edge_types_exist():
    """Verify all critical relationship and audit edge types are defined."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    expected_edges = [
        "CUSTOMER_OWNS_ACCOUNT",
        "ACCOUNT_PERFORMED_TRANSACTION",
        "TRANSACTION_TO_MERCHANT",
        "TRANSACTION_TO_ACCOUNT",
        "TRANSACTION_USED_DEVICE",
        "TRANSACTION_CONNECTED_IP",
        "CASE_INVESTIGATES_TRANSACTION",
        "CASE_INVESTIGATES_ACCOUNT",
        "CASE_INVESTIGATES_DEVICE",
        "CASE_HAS_EVIDENCE",
        "CASE_HAS_DECISION",
        "CASE_HAS_ACTION",
        "CASE_HAS_APPROVAL",
        "CASE_MATCHES_TYPOLOGY",
        "CASE_CITES_POLICY",
        "EVIDENCE_LINKED_TRANSACTION",
        "EVIDENCE_LINKED_ACCOUNT",
        "EVIDENCE_LINKED_DEVICE",
        "EVIDENCE_LINKED_IP",
    ]
    for edge in expected_edges:
        assert edge in content, f"Missing edge definition: {edge}"


def test_no_is_fraud_on_transaction():
    """Verify compliance with AGENTS.md: No is_fraud flag on Transaction vertex."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    tx_match = re.search(r"CREATE\s+VERTEX\s+Transaction\s*\((.*?)\)", content, re.DOTALL)
    assert tx_match is not None
    tx_body = tx_match.group(1).lower()

    assert "is_fraud" not in tx_body
    assert "fraud_label" not in tx_body
    assert "ground_truth" not in tx_body
    # Bank risk score MUST be present
    assert "bank_risk_score double" in tx_body


def test_directed_edges_correctness():
    """Verify directed financial flow edges are correctly defined."""
    content = SCHEMA_PATH.read_text(encoding="utf-8")
    assert "CREATE DIRECTED EDGE ACCOUNT_PERFORMED_TRANSACTION (FROM Account, TO Transaction)" in content
    assert "CREATE DIRECTED EDGE TRANSACTION_TO_MERCHANT (FROM Transaction, TO Merchant)" in content
    assert "CREATE DIRECTED EDGE TRANSACTION_TO_ACCOUNT (FROM Transaction, TO Account)" in content
