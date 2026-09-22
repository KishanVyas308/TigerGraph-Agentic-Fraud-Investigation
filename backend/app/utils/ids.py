"""Identifier utilities for cases, evidence, events, and actions."""

import hashlib
import uuid
from typing import Optional


def generate_uuid() -> str:
    """Generate a random standard UUID4 string."""
    return str(uuid.uuid4())


def generate_prefixed_id(prefix: str, length: int = 8) -> str:
    """Generate a compact prefixed ID using random UUID hex."""
    random_hex = uuid.uuid4().hex[:length].upper()
    return f"{prefix}_{random_hex}"


def generate_case_id() -> str:
    """Generate a new case identifier (e.g., CASE_A1B2C3D4)."""
    return generate_prefixed_id("CASE", length=8)


def generate_evidence_id() -> str:
    """Generate a new evidence identifier (e.g., EVD_A1B2C3D4)."""
    return generate_prefixed_id("EVD", length=8)


def generate_event_id() -> str:
    """Generate a new event/timeline identifier (e.g., EVT_A1B2C3D4)."""
    return generate_prefixed_id("EVT", length=8)


def generate_action_id() -> str:
    """Generate a new action identifier (e.g., ACT_A1B2C3D4)."""
    return generate_prefixed_id("ACT", length=8)


def generate_deterministic_id(prefix: str, *components: str) -> str:
    """Generate a deterministic ID from input components using SHA-256 hash."""
    seed = ":".join(str(c) for c in components)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}_{digest}"
