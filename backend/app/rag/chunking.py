"""Semantic document chunking for GraphRAG policies, typologies, regulations, and cases."""

from typing import Any, Dict, List, Optional
import polars as pl
from pydantic import BaseModel, Field

from backend.app.utils.logging import get_logger

logger = get_logger("rag.chunking")


class RAGChunk(BaseModel):
    """Semantic chunk with provenance tracking for GraphRAG."""
    chunk_id: str
    source_id: str
    section_title: str
    document_type: str  # POLICY, TYPOLOGY, REGULATION, HISTORICAL_CASE
    text: str
    graph_references: List[str] = Field(default_factory=list)


def chunk_policies(policies_df: pl.DataFrame) -> List[RAGChunk]:
    """Chunk bank fraud policies into grounded policy chunks."""
    chunks: List[RAGChunk] = []
    for row in policies_df.iter_rows(named=True):
        pid = row["policy_id"]
        title = row.get("title", f"Policy {pid}")
        cat = row.get("category", "GENERAL")
        content = row.get("content", "")
        action = row.get("action_required", "NO_ACTION")

        text = f"Policy [{pid}] {title} ({cat}): {content} Mandatory Action: {action}."
        chunks.append(RAGChunk(
            chunk_id=f"CHK_{pid}",
            source_id=pid,
            section_title=title,
            document_type="POLICY",
            text=text,
            graph_references=[action, cat],
        ))
    logger.info("Chunked %d bank policies", len(chunks))
    return chunks


def chunk_typologies(typologies_df: pl.DataFrame) -> List[RAGChunk]:
    """Chunk fraud typologies into descriptive indicator chunks."""
    chunks: List[RAGChunk] = []
    for row in typologies_df.iter_rows(named=True):
        tid = row["typology_id"]
        name = row.get("name", tid)
        desc = row.get("description", "")
        indicators = row.get("indicators", "")

        text = f"Fraud Typology [{tid}] {name}: {desc} Key Graph Indicators: {indicators}."
        chunks.append(RAGChunk(
            chunk_id=f"CHK_{tid}",
            source_id=tid,
            section_title=name,
            document_type="TYPOLOGY",
            text=text,
            graph_references=[name],
        ))
    logger.info("Chunked %d fraud typologies", len(chunks))
    return chunks


def chunk_regulatory_guidelines() -> List[RAGChunk]:
    """Chunk standard regulatory AML/fraud guidelines."""
    regulations = [
        {
            "reg_id": "REG_FINCEN_SAR",
            "title": "FinCEN Suspicious Activity Reporting (SAR) Mandate",
            "text": "Financial institutions must file a Suspicious Activity Report (SAR) with FinCEN within 30 days of initial detection of known or suspected insider abuse, or suspicious transactions involving $5,000 or more with no apparent lawful purpose.",
            "refs": ["FILE_SAR", "COMPLIANCE"],
        },
        {
            "reg_id": "REG_REG_E",
            "title": "Electronic Fund Transfer Act (Regulation E) Consumer Protection",
            "text": "Consumers are protected against unauthorized electronic fund transfers if reported within 60 days of transmittal. Banks must investigate customer fraud claims, provide provisional credit when required, and restrict compromised access devices.",
            "refs": ["CUSTOMER_DISPUTE", "BLOCK_CARD"],
        },
        {
            "reg_id": "REG_OFAC_SANCTIONS",
            "title": "OFAC Sanctions & Prohibited Counterparties Screening",
            "text": "Transactions involving sanctioned individuals, entities, or designated high-risk jurisdictions must be blocked immediately and reported to OFAC within 10 business days.",
            "refs": ["BLOCK_TRANSACTION", "SANCTIONS"],
        },
    ]

    chunks: List[RAGChunk] = []
    for reg in regulations:
        chunks.append(RAGChunk(
            chunk_id=f"CHK_{reg['reg_id']}",
            source_id=reg["reg_id"],
            section_title=reg["title"],
            document_type="REGULATION",
            text=f"Regulation [{reg['reg_id']}] {reg['title']}: {reg['text']}",
            graph_references=reg["refs"],
        ))
    logger.info("Chunked %d regulatory guidelines", len(chunks))
    return chunks


def chunk_historical_cases(hist_df: pl.DataFrame) -> List[RAGChunk]:
    """Chunk historical resolved cases into precedent memory chunks."""
    chunks: List[RAGChunk] = []
    for row in hist_df.iter_rows(named=True):
        cid = row["case_id"]
        # Ensure benchmark cases are never included
        if cid.startswith("CASE_"):
            continue

        outcome = row.get("outcome", "INCONCLUSIVE")
        typology = row.get("primary_typology", "GENERAL")
        summary = row.get("summary", "")

        text = f"Precedent Case [{cid}] Outcome: {outcome}. Typology: {typology}. Findings: {summary}"
        chunks.append(RAGChunk(
            chunk_id=f"CHK_{cid}",
            source_id=cid,
            section_title=f"Case Precedent {cid}",
            document_type="HISTORICAL_CASE",
            text=text,
            graph_references=[outcome, typology],
        ))
    logger.info("Chunked %d historical case precedents", len(chunks))
    return chunks
