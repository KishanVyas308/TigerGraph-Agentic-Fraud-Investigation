# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 16 — Main Fraud Reasoning Model (Stage C — Reasoning + Control)**

## Objective
Implement the main fraud reasoning agent node in `backend/app/agents/nodes/reasoning.py` that processes normalized evidence, graph features, risk signals, policy context, and historical cases through the `LLMRouter` (Groq `openai/gpt-oss-120b` with Gemini Flash fallback) to produce structured output (`hypotheses`, `risk_level`, `risk_score`, `confidence`, `evidence_completeness`, `missing_evidence`, `preliminary_next_best_action`, and `explanation`).

## Acceptance Criteria
- [ ] Ground all fraud reasoning strictly in normalized evidence and deterministic graph features (no fabricated facts).
- [ ] Output structured Pydantic `RiskAssessment` and competing `FraudHypothesis` objects.
- [ ] Keep `risk_level`, `confidence`, and `evidence_completeness` separate (do not collapse into one score).
- [ ] Require every material assertion to reference evidence IDs.
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
