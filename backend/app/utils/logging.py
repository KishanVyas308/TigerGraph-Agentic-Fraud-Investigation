"""Structured logging utility for TigerGraph Agentic Fraud Investigation."""

import json
import logging
import sys
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Custom logging formatter outputting clean, human-readable structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S")
        extra_fields: Dict[str, Any] = {}
        for key, val in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message"
            }:
                extra_fields[key] = val

        extra_str = f" | {json.dumps(extra_fields)}" if extra_fields else ""
        return f"[{timestamp}] [{record.levelname:<7}] [{record.name}] {record.getMessage()}{extra_str}"


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with structured formatter."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(StructuredFormatter())


def get_logger(name: str) -> logging.Logger:
    """Retrieve a namespaced logger."""
    return logging.getLogger(name)
