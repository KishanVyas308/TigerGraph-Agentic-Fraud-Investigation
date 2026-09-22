"""Unit tests for dataset inspection and data dictionary generation."""

import json
from pathlib import Path
import polars as pl
from scripts.inspect_dataset import inspect_dataset_directory, detect_file_type


def test_detect_file_type():
    """Verify file type detection handles expected extensions."""
    assert detect_file_type(Path("test.csv")) == "csv"
    assert detect_file_type(Path("test.parquet")) == "parquet"
    assert detect_file_type(Path("README.md")) == "markdown"
    assert detect_file_type(Path("metadata.json")) == "json"
    assert detect_file_type(Path("unknown.xyz")) == "unknown"


def test_inspect_dataset_directory(tmp_path: Path):
    """Verify inspecting a sample dataset creates structured catalog."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # Create dummy transaction CSV
    df = pl.DataFrame({
        "transaction_id": ["TX001", "TX002"],
        "customer_id": ["CUST01", "CUST02"],
        "amount": [120.50, 450.00],
        "bank_risk_score": [0.12, 0.88],
    })
    csv_file = raw_dir / "transactions.csv"
    df.write_csv(csv_file)

    # Create dummy README
    readme_file = raw_dir / "README.md"
    readme_file.write_text("# Dataset Documentation\nSample transactions dataset.")

    output_json = tmp_path / "data_dictionary.json"
    report = inspect_dataset_directory(raw_dir, output_json)

    assert report["file_count"] == 2
    assert output_json.exists()

    with open(output_json, "r") as f:
        data = json.load(f)

    assert data["file_count"] == 2
    csv_meta = next(item for item in data["files"] if item["filename"] == "transactions.csv")
    assert csv_meta["total_rows"] == 2
    assert csv_meta["column_count"] == 4

    roles = {col["column_name"]: col["inferred_role"] for col in csv_meta["columns"]}
    assert roles["transaction_id"] == "transaction_id"
    assert roles["customer_id"] == "customer_id"
    assert roles["bank_risk_score"] == "risk_score_signal"
