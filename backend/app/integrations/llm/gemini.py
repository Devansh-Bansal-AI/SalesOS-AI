# ============================================================
# SalesOS AI — Gemini Provider
# ============================================================

import time
from typing import Any

import google.generativeai as genai

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.integrations.llm.base import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)

logger = get_logger("llm.gemini")


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    provider_name = "gemini"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise LLMError("gemini", "GEMINI_API_KEY not configured")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._default_model = settings.GEMINI_MODEL

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        config = config or LLMConfig()
        model_name = config.model or self._default_model

        try:
            model = genai.GenerativeModel(model_name)

            # Convert messages to Gemini format
            system_instruction = None
            gemini_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_instruction = msg.content
                elif msg.role == "user":
                    gemini_messages.append({"role": "user", "parts": [msg.content]})
                elif msg.role == "assistant":
                    gemini_messages.append({"role": "model", "parts": [msg.content]})

            if system_instruction:
                model = genai.GenerativeModel(
                    model_name, system_instruction=system_instruction
                )

            generation_config = genai.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
                top_p=config.top_p,
            )

            if config.response_format == "json":
                generation_config.response_mime_type = "application/json"

            start = time.perf_counter()
            response = await model.generate_content_async(
                gemini_messages,
                generation_config=generation_config,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)

            # Extract token counts
            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

            return LLMResponse(
                content=response.text,
                model=model_name,
                provider=self.provider_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                raw_response=response,
            )

        except Exception as e:
            logger.error("gemini_error", model=model_name, error=str(e))
            raise LLMError("gemini", str(e))

    async def generate_structured(
        self,
        messages: list[LLMMessage],
        output_schema: type,
        config: LLMConfig | None = None,
    ) -> tuple[Any, LLMResponse]:
        config = config or LLMConfig()
        config.response_format = "json"

        # Add schema instruction to the system message
        schema_json = output_schema.model_json_schema()
        schema_instruction = (
            f"\n\nYou MUST respond with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any text outside the JSON object."
        )

        # Append to last user message or system message
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
        try:
            parsed = output_schema.model_validate_json(response.content)
        except Exception:
            # Try to extract JSON from response
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = output_schema.model_validate(json.loads(content))

        return parsed, response
