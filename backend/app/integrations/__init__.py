# ============================================================
# SalesOS AI — Integration Provider Registry
#
# Plugin architecture for external service integrations.
# Every integration (email, calendar, CRM) follows the same pattern:
#
#   1. Define an abstract provider interface
#   2. Implement concrete providers (Gmail, Outlook, SMTP)
#   3. Register them in the registry
#   4. Services resolve providers at runtime
#
# This makes the Email Service depend on EmailProvider,
# not on Gmail or Outlook directly.
# ============================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

logger = get_logger("integrations.registry")


# ── Email Provider Interface ───────────────────────────────


@dataclass
class EmailMessage:
    """Standardized email message for all providers."""
    to: str
    subject: str
    body_text: str
    body_html: str | None = None
    from_email: str | None = None
    reply_to: str | None = None
    cc: list[str] | None = None
    bcc: list[str] | None = None
    headers: dict[str, str] | None = None


@dataclass
class EmailResult:
    """Standardized email delivery result."""
    success: bool
    provider: str
    message_id: str | None = None
    error: str | None = None


class EmailProvider(ABC):
    """Abstract email provider interface.

    Implementations: GmailProvider, OutlookProvider, AzureProvider, SMTPProvider
    """

    provider_name: str = "base"

    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailResult:
        """Send an email through this provider."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable."""
        ...


# ── Calendar Provider Interface ────────────────────────────


@dataclass
class CalendarEvent:
    """Standardized calendar event for all providers."""
    title: str
    description: str | None = None
    start_time: str = ""  # ISO 8601
    end_time: str = ""    # ISO 8601
    timezone: str = "UTC"
    attendees: list[str] | None = None
    location: str | None = None
    meeting_link: str | None = None


@dataclass
class CalendarSlot:
    """Available time slot."""
    start_time: str  # ISO 8601
    end_time: str    # ISO 8601


@dataclass
class CalendarResult:
    """Result from a calendar operation."""
    success: bool
    provider: str
    event_id: str | None = None
    meeting_link: str | None = None
    error: str | None = None


class CalendarProvider(ABC):
    """Abstract calendar provider interface.

    Implementations: GoogleCalendarProvider, MicrosoftCalendarProvider, CalendlyProvider
    """

    provider_name: str = "base"

    @abstractmethod
    async def create_event(self, event: CalendarEvent) -> CalendarResult:
        """Create a calendar event."""
        ...

    @abstractmethod
    async def get_availability(
        self, start: str, end: str, timezone: str = "UTC"
    ) -> list[CalendarSlot]:
        """Get available time slots in a date range."""
        ...

    @abstractmethod
    async def cancel_event(self, event_id: str) -> CalendarResult:
        """Cancel a calendar event."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable."""
        ...


# ── Search Provider Interface ──────────────────────────────


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str


class SearchProvider(ABC):
    """Abstract search provider for enrichment agents."""

    provider_name: str = "base"

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search the web for information."""
        ...


# ── Provider Registry ──────────────────────────────────────


class IntegrationRegistry:
    """Central registry for all integration providers.

    Usage:
        registry = IntegrationRegistry()
        registry.register_email("gmail", GmailProvider())
        registry.register_email("smtp", SMTPProvider())

        # Resolve at runtime
        email_provider = registry.get_email("gmail")
        await email_provider.send(message)
    """

    def __init__(self) -> None:
        self._email_providers: dict[str, EmailProvider] = {}
        self._calendar_providers: dict[str, CalendarProvider] = {}
        self._search_providers: dict[str, SearchProvider] = {}
        self._default_email: str | None = None
        self._default_calendar: str | None = None
        self._default_search: str | None = None

    # ── Email ───────────────────────────────────────────

    def register_email(
        self, name: str, provider: EmailProvider, *, default: bool = False
    ) -> None:
        self._email_providers[name] = provider
        if default or self._default_email is None:
            self._default_email = name
        logger.info("email_provider_registered", provider=name, default=default)

    def get_email(self, name: str | None = None) -> EmailProvider:
        name = name or self._default_email
        if not name or name not in self._email_providers:
            raise ValueError(f"Email provider '{name}' not registered")
        return self._email_providers[name]

    # ── Calendar ────────────────────────────────────────

    def register_calendar(
        self, name: str, provider: CalendarProvider, *, default: bool = False
    ) -> None:
        self._calendar_providers[name] = provider
        if default or self._default_calendar is None:
            self._default_calendar = name
        logger.info("calendar_provider_registered", provider=name, default=default)

    def get_calendar(self, name: str | None = None) -> CalendarProvider:
        name = name or self._default_calendar
        if not name or name not in self._calendar_providers:
            raise ValueError(f"Calendar provider '{name}' not registered")
        return self._calendar_providers[name]

    # ── Search ──────────────────────────────────────────

    def register_search(
        self, name: str, provider: SearchProvider, *, default: bool = False
    ) -> None:
        self._search_providers[name] = provider
        if default or self._default_search is None:
            self._default_search = name
        logger.info("search_provider_registered", provider=name, default=default)

    def get_search(self, name: str | None = None) -> SearchProvider:
        name = name or self._default_search
        if not name or name not in self._search_providers:
            raise ValueError(f"Search provider '{name}' not registered")
        return self._search_providers[name]

    # ── Introspection ───────────────────────────────────

    def list_providers(self) -> dict[str, list[str]]:
        """List all registered providers for diagnostics."""
        return {
            "email": list(self._email_providers.keys()),
            "calendar": list(self._calendar_providers.keys()),
            "search": list(self._search_providers.keys()),
        }


# ── Global Registry Instance ───────────────────────────────

_registry = IntegrationRegistry()


def get_registry() -> IntegrationRegistry:
    """Get the global integration registry."""
    return _registry
