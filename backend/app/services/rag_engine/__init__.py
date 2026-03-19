"""
app/services/rag_engine/__init__.py
Public entry point: retrieve_context(message, url) -> str
"""
from app.services.rag_engine.knowledge_retriever import retrieve_knowledge
from app.services.rag_engine.context_builder import build_rag_context
from app.logger import logger
from typing import Tuple, List, Dict, Any


async def retrieve_context(message: str = "", url: str = "") -> Tuple[str, List[str]]:
    """
    High-level RAG entry point with 1.5s strict timeout.
    Returns (rag_context_string, evidence_titles_list)
    """
    import asyncio
    
    try:
        # Offload synchronous vector search with strict timeout
        results = await asyncio.wait_for(
            asyncio.to_thread(retrieve_knowledge, message, url),
            timeout=1.5
        )
    except asyncio.TimeoutError:
        logger.warning(f"RAG retrieval timed out after 1.5s for {url}")
        results = []
    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        results = []
    
    context = build_rag_context(results)
    evidence = [r.get("title", "") for r in results if r.get("title")]
    return context, evidence


__all__ = ["retrieve_context"]
