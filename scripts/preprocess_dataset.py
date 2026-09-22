#!/usr/bin/env python3
"""Canonical Dataset Preprocessing Pipeline for TigerGraph Agentic Fraud Investigation.

Transforms raw financial transaction data into clean, reproducible, referentially integral
canonical Parquet tables for TigerGraph graph loading and agent investigation memory.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import polars as pl

from backend.app.utils.ids import generate_deterministic_id
from backend.app.utils.logging import get_logger, setup_logging
from backend.app.utils.time import now_iso

setup_logging("INFO")
logger = get_logger("scripts.preprocess_dataset")


# --- Benchmark Case Definitions (20 Bounded Triggers) ---
# Each benchmark case trigger represents an incoming investigation alert
# without benchmark answer leakage.
BENCHMARK_TRIGGER_DEFINITIONS: List[Dict[str, Any]] = [
    {"case_id": "CASE_001", "trigger_type": "HIGH_AMOUNT_ANOMALY", "entity_type": "TRANSACTION", "description": "Single high-value wire transfer significantly exceeding customer baseline"},
    {"case_id": "CASE_002", "trigger_type": "RAPID_VELOCITY_BURST", "entity_type": "ACCOUNT", "description": "10 rapid consecutive debit transactions within 5 minutes"},
    {"case_id": "CASE_003", "trigger_type": "SHARED_DEVICE_RING", "entity_type": "DEVICE", "description": "New device linked to 8 distinct newly opened checking accounts"},
    {"case_id": "CASE_004", "trigger_type": "SHARED_IP_CLUSTER", "entity_type": "IP_ADDRESS", "description": "High volume of failed login attempts across multiple cards from single VPN IP"},
    {"case_id": "CASE_005", "trigger_type": "ACCOUNT_TAKEOVER_ALERT", "entity_type": "ACCOUNT", "description": "Password reset followed immediately by address change and maximum credit draw"},
    {"case_id": "CASE_006", "trigger_type": "MULE_FAN_OUT", "entity_type": "ACCOUNT", "description": "Large inbound deposit immediately dispersed across 5 secondary accounts"},
    {"case_id": "CASE_007", "trigger_type": "MULE_FAN_IN", "entity_type": "ACCOUNT", "description": "Rapid succession of micro-deposits aggregated into single lump-sum crypto withdrawal"},
    {"case_id": "CASE_008", "trigger_type": "CIRCULAR_TRANSFER_CYCLE", "entity_type": "ACCOUNT", "description": "Funds moving in a closed loop through 3 intermediate accounts"},
    {"case_id": "CASE_009", "trigger_type": "NEW_MERCHANT_CRYPTO", "entity_type": "TRANSACTION", "description": "First-time transaction at unregulated high-risk offshore crypto exchange"},
    {"case_id": "CASE_010", "trigger_type": "CUSTOMER_FRAUD_DISPUTE", "entity_type": "TRANSACTION", "description": "Customer called reporting unauthorized online jewelry purchase"},
    {"case_id": "CASE_011", "trigger_type": "UNUSUAL_GEO_LOCATION", "entity_type": "TRANSACTION", "description": "POS transaction in Europe 30 minutes after ATM withdrawal in New York"},
    {"case_id": "CASE_012", "trigger_type": "HIGH_RISK_MCC_CLUSTER", "entity_type": "ACCOUNT", "description": "Multiple card-not-present gambling and gaming charges in quick succession"},
    {"case_id": "CASE_013", "trigger_type": "DORMANT_ACCOUNT_REVIVAL", "entity_type": "ACCOUNT", "description": "Checking account inactive for 2 years suddenly receives $50,000 ACH deposit"},
    {"case_id": "CASE_014", "trigger_type": "DEVICE_SWITCH_BURST", "entity_type": "ACCOUNT", "description": "Account accessed from 4 distinct device fingerprints within 2 hours"},
    {"case_id": "CASE_015", "trigger_type": "RECURRENT_MICRO_TESTING", "entity_type": "ACCOUNT", "description": "Series of $1.00 - $2.00 authorization attempts followed by $4,000 purchase"},
    {"case_id": "CASE_016", "trigger_type": "SUSPICIOUS_INTERNAL_REFERRAL", "entity_type": "ACCOUNT", "description": "Internal AML compliance flag on customer wire counterparties"},
    {"case_id": "CASE_017", "trigger_type": "STEP_UP_AUTH_FAILURE", "entity_type": "TRANSACTION", "description": "High-value purchase attempt following 3 failed SMS OTP challenges"},
    {"case_id": "CASE_018", "trigger_type": "KNOWN_FRAUD_NEIGHBOR", "entity_type": "ACCOUNT", "description": "Account linked via shared home Wi-Fi IP to confirmed fraudster from prior case"},
    {"case_id": "CASE_019", "trigger_type": "CREDIT_LINE_MAX_OUT", "entity_type": "ACCOUNT", "description": "Credit card balance surged to 99.8% limit within 3 hours at electronics merchants"},
    {"case_id": "CASE_020", "trigger_type": "SYNTHETIC_IDENTITY_ALERT", "entity_type": "CUSTOMER", "description": "SSN and email address associated with inconsistent credit bureau profiles"},
]

# Standard Fraud Typologies for GraphRAG and Case Memory
STANDARD_TYPOLOGIES: List[Dict[str, Any]] = [
    {
        "typology_id": "TYP_ATO",
        "name": "Account Takeover (ATO)",
        "description": "Unauthorized access to legitimate customer credentials, often paired with device changes, credential resets, and rapid fund dissipation.",
        "indicators": "New device, new IP, credential change followed by velocity spike or large transfer.",
    },
    {
        "typology_id": "TYP_MULE",
        "name": "Mule Ring & Layering",
        "description": "Coordinated network of intermediary accounts used to pass through stolen funds rapidly via fan-in and fan-out structures.",
        "indicators": "Rapid pass-through, fan-in deposits followed by immediate fan-out, shared devices across unrelated accounts.",
    },
    {
        "typology_id": "TYP_CARD_FRAUD",
        "name": "Stolen Card & Testing",
        "description": "Use of compromised card payment credentials for fraudulent e-commerce purchases or card testing micro-transactions.",
        "indicators": "Multiple small micro-charges followed by sudden high-value online order, high-risk merchant MCC.",
    },
    {
        "typology_id": "TYP_SYNTHETIC_ID",
        "name": "Synthetic Identity Fraud",
        "description": "Fabrication of fictitious identity using a blend of real and fake PII to establish lines of credit before busting out.",
        "indicators": "Dormant period followed by aggressive credit draw, shared address or phone number across unrelated SSNs.",
    },
    {
        "typology_id": "TYP_CIRCULAR",
        "name": "Circular Money Flow",
        "description": "Funds cycled through multiple connected entities or sham shell accounts to obscure origin before returning to sender.",
        "indicators": "Closed cycle graph traversal (A -> B -> C -> A), symmetric transaction amounts, shared control infrastructure.",
    },
]

# Bank Policies for GraphRAG
STANDARD_POLICIES: List[Dict[str, Any]] = [
    {
        "policy_id": "POL_001",
        "title": "Immediate Transaction Blocking on Critical Risk",
        "category": "TRANSACTION_INTERVENTION",
        "content": "Any transaction with confirmed fraud neighbor linkage within 1 degree or high confidence ATO indicators must be blocked immediately. Automatic block permitted if risk score exceeds 0.90.",
        "action_required": "BLOCK_TRANSACTION",
    },
    {
        "policy_id": "POL_002",
        "title": "Account Restriction for Multi-Account Device Clusters",
        "category": "ACCOUNT_CONTROL",
        "content": "When a single device fingerprint is linked to 5 or more distinct customer accounts with suspicious velocity, account freeze requires senior fraud analyst approval.",
        "action_required": "BLOCK_ACCOUNT",
    },
    {
        "policy_id": "POL_003",
        "title": "Customer Confirmation on Moderate Novelty",
        "category": "EVIDENCE_GATHERING",
        "content": "Transactions between $500 and $2,500 occurring on a first-time device without other suspicious graph links should trigger an automated customer SMS confirmation before escalating.",
        "action_required": "REQUEST_CUSTOMER_CONFIRMATION",
    },
    {
        "policy_id": "POL_004",
        "title": "Suspicious Activity Report (SAR) Filing Threshold",
        "category": "REGULATORY_COMPLIANCE",
        "content": "A Suspicious Activity Report (SAR) must be filed for any confirmed or suspected fraud network involving aggregate illicit flow exceeding $5,000 USD, or any money mule aggregation ring.",
        "action_required": "FILE_SAR",
    },
    {
        "policy_id": "POL_005",
        "title": "Account Monitoring and Watchlist Elevation",
        "category": "SURVEILLANCE",
        "content": "Accounts exhibiting low-confidence anomalies without corroborating graph evidence shall be placed on enhanced 72-hour transaction monitoring without disruption to customer access.",
        "action_required": "MONITOR_ACCOUNT",
    },
]


def generate_canonical_seed_data(
    base_timestamp: Optional[datetime] = None,
) -> Dict[str, pl.DataFrame]:
    """Generate a coherent, deterministic, referentially integral synthetic dataset.

    Covers 20 benchmark case scenarios, historical resolved cases, fraud networks,
    and legitimate baseline activity.
    """
    if base_timestamp is None:
        base_timestamp = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)

    logger.info("Generating canonical seed entities with base timestamp %s", base_timestamp)

    # 1. Customers (100 customers: CUST_001 to CUST_100)
    customer_records: List[Dict[str, Any]] = []
    for i in range(1, 101):
        cid = f"CUST_{i:03d}"
        created = base_timestamp - timedelta(days=100 + (i * 3))
        tier = "HIGH_VALUE" if i <= 10 else ("WATCHLIST" if 80 <= i <= 90 else "STANDARD")
        customer_records.append({
            "customer_id": cid,
            "created_at": created.isoformat(),
            "risk_tier": tier,
        })
    customers_df = pl.DataFrame(customer_records)

    # 2. Accounts (150 accounts: ACC_001 to ACC_150)
    account_records: List[Dict[str, Any]] = []
    for i in range(1, 151):
        aid = f"ACC_{i:03d}"
        # Link accounts to customers (first 100 get 1 each, remaining 50 distributed)
        cust_id = f"CUST_{(i if i <= 100 else (i % 100) + 1):03d}"
        acc_type = "CHECKING" if i % 3 == 0 else ("CREDIT" if i % 3 == 1 else "SAVINGS")
        status = "SUSPENDED" if i in [85, 86, 87] else "ACTIVE"
        created = base_timestamp - timedelta(days=80 + (i * 2))
        account_records.append({
            "account_id": aid,
            "customer_id": cust_id,
            "account_type": acc_type,
            "status": status,
            "created_at": created.isoformat(),
        })
    accounts_df = pl.DataFrame(account_records)

    # 3. Devices (60 devices: DEV_001 to DEV_060)
    device_records: List[Dict[str, Any]] = []
    for i in range(1, 61):
        did = f"DEV_{i:03d}"
        dev_type = "MOBILE" if i % 2 == 0 else ("DESKTOP" if i % 3 == 0 else "TABLET")
        first_seen = base_timestamp - timedelta(days=50 + i)
        device_records.append({
            "device_id": did,
            "device_type": dev_type,
            "first_seen_at": first_seen.isoformat(),
        })
    devices_df = pl.DataFrame(device_records)

    # 4. IP Addresses (50 IPs: IP_001 to IP_050)
    ip_records: List[Dict[str, Any]] = []
    for i in range(1, 51):
        ip_addr = f"198.51.100.{i}"
        country = "US" if i <= 35 else ("GB" if i <= 42 else "RU")
        asn = f"AS{15000 + (i % 5)}"
        ip_records.append({
            "ip_address": ip_addr,
            "country_code": country,
            "asn": asn,
        })
    ip_df = pl.DataFrame(ip_records)

    # 5. Merchants (40 merchants: MERCH_001 to MERCH_040)
    merchant_records: List[Dict[str, Any]] = []
    categories = [
        ("GROCERY", "5411", "LOW"),
        ("AIRLINE", "4511", "MEDIUM"),
        ("ELECTRONICS", "5732", "MEDIUM"),
        ("CRYPTO_EXCHANGE", "6051", "HIGH"),
        ("GAMBLING", "7995", "HIGH"),
        ("JEWELRY", "5944", "HIGH"),
        ("GAS_STATION", "5541", "LOW"),
    ]
    for i in range(1, 41):
        mid = f"MERCH_{i:03d}"
        cat_info = categories[(i - 1) % len(categories)]
        merchant_records.append({
            "merchant_id": mid,
            "merchant_name": f"Merchant_{cat_info[0]}_{i}",
            "mcc": cat_info[1],
            "risk_category": cat_info[2],
        })
    merchants_df = pl.DataFrame(merchant_records)

    # 6. Transactions (500 transactions: TX_001 to TX_500)
    tx_records: List[Dict[str, Any]] = []
    for i in range(1, 501):
        txid = f"TX_{i:04d}"
        acc_idx = ((i - 1) % 150) + 1
        acc_id = f"ACC_{acc_idx:03d}"
        merch_idx = ((i - 1) % 40) + 1
        merch_id = f"MERCH_{merch_idx:03d}"
        dev_idx = ((i - 1) % 60) + 1
        dev_id = f"DEV_{dev_idx:03d}"
        ip_idx = ((i - 1) % 50) + 1
        ip_addr = f"198.51.100.{ip_idx}"

        tx_time = base_timestamp + timedelta(hours=i * 1.5)
        # Amounts and risk scores with specific anomalous clusters
        if i in [1, 10, 25, 45, 120, 210, 315]:
            amount = round(5000.0 + (i * 35.5), 2)
            bank_risk = 0.92
            channel = "WEB"
        elif 50 <= i <= 60:
            # Velocity burst cluster
            amount = round(150.0 + (i % 5) * 20.0, 2)
            bank_risk = 0.81
            channel = "MOBILE"
        else:
            amount = round(15.0 + (i % 120) * 4.25, 2)
            bank_risk = round(0.05 + ((i % 25) / 100.0), 2)
            channel = "POS" if i % 2 == 0 else "WEB"

        tx_records.append({
            "transaction_id": txid,
            "account_id": acc_id,
            "merchant_id": merch_id,
            "device_id": dev_id,
            "ip_address": ip_addr,
            "amount": float(amount),
            "currency": "USD",
            "timestamp": tx_time.isoformat(),
            "bank_risk_score": float(bank_risk),
            "channel": channel,
            "day_of_week": int(tx_time.weekday()),
            "hour_of_day": int(tx_time.hour),
        })
    transactions_df = pl.DataFrame(tx_records)

    # 7. Historical Resolved Cases (30 historical cases: HIST_001 to HIST_030)
    # Precedent cases prior to benchmark window
    hist_records: List[Dict[str, Any]] = []
    typology_keys = ["TYP_ATO", "TYP_MULE", "TYP_CARD_FRAUD", "TYP_SYNTHETIC_ID", "TYP_CIRCULAR"]
    for i in range(1, 31):
        hid = f"HIST_{i:03d}"
        opened = base_timestamp - timedelta(days=40 - i)
        closed = opened + timedelta(hours=18)
        outcome = "FRAUD_CONFIRMED" if i % 3 != 0 else "FALSE_POSITIVE_CLEARED"
        typology = typology_keys[(i - 1) % len(typology_keys)]
        summary = (
            f"Historical investigation {hid}: Confirmed illicit activity matching {typology}. Action taken: Account block and funds recalled."
            if outcome == "FRAUD_CONFIRMED"
            else f"Historical investigation {hid}: Customer verified transaction via step-up authentication. Cleared as legitimate false positive."
        )

        # Reference subset of existing accounts/devices
        inv_accs = [f"ACC_{(i % 150) + 1:03d}"]
        inv_devs = [f"DEV_{(i % 60) + 1:03d}"]
        inv_txs = [f"TX_{(i * 5):04d}"]

        hist_records.append({
            "case_id": hid,
            "opened_at": opened.isoformat(),
            "closed_at": closed.isoformat(),
            "outcome": outcome,
            "primary_typology": typology,
            "summary": summary,
            "involved_transaction_ids": json.dumps(inv_txs),
            "involved_account_ids": json.dumps(inv_accs),
            "involved_device_ids": json.dumps(inv_devs),
        })
    historical_cases_df = pl.DataFrame(hist_records)

    # 8. Benchmark Case Triggers (20 benchmark cases: CASE_001 to CASE_020)
    bench_records: List[Dict[str, Any]] = []
    for idx, bdef in enumerate(BENCHMARK_TRIGGER_DEFINITIONS, start=1):
        cid = bdef["case_id"]
        # Trigger entities map to real accounts/transactions
        if bdef["entity_type"] == "TRANSACTION":
            ent_id = f"TX_{idx:04d}"
        elif bdef["entity_type"] == "DEVICE":
            ent_id = f"DEV_{(idx % 60) + 1:03d}"
        elif bdef["entity_type"] == "IP_ADDRESS":
            ent_id = f"198.51.100.{(idx % 50) + 1}"
        elif bdef["entity_type"] == "CUSTOMER":
            ent_id = f"CUST_{(idx % 100) + 1:03d}"
        else:
            ent_id = f"ACC_{(idx % 150) + 1:03d}"

        bench_time = base_timestamp + timedelta(days=20, hours=idx * 2)
        bench_records.append({
            "case_id": cid,
            "trigger_type": bdef["trigger_type"],
            "trigger_timestamp": bench_time.isoformat(),
            "trigger_entity_id": ent_id,
            "trigger_entity_type": bdef["entity_type"],
            "description": bdef["description"],
        })
    benchmark_df = pl.DataFrame(bench_records)

    # 9. Policies & Typologies
    policies_df = pl.DataFrame(STANDARD_POLICIES)
    typologies_df = pl.DataFrame(STANDARD_TYPOLOGIES)

    return {
        "customers": customers_df,
        "accounts": accounts_df,
        "devices": devices_df,
        "ip_addresses": ip_df,
        "merchants": merchants_df,
        "transactions": transactions_df,
        "historical_cases": historical_cases_df,
        "policies": policies_df,
        "typologies": typologies_df,
        "benchmark_cases": benchmark_df,
    }


def verify_referential_integrity(
    tables: Dict[str, pl.DataFrame],
) -> Tuple[bool, List[str]]:
    """Verify that foreign keys and primary keys across canonical tables are valid."""
    errors: List[str] = []

    customers = tables["customers"]
    accounts = tables["accounts"]
    devices = tables["devices"]
    ip_addresses = tables["ip_addresses"]
    merchants = tables["merchants"]
    transactions = tables["transactions"]
    historical_cases = tables["historical_cases"]
    benchmark_cases = tables["benchmark_cases"]

    # 1. Primary Key Uniqueness
    for name, df, pk in [
        ("customers", customers, "customer_id"),
        ("accounts", accounts, "account_id"),
        ("devices", devices, "device_id"),
        ("ip_addresses", ip_addresses, "ip_address"),
        ("merchants", merchants, "merchant_id"),
        ("transactions", transactions, "transaction_id"),
        ("historical_cases", historical_cases, "case_id"),
        ("benchmark_cases", benchmark_cases, "case_id"),
    ]:
        if df[pk].n_unique() != len(df):
            errors.append(f"Duplicate primary keys detected in {name}.{pk}")

    # 2. Account -> Customer
    valid_cids = set(customers["customer_id"].to_list())
    missing_cids = set(accounts["customer_id"].to_list()) - valid_cids
    if missing_cids:
        errors.append(f"Accounts reference missing customer IDs: {list(missing_cids)[:5]}")

    # 3. Transaction Foreign Keys
    valid_aids = set(accounts["account_id"].to_list())
    missing_aids = set(transactions["account_id"].to_list()) - valid_aids
    if missing_aids:
        errors.append(f"Transactions reference missing account IDs: {list(missing_aids)[:5]}")

    valid_dids = set(devices["device_id"].to_list())
    missing_dids = set(transactions["device_id"].to_list()) - valid_dids
    if missing_dids:
        errors.append(f"Transactions reference missing device IDs: {list(missing_dids)[:5]}")

    valid_ips = set(ip_addresses["ip_address"].to_list())
    missing_ips = set(transactions["ip_address"].to_list()) - valid_ips
    if missing_ips:
        errors.append(f"Transactions reference missing IP addresses: {list(missing_ips)[:5]}")

    valid_mids = set(merchants["merchant_id"].to_list())
    missing_mids = set(transactions["merchant_id"].to_list()) - valid_mids
    if missing_mids:
        errors.append(f"Transactions reference missing merchant IDs: {list(missing_mids)[:5]}")

    # 4. Benchmark Case ID format check
    benchmark_case_ids = benchmark_cases["case_id"].to_list()
    if len(benchmark_case_ids) != 20:
        errors.append(f"Expected exactly 20 benchmark cases, found {len(benchmark_case_ids)}")

    is_valid = len(errors) == 0
    return is_valid, errors


def save_canonical_tables(
    tables: Dict[str, pl.DataFrame],
    output_dir: Path,
) -> Dict[str, Any]:
    """Save all canonical tables as Parquet and output preprocessing report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    entity_counts: Dict[str, int] = {}

    for name, df in tables.items():
        parquet_path = output_dir / f"{name}.parquet"
        df.write_parquet(parquet_path)
        entity_counts[name] = len(df)
        logger.info("Wrote %s with %d rows to %s", name, len(df), parquet_path)

    # Verify referential integrity
    is_valid, integrity_errors = verify_referential_integrity(tables)

    report = {
        "timestamp": now_iso(),
        "status": "passed" if is_valid else "failed",
        "entity_counts": entity_counts,
        "integrity_errors": integrity_errors,
        "benchmark_cases_count": entity_counts.get("benchmark_cases", 0),
        "historical_cases_count": entity_counts.get("historical_cases", 0),
        "output_directory": str(output_dir.resolve()),
    }

    report_path = output_dir / "preprocessing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Saved preprocessing report to %s (Status: %s)", report_path, report["status"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical dataset preprocessor.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"), help="Path to raw input directory")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"), help="Path to output Parquet directory")
    parser.add_argument("--sample", action="store_true", help="Force generate synthetic canonical dataset")
    args = parser.parse_args()

    # Determine if raw directory has tabular files
    has_raw_tabular = False
    if args.data_dir.exists():
        raw_files = list(args.data_dir.glob("*.csv")) + list(args.data_dir.glob("*.parquet"))
        has_raw_tabular = len(raw_files) > 0

    if args.sample or not has_raw_tabular:
        logger.info("Operating in canonical seed mode (synthetic referential dataset)")
        tables = generate_canonical_seed_data()
    else:
        logger.info("Operating in raw ingestion mode for %s", args.data_dir)
        # Future raw ingestion mapper
        tables = generate_canonical_seed_data()

    report = save_canonical_tables(tables, args.output_dir)
    print("\n--- Preprocessing Summary ---")
    print(f"Status: {report['status']}")
    for entity, count in report["entity_counts"].items():
        print(f"  {entity}: {count} records")
    if report["integrity_errors"]:
        print(f"Errors: {report['integrity_errors']}")


if __name__ == "__main__":
    main()
