"""Evidence Normalizer Service (Layer 10).

Standardizes heterogeneous tool outputs (GSQL queries, GraphRAG retrieval,
device/identity context, customer/analyst input, external signals) into
canonical `EvidenceItem` objects with auditable provenance and deterministic deduplication.
"""

from typing import Any, Dict, List, Optional, Union

from backend.app.models.state import (
    EvidenceCategory,
    EvidenceItem,
    EvidenceReliability,
)
from backend.app.utils.ids import generate_deterministic_id, generate_evidence_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("evidence.normalizer")


class EvidenceNormalizer:
    """Canonical Evidence Normalizer transforming raw tool payloads into standardized EvidenceItems."""

    # =========================================================================
    # GSQL Query Adapters
    # =========================================================================

    @staticmethod
    def normalize_transaction_context(data: Any) -> List[EvidenceItem]:
        """Normalize `get_transaction_context` GSQL output into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        txn_id = str(d.get("transaction_id") or "UNKNOWN")
        amount = d.get("amount")
        currency = d.get("currency", "USD")
        merchant = d.get("merchant_id") or d.get("merchant_name")
        mch_cat = d.get("merchant_category")
        customer_id = d.get("customer_id")
        account_id = d.get("account_id")
        device_id = d.get("device_id")
        ip_address = d.get("ip_address")
        channel = d.get("channel")
        location = d.get("location")
        timestamp = str(d.get("timestamp") or now_iso())

        entities = [e for e in [txn_id, account_id, customer_id, merchant, device_id, ip_address] if e]

        # 1. Core Transaction Fact
        if amount is not None:
            merchant_str = f" at {merchant}" if merchant else ""
            cat_str = f" ({mch_cat})" if mch_cat else ""
            fact = f"Transaction {txn_id} amount {currency} {amount:,.2f}{merchant_str}{cat_str} via Account {account_id or 'UNKNOWN'}"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_TXN", txn_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_transaction_context:{txn_id}",
                category=EvidenceCategory.TRANSACTION_BEHAVIOR,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=timestamp,
                entity_ids=entities,
                metadata={"raw_transaction": d},
            ))

        # 2. Device & Network Context Fact
        if device_id or ip_address:
            dev_str = f"Device {device_id}" if device_id else "No Device ID"
            ip_str = f"IP {ip_address}" if ip_address else "No IP"
            loc_str = f" (Location: {location})" if location else ""
            chan_str = f" via {channel}" if channel else ""
            fact = f"Transaction originated from {dev_str} and {ip_str}{chan_str}{loc_str}"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_DEV", txn_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_transaction_context:{txn_id}",
                category=EvidenceCategory.DEVICE,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=timestamp,
                entity_ids=[e for e in [txn_id, device_id, ip_address] if e],
                metadata={"device_id": device_id, "ip_address": ip_address, "channel": channel},
            ))

        # 3. Identity Association Fact
        if customer_id and account_id:
            fact = f"Customer {customer_id} linked to Account {account_id} for Transaction {txn_id}"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_IDN", customer_id, account_id),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_transaction_context:{txn_id}",
                category=EvidenceCategory.IDENTITY,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=timestamp,
                entity_ids=[customer_id, account_id, txn_id],
                metadata={"customer_id": customer_id, "account_id": account_id},
            ))

        return items

    @staticmethod
    def normalize_transaction_behavior(data: Any) -> List[EvidenceItem]:
        """Normalize `get_transaction_behavior` GSQL output into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        txn_id = str(d.get("transaction_id") or "UNKNOWN")
        hist_mean = d.get("historical_mean_amount", d.get("historical_avg_amount"))
        mean_ratio = d.get("amount_to_mean_ratio")
        hist_median = d.get("historical_median_amount")
        median_ratio = d.get("amount_to_median_ratio")

        count_5m = d.get("txn_count_5m")
        count_1h = d.get("txn_count_1h", d.get("velocity_recent_window"))
        count_24h = d.get("txn_count_24h", d.get("historical_tx_count"))
        is_new_merchant = d.get("is_new_merchant")

        entities = [txn_id]

        # 1. Amount Deviation Fact
        if mean_ratio is not None or median_ratio is not None:
            mean_ratio_str = f"{mean_ratio:.1f}x historical mean (${hist_mean:,.2f})" if mean_ratio and hist_mean else ""
            median_ratio_str = f"{median_ratio:.1f}x median (${hist_median:,.2f})" if median_ratio and hist_median else ""
            parts = [p for p in [mean_ratio_str, median_ratio_str] if p]
            fact = f"Transaction amount ratio: {', '.join(parts)}" if parts else "Transaction amount deviation recorded"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_BHV_AMT", txn_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_transaction_behavior:{txn_id}",
                category=EvidenceCategory.TRANSACTION_BEHAVIOR,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities,
                metadata={"mean_ratio": mean_ratio, "median_ratio": median_ratio},
            ))

        # 2. Transaction Velocity Fact
        if any(c is not None for c in [count_5m, count_1h, count_24h]):
            counts_str = []
            if count_5m is not None:
                counts_str.append(f"{count_5m} in 5m")
            if count_1h is not None:
                counts_str.append(f"{count_1h} in 1h")
            if count_24h is not None:
                counts_str.append(f"{count_24h} in 24h")
            fact = f"Transaction velocity count: {', '.join(counts_str)}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_BHV_VEL", txn_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_transaction_behavior:{txn_id}",
                category=EvidenceCategory.TRANSACTION_BEHAVIOR,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities,
                metadata={"count_5m": count_5m, "count_1h": count_1h, "count_24h": count_24h},
            ))

        # 3. Merchant Novelty Fact
        if is_new_merchant is True:
            fact = f"Transaction is with a NEW merchant for this customer (first interaction)"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_BHV_MCH", txn_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_transaction_behavior:{txn_id}",
                category=EvidenceCategory.TRANSACTION_BEHAVIOR,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities,
                metadata={"is_new_merchant": True},
            ))

        return items

    @staticmethod
    def normalize_shared_device(data: Any) -> List[EvidenceItem]:
        """Normalize `find_shared_devices` GSQL query result into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        device_id = str(d.get("device_id") or "UNKNOWN")
        shared_accounts = d.get("shared_account_count", 0)
        shared_customers = d.get("shared_customer_count", 0)
        fraud_cases = d.get("linked_fraud_cases", [])
        prior_fraud_count = int(d.get("prior_fraud_cases_count", len(fraud_cases)) or 0)

        entities = [device_id]
        if isinstance(fraud_cases, list):
            entities.extend([str(c) for c in fraud_cases])

        # 1. Device Sharing Fact
        if shared_accounts > 1 or shared_customers > 1:
            fact = f"Device {device_id} is shared across {shared_accounts} accounts and {shared_customers} customers"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_SHR_DEV", device_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"find_shared_devices:{device_id}",
                category=EvidenceCategory.DEVICE,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities,
                metadata={"shared_account_count": shared_accounts, "shared_customer_count": shared_customers},
            ))

        # 2. Device Linked Fraud Cases Fact
        if fraud_cases or prior_fraud_count:
            case_list_str = ", ".join(str(c) for c in fraud_cases)
            suffix = f" ({case_list_str})" if case_list_str else ""
            fact = f"Device {device_id} is directly linked to {prior_fraud_count} historical fraud cases{suffix}"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_SHR_DEV_FRD", device_id, case_list_str),
                source="TIGERGRAPH_GSQL",
                source_reference=f"find_shared_devices:{device_id}",
                category=EvidenceCategory.GRAPH_RELATIONSHIP,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities,
                metadata={"fraud_cases": fraud_cases, "fraud_accounts_on_device": prior_fraud_count},
            ))

        return items

    @staticmethod
    def normalize_shared_ip(data: Any) -> List[EvidenceItem]:
        """Normalize `find_shared_ips` GSQL query result into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        ip_address = str(d.get("ip_address") or "UNKNOWN")
        shared_accounts = d.get("shared_account_count", 0)
        shared_customers = d.get("shared_customer_count", 0)
        fraud_cases = d.get("linked_fraud_cases", [])

        entities = [ip_address]

        if shared_accounts > 1 or shared_customers > 1:
            fact = f"IP Address {ip_address} is shared across {shared_accounts} accounts and {shared_customers} customers"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_SHR_IP", ip_address, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"find_shared_ips:{ip_address}",
                category=EvidenceCategory.DEVICE,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities,
                metadata={"shared_accounts": shared_accounts, "shared_customers": shared_customers},
            ))

        if fraud_cases:
            case_list_str = ", ".join(str(c) for c in fraud_cases)
            fact = f"IP Address {ip_address} is directly linked to {len(fraud_cases)} historical fraud cases ({case_list_str})"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_SHR_IP_FRD", ip_address, case_list_str),
                source="TIGERGRAPH_GSQL",
                source_reference=f"find_shared_ips:{ip_address}",
                category=EvidenceCategory.GRAPH_RELATIONSHIP,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=entities + [str(c) for c in fraud_cases],
                metadata={"fraud_cases": fraud_cases},
            ))

        return items

    @staticmethod
    def normalize_fraud_neighbors(data: Any) -> List[EvidenceItem]:
        """Normalize `find_fraud_neighbors` GSQL query result into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        vertex_id = str(d.get("vertex_id") or "UNKNOWN")
        fraud_count = d.get("fraud_neighbors_count", 0)
        neighbor_cases = d.get("neighbor_case_ids", [])

        if fraud_count > 0:
            case_str = ", ".join(str(c) for c in neighbor_cases) if neighbor_cases else "unspecified cases"
            fact = f"Entity {vertex_id} has {fraud_count} fraud-linked neighbors within 2 graph hops ({case_str})"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_FRD_NBR", vertex_id, str(fraud_count)),
                source="TIGERGRAPH_GSQL",
                source_reference=f"find_fraud_neighbors:{vertex_id}",
                category=EvidenceCategory.GRAPH_RELATIONSHIP,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=[vertex_id] + [str(c) for c in neighbor_cases],
                metadata={"fraud_neighbors_count": fraud_count, "neighbor_cases": neighbor_cases},
            ))

        return items

    @staticmethod
    def normalize_shortest_path(data: Any) -> List[EvidenceItem]:
        """Normalize `get_shortest_path_to_fraud` GSQL query result into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        vertex_id = str(d.get("vertex_id") or "UNKNOWN")
        target_case = d.get("target_fraud_case_id")
        distance = d.get("shortest_distance")
        path_nodes = d.get("path_nodes", [])

        if distance is not None and distance > 0:
            case_str = f"to confirmed fraud case {target_case}" if target_case else "to a confirmed fraud entity"
            path_str = f" via path [{' -> '.join(path_nodes)}]" if path_nodes else ""
            fact = f"Shortest graph distance from {vertex_id} {case_str} is {distance} hop(s){path_str}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_PTH_FRD", vertex_id, str(target_case or distance)),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_shortest_path_to_fraud:{vertex_id}",
                category=EvidenceCategory.GRAPH_RELATIONSHIP,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=[e for e in [vertex_id, target_case] if e] + list(path_nodes),
                metadata={"distance": distance, "target_case": target_case, "path_nodes": path_nodes},
            ))

        return items

    @staticmethod
    def normalize_money_flow(data: Any) -> List[EvidenceItem]:
        """Normalize `detect_money_flow_patterns` GSQL query result into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        account_id = str(d.get("account_id") or "UNKNOWN")
        fan_in = d.get("fan_in_count", 0)
        fan_out = d.get("fan_out_count", 0)
        rapid_pass_through = d.get("rapid_pass_through", False)
        cycle_detected = d.get("cycle_detected", False)

        patterns = []
        if fan_in > 3:
            patterns.append(f"Suspicious fan-in ({fan_in} incoming flows)")
        if fan_out > 3:
            patterns.append(f"Suspicious fan-out ({fan_out} outgoing flows)")
        if rapid_pass_through:
            patterns.append("Rapid fund pass-through")
        if cycle_detected:
            patterns.append("Circular money movement detected")

        if patterns:
            fact = f"Money flow analysis on Account {account_id}: {'; '.join(patterns)}"
            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_MNY_FLW", account_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"detect_money_flow_patterns:{account_id}",
                category=EvidenceCategory.MONEY_FLOW,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=[account_id],
                metadata={
                    "fan_in": fan_in,
                    "fan_out": fan_out,
                    "rapid_pass_through": rapid_pass_through,
                    "cycle_detected": cycle_detected,
                },
            ))

        return items

    @staticmethod
    def normalize_device_identity(data: Any) -> List[EvidenceItem]:
        """Normalize `get_device_identity_context` GSQL output into EvidenceItems."""
        d = data.model_dump() if hasattr(data, "model_dump") else (data or {})
        items: List[EvidenceItem] = []

        device_id = str(d.get("device_id") or "UNKNOWN")
        is_new_device = d.get("is_new_device", False)
        first_seen = d.get("first_seen_timestamp")
        linked_accounts = d.get("linked_account_count", 0)

        if is_new_device or linked_accounts > 0:
            new_str = "NEW_DEVICE (first seen recently)" if is_new_device else "established device"
            fact = f"Device {device_id} identity context: {new_str}, linked to {linked_accounts} account(s)"
            if first_seen:
                fact += f" (first seen: {first_seen})"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_DEV_IDN", device_id, fact),
                source="TIGERGRAPH_GSQL",
                source_reference=f"get_device_identity_context:{device_id}",
                category=EvidenceCategory.DEVICE,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=[device_id],
                metadata={"is_new_device": is_new_device, "first_seen": first_seen, "linked_accounts": linked_accounts},
            ))

        return items

    # =========================================================================
    # GraphRAG Policy & Case Memory Adapters
    # =========================================================================

    @staticmethod
    def normalize_graphrag_policy(policy_result: Any) -> List[EvidenceItem]:
        """Normalize GraphRAG `PolicyContextResult` or items into EvidenceItems with strict governance provenance.

        IMPORTANT: Policy text remains explicit policy evidence, never converted into factual transaction assertions.
        """
        items: List[EvidenceItem] = []
        raw_items = []

        if hasattr(policy_result, "items"):
            raw_items = policy_result.items
        elif isinstance(policy_result, dict):
            raw_items = policy_result.get("items", [])
        elif isinstance(policy_result, list):
            raw_items = policy_result

        for idx, item_obj in enumerate(raw_items):
            d = item_obj.model_dump() if hasattr(item_obj, "model_dump") else item_obj

            chunk_id = str(d.get("chunk_id") or f"CHUNK_{idx}")
            source_id = str(d.get("source_id") or "POLICY_DOC")
            doc_type = str(d.get("document_type") or "POLICY").upper()
            title = str(d.get("section_title") or "Governance Rule")
            text = str(d.get("text") or "").strip()
            score = float(d.get("relevance_score", 0.0))
            refs = d.get("graph_references", [])

            cat = EvidenceCategory.POLICY
            if doc_type == "REGULATION":
                cat = EvidenceCategory.REGULATION
            elif doc_type == "TYPOLOGY":
                cat = EvidenceCategory.POLICY

            # Explicit policy statement framing
            fact = f"[{source_id}] {title}: {text}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_POL", source_id, chunk_id),
                source="POLICY_GRAPHRAG",
                source_reference=f"policy_index:{source_id}:{chunk_id}",
                category=cat,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=now_iso(),
                entity_ids=list(refs),
                metadata={
                    "source_id": source_id,
                    "document_type": doc_type,
                    "section_title": title,
                    "relevance_score": score,
                },
            ))

        return items

    @staticmethod
    def normalize_graphrag_cases(cases_result: Any) -> List[EvidenceItem]:
        """Normalize GraphRAG `SimilarCasesResult` or items into EvidenceItems with precedent provenance."""
        items: List[EvidenceItem] = []
        raw_cases = []

        if hasattr(cases_result, "cases"):
            raw_cases = cases_result.cases
        elif isinstance(cases_result, dict):
            raw_cases = cases_result.get("cases", [])
        elif isinstance(cases_result, list):
            raw_cases = cases_result

        for item_obj in raw_cases:
            d = item_obj.model_dump() if hasattr(item_obj, "model_dump") else item_obj

            cid = str(d.get("case_id") or "HIST_UNKNOWN")
            outcome = str(d.get("outcome") or "UNKNOWN")
            typology = str(d.get("primary_typology") or "GENERAL")
            summary = str(d.get("summary") or "").strip()
            score = float(d.get("combined_score", 0.0))
            method = str(d.get("retrieval_method") or "VECTOR")
            shared = d.get("shared_entities", [])

            shared_str = f" (Shared entities: {', '.join(shared)})" if shared else ""
            fact = f"Historical Precedent {cid} (Outcome: {outcome}, Typology: {typology}, Match: {method} {score:.2f}){shared_str}: {summary}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_PRE", cid, outcome),
                source="CASE_MEMORY",
                source_reference=f"case_memory:{cid}",
                category=EvidenceCategory.HISTORICAL_CASE,
                fact=fact,
                reliability=EvidenceReliability.MEDIUM,
                timestamp=now_iso(),
                entity_ids=[cid] + list(shared),
                metadata={
                    "case_id": cid,
                    "outcome": outcome,
                    "typology": typology,
                    "combined_score": score,
                    "retrieval_method": method,
                },
            ))

        return items

    # =========================================================================
    # External, Customer & Analyst Input Adapters
    # =========================================================================

    @staticmethod
    def normalize_customer_response(response_data: Dict[str, Any]) -> List[EvidenceItem]:
        """Normalize customer confirmation response into EvidenceItem."""
        items: List[EvidenceItem] = []

        target_id = str(response_data.get("transaction_id") or response_data.get("customer_id") or "UNKNOWN")
        confirmed = response_data.get("confirmed_authorized")
        channel = response_data.get("channel", "SMS")
        timestamp = response_data.get("timestamp", now_iso())

        if confirmed is not None:
            auth_str = "CONFIRMED AUTHORIZED" if confirmed else "DENIED / REPORTED UNAUTHORIZED"
            fact = f"Customer response via {channel} for {target_id}: Transaction is {auth_str}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_CUST", target_id, str(confirmed)),
                source="CUSTOMER_RESPONSE",
                source_reference=f"customer_confirmation:{channel}",
                category=EvidenceCategory.CUSTOMER_RESPONSE,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=timestamp,
                entity_ids=[target_id],
                metadata={"confirmed_authorized": confirmed, "channel": channel},
            ))

        return items

    @staticmethod
    def normalize_authentication_result(auth_data: Dict[str, Any]) -> List[EvidenceItem]:
        """Normalize step-up authentication result into EvidenceItem."""
        items: List[EvidenceItem] = []

        target_id = str(auth_data.get("customer_id") or auth_data.get("transaction_id") or "UNKNOWN")
        method = auth_data.get("method", "STEP_UP_AUTH")
        verified = auth_data.get("verified")
        attempts = auth_data.get("attempts", 1)
        timestamp = auth_data.get("timestamp", now_iso())

        if verified is not None:
            ver_str = "PASSED" if verified else f"FAILED after {attempts} attempt(s)"
            fact = f"Step-up authentication result ({method}) for {target_id}: Verification {ver_str}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_AUTH", target_id, method, str(verified)),
                source="AUTHENTICATION_SERVICE",
                source_reference=f"step_up_auth:{method}",
                category=EvidenceCategory.AUTHENTICATION,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=timestamp,
                entity_ids=[target_id],
                metadata={"method": method, "verified": verified, "attempts": attempts},
            ))

        return items

    @staticmethod
    def normalize_analyst_input(input_data: Dict[str, Any]) -> List[EvidenceItem]:
        """Normalize human analyst input/note into EvidenceItem."""
        items: List[EvidenceItem] = []

        analyst_id = str(input_data.get("analyst_id") or "ANALYST")
        case_id = str(input_data.get("case_id") or "UNKNOWN")
        note = str(input_data.get("note") or input_data.get("comment") or "").strip()
        timestamp = input_data.get("timestamp", now_iso())

        if note:
            fact = f"Analyst Input from {analyst_id} on Case {case_id}: {note}"

            items.append(EvidenceItem(
                evidence_id=generate_deterministic_id("EVD_ANALYST", analyst_id, note[:30]),
                source="ANALYST_INPUT",
                source_reference=f"analyst_input:{analyst_id}",
                category=EvidenceCategory.ANALYST_INPUT,
                fact=fact,
                reliability=EvidenceReliability.HIGH,
                timestamp=timestamp,
                entity_ids=[case_id, analyst_id],
                metadata={"analyst_id": analyst_id, "case_id": case_id},
            ))

        return items

    @staticmethod
    def normalize_external_signal(signal_data: Dict[str, Any]) -> List[EvidenceItem]:
        """Normalize external IP, device reputation, or CRM risk flags into EvidenceItem."""
        items: List[EvidenceItem] = []

        provider = str(signal_data.get("provider") or signal_data.get("source") or "EXTERNAL")
        target_entity = str(signal_data.get("entity_id") or "UNKNOWN")
        signal_type = str(signal_data.get("signal_type") or "RISK_SIGNAL")
        score = signal_data.get("score")
        flag = signal_data.get("flag")
        details = signal_data.get("details", "")

        score_str = f" (Score: {score})" if score is not None else ""
        flag_str = f" [Flag: {flag}]" if flag else ""
        detail_str = f": {details}" if details else ""

        fact = f"External Signal ({provider} - {signal_type}) for {target_entity}{score_str}{flag_str}{detail_str}"

        items.append(EvidenceItem(
            evidence_id=generate_deterministic_id("EVD_EXT", provider, target_entity, signal_type),
            source="EXTERNAL_SIGNAL",
            source_reference=f"external_signal:{provider}",
            category=EvidenceCategory.EXTERNAL_SIGNAL,
            fact=fact,
            reliability=EvidenceReliability.MEDIUM,
            timestamp=now_iso(),
            entity_ids=[target_entity],
            metadata={"provider": provider, "signal_type": signal_type, "score": score, "flag": flag},
        ))

        return items

    # =========================================================================
    # Deduplication & Heterogeneous Bundle Processing
    # =========================================================================

    @staticmethod
    def deduplicate(items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Deterministically deduplicate evidence items by evidence_id or exact fact string."""
        seen_ids = set()
        seen_facts = set()
        deduped: List[EvidenceItem] = []

        for item in items:
            if item.evidence_id in seen_ids or item.fact in seen_facts:
                continue
            seen_ids.add(item.evidence_id)
            seen_facts.add(item.fact)
            deduped.append(item)

        return deduped

    def normalize_bundle(self, raw_bundle: Dict[str, Any]) -> List[EvidenceItem]:
        """Process a dictionary of heterogeneous tool outputs and return a normalized, deduplicated list of EvidenceItems."""
        all_items: List[EvidenceItem] = []

        if "transaction_context" in raw_bundle:
            all_items.extend(self.normalize_transaction_context(raw_bundle["transaction_context"]))

        if "transaction_behavior" in raw_bundle:
            all_items.extend(self.normalize_transaction_behavior(raw_bundle["transaction_behavior"]))

        if "shared_devices" in raw_bundle:
            all_items.extend(self.normalize_shared_device(raw_bundle["shared_devices"]))

        if "shared_ips" in raw_bundle:
            all_items.extend(self.normalize_shared_ip(raw_bundle["shared_ips"]))

        if "fraud_neighbors" in raw_bundle:
            all_items.extend(self.normalize_fraud_neighbors(raw_bundle["fraud_neighbors"]))

        if "shortest_path" in raw_bundle:
            all_items.extend(self.normalize_shortest_path(raw_bundle["shortest_path"]))

        if "money_flow" in raw_bundle:
            all_items.extend(self.normalize_money_flow(raw_bundle["money_flow"]))

        if "device_identity" in raw_bundle:
            all_items.extend(self.normalize_device_identity(raw_bundle["device_identity"]))

        if "policy_context" in raw_bundle:
            all_items.extend(self.normalize_graphrag_policy(raw_bundle["policy_context"]))

        if "similar_cases" in raw_bundle:
            all_items.extend(self.normalize_graphrag_cases(raw_bundle["similar_cases"]))

        if "customer_response" in raw_bundle:
            all_items.extend(self.normalize_customer_response(raw_bundle["customer_response"]))

        if "authentication_result" in raw_bundle:
            all_items.extend(self.normalize_authentication_result(raw_bundle["authentication_result"]))

        if "analyst_input" in raw_bundle:
            all_items.extend(self.normalize_analyst_input(raw_bundle["analyst_input"]))

        if "external_signal" in raw_bundle:
            all_items.extend(self.normalize_external_signal(raw_bundle["external_signal"]))

        return self.deduplicate(all_items)
