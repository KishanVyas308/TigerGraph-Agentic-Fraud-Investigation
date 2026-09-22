# AGENT.md — TigerGraph Agentic Fraud Investigation

## 1. Purpose

This file is the operating contract for any AI coding agent working on this repository.

The project is a TigerGraph-first agentic fraud investigation system for the HHGOA hackathon.

The agent must build and modify the codebase according to:

- `docs/project_description.md`
- `docs/layer_by_layer_implementation.md`
- `docs/dataset_mapping.md` when available
- the dataset README, which is the authoritative source for dataset meaning and benchmark format

This file defines:

- architecture constraints,
- implementation rules,
- coding expectations,
- fraud-investigation requirements,
- benchmark safety rules,
- testing requirements,
- repository working protocol,
- completion reporting.

The AI coding agent must treat this file as higher priority than convenience or personal architectural preference.

---

# 2. Core Objective

Build one reusable fraud investigation engine that can:

1. accept a fraud trigger,
2. create or resume a fraud case,
3. gather evidence from TigerGraph and GraphRAG,
4. calculate deterministic graph and transaction features,
5. retrieve similar historical cases,
6. retrieve relevant policy and regulatory context,
7. assess risk, confidence, and evidence completeness,
8. determine whether more evidence is required,
9. request additional evidence when needed,
10. update the case after new evidence,
11. recommend the next-best action,
12. enforce deterministic policy and approval rules,
13. execute or simulate permitted actions,
14. generate SAR/report output when required,
15. stop for an explicit reason,
16. persist the complete case back to TigerGraph,
17. make completed cases available as future case memory,
18. run all 20 benchmark cases through the same workflow.

---

# 3. Fixed Technology Choices

Do not replace these technologies unless the repository owner explicitly changes the architecture.

## Backend

- Python 3.11+
- FastAPI
- Pydantic v2
- asyncio

## Agent Orchestration

- LangGraph

## Graph Platform

- TigerGraph Savanna or TigerGraph Community Edition for local development

## Graph Query Language

- GSQL

## Agent-to-Graph Integration

- TigerGraph MCP

## GraphRAG

- TigerGraph GraphRAG

## Main LLM

- Groq SDK
- primary: `openai/gpt-oss-120b`
- fast model: `openai/gpt-oss-20b`

## LLM Fallback

- Gemini Flash

## Optional Fast Classifier

- ConvAI Innovations Laya

## Optional Historical ML Signal

- LightGBM

## Embeddings

- SentenceTransformers

## Data Processing

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

## Local Testing

- pytest
- frontend type checking / linting

---

# 4. Explicitly Excluded Technologies

Do not introduce these unless the repository owner explicitly requests them:

- CrewAI
- Hermes as a second orchestration framework
- Pinecone
- Qdrant
- Weaviate
- Chroma
- Neo4j
- OpenSearch as a separate retrieval layer
- Open Policy Agent
- SageMaker pipelines
- multiple agent frameworks
- multiple vector databases

The project intentionally uses a focused stack.

---

# 5. Deployment Restrictions

Do not implement deployment or public infrastructure unless explicitly requested later.

This repository should currently stop at:

- local development,
- local TigerGraph integration,
- local backend,
- local frontend,
- local benchmark execution,
- local evaluation,
- local demo preparation.

Do not add:

- cloud deployment scripts,
- Terraform,
- Kubernetes,
- public DNS,
- production load balancers,
- production CI/CD deployment,
- public hosting configuration,
- production secrets managers,
- live-bank integrations.

AWS may be referenced in project documentation, but implementation work must remain local unless the user explicitly changes this rule.

---

# 6. Dataset Rules

## 6.1 Dataset README Is Authoritative

Before touching graph schema, model features, benchmark logic, or output format:

1. read the dataset README,
2. read `docs/dataset_mapping.md`,
3. inspect relevant source files.

Do not guess field meanings.

## 6.2 No Invented Fields

Do not create fields such as:

```text
is_fraud
fraud_label
ground_truth_fraud
```

unless they actually exist in a permitted historical dataset source.

The bank risk score is a signal only.

It is not ground truth.

## 6.3 Benchmark Leakage Is Forbidden

Never:

- inspect hidden benchmark outcomes,
- infer benchmark truth from submission artifacts,
- tune logic to individual benchmark case IDs,
- hardcode benchmark answers,
- train on final benchmark outcomes,
- branch logic based on benchmark case number.

Every benchmark case must run through the same normal investigation workflow.

## 6.4 Historical Cases

Historical resolved cases may be used when the dataset permits.

Use them for:

- similar-case retrieval,
- historical pattern learning,
- LightGBM training,
- analyst-decision memory,
- cleared-case precedent,
- fraud-case precedent.

Historical cases are precedent, not proof.

---

# 7. Core Architectural Principle

The system must preserve clear responsibility boundaries.

## TigerGraph

Responsible for:

- entity relationships,
- transaction graph,
- fraud-network structure,
- historical cases,
- case memory,
- evidence relationships,
- graph traversal,
- graph algorithms,
- vector-backed graph retrieval.

## GSQL

Responsible for:

- deterministic graph facts,
- fraud-network features,
- bounded traversal,
- transaction behavior summaries,
- device sharing,
- IP sharing,
- fraud-neighbor detection,
- graph paths,
- connected components,
- money-flow patterns.

## GraphRAG

Responsible for:

- fraud policy retrieval,
- fraud typology retrieval,
- regulatory retrieval,
- similar historical case retrieval,
- graph + vector hybrid context.

## Laya

Responsible only for fast, cheap classification such as:

- trigger type,
- customer response classification,
- analyst response classification.

Laya must not:

- make final fraud decisions,
- decide policy,
- decide account blocking,
- vote over every evidence item,
- replace the main reasoning model.

## LightGBM

Responsible only for an optional historical risk signal.

It must not be presented as final truth.

Use the field:

```text
historical_ml_score
```

Do not call it a calibrated fraud probability unless calibration is actually implemented and validated.

## Main LLM

Responsible for:

- evidence synthesis,
- competing hypotheses,
- uncertainty assessment,
- structured reasoning,
- identifying missing evidence,
- proposing next-best actions,
- concise explanation.

The LLM must not fabricate graph facts.

## LangGraph

Responsible for:

- investigation stage,
- branch control,
- state progression,
- evidence loops,
- human interrupts,
- stopping rules,
- workflow consistency.

## Policy Engine

Responsible for:

- whether an action is allowed,
- whether autonomous execution is allowed,
- whether approval is required,
- approval role,
- action prerequisites,
- SAR/report requirement.

The LLM cannot override the policy engine.

---

# 8. Required Runtime Flow

The implementation must preserve this conceptual flow:

```text
Trigger
→ Validate Request
→ Create / Resume FraudCaseState
→ Optional Fast Trigger Classification
→ Create / Open Case in TigerGraph
→ Parallel Evidence Collection
→ Evidence Normalization
→ Graph Feature Calculation
→ Risk Signal Calculation
→ Main LLM Reasoning
→ Evidence Sufficiency Gate

If insufficient evidence:
    → Record current next-best action
    → Select highest-value missing evidence
    → Policy-check evidence request
    → Request evidence
    → Receive evidence
    → Normalize
    → Recalculate
    → Reassess

If sufficient evidence:
    → Determine next-best action
    → Deterministic policy gate
    → Human approval if required
    → Execute or simulate action
    → Generate SAR/report if required
    → Finalize case
    → Write complete case to TigerGraph
    → Create case summary embedding
    → Make case available to future investigations
```

Do not replace this with an unbounded autonomous ReAct loop.

---

# 9. Parallel Evidence Collection

Independent baseline evidence branches should run concurrently.

Use `asyncio.gather()` or equivalent.

Required branches:

## A. Transaction Analysis

Retrieve or calculate:

- current transaction context,
- transaction amount,
- historical mean/median,
- recent transaction counts,
- velocity,
- merchant novelty,
- timing anomalies,
- amount anomalies.

## B. Graph Relationship Analysis

Retrieve or calculate:

- bounded neighborhood,
- shared devices,
- shared IPs,
- fraud-linked neighbors,
- shortest path to historical fraud-linked entities,
- connected cluster,
- suspicious fan-in,
- suspicious fan-out,
- circular movement,
- rapid pass-through if supported.

## C. Policy GraphRAG

Retrieve:

- relevant fraud policy,
- relevant fraud typology,
- regulatory guidance,
- action restrictions,
- approval requirements.

## D. Historical Case Memory

Retrieve:

- top graph-similar cases,
- top vector-similar cases,
- shared entities,
- historical outcomes,
- prior analyst decisions,
- prior actions.

Include both fraud-confirmed and cleared cases where relevant.

## E. Device and Identity Analysis

Retrieve:

- new device status,
- device first-seen time,
- linked accounts,
- linked customers,
- prior fraud-case links,
- shared identity attributes,
- new/shared IP behavior.

## F. Optional External/Internal Signals

Examples:

- authentication result,
- mock CRM information,
- device reputation,
- IP reputation.

Failure of an optional source must not fail the entire investigation.

---

# 10. Evidence Contract

Every tool result must be normalized before reaching the reasoning model.

Use a canonical evidence model.

Required fields:

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

Possible categories:

```text
TRANSACTION_BEHAVIOR
GRAPH_RELATIONSHIP
DEVICE
IDENTITY
MONEY_FLOW
HISTORICAL_CASE
POLICY
REGULATION
CUSTOMER_RESPONSE
AUTHENTICATION
ANALYST_INPUT
EXTERNAL_SIGNAL
```

Evidence normalization must not make the final fraud decision.

It only transforms and standardizes facts.

---

# 11. Evidence Provenance

Every material fact must be traceable to a source.

Examples:

```text
TIGERGRAPH_GSQL
TIGERGRAPH_GRAPH_TRAVERSAL
POLICY_GRAPHRAG
CASE_MEMORY
CUSTOMER_RESPONSE
AUTHENTICATION_SERVICE
ANALYST_INPUT
EXTERNAL_SIGNAL
```

Never generate evidence with an unknown source.

Policy text must remain identifiable as policy evidence.

Historical case information must remain identifiable as historical precedent.

Model inference must remain identifiable as model inference.

---

# 12. Graph Feature Engine

Fraud features should be deterministic.

Implement when supported by the dataset:

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

Rules:

- use `None`/null when unavailable,
- never invent zero values for unavailable data,
- provide human-readable feature explanations,
- write unit tests.

---

# 13. Risk Model Requirements

Risk, confidence, and evidence completeness are separate.

## Risk

How suspicious or harmful the activity appears.

Example:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

## Confidence

How certain the system is about its current assessment.

## Evidence Completeness

Whether enough evidence exists to take a defensible action.

Do not collapse these into one score.

Examples:

```text
HIGH risk
LOW confidence
LOW completeness
→ gather more evidence
```

```text
HIGH risk
HIGH confidence
HIGH completeness
→ act, subject to policy
```

```text
LOW risk
HIGH confidence
HIGH completeness
→ allow / no action / close according to policy
```

---

# 14. Main LLM Output Contract

The main reasoning model must return structured output.

Required fields:

```text
hypotheses
supporting_evidence_ids
contradictory_evidence_ids
risk_level
risk_score
confidence
evidence_completeness
missing_evidence
preliminary_next_best_action
explanation
```

Rules:

1. Every material assertion must reference evidence IDs.
2. No unsupported fraud conclusion.
3. Prior cases are precedent, not proof.
4. Contradictory evidence must be represented.
5. Missing evidence must be explicit.
6. Do not expose hidden chain-of-thought.
7. Explanation should be concise and auditable.
8. Never fabricate policy.
9. Never fabricate transaction facts.
10. Never fabricate graph relationships.

---

# 15. Evidence Sufficiency Rules

The sufficiency gate must not be controlled by LLM intuition alone.

It should use:

- risk,
- confidence,
- evidence completeness,
- missing evidence,
- action severity,
- policy constraints,
- iteration count.

Valid outcomes:

```text
ACT
GATHER_MORE_EVIDENCE
ESCALATE
STOP_NO_MATERIAL_FRAUD
```

Thresholds must be configurable.

Evidence gathering loops must be bounded.

---

# 16. Evidence Planner Rules

When more evidence is needed, select the smallest useful evidence request.

Possible types:

```text
CUSTOMER_CONFIRMATION
STEP_UP_AUTH
ANALYST_INFORMATION
APPROVED_EXTERNAL_CHECK
```

Use an explainable approximation of value of information:

```text
expected uncertainty reduction
× expected decision impact
÷ cost / friction / latency
```

Before requesting additional evidence:

1. store the current next-best action,
2. store why evidence is insufficient,
3. store what evidence is being requested,
4. store what decision the evidence could change.

After evidence arrives:

1. normalize it,
2. recalculate features,
3. reassess,
4. store the updated next-best action.

Never overwrite the pre-evidence recommendation.

---

# 17. Supported Action Categories

Use typed enums.

Possible actions include:

```text
ALLOW_TRANSACTION
BLOCK_TRANSACTION
MONITOR_TRANSACTION
MONITOR_ACCOUNT
BLOCK_ACCOUNT
WARN_CUSTOMER
REQUEST_CUSTOMER_CONFIRMATION
REQUEST_STEP_UP_AUTH
REQUEST_ANALYST_EVIDENCE
ESCALATE_ANALYST
FILE_SAR
CLOSE_CASE
NO_ACTION
```

The actual enabled set must come from the hackathon policy.

Do not invent autonomous privileges.

---

# 18. Policy Engine Rules

Use deterministic code and `policy.yaml`.

For every action, determine:

```text
allowed
autonomous
approval_required
approval_role
report_required
unmet_prerequisites
policy_reference
```

The LLM recommends.

The policy engine authorizes.

If the LLM recommends a disallowed action:

1. reject it,
2. record the reason,
3. return to action selection or safe alternative logic.

Never allow the LLM to bypass the policy engine.

---

# 19. Human Approval Rules

Sensitive actions use LangGraph interrupt/resume semantics.

Supported analyst decisions:

```text
APPROVE
REJECT
MODIFY
```

On APPROVE:

- continue with approved action.

On REJECT:

- record rejection and reason,
- return to action selection.

On MODIFY:

- record modified action,
- run modified action through policy validation again.

All approval events must remain in the case timeline.

---

# 20. Mock Action Rules

The hackathon permits simulated actions.

Mocks must be clearly labeled:

```text
execution_mode = SIMULATED
```

Mock services may represent:

- transaction block,
- transaction allow,
- account monitoring,
- account freeze/block,
- customer warning,
- customer transaction confirmation,
- step-up authentication,
- analyst escalation,
- CRM update,
- report filing.

Never imply that a mock changed a real bank system.

---

# 21. SAR / Report Rules

Generate SAR/report output only when policy requires it.

The generator must use verified case evidence only.

Never invent:

- customer facts,
- amounts,
- transaction dates,
- identity information,
- regulatory requirements,
- policy references.

The report structure must follow the dataset README.

If a required field is unavailable, represent that according to the required output format rather than inventing it.

---

# 22. Stop Conditions

Every completed or paused investigation must have an explicit stop reason.

Allowed stop reasons include:

```text
SUFFICIENT_EVIDENCE_FOR_ACTION
POLICY_MANDATED_ESCALATION
LOW_VALUE_OF_ADDITIONAL_EVIDENCE
AWAITING_HUMAN_REVIEW
NO_MATERIAL_FRAUD_EVIDENCE
```

Do not silently end a case.

---

# 23. Case Memory Requirements

The final case must be persisted to TigerGraph.

Persist:

- case,
- trigger,
- investigated entities,
- evidence,
- graph findings,
- hypotheses,
- matched patterns,
- decisions,
- actions,
- approvals,
- policy references,
- requested evidence,
- received evidence,
- pre-evidence next-best action,
- post-evidence next-best action,
- SAR/report reference,
- outcome,
- stop reason.

Case history must be append-oriented.

Never erase earlier recommendations when the recommendation changes.

---

# 24. Future Case Memory Retrieval

Completed cases must support:

## Graph Similarity

Examples:

- shared device,
- shared IP,
- same merchant,
- same account,
- same identity attribute,
- same fraud network,
- similar structural topology.

## Vector Similarity

Use embeddings over concise case summaries.

Retrieve only top relevant cases.

Do not dump all historical cases into the LLM.

---

# 25. GSQL Requirements

Prefer installed GSQL queries.

Expected query library:

```text
get_transaction_context
get_transaction_behavior
get_entity_neighborhood
find_shared_devices
find_shared_ips
find_fraud_neighbors
get_shortest_path_to_fraud
detect_money_flow_patterns
get_connected_cluster
get_device_identity_context
find_similar_graph_cases
get_case_timeline
write_case_update
```

Rules:

- bounded traversal,
- bounded result count,
- deterministic output,
- machine-readable responses,
- no unbounded graph dumps,
- comments for non-obvious logic.

---

# 26. LangGraph Requirements

The investigation workflow must be explicit.

Expected nodes:

```text
validate_trigger
load_or_create_case
classify_trigger
persist_case_start
parallel_evidence_collection
normalize_evidence
calculate_features
optional_ml_score
main_reasoning
sufficiency_gate
record_pre_evidence_nba
evidence_planner
policy_check_for_evidence_request
request_evidence
ingest_evidence
determine_next_best_action
policy_gate
human_approval
execute_or_simulate
report_if_required
finalize
write_case_memory
embed_case_summary
```

Rules:

- bounded loops,
- explicit transitions,
- state validation,
- timeline event after every material transition,
- no infinite tool-use loop,
- no single giant node that does everything.

---

# 27. Frontend Requirements

The frontend is an analyst dashboard.

Required views:

## Case Queue

Show:

- case ID,
- trigger,
- risk,
- confidence,
- status,
- created time.

## Investigation View

Show:

- case header,
- fraud graph,
- evidence panel,
- assessment,
- hypotheses,
- similar cases,
- policy,
- next-best action,
- approval controls,
- investigation timeline.

## Graph Visualization

Use Cytoscape.js.

Display:

- customer,
- account/card,
- transaction,
- devices,
- IPs,
- merchants,
- related accounts,
- historical cases.

Keep graph bounded and readable.

## Evidence UI

Every evidence card shows:

- evidence ID,
- source,
- category,
- fact,
- reliability.

## Assessment UI

Always show separately:

- risk,
- confidence,
- evidence completeness.

## Next-Best Action UI

Show:

- pre-evidence recommendation,
- evidence requested,
- post-evidence recommendation,
- policy basis,
- approval route,
- execution mode.

---

# 28. SSE Requirements

Use Server-Sent Events for investigation progress.

Example events:

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

Frontend must:

- reconnect safely,
- deduplicate events,
- show running/completed/error state.

---

# 29. API Design Rules

FastAPI routes should remain thin.

Routes call services.

Services call:

- LangGraph,
- TigerGraph access layer,
- policy engine,
- action services.

Do not put business logic directly inside route handlers.

Expected endpoints:

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

---

# 30. Coding Standards

## Python

Use:

- type hints everywhere,
- Pydantic models at boundaries,
- dataclasses only when appropriate,
- enums for controlled values,
- async for I/O,
- pure functions for deterministic logic.

Avoid:

- global mutable state,
- massive service classes,
- hidden side effects,
- untyped dictionaries at major boundaries,
- business logic in routes.

## TypeScript

Use:

- strict TypeScript,
- shared API types,
- small focused components,
- predictable state handling.

Avoid:

- `any`,
- duplicated backend type definitions where generated/shared types are practical,
- giant page components.

---

# 31. Error Handling Rules

Errors must be explicit and typed where practical.

Distinguish:

- input validation error,
- graph query failure,
- GraphRAG retrieval failure,
- optional source failure,
- LLM provider failure,
- policy violation,
- approval rejection,
- action execution failure,
- benchmark output validation failure.

Optional evidence-source failure should not fail the whole case.

Critical graph failures should produce a controlled investigation error state.

Never swallow exceptions silently.

---

# 32. Logging Rules

Record structured local logs for:

- case ID,
- node name,
- start/end timestamp,
- graph query duration,
- retrieval duration,
- LLM provider/model,
- LLM latency,
- evidence count,
- policy decision,
- approval result,
- action result,
- stop reason,
- errors.

Do not log secrets.

Do not log API keys.

---

# 33. Testing Rules

Every new deterministic component must have tests.

## Unit Tests

Required for:

- preprocessing,
- evidence normalization,
- graph feature calculation,
- risk/sufficiency logic,
- policy engine,
- evidence planner,
- state validation,
- provider parsing,
- mock actions.

Unit tests must not require network access.

## Integration Tests

Required scenarios:

1. clear high-risk fraud,
2. high-risk uncertain case,
3. legitimate/cleared case,
4. approval interrupt,
5. SAR-required case,
6. Groq fallback,
7. optional evidence-source failure.

## Benchmark Tests

All 20 benchmark cases must:

- run through the same workflow,
- produce one answer file each,
- write case memory to TigerGraph,
- pass output validation.

---

# 34. Benchmark Output Requirements

Each benchmark answer must include the exact fields required by the dataset README.

At minimum the system architecture supports:

- case details,
- internal investigation record,
- evidence,
- findings,
- fraud hypotheses,
- matched patterns,
- policy context,
- similar historical cases,
- risk,
- confidence,
- evidence completeness,
- missing evidence,
- next-best action before additional evidence,
- requested evidence,
- received evidence,
- next-best action after evidence,
- approval route,
- actions,
- SAR/report where required,
- final status,
- stop reason.

Do not change submission format based on preference.

Follow the dataset README exactly.

---

# 35. Build Order

Implement in this order.

## Stage A — Data + Graph

1. repository bootstrap
2. dataset inspection
3. preprocessing
4. TigerGraph schema
5. loading jobs
6. GSQL query library
7. TigerGraph/MCP client

Do not proceed if transaction IDs cannot produce meaningful graph evidence.

## Stage B — Retrieval + Evidence

8. embeddings
9. GraphRAG
10. case state
11. evidence model
12. parallel evidence collection
13. graph feature engine

Do not proceed if one case cannot produce a clean normalized evidence bundle.

## Stage C — Reasoning + Controls

14. LLM router
15. main reasoning
16. evidence sufficiency
17. evidence planner
18. policy engine
19. human approval
20. mock actions
21. report generation
22. case finalizer
23. case memory
24. case embedding
25. complete LangGraph workflow

Optional only after core works:

- LightGBM
- Laya

## Stage D — API + UI

26. FastAPI
27. frontend shell
28. SSE timeline
29. graph visualization
30. evidence UI
31. action/approval UI
32. similar cases/policy UI
33. local traces

## Stage E — Quality

34. unit tests
35. integration tests
36. benchmark runner
37. output validator
38. historical evaluation
39. demo fixtures

---

# 36. Work Protocol for Every Coding Task

Before changing code:

1. inspect the repository,
2. read this file,
3. read `docs/project_description.md`,
4. read `docs/layer_by_layer_implementation.md`,
5. read `docs/dataset_mapping.md` if data fields matter,
6. inspect existing interfaces,
7. identify the requested layer,
8. identify dependencies already implemented,
9. identify tests that need updating.

Then implement only the requested scope.

Do not implement future layers unless a minimal interface stub is required.

---

# 37. AI Agent Task Execution Rules

When given a task:

## First

State internally:

- requested layer,
- affected files,
- dependencies,
- assumptions.

## Then

Inspect before editing.

Do not recreate modules that already exist.

Prefer extending existing abstractions.

## During Implementation

Keep interfaces stable.

If an interface must change:

1. update all callers,
2. update tests,
3. document the change.

## At Completion

Report:

```text
Implemented:
- ...

Files created:
- ...

Files modified:
- ...

Tests added:
- ...

Tests run:
- ...

Assumptions:
- ...

Known limitations:
- ...

Next unblocked layer:
- ...
```

Do not claim tests passed unless they were actually run.

---

# 38. Rules for AI-Generated Code

The coding agent must not:

- add placeholder fake fraud decisions,
- hardcode benchmark IDs,
- return random scores,
- silently mock core TigerGraph behavior,
- fabricate policy rules,
- silently replace failed graph analysis with LLM guessing,
- create unbounded graph queries,
- build a chatbot instead of an investigation workflow,
- hide missing evidence,
- collapse all logic into one prompt,
- expose destructive TigerGraph tools to runtime agent,
- introduce an unrelated framework.

---

# 39. Required Local Demo Behavior

The final local demo must support at least three deterministic scenarios.

## Demo A — Fraud Ring

Show:

- suspicious transaction,
- graph expansion,
- shared device/IP,
- prior fraud-linked accounts,
- strong graph evidence,
- action recommendation.

## Demo B — Uncertain Case

Show:

- high risk,
- low confidence,
- missing evidence,
- pre-evidence NBA,
- evidence request,
- customer/auth response,
- updated risk,
- post-evidence NBA.

## Demo C — Human Approval

Show:

- sensitive recommendation,
- policy requirement,
- approval interrupt,
- analyst approval/rejection/modification,
- final case update.

All demo scenarios must use the real workflow.

No demo-only decision engine.

---

# 40. Definition of Done

The project is locally complete when:

1. dataset processing is reproducible,
2. graph schema matches actual data,
3. TigerGraph loads successfully,
4. GSQL returns meaningful fraud evidence,
5. MCP access is controlled,
6. GraphRAG retrieves policy and case memory,
7. evidence is normalized with provenance,
8. graph features are deterministic,
9. main LLM returns structured grounded assessments,
10. risk/confidence/completeness remain separate,
11. uncertain cases request more evidence,
12. pre-evidence NBA is stored,
13. new evidence causes reassessment,
14. post-evidence NBA is stored,
15. policy engine controls actions,
16. sensitive actions require approval,
17. actions are simulated locally,
18. SAR/report is generated when required,
19. every case has a stop reason,
20. complete case memory is written to TigerGraph,
21. completed cases are retrievable in future investigations,
22. UI shows graph/evidence/risk/hypotheses/policy/actions/timeline,
23. SSE shows investigation progress,
24. tests cover all main branches,
25. all 20 benchmark cases use one workflow,
26. all benchmark outputs pass validation,
27. demo scenarios run deterministically.

---

# 41. One-Sentence Architectural Rule

When uncertain about where logic belongs, use this rule:

> TigerGraph discovers relationships, GSQL computes fraud facts, GraphRAG retrieves knowledge and precedent, LightGBM contributes an optional historical signal, Laya performs cheap classification, the main LLM reasons over grounded evidence, LangGraph controls the investigation lifecycle, and the deterministic policy engine controls what the system is allowed to do.

