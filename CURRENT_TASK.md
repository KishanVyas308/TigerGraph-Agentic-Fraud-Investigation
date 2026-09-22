# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 9 — Fraud Investigation State Models**

## Objective
Define all Pydantic v2 typed state models, enums, timeline events, and state reducer/merge semantics in `backend/app/models/state.py` for LangGraph orchestration before building graph nodes.

## Acceptance Criteria
- [ ] Enums for `TriggerType`, `RiskLevel`, `EvidenceCategory`, `EvidenceReliability`, `ActionType`, `ApprovalStatus`, `ApprovalRole`, `StopReason`, `CaseStatus`
- [ ] Sub-models: `EvidenceItem`, `FraudHypothesis`, `RiskAssessment`, `EvidenceRequest`, `NextBestAction`, `ApprovalDecision`, `ActionExecution`, `TimelineEvent`
- [ ] Main model: `FraudCaseState` with all 6 categories (Identity, Evidence, Features, Reasoning Output, Actions, Case Control)
- [ ] State reducer / merge utility for LangGraph node returns
- [ ] Strict Pydantic v2 validation (e.g., separate risk, confidence, and completeness; evidence ID format; JSON serialization)
- [ ] Unit tests in `tests/unit/test_state_models.py` pass with 100% success

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
