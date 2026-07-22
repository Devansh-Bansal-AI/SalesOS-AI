# ============================================================
# SalesOS AI — Health & Readiness Probes API Router
# ============================================================

from typing import Any

from fastapi import APIRouter, Response, status

from app.db.qdrant import get_qdrant_client
from app.db.redis import get_redis
from app.db.session import async_session_factory
from app.schemas.common import APIResponse

router = APIRouter(prefix="/health", tags=["Health & Readiness"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness probe: verifies basic HTTP server execution."""
    return {"status": "ok", "service": "SalesOS AI API"}


@router.get("/ready")
async def readiness_check(response: Response) -> APIResponse[dict[str, Any]]:
    """Readiness probe: validates connections to Postgres, Redis, and Qdrant."""
    db_status = "healthy"
    redis_status = "healthy"
    qdrant_status = "healthy"
    is_ready = True

    # 1. Check Postgres
    try:
        async with async_session_factory() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
        is_ready = False

    # 2. Check Redis
    try:
        redis = get_redis()
        ping_res = await redis.ping()
        if not ping_res:
            redis_status = "unhealthy"
            is_ready = False
    except Exception:
        redis_status = "unhealthy"
        is_ready = False

    # 3. Check Qdrant
    try:
        qdrant = get_qdrant_client()
        await qdrant.list_collections()
    except Exception:
        qdrant_status = "degraded"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return APIResponse(
        data={
            "status": "ready" if is_ready else "not_ready",
            "postgres": db_status,
            "redis": redis_status,
            "qdrant": qdrant_status,
        }
    )
