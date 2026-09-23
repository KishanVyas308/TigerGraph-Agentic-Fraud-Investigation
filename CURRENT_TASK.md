# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 11 — Parallel Evidence Collection Node**

## Objective
Build the parallel evidence collection node in `backend/app/agents/nodes/evidence_collection.py` that concurrently executes independent baseline evidence branches using `asyncio.gather()`, passes results through `EvidenceNormalizer`, and returns a structured `FraudCaseState` update.

## Acceptance Criteria
- [ ] Concurrent execution of 5 baseline evidence branches:
  1. Branch A: GSQL Transaction Analysis (`get_transaction_context`, `get_transaction_behavior`)
  2. Branch B: GSQL Graph Relationship Analysis (`find_shared_devices`, `find_shared_ips`, `find_fraud_neighbors`, `get_shortest_path_to_fraud`, `detect_money_flow_patterns`)
  3. Branch C: GraphRAG Policy & Governance Retrieval (`retrieve_policy_context`)
  4. Branch D: GraphRAG Historical Case Precedent Retrieval (`retrieve_similar_cases`)
  5. Branch E: Device & Identity Analysis (`get_device_identity_context`)
  6. Branch F: Optional internal/external signal retrieval (mock/CRM/reputation)
- [ ] Fault-tolerant isolation per branch: failure of an optional source (e.g. policy retrieval or external signal) must not crash the entire node or erase graph evidence.
- [ ] Direct routing of tool outputs through `EvidenceNormalizer` into canonical `EvidenceItem` models.
- [ ] Return a state patch compatible with `merge_fraud_case_state`.
- [ ] Unit tests in `tests/unit/test_evidence_collection_node.py` pass with 100% success.

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
