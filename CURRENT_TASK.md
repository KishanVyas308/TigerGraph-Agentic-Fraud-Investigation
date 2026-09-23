# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 13 — Historical LightGBM Risk Signal (Stage B Optional Signal)**

## Objective
Implement optional historical ML risk scoring model in `backend/app/features/lightgbm_signal.py` that computes `historical_ml_score` (0.0 to 1.0) from deterministic graph features and transaction attributes as a supporting signal without being treated as final ground truth.

## Acceptance Criteria
- [ ] Implement LightGBM risk model wrapper with graceful fallback when LightGBM model weights are not loaded.
- [ ] Output `historical_ml_score` bounded between 0.0 and 1.0.
- [ ] Do NOT name the field `is_fraud` or treat it as final fraud probability unless calibrated.
- [ ] Fallback gracefully when LightGBM package or model artifact is missing or unavailable.
- [ ] Unit tests pass cleanly.

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
