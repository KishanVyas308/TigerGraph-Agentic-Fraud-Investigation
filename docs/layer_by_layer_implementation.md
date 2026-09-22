# TigerGraph Agentic Fraud Investigation — Layer-by-Layer Code Implementation Plan

## Purpose

This document is the implementation playbook for the TigerGraph Agentic Fraud Investigation project.

It converts the architecture into a sequence of coding layers that can be implemented one by one by a developer or AI coding model.

This plan is intentionally limited to:

- local development,
- local integration,
- local testing,
- benchmark execution,
- demo preparation.

It does **not** include:

- production deployment,
- cloud deployment,
- live production testing,
- CI/CD deployment pipelines,
- domain/DNS setup,
- public hosting,
- production observability setup,
- production secrets management.

The goal is to build a complete working hackathon system locally first.

---

# 1. Final Fixed Stack

Use the following stack unless a dataset constraint makes a component impossible.

## Core

- Python 3.11+
- FastAPI
- Pydantic v2
- LangGraph
- TigerGraph Savanna or local Community Edition
- TigerGraph MCP
- GSQL
- TigerGraph GraphRAG
- Groq SDK
- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`
- Gemini Flash as fallback
- SentenceTransformers
- LightGBM
- Laya for optional fast classification
- Polars
- DuckDB

## Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS
- shadcn/ui
- Cytoscape.js
- Recharts
- Server-Sent Events

## Local Observability

- structured Python logging
- optional Langfuse local/development integration

---

# 2. Global Engineering Rules

Every AI coding task in this project must follow these rules.

1. Do not hardcode benchmark answers.
2. Do not use hidden benchmark outcomes as investigation inputs.
3. Read the dataset README before making schema assumptions.
4. Treat the bank risk score as one signal, not ground truth.
5. TigerGraph must perform meaningful graph analysis.
6. GSQL must calculate fraud-related graph facts.
7. The LLM must not fabricate graph facts.
8. Every important LLM claim must reference evidence IDs.
9. Risk, confidence, and evidence completeness must remain separate.
10. Sensitive actions must pass through a deterministic policy layer.
11. Human approval must be represented explicitly where required.
12. Historical cases are precedent, not proof.
13. Both confirmed-fraud and cleared historical cases must be retrievable.
14. All evidence must have provenance.
15. All case updates must be append-oriented and auditable.
16. Use typed Pydantic models for all application boundaries.
17. Prefer deterministic code over LLM calls where possible.
18. Prefer installed GSQL queries over arbitrary generated queries.
19. Parallelize independent evidence retrieval.
20. Keep the runtime tool surface small.
21. Do not add extra frameworks without a clear requirement.
22. All benchmark cases must use the same investigation workflow.
23. Stop conditions must always be explicit.
24. Local mocks are acceptable for actions and evidence requests.
25. Do not add any online deployment layer to this implementation plan.

---

# 3. Target Repository Structure

Create the following structure.

```text
project-root/

backend/
  app/
    main.py
    config.py

    api/
      routes/
        investigations.py
        cases.py
        approvals.py
        evidence.py
        benchmark.py
        mock_actions.py
      dependencies.py

    agents/
      state.py
      graph.py
      nodes/
        intake.py
        trigger_classifier.py
        create_case.py
        parallel_evidence.py
        evidence_normalizer.py
        feature_engine.py
        risk_engine.py
        reasoner.py
        sufficiency.py
        evidence_planner.py
        policy_gate.py
        approval.py
        action_executor.py
        finalizer.py
        memory_writer.py

    graph/
      tigergraph_client.py
      mcp_client.py
      queries.py
      loaders.py
      models.py

    rag/
      chunking.py
      embeddings.py
      policy_index.py
      case_memory.py
      retrieval.py

    ml/
      features.py
      dataset.py
      train.py
      inference.py

    llm/
      router.py
      groq_client.py
      gemini_client.py
      schemas.py
      prompts.py

    classification/
      laya_client.py
      schemas.py

    policies/
      engine.py
      loader.py
      policy.yaml

    evidence/
      models.py
      normalize.py
      scoring.py

    actions/
      base.py
      mocks.py

    services/
      case_service.py
      investigation_service.py
      event_stream.py
      audit_service.py

    schemas/
      api.py
      case.py
      actions.py
      approvals.py

    utils/
      ids.py
      time.py
      logging.py

frontend/
  app/
    page.tsx
    cases/
      page.tsx
      [caseId]/
        page.tsx

  components/
    CaseQueue.tsx
    CaseHeader.tsx
    InvestigationTimeline.tsx
    FraudGraph.tsx
    EvidencePanel.tsx
    AssessmentPanel.tsx
    HypothesisPanel.tsx
    SimilarCasesPanel.tsx
    NextBestActionPanel.tsx
    ApprovalPanel.tsx
    PolicyPanel.tsx

  lib/
    api.ts
    sse.ts
    types.ts

gsql/
  schema/
    fraud_schema.gsql
  loading/
    load_core_data.gsql
    load_cases.gsql
  queries/
    get_transaction_context.gsql
    get_transaction_behavior.gsql
    get_entity_neighborhood.gsql
    find_shared_devices.gsql
    find_shared_ips.gsql
    find_fraud_neighbors.gsql
    get_shortest_path_to_fraud.gsql
    detect_money_flow_patterns.gsql
    get_connected_cluster.gsql
    get_device_identity_context.gsql
    find_similar_graph_cases.gsql
    get_case_timeline.gsql
    write_case_update.gsql

data/
  raw/
  processed/
  policies/
  benchmark/

scripts/
  inspect_dataset.py
  preprocess_dataset.py
  create_graph_files.py
  load_tigergraph.py
  build_embeddings.py
  train_lightgbm.py
  run_benchmark.py
  validate_outputs.py

outputs/
  benchmark/
  cases/
  sar/
  traces/

tests/
  unit/
  integration/
  benchmark/

docs/
  project_description.md
  layer_by_layer_implementation.md
  architecture.md
  local_setup.md
  demo_flow.md
```

---

# 4. Layer 0 — Repository Bootstrap and Local Configuration

## Objective

Create the local project skeleton and shared configuration conventions before implementing business logic.

## Tasks

1. Create the repository structure.
2. Create Python virtual environment configuration.
3. Create backend dependency file.
4. Create frontend package configuration.
5. Create `.env.example`.
6. Create typed configuration loader.
7. Create local structured logging.
8. Create common ID-generation utilities.
9. Create UTC timestamp helpers.
10. Create a local README with startup prerequisites only.
11. Do not include cloud deployment instructions.

## Required Environment Variables

```text
TIGERGRAPH_HOST=
TIGERGRAPH_USERNAME=
TIGERGRAPH_PASSWORD=
TIGERGRAPH_GRAPH=
TIGERGRAPH_SECRET=

GROQ_API_KEY=
GROQ_PRIMARY_MODEL=openai/gpt-oss-120b
GROQ_FAST_MODEL=openai/gpt-oss-20b

GEMINI_API_KEY=
GEMINI_FALLBACK_MODEL=

ENABLE_LAYA=false
ENABLE_LIGHTGBM=false
ENABLE_LANGFUSE=false

DATASET_PATH=
OUTPUT_PATH=./outputs
```

## Deliverables

- local backend can import successfully,
- frontend can start locally,
- configuration validates missing required values,
- logging works,
- no application functionality yet.

## Acceptance Criteria

- `python -m backend.app.main` imports without error.
- frontend TypeScript passes type checking.
- secrets are never committed.
- application config comes from environment variables.

## AI Coding Prompt

```text
You are implementing Layer 0 of a TigerGraph agentic fraud investigation project.

Create the repository bootstrap and local configuration only.

Requirements:
- Python 3.11+ backend using FastAPI and Pydantic v2.
- Next.js TypeScript frontend.
- Create the exact directory structure specified in the project implementation document.
- Add a typed Settings/config module using environment variables.
- Add `.env.example` with TigerGraph, Groq, Gemini, optional Laya, optional LightGBM, and local output settings.
- Add structured logging utilities.
- Add UUID/ID helpers and UTC timestamp helpers.
- Add dependency files for backend and frontend.
- Do not implement fraud logic yet.
- Do not implement deployment, Docker hosting, CI/CD, cloud setup, DNS, or production configuration.
- Keep all code type-safe and minimal.
- After implementation, list all files created and explain how to verify imports locally.
```

---

# 5. Layer 1 — Dataset Inspection and Authoritative Schema Mapping

## Objective

Understand the dataset before creating TigerGraph or application schemas.

This layer must happen before graph design.

## Tasks

1. Read the dataset README completely.
2. Enumerate every file.
3. Record:
   - filename,
   - purpose,
   - row count,
   - columns,
   - identifiers,
   - references to other files,
   - date range,
   - benchmark/training role.
4. Identify:
   - transaction identifier,
   - customer identifier,
   - account/card identifiers,
   - device fields,
   - connection/IP fields,
   - merchant fields,
   - historical case fields,
   - case outcomes,
   - risk score,
   - policy files,
   - typology files,
   - regulatory references,
   - benchmark files.
5. Determine what must not be treated as ground truth.
6. Document benchmark leakage boundaries.
7. Produce a machine-readable data dictionary JSON.
8. Produce `docs/dataset_mapping.md`.

## Deliverables

```text
docs/dataset_mapping.md
data/processed/data_dictionary.json
scripts/inspect_dataset.py
```

## Acceptance Criteria

- no TigerGraph field is invented without a documented mapping,
- every graph vertex/edge later traces back to real dataset fields,
- benchmark data is clearly separated from historical training data,
- case outcome availability is documented by time period.

## AI Coding Prompt

```text
You are implementing Layer 1 of a TigerGraph fraud investigation system.

Your task is dataset inspection and schema mapping only.

First read the dataset README completely. Treat it as authoritative.

Then:
1. enumerate every dataset file,
2. inspect schemas and representative rows,
3. identify primary keys and relationship keys,
4. identify the bank risk score field,
5. identify historical closed-case labels/outcomes,
6. identify benchmark cases,
7. identify policy, fraud typology, and regulatory files,
8. identify all device, IP, identity, merchant, customer, account/card, and transaction fields,
9. document missing values and unusual types,
10. identify any fields that could cause benchmark leakage.

Create:
- `scripts/inspect_dataset.py`,
- `docs/dataset_mapping.md`,
- `data/processed/data_dictionary.json`.

Do not build the graph yet.
Do not guess undocumented meanings.
Do not use benchmark outcomes as model inputs.
At the end, provide a proposed entity/relationship mapping but mark it as provisional until Layer 2.
```

---

# 6. Layer 2 — Data Preprocessing and Canonical Entity Tables

## Objective

Transform raw dataset files into clean, reproducible canonical tables suitable for TigerGraph loading.

## Tasks

Use Polars and DuckDB.

Create canonical files for:

- transactions,
- customers,
- accounts/cards,
- devices,
- IP/connection entities,
- merchants,
- identity attributes where supported,
- historical cases,
- case-to-entity relationships,
- policies,
- typologies,
- regulatory documents,
- benchmark triggers.

Normalize:

- IDs,
- timestamps,
- nulls,
- booleans,
- categorical values,
- numeric types.

Create derived non-label fields only when defensible.

Examples:

- event timestamp,
- transaction day/hour,
- normalized merchant identifier,
- normalized device identifier.

Do not calculate benchmark answers.

## Deliverables

```text
scripts/preprocess_dataset.py
data/processed/*.parquet
data/processed/preprocessing_report.json
```

## Acceptance Criteria

- preprocessing is deterministic,
- rerunning produces the same canonical IDs,
- no duplicate primary keys,
- referential integrity report exists,
- benchmark and historical closed cases remain distinguishable.

## AI Coding Prompt

```text
Implement Layer 2: canonical dataset preprocessing.

Use Polars and DuckDB.

Input:
- raw hackathon dataset,
- data dictionary from Layer 1.

Output canonical Parquet tables for every graph entity and relationship that actually exists in the dataset.

Requirements:
- stable deterministic identifiers,
- normalized timestamps,
- explicit null handling,
- validated numeric types,
- no hidden label leakage,
- separate historical resolved cases from benchmark cases,
- produce referential-integrity checks,
- produce a preprocessing report with row counts before and after transformations.

Do not train models.
Do not create TigerGraph schema.
Do not infer unsupported entities.
Write modular functions and unit-testable transformations.
```

---

# 7. Layer 3 — TigerGraph Graph Schema

## Objective

Create the graph model that will support fraud investigation and case memory.

## Core Vertex Categories

Create only vertices supported by the dataset.

Expected categories may include:

- Customer
- Account
- Card
- Transaction
- Device
- IPAddress
- Merchant
- Email
- Phone
- Address
- FraudCase
- Evidence
- FraudPattern
- PolicySection
- RegulationSection
- Action
- Decision
- Approval
- CaseOutcome

## Core Relationship Categories

Examples:

- OWNS
- USES_CARD
- INITIATED
- RECEIVED
- USES_DEVICE
- USES_IP
- TRANSACTED_WITH
- HAS_EMAIL
- HAS_PHONE
- HAS_ADDRESS
- CASE_INVESTIGATES
- CASE_HAS_EVIDENCE
- CASE_HAS_DECISION
- CASE_HAS_ACTION
- CASE_HAS_APPROVAL
- MATCHES_PATTERN
- REFERENCES_POLICY
- HAS_OUTCOME
- LINKED_TO

Exact relationships must follow dataset reality.

## Tasks

1. Map canonical data to graph schema.
2. Add appropriate indexes/primary IDs.
3. Add attributes needed by queries.
4. Keep case investigation entities first-class.
5. Add edge directions intentionally.
6. Document schema rationale.

## Deliverables

```text
gsql/schema/fraud_schema.gsql
docs/graph_schema.md
```

## Acceptance Criteria

The graph supports:

- transaction investigation,
- multi-hop traversal,
- device-sharing analysis,
- IP-sharing analysis,
- fraud-case memory,
- evidence linkage,
- action/approval audit trail.

## AI Coding Prompt

```text
Implement Layer 3: TigerGraph schema design.

Inputs:
- authoritative dataset mapping,
- canonical processed tables.

Create `gsql/schema/fraud_schema.gsql` and `docs/graph_schema.md`.

Requirements:
- model real entities only,
- make FraudCase, Evidence, Decision, Action, Approval, FraudPattern, and CaseOutcome first-class graph objects where useful,
- support shared-device/shared-IP analysis,
- support multi-hop paths from transactions to historical fraud cases,
- support future case-memory retrieval,
- support policy references,
- document why each edge direction exists,
- include only attributes required for investigation or retrieval.

Do not add an IsFraud flag to transactions if the dataset does not contain one.
Do not encode benchmark truth.
Do not create GSQL investigation queries yet.
```

---

# 8. Layer 4 — TigerGraph Loading Jobs

## Objective

Load canonical processed data into TigerGraph reproducibly.

## Tasks

1. Create loading jobs for:
   - core entities,
   - relationship edges,
   - historical cases,
   - policy/typology metadata.
2. Add loading validation.
3. Validate row counts.
4. Validate representative relationships.
5. Create a local Python loader script.
6. Make reload behavior explicit.

## Deliverables

```text
gsql/loading/load_core_data.gsql
gsql/loading/load_cases.gsql
scripts/load_tigergraph.py
tests/integration/test_graph_load.py
```

## Acceptance Criteria

After loading:

- expected vertex counts match processed tables,
- expected edge counts are plausible,
- random transaction IDs can retrieve customer/account/device context,
- historical cases are connected to investigated entities.

## AI Coding Prompt

```text
Implement Layer 4: TigerGraph data loading.

Create GSQL loading jobs and a local Python driver script.

Requirements:
- load canonical Parquet/CSV-compatible outputs from Layer 2,
- load core graph entities first,
- then edges,
- then historical cases and their relationships,
- then policy/typology metadata where applicable,
- include count validation,
- include representative relationship checks,
- fail loudly on missing required IDs,
- log load statistics.

Do not implement investigation reasoning.
Do not implement deployment.
```

---

# 9. Layer 5 — Core GSQL Investigation Query Library

## Objective

Build the deterministic graph-analysis foundation.

This layer is mandatory before LLM reasoning.

## Query 1 — `get_transaction_context`

Return:

- transaction,
- customer,
- account/card,
- merchant,
- device,
- IP,
- relevant direct relationships.

## Query 2 — `get_transaction_behavior`

Calculate:

- amount vs historical average,
- amount vs median,
- recent transaction counts,
- velocity windows,
- merchant novelty,
- time anomalies where supported.

## Query 3 — `get_entity_neighborhood`

Return a bounded graph neighborhood.

Rules:

- 1–3 hops,
- configurable limits,
- avoid unbounded expansion.

## Query 4 — `find_shared_devices`

Calculate:

- accounts per device,
- customers per device,
- prior fraud cases attached to device-linked entities.

## Query 5 — `find_shared_ips`

Calculate similar metrics for IPs.

## Query 6 — `find_fraud_neighbors`

Calculate:

- direct historical fraud-case connections,
- suspicious case-linked neighbors,
- counts by relationship type.

## Query 7 — `get_shortest_path_to_fraud`

Return bounded shortest paths from current entity to entities connected to confirmed historical fraud cases.

## Query 8 — `detect_money_flow_patterns`

Where transaction relationships allow it, calculate:

- fan-in,
- fan-out,
- rapid movement,
- circular paths,
- pass-through patterns.

## Query 9 — `get_connected_cluster`

Return suspicious connected component/community information.

## Query 10 — `get_device_identity_context`

Return:

- first seen,
- linked accounts/customers,
- historical case links,
- shared identity attributes.

## Query 11 — `get_case_timeline`

Return complete case history.

## Query 12 — `write_case_update`

Append case evidence/action/decision records safely.

## Deliverables

All files under:

```text
gsql/queries/
```

plus typed Python wrappers.

## Acceptance Criteria

Each query:

- has deterministic output,
- has bounded runtime behavior,
- has clear JSON output,
- can be tested against sample IDs,
- returns only useful investigation facts.

## AI Coding Prompt

```text
Implement Layer 5: the GSQL investigation query library.

Build installed GSQL queries for:
- transaction context,
- behavioral features,
- bounded entity neighborhood,
- shared devices,
- shared IPs,
- fraud-linked neighbors,
- shortest path to historical fraud-linked entities,
- suspicious money-flow patterns,
- connected clusters,
- device/identity context,
- case timeline,
- safe case update.

Requirements:
- deterministic outputs,
- bounded traversal,
- no unbounded graph dumps,
- machine-readable JSON-oriented results,
- clear comments,
- typed Python wrappers,
- integration tests using known sample IDs.

The LLM must not be required to calculate these facts.
```

---

# 10. Layer 6 — TigerGraph Client and MCP Integration

## Objective

Create a single graph access layer for the rest of the backend.

## Tasks

1. Build `TigerGraphClient`.
2. Build MCP adapter/client.
3. Define graph tool methods.
4. Add timeout handling.
5. Add retry for safe reads.
6. Add typed results.
7. Restrict available methods.
8. Separate read tools and write tools.
9. Add local mock mode for unit tests.

## Required Methods

```text
get_transaction_context()
get_transaction_behavior()
get_entity_neighborhood()
find_shared_devices()
find_shared_ips()
find_fraud_neighbors()
get_shortest_path_to_fraud()
detect_money_flow_patterns()
get_connected_cluster()
get_device_identity_context()
get_case_timeline()
write_case_update()
vector_search()
```

## Acceptance Criteria

No agent node should call TigerGraph through raw HTTP directly.

## AI Coding Prompt

```text
Implement Layer 6: the TigerGraph access layer.

Create:
- `TigerGraphClient`,
- TigerGraph MCP adapter,
- typed response models,
- safe read/write separation,
- configurable timeouts,
- retries for idempotent reads only,
- local mock implementation for tests.

Expose explicit methods for every installed GSQL query and vector search.

Do not expose arbitrary graph deletion or schema mutation.
Do not let higher-level agent code construct raw TigerGraph requests.
```

---

# 11. Layer 7 — Policy, Typology, Regulation, and Historical Case Embeddings

## Objective

Prepare GraphRAG knowledge.

## Tasks

1. Parse policy documents.
2. Parse typology documents.
3. Parse regulatory references.
4. Create historical case summaries from allowed historical data.
5. Chunk by semantic section, not arbitrary token count where possible.
6. Generate local embeddings.
7. Store:
   - source ID,
   - section,
   - document type,
   - text,
   - embedding,
   - graph references.
8. Link policy/typology entities into TigerGraph.

## Deliverables

```text
backend/app/rag/chunking.py
backend/app/rag/embeddings.py
backend/app/rag/policy_index.py
scripts/build_embeddings.py
```

## Acceptance Criteria

Queries can retrieve:

- relevant policy,
- relevant typology,
- relevant regulation,
- similar historical cases.

## AI Coding Prompt

```text
Implement Layer 7: GraphRAG corpus preparation.

Sources:
- bank fraud policy,
- fraud typologies,
- regulatory references,
- historical resolved case summaries.

Use SentenceTransformers locally for embeddings.

Requirements:
- preserve source provenance,
- chunk by meaningful section,
- store section IDs and source types,
- build embeddings deterministically,
- connect retrievable documents/cases to TigerGraph entities,
- do not embed every raw transaction,
- do not include hidden benchmark outcomes.

Create local scripts to rebuild the index from scratch.
```

---

# 12. Layer 8 — GraphRAG Retrieval Service

## Objective

Provide compact grounded context to the reasoning agent.

## Retrieval Modes

### Policy Retrieval

Input:

- current evidence summary,
- candidate action,
- fraud hypothesis.

Output:

- top relevant policy sections,
- typologies,
- regulatory sections.

### Historical Case Retrieval

Use:

- graph overlap,
- vector similarity,
- shared entity matches,
- structural features.

Return top 3–5 cases.

## Tasks

1. Build retrieval service.
2. Add result deduplication.
3. Add relevance threshold.
4. Add compact summaries.
5. Add source references.
6. Retrieve both fraud and cleared cases.
7. Never return massive raw documents.

## AI Coding Prompt

```text
Implement Layer 8: TigerGraph GraphRAG retrieval.

Create a retrieval service with two major APIs:

1. retrieve_policy_context(case_context)
2. retrieve_similar_cases(case_context)

Policy retrieval must return relevant policy, typology, and regulatory sections with source IDs.

Similar-case retrieval must combine:
- graph overlap,
- vector similarity,
- shared entities,
- available structural features.

Return only the top relevant cases and include both fraud-confirmed and cleared outcomes when relevant.

Do not dump entire documents or full historical cases into the LLM context.
```

---

# 13. Layer 9 — Fraud Investigation State Models

## Objective

Define all typed state before building LangGraph.

## Main Model

Create `FraudCaseState`.

Required categories:

### Identity

```text
case_id
trigger_type
transaction_id
customer_id
account_ids
```

### Evidence

```text
transaction_evidence
graph_evidence
device_evidence
identity_evidence
policy_evidence
historical_case_evidence
external_evidence
```

### Features

```text
graph_features
behavior_features
bank_risk_score
historical_ml_score
```

### Reasoning Output

```text
hypotheses
risk_level
risk_score
confidence
evidence_completeness
missing_evidence
supporting_evidence_ids
contradictory_evidence_ids
```

### Actions

```text
pre_evidence_next_best_action
requested_evidence
received_evidence
post_evidence_next_best_action
approval_required
approval_status
executed_actions
```

### Case Control

```text
case_status
iteration_count
stop_reason
timeline
```

## Tasks

1. Define enums.
2. Define Pydantic models.
3. Define serialization.
4. Define state merge behavior.
5. Validate evidence IDs.
6. Validate action types.

## AI Coding Prompt

```text
Implement Layer 9: typed fraud investigation state.

Create Pydantic v2 models and enums for:
- FraudCaseState,
- Evidence,
- Hypothesis,
- RiskAssessment,
- EvidenceRequest,
- NextBestAction,
- Approval,
- ActionExecution,
- TimelineEvent,
- StopReason.

Requirements:
- explicit enum values,
- validation,
- serializable to JSON,
- no untyped dictionaries at core boundaries,
- support LangGraph state updates,
- separate risk, confidence, and evidence completeness.
```

---

# 14. Layer 10 — Evidence Model and Evidence Normalizer

## Objective

Convert heterogeneous tool outputs into one auditable evidence format.

## Evidence Model

Each evidence object must contain:

```text
evidence_id
source
source_reference
category
fact
reliability
timestamp
entity_ids
supports_hypotheses
contradicts_hypotheses
metadata
```

## Evidence Categories

Suggested:

- TRANSACTION_BEHAVIOR
- GRAPH_RELATIONSHIP
- DEVICE
- IDENTITY
- MONEY_FLOW
- HISTORICAL_CASE
- POLICY
- REGULATION
- CUSTOMER_RESPONSE
- AUTHENTICATION
- ANALYST_INPUT
- EXTERNAL_SIGNAL

## Tasks

1. Normalize every GSQL result.
2. Normalize GraphRAG results.
3. Normalize external/mock evidence.
4. Deduplicate evidence.
5. Preserve provenance.
6. Avoid converting policy text into factual transaction evidence.

## Acceptance Criteria

The reasoning model receives evidence objects, not tool-specific payloads.

## AI Coding Prompt

```text
Implement Layer 10: evidence normalization.

Create a canonical Evidence model and adapters for:
- GSQL transaction output,
- GSQL graph output,
- device/identity output,
- GraphRAG policy results,
- historical case retrieval,
- customer responses,
- authentication results,
- analyst input,
- optional external signals.

Requirements:
- every evidence item gets a stable evidence ID,
- provenance must be preserved,
- deduplicate equivalent facts,
- policy evidence must remain distinguishable from case facts,
- do not infer fraud merely while normalizing evidence.
```

---

# 15. Layer 11 — Parallel Evidence Collection Node

## Objective

Gather independent evidence simultaneously.

## Parallel Branches

### Branch A — Transaction Analysis

Call:

- transaction context,
- transaction behavior.

### Branch B — Graph Relationship Analysis

Call:

- neighborhood,
- shared devices,
- shared IPs,
- fraud neighbors,
- shortest fraud path,
- money-flow analysis,
- cluster analysis.

### Branch C — Policy GraphRAG

Retrieve:

- relevant policy,
- typology,
- regulatory guidance.

### Branch D — Historical Case Memory

Retrieve:

- graph-similar cases,
- vector-similar cases,
- prior outcomes,
- prior analyst decisions.

### Branch E — Device and Identity Analysis

Retrieve:

- device novelty,
- device age,
- linked accounts/customers,
- linked fraud cases,
- shared identity attributes.

### Branch F — Optional Internal/External Signals

Use only when configured.

## Implementation

Use `asyncio.gather()` or equivalent concurrency.

Failures must be isolated.

Example:

- policy retrieval failure should not erase graph evidence,
- optional signal failure should not stop the case.

## AI Coding Prompt

```text
Implement Layer 11: parallel evidence collection.

Create one LangGraph-compatible node that launches independent tasks concurrently using asyncio.

Run:
1. GSQL transaction analysis,
2. GSQL graph relationship analysis,
3. GraphRAG policy retrieval,
4. historical case-memory retrieval,
5. device/identity analysis,
6. optional internal/external signal retrieval.

Requirements:
- independent calls run concurrently,
- each branch has timeout/error isolation,
- required and optional branches are distinguished,
- results are passed through the Evidence Normalizer,
- node returns a structured state update,
- no LLM call is needed to decide how to run these baseline branches.
```

---

# 16. Layer 12 — Graph Feature Engine

## Objective

Produce deterministic features from graph and transaction evidence.

## Core Features

Implement when supported by data:

```text
shared_device_account_count
shared_device_customer_count
fraud_accounts_on_device
shared_ip_account_count
fraud_neighbors_count
shortest_distance_to_fraud
connected_component_size
community_size
transaction_count_5m
transaction_count_10m
transaction_count_1h
transaction_amount_ratio_to_mean
transaction_amount_ratio_to_median
new_device
new_ip
new_merchant
fan_in_count
fan_out_count
cycle_detected
rapid_pass_through
```

## Tasks

1. Create typed feature model.
2. Derive only deterministic features.
3. Preserve null when unavailable.
4. Add feature explanations.
5. Write unit tests.

## AI Coding Prompt

```text
Implement Layer 12: deterministic fraud feature engine.

Input:
- normalized evidence,
- GSQL query outputs.

Output:
- typed FraudFeatureSet.

Calculate supported features including:
shared-device counts,
shared-IP counts,
fraud-neighbor counts,
shortest distance to historical fraud-linked entities,
component/community size,
transaction velocity,
amount deviation,
new device/IP/merchant flags,
fan-in/fan-out,
cycle detection,
rapid pass-through.

Do not invent missing values.
Do not use the LLM.
Include a human-readable explanation for every non-null feature.
```

---

# 17. Layer 13 — Historical LightGBM Risk Signal

## Objective

Train a lightweight historical classifier from permitted resolved cases.

This is an optional enhancement and must not block the core system.

## Tasks

1. Build training dataset from historical resolved cases only.
2. Use graph and behavior features.
3. Prevent benchmark leakage.
4. Train LightGBM.
5. Evaluate:
   - precision,
   - recall,
   - F1,
   - ROC-AUC where meaningful,
   - confusion matrix.
6. Save model locally.
7. Provide inference API.
8. Return score plus model metadata.
9. If model quality is poor, allow disabling it.

## Important

Call this signal:

```text
historical_ml_score
```

Do not call it calibrated fraud probability unless calibration is actually performed.

## AI Coding Prompt

```text
Implement Layer 13: optional LightGBM historical risk model.

Use only historical closed cases legitimately available before the benchmark period.

Features must come from Layer 12 plus the bank risk score where allowed.

Requirements:
- explicit train/validation split,
- no benchmark leakage,
- reproducible random seed,
- report precision/recall/F1 and confusion matrix,
- persist feature ordering and model version,
- expose local inference function,
- return `historical_ml_score`,
- allow feature flag to disable the model if unavailable.

Do not make this model the final fraud decision-maker.
```

---

# 18. Layer 14 — Laya Fast Classifier

## Objective

Use Laya only for cheap local routing/classification.

This layer is optional.

## Supported Tasks

- trigger classification,
- customer confirmation classification,
- authentication-result interpretation if text-based,
- analyst-response classification.

## Not Allowed

Laya must not:

- make final fraud decisions,
- classify every evidence item as a vote,
- decide policy,
- decide whether an account is blocked,
- replace the main reasoning model.

## AI Coding Prompt

```text
Implement Layer 14: optional Laya local classifier.

Create a small abstraction with typed classification outputs for:
- trigger type,
- customer confirmation response,
- analyst response.

Requirements:
- feature-flagged,
- preload model once,
- fallback to deterministic parsing or main LLM when confidence is insufficient,
- never make final fraud or policy decisions,
- log classification latency locally.
```

---

# 19. Layer 15 — LLM Provider Router

## Objective

Create one provider-independent interface.

## Routing Rules

### Primary

Groq `openai/gpt-oss-120b`

### Fast Model

Groq `openai/gpt-oss-20b`

### Fallback

Gemini Flash

## Tasks

1. Define provider interface.
2. Support structured output.
3. Add JSON schema validation.
4. Add retry for transient failures.
5. Add fallback.
6. Track latency locally.
7. Never silently accept invalid JSON.

## AI Coding Prompt

```text
Implement Layer 15: LLM provider router.

Create provider clients for:
- Groq primary reasoning,
- Groq fast reasoning,
- Gemini fallback.

Requirements:
- one shared interface,
- structured Pydantic output,
- schema validation,
- timeout handling,
- safe retry for transient provider errors,
- fallback to Gemini when Groq is unavailable/rate-limited,
- local logging of model, latency, and request ID,
- do not expose provider-specific response types to agent nodes.
```

---

# 20. Layer 16 — Main Fraud Reasoning Model

## Objective

Reason over already-computed evidence.

The LLM does not search raw data directly in this node.

## Inputs

- normalized evidence,
- graph features,
- bank risk score,
- optional LightGBM score,
- policy context,
- similar cases.

## Output Schema

```text
hypotheses[]
supporting_evidence_ids[]
contradictory_evidence_ids[]
risk_level
risk_score
confidence
evidence_completeness
missing_evidence[]
preliminary_next_best_action
explanation
```

## Required Reasoning Behavior

The model must:

- generate competing hypotheses,
- cite evidence IDs,
- distinguish policy from facts,
- identify contradictory evidence,
- state uncertainty,
- avoid treating prior cases as proof,
- avoid unsupported claims.

## AI Coding Prompt

```text
Implement Layer 16: the main fraud reasoning node.

Input:
- normalized Evidence objects,
- FraudFeatureSet,
- bank risk score,
- optional historical_ml_score,
- relevant policy/typology context,
- top similar historical cases.

Use the primary Groq reasoning model through the provider router.

Return a validated structured object containing:
- fraud hypotheses,
- supporting evidence IDs,
- contradictory evidence IDs,
- risk level,
- risk score,
- confidence,
- evidence completeness,
- missing evidence,
- preliminary next-best action,
- concise auditable explanation.

Rules:
- never fabricate facts,
- every material assertion must reference evidence IDs,
- prior cases are precedent, not proof,
- do not expose chain-of-thought,
- distinguish risk from confidence,
- if evidence is weak, say so explicitly.
```

---

# 21. Layer 17 — Evidence Sufficiency Engine

## Objective

Decide whether investigation should act, gather more evidence, escalate, or stop.

Do not rely on one threshold alone.

## Inputs

- risk,
- confidence,
- evidence completeness,
- missing evidence,
- policy constraints,
- action severity,
- iteration count.

## Output

```text
ACT
GATHER_MORE_EVIDENCE
ESCALATE
STOP_NO_MATERIAL_FRAUD
```

## Rules

Examples:

- high risk + high confidence + complete evidence → ACT
- high risk + low confidence → GATHER_MORE_EVIDENCE
- policy requires escalation → ESCALATE
- low risk + high confidence + sufficient evidence → STOP/ALLOW/CLOSE
- max investigation iterations reached → ESCALATE or stop according to policy.

## AI Coding Prompt

```text
Implement Layer 17: evidence sufficiency decision engine.

Create deterministic code that consumes:
- risk level,
- confidence,
- evidence completeness,
- missing evidence,
- candidate action severity,
- policy constraints,
- investigation iteration count.

Return one of:
ACT,
GATHER_MORE_EVIDENCE,
ESCALATE,
STOP_NO_MATERIAL_FRAUD.

Do not use a simplistic majority vote over evidence.
Do not let the LLM alone control this gate.
Make thresholds configurable and document them.
```

---

# 22. Layer 18 — Evidence Planner / Value of Information

## Objective

When uncertainty remains, select the smallest useful next evidence request.

## Candidate Evidence Types

- CUSTOMER_CONFIRMATION
- STEP_UP_AUTH
- ANALYST_INFORMATION
- APPROVED_EXTERNAL_CHECK

## Scoring Concept

Approximate:

```text
VOI =
expected_uncertainty_reduction
× decision_impact
÷ (cost + friction + latency)
```

This does not need mathematically perfect calibration.

It must be explainable and deterministic enough for the demo.

## Required Behavior

Before requesting evidence:

1. record current next-best action,
2. record why more evidence is needed,
3. record selected evidence request,
4. record what decision the evidence could change.

## AI Coding Prompt

```text
Implement Layer 18: value-of-information evidence planner.

Input:
- current fraud assessment,
- missing evidence,
- candidate next-best action,
- policy constraints.

Candidates:
- customer transaction confirmation,
- step-up authentication,
- analyst-provided information,
- approved external check.

Score candidates using an explainable approximation of:
expected uncertainty reduction × decision impact / cost-friction-latency.

Output:
- selected evidence request,
- rationale,
- expected decision impact,
- approval requirement,
- current pre-evidence next-best action.

The planner must choose the smallest useful request, not request everything.
```

---

# 23. Layer 19 — Deterministic Policy Engine

## Objective

Separate recommendation from authorization.

## Files

```text
backend/app/policies/policy.yaml
backend/app/policies/loader.py
backend/app/policies/engine.py
```

## Policy Entry Example

```yaml
BLOCK_ACCOUNT:
  allowed: true
  autonomous: false
  approval_required: true
  approval_role: SENIOR_FRAUD_ANALYST

ALLOW_TRANSACTION:
  allowed: true
  autonomous: true
  approval_required: false
```

Actual values must come from dataset policy.

## Engine Checks

- is action recognized,
- is action allowed,
- can agent execute autonomously,
- approval required,
- approver role,
- SAR/report requirement,
- evidence prerequisites.

## AI Coding Prompt

```text
Implement Layer 19: deterministic action policy engine.

Read action rules from `policy.yaml`, populated only from the hackathon policy.

For any recommended action return:
- allowed,
- autonomous,
- approval_required,
- approval_role,
- report_required,
- unmet_prerequisites,
- policy_reference.

The LLM may recommend an action but cannot override this engine.

Do not implement Open Policy Agent.
Keep the engine local, deterministic, typed, and testable.
```

---

# 24. Layer 20 — Human Approval State

## Objective

Pause and resume investigations requiring approval.

## Supported Decisions

- APPROVE
- REJECT
- MODIFY

## Tasks

1. Create approval request schema.
2. Add LangGraph interrupt point.
3. Persist pending approval state.
4. Resume workflow after analyst decision.
5. Record analyst identity/reference if available.
6. Record decision reason.
7. If rejected, return to action selection.
8. If modified, re-run policy check.

## AI Coding Prompt

```text
Implement Layer 20: human-in-the-loop approval.

Use LangGraph interrupt/resume semantics.

When the policy engine requires approval:
- create an ApprovalRequest,
- pause workflow,
- expose data needed by frontend,
- accept APPROVE, REJECT, or MODIFY,
- record timestamp and reason,
- resume workflow safely.

On reject:
- return to next-best-action selection.

On modify:
- run the modified action through policy validation again.

All approval events must be appended to case history.
```

---

# 25. Layer 21 — Mock Evidence and Action Services

## Objective

Simulate external operations required by the challenge.

## Mock Evidence Services

- customer transaction confirmation,
- step-up authentication,
- analyst evidence submission,
- device/IP reputation if used.

## Mock Action Services

- allow transaction,
- block transaction,
- monitor account,
- block/freeze account,
- warn customer,
- escalate analyst,
- create SAR/report reference,
- close case.

## Requirements

Mocks must:

- have deterministic demo controls,
- return typed results,
- append events,
- never pretend to be real bank systems.

## AI Coding Prompt

```text
Implement Layer 21: local mock evidence and action services.

Create typed mock APIs/services for:
- customer confirms transaction,
- customer denies transaction,
- step-up authentication passes,
- step-up authentication fails,
- analyst provides evidence,
- allow/block transaction,
- monitor/block account,
- warn customer,
- escalate,
- close case,
- create report reference.

Requirements:
- deterministic demo inputs,
- no external live systems,
- append all results to case timeline,
- clearly mark execution_mode = SIMULATED.
```

---

# 26. Layer 22 — SAR / Report Generator

## Objective

Generate a structured suspicious activity report when policy requires it.

## Rules

Use verified evidence only.

Never invent:

- customer facts,
- transaction facts,
- regulations,
- dates,
- amounts,
- identities.

## Output

Must follow the dataset README-required format.

## AI Coding Prompt

```text
Implement Layer 22: SAR/report generator.

Input:
- finalized case state,
- verified evidence,
- applicable policy/regulatory context.

Generate the exact report structure required by the dataset README.

Rules:
- use verified facts only,
- cite evidence IDs internally,
- never invent missing information,
- if a required field is unavailable, mark it explicitly according to the answer format,
- save the report under `outputs/sar/`,
- return a report reference for case memory.
```

---

# 27. Layer 23 — Case Finalizer and Stop Conditions

## Objective

Finalize investigation consistently.

## Stop Reasons

```text
SUFFICIENT_EVIDENCE_FOR_ACTION
POLICY_MANDATED_ESCALATION
LOW_VALUE_OF_ADDITIONAL_EVIDENCE
AWAITING_HUMAN_REVIEW
NO_MATERIAL_FRAUD_EVIDENCE
```

## Final Case Output

Must include:

- final risk,
- final confidence,
- final evidence completeness,
- hypotheses,
- evidence,
- next-best action,
- approval route,
- action results,
- SAR status,
- stop reason.

## AI Coding Prompt

```text
Implement Layer 23: case finalization.

Create deterministic finalization logic that:
- validates the case has a stop reason,
- validates next-best-action state,
- validates approval state where required,
- captures final risk/confidence/evidence completeness,
- records executed or simulated actions,
- records SAR/report status,
- generates final case summary data.

Do not close a case silently without a stop reason.
```

---

# 28. Layer 24 — Case Memory Writer

## Objective

Write the entire investigation back to TigerGraph.

## Graph Memory Must Include

- Case vertex,
- investigated entities,
- evidence,
- hypotheses/findings,
- decisions,
- actions,
- approvals,
- fraud-pattern matches,
- policy references,
- report reference,
- outcome,
- stop reason.

## Important

Case history should be append-oriented.

Do not overwrite previous recommendations when updated evidence changes the decision.

Preserve:

```text
pre_evidence_next_best_action
post_evidence_next_best_action
```

## AI Coding Prompt

```text
Implement Layer 24: TigerGraph case-memory writer.

Persist the complete investigation as graph-connected memory.

Requirements:
- create/update Case vertex,
- append Evidence vertices,
- append Decision and Action records,
- link approvals,
- link investigated transactions/accounts/devices,
- link matched fraud patterns,
- link relevant policy sections,
- store final outcome and stop reason,
- preserve recommendation history before and after additional evidence.

Do not replace historical events with the latest value only.
```

---

# 29. Layer 25 — Case Summary Embedding and Future Retrieval

## Objective

Make completed cases retrievable by future investigations.

## Tasks

1. Generate concise structured case summary.
2. Generate embedding locally.
3. Store vector.
4. Link summary to case vertex.
5. Make case available to hybrid retrieval.

## Case Summary Should Include

- trigger,
- important graph findings,
- fraud pattern,
- evidence,
- requested additional evidence,
- action,
- analyst decision,
- outcome.

## AI Coding Prompt

```text
Implement Layer 25: completed-case memory indexing.

For every finalized case:
- generate a concise factual case summary from verified state,
- create a local SentenceTransformer embedding,
- store it with the case,
- preserve graph links,
- expose it to future hybrid graph + vector retrieval.

Do not include hidden reasoning.
Do not summarize unsupported facts.
```

---

# 30. Layer 26 — Complete LangGraph Workflow

## Objective

Connect all implemented layers into one investigation state machine.

## Required Workflow

```text
START
→ validate_trigger
→ load_or_create_case
→ classify_trigger
→ persist_case_start
→ parallel_evidence_collection
→ normalize_evidence
→ calculate_features
→ optional_ml_score
→ main_reasoning
→ sufficiency_gate

If more evidence required:
  → record_pre_evidence_nba
  → evidence_planner
  → policy_check_for_evidence_request
  → request_evidence
  → ingest_evidence
  → normalize
  → recalculate
  → main_reasoning

If enough evidence:
  → determine_next_best_action
  → policy_gate
  → human_approval_if_required
  → execute_or_simulate
  → report_if_required
  → finalize
  → write_case_memory
  → embed_case_summary
  → END
```

## Safety Controls

- max evidence-gathering loops,
- node timeouts,
- state validation,
- error transitions,
- audit events.

## AI Coding Prompt

```text
Implement Layer 26: full LangGraph fraud investigation state machine.

Use the already implemented layers as nodes.

Requirements:
- one workflow for all cases,
- explicit branches,
- bounded evidence loops,
- human interrupt/resume,
- deterministic policy gate,
- state persistence,
- timeline event after every material transition,
- errors become controlled case events,
- no infinite ReAct loop,
- no direct raw LLM tool loop controlling the whole system.

Provide a Mermaid diagram matching the implementation.
```

---

# 31. Layer 27 — FastAPI Application Layer

## Objective

Expose the investigation system to the frontend locally.

## Required Endpoints

```text
POST /api/investigations
GET  /api/investigations/{case_id}
GET  /api/investigations/{case_id}/events
GET  /api/investigations/{case_id}/graph
GET  /api/investigations/{case_id}/evidence

POST /api/investigations/{case_id}/evidence
POST /api/investigations/{case_id}/approve
POST /api/investigations/{case_id}/reject
POST /api/investigations/{case_id}/modify-action

GET  /api/cases
GET  /api/cases/{case_id}

POST /api/mock/customer-confirmation
POST /api/mock/step-up-auth

POST /api/benchmark/run
```

## SSE Events

Examples:

```text
CASE_CREATED
EVIDENCE_COLLECTION_STARTED
TRANSACTION_ANALYSIS_COMPLETED
GRAPH_ANALYSIS_COMPLETED
POLICY_RETRIEVED
SIMILAR_CASES_RETRIEVED
EVIDENCE_NORMALIZED
FEATURES_CALCULATED
RISK_ASSESSED
MORE_EVIDENCE_REQUIRED
ACTION_RECOMMENDED
APPROVAL_REQUIRED
ACTION_EXECUTED
CASE_FINALIZED
```

## AI Coding Prompt

```text
Implement Layer 27: local FastAPI interface.

Expose typed REST APIs for:
- starting investigations,
- fetching cases,
- retrieving graph/evidence views,
- submitting evidence,
- approvals/rejections/modifications,
- mock customer/auth responses,
- benchmark execution.

Add SSE endpoint for investigation progress.

Requirements:
- Pydantic request/response models,
- proper HTTP status handling,
- no deployment configuration,
- no public authentication provider integration,
- local analyst identity may be mocked/configured,
- API must call services/LangGraph rather than business logic directly inside route handlers.
```

---

# 32. Layer 28 — Frontend Foundation

## Objective

Build the analyst dashboard shell.

## Pages

```text
/
cases
cases/[caseId]
```

## Core Components

- CaseQueue
- CaseHeader
- InvestigationTimeline
- FraudGraph
- EvidencePanel
- AssessmentPanel
- HypothesisPanel
- SimilarCasesPanel
- NextBestActionPanel
- ApprovalPanel
- PolicyPanel

## AI Coding Prompt

```text
Implement Layer 28: frontend foundation.

Use:
- Next.js,
- TypeScript,
- Tailwind,
- shadcn/ui.

Build:
- case queue page,
- case investigation page,
- responsive panel layout,
- shared typed API client,
- loading and error states.

Do not add graph rendering yet.
Do not add deployment.
Use mock data only where backend endpoints are not finished.
```

---

# 33. Layer 29 — Live Investigation Timeline via SSE

## Objective

Show agent progress in real time locally.

## Tasks

1. Connect browser to SSE endpoint.
2. Maintain timeline.
3. Reconnect safely.
4. Deduplicate events.
5. Show active step.
6. Show completed steps.
7. Show errors visibly.

## AI Coding Prompt

```text
Implement Layer 29: frontend SSE investigation timeline.

Connect to:
`GET /api/investigations/{case_id}/events`.

Render:
- timestamp,
- event type,
- concise message,
- status.

Requirements:
- reconnect safely,
- prevent duplicate events,
- visually distinguish running/completed/error/pending states,
- update the case header when final state changes,
- no WebSocket dependency.
```

---

# 34. Layer 30 — Fraud Graph Visualization

## Objective

Show why TigerGraph matters.

## Use Cytoscape.js

Display:

- current transaction,
- customer,
- account/card,
- devices,
- IPs,
- merchants,
- related accounts,
- historical fraud cases,
- evidence-linked nodes.

## Interactions

On node click show:

- node type,
- identifier,
- why relevant,
- evidence IDs,
- fraud-case links.

On edge click show:

- relationship type,
- supporting evidence.

## Visual Requirements

Distinguish:

- focal entity,
- normal entity,
- suspicious entity,
- prior confirmed-fraud-linked entity,
- case/evidence entities.

## AI Coding Prompt

```text
Implement Layer 30: Cytoscape.js fraud network visualization.

Input:
`GET /api/investigations/{case_id}/graph`.

Requirements:
- render customers/accounts/transactions/devices/IPs/merchants/cases,
- highlight focal entities,
- distinguish suspicious and prior-fraud-linked entities,
- show relationship type,
- node click opens a detail panel with evidence references,
- support fit-to-view and reset,
- avoid rendering huge unbounded graphs,
- keep graph readable for demo cases.
```

---

# 35. Layer 31 — Evidence and Assessment UI

## Objective

Make evidence and uncertainty understandable.

## Evidence Panel

Show:

- evidence ID,
- category,
- source,
- fact,
- reliability,
- supporting/contradicting direction.

## Assessment Panel

Show separately:

- Risk
- Confidence
- Evidence Completeness

Never merge them into one number.

## Hypotheses

Show:

- hypothesis,
- supporting evidence,
- contradicting evidence,
- missing evidence.

## AI Coding Prompt

```text
Implement Layer 31: evidence and assessment UI.

Build:
- EvidencePanel,
- AssessmentPanel,
- HypothesisPanel.

Requirements:
- every evidence card shows ID and provenance,
- distinguish graph-computed fact, retrieved policy, historical precedent, and model inference,
- show risk, confidence, and evidence completeness separately,
- hypotheses must show supporting and contradictory evidence references,
- missing evidence must be visible.
```

---

# 36. Layer 32 — Next-Best Action and Approval UI

## Objective

Clearly show before/after decisions and human control.

## Display

- preliminary recommendation,
- recommendation before evidence request,
- requested evidence,
- recommendation after evidence,
- policy basis,
- approval requirement,
- approver role,
- execution mode.

## Approval Actions

- APPROVE
- REJECT
- MODIFY

## AI Coding Prompt

```text
Implement Layer 32: next-best-action and approval UI.

Show:
- pre-evidence recommendation,
- requested evidence and why,
- post-evidence recommendation,
- policy reference,
- approval requirement,
- required role,
- simulated/executable status.

If approval is pending, show APPROVE, REJECT, MODIFY controls.

All controls must call the appropriate local FastAPI endpoints.
```

---

# 37. Layer 33 — Similar Cases and Policy UI

## Objective

Show memory and grounding visibly.

## Similar Cases Panel

Display:

- case ID,
- graph similarity,
- vector similarity,
- shared entities,
- pattern,
- historical outcome,
- historical action.

## Policy Panel

Display:

- policy section,
- relevance,
- action constraint,
- approval requirement.

## AI Coding Prompt

```text
Implement Layer 33: similar-case memory and policy panels.

SimilarCasesPanel:
- top relevant cases,
- graph overlap,
- vector similarity,
- shared entities,
- outcome,
- previous analyst action.

PolicyPanel:
- relevant policy section,
- policy source ID,
- concise retrieved text/summary,
- action constraints,
- approval requirements.

Make clear that historical cases are precedent and not proof.
```

---

# 38. Layer 34 — Local Audit Trail and Observability

## Objective

Make investigations traceable during development and demo.

## Record

- node start/end,
- graph query duration,
- retrieval duration,
- LLM model used,
- LLM latency,
- evidence count,
- policy decision,
- approval event,
- action event,
- errors.

## Output

Store locally under:

```text
outputs/traces/
```

Optional Langfuse can be enabled through a feature flag.

## AI Coding Prompt

```text
Implement Layer 34: local investigation tracing.

Create structured local audit logging for:
- LangGraph nodes,
- graph queries,
- GraphRAG retrieval,
- LLM calls,
- evidence counts,
- risk assessments,
- policy decisions,
- approvals,
- actions,
- errors.

Write JSONL or structured logs under `outputs/traces/`.

Add optional Langfuse integration behind a feature flag.

Do not add production monitoring or cloud deployment configuration.
```

---

# 39. Layer 35 — Unit Test Suite

## Objective

Test deterministic logic independently.

## Required Unit Tests

- data normalization,
- evidence normalization,
- feature engine,
- risk/sufficiency thresholds,
- policy engine,
- evidence planner,
- state validation,
- LLM structured-output parsing,
- Laya fallback behavior,
- action mocks.

## AI Coding Prompt

```text
Implement Layer 35: unit tests.

Use pytest.

Cover:
- evidence normalization,
- fraud feature calculations,
- policy engine,
- evidence sufficiency decisions,
- evidence planner ranking,
- state validation,
- action mocks,
- provider output parsing,
- fallback behavior.

Mock TigerGraph and LLM calls.
Unit tests must run without network access.
```

---

# 40. Layer 36 — Local Integration Tests

## Objective

Verify the complete local investigation pipeline.

## Required Scenarios

### Scenario 1 — Clear high-risk fraud

Expected:

- enough evidence,
- no unnecessary evidence request,
- blocking/escalation recommendation according to policy.

### Scenario 2 — High risk but uncertain

Expected:

- evidence request,
- pre-evidence NBA stored,
- customer response changes assessment,
- post-evidence NBA stored.

### Scenario 3 — Cleared activity

Expected:

- low/no material fraud evidence,
- case closes,
- cleared case stored as memory.

### Scenario 4 — Human approval

Expected:

- interrupt,
- resume after approve/reject/modify.

### Scenario 5 — SAR required

Expected:

- report generated only when policy says so.

### Scenario 6 — Provider failure

Expected:

- Groq error falls back to Gemini.

### Scenario 7 — Optional source failure

Expected:

- investigation continues.

## AI Coding Prompt

```text
Implement Layer 36: local integration tests.

Exercise the complete workflow using local/mocked inputs and a development TigerGraph graph.

Test at least:
1. clear fraud,
2. uncertain fraud requiring evidence,
3. legitimate/cleared case,
4. approval interruption,
5. SAR-required case,
6. Groq fallback,
7. optional evidence-source failure.

Assert state transitions, evidence IDs, policy gates, pre/post NBA storage, stop reason, and case-memory write.
```

---

# 41. Layer 37 — Benchmark Runner

## Objective

Run all 20 benchmark cases through the same workflow.

## Script

```text
python scripts/run_benchmark.py
```

## Per Case

1. load benchmark trigger,
2. create case,
3. run workflow,
4. handle permitted simulated evidence path,
5. generate final case result,
6. generate SAR when required,
7. verify graph write,
8. export exact answer file.

## Output Directory

```text
outputs/benchmark/
```

## Required Metadata

For each run store:

- case ID,
- start/end timestamp,
- workflow status,
- errors,
- answer-file path,
- graph-write verification.

## AI Coding Prompt

```text
Implement Layer 37: benchmark runner.

Run all 20 provided benchmark cases through the exact same LangGraph investigation workflow.

Requirements:
- no hardcoded benchmark answer logic,
- no benchmark label leakage,
- deterministic case IDs/output names,
- generate one answer file per case in the exact README-required format,
- include pre-evidence and post-evidence next-best action when applicable,
- include approval route,
- include SAR when required,
- verify the case exists in TigerGraph after completion,
- produce a run summary JSON.
```

---

# 42. Layer 38 — Benchmark Output Validator

## Objective

Catch submission-format failures.

## Validate

Each answer has:

- case,
- internal investigation record,
- evidence,
- findings,
- decisions,
- actions,
- pre-evidence NBA,
- requested evidence when applicable,
- post-evidence NBA,
- approval route,
- SAR when required,
- final status,
- stop reason.

## AI Coding Prompt

```text
Implement Layer 38: benchmark output validator.

Read the exact answer format from the dataset README.

Validate every generated benchmark answer file.

Fail with precise messages when:
- required fields are missing,
- evidence IDs are broken,
- pre/post NBA requirements are violated,
- approval route is missing,
- SAR-required output is missing,
- stop reason is missing,
- case graph-write verification failed.

Do not silently auto-correct semantic decisions.
```

---

# 43. Layer 39 — Evaluation Harness Using Historical Cases

## Objective

Measure quality without using benchmark truth.

## Evaluate

When historical ground truth permits:

- fraud/cleared performance,
- fraud-pattern identification,
- action agreement where historical action exists,
- evidence request rate,
- unnecessary evidence requests,
- retrieval relevance,
- graph query latency,
- LLM latency,
- total case latency.

## Ablation Modes

Run:

```text
A. bank risk score only
B. bank score + behavior
C. graph + behavior
D. graph + behavior + case memory + policy GraphRAG
```

## AI Coding Prompt

```text
Implement Layer 39: historical evaluation harness.

Use only historical resolved cases allowed for evaluation.

Measure:
- fraud/cleared classification metrics where valid,
- pattern identification where labels exist,
- next-action agreement where historical decisions exist,
- evidence-request frequency,
- graph retrieval latency,
- LLM latency.

Also run ablations:
A risk score only,
B risk + behavior,
C graph + behavior,
D graph + behavior + memory + policy GraphRAG.

Do not evaluate against hidden benchmark outcomes.
```

---

# 44. Layer 40 — Demo Scenario Preparation

## Objective

Prepare deterministic local demo cases.

## Required Demo Scenarios

### Demo 1 — Fraud Network

Show:

- shared device,
- related accounts,
- prior fraud case,
- graph path,
- strong action.

### Demo 2 — Uncertain Case

Show:

- initial uncertainty,
- pre-evidence recommendation,
- evidence request,
- customer confirmation/denial,
- changed recommendation.

### Demo 3 — Human Approval

Show:

- sensitive action,
- policy requirement,
- analyst approval,
- final action.

## AI Coding Prompt

```text
Implement Layer 40: local deterministic demo scenarios.

Prepare local demo fixtures for:
1. graph-detected fraud ring,
2. uncertain case that requests evidence and changes recommendation,
3. human approval case.

Requirements:
- use the real investigation workflow,
- no special demo-only decision logic,
- allow deterministic simulated customer/auth/analyst responses,
- create a short demo script describing what to click and what evidence should appear.

Do not add deployment or public hosting.
```

---

# 45. Recommended Build Order

Do not ask an AI coding agent to implement everything at once.

Use this order.

## Stage A — Data + Graph Foundation

```text
Layer 0
Layer 1
Layer 2
Layer 3
Layer 4
Layer 5
Layer 6
```

Checkpoint:

```text
Can I give the system a transaction ID and retrieve meaningful TigerGraph fraud evidence?
```

If no, stop and fix the graph.

---

## Stage B — Retrieval + Evidence

```text
Layer 7
Layer 8
Layer 9
Layer 10
Layer 11
Layer 12
```

Checkpoint:

```text
Can one case produce a normalized evidence bundle from transaction, graph, policy, prior cases, and device analysis?
```

---

## Stage C — Reasoning + Control

```text
Layer 15
Layer 16
Layer 17
Layer 18
Layer 19
Layer 20
Layer 21
Layer 22
Layer 23
Layer 24
Layer 25
Layer 26
```

Optional after core works:

```text
Layer 13 LightGBM
Layer 14 Laya
```

Checkpoint:

```text
Can one case go from trigger to final action, including an uncertainty loop and human approval?
```

---

## Stage D — API + UI

```text
Layer 27
Layer 28
Layer 29
Layer 30
Layer 31
Layer 32
Layer 33
Layer 34
```

Checkpoint:

```text
Can an analyst start and inspect a case entirely through the local UI?
```

---

## Stage E — Quality + Submission

```text
Layer 35
Layer 36
Layer 37
Layer 38
Layer 39
Layer 40
```

Checkpoint:

```text
Can all 20 benchmark cases execute and produce valid output files using the same workflow?
```

---

# 46. AI Model Working Protocol

Use this instruction before every layer-specific prompt when working with an AI coding model.

```text
You are working inside an existing TigerGraph agentic fraud investigation codebase.

Before writing code:

1. Inspect the repository.
2. Read `docs/project_description.md`.
3. Read `docs/layer_by_layer_implementation.md`.
4. Read the dataset mapping when the task depends on dataset fields.
5. Inspect existing interfaces and do not duplicate them.
6. Preserve the fixed technology choices.
7. Do not introduce new frameworks without necessity.
8. Do not implement future layers unless needed for an interface stub.
9. Keep code typed and testable.
10. Do not invent dataset fields.
11. Do not hardcode benchmark results.
12. Do not add cloud deployment, live hosting, CI/CD deployment, or public infrastructure.
13. Add or update tests for the layer.
14. At completion report:
    - files created,
    - files modified,
    - assumptions,
    - tests run,
    - unresolved blockers,
    - exact next layer that is now unblocked.

Implement only the requested layer.
```

---

# 47. Definition of Done for the Entire Local Project

The local implementation is complete when:

1. The dataset is processed reproducibly.
2. TigerGraph schema is created from real dataset fields.
3. Historical data and cases load successfully.
4. GSQL queries return meaningful fraud evidence.
5. TigerGraph MCP provides controlled graph access.
6. GraphRAG retrieves policy, typology, regulation, and historical cases.
7. Evidence is normalized and provenance-preserving.
8. Graph features are calculated deterministically.
9. Groq performs structured evidence reasoning.
10. Gemini fallback works.
11. Laya is optional and limited to fast classification.
12. LightGBM is optional and used only as a supporting signal.
13. Risk, confidence, and evidence completeness remain separate.
14. Uncertain cases request additional evidence.
15. Pre-evidence NBA is recorded.
16. New evidence triggers reassessment.
17. Post-evidence NBA is recorded.
18. Policy engine controls authorization.
19. Sensitive actions trigger human approval.
20. Actions are simulated locally.
21. SAR/report is generated when policy requires it.
22. Every case has an explicit stop reason.
23. Complete case history is written to TigerGraph.
24. Completed cases become future case memory.
25. Frontend displays graph, evidence, hypotheses, risk, confidence, policy, similar cases, timeline, and next action.
26. SSE shows investigation progress.
27. Local tests cover all major branches.
28. All 20 benchmark cases run through one workflow.
29. Output validation passes.
30. Demo scenarios work deterministically.

At this point, the project is ready for benchmark submission preparation and demo recording without requiring any additional deployment layer.
