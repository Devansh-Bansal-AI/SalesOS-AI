# ============================================================
# SalesOS AI — Rate Limiting Middleware
#
# In-memory sliding-window rate limiter per client IP.
# Uses the configurable RATE_LIMIT_PER_MINUTE and
# RATE_LIMIT_PUBLIC_PER_MINUTE settings.
#
# NOTE: In-memory storage is suitable for single-instance
# deployments only. For production multi-instance, migrate
# to Redis-backed storage.
# ============================================================

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("rate_limit")

# Public endpoint prefixes (no auth required → stricter limits)
_PUBLIC_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/public/",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per client IP.

    Applies stricter limits to public/auth endpoints and standard
    limits to authenticated endpoints.
    """

    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self._limit_authenticated = settings.RATE_LIMIT_PER_MINUTE
        self._limit_public = settings.RATE_LIMIT_PUBLIC_PER_MINUTE
        self._window_seconds = 60
        # IP → list of request timestamps (sliding window)
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind a proxy."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_public(self, path: str) -> bool:
        """Check if a path is a public (unauthenticated) endpoint."""
        return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)

    def _cleanup_window(self, timestamps: list[float], now: float) -> list[float]:
        """Remove timestamps outside the sliding window."""
        cutoff = now - self._window_seconds
        return [ts for ts in timestamps if ts > cutoff]

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/api/v1/health", "/api/v1/health/ready"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.monotonic()
        is_public = self._is_public(request.url.path)
        limit = self._limit_public if is_public else self._limit_authenticated

        # Clean and check
        key = f"{client_ip}:{'pub' if is_public else 'auth'}"
        self._requests[key] = self._cleanup_window(self._requests[key], now)

        if len(self._requests[key]) >= limit:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                limit=limit,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "errors": [{
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {limit} requests per minute.",
                    }]
                },
                headers={"Retry-After": str(self._window_seconds)},
            )

        # Record this request
        self._requests[key].append(now)

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, limit - len(self._requests[key]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(self._window_seconds)

        return response
