# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 40 — Demo Scenario Preparation (Stage E — Quality, Benchmark, and Demo) [COMPLETED]**

## All 41 Layers Completed
All layers from Layer 0 through Layer 40 across Stages A, B, C, D, and E are now fully implemented, tested, and verified.

## Objective
Prepare three deterministic, high-impact local demo scenarios showcasing the core capabilities of the system using the real LangGraph investigation workflow without demo-only branching or logic shortcuts:
1. **Demo 1 — Fraud Network**: Graph-detected fraud ring with shared devices, related accounts, prior fraud case link, graph path, and immediate high-risk action.
2. **Demo 2 — Uncertain Case**: Borderline transaction triggering evidence gathering, customer confirmation, and dynamic recommendation change.
3. **Demo 3 — Human Approval**: High-risk sensitive action triggering policy gate, analyst approval interrupt/resume, and final execution.

## Acceptance Criteria
- [x] Implement `backend/app/services/demo_runner.py`:
  - Demo orchestration service preparing fixtures and executing the 3 required demo scenarios through the unified LangGraph workflow.
  - Demo 1 (Fraud Network): Executes graph traversal, computes shared device and fraud-linked neighbors, identifies mule/ring topology, executes automated block.
  - Demo 2 (Uncertain Case): Triggers evidence loop, requests customer confirmation, ingests simulated customer response, verifies pre-evidence and post-evidence recommendations.
  - Demo 3 (Human Approval): Recommends governed sensitive action (e.g. `BLOCK_ACCOUNT`), enters `AWAITING_APPROVAL`, accepts simulated analyst approval, resumes execution to completion.
- [x] Implement `scripts/run_demo.py` CLI:
  - Command-line runner supporting `--scenario <1|2|3|ALL>`, `--step-by-step`, `--export-dir`.
  - Displays human-readable investigation narrative, graph facts, policy checks, approval gates, and timeline events.
- [x] Create `docs/demo_walkthrough.md`:
  - Concise analyst walkthrough script describing what to click in the dashboard, what evidence should appear, and expected system behavior.
- [x] Add unit test suite in `tests/unit/test_demo_scenarios.py`:
  - Unit tests verifying deterministic execution and state invariants for all 3 demo scenarios.

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
- Layer 35 — Unit Test Suite
- Layer 36 — Local Integration Tests
- Layer 37 — Benchmark Runner
- Layer 38 — Benchmark Output Validator
- Layer 39 — Evaluation Harness Using Historical Cases
