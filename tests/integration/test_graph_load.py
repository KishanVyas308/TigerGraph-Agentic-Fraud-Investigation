"""Integration tests for TigerGraph data loading pipeline."""

from pathlib import Path
import pytest

from scripts.load_tigergraph import run_loader, check_tigergraph_connection
from backend.app.config import get_settings


def test_tigergraph_connectivity_check():
    """Verify connectivity checker handles active or inactive endpoints safely."""
    settings = get_settings()
    # Check default endpoint - should return boolean without uncaught exception
    status = check_tigergraph_connection(settings.TIGERGRAPH_HOST)
    assert isinstance(status, bool)


def test_end_to_end_loading_pipeline_dry_run(tmp_path: Path):
    """Verify complete loading pipeline executes deterministically."""
    processed_dir = Path("data/processed")
    staging_dir = tmp_path / "staging"

    summary = run_loader(
        processed_dir=processed_dir,
        dry_run=True,
        staging_dir=staging_dir,
    )

    assert summary["status"] == "verified_dry_run"
    assert summary["staged_files_count"] == 12
    assert summary["source_counts"]["transactions"] == 500
    assert summary["source_counts"]["customers"] == 100
    assert summary["source_counts"]["accounts"] == 150
    assert summary["source_counts"]["devices"] == 60
    assert summary["source_counts"]["ip_addresses"] == 50
    assert summary["source_counts"]["merchants"] == 40
    assert summary["source_counts"]["historical_cases"] == 30

    # Ensure staging directory has all generated CSVs
    csv_files = list(staging_dir.glob("*.csv"))
    assert len(csv_files) == 12
