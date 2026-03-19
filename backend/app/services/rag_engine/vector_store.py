"""
vector_store.py
────────────────
ChromaDB-backed persistent vector store for phishing knowledge.

On first startup: seeds the collection from phishing_knowledge.json.
On subsequent startups: reuses persisted collection (no re-seeding).

ChromaDB persistent directory: backend/data/chroma_db/
Knowledge JSON file:          backend/data/phishing_knowledge.json
"""
import os
import json
import shutil
from typing import List, Dict, Any, Optional, Tuple
from app.logger import logger
from app.config import settings


_CHROMA_PATH = getattr(settings, "CHROMA_DB_PATH", os.path.join("data", "chroma_db"))
_KNOWLEDGE_PATH = getattr(settings, "PHISHING_KNOWLEDGE_PATH",
                          os.path.join("data", "phishing_knowledge.json"))
_COLLECTION_NAME = "phishing_knowledge"

_client = None
_collection = None
_fallback_index: Optional[List[Tuple[Dict[str, Any], List[float]]]] = None
_chroma_disabled: bool = False


def _reset_chroma_store() -> None:
    """
    Reset the persisted ChromaDB directory when on-disk state is incompatible.
    This can happen after dependency/version changes (e.g., sqlite encoding changes).
    """
    try:
        if os.path.isdir(_CHROMA_PATH):
            shutil.rmtree(_CHROMA_PATH, ignore_errors=True)
        os.makedirs(_CHROMA_PATH, exist_ok=True)
        logger.warning(f"ChromaDB store reset at '{_CHROMA_PATH}'")
    except Exception as e:
        logger.error(f"Failed to reset ChromaDB store at '{_CHROMA_PATH}': {e}")


def _ensure_fallback_index() -> List[Tuple[Dict[str, Any], List[float]]]:
    """
    Build an in-process vector index if ChromaDB is unavailable.
    This keeps RAG functional in constrained environments.
    """
    global _fallback_index
    if _fallback_index is not None:
        return _fallback_index

    if not os.path.exists(_KNOWLEDGE_PATH):
        logger.warning(f"Knowledge file not found at '{_KNOWLEDGE_PATH}' — fallback RAG empty")
        _fallback_index = []
        return _fallback_index

    try:
        from app.services.rag_engine.embedding_model import embedding_model
        with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            entries: List[Dict[str, Any]] = json.load(f)
        texts = [f"{e.get('title','')}. {e.get('description','')}".strip() for e in entries]
        embeddings = embedding_model.embed_batch(texts)
        _fallback_index = list(zip(entries, embeddings))
        logger.warning(f"Fallback RAG index built (entries={len(_fallback_index)})")
        return _fallback_index
    except Exception as e:
        logger.error(f"Fallback RAG index build failed: {e}")
        _fallback_index = []
        return _fallback_index


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    try:
        import numpy as np
        av = np.asarray(a, dtype=float)
        bv = np.asarray(b, dtype=float)
        denom = (np.linalg.norm(av) * np.linalg.norm(bv))
        if denom == 0:
            return 0.0
        return float(np.dot(av, bv) / denom)
    except Exception:
        return 0.0


def _get_collection():
    """Lazy-initialise ChromaDB client and collection."""
    global _client, _collection, _chroma_disabled

    if _collection is not None:
        return _collection
    if _chroma_disabled:
        return None

    def _init_once():
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        os.makedirs(_CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=_CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Get or create the collection (cosine similarity)
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        # Count can trigger sqlite metadata decoding; protect against incompatible on-disk state.
        try:
            docs = _collection.count()
        except TypeError as e:
            # Known failure mode: "object of type 'int' has no len()"
            raise e

        logger.info(f"ChromaDB collection '{_COLLECTION_NAME}' ready (docs={docs})")

        # Seed if empty
        if docs == 0:
            _seed_collection(_collection)

        return _collection

    try:
        return _init_once()
    except TypeError as e:
        msg = str(e)
        if "has no len" in msg:
            logger.warning(f"ChromaDB persistent state incompatible ({e}); resetting store and re-initializing")
            _reset_chroma_store()
            try:
                return _init_once()
            except Exception as e2:
                logger.error(f"ChromaDB re-init after reset failed: {e2}")
                _chroma_disabled = True
                return None
        logger.error(f"ChromaDB init type error: {e}")
        _chroma_disabled = True
        return None

    except Exception as e:
        logger.error(f"ChromaDB init failed: {e}")
        _chroma_disabled = True
        return None


def _seed_collection(collection) -> None:
    """Load phishing_knowledge.json and insert all entries into ChromaDB."""
    if not os.path.exists(_KNOWLEDGE_PATH):
        logger.warning(f"Knowledge file not found at '{_KNOWLEDGE_PATH}' — RAG will have no knowledge")
        return

    try:
        from app.services.rag_engine.embedding_model import embedding_model

        with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            entries: List[Dict] = json.load(f)

        logger.info(f"Seeding ChromaDB with {len(entries)} knowledge entries...")

        # Batch embed all documents
        texts = [f"{e['title']}. {e['description']}" for e in entries]
        embeddings = embedding_model.embed_batch(texts)

        ids = [str(e["id"]) for e in entries]
        documents = texts
        metadatas = [
            {
                "title": e.get("title", ""),
                "brand": e.get("brand", ""),
                "threat_type": e.get("threat_type", ""),
                "indicators": ", ".join(e.get("indicators", []))
            }
            for e in entries
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"ChromaDB seeded with {len(entries)} entries")

    except Exception as e:
        logger.error(f"ChromaDB seeding failed: {e}")


def search(query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Semantic search against the phishing knowledge base.

    Args:
        query_text: The text to search for (message + URL signals)
        n_results: Number of top results to return

    Returns:
        List of result dicts with title, description, threat_type, distance
    """
    collection = _get_collection()
    if collection is None:
        # Fallback to in-process vector search
        try:
            from app.services.rag_engine.embedding_model import embed
            query_embedding = embed(query_text)
            idx = _ensure_fallback_index()
            if not idx:
                return []

            scored: List[Tuple[float, Dict[str, Any]]] = []
            for entry, emb in idx:
                sim = _cosine_similarity(query_embedding, emb)
                scored.append((sim, entry))

            scored.sort(key=lambda x: x[0], reverse=True)
            hits = []
            for sim, e in scored[: max(1, n_results)]:
                hits.append(
                    {
                        "title": e.get("title", ""),
                        "description": f"{e.get('title','')}. {e.get('description','')}".strip(),
                        "brand": e.get("brand", ""),
                        "threat_type": e.get("threat_type", ""),
                        "indicators": ", ".join(e.get("indicators", [])) if isinstance(e.get("indicators"), list) else str(e.get("indicators", "")),
                        "similarity": round(float(sim), 3),
                    }
                )
            return hits
        except Exception as e:
            logger.warning(f"RAG fallback search failed: {e}")
            return []

    try:
        from app.services.rag_engine.embedding_model import embed
        query_embedding = embed(query_text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count() or 1),
            include=["documents", "metadatas", "distances"]
        )

        hits = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            hits.append({
                "title": meta.get("title", ""),
                "description": doc,
                "brand": meta.get("brand", ""),
                "threat_type": meta.get("threat_type", ""),
                "indicators": meta.get("indicators", ""),
                "similarity": round(1 - dist, 3)   # cosine: distance→similarity
            })

        return hits

    except Exception as e:
        logger.error(f"ChromaDB search failed: {e}")
        return []
