"""Reporting package initialization (Layer 22).

Exports:
- SARSubject, SARSuspiciousActivity, SARNarrative, SARReport
- SARGenerator, generate_case_sar, SAR_AUDIT_DISCLAIMER
"""

from backend.app.reporting.sar_generator import (
    SAR_AUDIT_DISCLAIMER,
    SARGenerator,
    SARNarrative,
    SARReport,
    SARSubject,
    SARSuspiciousActivity,
    generate_case_sar,
)

__all__ = [
    "SARSubject",
    "SARSuspiciousActivity",
    "SARNarrative",
    "SARReport",
    "SARGenerator",
    "generate_case_sar",
    "SAR_AUDIT_DISCLAIMER",
]
