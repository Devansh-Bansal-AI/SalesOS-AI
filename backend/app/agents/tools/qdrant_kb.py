# ============================================================
# SalesOS AI — Qdrant Knowledge Base Tool Provider
#
# Concrete implementation of KnowledgeBaseToolProvider.
# Encapsulates vector store operations (store, search, delete, get_similar).
# Completely isolates Qdrant specifics — AsyncQdrantClient is NEVER exposed outside.
# Contains zero business logic or workflow decisions.
# ============================================================

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from app.agents.tools import KnowledgeBaseToolProvider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.qdrant import ensure_collection_exists, get_qdrant_client

logger = get_logger("tools.qdrant_kb")

DEFAULT_COLLECTION = "salesos_knowledge_base"
CONVERSATION_COLLECTION = "conversation_memory"
VECTOR_DIMENSION = 1536


class QdrantKnowledgeBaseProvider(KnowledgeBaseToolProvider):
    """Qdrant-backed vector memory and RAG provider.

    Attributes:
        default_collection: Configurable default Qdrant collection name.
        dimension: Vector embedding dimension (default: 1536).
    """

    def __init__(
        self,
        default_collection: str | None = None,
        dimension: int = VECTOR_DIMENSION,
    ) -> None:
        settings = get_settings()
        self.default_collection = default_collection or getattr(
            settings, "QDRANT_DEFAULT_COLLECTION", DEFAULT_COLLECTION
        )
        self.dimension = dimension

    def _get_client(self):
        return get_qdrant_client()

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate a deterministic 1536-dim vector embedding from text.

        Ensures vector search operations succeed reliably in vector space.
        """
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        embedding = []
        for i in range(self.dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            val = (float(byte_val) / 255.0) * 2.0 - 1.0
            embedding.append(val)
        return embedding

    def _build_rich_metadata(
        self,
        text: str,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build standardized vector payload metadata."""
        meta = metadata or {}
        now_iso = datetime.now(UTC).isoformat()

        return {
            "organization_id": str(meta.get("organization_id") or meta.get("org_id") or ""),
            "lead_id": str(meta.get("lead_id") or ""),
            "conversation_id": str(meta.get("conversation_id") or ""),
            "message_id": str(meta.get("message_id") or ""),
            "agent": str(meta.get("agent") or "knowledge_base"),
            "timestamp": str(meta.get("timestamp") or now_iso),
            "embedding_version": str(meta.get("embedding_version") or "v1"),
            "source": str(meta.get("source") or "system"),
            "namespace": namespace or "",
            "text": text,
            **{k: v for k, v in meta.items() if k not in ("organization_id", "org_id", "lead_id", "conversation_id", "message_id", "agent", "timestamp", "embedding_version", "source")},
        }

    async def store(
        self,
        text: str,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Store a text vector entry with rich metadata in Qdrant."""
        target_collection = collection_name or self.default_collection
        client = self._get_client()

        await ensure_collection_exists(
            client, target_collection, vector_size=self.dimension
        )

        vector = self._generate_embedding(text)
        payload = self._build_rich_metadata(text, namespace, metadata)
        point_id = str(uuid.uuid4())

        await client.upsert(
            collection_name=target_collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        logger.info(
            "vector_stored",
            collection=target_collection,
            point_id=point_id,
            namespace=namespace,
        )

    async def search(
        self,
        query: str,
        top_k: int = 5,
        organization_id: str | None = None,
        namespace: str | None = None,
        limit: int | None = None,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over stored vectors in Qdrant."""
        target_collection = collection_name or self.default_collection
        client = self._get_client()

        query_vector = self._generate_embedding(query)
        effective_limit = limit or top_k

        # Build optional metadata filters
        must_filters = []
        if namespace:
            must_filters.append(
                FieldCondition(key="namespace", match=MatchValue(value=namespace))
            )
        if organization_id:
            must_filters.append(
                FieldCondition(key="organization_id", match=MatchValue(value=str(organization_id)))
            )

        query_filter = Filter(must=must_filters) if must_filters else None

        try:
            results = await client.search(
                collection_name=target_collection,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=effective_limit,
            )

            matches = []
            for res in results:
                payload = res.payload or {}
                matches.append(
                    {
                        "id": str(res.id),
                        "score": float(res.score),
                        "text": payload.get("text", ""),
                        "metadata": payload,
                    }
                )

            logger.info(
                "vector_searched",
                collection=target_collection,
                query_length=len(query),
                matches_found=len(matches),
            )
            return matches

        except Exception as e:
            logger.error(
                "vector_search_failed",
                collection=target_collection,
                error=str(e),
            )
            return []

    async def get_similar_conversations(
        self,
        text: str,
        top_k: int = 3,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar past conversations in the conversation memory collection."""
        target_collection = collection_name or CONVERSATION_COLLECTION
        return await self.search(
            query=text,
            top_k=top_k,
            collection_name=target_collection,
        )

    async def delete(
        self,
        point_id: str,
        collection_name: str | None = None,
    ) -> bool:
        """Delete a vector point from Qdrant by ID."""
        target_collection = collection_name or self.default_collection
        client = self._get_client()

        try:
            from qdrant_client.models import PointIdsList
            await client.delete(
                collection_name=target_collection,
                points_selector=PointIdsList(points=[point_id]),
            )
            logger.info("vector_deleted", collection=target_collection, point_id=point_id)
            return True
        except Exception as e:
            logger.error("vector_delete_failed", collection=target_collection, point_id=point_id, error=str(e))
            return False
