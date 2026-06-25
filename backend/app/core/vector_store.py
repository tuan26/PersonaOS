"""
Vector Store — semantic memory layer for personas.

This is what lets a persona actually *remember*: instead of only loading the
N most recent rows, we embed every memory and retrieve the ones semantically
relevant to the current message/topic.

- Embeddings: OpenAI (text-embedding-3-small) — cheap, good quality.
- Storage: ChromaDB (PersistentClient on disk at settings.CHROMADB_PATH).

Design notes:
- ChromaDB's client is synchronous → all chroma calls run in a thread via
  asyncio.to_thread so they don't block the FastAPI event loop.
- Everything is best-effort: if embedding or chroma fails, callers degrade
  gracefully to the SQL "recent memories" path. Memory must never break chat.
- One shared collection, filtered by `persona_id` in metadata.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.config import settings
from app.core.llm import get_openai_client

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "persona_memories"
_collection: Any = None  # lazy-initialized chromadb collection


def _get_collection() -> Any:
    """Lazily create the ChromaDB persistent collection (sync)."""
    global _collection
    if _collection is None:
        import chromadb  # imported lazily so app starts even if chromadb missing

        client = chromadb.PersistentClient(path=settings.CHROMADB_PATH)
        _collection = client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def _embed(texts: list[str]) -> Optional[list[list[float]]]:
    """Embed a batch of texts via OpenAI. Returns None on failure."""
    if not texts:
        return []
    try:
        client = get_openai_client()
        resp = await client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=texts,
        )
        return [item.embedding for item in resp.data]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Embedding failed: {str(e)[:200]}")
        return None


def _clean_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """ChromaDB metadata only accepts str/int/float/bool — drop the rest."""
    clean: dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif v is not None:
            clean[k] = str(v)
    return clean


class VectorStore:
    """Semantic memory store keyed by persona."""

    @staticmethod
    async def add_memory(
        memory_id: str,
        persona_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Embed a memory and upsert it into the vector store.
        Returns True on success, False if it degraded (caller can ignore).
        """
        if not text or not text.strip():
            return False

        embeddings = await _embed([text])
        if not embeddings:
            return False

        meta = _clean_metadata(metadata or {})
        meta["persona_id"] = persona_id

        try:
            collection = _get_collection()
            await asyncio.to_thread(
                collection.upsert,
                ids=[memory_id],
                embeddings=embeddings,
                documents=[text],
                metadatas=[meta],
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"VectorStore.add_memory failed: {str(e)[:200]}")
            return False

    @staticmethod
    async def search(
        persona_id: str,
        query_text: str,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Return memories semantically relevant to query_text for this persona.

        Each result: {"id", "content", "metadata", "distance"}.
        Returns [] on any failure (caller falls back to recent memories).
        """
        if not query_text or not query_text.strip():
            return []

        embeddings = await _embed([query_text])
        if not embeddings:
            return []

        try:
            collection = _get_collection()
            res = await asyncio.to_thread(
                collection.query,
                query_embeddings=embeddings,
                n_results=n_results,
                where={"persona_id": persona_id},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"VectorStore.search failed: {str(e)[:200]}")
            return []

        out: list[dict[str, Any]] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for i, mid in enumerate(ids):
            out.append({
                "id": mid,
                "content": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
            })
        return out

    @staticmethod
    async def delete_persona(persona_id: str) -> bool:
        """Delete all vectors for a persona (e.g., on hard delete)."""
        try:
            collection = _get_collection()
            await asyncio.to_thread(
                collection.delete, where={"persona_id": persona_id}
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"VectorStore.delete_persona failed: {str(e)[:200]}")
            return False
