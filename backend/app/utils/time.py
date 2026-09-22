"""UTC timestamp utilities for the TigerGraph Agentic Fraud Investigation system."""

from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO-8601 string."""
    return now_utc().isoformat()


def format_utc(dt: Optional[datetime] = None) -> str:
    """Format a datetime as an ISO-8601 string with UTC guarantee."""
    if dt is None:
        dt = now_utc()
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def parse_iso(iso_str: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware UTC datetime."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
