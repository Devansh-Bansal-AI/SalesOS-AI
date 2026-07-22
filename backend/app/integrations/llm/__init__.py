# ============================================================
# SalesOS AI — LLM Provider Registry
#
# Central factory that resolves which provider to use.
# Agents call: llm = get_llm_provider("gemini")
# Or simply:   llm = get_default_llm()
# ============================================================

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider

logger = get_logger("llm.registry")

# Lazy-loaded provider cache
_providers: dict[str, LLMProvider] = {}


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Get an LLM provider by name. Defaults to primary configured provider.

    Usage:
        llm = get_llm_provider()          # Default (Gemini)
        llm = get_llm_provider("openai")  # Specific provider
        llm = get_llm_provider("claude")  # Specific provider

        response = await llm.generate([...])
    """
    settings = get_settings()

    if provider_name is None:
        # Determine default from config: pick the first one with an API key
        if settings.GEMINI_API_KEY:
            provider_name = "gemini"
        elif settings.OPENAI_API_KEY:
            provider_name = "openai"
        elif settings.ANTHROPIC_API_KEY:
            provider_name = "claude"
        else:
            raise LLMError("none", "No LLM provider API key configured")

    # Return cached provider if available
    if provider_name in _providers:
        return _providers[provider_name]

    # Lazy-load the provider
    provider: LLMProvider

    if provider_name == "gemini":
        from app.integrations.llm.gemini import GeminiProvider

        provider = GeminiProvider()

    elif provider_name == "openai":
        from app.integrations.llm.openai import OpenAIProvider

        provider = OpenAIProvider()

    elif provider_name == "claude":
        from app.integrations.llm.claude import ClaudeProvider

        provider = ClaudeProvider()

    else:
        raise LLMError(provider_name, f"Unknown LLM provider: {provider_name}")

    _providers[provider_name] = provider
    logger.info("llm_provider_initialized", provider=provider_name)
    return provider


def get_default_llm() -> LLMProvider:
    """Shorthand for get_llm_provider() with default."""
    return get_llm_provider()
