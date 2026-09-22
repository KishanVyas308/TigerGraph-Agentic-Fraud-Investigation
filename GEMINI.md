# GEMINI.md — Google Antigravity Working Instructions

## Purpose

This file provides Google Antigravity with the project-specific instructions needed to work safely and consistently inside this repository.

The primary engineering contract for this project is:

- `AGENTS.md`

The primary architecture and implementation references are:

- `docs/project_description.md`
- `docs/layer_by_layer_implementation.md`
- `docs/dataset_mapping.md` once Layer 1 is complete
- the dataset README, which is authoritative for dataset fields, benchmark cases, policies, and submission format

Antigravity must treat these files as the source of truth before making code changes.

---

# 1. Project

This repository contains the:

**TigerGraph Agentic Fraud Investigation Agent — HHGOA**

The system investigates fraud using:

- TigerGraph
- GSQL
- TigerGraph MCP
- TigerGraph GraphRAG
- LangGraph
- Groq
- Gemini fallback
- optional Laya
- optional LightGBM
- FastAPI
- Next.js

The objective is to create one reusable investigation workflow that can:

1. receive a fraud trigger,
2. create or resume a case,
3. gather graph and transaction evidence,
4. retrieve fraud policies and similar historical cases,
5. calculate fraud features,
6. assess risk, confidence, and evidence completeness,
7. request additional evidence when required,
8. recommend the next-best action,
9. enforce policy and approval requirements,
10. simulate permitted actions,
11. write the full case back into TigerGraph,
12. reuse completed cases as future investigation memory,
13. process all 20 benchmark cases using the same workflow.

---

# 2. Required Reading Before Editing

Before making any code change:

1. Read `AGENTS.md`.
2. Read `docs/project_description.md`.
3. Read `docs/layer_by_layer_implementation.md`.
4. Read `CURRENT_TASK.md`.
5. Read `IMPLEMENTATION_STATUS.md`.
6. If the task depends on dataset fields, read `docs/dataset_mapping.md`.
7. If the dataset mapping is not yet available, read the original dataset README and inspect the relevant raw files.
8. Inspect the existing repository implementation before creating new modules.

Do not begin implementation until the required context has been inspected.

---

# 3. Current Task Rule

`CURRENT_TASK.md` defines the only active implementation scope.

Implement only the active task.

Do not automatically implement the next layer.

Do not jump ahead because a later feature appears easy.

If a future layer requires a minimal interface stub to keep the current layer compilable, create only that minimal interface and document it clearly.

At completion:

1. run the relevant tests,
2. update `IMPLEMENTATION_STATUS.md`,
3. report files created,
4. report files modified,
5. report tests actually executed,
6. report assumptions,
7. report known limitations,
8. identify the next unblocked layer,
9. stop.

---

# 4. Fixed Architecture

Do not redesign the stack unless explicitly instructed by the repository owner.

## Backend

- Python 3.11+
- FastAPI
- Pydantic v2
- asyncio

## Agent Workflow

- LangGraph

## Graph

- TigerGraph Savanna or TigerGraph Community Edition for local development
- GSQL
- TigerGraph MCP
- TigerGraph GraphRAG

## Main LLM

- Groq
- primary: `openai/gpt-oss-120b`
- fast: `openai/gpt-oss-20b`

## Fallback LLM

- Gemini Flash

## Optional Components

- Laya for lightweight classification
- LightGBM for historical risk scoring

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

---

# 5. Technology Restrictions

Do not introduce:

- CrewAI
- Hermes as a second agent framework
- Pinecone
- Qdrant
- Weaviate
- Chroma
- Neo4j
- OpenSearch as another retrieval platform
- Open Policy Agent
- SageMaker pipelines
- another graph database
- another orchestration framework
- another vector database

Do not add new frameworks because they are popular or convenient.

Use the existing fixed stack.

---

# 6. Deployment Restriction

This project currently stops at local development and hackathon preparation.

Do not add:

- public hosting,
- production deployment,
- Terraform,
- Kubernetes,
- cloud deployment scripts,
- production CI/CD,
- DNS configuration,
- production load balancers,
- production secrets managers,
- live banking integrations.

Local development, local integration testing, benchmark execution, and demo preparation are in scope.

---

# 7. Dataset Safety

The dataset README is authoritative.

Never invent field meanings.

Never create an `is_fraud` or equivalent transaction field unless the dataset legitimately contains it for the applicable historical data.

Treat the bank risk score only as one investigation signal.

Do not use benchmark outcomes as inputs.

Do not hardcode behavior for benchmark case IDs.

Do not train on hidden benchmark outcomes.

Do not inspect benchmark answer artifacts as a source of truth.

All 20 benchmark cases must use the same normal workflow.

---

# 8. Responsibility Boundaries

Maintain these boundaries.

## TigerGraph

Use for:

- entity relationships,
- transaction graph,
- devices,
- IPs,
- accounts,
- historical fraud cases,
- case memory,
- graph algorithms,
- hybrid graph/vector retrieval.

## GSQL

Use for deterministic calculations such as:

- transaction context,
- transaction behavior,
- shared devices,
- shared IPs,
- fraud-linked neighbors,
- shortest path to known fraud,
- bounded neighborhoods,
- connected clusters,
- fan-in,
- fan-out,
- cycles,
- money movement patterns.

Do not make the LLM calculate graph facts that GSQL can calculate.

## GraphRAG

Use for:

- policy retrieval,
- typology retrieval,
- regulatory context,
- similar historical case retrieval.

## Laya

Use only for fast classification and routing such as:

- trigger classification,
- customer response classification,
- analyst response classification.

Do not use Laya as the final fraud adjudicator.

## LightGBM

Use only as an optional supporting historical risk signal.

## Main LLM

Use for:

- evidence synthesis,
- competing fraud hypotheses,
- uncertainty assessment,
- missing-evidence identification,
- next-best-action recommendation,
- concise explanation.

The LLM must not fabricate evidence.

## LangGraph

Use for:

- workflow progression,
- branches,
- evidence loops,
- human interrupts,
- stopping conditions.

## Policy Engine

Use deterministic logic for:

- action authorization,
- approval requirements,
- approval role,
- report requirements,
- action prerequisites.

The LLM cannot bypass the policy engine.

---

# 9. Runtime Flow

The intended runtime flow is:

```text
Trigger
→ Validate Request
→ Create or Resume FraudCaseState
→ Optional Fast Trigger Classification
→ Create or Open Case in TigerGraph
→ Parallel Evidence Collection
→ Evidence Normalization
→ Graph Feature Calculation
→ Risk Signal Calculation
→ Main LLM Reasoning
→ Evidence Sufficiency Gate

If evidence is insufficient:
    → Record current next-best action
    → Select highest-value missing evidence
    → Policy-check evidence request
    → Request evidence
    → Receive evidence
    → Normalize
    → Recalculate
    → Reassess

If evidence is sufficient:
    → Determine next-best action
    → Policy gate
    → Human approval if required
    → Execute or simulate action
    → Generate SAR/report if required
    → Finalize case
    → Write complete case to TigerGraph
    → Create case summary embedding
    → Make case available to future investigations
```

Do not replace this architecture with an unbounded agent loop.

---

# 10. Coding Rules

## Python

Use:

- strict type hints,
- Pydantic at application boundaries,
- enums for controlled values,
- async I/O,
- pure functions for deterministic logic,
- small services,
- explicit dependency injection where useful.

Avoid:

- untyped dictionaries at important boundaries,
- giant service classes,
- business logic inside route handlers,
- hidden global mutable state,
- silent exception swallowing.

## TypeScript

Use:

- strict TypeScript,
- focused components,
- shared API types,
- explicit loading/error states.

Avoid:

- `any`,
- oversized page components,
- duplicated business logic from backend.

---

# 11. Testing Rule

Every deterministic layer must have tests.

Use:

- pytest for backend,
- frontend type checking/linting,
- integration tests for workflow branches.

Do not claim tests passed unless they were actually run.

Unit tests must not require network access.

Use mocks for external providers in unit tests.

---

# 12. Error Handling

Distinguish errors such as:

- input validation failure,
- TigerGraph query failure,
- GraphRAG retrieval failure,
- optional source failure,
- LLM provider failure,
- policy rejection,
- approval rejection,
- action simulation failure,
- benchmark validation failure.

Optional evidence-source failure must not automatically fail the entire investigation.

Critical graph failures must enter a controlled error state.

---

# 13. Output and Evidence Rules

Every meaningful fraud assertion must be grounded.

Evidence must contain provenance.

The reasoning model should reference evidence IDs.

Risk, confidence, and evidence completeness must remain separate.

Never overwrite the pre-evidence next-best action when later evidence changes the recommendation.

Preserve both:

```text
pre_evidence_next_best_action
post_evidence_next_best_action
```

---

# 14. Benchmark Rules

Every benchmark case must:

- use the same LangGraph workflow,
- create a real case,
- collect graph evidence,
- retrieve policy/context,
- record before/after next-best actions when applicable,
- record approval routes,
- generate SAR/report when required,
- write the final case into TigerGraph,
- export one answer file in the exact README format.

No benchmark-specific decision logic is allowed.

---

# 15. Working Procedure

For every task:

## Inspect

- repository structure,
- existing implementation,
- active task,
- status file,
- architecture docs.

## Plan

Identify:

- requested layer,
- affected files,
- dependencies,
- required tests.

## Implement

Modify only necessary files.

Keep interfaces stable.

## Verify

Run:

- unit tests,
- type checks,
- targeted integration tests when relevant.

## Update

Update `IMPLEMENTATION_STATUS.md`.

Do not alter the completion status of a layer unless its acceptance criteria are actually met.

---

# 16. Completion Response Format

At the end of each coding task, report:

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

Implementation status updated:
- ...

Next unblocked layer:
- ...
```

Do not automatically continue to the next layer.

---

# 17. One-Sentence Architecture Rule

When uncertain where logic belongs:

> TigerGraph discovers relationships, GSQL computes fraud facts, GraphRAG retrieves knowledge and precedent, LightGBM contributes an optional historical signal, Laya performs cheap classification, the main LLM reasons over grounded evidence, LangGraph controls the investigation lifecycle, and the deterministic policy engine controls what the system is allowed to do.
