"""Policy Configuration Loader (Layer 19).

Loads deterministic policy configurations from `policy.yaml` or fallback dicts.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from backend.app.utils.logging import get_logger

logger = get_logger("policies.loader")

# Default search paths for policy.yaml
DEFAULT_POLICY_PATHS = [
    Path("backend/app/policies/policy.yaml"),
    Path("config/policy.yaml"),
]


def load_policy_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load policy dictionary from specified path or default search locations."""
    target_path: Optional[Path] = None

    if config_path:
        p = Path(config_path)
        if p.exists():
            target_path = p
        else:
            logger.warning("Specified policy config path '%s' not found.", config_path)

    if target_path is None:
        for p in DEFAULT_POLICY_PATHS:
            if p.exists():
                target_path = p
                break

    if target_path and target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "policies" in data:
                    logger.info("Successfully loaded policy configuration from '%s'", target_path)
                    return data["policies"]
                elif isinstance(data, dict):
                    return data
        except Exception as exc:
            logger.error("Failed to parse policy YAML from '%s': %s", target_path, exc)

    logger.warning("Using built-in fallback policy configuration.")
    return _get_fallback_policy_config()


def _get_fallback_policy_config() -> Dict[str, Any]:
    """Return hardcoded fallback policy rules if configuration file is unavailable."""
    return {
        "ALLOW_TRANSACTION": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.0,
            "max_risk_score": 0.70,
            "required_prerequisites": [],
            "policy_reference": "POL_003",
        },
        "BLOCK_TRANSACTION": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.60,
            "max_risk_score": 1.00,
            "required_prerequisites": ["transaction_id"],
            "policy_reference": "POL_001",
        },
        "MONITOR_TRANSACTION": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.30,
            "max_risk_score": 0.85,
            "required_prerequisites": ["transaction_id"],
            "policy_reference": "POL_005",
        },
        "MONITOR_ACCOUNT": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.30,
            "max_risk_score": 0.90,
            "required_prerequisites": ["account_ids"],
            "policy_reference": "POL_005",
        },
        "BLOCK_ACCOUNT": {
            "allowed": True,
            "autonomous": False,
            "approval_required": True,
            "approval_role": "SENIOR_ANALYST",
            "report_required": False,
            "min_risk_score": 0.75,
            "max_risk_score": 1.00,
            "required_prerequisites": ["customer_id", "account_ids"],
            "policy_reference": "POL_002",
        },
        "WARN_CUSTOMER": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.30,
            "max_risk_score": 0.75,
            "required_prerequisites": ["customer_id"],
            "policy_reference": "POL_003",
        },
        "REQUEST_CUSTOMER_CONFIRMATION": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.40,
            "max_risk_score": 0.85,
            "required_prerequisites": ["customer_id"],
            "policy_reference": "POL_003",
        },
        "REQUEST_STEP_UP_AUTH": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.45,
            "max_risk_score": 0.90,
            "required_prerequisites": ["customer_id"],
            "policy_reference": "POL_003",
        },
        "REQUEST_ANALYST_EVIDENCE": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.50,
            "max_risk_score": 1.00,
            "required_prerequisites": ["case_id"],
            "policy_reference": "POL_005",
        },
        "ESCALATE_ANALYST": {
            "allowed": True,
            "autonomous": False,
            "approval_required": True,
            "approval_role": "ANALYST",
            "report_required": False,
            "min_risk_score": 0.50,
            "max_risk_score": 1.00,
            "required_prerequisites": ["case_id"],
            "policy_reference": "POL_005",
        },
        "FILE_SAR": {
            "allowed": True,
            "autonomous": False,
            "approval_required": True,
            "approval_role": "COMPLIANCE_OFFICER",
            "report_required": True,
            "min_risk_score": 0.80,
            "max_risk_score": 1.00,
            "required_prerequisites": ["case_id", "customer_id"],
            "policy_reference": "POL_004",
        },
        "CLOSE_CASE": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.0,
            "max_risk_score": 0.40,
            "required_prerequisites": ["case_id"],
            "policy_reference": "GENERAL_CLOSE_POLICY",
        },
        "NO_ACTION": {
            "allowed": True,
            "autonomous": True,
            "approval_required": False,
            "approval_role": "SYSTEM_AUTOMATIC",
            "report_required": False,
            "min_risk_score": 0.0,
            "max_risk_score": 1.00,
            "required_prerequisites": [],
            "policy_reference": "GENERAL_NO_ACTION_POLICY",
        },
    }
