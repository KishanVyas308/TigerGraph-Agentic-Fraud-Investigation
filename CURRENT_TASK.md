# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 18 — Evidence Planner / Value of Information (Stage C — Reasoning + Control)**

## Objective
Implement the Evidence Planner service in `backend/app/agents/nodes/evidence_planner.py` that selects the smallest, highest-value evidence request (`CUSTOMER_CONFIRMATION`, `STEP_UP_AUTH`, `ANALYST_INFORMATION`, `APPROVED_EXTERNAL_CHECK`) using an explainable Value of Information (VoI) approximation: `(expected uncertainty reduction * expected decision impact) / cost_friction`.

## Acceptance Criteria
- [ ] Select the highest-value missing evidence item from `state.missing_evidence`.
- [ ] Before requesting additional evidence, preserve the current recommendation as `state.pre_evidence_next_best_action`.
- [ ] Record why evidence is insufficient, what evidence is being requested, and what decision the evidence could change.
- [ ] Support typed evidence requests (`CUSTOMER_CONFIRMATION`, `STEP_UP_AUTH`, `ANALYST_INFORMATION`, `APPROVED_EXTERNAL_CHECK`).
- [ ] Unit tests pass with 100% success.

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
- Layer 10 — Evidence Model and Evidence Normalizer
- Layer 11 — Parallel Evidence Collection Node
- Layer 12 — Graph Feature Engine
- Layer 13 — Historical LightGBM Risk Signal
- Layer 14 — Laya Fast Classifier
- Layer 15 — LLM Provider Router
- Layer 16 — Main Fraud Reasoning Model
- Layer 17 — Evidence Sufficiency Engine
