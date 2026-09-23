# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 21 — Mock Evidence and Action Services (Stage C — Reasoning + Control)**

## Objective
Implement simulated action execution services (`execution_mode = SIMULATED`) for allowed banking actions (transaction allow/block, account freeze/block, customer warnings/SMS confirmation, step-up 2FA biometrics, escalation, CRM updates). Ensure all simulated executions produce explicit mock audit records without implying changes to real banking systems.

## Acceptance Criteria
- [ ] Implement simulated mock services for all permitted hackathon actions.
- [ ] Explicitly tag all mock execution results with `execution_mode = SIMULATED`.
- [ ] Ingest simulated evidence responses into `state.received_evidence` upon customer confirmation or step-up authentication.
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
- Layer 19 — Deterministic Policy Engine
- Layer 20 — Human Approval State
