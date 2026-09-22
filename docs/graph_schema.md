# TigerGraph Graph Schema Architecture & Rationale

## 1. Graph Overview

The `FraudInvestigationGraph` supports two core operational functions:
1. **Real-time Fraud Graph Traversal**: Bounded multi-hop traversal to detect fraud rings, shared devices, shared IPs, rapid pass-through mule chains, and money loops.
2. **Case Memory & Audit Trail**: Persisting full investigation state (evidence, hypotheses, policy citations, human approvals, and actions) directly in graph vertices and edges, enabling future graph and vector similarity search.

---

## 2. Vertex Type Definitions

### 2.1 Domain Financial Entities

| Vertex Type | Primary ID | Key Attributes | Traversal Role |
| :--- | :--- | :--- | :--- |
| `Customer` | `customer_id` | `created_at`, `risk_tier` | Root customer entity; links to owned accounts. |
| `Account` | `account_id` | `account_type`, `status`, `created_at` | Origin or destination financial account. |
| `Transaction`| `transaction_id` | `amount`, `currency`, `timestamp`, `bank_risk_score`, `channel`, `day_of_week`, `hour_of_day` | Core financial event; links accounts, merchants, devices, and IPs. |
| `Device` | `device_id` | `device_type`, `first_seen_at` | Hardware device/fingerprint. Shared devices across accounts reveal fraud rings. |
| `IPAddress` | `ip_address` | `country_code`, `asn` | Client network connection point. Detects bot/proxy/VPN clusters. |
| `Merchant` | `merchant_id` | `merchant_name`, `mcc`, `risk_category` | Counterparty for card and e-commerce payments. |

### 2.2 Case Memory and Investigation Entities

| Vertex Type | Primary ID | Key Attributes | Role |
| :--- | :--- | :--- | :--- |
| `FraudCase` | `case_id` | `opened_at`, `closed_at`, `status`, `outcome`, `primary_typology`, `risk_level`, `confidence`, `evidence_completeness`, `stop_reason`, `summary` | First-class case object. Both historical precedent cases and active investigations reside here. |
| `Evidence` | `evidence_id` | `category`, `source`, `reliability`, `fact`, `timestamp` | Normalized evidence fact grounded in source provenance. |
| `Decision` | `decision_id` | `stage`, `recommended_action`, `pre_or_post`, `reasoning`, `timestamp` | Preserves both pre-evidence NBA and post-evidence NBA. |
| `Action` | `action_id` | `action_type`, `execution_mode`, `status`, `payload`, `timestamp` | Action taken or simulated. |
| `Approval` | `approval_id` | `decision`, `role`, `comment`, `timestamp` | Human analyst approval/rejection/modification record. |
| `Policy` | `policy_id` | `title`, `category`, `content`, `action_required` | Bank fraud policy rule for GraphRAG grounding. |
| `Typology` | `typology_id` | `name`, `description`, `indicators` | Fraud typology definition (ATO, Mule, Stolen Card, etc.). |

---

## 3. Edge Directionality & Traversal Semantics

### 3.1 Directed Edges
- `ACCOUNT_PERFORMED_TRANSACTION` (`Account` -> `Transaction`): Captures the initiating entity of a transaction.
- `TRANSACTION_TO_MERCHANT` (`Transaction` -> `Merchant`): Captures merchant card purchase payment flow.
- `TRANSACTION_TO_ACCOUNT` (`Transaction` -> `Account`): Captures peer-to-peer or internal account transfer money flow.

### 3.2 Undirected Edges
- `CUSTOMER_OWNS_ACCOUNT`: Bidirectional ownership lookup (find customer for account, or all accounts for customer).
- `TRANSACTION_USED_DEVICE` & `TRANSACTION_CONNECTED_IP`: Enables natural 2-hop traversals `(Transaction1)-[:TRANSACTION_USED_DEVICE]-(Device)-[:TRANSACTION_USED_DEVICE]-(Transaction2)` to discover co-occurring accounts on the same device.
- `CASE_INVESTIGATES_*`: Links a fraud case to its involved transactions, accounts, and devices.
- `CASE_HAS_*`: Links a case to its audit trail of evidence, decisions, actions, and approvals.
- `EVIDENCE_LINKED_*`: Grounded linkage between normalized evidence facts and underlying graph entities.

---

## 4. Benchmark & Ground Truth Integrity Rules

1. **No `is_fraud` on `Transaction`**:
   The transaction vertex does NOT have a fraud flag attribute. The system relies on `bank_risk_score` as an auxiliary signal alongside graph analytics and policy evaluation.
2. **Historical Case Precedents**:
   Historical resolved cases in `FraudCase` hold outcomes (`outcome = 'FRAUD_CONFIRMED'` or `'FALSE_POSITIVE_CLEARED'`).
   Benchmark cases (`CASE_001` to `CASE_020`) do NOT contain ground truth outcomes prior to investigation execution.
