# ============================================================
# SalesOS AI — Prompt Registry
#
# Prompt versioning, rollback, and management.
# Instead of hardcoded prompt files, prompts are registered
# centrally with version tracking.
#
# Features:
#   - Version management (v1, v2, ...)
#   - Active version selection (per org or global)
#   - Rollback to previous versions
#   - List all prompts with versions for admin UI
# ============================================================

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger("prompt_registry")


class PromptVersion(BaseModel):
    """A single version of a prompt template."""

    version: str
    system_prompt: str
    user_prompt_template: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    description: str = ""
    is_active: bool = False


class PromptRegistration(BaseModel):
    """Metadata about a registered prompt."""

    name: str
    agent_type: str
    description: str = ""
    versions: list[PromptVersion] = Field(default_factory=list)
    active_version: str | None = None


class PromptRegistry:
    """Central registry for prompt templates with versioning.

    Usage:
        registry = get_prompt_registry()

        # Register
        registry.register("qualification", "v1", system, user, description="Initial")
        registry.register("qualification", "v2", system_v2, user_v2, description="Improved")

        # Get active
        system, user = registry.get_active("qualification")

        # Get specific version
        system, user = registry.get("qualification", "v1")

        # Rollback
        registry.set_active("qualification", "v1")
    """

    def __init__(self):
        self._prompts: dict[str, PromptRegistration] = {}

    def register(
        self,
        name: str,
        version: str,
        system_prompt: str,
        user_prompt_template: str,
        *,
        agent_type: str = "",
        description: str = "",
        set_active: bool = True,
    ) -> None:
        """Register a prompt version."""
        if name not in self._prompts:
            self._prompts[name] = PromptRegistration(
                name=name,
                agent_type=agent_type or name,
                description=description,
            )

        registration = self._prompts[name]

        # Check if version already exists
        existing = next((v for v in registration.versions if v.version == version), None)
        if existing:
            # Update existing version
            existing.system_prompt = system_prompt
            existing.user_prompt_template = user_prompt_template
            existing.description = description
        else:
            # Add new version
            prompt_version = PromptVersion(
                version=version,
                system_prompt=system_prompt,
                user_prompt_template=user_prompt_template,
                description=description,
            )
            registration.versions.append(prompt_version)

        if set_active:
            self.set_active(name, version)

        logger.info(
            "prompt_registered",
            name=name,
            version=version,
            active=set_active,
        )

    def get_active(self, name: str) -> tuple[str, str]:
        """Get the active system and user prompt for a named prompt.

        Returns:
            Tuple of (system_prompt, user_prompt_template)

        Raises:
            KeyError: If prompt name not registered or no active version.
        """
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not registered")

        registration = self._prompts[name]
        if not registration.active_version:
            raise KeyError(f"No active version for prompt '{name}'")

        version = next(
            (v for v in registration.versions if v.version == registration.active_version),
            None,
        )
        if not version:
            raise KeyError(f"Active version '{registration.active_version}' not found for '{name}'")

        return version.system_prompt, version.user_prompt_template

    def get(self, name: str, version: str) -> tuple[str, str]:
        """Get a specific version of a prompt.

        Returns:
            Tuple of (system_prompt, user_prompt_template)
        """
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not registered")

        v = next(
            (v for v in self._prompts[name].versions if v.version == version),
            None,
        )
        if not v:
            raise KeyError(f"Version '{version}' not found for prompt '{name}'")

        return v.system_prompt, v.user_prompt_template

    def set_active(self, name: str, version: str) -> None:
        """Set the active version for a prompt."""
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not registered")

        registration = self._prompts[name]
        if not any(v.version == version for v in registration.versions):
            raise KeyError(f"Version '{version}' not found for prompt '{name}'")

        # Deactivate all
        for v in registration.versions:
            v.is_active = False

        # Activate target
        target = next(v for v in registration.versions if v.version == version)
        target.is_active = True
        registration.active_version = version

        logger.info("prompt_active_version_changed", name=name, version=version)

    def rollback(self, name: str) -> str:
        """Rollback to the previous version.

        Returns the version rolled back to.
        """
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not registered")

        registration = self._prompts[name]
        versions = registration.versions

        if len(versions) < 2:
            raise ValueError(f"Cannot rollback '{name}': only one version exists")

        # Find current active index
        current_idx = next(
            (i for i, v in enumerate(versions) if v.version == registration.active_version),
            len(versions) - 1,
        )

        # Go to previous version
        prev_idx = current_idx - 1 if current_idx > 0 else len(versions) - 1
        prev_version = versions[prev_idx].version

        self.set_active(name, prev_version)
        logger.info("prompt_rolled_back", name=name, to_version=prev_version)

        return prev_version

    def list_prompts(self) -> list[PromptRegistration]:
        """List all registered prompts with their versions."""
        return list(self._prompts.values())

    def get_registration(self, name: str) -> PromptRegistration | None:
        """Get full registration details for a prompt."""
        return self._prompts.get(name)


# ── Global singleton ────────────────────────────────────────

_registry = PromptRegistry()


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry."""
    return _registry


def register_all_prompts() -> None:
    """Register all built-in prompt templates.

    Called at application startup.
    """
    from app.prompts.booking_v1 import (
        BOOKING_SYSTEM_PROMPT,
        BOOKING_USER_PROMPT,
    )
    from app.prompts.conversation_intelligence_v1 import (
        CONVERSATION_INTELLIGENCE_SYSTEM_PROMPT,
        CONVERSATION_INTELLIGENCE_USER_PROMPT,
    )
    from app.prompts.outreach_v1 import (
        OUTREACH_SYSTEM_PROMPT,
        OUTREACH_USER_PROMPT,
    )
    from app.prompts.qualification_v1 import (
        QUALIFICATION_SYSTEM_PROMPT,
        QUALIFICATION_USER_PROMPT,
    )

    _registry.register(
        "qualification",
        "v1",
        QUALIFICATION_SYSTEM_PROMPT,
        QUALIFICATION_USER_PROMPT,
        agent_type="qualification",
        description="Lead scoring and qualification (initial version)",
    )
    _registry.register(
        "conversation_intelligence",
        "v1",
        CONVERSATION_INTELLIGENCE_SYSTEM_PROMPT,
        CONVERSATION_INTELLIGENCE_USER_PROMPT,
        agent_type="conversation_intelligence",
        description="9-dimension conversation analysis with memory",
    )
    _registry.register(
        "outreach",
        "v1",
        OUTREACH_SYSTEM_PROMPT,
        OUTREACH_USER_PROMPT,
        agent_type="outreach",
        description="Personalized outreach email generation",
    )
    _registry.register(
        "booking",
        "v1",
        BOOKING_SYSTEM_PROMPT,
        BOOKING_USER_PROMPT,
        agent_type="booking",
        description="Meeting setup recommendation",
    )

    logger.info(
        "all_prompts_registered",
        count=len(_registry.list_prompts()),
    )
