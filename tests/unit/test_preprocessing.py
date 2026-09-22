"""Unit tests for dataset preprocessing and canonical entity tables."""

import json
from pathlib import Path
import polars as pl
import pytest

from scripts.preprocess_dataset import (
    generate_canonical_seed_data,
    verify_referential_integrity,
    save_canonical_tables,
)


def test_generate_canonical_seed_data():
    """Verify generated canonical tables have expected schema and row counts."""
    tables = generate_canonical_seed_data()

    assert "customers" in tables
    assert "accounts" in tables
    assert "devices" in tables
    assert "ip_addresses" in tables
    assert "merchants" in tables
    assert "transactions" in tables
    assert "historical_cases" in tables
    assert "benchmark_cases" in tables
    assert "policies" in tables
    assert "typologies" in tables

    assert len(tables["customers"]) == 100
    assert len(tables["accounts"]) == 150
    assert len(tables["devices"]) == 60
    assert len(tables["ip_addresses"]) == 50
    assert len(tables["merchants"]) == 40
    assert len(tables["transactions"]) == 500
    assert len(tables["historical_cases"]) == 30
    assert len(tables["benchmark_cases"]) == 20


def test_referential_integrity_success():
    """Verify valid canonical seed data passes all integrity checks."""
    tables = generate_canonical_seed_data()
    is_valid, errors = verify_referential_integrity(tables)

    assert is_valid is True
    assert len(errors) == 0


def test_referential_integrity_catches_invalid_foreign_key():
    """Verify that corrupt foreign keys are detected by the integrity validator."""
    tables = generate_canonical_seed_data()
    # Inject invalid customer ID in accounts
    accounts = tables["accounts"]
    corrupted_accounts = accounts.with_columns(
        pl.when(pl.col("account_id") == "ACC_001")
        .then(pl.lit("CUST_NON_EXISTENT"))
        .otherwise(pl.col("customer_id"))
        .alias("customer_id")
    )
    corrupted_tables = {**tables, "accounts": corrupted_accounts}

    is_valid, errors = verify_referential_integrity(corrupted_tables)
    assert is_valid is False
    assert any("Accounts reference missing customer IDs" in e for e in errors)


def test_benchmark_cases_isolation():
    """Verify benchmark cases contain exactly 20 cases and no ground truth labels."""
    tables = generate_canonical_seed_data()
    benchmark_df = tables["benchmark_cases"]

    assert len(benchmark_df) == 20
    case_ids = benchmark_df["case_id"].to_list()
    assert case_ids[0] == "CASE_001"
    assert case_ids[-1] == "CASE_020"

    # Leakage check: no outcome/label column
    assert "outcome" not in benchmark_df.columns
    assert "is_fraud" not in benchmark_df.columns
    assert "ground_truth" not in benchmark_df.columns


def test_save_canonical_tables(tmp_path: Path):
    """Verify saving tables produces valid Parquet files and preprocessing report."""
    tables = generate_canonical_seed_data()
    report = save_canonical_tables(tables, tmp_path)

    assert report["status"] == "passed"
    assert report["benchmark_cases_count"] == 20
    assert report["historical_cases_count"] == 30

    report_file = tmp_path / "preprocessing_report.json"
    assert report_file.exists()

    # Read back a parquet file with Polars
    tx_parquet = tmp_path / "transactions.parquet"
    assert tx_parquet.exists()
    df = pl.read_parquet(tx_parquet)
    assert len(df) == 500
    assert "amount" in df.columns
    assert "bank_risk_score" in df.columns
