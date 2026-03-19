"""
embedding_model.py
───────────────────
Singleton sentence-transformer embedding model.

Reuses the ALL-MiniLM-L6-v2 model that sentence-transformers
already downloaded during Message Intelligence setup.
Loaded once at startup — no repeated model loads per request.
"""
from typing import List
from app.logger import logger


class EmbeddingModel:
    """Singleton wrapper around sentence-transformers for RAG embeddings."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    def _ensure_loaded(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model for RAG: all-MiniLM-L6-v2")
                self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                logger.info("RAG embedding model ready")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise

    def embed(self, text: str) -> List[float]:
        """Embed a text string into a float vector."""
        self._ensure_loaded()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in a single batch pass."""
        self._ensure_loaded()
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]


# Module-level singleton
embedding_model = EmbeddingModel()


def embed(text: str) -> List[float]:
    """Public shorthand: embed a single text."""
    return embedding_model.embed(text)
