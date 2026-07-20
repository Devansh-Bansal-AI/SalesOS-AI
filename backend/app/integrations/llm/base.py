# ============================================================
# SalesOS AI — LLM Provider Abstraction
#
# Every agent calls llm.generate(...) — never a specific provider.
# Switching from Gemini to OpenAI is a config change, not a code change.
# ============================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger("llm")


# ── Response Model ──────────────────────────────────────────


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    finish_reason: str = "stop"
    raw_response: Any = None  # Provider-specific response for debugging

    @property
    def estimated_cost(self) -> float:
        """Rough cost estimate. Override per provider for accuracy."""
        # Default: $0.15/1M input, $0.60/1M output (Gemini Flash tier)
        return (self.prompt_tokens * 0.00000015) + (self.completion_tokens * 0.0000006)


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMConfig:
    """Configuration passed to every LLM call."""
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 2048
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)
    response_format: str | None = None  # "json" for structured output
    timeout_seconds: int = 30


# ── Abstract Provider ───────────────────────────────────────


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.

    To add a new provider:
    1. Create a new class extending LLMProvider
    2. Implement generate() and generate_structured()
    3. Register it in the LLMProviderRegistry
    """

    provider_name: str = "base"

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a text response from messages."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[LLMMessage],
        output_schema: type,
        config: LLMConfig | None = None,
    ) -> tuple[Any, LLMResponse]:
        """Generate a structured response conforming to a Pydantic schema.

        Returns:
            Tuple of (parsed Pydantic object, raw LLMResponse)
        """
        ...

    async def health_check(self) -> bool:
        """Verify the provider is reachable. Override for custom checks."""
        try:
            response = await self.generate(
                [LLMMessage(role="user", content="Say 'ok'")],
                LLMConfig(max_tokens=5, temperature=0),
            )
            return bool(response.content)
        except Exception:
            return False
