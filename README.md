# TigerGraph Agentic Fraud Investigation Agent — HHGOA

An agentic fraud investigation system built for the TigerGraph HHGOA hackathon.

The system investigates suspicious financial activity using graph analysis, historical case memory, fraud policy retrieval, uncertainty-aware reasoning, controlled evidence gathering, and next-best-action recommendations.

The design is **TigerGraph-first**: graph traversal and GSQL produce fraud evidence, while the LLM reasons over grounded evidence rather than replacing graph analysis.

---

# What the System Does

The system can:

- investigate fraud alerts,
- investigate customer-reported fraud,
- investigate analyst-requested cases,
- analyze transaction behavior,
- trace connected accounts, devices, IPs, merchants, and identities,
- detect suspicious graph relationships,
- retrieve fraud policies and typologies,
- find similar historical cases,
- assess risk, confidence, and evidence completeness,
- request more evidence when uncertainty remains,
- recommend a next-best action,
- enforce deterministic action policies,
- pause for human approval,
- simulate fraud-response actions,
- generate SAR/report output when required,
- store the complete case back into TigerGraph,
- reuse completed investigations as future case memory.

---

# Core Architecture

```text
Frontend
   ↓
FastAPI
   ↓
LangGraph Investigation Workflow
   ↓
TigerGraph MCP
   ↓
┌─────────────────────────────────────────────┐
│ TigerGraph                                  │
│                                             │
│ GSQL graph investigation                    │
│ Graph algorithms                            │
│ Transaction relationships                   │
│ Device and identity relationships           │
│ Historical case memory                      │
│ GraphRAG policy and case retrieval           │
└─────────────────────────────────────────────┘
   ↓
Evidence Normalization
   ↓
Graph Feature Engine
   ↓
Risk Signals
   ↓
Main LLM Reasoning
   ↓
Evidence Sufficiency
   ↓
More Evidence OR Next-Best Action
   ↓
Deterministic Policy Gate
   ↓
Human Approval When Required
   ↓
Simulated Action
   ↓
Case Finalization
   ↓
TigerGraph Case Memory
```

---

# Fixed Technology Stack

## Graph and Retrieval

- TigerGraph
- GSQL
- TigerGraph MCP
- TigerGraph GraphRAG

## Agent Orchestration

- LangGraph

## Backend

- Python 3.11+
- FastAPI
- Pydantic v2
- asyncio

## LLMs

Primary:

```text
Groq
openai/gpt-oss-120b
```

Fast model:

```text
Groq
openai/gpt-oss-20b
```

Fallback:

```text
Gemini Flash
```

## Optional Intelligence

- ConvAI Innovations Laya for fast classification
- LightGBM for historical risk signal
- SentenceTransformers for local embeddings

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

# Important Documentation

Read these files before implementing anything.

## AI Agent Rules

```text
AGENTS.md
```

Permanent engineering and architectural rules for AI coding agents.

## Antigravity Instructions

```text
GEMINI.md
```

Google Antigravity-specific working instructions.

## Current Work

```text
CURRENT_TASK.md
```

Defines the only implementation layer that should currently be worked on.

## Progress

```text
IMPLEMENTATION_STATUS.md
```

Tracks all implementation layers and current blockers.

## Architecture

```text
docs/project_description.md
```

Full project architecture, system flow, case flows, technology choices, and functional requirements.

## Layer-by-Layer Build Plan

```text
docs/layer_by_layer_implementation.md
```

Detailed implementation plan with tasks, deliverables, acceptance criteria, and AI coding prompts for each layer.

## Dataset Mapping

```text
docs/dataset_mapping.md
```

Created during Layer 1 after reading and inspecting the official dataset.

Do not create this file from assumptions.

---

# Development Philosophy

The project follows one central rule:

> TigerGraph discovers relationships, GSQL computes fraud facts, GraphRAG retrieves knowledge and precedent, LightGBM contributes an optional historical signal, Laya performs cheap classification, the main LLM reasons over grounded evidence, LangGraph controls the investigation lifecycle, and the deterministic policy engine controls what the system is allowed to do.

The LLM is not the fraud database.

The LLM is not the policy engine.

The LLM does not invent graph relationships.

---

# Investigation Flow

Every case follows one shared workflow.

```text
Trigger
→ Validate
→ Create or Open Case
→ Gather Evidence in Parallel
→ Normalize Evidence
→ Calculate Graph Features
→ Calculate Risk Signals
→ LLM Fraud Assessment
→ Evidence Sufficiency Check
```

If evidence is insufficient:

```text
Record Current NBA
→ Select Highest-Value Missing Evidence
→ Request Evidence
→ Receive Evidence
→ Recalculate
→ Reassess
```

If evidence is sufficient:

```text
Determine Next-Best Action
→ Policy Check
→ Human Approval if Required
→ Execute or Simulate
→ Generate Report if Required
→ Finalize Case
→ Write Case to TigerGraph
→ Create Future Case Memory
```

---

# Parallel Evidence Collection

Each investigation gathers several evidence classes concurrently.

## Transaction Analysis

Examples:

- amount anomaly,
- transaction velocity,
- merchant novelty,
- recent activity.

## Graph Relationship Analysis

Examples:

- shared devices,
- shared IPs,
- fraud-linked neighbors,
- shortest path to historical fraud,
- connected components,
- fan-in,
- fan-out,
- circular movement.

## Policy and Typology Retrieval

GraphRAG retrieves:

- bank fraud policy,
- fraud typologies,
- regulatory guidance,
- action approval rules.

## Historical Case Memory

The system retrieves:

- graph-similar cases,
- vector-similar cases,
- shared entities,
- historical outcomes,
- prior analyst decisions.

## Device and Identity Analysis

Examples:

- new device,
- device age,
- number of linked accounts,
- previous fraud cases involving the device,
- shared identity attributes.

## Optional Signals

Locally simulated sources may include:

- step-up authentication,
- customer transaction confirmation,
- device reputation,
- IP reputation,
- CRM context.

---

# Evidence Model

All tool outputs are normalized into a common evidence format.

Example:

```json
{
  "evidence_id": "E019",
  "source": "TIGERGRAPH_GSQL",
  "category": "DEVICE",
  "fact": "Device D91 is shared by 11 accounts.",
  "reliability": "HIGH",
  "entity_ids": ["D91"]
}
```

Every important investigation claim should be traceable to evidence.

---

# Risk Model

The system keeps three concepts separate.

## Risk

How suspicious or harmful the activity appears.

```text
LOW
MEDIUM
HIGH
CRITICAL
```

## Confidence

How certain the system is about its assessment.

## Evidence Completeness

Whether enough information exists to take a defensible action.

Example:

```text
Risk = HIGH
Confidence = LOW
Evidence Completeness = LOW
```

Result:

```text
Gather more evidence.
```

---

# Next-Best Action

Possible action categories include:

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

The actual permitted actions are controlled by the official fraud policy.

---

# Human Approval

Sensitive actions pass through a deterministic policy engine.

If approval is required, LangGraph pauses the investigation.

The analyst can:

```text
APPROVE
REJECT
MODIFY
```

The decision is added to the case timeline.

---

# Case Memory

Completed cases are stored back into TigerGraph with links to:

- transactions,
- accounts,
- devices,
- evidence,
- fraud patterns,
- policy references,
- decisions,
- actions,
- approvals,
- outcomes.

Future investigations can retrieve these cases using:

- graph similarity,
- shared entities,
- vector similarity.

Both confirmed-fraud and cleared cases are valid memory.

---

# Repository Structure

The target structure is:

```text
project-root/

AGENTS.md
GEMINI.md
CURRENT_TASK.md
IMPLEMENTATION_STATUS.md
README.md
.env.example
.gitignore

backend/
frontend/
gsql/
data/
scripts/
outputs/
tests/

docs/
  project_description.md
  layer_by_layer_implementation.md
  dataset_mapping.md
  local_setup.md
  architecture.md
```

Detailed subdirectories are defined in:

```text
docs/layer_by_layer_implementation.md
```

---

# Current Development Stage

Check:

```text
CURRENT_TASK.md
```

and:

```text
IMPLEMENTATION_STATUS.md
```

Do not start from this README alone.

The implementation plan is intentionally layer-based.

---

# Recommended AI Coding Workflow

For Google Antigravity or another coding agent:

```text
1. Read GEMINI.md
2. Read AGENTS.md
3. Read CURRENT_TASK.md
4. Read IMPLEMENTATION_STATUS.md
5. Read relevant architecture docs
6. Inspect existing code
7. Implement only the active layer
8. Run relevant tests
9. Update IMPLEMENTATION_STATUS.md
10. Stop
```

A simple instruction should be enough:

```text
Implement CURRENT_TASK.md.
```

---

# Benchmark Requirements

The final system must run all 20 benchmark cases through the same investigation workflow.

For each case, the system must support producing:

- internal investigation record,
- evidence,
- graph findings,
- fraud hypotheses,
- matched patterns,
- policy evidence,
- similar historical cases,
- risk,
- confidence,
- evidence completeness,
- missing evidence,
- next-best action before additional evidence,
- requested evidence,
- received evidence,
- next-best action after additional evidence,
- approval route,
- actions,
- SAR/report when required,
- final status,
- stop reason.

The exact submission format must follow the official dataset README.

---

# Local-Only Scope

The current implementation plan intentionally excludes deployment.

Do not add:

- public hosting,
- Terraform,
- Kubernetes,
- production CI/CD,
- DNS,
- production secrets management,
- live financial-system integrations.

The project should first become fully functional through:

- local development,
- local TigerGraph integration,
- local API,
- local UI,
- local tests,
- benchmark execution,
- demo preparation.

---

# Definition of Done

The project is ready when:

1. the dataset is processed reproducibly,
2. TigerGraph contains the required graph,
3. GSQL returns meaningful fraud evidence,
4. GraphRAG retrieves relevant policy and prior cases,
5. evidence is normalized and traceable,
6. graph features are deterministic,
7. LLM reasoning is structured and grounded,
8. risk/confidence/completeness are separate,
9. uncertain cases gather more evidence,
10. recommendations update after new evidence,
11. deterministic policy controls actions,
12. human approval works,
13. actions are simulated locally,
14. required reports are generated,
15. completed cases are stored as memory,
16. future cases can retrieve historical cases,
17. the UI explains the investigation clearly,
18. tests cover major branches,
19. all benchmark cases run through one workflow,
20. benchmark outputs pass validation.
