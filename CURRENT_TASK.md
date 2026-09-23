# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 35 — Unit Test Suite (Stage E — Quality, Benchmark, and Demo)**

## Objective
Establish a comprehensive, consolidated, network-free unit test suite using `pytest` covering all core deterministic logic across the fraud investigation engine:
1. Evidence normalization and provenance verification.
2. Fraud graph feature engine calculations and boundary conditions.
3. Policy engine deterministic authorization, rules, prerequisites, and approval roles.
4. Evidence sufficiency gate decisions across risk, confidence, and completeness dimensions.
5. Evidence planner / Value of Information ranking and friction penalties.
6. State validation and transitions for `FraudCaseState`.
7. Action simulator and mock services.
8. LLM structured-output parsing, schema validation, and fallback routing logic.

## Acceptance Criteria
- [ ] Create/consolidate unit test modules under `tests/unit/` covering:
  - Evidence normalization (`test_evidence_normalizer.py`),
  - Graph features (`test_graph_feature_engine.py`),
  - Policy engine rules (`test_policy_engine.py`),
  - Sufficiency gate logic (`test_sufficiency_gate.py`),
  - Evidence planner ranking (`test_evidence_planner.py`),
  - State schemas & transitions (`test_fraud_state.py`),
  - Action simulation & mocks (`test_action_mocks.py`),
  - Router, provider parsing & fallback (`test_provider_router.py`).
- [ ] Strict mocking of TigerGraph and external LLM APIs (100% offline, zero network access required).
- [ ] Maintain clean execution and high test assertion coverage.

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
- Layer 19 — Deterministic Policy Engine
- Layer 20 — Human Approval State
- Layer 21 — Mock Evidence and Action Services
- Layer 22 — SAR / Report Generator
- Layer 23 — Case Finalizer and Stop Conditions
- Layer 24 — Case Memory Writer
- Layer 25 — Case Summary Embedding and Future Retrieval
- Layer 26 — Complete LangGraph Workflow
- Layer 27 — FastAPI Application Layer
- Layer 28 — Frontend Foundation
- Layer 29 — Live Investigation Timeline via SSE
- Layer 30 — Fraud Graph Visualization
- Layer 31 — Evidence and Assessment UI
- Layer 32 — Next-Best Action and Approval UI
- Layer 33 — Similar Cases and Policy UI
- Layer 34 — Local Audit Trail and Observability
