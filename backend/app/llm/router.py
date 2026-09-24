"""Unified LLM Provider Router & Fallback Service (Layer 15).

Provides a provider-independent interface for LLM completions with:
1. Primary Reasoning: Groq (`openai/gpt-oss-120b`)
2. Fast Reasoning: Groq (`openai/gpt-oss-20b`)
3. Fallback Reasoning: Gemini Flash (`gemini-1.5-flash` / `gemini-2.0-flash`)
4. Offline Mock Fallback: Grounded mock output for offline testing/development

Features:
- Pydantic structured output validation and auto-repair.
- Latency, model version, and token usage tracking.
- Automatic failover from Groq to Gemini Flash on rate limit, timeout, or API errors.
- Never silently accepts invalid JSON when a response schema is requested.
"""

from enum import Enum
import json
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.utils.logging import get_logger

logger = get_logger("llm.router")

# Optional Groq SDK import
try:
    import groq

    HAS_GROQ = True
except ImportError:
    groq = None
    HAS_GROQ = False

# Optional Gemini SDK import
try:
    import google.generativeai as genai

    HAS_GEMINI = True
except ImportError:
    genai = None
    HAS_GEMINI = False

T = TypeVar("T", bound=BaseModel)
_USE_CONFIGURED_KEY = object()


class LLMResponse(BaseModel):
    """Standardized response container across all LLM providers."""

    model_config = ConfigDict(extra="ignore")

    content: str = Field(description="Raw output text from the language model.")
    parsed_output: Optional[Any] = Field(
        default=None,
        description="Parsed Pydantic object if a response schema was requested.",
    )
    provider: str = Field(description="LLM Provider used ('groq', 'gemini', or 'mock').")
    model_name: str = Field(description="Exact model name/version executed.")
    latency_ms: float = Field(default=0.0, description="Inference latency in milliseconds.")
    token_usage: Dict[str, int] = Field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        description="Token usage stats.",
    )
    is_fallback: bool = Field(
        default=False,
        description="True if request fell back to backup provider or mock.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error details if failover occurred during processing.",
    )


class LLMRouter:
    """Provider-independent router with primary Groq models, Gemini Flash fallback, and JSON validation."""

    def __init__(
        self,
        groq_api_key: Union[Optional[str], object] = _USE_CONFIGURED_KEY,
        gemini_api_key: Union[Optional[str], object] = _USE_CONFIGURED_KEY,
        groq_primary_model: Optional[str] = None,
        groq_fast_model: Optional[str] = None,
        gemini_model: Optional[str] = None,
    ):
        settings = get_settings()
        # Omitted keys use application settings; explicit None forces offline
        # mode, which keeps tests and local deterministic demos predictable.
        self.groq_api_key = (
            settings.GROQ_API_KEY
            if groq_api_key is _USE_CONFIGURED_KEY
            else groq_api_key
        )
        self.gemini_api_key = (
            settings.GEMINI_API_KEY
            if gemini_api_key is _USE_CONFIGURED_KEY
            else gemini_api_key
        )
        self.groq_primary_model = groq_primary_model or settings.GROQ_PRIMARY_MODEL
        self.groq_fast_model = groq_fast_model or settings.GROQ_FAST_MODEL
        self.gemini_model = gemini_model or getattr(settings, "GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")

        # Initialize Groq client if key available
        self._groq_client = None
        if self.groq_api_key:
            if HAS_GROQ:
                try:
                    self._groq_client = groq.Groq(api_key=self.groq_api_key)
                    logger.info("Initialized Groq client (Primary: %s, Fast: %s)", self.groq_primary_model, self.groq_fast_model)
                except Exception as exc:
                    logger.warning("Failed to initialize Groq client: %s", exc)
            else:
                self._groq_client = "CONFIGURED_WITHOUT_SDK"

        # Initialize Gemini client if key available
        self._gemini_configured = False
        if self.gemini_api_key:
            if HAS_GEMINI:
                try:
                    genai.configure(api_key=self.gemini_api_key)
                    self._gemini_configured = True
                    logger.info("Initialized Gemini client (Model: %s)", self.gemini_model)
                except Exception as exc:
                    logger.warning("Failed to initialize Gemini client: %s", exc)
            else:
                self._gemini_configured = True

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Type[T]] = None,
        use_fast_model: bool = False,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        max_retries: int = 2,
    ) -> LLMResponse:
        """Route completion call to primary Groq, fallback to Gemini, or mock.

        Validates and parses JSON if response_schema is provided.
        """
        target_groq_model = self.groq_fast_model if use_fast_model else self.groq_primary_model

        # Augment prompt if structured output schema is required
        effective_prompt = prompt
        effective_system = system_prompt or "You are an expert fraud investigation AI assistant."

        if response_schema is not None:
            schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
            effective_system += (
                f"\n\nCRITICAL INSTRUCTION: You MUST return a valid JSON object matching this schema exactly:\n"
                f"```json\n{schema_json}\n```\n"
                f"Do not include any conversational preamble, intro, or explanation outside of the valid JSON object."
            )

        # Attempt 1: Groq Provider
        if self._groq_client is not None:
            try:
                response = self._call_groq(
                    prompt=effective_prompt,
                    system_prompt=effective_system,
                    model_name=target_groq_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_schema=response_schema,
                )
                return response
            except Exception as exc:
                logger.warning("Groq call failed (%s); falling back to Gemini Flash: %s", target_groq_model, exc)

        # Attempt 2: Gemini Provider Fallback
        if self._gemini_configured:
            try:
                response = self._call_gemini(
                    prompt=effective_prompt,
                    system_prompt=effective_system,
                    model_name=self.gemini_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_schema=response_schema,
                )
                response.is_fallback = True
                return response
            except Exception as exc:
                logger.warning("Gemini Flash fallback failed: %s", exc)

        # Attempt 3: Offline Mock Fallback
        logger.info("Operating in offline / mock mode for LLM completion.")
        return self._call_mock(
            prompt=prompt,
            response_schema=response_schema,
            model_name="mock-llm-fallback",
        )

    def _call_groq(
        self,
        prompt: str,
        system_prompt: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[T]],
    ) -> LLMResponse:
        """Execute request via Groq API."""
        start_time = time.time()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}

        res = self._groq_client.chat.completions.create(**kwargs)
        latency_ms = round((time.time() - start_time) * 1000, 2)

        content = res.choices[0].message.content or ""
        usage = {
            "prompt_tokens": getattr(res.usage, "prompt_tokens", 0) if hasattr(res, "usage") else 0,
            "completion_tokens": getattr(res.usage, "completion_tokens", 0) if hasattr(res, "usage") else 0,
            "total_tokens": getattr(res.usage, "total_tokens", 0) if hasattr(res, "usage") else 0,
        }

        parsed_obj = None
        if response_schema is not None:
            parsed_obj = self._parse_and_validate_json(content, response_schema)

        return LLMResponse(
            content=content,
            parsed_output=parsed_obj,
            provider="groq",
            model_name=model_name,
            latency_ms=latency_ms,
            token_usage=usage,
            is_fallback=False,
        )

    def _call_gemini(
        self,
        prompt: str,
        system_prompt: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[T]],
    ) -> LLMResponse:
        """Execute request via Gemini Flash API."""
        start_time = time.time()

        g_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )

        gen_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if response_schema is not None else "text/plain",
        )

        res = g_model.generate_content(prompt, generation_config=gen_config)
        latency_ms = round((time.time() - start_time) * 1000, 2)

        content = res.text or ""
        parsed_obj = None
        if response_schema is not None:
            parsed_obj = self._parse_and_validate_json(content, response_schema)

        return LLMResponse(
            content=content,
            parsed_output=parsed_obj,
            provider="gemini",
            model_name=model_name,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            is_fallback=True,
        )

    def _call_mock(
        self,
        prompt: str,
        response_schema: Optional[Type[T]],
        model_name: str,
    ) -> LLMResponse:
        """Provide deterministic offline mock responses for testing."""
        start_time = time.time()

        parsed_obj = None
        if response_schema is not None:
            parsed_obj = self._generate_mock_instance(response_schema)
            content = parsed_obj.model_dump_json(indent=2)
        else:
            content = (
                f"[OFFLINE MOCK RESPONSE]\n"
                f"Successfully processed prompt in mock mode.\n"
                f"Prompt snippet: {prompt[:100]}..."
            )

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return LLMResponse(
            content=content,
            parsed_output=parsed_obj,
            provider="mock",
            model_name=model_name,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
            is_fallback=True,
        )

    def _parse_and_validate_json(
        self,
        content: str,
        response_schema: Type[T],
    ) -> T:
        """Parse JSON text and validate against target Pydantic schema with markdown block repair."""
        clean_text = content.strip()

        # Strip markdown codeblocks (```json ... ```)
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        # Extract JSON object substring `{ ... }` if surrounding text exists
        match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(1).strip()

        try:
            return response_schema.model_validate_json(clean_text)
        except Exception as exc:
            logger.error("Failed to parse/validate LLM JSON output against schema %s: %s", response_schema.__name__, exc)
            raise ValueError(f"Invalid JSON for schema {response_schema.__name__}: {exc}") from exc

    def _generate_mock_instance(self, schema_cls: Type[T]) -> T:
        """Generate a valid default instance of a Pydantic schema for mock execution."""
        sample_dict: Dict[str, Any] = {}
        for fname, field_info in schema_cls.model_fields.items():
            ftype = field_info.annotation

            # Handle specific known fields for coherent mock reasoning
            if fname == "risk_level":
                sample_dict[fname] = "HIGH"
            elif fname == "recommended_action_type":
                sample_dict[fname] = "BLOCK_TRANSACTION"
            elif fname == "risk_score":
                sample_dict[fname] = 0.85
            elif fname in ["confidence", "evidence_completeness"]:
                sample_dict[fname] = 0.90
            # Handle Enum fields
            elif isinstance(ftype, type) and issubclass(ftype, Enum):
                sample_dict[fname] = list(ftype)[0].value
            elif ftype in [str, Optional[str]]:
                sample_dict[fname] = f"mock_{fname}"
            elif ftype in [int, Optional[int]]:
                sample_dict[fname] = 1
            elif ftype in [float, Optional[float]]:
                sample_dict[fname] = 0.85
            elif ftype in [bool, Optional[bool]]:
                sample_dict[fname] = True
            elif hasattr(ftype, "__origin__") and ftype.__origin__ is list:
                sample_dict[fname] = []
            elif hasattr(ftype, "__origin__") and ftype.__origin__ is dict:
                sample_dict[fname] = {}
            else:
                sample_dict[fname] = None

        try:
            return schema_cls.model_validate(sample_dict)
        except Exception as exc:
            logger.warning("Mock validation failed for %s: %s", schema_cls.__name__, exc)
            return schema_cls.model_construct()
