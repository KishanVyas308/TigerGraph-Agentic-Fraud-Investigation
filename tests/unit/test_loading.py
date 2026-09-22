"""Unit tests for TigerGraph GSQL loading jobs and loader script."""

from pathlib import Path
import polars as pl
import pytest

from scripts.load_tigergraph import (
    export_parquet_to_csv_staging,
    validate_canonical_data_readiness,
    run_loader,
)

CORE_LOADING_JOB = Path("gsql/loading/load_core_data.gsql")
CASES_LOADING_JOB = Path("gsql/loading/load_cases.gsql")


def test_loading_jobs_exist_and_valid():
    """Verify that both GSQL loading job files exist and have valid syntax."""
    assert CORE_LOADING_JOB.exists()
    assert CASES_LOADING_JOB.exists()

    core_content = CORE_LOADING_JOB.read_text(encoding="utf-8")
    assert "CREATE LOADING JOB load_core_data" in core_content
    assert "LOAD customer_file TO VERTEX Customer" in core_content
    assert "LOAD account_file TO VERTEX Account" in core_content
    assert "LOAD transaction_file TO VERTEX Transaction" in core_content
    assert "LOAD account_file TO EDGE CUSTOMER_OWNS_ACCOUNT" in core_content
    assert "LOAD transaction_file TO EDGE ACCOUNT_PERFORMED_TRANSACTION" in core_content

    cases_content = CASES_LOADING_JOB.read_text(encoding="utf-8")
    assert "CREATE LOADING JOB load_cases" in cases_content
    assert "LOAD case_file TO VERTEX FraudCase" in cases_content
    assert "LOAD policy_file TO VERTEX Policy" in cases_content
    assert "LOAD typology_file TO VERTEX Typology" in cases_content
    assert "LOAD case_file TO EDGE CASE_MATCHES_TYPOLOGY" in cases_content


def test_validate_canonical_data_readiness():
    """Verify data readiness validator succeeds on processed directory."""
    readiness = validate_canonical_data_readiness(Path("data/processed"))
    assert readiness["status"] == "ready"
    assert readiness["counts"]["customers"] == 100
    assert readiness["counts"]["transactions"] == 500
    assert readiness["counts"]["historical_cases"] == 30


def test_export_parquet_to_csv_staging(tmp_path: Path):
    """Verify staging exports Parquet tables and creates derived case links."""
    staged = export_parquet_to_csv_staging(Path("data/processed"), tmp_path)

    assert "customers" in staged
    assert "transactions" in staged
    assert "case_tx" in staged
    assert "case_acc" in staged
    assert "case_dev" in staged

    # Check case-tx link file
    case_tx_df = pl.read_csv(staged["case_tx"])
    assert len(case_tx_df) == 30
    assert "case_id" in case_tx_df.columns
    assert "transaction_id" in case_tx_df.columns


def test_run_loader_dry_run(tmp_path: Path):
    """Verify loader completes in dry-run mode without external connection."""
    summary = run_loader(
        processed_dir=Path("data/processed"),
        dry_run=True,
        staging_dir=tmp_path,
    )
    assert summary["status"] == "verified_dry_run"
    assert summary["simulated_loaded_vertices"] == 940
    assert summary["simulated_loaded_edges"] > 1000
