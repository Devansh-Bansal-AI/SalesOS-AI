# ============================================================
# SalesOS AI — Feature Flags
#
# Config-driven feature flags with Redis backing for runtime
# toggling. Allows gradual rollout without redeployment.
#
# Usage:
#   if await flags.is_enabled("conversation_memory"):
#       ...
#
#   @require_feature("qdrant_search")
#   async def semantic_search(...):
#       ...
# ============================================================

from collections.abc import Callable
from functools import wraps
from typing import Any

from app.core.logging import get_logger

logger = get_logger("feature_flags")


# ── Default Flag Definitions ───────────────────────────────
# These are the source of truth. Redis overrides take precedence.

DEFAULT_FLAGS: dict[str, dict[str, Any]] = {
    # AI Features
    "conversation_memory": {
        "enabled": True,
        "description": "Use Qdrant for conversation memory retrieval",
    },
    "qdrant_search": {
        "enabled": False,
        "description": "Semantic search across knowledge base",
    },
    "prompt_caching": {
        "enabled": True,
        "description": "Cache LLM responses in Redis for identical inputs",
    },
    # Agent Features
    "enrichment_agent": {
        "enabled": True,
        "description": "Run company enrichment on new leads",
    },
    "analytics_agent": {
        "enabled": False,
        "description": "AI-powered analytics insights",
    },
    "experimental_agents": {
        "enabled": False,
        "description": "Enable experimental agent capabilities",
    },
    # Decision Engine
    "llm_fallback_decisions": {
        "enabled": True,
        "description": "Use LLM for decision engine when no rule matches",
    },
    "auto_booking": {
        "enabled": True,
        "description": "Automatically schedule meetings for high-score demo requests",
    },
    "auto_disqualify": {
        "enabled": True,
        "description": "Automatically disqualify low-score leads",
    },
    # Communication
    "email_sending": {
        "enabled": True,
        "description": "Actually send emails (disable for testing)",
    },
    "follow_up_sequences": {
        "enabled": True,
        "description": "Automated follow-up email sequences",
    },
    # Platform
    "audit_logging": {
        "enabled": True,
        "description": "Log all data changes to audit_logs table",
    },
    "rate_limiting": {
        "enabled": True,
        "description": "Enable API rate limiting",
    },
    "public_lead_submission": {
        "enabled": True,
        "description": "Accept leads from unauthenticated public endpoints",
    },
}


class FeatureFlags:
    """Feature flag manager with static defaults and Redis runtime overrides.

    Evaluation order:
    1. Check Redis for runtime override (org-specific or global)
    2. Fall back to DEFAULT_FLAGS
    3. Fall back to False (unknown flags are disabled)
    """

    def __init__(self) -> None:
        self._overrides: dict[str, bool] = {}

    async def is_enabled(
        self,
        flag_name: str,
        *,
        organization_id: str | None = None,
    ) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: The flag to check
            organization_id: Optional org ID for org-specific overrides
        """
        # 1. Check Redis for runtime override
        try:
            redis_value = await self._check_redis(flag_name, organization_id)
            if redis_value is not None:
                return redis_value
        except Exception:
            pass  # Redis unavailable — fall through to defaults

        # 2. Check in-memory overrides
        if flag_name in self._overrides:
            return self._overrides[flag_name]

        # 3. Check defaults
        flag_def = DEFAULT_FLAGS.get(flag_name)
        if flag_def:
            return flag_def.get("enabled", False)

        # 4. Unknown flags are disabled
        logger.warning("unknown_feature_flag", flag=flag_name)
        return False

    async def _check_redis(self, flag_name: str, organization_id: str | None) -> bool | None:
        """Check Redis for runtime flag override."""
        from app.db.redis import get_redis

        redis = get_redis()

        # Check org-specific override first
        if organization_id:
            key = f"feature_flag:{organization_id}:{flag_name}"
            value = await redis.get(key)
            if value is not None:
                return value == "1"

        # Check global override
        key = f"feature_flag:global:{flag_name}"
        value = await redis.get(key)
        if value is not None:
            return value == "1"

        return None

    async def set_override(
        self,
        flag_name: str,
        enabled: bool,
        *,
        organization_id: str | None = None,
    ) -> None:
        """Set a runtime override in Redis."""
        from app.db.redis import get_redis

        redis = get_redis()

        if organization_id:
            key = f"feature_flag:{organization_id}:{flag_name}"
        else:
            key = f"feature_flag:global:{flag_name}"

        await redis.set(key, "1" if enabled else "0")
        logger.info(
            "feature_flag_override",
            flag=flag_name,
            enabled=enabled,
            org=organization_id,
        )

    async def clear_override(
        self,
        flag_name: str,
        *,
        organization_id: str | None = None,
    ) -> None:
        """Remove a runtime override, reverting to default."""
        from app.db.redis import get_redis

        redis = get_redis()

        if organization_id:
            key = f"feature_flag:{organization_id}:{flag_name}"
        else:
            key = f"feature_flag:global:{flag_name}"

        await redis.delete(key)

    def set_memory_override(self, flag_name: str, enabled: bool) -> None:
        """Set an in-memory override (for testing, no Redis required)."""
        self._overrides[flag_name] = enabled

    def list_flags(self) -> dict[str, dict[str, Any]]:
        """List all defined flags with their default states."""
        return DEFAULT_FLAGS.copy()


# ── Global Instance ─────────────────────────────────────────

_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    return _flags


# ── Decorator ───────────────────────────────────────────────


def require_feature(flag_name: str):
    """Decorator that disables a function when a feature flag is off.

    Usage:
        @require_feature("qdrant_search")
        async def search_knowledge_base(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            flags = get_feature_flags()
            org_id = kwargs.get("organization_id")
            if not await flags.is_enabled(
                flag_name, organization_id=str(org_id) if org_id else None
            ):
                from app.core.exceptions import SalesOSError

                raise SalesOSError(
                    message=f"Feature '{flag_name}' is not enabled",
                    code="FEATURE_DISABLED",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
