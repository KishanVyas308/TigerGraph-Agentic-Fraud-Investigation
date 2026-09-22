"""Unit tests for ID, time, and logging utilities."""

from datetime import datetime, timezone
from backend.app.utils.ids import (
    generate_case_id,
    generate_evidence_id,
    generate_event_id,
    generate_action_id,
    generate_uuid,
    generate_deterministic_id,
)
from backend.app.utils.time import now_utc, now_iso, format_utc, parse_iso
from backend.app.utils.logging import get_logger, setup_logging


def test_id_generation_formats():
    """Verify generated IDs have correct prefixes and lengths."""
    case_id = generate_case_id()
    assert case_id.startswith("CASE_")
    assert len(case_id) == 13  # CASE_ + 8 hex chars

    evd_id = generate_evidence_id()
    assert evd_id.startswith("EVD_")

    evt_id = generate_event_id()
    assert evt_id.startswith("EVT_")

    act_id = generate_action_id()
    assert act_id.startswith("ACT_")

    uid = generate_uuid()
    assert len(uid) == 36


def test_deterministic_id():
    """Verify deterministic ID produces identical output for identical input."""
    id1 = generate_deterministic_id("TX", "user_123", "2026-09-23", "100.50")
    id2 = generate_deterministic_id("TX", "user_123", "2026-09-23", "100.50")
    id3 = generate_deterministic_id("TX", "user_456", "2026-09-23", "100.50")

    assert id1.startswith("TX_")
    assert id1 == id2
    assert id1 != id3


def test_time_utc_handling():
    """Verify UTC time helpers always preserve UTC timezone."""
    dt = now_utc()
    assert dt.tzinfo == timezone.utc

    iso_str = now_iso()
    parsed = parse_iso(iso_str)
    assert parsed.tzinfo == timezone.utc

    # Test naive datetime formatting adds UTC
    naive_dt = datetime(2026, 9, 23, 12, 0, 0)
    formatted = format_utc(naive_dt)
    assert formatted.endswith("+00:00")


def test_logging_configuration():
    """Verify logger setup runs without errors."""
    setup_logging(level="DEBUG")
    logger = get_logger("test.logger")
    assert logger is not None
