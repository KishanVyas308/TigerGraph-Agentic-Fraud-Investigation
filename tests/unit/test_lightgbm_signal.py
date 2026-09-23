"""Unit tests for Layer 13: Historical LightGBM Risk Signal."""

from pathlib import Path

import numpy as np
import pytest

from backend.app.features.engine import FraudFeatureSet
from backend.app.features.lightgbm_signal import (
    FEATURE_NAMES,
    LightGBMRiskSignal,
    LightGBMSignalResult,
)
from scripts.train_lightgbm import load_historical_training_data


def test_feature_vector_conversion():
    """Verify FraudFeatureSet conversion to numpy vector with NaN missing handling."""
    signal = LightGBMRiskSignal(enable=False)

    features = FraudFeatureSet(
        shared_device_account_count=4,
        fraud_neighbors_count=2,
        new_merchant=True,
        transaction_amount_ratio_to_mean=3.5,
    )

    vec = signal.feature_set_to_vector(features, bank_risk_score=75.0)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (1, len(FEATURE_NAMES))

    # Check specific feature values by name index
    idx_dev = FEATURE_NAMES.index("shared_device_account_count")
    idx_mch = FEATURE_NAMES.index("new_merchant")
    idx_ip = FEATURE_NAMES.index("shared_ip_account_count")
    idx_bank = FEATURE_NAMES.index("bank_risk_score")

    assert vec[0, idx_dev] == 4.0
    assert vec[0, idx_mch] == 1.0
    assert np.isnan(vec[0, idx_ip])
    assert vec[0, idx_bank] == 75.0


def test_disabled_signal_fallback():
    """Verify graceful fallback when LightGBM signal is explicitly disabled."""
    signal = LightGBMRiskSignal(enable=False)
    features = FraudFeatureSet(shared_device_account_count=3)

    result = signal.predict(features)

    assert isinstance(result, LightGBMSignalResult)
    assert result.historical_ml_score is None
    assert result.is_enabled is False
    assert result.model_version == "DISABLED"
    assert "disabled" in result.error.lower()


def test_missing_model_file_fallback(tmp_path):
    """Verify fallback when model weights file does not exist."""
    fake_path = tmp_path / "non_existent_model.txt"
    signal = LightGBMRiskSignal(model_path=fake_path, enable=True)

    assert signal.enabled is False
    features = FraudFeatureSet(shared_device_account_count=3)
    result = signal.predict(features)

    assert result.historical_ml_score is None
    assert result.is_enabled is False


def test_enabled_signal_inference():
    """Verify inference when LightGBM model weights exist."""
    settings = LightGBMRiskSignal(enable=True)
    if not settings.enabled:
        pytest.skip("LightGBM model not trained or disabled locally.")

    features = FraudFeatureSet(
        shared_device_account_count=5,
        fraud_neighbors_count=3,
        transaction_amount_ratio_to_mean=4.2,
        rapid_pass_through=True,
    )

    result = settings.predict(features, bank_risk_score=85.0)

    assert result.is_enabled is True
    assert result.historical_ml_score is not None
    assert 0.0 <= result.historical_ml_score <= 1.0
    assert result.model_version.startswith("lightgbm_")


def test_benchmark_isolation_in_training(tmp_path):
    """Verify benchmark cases (CASE_001 - CASE_020) are strictly excluded from training data."""
    data_dir = Path("data/processed")
    if not (data_dir / "historical_cases.parquet").exists():
        pytest.skip("historical_cases.parquet not found.")

    X, y, case_ids = load_historical_training_data(data_dir)

    for cid in case_ids:
        assert not cid.startswith("CASE_"), f"Benchmark case {cid} leaked into LightGBM training data!"
