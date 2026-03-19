"""
semantic_risk/__init__.py
Public entry point: assess_semantic_risk(message, url, url_signals) -> SemanticRiskReport
"""
import asyncio
from typing import Dict, Any

from app.services.semantic_risk.contextual_similarity import compute_contextual_similarity
from app.services.semantic_risk.template_matching import match_phishing_templates
from app.services.semantic_risk.intent_conflict_detector import detect_intent_conflict


async def assess_semantic_risk(
    message: str = "",
    url: str = "",
    url_signals: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run all semantic risk checks and return consolidated SemanticRiskReport.

    Returns semantic_risk_score (0-100).
    """
    url_signals = url_signals or {}

    similarity, templates, conflict = await asyncio.gather(
        asyncio.to_thread(compute_contextual_similarity, message, url),
        asyncio.to_thread(match_phishing_templates, message, url),
        asyncio.to_thread(detect_intent_conflict, message, url, url_signals)
    )

    # Composite semantic risk score
    sim_pts      = int(similarity.get("max_similarity", 0) * 50)        # max 50
    template_pts = int(templates.get("match_confidence", 0) * 30)       # max 30
    conflict_pts = int(conflict.get("mismatch_severity", 0) * 20)       # max 20
    semantic_risk_score = min(sim_pts + template_pts + conflict_pts, 100)

    return {
        "contextual_similarity": similarity,
        "template_matching": templates,
        "intent_conflict": conflict,
        "semantic_risk_score": semantic_risk_score
    }


__all__ = ["assess_semantic_risk"]
