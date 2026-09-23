# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 19 — Deterministic Policy Engine (Stage C — Reasoning + Control)**

## Objective
Implement the Policy Engine in `backend/app/policy/engine.py` driven by `data/processed/policies.parquet` or `config/policy.yaml` to authorize next-best actions, determine approval requirements, roles, prerequisites, and SAR/report mandates. The policy engine must strictly govern all LLM recommendations.

## Acceptance Criteria
- [ ] Evaluate candidate actions against deterministic policies.
- [ ] Output authorization result: `allowed`, `autonomous`, `approval_required`, `approval_role`, `report_required`, `unmet_prerequisites`, `policy_reference`.
- [ ] Ensure LLM cannot bypass policy constraints.
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
- Layer 18 — Evidence Planner / Value of Information
