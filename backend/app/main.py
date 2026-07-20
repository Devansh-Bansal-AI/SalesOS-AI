# ============================================================
# SalesOS AI — FastAPI Application Factory
# Entry point for the backend application.
# ============================================================

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    SalesOSError,
    ValidationError,
)
from app.core.logging import get_logger, setup_logging
from app.db.redis import close_redis
from app.db.session import close_db
from app.middleware.logging import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.schemas.common import ErrorDetail, ErrorResponse

logger = get_logger("app")


# ── Lifespan ────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()

    # Startup
    setup_logging()
    logger.info(
        "application_starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )

    # Register workflows and event handlers
    from app.events.communication_handlers import register_communication_handlers
    from app.events.handlers import register_event_handlers
    from app.workflows.lead_lifecycle import register_lead_lifecycle_workflow

    register_lead_lifecycle_workflow()
    register_event_handlers()
    register_communication_handlers()

    # Register SMTP email provider
    from app.integrations import get_registry
    from app.integrations.email.smtp import SMTPProvider

    registry = get_registry()
    registry.register_email("smtp", SMTPProvider(), default=True)

    # Register Postgres CRM Tool Provider & Qdrant Knowledge Base Provider
    from app.agents.tools import get_tool_registry
    from app.agents.tools.postgres_crm import PostgresCRMProvider
    from app.agents.tools.qdrant_kb import QdrantKnowledgeBaseProvider

    tool_registry = get_tool_registry()
    tool_registry.register_crm(PostgresCRMProvider())
    tool_registry.register_knowledge_base(QdrantKnowledgeBaseProvider())

    # Register all AI agents (plugin registry)
    from app.agents.registry import register_all_agents

    register_all_agents()

    # Register all prompt templates (versioned)
    from app.prompts.registry import register_all_prompts

    register_all_prompts()

    logger.info("platform_initialized")

    yield

    # Shutdown
    logger.info("application_shutting_down")
    from app.db.qdrant import close_qdrant_client
    await close_db()
    await close_redis()
    await close_qdrant_client()
    logger.info("application_stopped")


# ── App Factory ─────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Sales Operations Platform",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost first) ─────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)

    # ── Exception Handlers ──────────────────────────────
    _register_exception_handlers(app)

    # ── Routes ──────────────────────────────────────────
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }

    return app


# ── Exception Handlers ─────────────────────────────────────

HTTP_STATUS_MAP = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    NotFoundError: 404,
    ValidationError: 422,
    ConflictError: 409,
    RateLimitError: 429,
}


def _register_exception_handlers(app: FastAPI) -> None:
    """Map custom exceptions to HTTP responses."""

    @app.exception_handler(SalesOSError)
    async def salesos_exception_handler(request: Request, exc: SalesOSError):
        status_code = HTTP_STATUS_MAP.get(type(exc), 500)
        return ORJSONResponse(
            status_code=status_code,
            content=ErrorResponse(
                errors=[
                    ErrorDetail(
                        code=exc.code,
                        message=exc.message,
                        field=getattr(exc, "field", None),
                    )
                ]
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), exc_info=True)
        return ORJSONResponse(
            status_code=500,
            content=ErrorResponse(
                errors=[
                    ErrorDetail(
                        code="INTERNAL_ERROR",
                        message="An unexpected error occurred",
                    )
                ]
            ).model_dump(),
        )


# ── Application Instance ───────────────────────────────────

app = create_app()
