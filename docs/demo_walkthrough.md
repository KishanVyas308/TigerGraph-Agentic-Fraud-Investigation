# Analyst Demo Walkthrough Guide — HHGOA Hackathon

This guide provides an end-to-end script and checklist for presenting the **TigerGraph Agentic Fraud Investigation Agent** across the three canonical local demo scenarios.

---

## Architecture Overview

```text
Trigger
→ Parallel Evidence Collection (TigerGraph GSQL + GraphRAG + Precedents)
→ Evidence Normalization & Graph Feature Engine
→ Main Fraud Reasoning (Competing Hypotheses & Grounding)
→ Evidence Sufficiency Gate
    ├── Insufficient Evidence: Bounded Loop (SMS / Step-up)
    └── Sufficient Evidence: Deterministic Policy Gate
         ├── Autonomous Action: Simulated Execution
         └── Sensitive Action: Analyst Human Approval Gate (Interrupt / Resume)
→ Finalization & Persistence back into TigerGraph Case Memory
```

---

## Pre-Demo Checklist

1. **Verify Backend**:
   ```bash
   uvicorn backend.app.main:app --port 8000
   ```
2. **Verify CLI Runner**:
   ```bash
   python scripts/run_demo.py --scenario ALL
   ```
3. **Artifact Directory**:
   Confirm demo artifacts exist in `outputs/demo/`.

---

## Demo 1: Graph-Detected Fraud Ring (Mule Network)

### Scenario Goal
Demonstrate TigerGraph's core graph traversal power detecting a multi-account mule ring and shared device cluster that cannot be identified from tabular transaction features alone.

### Storyline
A seemingly routine $4,850.00 wire transfer is initiated from customer `CUST_001`. A standard tabular model would see an ordinary wire; however, graph traversal reveals the mobile device is shared across 4 accounts, with a direct 2-hop path to a prior confirmed illicit fraud case (`HIST_001`).

### Step-by-Step Presentation
1. **Trigger Intake**:
   - Case ID: `CASE_DEMO_01`
   - Trigger Entity: Transaction `TX_0001` ($4,850.00)
2. **Graph Visualization (Cytoscape Panel)**:
   - Click on the central node `TX_0001` and expand the 2-hop neighborhood.
   - Point out hardware node `DEV_001` (iPhone 14) connected to 4 distinct accounts (`ACC_001`, `ACC_002`, `ACC_003`, `ACC_005`).
   - Highlight the edge connecting `ACC_002` to historical case vertex `HIST_001` (Outcome: `FRAUD_CONFIRMED`).
   - Notice the circular / fan-in topology highlighting rapid pass-through money movement.
3. **Evidence Panel**:
   - Inspect evidence items:
     - `EVD_D1_001` (DEVICE): "Device DEV_001 shared across 4 accounts across 3 customers."
     - `EVD_D1_002` (GRAPH_RELATIONSHIP): "2-hop shortest path to confirmed fraud case HIST_001."
     - `EVD_D1_004` (POLICY): "Policy POL_001 mandates immediate freeze on shared confirmed fraud hardware."
4. **Assessment & Sufficiency**:
   - Risk: **CRITICAL (0.92)**
   - Confidence: **HIGH (0.90)**
   - Evidence Completeness: **HIGH (0.90)**
   - Sufficiency Gate: **ACT** (graph evidence is complete and decisive; no additional evidence needed).
5. **Action Execution & Final Status**:
   - Policy Gate authorizes autonomous `BLOCK_TRANSACTION` under Policy `POL_001`.
   - Simulated action executed with disposition `IMMEDIATE_STOP`.
   - Case persisted back into TigerGraph case memory for future investigations.

---

## Demo 2: Borderline Case with Dynamic Evidence Loop

### Scenario Goal
Demonstrate how the system handles uncertainty. Instead of guessing or hallucinating, the agent pauses, preserves its initial recommendation, requests the highest-value missing evidence (SMS customer confirmation), and dynamically updates its decision upon ingesting the response.

### Storyline
Customer `CUST_003` initiates a $1,250.00 wire transfer on a first-time mobile device. The IP address is a clean residential connection, and there are no links to known fraud clusters. Because the transaction is moderately novel, the system is uncertain.

### Step-by-Step Presentation
1. **Initial Assessment (Baseline Uncertainty)**:
   - Case ID: `CASE_DEMO_02`
   - Risk: **MEDIUM (0.55)**
   - Confidence: **LOW (0.45)**
   - Evidence Completeness: **LOW (0.40)**
   - Missing Evidence: `CUSTOMER_TRANSACTION_CONFIRMATION`
2. **Preserving Pre-Evidence Recommendation**:
   - Notice in the Decision Panel:
     - `pre_evidence_next_best_action`: **MONITOR_TRANSACTION**
   - Sufficiency Gate routes to `GATHER_MORE_EVIDENCE`.
3. **Evidence Planner**:
   - Value of Information calculation selects two-way SMS confirmation as the lowest-friction, highest-value evidence source.
   - System triggers `REQUEST_CUSTOMER_CONFIRMATION` via automated SMS prompt.
4. **Simulated Customer Confirmation**:
   - Ingest customer response:
     > *"YES, I authorized this $1,250 transfer to Merchant."*
   - Evidence `EVD_D2_004` (CUSTOMER_RESPONSE) is normalized and added to the evidence bundle.
5. **Dynamic Reassessment & Recommendation Update**:
   - Risk drops from **MEDIUM (0.55)** to **LOW (0.18)**.
   - Confidence increases to **0.94**, Completeness to **0.88**.
   - `post_evidence_next_best_action` updates to: **ALLOW_TRANSACTION**.
6. **Audit Trail Verification**:
   - Point out in the audit trail:
     - Pre-Evidence Action (`MONITOR_TRANSACTION`) is preserved.
     - Post-Evidence Action (`ALLOW_TRANSACTION`) is executed.
     - The system never overwrote its pre-evidence recommendation.

---

## Demo 3: High-Risk Account Freeze with Human Approval

### Scenario Goal
Demonstrate deterministic policy governance and human-in-the-loop approval on sensitive banking actions. Proves that the LLM cannot bypass bank policy or autonomously freeze customer accounts without human sign-off.

### Storyline
An established customer account (`ACC_007`) initiates an anomalous $9,800.00 wire transfer immediately following a sudden credential change from a foreign IP address to a known mule account (`ACC_MULE_88`). The reasoning engine identifies an Account Takeover (`TYP_ATO`) and recommends freezing the entire account (`BLOCK_ACCOUNT`).

### Step-by-Step Presentation
1. **High-Risk Assessment**:
   - Case ID: `CASE_DEMO_03`
   - Risk: **CRITICAL (0.95)**
   - Typology: **TYP_ATO (Account Takeover)**
   - Recommended Action: **BLOCK_ACCOUNT** + **FILE_SAR**
2. **Deterministic Policy Gate (POL_005)**:
   - Bank policy `POL_005` specifies that full account freezes (`BLOCK_ACCOUNT`) cannot be executed autonomously.
   - Requirement: Human authorization required by role `SENIOR_FRAUD_ANALYST`.
3. **LangGraph Interrupt / Paused State**:
   - The workflow enters `CaseStatus.AWAITING_APPROVAL`.
   - Stop Reason: `AWAITING_HUMAN_REVIEW`.
   - Investigation progress indicator turns amber; execution is paused safely.
4. **Analyst Dashboard Interaction**:
   - The analyst reviews:
     - Transaction anomaly: 14.2x baseline wire.
     - Graph link: Destination account `ACC_MULE_88` is a known cash-out node.
   - Analyst clicks **Approve Action** and inputs notes:
     > *"Confirmed account takeover: credential change from foreign IP followed by 14x wire to known mule account ACC_MULE_88. Approving account freeze and regulatory SAR filing."*
5. **Resumed Execution & Regulatory SAR Report**:
   - LangGraph resumes from the interrupt checkpoint.
   - `BLOCK_ACCOUNT` executed in simulated mode.
   - Automated grounded SAR report generated:
     - Report ID: `SAR_DEMO_03_ATO`
     - Typology: `TYP_ATO`
     - Narrative: Grounded in verified evidence items, citing customer ID, amount, and mule node.
   - Case marked `COMPLETED` and persisted to TigerGraph case memory.

---

## Key Takeaways for Judges

1. **TigerGraph-First**: Deep graph relationships (shared hardware, hops to fraud, mule rings) drive deterministic features.
2. **Deterministic Policy Control**: The LLM suggests recommendations, but deterministic code (`policy.yaml`) authorizes actions.
3. **Grounded Reasoning**: Every fraud hypothesis references verified evidence IDs; zero hallucinations.
4. **Preserved Lifecycle**: Pre-evidence NBA and post-evidence NBA are never overwritten.
5. **Full Case Memory**: Resolved cases are embedded and persisted back into TigerGraph to continuously improve future investigations.
