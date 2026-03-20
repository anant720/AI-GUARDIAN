"""
knowledge_retriever.py
───────────────────────
Combines message and URL signals into a query, searches the vector store,
and returns the top-k most relevant phishing knowledge entries.
"""
from typing import List, Dict, Any
from app.logger import logger
from app.services.rag_engine.vector_store import search


def _build_query(message: str, url: str) -> str:
    """Combine available signals into a single search query."""
    parts = []
    if message and message.strip():
        parts.append(message.strip())
    if url and url.strip():
        parts.append(url.strip())
    query = " ".join(parts)
    return query[:512]  # cap length for embedding model


def retrieve_knowledge(
    message: str = "",
    url: str = "",
    n_results: int = 3
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k relevant phishing/scam knowledge entries.

    Args:
        message: The user-submitted message text
        url: The scanned URL
        n_results: How many results to return

    Returns:
        List of knowledge entry dicts sorted by relevance
    """
    query = _build_query(message, url)

    if not query.strip():
        logger.warning("RAG: empty query — skipping retrieval")
        return []

    results = search(query, n_results=n_results)

    # Filter out low-similarity results (< 0.7 threshold for production precision)
    filtered = [r for r in results if r.get("similarity", 0) >= 0.7]

    logger.info(
        f"RAG retrieved {len(filtered)}/{len(results)} knowledge entries "
        f"(similarity >= 0.7)"
    )
    return filtered
