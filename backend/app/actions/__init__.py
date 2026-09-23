"""Actions package initialization (Layer 20).

Exports ApprovalRequest and process_analyst_decision.
"""

from backend.app.actions.approval import ApprovalRequest, process_analyst_decision

__all__ = [
    "ApprovalRequest",
    "process_analyst_decision",
]
