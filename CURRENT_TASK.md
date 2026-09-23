# CURRENT_TASK.md — Active Implementation Task

## Current Active Layer
**Layer 12 — Graph Feature Engine**

## Objective
Implement the deterministic fraud feature calculation engine in `backend/app/features/engine.py` that computes typed `FraudFeatureSet` metrics (shared devices, shared IPs, fraud neighbors, shortest distance to fraud, connected cluster size, transaction velocity windows, amount deviation ratios, fan-in/fan-out, cycles, rapid pass-through) from normalized evidence and GSQL outputs without using an LLM.

## Acceptance Criteria
- [ ] Calculate deterministic graph relationship features (`shared_device_account_count`, `shared_device_customer_count`, `fraud_accounts_on_device`, `shared_ip_account_count`, `fraud_neighbors_count`, `shortest_distance_to_fraud`, `connected_component_size`).
- [ ] Calculate deterministic transaction behavior & velocity features (`transaction_count_5m`, `transaction_count_1h`, `transaction_count_24h`, `transaction_amount_ratio_to_mean`, `transaction_amount_ratio_to_median`, `new_device`, `new_ip`, `new_merchant`).
- [ ] Calculate deterministic money flow features (`fan_in_count`, `fan_out_count`, `cycle_detected`, `rapid_pass_through`).
- [ ] Preserve `None` / null when feature data is unavailable; never invent zero values or fabricate missing metrics.
- [ ] Produce human-readable feature explanations for every non-null feature.
- [ ] Unit tests in `tests/unit/test_feature_engine.py` pass with 100% success.

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
