# ============================================================
# SalesOS AI — Claude (Anthropic) Provider
# ============================================================

import time
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.integrations.llm.base import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)

logger = get_logger("llm.claude")


class ClaudeProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    provider_name = "claude"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            raise LLMError("claude", "ANTHROPIC_API_KEY not configured")

        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._default_model = settings.ANTHROPIC_MODEL

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        config = config or LLMConfig()
        model_name = config.model or self._default_model

        try:
            # Claude separates system from messages
            system_content = None
            claude_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_content = msg.content
                else:
                    claude_messages.append({"role": msg.role, "content": msg.content})

            kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": claude_messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
            }

            if system_content:
                kwargs["system"] = system_content

            if config.stop_sequences:
                kwargs["stop_sequences"] = config.stop_sequences

            start = time.perf_counter()
            response = await self._client.messages.create(**kwargs)
            latency_ms = int((time.perf_counter() - start) * 1000)

            content = response.content[0].text if response.content else ""

            return LLMResponse(
                content=content,
                model=model_name,
                provider=self.provider_name,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency_ms,
                finish_reason=response.stop_reason or "stop",
                raw_response=response,
            )

        except Exception as e:
            logger.error("claude_error", model=model_name, error=str(e))
            raise LLMError("claude", str(e))

    async def generate_structured(
        self,
        messages: list[LLMMessage],
        output_schema: type,
        config: LLMConfig | None = None,
    ) -> tuple[Any, LLMResponse]:
        config = config or LLMConfig()

        schema_json = output_schema.model_json_schema()
        schema_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"No explanation, no markdown, just the JSON object."
        )

        enhanced_messages = list(messages)
        for i in range(len(enhanced_messages) - 1, -1, -1):
            if enhanced_messages[i].role in ("user", "system"):
                enhanced_messages[i] = LLMMessage(
                    role=enhanced_messages[i].role,
                    content=enhanced_messages[i].content + schema_instruction,
                )
                break

        response = await self.generate(enhanced_messages, config)

        import json

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = output_schema.model_validate(json.loads(content))
        return parsed, response
