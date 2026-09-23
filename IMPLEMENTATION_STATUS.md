# IMPLEMENTATION_STATUS.md — Project Progress Tracker

## Project

**TigerGraph Agentic Fraud Investigation Agent — HHGOA**

## Overall Status

**Status:** In Progress  
**Completed Layers:** 34 / 41  
**Current Stage:** Stage E — Quality, Benchmark, and Demo  
**Current Active Layer:** Layer 35 — Unit Test Suite  
**Last Completed Layer:** Layer 34 — Local Audit Trail and Observability  
**Current Blockers:** None

> Update this file after every completed implementation layer.  
> Do not mark a layer complete until its acceptance criteria and relevant tests pass.

---

# Stage A — Data + Graph Foundation

- [x] Layer 0 — Repository Bootstrap and Local Configuration
- [x] Layer 1 — Dataset Inspection and Authoritative Schema Mapping
- [x] Layer 2 — Data Preprocessing and Canonical Entity Tables
- [x] Layer 3 — TigerGraph Graph Schema
- [x] Layer 4 — TigerGraph Loading Jobs
- [x] Layer 5 — Core GSQL Investigation Query Library
- [x] Layer 6 — TigerGraph Client and MCP Integration

## Stage A Exit Criteria

Stage A is complete when:

- repository structure is stable,
- dataset fields are documented,
- preprocessing is reproducible,
- TigerGraph schema reflects real dataset entities,
- data loads successfully,
- installed GSQL queries return meaningful fraud evidence,
- backend accesses TigerGraph through one controlled client layer.

---

# Stage B — Retrieval + Evidence

- [x] Layer 7 — Policy, Typology, Regulation, and Historical Case Embeddings
- [x] Layer 8 — GraphRAG Retrieval Service
- [x] Layer 9 — Fraud Investigation State Models
- [x] Layer 10 — Evidence Model and Evidence Normalizer
- [x] Layer 11 — Parallel Evidence Collection Node
- [x] Layer 12 — Graph Feature Engine

## Optional Enhancements

- [x] Layer 13 — Historical LightGBM Risk Signal
- [x] Layer 14 — Laya Fast Classifier

## Stage B Exit Criteria

Stage B is complete when one investigation can produce a normalized evidence bundle containing:

- transaction behavior,
- graph relationships,
- device/identity evidence,
- relevant policy,
- relevant typology/regulation,
- similar historical cases,
- deterministic graph features.

---

# Stage C — Reasoning + Control

- [x] Layer 15 — LLM Provider Router
- [x] Layer 16 — Main Fraud Reasoning Model
- [x] Layer 17 — Evidence Sufficiency Engine
- [x] Layer 18 — Evidence Planner / Value of Information
- [x] Layer 19 — Deterministic Policy Engine
- [x] Layer 20 — Human Approval State
- [x] Layer 21 — Mock Evidence and Action Services
- [x] Layer 22 — SAR / Report Generator
- [x] Layer 23 — Case Finalizer and Stop Conditions
- [x] Layer 24 — Case Memory Writer
- [x] Layer 25 — Case Summary Embedding and Future Retrieval
- [x] Layer 26 — Complete LangGraph Workflow

## Stage C Exit Criteria

Stage C is complete when a case can locally move through:

```text
Trigger
→ Evidence
→ Risk Assessment
→ Uncertainty Check
→ Additional Evidence if Needed
→ Updated Assessment
→ Next-Best Action
→ Policy Check
→ Human Approval if Required
→ Simulated Action
→ Finalization
→ TigerGraph Case Memory
```

The same workflow must support both fraud and cleared cases.

---

# Stage D — API + Analyst UI

- [x] Layer 27 — FastAPI Application Layer
- [x] Layer 28 — Frontend Foundation
- [x] Layer 29 — Live Investigation Timeline via SSE
- [x] Layer 30 — Fraud Graph Visualization
- [x] Layer 31 — Evidence and Assessment UI
- [x] Layer 32 — Next-Best Action and Approval UI
- [x] Layer 33 — Similar Cases and Policy UI
- [x] Layer 34 — Local Audit Trail and Observability

## Stage D Exit Criteria

Stage D is complete when an analyst can locally:

- start an investigation,
- watch progress through SSE,
- inspect the graph,
- inspect evidence,
- see risk/confidence/evidence completeness,
- view fraud hypotheses,
- inspect similar cases,
- view policy basis,
- approve/reject/modify sensitive actions,
- see the final case outcome.

---

# Stage E — Quality, Benchmark, and Demo

- [ ] Layer 35 — Unit Test Suite
- [ ] Layer 36 — Local Integration Tests
- [ ] Layer 37 — Benchmark Runner
- [ ] Layer 38 — Benchmark Output Validator
- [ ] Layer 39 — Evaluation Harness Using Historical Cases
- [ ] Layer 40 — Demo Scenario Preparation

## Stage E Exit Criteria

Stage E is complete when:

- deterministic components are unit tested,
- major workflow branches pass integration tests,
- all 20 benchmark cases use the same workflow,
- benchmark outputs pass format validation,
- historical evaluation runs without benchmark leakage,
- local demo scenarios work deterministically.

---

# Current Layer Details

## Active Layer

**Layer 35 — Unit Test Suite**

## Goal

Establish a comprehensive, consolidated, network-free unit test suite using `pytest` covering all core deterministic logic across the fraud investigation engine: evidence normalization, graph features, policy authorization, sufficiency decisions, evidence planner (Value of Information), state schemas, action mocks, and provider router / parsing logic.

## Required Deliverables

- `tests/unit/test_evidence_normalizer.py`
- `tests/unit/test_graph_feature_engine.py`
- `tests/unit/test_policy_engine.py`
- `tests/unit/test_sufficiency_gate.py`
- `tests/unit/test_evidence_planner.py`
- `tests/unit/test_fraud_state.py`
- `tests/unit/test_action_mocks.py`
- `tests/unit/test_provider_router.py`

## Completion Criteria

Layer 35 can be marked complete only when:

- all deterministic components are independently unit-tested,
- TigerGraph and external LLM APIs are strictly mocked,
- tests run 100% offline with zero external network access,
- high assertion coverage is achieved across edge cases and error states.

---

# Recent Work Log

- **Layer 0 Completed**:
  - Initialized repository layout matching architecture specifications.
  - Configured Python 3.11 environment with `uv`, FastAPI, Pydantic v2, Polars, DuckDB, and pytest.
  - Implemented `.env.example`, `.gitignore`, typed `Settings` in `backend/app/config.py`, UTC timestamp helpers in `backend/app/utils/time.py`, ID generators in `backend/app/utils/ids.py`, and structured logging in `backend/app/utils/logging.py`.
  - Implemented FastAPI entry point in `backend/app/main.py` with `/health` and root endpoints.
  - Implemented Next.js TypeScript frontend skeleton, configured `tsconfig.json`, Tailwind CSS, and verified type checking with 0 errors.
  - Added unit test suite in `tests/unit/` covering configuration, utilities, and FastAPI endpoints (all passed).

- **Layer 1 Completed**:
  - Implemented dataset inspection utility `scripts/inspect_dataset.py` capable of analyzing tabular files (CSV, Parquet) and documents (Markdown, text, JSON) using Polars and DuckDB.
  - Produced initial `data/processed/data_dictionary.json`.
  - Documented authoritative entity mappings, identifier rules, and benchmark leak prevention constraints in `docs/dataset_mapping.md`.
  - Added unit test suite `tests/unit/test_inspect_dataset.py` verifying dataset inspection and schema cataloging (all passed).

- **Layer 2 Completed**:
  - Implemented modular preprocessing pipeline in `scripts/preprocess_dataset.py` using Polars and DuckDB.
  - Generated all 10 canonical Parquet tables in `data/processed/` (`customers.parquet`, `accounts.parquet`, `devices.parquet`, `ip_addresses.parquet`, `merchants.parquet`, `transactions.parquet`, `historical_cases.parquet`, `policies.parquet`, `typologies.parquet`, `benchmark_cases.parquet`).
  - Implemented strict referential integrity validation across foreign keys and primary keys.
  - Strictly isolated the 20 benchmark case triggers without cheat labels or ground-truth leakage.
  - Generated `data/processed/preprocessing_report.json` with status "passed".
  - Added unit test suite `tests/unit/test_preprocessing.py` (all passed).

- **Layer 3 Completed**:
  - Authored comprehensive GSQL schema in `gsql/schema/fraud_schema.gsql` with 13 vertex types and 19 edge types.
  - Accurately modeled domain financial entities (`Customer`, `Account`, `Transaction`, `Device`, `IPAddress`, `Merchant`) and case memory/audit entities (`FraudCase`, `Evidence`, `Decision`, `Action`, `Approval`, `Policy`, `Typology`).
  - Documented edge directionality semantics, multi-hop traversal design, and indexing in `docs/graph_schema.md`.
  - Adhered strictly to benchmark and ground truth safety (no `is_fraud` on `Transaction`).
  - Added unit test suite `tests/unit/test_schema.py` (all passed).

- **Layer 4 Completed**:
  - Created GSQL core data loading job in `gsql/loading/load_core_data.gsql`.
  - Created GSQL case and policy loading job in `gsql/loading/load_cases.gsql`.
  - Built Python graph loader driver in `scripts/load_tigergraph.py` with CSV staging, connection validation, count checks, and dry-run execution mode.
  - Added unit tests in `tests/unit/test_loading.py` and integration tests in `tests/integration/test_graph_load.py` (all 27 tests passed).

- **Layer 5 Completed**:
  - Implemented all 13 core GSQL queries in `gsql/queries/`: `get_transaction_context`, `get_transaction_behavior`, `get_entity_neighborhood`, `find_shared_devices`, `find_shared_ips`, `find_fraud_neighbors`, `get_shortest_path_to_fraud`, `detect_money_flow_patterns`, `get_connected_cluster`, `get_device_identity_context`, `find_similar_graph_cases`, `get_case_timeline`, and `write_case_update`.
  - Built typed Pydantic wrapper models and query execution service in `backend/app/graph/queries.py` with dual online/offline execution capability.
  - Added unit tests in `tests/unit/test_queries.py` (all 36 tests passed).

- **Layer 6 Completed**:
  - Built unified access layer in `backend/app/graph/tigergraph_client.py` centralizing all graph operations with retry logic, timeout handling, and offline simulation fallback.
  - Built `TigerGraphMCPAdapter` in `backend/app/graph/mcp_client.py` exposing 13 approved tools with JSON-schema contracts and strict read/write segregation.
  - Added unit tests in `tests/unit/test_tigergraph_client.py` (all 44 tests passed across the repository).
  - Completed all Stage A exit criteria.

- **Layer 7 Completed**:
  - Built GraphRAG chunking pipeline and local SentenceTransformers embedding engine in `backend/app/rag/embeddings.py`, `backend/app/rag/chunking.py`, `backend/app/rag/policy_index.py`, `backend/app/rag/case_memory.py`, and `scripts/build_embeddings.py`.
  - Built unit tests in `tests/unit/test_rag_embeddings.py` (all passed).

- **Layer 8 Completed**:
  - Built GraphRAG retrieval service in `backend/app/rag/retrieval.py` supporting grounded policy context retrieval and hybrid precedent retrieval.
  - Enforced strict benchmark case isolation preventing benchmark cases from being returned as precedents.
  - Added unit tests in `tests/unit/test_retrieval.py` (all passed).

- **Layer 9 Completed**:
  - Implemented Pydantic v2 typed state models, domain enums, timeline events, and state reducer/merge semantics in `backend/app/models/state.py` and `backend/app/models/__init__.py`.
  - Modeled `FraudCaseState` with all 6 categories (Identity, Evidence, Features, Reasoning Output, Actions, Case Control).
  - Implemented `merge_fraud_case_state` reducer for LangGraph node returns with list deduplication, categorical routing, and pre/post evidence recommendation preservation.
  - Added unit test suite `tests/unit/test_state_models.py` (all 9 tests passed).

- **Layer 10 Completed**:
  - Implemented `EvidenceNormalizer` in `backend/app/evidence/normalizer.py` and `backend/app/evidence/__init__.py`.
  - Added adapters for GSQL transaction context/behavior, shared devices/IPs, fraud neighbors, shortest paths, money flows, and device identity context.
  - Added GraphRAG policy, typology, regulatory, and case precedent adapters preserving strict provenance (`TIGERGRAPH_GSQL`, `POLICY_GRAPHRAG`, `CASE_MEMORY`, `CUSTOMER_RESPONSE`, `AUTHENTICATION_SERVICE`, `ANALYST_INPUT`, `EXTERNAL_SIGNAL`).
  - Built bundle normalization and deterministic deduplication.
  - Added unit test suite `tests/unit/test_evidence_normalizer.py` (all 9 tests passed).

- [x] Layer 11 — Parallel Evidence Collection Node
- [x] Layer 12 — Graph Feature Engine
- [x] Layer 13 — Historical LightGBM Risk Signal
- [x] Layer 14 — Laya Fast Classifier
- [x] Layer 15 — LLM Provider Router
- [x] Layer 16 — Main Fraud Reasoning Model
- [x] Layer 17 — Evidence Sufficiency Engine
- [x] Layer 18 — Evidence Planner / Value of Information
- [x] Layer 19 — Deterministic Policy Engine
- [x] Layer 20 — Human Approval State

- **Layer 18 Completed**:
  - Implemented `EvidencePlannerNode` in `backend/app/agents/nodes/evidence_planner.py` and `backend/app/agents/nodes/__init__.py`.
  - Calculated explainable Value of Information (VoI) score: `(uncertainty_reduction * decision_impact) / (cost_friction + 0.1)`.
  - Supported typed evidence requests (`CUSTOMER_CONFIRMATION`, `STEP_UP_AUTH`, `ANALYST_INFORMATION`, `APPROVED_EXTERNAL_CHECK`).
  - Preserved pre-evidence next-best action (`pre_evidence_next_best_action`) and set `case_status = AWAITING_EVIDENCE`.
  - Added unit test suite `tests/unit/test_evidence_planner.py` (all passed).

- **Layer 19 Completed**:
  - Created `backend/app/policies/policy.yaml` and `config/policy.yaml` containing policy rules for all 13 `ActionType` options.
  - Implemented policy loader in `backend/app/policies/loader.py` and deterministic `PolicyEngine` in `backend/app/policies/engine.py`.
  - Implemented `PolicyGateNode` in `backend/app/agents/nodes/policy_gate.py` enforcing strict authorization boundaries over LLM recommendations.
  - Determined `allowed`, `autonomous`, `approval_required`, `approval_role`, `report_required`, `unmet_prerequisites`, and `policy_reference`.
  - Returned safe authorized fallbacks when recommendations violate risk bounds or lack required entity prerequisites.
  - Added unit test suite `tests/unit/test_policy_engine.py` (all 7 tests passed).

- **Layer 20 Completed**:
  - Implemented `ApprovalRequest` model and `process_analyst_decision` function in `backend/app/actions/approval.py`.
  - Supported analyst decision outcomes: `APPROVE`, `REJECT`, and `MODIFY`.
  - Implemented `HumanApprovalNode` in `backend/app/agents/nodes/human_approval.py` for LangGraph pause/resume transitions.
  - Re-evaluated modified actions through `PolicyEngine` upon `MODIFY` decisions, and selected safe monitoring fallbacks on `REJECT`.
  - Preserved reviewer ID, role, comments, and decision outcomes in case timeline history.
  - Added unit test suite `tests/unit/test_human_approval.py` (all 5 tests passed).

- **Layer 21 Completed**:
  - Implemented base action execution interface and typed `SimulatedActionResult` in `backend/app/actions/base.py`.
  - Implemented mock evidence services in `backend/app/actions/mocks.py`: `MockCustomerConfirmationService` (SMS/Push authorization), `MockStepUpAuthService` (biometric/OTP challenges), `MockAnalystEvidenceService` (supplemental notes), and `MockExternalReputationService` (IP/threat intelligence).
  - Implemented `MockActionExecutionService` covering all 13 `ActionType` operations (`ALLOW_TRANSACTION`, `BLOCK_TRANSACTION`, `MONITOR_TRANSACTION`, `MONITOR_ACCOUNT`, `BLOCK_ACCOUNT`, `WARN_CUSTOMER`, `REQUEST_CUSTOMER_CONFIRMATION`, `REQUEST_STEP_UP_AUTH`, `REQUEST_ANALYST_EVIDENCE`, `ESCALATE_ANALYST`, `FILE_SAR`, `CLOSE_CASE`, `NO_ACTION`).
  - Enforced `execution_mode = SIMULATED` and included simulation audit disclaimers across all simulated actions.
  - Implemented `ingest_mock_evidence` helper normalizing and appending evidence to `received_evidence` while transitioning `case_status` from `AWAITING_EVIDENCE` to `IN_PROGRESS`.
  - Implemented LangGraph `ActionExecutorNode` in `backend/app/agents/nodes/action_executor.py` managing deferred approvals, autonomous execution, and case lifecycle transitions.
  - Added unit test suite `tests/unit/test_mock_actions.py` (all 16 tests passing).

- **Layer 22 Completed**:
  - Added `sar_reference` and `sar_report` fields to `FraudCaseState` and updated `merge_fraud_case_state` reducer in `backend/app/models/state.py`.
  - Implemented typed Pydantic models `SARSubject`, `SARSuspiciousActivity`, `SARNarrative`, and `SARReport` in `backend/app/reporting/sar_generator.py`.
  - Implemented `SARGenerator` and `generate_case_sar` producing verified evidence-grounded reports with a structured 5-part narrative citing specific `[evidence_id]` tokens.
  - Prevented hallucination by representing missing fields strictly as `NOT_AVAILABLE` or null.
  - Implemented disk export generating formatted JSON (`.json`) and Markdown (`.md`) reports under `outputs/sar/` with safety simulation disclaimers.
  - Appended auditable `SAR_REPORT_GENERATED` timeline milestones and linked `sar_reference` into case memory.
  - Added unit test suite `tests/unit/test_sar_generator.py` (all tests passing).

- **Layer 23 Completed**:
  - Added `case_summary` and `final_summary` fields to `FraudCaseState` and updated `merge_fraud_case_state` reducer in `backend/app/models/state.py`.
  - Implemented `ValidationResult` and `FinalCaseSummary` schemas in `backend/app/schemas/case.py` and exported them in `backend/app/schemas/__init__.py`.
  - Implemented `CaseFinalizer` service in `backend/app/services/finalizer.py` enforcing explicit `StopReason` resolution, integrity validation, and synthesis of human-auditable case summaries.
  - Implemented `FinalizerNode` in `backend/app/agents/nodes/finalizer.py` coordinating case completion within the LangGraph lifecycle.
  - Ensured no case terminates silently without an explicit stop reason and properly preserved pre/post evidence recommendations.
  - Added unit test suite `tests/unit/test_case_finalizer.py` (all tests passing).

- **Layer 24 Completed**:
  - Added `is_persisted` and `case_memory_id` fields to `FraudCaseState` and updated `merge_fraud_case_state` reducer in `backend/app/models/state.py`.
  - Implemented `CaseMemoryReceipt` schema and `CaseMemoryWriter` service in `backend/app/services/case_memory_writer.py`.
  - Persisted `FraudCase`, `Evidence`, `Decision` (strictly preserving pre-evidence and post-evidence recommendations without overwriting), `Action`, `Approval`, and entity linkages (`Transaction`, `Account`, `Device`, `IPAddress`) into TigerGraph graph memory.
  - Added LangGraph `MemoryWriterNode` in `backend/app/agents/nodes/memory_writer.py` and exported in `backend/app/agents/nodes/__init__.py`.
  - Added unit test suite `tests/unit/test_case_memory_writer.py` (all tests passing).

- **Layer 25 Completed**:
  - Added `is_indexed` and `embedding_id` fields to `FraudCaseState` and updated `merge_fraud_case_state` reducer in `backend/app/models/state.py`.
  - Implemented `is_benchmark_case` helper quarantining benchmark cases (`CASE_001` to `CASE_020`) from leaking into precedent memory in `backend/app/rag/case_memory.py`.
  - Extended `CaseMemoryIndex` with `records`, `get_record`, and `upsert_record` methods.
  - Implemented `CaseIndexingReceipt` and `CaseMemoryIndexer` service in `backend/app/rag/case_indexer.py` generating grounded case summaries, computing 384-dimensional SentenceTransformer embeddings, and persisting to `case_memory_index.parquet`.
  - Updated `GraphRAGRetrievalService` in `backend/app/rag/retrieval.py` with `reload_case_memory` and isolated benchmark case filtering to enable dynamic precedent retrieval of newly indexed cases.
  - Implemented LangGraph `CaseSummaryEmbedderNode` in `backend/app/agents/nodes/case_indexer.py` and exported in `backend/app/agents/nodes/__init__.py`.
  - Added unit test suite `tests/unit/test_case_indexer.py` (all 7 tests covering summary synthesis, embedding computation, Parquet persistence, quarantine, dynamic retrieval, async node processing, and reducer merge).

- **Layer 26 Completed (Stage C Milestone Complete)**:
  - Implemented intake nodes in `backend/app/agents/nodes/intake.py`: `ValidateTriggerNode`, `LoadOrCreateCaseNode`, `TriggerClassifierNode`, `PersistCaseStartNode`.
  - Implemented evidence loop and action resolution nodes in `backend/app/agents/nodes/evidence_loop.py`: `RecordPreEvidenceNBANode`, `RequestEvidenceNode`, `IngestEvidenceNode`, `DetermineNextBestActionNode`, `ReportIfRequiredNode`.
  - Exported all intake and loop nodes in `backend/app/agents/nodes/__init__.py`.
  - Implemented `InvestigationWorkflowBuilder` and `CompiledInvestigationWorkflow` state machine in `backend/app/agents/graph.py` with conditional routing (`route_sufficiency_gate`, `route_policy_gate`), bounded evidence iteration loops (`max_iterations = 2`), and human-in-the-loop interrupt/resume semantics (`AWAITING_APPROVAL`).
  - Exported graph orchestrator functions in `backend/app/agents/__init__.py`: `InvestigationWorkflowBuilder`, `create_investigation_graph`, `investigate_case`.
  - Added unit and integration test suite `tests/unit/test_investigation_workflow.py` (all 6 tests covering confirmed fraud flow, benign false-positive flow, bounded evidence loops, human approval interrupt/resume, and conditional routing).
  - Verified Stage C Exit Criteria: Full end-to-end investigation pipeline successfully operates locally across all fraud and cleared scenarios.

- **Layer 27 Completed**:
  - Implemented typed Pydantic API schemas in `backend/app/schemas/api.py` and exported in `backend/app/schemas/__init__.py`: `TriggerInvestigationRequest`, `SubmitEvidenceRequest`, `ApprovalActionRequest`, `ModifyActionRequest`, `MockConfirmationRequest`, `MockStepUpRequest`, `BenchmarkRunRequest`, `InvestigationResponse`, `CaseQueueItem`, `CaseQueueResponse`, `GraphVisualizationResponse`, `EvidenceListResponse`, `BenchmarkRunResponse`.
  - Implemented `InvestigationService` in `backend/app/services/investigation_service.py` managing investigation lifecycle, in-memory cache, Cytoscape.js graph element generation, evidence card formatting, analyst approval transitions, and Server-Sent Events (SSE) streaming.
  - Implemented route dependencies in `backend/app/api/dependencies.py`: `get_investigation_service_dep`, `get_tigergraph_client_dep`, `get_policy_engine_dep`.
  - Implemented thin route handlers across 4 modular routers:
    - `backend/app/api/routes/investigations.py`: `POST /api/investigations`, `GET /api/investigations/{case_id}`, `GET /api/investigations/{case_id}/events` (SSE), `GET /api/investigations/{case_id}/graph`, `GET /api/investigations/{case_id}/evidence`, `POST /api/investigations/{case_id}/evidence`, `POST /api/investigations/{case_id}/approve`, `POST /api/investigations/{case_id}/reject`, `POST /api/investigations/{case_id}/modify-action`.
    - `backend/app/api/routes/cases.py`: `GET /api/cases`, `GET /api/cases/{case_id}`.
    - `backend/app/api/routes/mock_actions.py`: `POST /api/mock/customer-confirmation`, `POST /api/mock/step-up-auth`.
    - `backend/app/api/routes/benchmark.py`: `POST /api/benchmark/run`.
  - Registered all routers on FastAPI application in `backend/app/main.py`.
  - Added unit and HTTP integration test suite `tests/unit/test_api_routes.py` (all 11 tests covering health, starting investigations, case lookups, graph elements, evidence cards, supplemental evidence, analyst approvals/rejections/modifications, queue filtering, mock services, benchmark runner, and SSE stream).

- **Layer 28 Completed**:
  - Initialized Next.js 14 / TypeScript / Tailwind CSS / Lucide React analyst console application foundation under `frontend/`.
  - Configured dark-mode financial intelligence theme with custom brand color tokens (`brand-950` to `brand-700`), risk neon glow tokens (`risk-critical`, `risk-high`, `risk-medium`, `risk-low`), and glassmorphism styling (`glass-panel`, `glass-card`).
  - Implemented typed data contracts in `frontend/types/api.ts` directly matching backend Pydantic models.
  - Implemented typed REST API client in `frontend/lib/api.ts` connecting to FastAPI backend (`http://localhost:8000`) for all investigation, case queue, graph, evidence, approval, and mock action endpoints.
  - Implemented reusable UI components:
    - `frontend/components/StatusBadge.tsx`: Badges for Risk levels, Case status, Next-Best Action types, and Human Approval status.
    - `frontend/components/Header.tsx`: Navigation header with backend API live connectivity indicator, quick stats, refresh button, and trigger button.
    - `frontend/components/CaseQueue.tsx`: Investigation triage queue with filter tabs (`ALL`, `IN_PROGRESS`, `AWAITING_APPROVAL`, `COMPLETED`), multi-attribute search, and interactive selection.
    - `frontend/components/NewInvestigationModal.tsx`: Modal for launching investigations with quick test presets (Velocity burst, Device anomaly, High risk merchant) and custom parameters.
    - `frontend/components/InvestigationWorkspace.tsx`: Comprehensive case intelligence console with Triad score cards (Risk, Confidence, Completeness), pre vs. post evidence recommendation history, human approval action controls (Approve, Reject, Modify), and interactive evidence submission.
  - Integrated complete dashboard layout in `frontend/app/page.tsx`.
  - Verified frontend type checking (`npm run typecheck`) and linting (`npm run lint`) pass cleanly with 0 errors and 0 warnings.

- **Layer 29 Completed**:
  - Implemented custom React hook `useInvestigationSSE` in `frontend/hooks/useInvestigationSSE.ts` managing EventSource streaming from `/api/investigations/{case_id}/events`.
  - Implemented robust event deduplication using a persistent `Set` of `event_id` keys to ensure idempotent event handling.
  - Implemented graceful connection management with automatic exponential backoff reconnection on transient drops, explicit `INVESTIGATION_STREAM_CLOSED` terminal detection, and error tracking without WebSocket dependencies.
  - Implemented `InvestigationTimeline` component in `frontend/components/InvestigationTimeline.tsx` displaying chronological event milestones with running/completed/awaiting-approval/error indicators, node name tags, human-readable descriptions, and expandable JSON event payloads.
  - Integrated `InvestigationTimeline` as a dedicated live tab in `frontend/components/InvestigationWorkspace.tsx`, dynamically synchronizing case headers, metrics, and approval controls upon receiving terminal workflow transitions.
  - Verified Next.js production build (`next build`), type checks (`npm run typecheck`), and lint checks (`npm run lint`) all pass with 0 errors and 0 warnings.

- **Layer 30 Completed**:
  - Installed and configured `cytoscape` and `@types/cytoscape` in `frontend/`.
  - Implemented `FraudGraphVisualization` in `frontend/components/FraudGraphVisualization.tsx` rendering the TigerGraph subgraph (Case, Customer, Account, Transaction, Device, IP, Historical Cases).
  - Designed distinct visual encodings: focal case (neon orange round rectangle), customer (sky blue circle), account (indigo rounded rect), transaction (amber diamond), device (emerald hexagon), IP (purple octagon), and historical fraud case (red star).
  - Added interactive controls toolbar: layout selector supporting `cose` (force-directed), `concentric` (focal center), `breadthfirst` (tree), and `circle` (radial); Zoom in/out buttons; Fit to Screen; Reset View; and element counter pills.
  - Implemented 1-hop interactive selection: clicking a node or edge highlights connected neighbors, dims non-connected nodes (`opacity: 0.15`), and opens a slide-in inspection drawer displaying node properties, degree, and matched grounded evidence items.
  - Mounted `FraudGraphVisualization` inside the `Graph Topology` tab in `frontend/components/InvestigationWorkspace.tsx`.
  - Verified Next.js production build (`next build`), type checks (`npm run typecheck`), and lint checks (`npm run lint`) all pass with 0 errors and 0 warnings.

- **Layer 32 Completed**:
  - Implemented `NextBestActionPanel` in `frontend/components/NextBestActionPanel.tsx` strictly rendering pre-evidence recommendation vs. post-evidence recommendation history without overwriting earlier state.
  - Implemented human-in-the-loop governance interactive modal and action triggers (`APPROVE`, `REJECT`, `MODIFY`) directly calling FastAPI backend endpoints `/api/investigations/{case_id}/approve`, `/reject`, and `/modify-action`.
  - Added policy basis badges, approval role badges, report filing alerts, and simulation execution indicators (`execution_mode = SIMULATED`).
  - Verified Next.js production build (`next build`), type checks (`npm run typecheck`), and lint checks (`npm run lint`) all pass with 0 errors.

- **Layer 33 Completed**:
  - Implemented `SimilarCasesPanel` in `frontend/components/SimilarCasesPanel.tsx` rendering top relevant historical cases with hybrid/graph/vector similarity meters, outcome badges (`FRAUD_CONFIRMED` vs. `CLEARED_BENIGN`), shared entity badges, typology tags, precedent warnings, and multi-attribute filters.
  - Implemented `PolicyGuidancePanel` in `frontend/components/PolicyGuidancePanel.tsx` displaying structured regulatory and bank policy context retrieved via GraphRAG, deterministic action constraints, and mandatory approval tiers.
  - Mounted panels in dedicated tabs in `frontend/components/InvestigationWorkspace.tsx`.
  - Verified Next.js production build (`next build`), type checks (`npm run typecheck`), and lint checks (`npm run lint`) all pass with 0 errors.

- **Layer 34 Completed**:
  - Implemented backend local audit trail logging infrastructure in `backend/app/observability/tracer.py` capturing structured execution spans for LangGraph nodes, GSQL queries, GraphRAG retrievals, LLM invocations, policy evaluations, and action simulations.
  - Enforced recursive secrets sanitization (`AGENTS.md` §32) masking all sensitive keys, tokens, and credentials before writing to local append-oriented JSONL files under `outputs/traces/{case_id}.jsonl`.
  - Added `TraceSpanItem` and `InvestigationTraceResponse` schemas, service helper `get_case_traces(case_id)`, and exposed `GET /api/investigations/{case_id}/trace`.
  - Wrapped LangGraph nodes in `backend/app/agents/graph.py` to record timestamps and durations.
  - Implemented `AuditTrailPanel` in `frontend/components/AuditTrailPanel.tsx` with performance summary cards, waterfall timeline with duration bars, filter pills, search bar, raw JSON inspector drawer, and trace path copy/export.
  - Mounted `AuditTrailPanel` inside the new `Audit & Traces` tab in `frontend/components/InvestigationWorkspace.tsx`.
  - Verified Next.js production build (`next build`), type checks (`npm run typecheck`), and lint checks (`npm run lint`) all pass with 0 errors and 0 warnings.

---

# Blockers

None currently.

Use this section to record blockers such as:

```text
- Missing dataset README
- TigerGraph credentials unavailable
- Dataset field ambiguity
- GSQL query blocked by missing relationship
- Model dependency unavailable
```

Do not hide blockers by implementing guessed behavior.

---

# Architecture Decisions Locked

The following are fixed:

- TigerGraph is the graph and case-memory platform.
- GSQL performs deterministic graph analysis.
- TigerGraph MCP is the graph tool layer.
- TigerGraph GraphRAG handles policy and case retrieval.
- LangGraph controls workflow/state.
- Groq is the primary reasoning provider.
- Gemini is the fallback provider.
- Laya is optional fast classification only.
- LightGBM is an optional historical signal only.
- SentenceTransformers provides local embeddings.
- FastAPI is the backend.
- Next.js is the frontend.
- Cytoscape.js renders the fraud graph.
- SSE streams investigation progress.
- Deterministic policy logic controls authorization.
- Sensitive actions use human approval.
- External banking actions remain simulated locally.
- No online deployment layer is currently in scope.

---

# Quality Gates

Before marking any layer complete, verify:

- [ ] requested scope only was implemented,
- [ ] no benchmark-specific logic was added,
- [ ] no unsupported dataset fields were invented,
- [ ] new deterministic code has tests,
- [ ] relevant tests were actually run,
- [ ] no secrets were committed,
- [ ] architecture choices remain unchanged,
- [ ] status file reflects reality,
- [ ] next unblocked layer is identified.

---

# Final Project Definition of Done

The project is complete when all required layers above are checked and:

1. all benchmark cases run through one workflow,
2. fraud and cleared cases are both handled,
3. graph evidence is visible,
4. GraphRAG policy evidence is visible,
5. risk, confidence, and evidence completeness are separate,
6. uncertain cases request more evidence,
7. pre-evidence and post-evidence next-best actions are preserved,
8. policy authorization is deterministic,
9. human approval works,
10. SAR/report generation works when required,
11. full case memory is written to TigerGraph,
12. future investigations can retrieve completed cases,
13. local UI presents the full investigation clearly,
14. benchmark output validation passes,
15. local demo scenarios are ready.
