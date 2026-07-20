# ============================================================
# SalesOS AI — Redis Connection
# Async Redis client with connection pooling.
# ============================================================

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

settings = get_settings()

# Connection pool
_redis_pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True,
)


def get_redis() -> Redis:
    """Get an async Redis client from the connection pool.

    Usage in route handlers:
        async def my_endpoint(redis: Redis = Depends(get_redis)):
            ...
    """
    return Redis(connection_pool=_redis_pool)


async def close_redis() -> None:
    """Close the Redis connection pool."""
    await _redis_pool.disconnect()
