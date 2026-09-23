"""Historical LightGBM Risk Signal Service (Layer 13).

Provides an optional historical ML risk signal (`historical_ml_score`) trained on permitted historical closed cases.

IMPORTANT RULES (AGENTS.md & GEMINI.md):
- Signal is named `historical_ml_score` (never `is_fraud` or ground truth probability).
- Optional supporting signal only — does not make final fraud decisions.
- Strictly isolated from benchmark cases (CASE_001 to CASE_020).
- Fallbacks gracefully to `None` if LightGBM is disabled or model weights are missing.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.features.engine import FraudFeatureSet
from backend.app.utils.logging import get_logger

logger = get_logger("features.lightgbm_signal")

# Optional LightGBM import with graceful fallback
try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    lgb = None
    HAS_LIGHTGBM = False


# Canonical feature ordering used during model training and inference
FEATURE_NAMES: List[str] = [
    "shared_device_account_count",
    "shared_device_customer_count",
    "fraud_accounts_on_device",
    "shared_ip_account_count",
    "shared_ip_customer_count",
    "fraud_neighbors_count",
    "shortest_distance_to_fraud",
    "connected_component_size",
    "community_size",
    "transaction_count_5m",
    "transaction_count_10m",
    "transaction_count_1h",
    "transaction_count_24h",
    "transaction_amount_ratio_to_mean",
    "transaction_amount_ratio_to_median",
    "new_device",
    "new_ip",
    "new_merchant",
    "fan_in_count",
    "fan_out_count",
    "cycle_detected",
    "rapid_pass_through",
    "bank_risk_score",
]


class LightGBMSignalResult(BaseModel):
    """Result payload from the LightGBM historical risk signal model."""

    model_config = ConfigDict(extra="ignore")

    historical_ml_score: Optional[float] = Field(
        default=None,
        description="Optional historical ML risk score bounded [0.0, 1.0]. None if disabled/unavailable.",
    )
    model_version: str = Field(
        default="DISABLED",
        description="Version or identifier of the LightGBM model used.",
    )
    is_enabled: bool = Field(
        default=False,
        description="Whether the LightGBM model signal is actively enabled and evaluated.",
    )
    feature_importance: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional feature importance weights if available.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error or explanation if model evaluation fell back to disabled state.",
    )


class LightGBMRiskSignal:
    """Service wrapping LightGBM model loading and inference for historical risk scoring."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        enable: Optional[bool] = None,
        data_dir: Optional[Path] = None,
    ):
        settings = get_settings()
        self.data_dir = data_dir or settings.PROCESSED_DATA_DIR
        self.enabled = enable if enable is not None else settings.ENABLE_LIGHTGBM
        self.model_path = model_path or (self.data_dir / "lightgbm_fraud_model.txt")

        self.model: Any = None
        self.model_version: str = "DISABLED"

        if self.enabled:
            self._load_model()

    def _load_model(self) -> None:
        """Attempt to load trained LightGBM model file."""
        if not HAS_LIGHTGBM:
            logger.warning("LightGBM package is not installed. Historical ML risk signal disabled.")
            self.enabled = False
            return

        if not self.model_path.exists():
            logger.info("LightGBM model weights file %s does not exist. Signal disabled.", self.model_path)
            self.enabled = False
            return

        try:
            self.model = lgb.Booster(model_file=str(self.model_path))
            self.model_version = "lightgbm_v1.0"
            logger.info("Successfully loaded LightGBM model from %s", self.model_path)
        except Exception as exc:
            logger.warning("Failed to load LightGBM model from %s: %s", self.model_path, exc)
            self.enabled = False
            self.model = None

    def feature_set_to_vector(
        self,
        features: Union[FraudFeatureSet, Dict[str, Any]],
        bank_risk_score: Optional[float] = None,
    ) -> np.ndarray:
        """Convert a FraudFeatureSet or dict into an ordered numpy float array with NaN for missing values."""
        feat_dict = features.to_dict() if isinstance(features, FraudFeatureSet) else dict(features)

        vector = []
        for name in FEATURE_NAMES:
            if name == "bank_risk_score":
                val = bank_risk_score if bank_risk_score is not None else feat_dict.get("bank_risk_score")
            else:
                val = feat_dict.get(name)

            if val is None:
                vector.append(np.nan)
            elif isinstance(val, bool):
                vector.append(1.0 if val else 0.0)
            else:
                try:
                    vector.append(float(val))
                except (ValueError, TypeError):
                    vector.append(np.nan)

        return np.array([vector], dtype=np.float32)

    def predict(
        self,
        features: Union[FraudFeatureSet, Dict[str, Any]],
        bank_risk_score: Optional[float] = None,
    ) -> LightGBMSignalResult:
        """Predict historical_ml_score using the loaded LightGBM model.

        Gracefully falls back to None if model is disabled or unavailable.
        """
        if not self.enabled or self.model is None or not HAS_LIGHTGBM:
            return LightGBMSignalResult(
                historical_ml_score=None,
                model_version="DISABLED",
                is_enabled=False,
                error="LightGBM signal is disabled or model weights are missing.",
            )

        try:
            X = self.feature_set_to_vector(features, bank_risk_score=bank_risk_score)
            raw_prob = float(self.model.predict(X)[0])
            score = round(max(0.0, min(1.0, raw_prob)), 4)

            # Feature importances if available
            importances: Dict[str, float] = {}
            if hasattr(self.model, "feature_importance"):
                raw_imp = self.model.feature_importance(importance_type="gain")
                for fn, imp in zip(FEATURE_NAMES, raw_imp):
                    importances[fn] = round(float(imp), 4)

            return LightGBMSignalResult(
                historical_ml_score=score,
                model_version=self.model_version,
                is_enabled=True,
                feature_importance=importances,
            )

        except Exception as exc:
            logger.error("Error evaluating LightGBM risk model: %s", exc)
            return LightGBMSignalResult(
                historical_ml_score=None,
                model_version="ERROR",
                is_enabled=False,
                error=f"Inference failure: {exc}",
            )
