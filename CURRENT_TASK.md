# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 17 — Evidence Sufficiency Engine (Stage C — Reasoning + Control)**

## Objective
Implement the deterministic evidence sufficiency gate in `backend/app/agents/nodes/sufficiency_gate.py` that decides whether an investigation has enough evidence to take a defensible action or must request additional evidence.

## Acceptance Criteria
- [ ] Evaluate sufficiency using risk, confidence, evidence completeness, missing evidence list, action severity, policy constraints, and iteration count.
- [ ] Output one of 4 deterministic routing outcomes: `ACT`, `GATHER_MORE_EVIDENCE`, `ESCALATE`, or `STOP_NO_MATERIAL_FRAUD`.
- [ ] Prevent infinite loops by enforcing configurable maximum iteration bounds (`max_iterations`).
- [ ] Ensure decision rules are deterministic and configurable.
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
