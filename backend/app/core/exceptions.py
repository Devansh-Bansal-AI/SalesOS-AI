# ============================================================
# SalesOS AI — Exception Hierarchy
# All custom exceptions used throughout the application.
# Maps cleanly to HTTP status codes in API layer.
# ============================================================

from typing import Any


class SalesOSError(Exception):
    """Base exception for all SalesOS errors."""

    def __init__(self, message: str = "An unexpected error occurred", code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ── Authentication & Authorization ──────────────────────────


class AuthenticationError(SalesOSError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthorizationError(SalesOSError):
    """Raised when authorization fails (403)."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, code="AUTHORIZATION_ERROR")


# ── Validation ──────────────────────────────────────────────


class ValidationError(SalesOSError):
    """Raised when input validation fails (422)."""

    def __init__(self, message: str = "Validation error", field: str | None = None):
        self.field = field
        super().__init__(message=message, code="VALIDATION_ERROR")


# ── Resource Errors ─────────────────────────────────────────


class NotFoundError(SalesOSError):
    """Raised when a requested resource is not found (404)."""

    def __init__(self, resource: str = "Resource", identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message=message, code="NOT_FOUND")


class ConflictError(SalesOSError):
    """Raised when a resource conflict occurs (409)."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message=message, code="CONFLICT")


class DuplicateError(ConflictError):
    """Raised when a duplicate resource is detected."""

    def __init__(self, resource: str = "Resource", field: str = ""):
        message = f"{resource} already exists"
        if field:
            message = f"{resource} with this {field} already exists"
        super().__init__(message=message)
        self.code = "DUPLICATE"


# ── Rate Limiting ───────────────────────────────────────────


class RateLimitError(SalesOSError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED")


# ── AI / Agent Errors ───────────────────────────────────────


class AgentError(SalesOSError):
    """Raised when an AI agent fails."""

    def __init__(self, agent_type: str, message: str = "Agent execution failed"):
        self.agent_type = agent_type
        super().__init__(message=f"[{agent_type}] {message}", code="AGENT_ERROR")


class LLMError(SalesOSError):
    """Raised when an LLM call fails."""

    def __init__(self, provider: str, message: str = "LLM request failed"):
        self.provider = provider
        super().__init__(message=f"[{provider}] {message}", code="LLM_ERROR")


class LowConfidenceError(AgentError):
    """Raised when agent confidence is below threshold."""

    def __init__(self, agent_type: str, confidence: float, threshold: float):
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            agent_type=agent_type,
            message=f"Confidence {confidence:.2f} below threshold {threshold:.2f}",
        )
        self.code = "LOW_CONFIDENCE"


# ── External Service Errors ─────────────────────────────────


class ExternalServiceError(SalesOSError):
    """Raised when an external service call fails."""

    def __init__(self, service: str, message: str = "External service error"):
        self.service = service
        super().__init__(message=f"[{service}] {message}", code="EXTERNAL_SERVICE_ERROR")


class EmailDeliveryError(ExternalServiceError):
    """Raised when email delivery fails."""

    def __init__(self, message: str = "Email delivery failed"):
        super().__init__(service="email", message=message)
        self.code = "EMAIL_DELIVERY_ERROR"


class CalendarError(ExternalServiceError):
    """Raised when calendar integration fails."""

    def __init__(self, message: str = "Calendar operation failed"):
        super().__init__(service="calendar", message=message)
        self.code = "CALENDAR_ERROR"
