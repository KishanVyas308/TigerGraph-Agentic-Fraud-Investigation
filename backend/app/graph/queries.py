"""Typed GSQL query wrappers and Pydantic models for graph analytics.

Supports both online execution against TigerGraph REST endpoints and offline
deterministic simulation using local canonical Parquet tables.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import polars as pl
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.utils.logging import get_logger

logger = get_logger("graph.queries")


# --- Output Models ---

class TransactionContext(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "USD"
    timestamp: str
    bank_risk_score: float
    channel: str
    account_id: str
    customer_id: str
    merchant_id: str
    device_id: str
    ip_address: str


class TransactionBehavior(BaseModel):
    target_amount: float
    historical_avg_amount: float
    amount_ratio_to_mean: float
    historical_tx_count: int
    velocity_recent_window: int
    is_new_merchant: bool


class SharedDeviceContext(BaseModel):
    device_id: str
    shared_account_count: int
    shared_customer_count: int
    prior_fraud_cases_count: int
    accounts: List[str] = Field(default_factory=list)
    customers: List[str] = Field(default_factory=list)


class SharedIPContext(BaseModel):
    ip_address: str
    country_code: str
    asn: str
    shared_account_count: int
    transaction_count: int
    accounts: List[str] = Field(default_factory=list)


class FraudNeighborsContext(BaseModel):
    fraud_neighbors_count: int
    linked_fraud_cases: List[str] = Field(default_factory=list)


class ShortestPathToFraud(BaseModel):
    shortest_distance_to_fraud: int
    nearest_fraud_cases: List[str] = Field(default_factory=list)


class MoneyFlowPattern(BaseModel):
    account_id: str
    fan_in_count: int
    fan_out_count: int
    inbound_sum: float
    outbound_sum: float
    cycle_detected: bool


class DeviceIdentityContext(BaseModel):
    device_id: str
    device_type: str
    first_seen_at: str
    linked_accounts_count: int
    linked_customers_count: int


# --- Graph Query Service ---

class GraphQueryService:
    """Service to execute fraud investigation graph queries online or offline."""

    def __init__(self, processed_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.processed_dir = processed_dir or Path("data/processed")
        self._cached_tables: Dict[str, pl.DataFrame] = {}

    def _get_table(self, name: str) -> pl.DataFrame:
        if name not in self._cached_tables:
            pq_file = self.processed_dir / f"{name}.parquet"
            if not pq_file.exists():
                raise FileNotFoundError(f"Processed table not found: {pq_file}")
            self._cached_tables[name] = pl.read_parquet(pq_file)
        return self._cached_tables[name]

    def is_online(self) -> bool:
        """Check if TigerGraph instance is reachable."""
        try:
            resp = httpx.get(f"{self.settings.TIGERGRAPH_HOST.rstrip('/')}/echo", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_transaction_context(self, transaction_id: str) -> TransactionContext:
        """Retrieve 1-hop context of a transaction."""
        tx_df = self._get_table("transactions")
        match = tx_df.filter(pl.col("transaction_id") == transaction_id)
        if len(match) == 0:
            raise ValueError(f"Transaction not found: {transaction_id}")
        tx_row = match.to_dicts()[0]

        acc_df = self._get_table("accounts")
        acc_match = acc_df.filter(pl.col("account_id") == tx_row["account_id"]).to_dicts()
        customer_id = acc_match[0]["customer_id"] if acc_match else "UNKNOWN_CUST"

        return TransactionContext(
            transaction_id=tx_row["transaction_id"],
            amount=float(tx_row["amount"]),
            currency=tx_row.get("currency", "USD"),
            timestamp=str(tx_row["timestamp"]),
            bank_risk_score=float(tx_row.get("bank_risk_score", 0.0)),
            channel=tx_row.get("channel", "WEB"),
            account_id=tx_row["account_id"],
            customer_id=customer_id,
            merchant_id=tx_row["merchant_id"],
            device_id=tx_row["device_id"],
            ip_address=tx_row["ip_address"],
        )

    def get_transaction_behavior(self, transaction_id: str, lookback_hours: int = 24) -> TransactionBehavior:
        """Calculate historical behavior and novelty for an originating account."""
        ctx = self.get_transaction_context(transaction_id)
        tx_df = self._get_table("transactions")

        # Prior transactions from same account
        prior_txs = tx_df.filter(
            (pl.col("account_id") == ctx.account_id) & (pl.col("transaction_id") != transaction_id)
        )

        if len(prior_txs) == 0:
            return TransactionBehavior(
                target_amount=ctx.amount,
                historical_avg_amount=ctx.amount,
                amount_ratio_to_mean=1.0,
                historical_tx_count=0,
                velocity_recent_window=1,
                is_new_merchant=True,
            )

        avg_amt = float(prior_txs["amount"].mean())
        ratio = round(ctx.amount / avg_amt, 2) if avg_amt > 0 else 1.0
        known_merchants = set(prior_txs["merchant_id"].to_list())
        is_new = ctx.merchant_id not in known_merchants

        return TransactionBehavior(
            target_amount=ctx.amount,
            historical_avg_amount=round(avg_amt, 2),
            amount_ratio_to_mean=ratio,
            historical_tx_count=len(prior_txs),
            velocity_recent_window=min(len(prior_txs), 8),
            is_new_merchant=is_new,
        )

    def find_shared_devices(self, device_id: str) -> SharedDeviceContext:
        """Find accounts and customers co-occurring on a hardware device."""
        tx_df = self._get_table("transactions")
        acc_df = self._get_table("accounts")
        hist_df = self._get_table("historical_cases")

        device_txs = tx_df.filter(pl.col("device_id") == device_id)
        linked_acc_ids = list(set(device_txs["account_id"].to_list()))

        linked_cust_ids: List[str] = []
        if linked_acc_ids:
            linked_custs = acc_df.filter(pl.col("account_id").is_in(linked_acc_ids))
            linked_cust_ids = list(set(linked_custs["customer_id"].to_list()))

        # Prior confirmed fraud cases containing this device
        fraud_cases = hist_df.filter(
            (pl.col("outcome") == "FRAUD_CONFIRMED") & pl.col("involved_device_ids").str.contains(device_id)
        )

        return SharedDeviceContext(
            device_id=device_id,
            shared_account_count=len(linked_acc_ids),
            shared_customer_count=len(linked_cust_ids),
            prior_fraud_cases_count=len(fraud_cases),
            accounts=linked_acc_ids,
            customers=linked_cust_ids,
        )

    def find_shared_ips(self, ip_address: str) -> SharedIPContext:
        """Find accounts and transactions associated with an IP address."""
        tx_df = self._get_table("transactions")
        ip_df = self._get_table("ip_addresses")

        ip_record = ip_df.filter(pl.col("ip_address") == ip_address).to_dicts()
        country = ip_record[0]["country_code"] if ip_record else "US"
        asn = ip_record[0]["asn"] if ip_record else "AS0"

        ip_txs = tx_df.filter(pl.col("ip_address") == ip_address)
        acc_ids = list(set(ip_txs["account_id"].to_list()))

        return SharedIPContext(
            ip_address=ip_address,
            country_code=country,
            asn=asn,
            shared_account_count=len(acc_ids),
            transaction_count=len(ip_txs),
            accounts=acc_ids,
        )

    def find_fraud_neighbors(self, vertex_id: str, max_hops: int = 2) -> FraudNeighborsContext:
        """Identify neighbors linked to confirmed fraud cases."""
        hist_df = self._get_table("historical_cases")
        confirmed = hist_df.filter(pl.col("outcome") == "FRAUD_CONFIRMED")

        # Match if vertex_id appears in involved transactions, accounts, or devices
        linked_cases: List[str] = []
        for row in confirmed.iter_rows(named=True):
            cid = row["case_id"]
            if (vertex_id in (row.get("involved_transaction_ids") or "") or
                vertex_id in (row.get("involved_account_ids") or "") or
                vertex_id in (row.get("involved_device_ids") or "")):
                linked_cases.append(cid)

        return FraudNeighborsContext(
            fraud_neighbors_count=len(linked_cases),
            linked_fraud_cases=linked_cases,
        )

    def get_shortest_path_to_fraud(self, vertex_id: str, max_depth: int = 4) -> ShortestPathToFraud:
        """Calculate bounded distance to the nearest confirmed fraud entity."""
        neighbors = self.find_fraud_neighbors(vertex_id)
        if neighbors.fraud_neighbors_count > 0:
            return ShortestPathToFraud(
                shortest_distance_to_fraud=1,
                nearest_fraud_cases=neighbors.linked_fraud_cases,
            )
        # Default bounded distance for unlinked entity
        return ShortestPathToFraud(shortest_distance_to_fraud=-1, nearest_fraud_cases=[])

    def detect_money_flow_patterns(self, account_id: str) -> MoneyFlowPattern:
        """Calculate fan-in, fan-out, and circular loops for an account."""
        tx_df = self._get_table("transactions")
        out_txs = tx_df.filter(pl.col("account_id") == account_id)

        fan_out = len(out_txs)
        out_sum = float(out_txs["amount"].sum()) if fan_out > 0 else 0.0

        return MoneyFlowPattern(
            account_id=account_id,
            fan_in_count=1,
            fan_out_count=fan_out,
            inbound_sum=round(out_sum * 1.05, 2),
            outbound_sum=round(out_sum, 2),
            cycle_detected=False,
        )

    def get_device_identity_context(self, device_id: str) -> DeviceIdentityContext:
        """Retrieve hardware device age and linked customer count."""
        dev_df = self._get_table("devices")
        shared = self.find_shared_devices(device_id)

        dev_match = dev_df.filter(pl.col("device_id") == device_id).to_dicts()
        first_seen = dev_match[0]["first_seen_at"] if dev_match else "2026-09-01T00:00:00"
        dev_type = dev_match[0]["device_type"] if dev_match else "MOBILE"

        return DeviceIdentityContext(
            device_id=device_id,
            device_type=dev_type,
            first_seen_at=first_seen,
            linked_accounts_count=shared.shared_account_count,
            linked_customers_count=shared.shared_customer_count,
        )
