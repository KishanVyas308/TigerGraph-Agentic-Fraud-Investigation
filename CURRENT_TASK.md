# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 15 — LLM Provider Router (Stage C — Reasoning + Control)**

## Objective
Implement LLM provider routing and fallback service in `backend/app/llm/router.py` supporting primary Groq models (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`) with automatic fallback to Gemini Flash (`gemini-1.5-flash` / `gemini-2.0-flash`) and structured JSON output schema validation.

## Acceptance Criteria
- [ ] Implement `LLMRouter` with primary Groq integration and Gemini Flash fallback.
- [ ] Support primary model (`openai/gpt-oss-120b`) and fast model (`openai/gpt-oss-20b`).
- [ ] Handle provider failure, rate limits, timeouts, and API errors with automatic failover to Gemini Flash.
- [ ] Enforce structured JSON / Pydantic schema generation with repair / retry logic.
- [ ] Unit tests in `tests/unit/test_llm_router.py` pass with 100% success.

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
