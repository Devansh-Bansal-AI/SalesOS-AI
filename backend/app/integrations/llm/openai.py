# ============================================================
# SalesOS AI — OpenAI Provider
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

logger = get_logger("llm.openai")


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    provider_name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise LLMError("openai", "OPENAI_API_KEY not configured")

        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._default_model = settings.OPENAI_MODEL

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        config = config or LLMConfig()
        model_name = config.model or self._default_model

        try:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": openai_messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
            }

            if config.response_format == "json":
                kwargs["response_format"] = {"type": "json_object"}

            if config.stop_sequences:
                kwargs["stop"] = config.stop_sequences

            start = time.perf_counter()
            response = await self._client.chat.completions.create(**kwargs)
            latency_ms = int((time.perf_counter() - start) * 1000)

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=model_name,
                provider=self.provider_name,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                latency_ms=latency_ms,
                finish_reason=choice.finish_reason or "stop",
                raw_response=response,
            )

        except Exception as e:
            logger.error("openai_error", model=model_name, error=str(e))
            raise LLMError("openai", str(e))

    async def generate_structured(
        self,
        messages: list[LLMMessage],
        output_schema: type,
        config: LLMConfig | None = None,
    ) -> tuple[Any, LLMResponse]:
        config = config or LLMConfig()
        config.response_format = "json"

        schema_json = output_schema.model_json_schema()
        schema_instruction = (
            f"\n\nRespond with valid JSON matching this schema:\n```json\n{schema_json}\n```"
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

        parsed = output_schema.model_validate(json.loads(response.content))
        return parsed, response
