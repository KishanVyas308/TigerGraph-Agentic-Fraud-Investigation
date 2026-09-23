"""Deterministic Fraud Feature Engine (Layer 12).

Calculates typed `FraudFeatureSet` metrics from normalized evidence and GSQL query outputs
without using LLM intuition.

Features derived include:
- Shared device / IP account and customer counts
- Fraud-neighbor counts & shortest path distance to historical fraud
- Connected component & community sizes
- Transaction velocity windows (5m, 10m, 1h, 24h)
- Amount deviation ratios (mean ratio, median ratio)
- Novelty flags (new device, new IP, new merchant)
- Money flow patterns (fan-in, fan-out, cycle detection, rapid pass-through)

Preserves `None` when data is unavailable. Generates human-readable explanations for all non-null features.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.state import EvidenceCategory, EvidenceItem, FraudCaseState
from backend.app.utils.logging import get_logger

logger = get_logger("features.engine")


class FraudFeatureSet(BaseModel):
    """Typed deterministic feature set for graph and transaction analysis."""
    model_config = ConfigDict(extra="ignore")

    # Graph Relationship Features
    shared_device_account_count: Optional[int] = None
    shared_device_customer_count: Optional[int] = None
    fraud_accounts_on_device: Optional[int] = None
    shared_ip_account_count: Optional[int] = None
    shared_ip_customer_count: Optional[int] = None
    fraud_neighbors_count: Optional[int] = None
    shortest_distance_to_fraud: Optional[int] = None
    connected_component_size: Optional[int] = None
    community_size: Optional[int] = None

    # Transaction Behavior & Velocity Features
    transaction_count_5m: Optional[int] = None
    transaction_count_10m: Optional[int] = None
    transaction_count_1h: Optional[int] = None
    transaction_count_24h: Optional[int] = None
    transaction_amount_ratio_to_mean: Optional[float] = None
    transaction_amount_ratio_to_median: Optional[float] = None
    new_device: Optional[bool] = None
    new_ip: Optional[bool] = None
    new_merchant: Optional[bool] = None

    # Money Flow Features
    fan_in_count: Optional[int] = None
    fan_out_count: Optional[int] = None
    cycle_detected: Optional[bool] = None
    rapid_pass_through: Optional[bool] = None

    # Explanations for non-null features
    feature_explanations: Dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert feature set to dictionary."""
        return self.model_dump(mode="python")


class GraphFeatureEngine:
    """Deterministic feature engine deriving features and explanations from graph evidence."""

    def compute_features(
        self,
        evidence: Optional[List[EvidenceItem]] = None,
        gsql_outputs: Optional[Dict[str, Any]] = None,
        state: Optional[FraudCaseState] = None,
    ) -> FraudFeatureSet:
        """Compute FraudFeatureSet from evidence items, GSQL outputs, or state."""
        # Consolidate evidence list
        all_ev: List[EvidenceItem] = list(evidence or [])
        if state:
            all_ev.extend(state.all_evidence)

        # Consolidate raw GSQL outputs dict
        raw_gsql: Dict[str, Any] = dict(gsql_outputs or {})
        if state:
            if state.graph_features:
                raw_gsql.update(state.graph_features)
            if state.behavior_features:
                raw_gsql.update(state.behavior_features)

        features = FraudFeatureSet()
        explanations: Dict[str, str] = {}

        # ---------------------------------------------------------------------
        # 1. Graph Relationship Features
        # ---------------------------------------------------------------------

        # A. Shared Devices
        sd_data = raw_gsql.get("shared_devices") if isinstance(raw_gsql.get("shared_devices"), dict) else None
        dev_acc = self._extract_value(sd_data, raw_gsql if sd_data is None else {}, all_ev, ["shared_device_account_count", "shared_account_count"])
        if dev_acc is not None:
            features.shared_device_account_count = int(dev_acc)
            explanations["shared_device_account_count"] = (
                f"Device is shared across {features.shared_device_account_count} distinct bank accounts."
            )

        dev_cust = self._extract_value(sd_data, raw_gsql if sd_data is None else {}, all_ev, ["shared_device_customer_count", "shared_customer_count"])
        if dev_cust is not None:
            features.shared_device_customer_count = int(dev_cust)
            explanations["shared_device_customer_count"] = (
                f"Device is shared across {features.shared_device_customer_count} distinct customer identities."
            )

        fraud_cases = self._extract_value(sd_data, raw_gsql if sd_data is None else {}, all_ev, ["linked_fraud_cases", "fraud_cases"])
        if fraud_cases and isinstance(fraud_cases, (list, tuple)):
            features.fraud_accounts_on_device = len(fraud_cases)
            explanations["fraud_accounts_on_device"] = (
                f"Device is linked to {features.fraud_accounts_on_device} confirmed historical fraud cases."
            )

        # B. Shared IPs
        sip_data = raw_gsql.get("shared_ips") if isinstance(raw_gsql.get("shared_ips"), dict) else None
        ip_acc = self._extract_value(sip_data, raw_gsql if sip_data is None else {}, all_ev, ["shared_ip_account_count", "shared_account_count", "shared_accounts"])
        if ip_acc is not None:
            features.shared_ip_account_count = int(ip_acc)
            explanations["shared_ip_account_count"] = (
                f"IP address is shared across {features.shared_ip_account_count} distinct accounts."
            )

        ip_cust = self._extract_value(sip_data, raw_gsql if sip_data is None else {}, all_ev, ["shared_ip_customer_count", "shared_customer_count", "shared_customers"])
        if ip_cust is not None:
            features.shared_ip_customer_count = int(ip_cust)
            explanations["shared_ip_customer_count"] = (
                f"IP address is shared across {features.shared_ip_customer_count} distinct customers."
            )

        # C. Fraud Neighbors
        fn_data = raw_gsql.get("fraud_neighbors") if isinstance(raw_gsql.get("fraud_neighbors"), dict) else None
        fn_cnt = self._extract_value(fn_data, raw_gsql, all_ev, ["fraud_neighbors_count"])
        if fn_cnt is not None:
            features.fraud_neighbors_count = int(fn_cnt)
            explanations["fraud_neighbors_count"] = (
                f"Target entity has {features.fraud_neighbors_count} confirmed fraud-linked neighbors within 2 graph hops."
            )

        # D. Shortest Distance to Fraud
        sp_data = raw_gsql.get("shortest_path") if isinstance(raw_gsql.get("shortest_path"), dict) else None
        dist = self._extract_value(sp_data, raw_gsql, all_ev, ["shortest_distance", "distance"])
        if dist is not None:
            features.shortest_distance_to_fraud = int(dist)
            target_case = self._extract_value(sp_data, raw_gsql, all_ev, ["target_case", "target_fraud_case_id"])
            target_str = f" to case {target_case}" if target_case else ""
            explanations["shortest_distance_to_fraud"] = (
                f"Shortest graph distance{target_str} is {features.shortest_distance_to_fraud} hop(s)."
            )

        # E. Connected Cluster & Community
        cc_data = raw_gsql.get("connected_cluster") if isinstance(raw_gsql.get("connected_cluster"), dict) else None
        cmp_size = self._extract_value(cc_data, raw_gsql, all_ev, ["connected_component_size", "component_size"])
        if cmp_size is not None:
            features.connected_component_size = int(cmp_size)
            explanations["connected_component_size"] = (
                f"Target entity belongs to a connected graph cluster of {features.connected_component_size} entities."
            )

        comm_size = self._extract_value(cc_data, raw_gsql, all_ev, ["community_size"])
        if comm_size is not None:
            features.community_size = int(comm_size)
            explanations["community_size"] = (
                f"Target entity community cluster size is {features.community_size} entities."
            )

        # ---------------------------------------------------------------------
        # 2. Transaction Behavior & Velocity Features
        # ---------------------------------------------------------------------

        tb_data = raw_gsql.get("transaction_behavior") if isinstance(raw_gsql.get("transaction_behavior"), dict) else None

        cnt_5m = self._extract_value(tb_data, raw_gsql, all_ev, ["txn_count_5m", "count_5m"])
        if cnt_5m is not None:
            features.transaction_count_5m = int(cnt_5m)
            explanations["transaction_count_5m"] = (
                f"Transaction velocity: {features.transaction_count_5m} transactions in last 5 minutes."
            )

        cnt_10m = self._extract_value(tb_data, raw_gsql, all_ev, ["txn_count_10m", "count_10m"])
        if cnt_10m is not None:
            features.transaction_count_10m = int(cnt_10m)
            explanations["transaction_count_10m"] = (
                f"Transaction velocity: {features.transaction_count_10m} transactions in last 10 minutes."
            )

        cnt_1h = self._extract_value(tb_data, raw_gsql, all_ev, ["txn_count_1h", "count_1h"])
        if cnt_1h is not None:
            features.transaction_count_1h = int(cnt_1h)
            explanations["transaction_count_1h"] = (
                f"Transaction velocity: {features.transaction_count_1h} transactions in last 1 hour."
            )

        cnt_24h = self._extract_value(tb_data, raw_gsql, all_ev, ["txn_count_24h", "count_24h"])
        if cnt_24h is not None:
            features.transaction_count_24h = int(cnt_24h)
            explanations["transaction_count_24h"] = (
                f"Transaction velocity: {features.transaction_count_24h} transactions in last 24 hours."
            )

        mean_ratio = self._extract_value(tb_data, raw_gsql, all_ev, ["amount_to_mean_ratio", "mean_ratio"])
        if mean_ratio is not None:
            features.transaction_amount_ratio_to_mean = float(mean_ratio)
            explanations["transaction_amount_ratio_to_mean"] = (
                f"Transaction amount is {features.transaction_amount_ratio_to_mean:.2f}x historical 30-day mean."
            )

        median_ratio = self._extract_value(tb_data, raw_gsql, all_ev, ["amount_to_median_ratio", "median_ratio"])
        if median_ratio is not None:
            features.transaction_amount_ratio_to_median = float(median_ratio)
            explanations["transaction_amount_ratio_to_median"] = (
                f"Transaction amount is {features.transaction_amount_ratio_to_median:.2f}x historical median."
            )

        is_new_mch = self._extract_value(tb_data, raw_gsql, all_ev, ["is_new_merchant"])
        if is_new_mch is not None:
            features.new_merchant = bool(is_new_mch)
            status_str = "NEW merchant for customer" if features.new_merchant else "established merchant history"
            explanations["new_merchant"] = f"Merchant novelty status: {status_str}."

        # Device Identity & IP Novelty
        di_data = raw_gsql.get("device_identity") if isinstance(raw_gsql.get("device_identity"), dict) else None

        is_new_dev = self._extract_value(di_data, raw_gsql, all_ev, ["is_new_device"])
        if is_new_dev is not None:
            features.new_device = bool(is_new_dev)
            status_str = "NEW device (first seen recently)" if features.new_device else "recognized device"
            explanations["new_device"] = f"Device status: {status_str}."

        is_new_ip = self._extract_value(di_data, raw_gsql, all_ev, ["is_new_ip"])
        if is_new_ip is not None:
            features.new_ip = bool(is_new_ip)
            status_str = "NEW IP address for customer" if features.new_ip else "recognized IP address"
            explanations["new_ip"] = f"IP novelty status: {status_str}."

        # ---------------------------------------------------------------------
        # 3. Money Flow Features
        # ---------------------------------------------------------------------

        mf_data = raw_gsql.get("money_flow") if isinstance(raw_gsql.get("money_flow"), dict) else None

        fin = self._extract_value(mf_data, raw_gsql, all_ev, ["fan_in_count", "fan_in"])
        if fin is not None:
            features.fan_in_count = int(fin)
            explanations["fan_in_count"] = (
                f"Money flow fan-in count: {features.fan_in_count} inbound transaction sources."
            )

        fout = self._extract_value(mf_data, raw_gsql, all_ev, ["fan_out_count", "fan_out"])
        if fout is not None:
            features.fan_out_count = int(fout)
            explanations["fan_out_count"] = (
                f"Money flow fan-out count: {features.fan_out_count} outbound destination accounts."
            )

        cyc = self._extract_value(mf_data, raw_gsql, all_ev, ["cycle_detected"])
        if cyc is not None:
            features.cycle_detected = bool(cyc)
            status_str = "CIRCULAR movement detected" if features.cycle_detected else "No circular paths"
            explanations["cycle_detected"] = f"Money flow cycle analysis: {status_str}."

        rpt = self._extract_value(mf_data, raw_gsql, all_ev, ["rapid_pass_through"])
        if rpt is not None:
            features.rapid_pass_through = bool(rpt)
            status_str = "RAPID pass-through pattern detected" if features.rapid_pass_through else "No rapid pass-through"
            explanations["rapid_pass_through"] = f"Fund movement pattern: {status_str}."

        features.feature_explanations = explanations
        return features

    @staticmethod
    def _extract_value(
        gsql_section: Optional[Dict[str, Any]],
        gsql_root: Dict[str, Any],
        evidence_list: List[EvidenceItem],
        keys: List[str],
    ) -> Any:
        """Extract a value for any target keys from gsql_section, gsql_root, or evidence metadata."""
        if isinstance(gsql_section, dict):
            for k in keys:
                if k in gsql_section and gsql_section[k] is not None:
                    return gsql_section[k]

        if isinstance(gsql_root, dict):
            for k in keys:
                if k in gsql_root and gsql_root[k] is not None:
                    return gsql_root[k]

        for item in evidence_list:
            if isinstance(item.metadata, dict):
                for k in keys:
                    if k in item.metadata and item.metadata[k] is not None:
                        return item.metadata[k]
        return None

    @staticmethod
    def _find_metadata_by_category(evidence_list: List[EvidenceItem], category_name: str) -> Optional[Dict[str, Any]]:
        """Find the metadata dict of the first evidence item matching category."""
        for item in evidence_list:
            cat_val = item.category.value if hasattr(item.category, "value") else str(item.category)
            if cat_val == category_name and isinstance(item.metadata, dict):
                return item.metadata
        return None

    @staticmethod
    def _find_metadata_keys(evidence_list: List[EvidenceItem], keys: List[str]) -> Optional[Dict[str, Any]]:
        """Find the metadata dict of the first evidence item containing any target key."""
        for item in evidence_list:
            if isinstance(item.metadata, dict):
                if any(k in item.metadata for k in keys):
                    return item.metadata
        return None

    @staticmethod
    def _find_key_in_evidence(evidence_list: List[EvidenceItem], key: str) -> Any:
        """Find the value for a specific metadata key across all evidence items."""
        for item in evidence_list:
            if isinstance(item.metadata, dict) and key in item.metadata:
                return item.metadata[key]
        return None
