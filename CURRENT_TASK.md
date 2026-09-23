# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 14 — Laya Fast Classifier (Stage B Optional Signal)**

## Objective
Implement optional Laya local classifier wrapper in `backend/app/models/laya_classifier.py` for lightweight local routing/classification (trigger classification, customer response classification, analyst response classification) with feature flag control and deterministic fallback.

## Acceptance Criteria
- [ ] Implement fast classification wrapper supporting trigger classification, customer response, and analyst response.
- [ ] Strictly restrict Laya from making final fraud decisions, deciding account blocking, or voting over evidence items.
- [ ] Feature-flagged control (`ENABLE_LAYA: bool = False`) with graceful fallback to deterministic parsing or main LLM when disabled or unconfident.
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
