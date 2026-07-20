# ============================================================
# SalesOS AI — Qdrant Vector Client
# Lifecycle management for the async Qdrant vector database client.
# Strictly encapsulated within app/db — never leaked outside.
# ============================================================

from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("db.qdrant")

_qdrant_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """Get or initialize the global async Qdrant client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        api_key = settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        
        # Build client connection params
        url_or_host = {}
        if settings.QDRANT_HOST.startswith("http://") or settings.QDRANT_HOST.startswith("https://"):
            url_or_host["url"] = settings.QDRANT_HOST
        else:
            url_or_host["host"] = settings.QDRANT_HOST
            url_or_host["port"] = settings.QDRANT_PORT

        _qdrant_client = AsyncQdrantClient(
            api_key=api_key,
            **url_or_host,
        )
        logger.info(
            "qdrant_client_initialized",
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
    return _qdrant_client


async def close_qdrant_client() -> None:
    """Close the global Qdrant client connection on application shutdown."""
    global _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
        logger.info("qdrant_client_closed")


async def ensure_collection_exists(
    client: AsyncQdrantClient,
    collection_name: str,
    vector_size: int = 1536,
    distance: Distance = Distance.COSINE,
) -> None:
    """Ensure a Qdrant collection exists; create it with vector params if absent."""
    try:
        collections = await client.get_collections()
        existing_names = {c.name for c in collections.collections}
        if collection_name not in existing_names:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )
            logger.info(
                "qdrant_collection_created",
                collection_name=collection_name,
                vector_size=vector_size,
            )
    except Exception as e:
        logger.error(
            "qdrant_collection_ensure_failed",
            collection_name=collection_name,
            error=str(e),
        )
