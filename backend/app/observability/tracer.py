"""Local Audit Trail and Observability Engine (Layer 34).

Provides structured, append-only JSONL tracing under `outputs/traces/{case_id}.jsonl`
tracking:
- LangGraph node start/finish and execution durations,
- TigerGraph GSQL query latency and record metrics,
- GraphRAG policy & case retrieval latency,
- LLM model invocation metadata (provider, model, duration),
- Policy authorization decisions and prerequisite checks,
- Human approval decisions and action modifications,
- Simulated action executions and error states.

Enforces strict secrets sanitization (no API keys, secrets, or passwords logged per AGENTS.md §32)
and supports optional Langfuse exporting behind a feature flag.
"""

from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from pathlib import Path
import json
import os
import re
import time
from typing import Any, Dict, Generator, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.utils.ids import generate_prefixed_id
from backend.app.utils.logging import get_logger
from backend.app.utils.time import now_iso

logger = get_logger("observability.tracer")

# Sensitive key regex patterns to sanitize per AGENTS.md §32
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(key|secret|password|token|auth|credential|bearer|private)"
)


class SpanType(str, Enum):
    """Categorical types of audited execution spans."""
    NODE_EXECUTION = "NODE_EXECUTION"
    GSQL_QUERY = "GSQL_QUERY"
    GRAPHRAG_RETRIEVAL = "GRAPHRAG_RETRIEVAL"
    LLM_INVOCATION = "LLM_INVOCATION"
    FEATURE_CALCULATION = "FEATURE_CALCULATION"
    POLICY_DECISION = "POLICY_DECISION"
    APPROVAL_EVENT = "APPROVAL_EVENT"
    ACTION_EXECUTION = "ACTION_EXECUTION"
    CASE_FINALIZATION = "CASE_FINALIZATION"
    ERROR = "ERROR"


class TraceSpan(BaseModel):
    """Individual auditable execution span in the investigation trace."""
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    span_id: str = Field(default_factory=lambda: generate_prefixed_id("SPAN", 8))
    case_id: str
    span_type: SpanType
    name: str
    start_time: str = Field(default_factory=now_iso)
    end_time: str = Field(default_factory=now_iso)
    duration_ms: float = 0.0
    status: str = "SUCCESS"  # SUCCESS, ERROR, PAUSED, SKIPPED
    metadata: Dict[str, Any] = Field(default_factory=dict)


def sanitize_sensitive_data(val: Any) -> Any:
    """Recursively strip or mask API keys, secrets, and credentials per AGENTS.md §32."""
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    elif isinstance(val, (list, tuple, set)):
        return [sanitize_sensitive_data(item) for item in val]
    elif isinstance(val, str) and (
        val.startswith("gsk_") or val.startswith("AIza") or val.startswith("sk-")
    ):
        return "[REDACTED_API_KEY]"
    return val


class InvestigationTracer:
    """Audit Trail and Trace Manager persisting structured JSONL logs to disk."""

    def __init__(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        enable_langfuse: Optional[bool] = None,
    ):
        settings = get_settings()
        base_output = output_dir or settings.OUTPUT_PATH
        self.output_dir = Path(base_output) / "traces"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.enable_langfuse = (
            enable_langfuse if enable_langfuse is not None else settings.ENABLE_LANGFUSE
        )
        self._langfuse_client = None
        if self.enable_langfuse:
            try:
                from langfuse import Langfuse
                self._langfuse_client = Langfuse()
                logger.info("Langfuse tracing enabled for InvestigationTracer")
            except Exception as exc:
                logger.warning("Failed to initialize Langfuse client: %s", exc)

    def get_trace_path(self, case_id: str) -> Path:
        """Resolve absolute JSONL trace file path for a given investigation case ID."""
        clean_cid = re.sub(r"[^a-zA-Z0-9_\-]", "_", case_id)
        return self.output_dir / f"{clean_cid}.jsonl"

    def record_span(self, span: TraceSpan) -> None:
        """Append a sanitized TraceSpan record to the local case JSONL trace file."""
        trace_path = self.get_trace_path(span.case_id)
        sanitized_meta = sanitize_sensitive_data(span.metadata)
        span_dict = span.model_dump()
        span_dict["metadata"] = sanitized_meta

        try:
            line = json.dumps(span_dict) + "\n"
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:
            logger.error("Failed to write trace span to %s: %s", trace_path, exc)

        # Optional Langfuse export
        if self._langfuse_client:
            try:
                self._export_to_langfuse(span)
            except Exception as exc:
                logger.debug("Langfuse export error: %s", exc)

    @contextmanager
    def span(
        self,
        case_id: str,
        span_type: SpanType,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Synchronous context manager measuring span execution time and recording trace."""
        start_ts = now_iso()
        t0 = time.perf_counter()
        meta = metadata.copy() if metadata else {}
        status = "SUCCESS"

        try:
            yield meta
        except Exception as exc:
            status = "ERROR"
            meta["error_type"] = type(exc).__name__
            meta["error_message"] = str(exc)
            raise
        finally:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            end_ts = now_iso()
            span = TraceSpan(
                case_id=case_id,
                span_type=span_type,
                name=name,
                start_time=start_ts,
                end_time=end_ts,
                duration_ms=duration_ms,
                status=status,
                metadata=meta,
            )
            self.record_span(span)

    @asynccontextmanager
    async def async_span(
        self,
        case_id: str,
        span_type: SpanType,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Asynchronous context manager measuring span execution time and recording trace."""
        start_ts = now_iso()
        t0 = time.perf_counter()
        meta = metadata.copy() if metadata else {}
        status = "SUCCESS"

        try:
            yield meta
        except Exception as exc:
            status = "ERROR"
            meta["error_type"] = type(exc).__name__
            meta["error_message"] = str(exc)
            raise
        finally:
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            end_ts = now_iso()
            span = TraceSpan(
                case_id=case_id,
                span_type=span_type,
                name=name,
                start_time=start_ts,
                end_time=end_ts,
                duration_ms=duration_ms,
                status=status,
                metadata=meta,
            )
            self.record_span(span)

    # Convenience Loggers
    def log_node(
        self,
        case_id: str,
        node_name: str,
        duration_ms: float,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a LangGraph node transition span."""
        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.NODE_EXECUTION,
            name=f"Node:{node_name}",
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {},
        )
        self.record_span(span)

    def log_query(
        self,
        case_id: str,
        query_name: str,
        duration_ms: float,
        target_entity: Optional[str] = None,
        record_count: Optional[int] = None,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a TigerGraph GSQL query execution span."""
        meta = metadata or {}
        if target_entity:
            meta["target_entity"] = target_entity
        if record_count is not None:
            meta["record_count"] = record_count

        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.GSQL_QUERY,
            name=f"GSQL:{query_name}",
            duration_ms=duration_ms,
            status=status,
            metadata=meta,
        )
        self.record_span(span)

    def log_retrieval(
        self,
        case_id: str,
        retrieval_type: str,
        duration_ms: float,
        query_text: Optional[str] = None,
        results_count: Optional[int] = None,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a TigerGraph GraphRAG policy or case retrieval span."""
        meta = metadata or {}
        if query_text:
            meta["query_text"] = query_text
        if results_count is not None:
            meta["results_count"] = results_count

        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.GRAPHRAG_RETRIEVAL,
            name=f"GraphRAG:{retrieval_type}",
            duration_ms=duration_ms,
            status=status,
            metadata=meta,
        )
        self.record_span(span)

    def log_llm(
        self,
        case_id: str,
        provider: str,
        model: str,
        duration_ms: float,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an LLM reasoning call span."""
        meta = metadata or {}
        meta["provider"] = provider
        meta["model"] = model

        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.LLM_INVOCATION,
            name=f"LLM:{provider}:{model}",
            duration_ms=duration_ms,
            status=status,
            metadata=meta,
        )
        self.record_span(span)

    def log_policy(
        self,
        case_id: str,
        action_type: str,
        allowed: bool,
        approval_required: bool,
        policy_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a deterministic policy gate evaluation span."""
        meta = metadata or {}
        meta["action_type"] = action_type
        meta["allowed"] = allowed
        meta["approval_required"] = approval_required
        if policy_ref:
            meta["policy_reference"] = policy_ref

        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.POLICY_DECISION,
            name=f"Policy:{action_type}",
            duration_ms=0.5,
            status="SUCCESS" if allowed else "REJECTED",
            metadata=meta,
        )
        self.record_span(span)

    def log_action(
        self,
        case_id: str,
        action_type: str,
        execution_mode: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an executed or simulated action span."""
        meta = metadata or {}
        meta["action_type"] = action_type
        meta["execution_mode"] = execution_mode
        meta["success"] = success
        if result:
            meta["result"] = result

        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.ACTION_EXECUTION,
            name=f"Action:{action_type}",
            duration_ms=1.0,
            status="SUCCESS" if success else "FAILED",
            metadata=meta,
        )
        self.record_span(span)

    def log_error(
        self,
        case_id: str,
        name: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an isolated or fatal investigation error span."""
        meta = metadata or {}
        meta["error_message"] = error_message

        span = TraceSpan(
            case_id=case_id,
            span_type=SpanType.ERROR,
            name=f"Error:{name}",
            duration_ms=0.0,
            status="ERROR",
            metadata=meta,
        )
        self.record_span(span)

    def read_traces(self, case_id: str) -> List[TraceSpan]:
        """Read and parse all JSONL trace records for a case ID."""
        trace_path = self.get_trace_path(case_id)
        if not trace_path.exists():
            return []

        spans: List[TraceSpan] = []
        try:
            with open(trace_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        spans.append(TraceSpan.model_validate(data))
                    except Exception as err:
                        logger.warning("Skipping malformed trace line in %s: %s", trace_path, err)
        except Exception as exc:
            logger.error("Failed to read trace file %s: %s", trace_path, exc)

        return spans

    def _export_to_langfuse(self, span: TraceSpan) -> None:
        """Internal helper sending span metadata to Langfuse if enabled."""
        if not self._langfuse_client:
            return
        try:
            self._langfuse_client.trace(
                name=span.name,
                metadata={"case_id": span.case_id, **span.metadata},
                input=span.metadata.get("input"),
                output=span.metadata.get("output"),
            )
        except Exception as exc:
            logger.debug("Failed export to Langfuse: %s", exc)


_GLOBAL_TRACER: Optional[InvestigationTracer] = None


def get_tracer() -> InvestigationTracer:
    """Singleton factory for the global InvestigationTracer."""
    global _GLOBAL_TRACER
    if _GLOBAL_TRACER is None:
        _GLOBAL_TRACER = InvestigationTracer()
    return _GLOBAL_TRACER
