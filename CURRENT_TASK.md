# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 10 — Evidence Model and Evidence Normalizer**

## Objective
Implement the Evidence Normalizer service in `backend/app/evidence/normalizer.py` to standardize heterogeneous tool outputs (GSQL queries, GraphRAG policy/case retrieval, device/identity context, customer/analyst input, external signals) into canonical `EvidenceItem` objects with auditable provenance.

## Acceptance Criteria
- [ ] Adapt GSQL transaction context and behavior query outputs to canonical `EvidenceItem` objects.
- [ ] Adapt GSQL graph relationship, shared device/IP, fraud neighbor, and money flow query outputs.
- [ ] Adapt GraphRAG policy, typology, and regulatory retrieval outputs without treating policy text as factual transaction facts.
- [ ] Adapt GraphRAG historical case retrieval outputs with clear precedent provenance labeling.
- [ ] Adapt mock customer responses, authentication results, and external signal outputs.
- [ ] Deduplicate equivalent evidence items deterministically by evidence ID or content hash.
- [ ] Preserve source provenance (`TIGERGRAPH_GSQL`, `POLICY_GRAPHRAG`, `CASE_MEMORY`, `CUSTOMER_RESPONSE`, `AUTHENTICATION_SERVICE`, etc.).
- [ ] Unit tests in `tests/unit/test_evidence_normalizer.py` pass with 100% success.

## Previous Completed Layers
- Layer 0 — Repository Bootstrap and Local Configuration
- Layer 1 — Dataset Inspection and Authoritative Schema Mapping
- Layer 2 — Data Preprocessing and Canonical Entity Tables
- Layer 3 — TigerGraph Graph Schema
- Layer 4 — TigerGraph Loading Jobs
- Layer 5 — Core GSQL Investigation Query Library
- Layer 6 — TigerGraph Client and MCP Integration
- Layer 7 — Policy, Typology, Regulation, and Historical Case Embeddings
- Layer 8 — GraphRAG Retrieval Service
- Layer 9 — Fraud Investigation State Models
