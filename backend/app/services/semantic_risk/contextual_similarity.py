"""
contextual_similarity.py
─────────────────────────
Computes semantic similarity between the current message+URL and all 50
phishing knowledge entries stored in ChromaDB.

Reuses the RAG engine's vector store — no second embedding model needed.
Returns top-3 matches with similarity scores.
"""
from typing import Dict, Any, List

from app.logger import logger


def compute_contextual_similarity(
    message: str = "",
    url: str = "",
    n_results: int = 3
) -> Dict[str, Any]:
    """
    Embed message+URL query and search ChromaDB phishing knowledge.

    Returns:
        max_similarity (0-1), top_matches list, semantic_risk_score (0-100)
    """
    query = " ".join(filter(None, [message.strip(), url.strip()]))[:512]

    if not query.strip():
        return {
            "max_similarity": 0.0,
            "top_matches": [],
            "semantic_risk_score": 0
        }

    try:
        from app.services.rag_engine.vector_store import search
        results = search(query, n_results=n_results)

        if not results:
            return {"max_similarity": 0.0, "top_matches": [], "semantic_risk_score": 0}

        max_sim = max(r.get("similarity", 0) for r in results)
        top_matches = [
            {
                "title": r.get("title"),
                "threat_type": r.get("threat_type"),
                "brand": r.get("brand"),
                "similarity": r.get("similarity")
            }
            for r in results if r.get("similarity", 0) >= 0.25
        ]

        semantic_risk_score = int(min(max_sim * 100, 100))

        logger.info(
            f"Contextual similarity: max={max_sim:.3f} "
            f"matches={len(top_matches)}"
        )

        return {
            "max_similarity": round(max_sim, 3),
            "top_matches": top_matches,
            "semantic_risk_score": semantic_risk_score
        }

    except Exception as e:
        logger.error(f"Contextual similarity check failed: {e}")
        return {"max_similarity": 0.0, "top_matches": [], "semantic_risk_score": 0}
