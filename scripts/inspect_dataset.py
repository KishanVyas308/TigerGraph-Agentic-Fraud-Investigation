#!/usr/bin/env python3
"""Dataset Inspection and Data Dictionary Generator for TigerGraph Agentic Fraud Investigation.

Reads raw dataset files (CSV, Parquet, JSON, JSONL, Markdown), analyzes column types,
null counts, distinct counts, date ranges, and generates data/processed/data_dictionary.json.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb
import polars as pl

from backend.app.utils.logging import get_logger, setup_logging
from backend.app.utils.time import now_iso

setup_logging("INFO")
logger = get_logger("scripts.inspect_dataset")


def detect_file_type(file_path: Path) -> str:
    """Return normalized file format extension."""
    suffix = file_path.suffix.lower()
    if suffix in [".csv", ".tsv"]:
        return "csv"
    if suffix in [".parquet", ".pq"]:
        return "parquet"
    if suffix in [".json", ".jsonl"]:
        return "json"
    if suffix in [".md", ".markdown"]:
        return "markdown"
    if suffix in [".txt"]:
        return "text"
    return "unknown"


def inspect_tabular_file(file_path: Path, file_type: str) -> Dict[str, Any]:
    """Inspect CSV or Parquet tabular file using Polars and DuckDB."""
    logger.info("Inspecting tabular file: %s", file_path.name)
    try:
        if file_type == "csv":
            df = pl.read_csv(file_path, n_rows=10000, ignore_errors=True)
            # Count total rows using duckdb for memory efficiency
            total_rows = duckdb.execute(f"SELECT count(*) FROM read_csv_auto('{file_path}')").fetchone()[0]
        elif file_type == "parquet":
            df = pl.read_parquet(file_path, n_rows=10000)
            total_rows = duckdb.execute(f"SELECT count(*) FROM read_parquet('{file_path}')").fetchone()[0]
        else:
            return {"error": f"Unsupported tabular type {file_type}"}

        columns_meta: List[Dict[str, Any]] = []
        for col in df.columns:
            series = df[col]
            null_count = series.null_count()
            dtype_str = str(series.dtype)
            n_unique = series.n_unique()

            # Identify role heuristics
            inferred_role = "attribute"
            lower_name = col.lower()
            if any(k in lower_name for k in ["transaction_id", "tx_id", "trans_id"]):
                inferred_role = "transaction_id"
            elif any(k in lower_name for k in ["customer_id", "cust_id", "user_id", "party_id"]):
                inferred_role = "customer_id"
            elif any(k in lower_name for k in ["account_id", "acc_id", "card_id", "card_number", "pan"]):
                inferred_role = "account_or_card_id"
            elif any(k in lower_name for k in ["device_id", "device_fingerprint", "mac_address"]):
                inferred_role = "device_id"
            elif any(k in lower_name for k in ["ip_address", "ip", "client_ip"]):
                inferred_role = "ip_address"
            elif any(k in lower_name for k in ["merchant_id", "merchant_name", "merchant"]):
                inferred_role = "merchant_id"
            elif any(k in lower_name for k in ["case_id", "investigation_id"]):
                inferred_role = "case_id"
            elif any(k in lower_name for k in ["risk_score", "bank_risk", "model_score", "fraud_score"]):
                inferred_role = "risk_score_signal"
            elif any(k in lower_name for k in ["label", "outcome", "case_decision", "resolution"]):
                inferred_role = "historical_case_outcome"
            elif any(k in lower_name for k in ["time", "date", "timestamp"]):
                inferred_role = "timestamp"

            # Sample values (convert non-serializables)
            samples = [str(v) if v is not None else None for v in series.drop_nulls().head(3).to_list()]

            columns_meta.append({
                "column_name": col,
                "data_type": dtype_str,
                "sample_null_count": null_count,
                "sample_unique_count": n_unique,
                "inferred_role": inferred_role,
                "sample_values": samples,
            })

        return {
            "filename": file_path.name,
            "format": file_type,
            "file_size_bytes": file_path.stat().st_size,
            "total_rows": total_rows,
            "column_count": len(df.columns),
            "columns": columns_meta,
        }
    except Exception as exc:
        logger.error("Error inspecting %s: %s", file_path, exc)
        return {
            "filename": file_path.name,
            "format": file_type,
            "error": str(exc),
        }


def inspect_text_or_markdown(file_path: Path, file_type: str) -> Dict[str, Any]:
    """Inspect text, markdown, policy, or README documents."""
    logger.info("Inspecting document: %s", file_path.name)
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        headings = [line.strip() for line in lines if line.strip().startswith("#")]

        inferred_category = "document"
        lower_name = file_path.name.lower()
        if "readme" in lower_name:
            inferred_category = "dataset_documentation"
        elif "policy" in lower_name:
            inferred_category = "fraud_policy"
        elif "typolog" in lower_name:
            inferred_category = "fraud_typology"
        elif "regulat" in lower_name:
            inferred_category = "regulatory_guidance"
        elif "benchmark" in lower_name:
            inferred_category = "benchmark_cases"

        return {
            "filename": file_path.name,
            "format": file_type,
            "file_size_bytes": file_path.stat().st_size,
            "line_count": len(lines),
            "inferred_category": inferred_category,
            "headings_sample": headings[:10],
            "preview": lines[:5],
        }
    except Exception as exc:
        logger.error("Error reading %s: %s", file_path, exc)
        return {"filename": file_path.name, "format": file_type, "error": str(exc)}


def inspect_dataset_directory(data_dir: Path, output_file: Path) -> Dict[str, Any]:
    """Scan all files in data_dir, extract metadata, and save data dictionary."""
    if not data_dir.exists():
        logger.warning("Data directory does not exist: %s", data_dir)
        return {"error": f"Directory not found: {data_dir}", "files": []}

    files = [p for p in data_dir.glob("**/*") if p.is_file() and not p.name.startswith(".")]
    logger.info("Discovered %d files in %s", len(files), data_dir)

    catalog: List[Dict[str, Any]] = []
    for file_path in sorted(files):
        fmt = detect_file_type(file_path)
        if fmt in ["csv", "parquet"]:
            catalog.append(inspect_tabular_file(file_path, fmt))
        elif fmt in ["markdown", "text", "json"]:
            catalog.append(inspect_text_or_markdown(file_path, fmt))
        else:
            catalog.append({
                "filename": file_path.name,
                "format": fmt,
                "file_size_bytes": file_path.stat().st_size,
                "note": "Binary or unknown file type",
            })

    report = {
        "timestamp": now_iso(),
        "dataset_directory": str(data_dir.resolve()),
        "file_count": len(files),
        "files": catalog,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Data dictionary saved successfully to %s", output_file)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect dataset and build data dictionary.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw"),
        help="Path to raw dataset directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/data_dictionary.json"),
        help="Path to output data dictionary JSON",
    )
    args = parser.parse_args()

    report = inspect_dataset_directory(args.data_dir, args.output)
    print(f"\n--- Inspection Summary ---")
    print(f"Files inspected: {report.get('file_count', 0)}")
    print(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()
