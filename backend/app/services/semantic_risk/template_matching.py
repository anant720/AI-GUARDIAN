"""
template_matching.py
─────────────────────
Matches message text and URL against known phishing template indicator phrases.

Uses n-gram keyword scanning against indicator lists from phishing_knowledge.json.
Lightweight, zero-latency — runs before any API call for early detection.
"""
import os
import json
import re
from typing import Dict, Any, List, Optional

from app.logger import logger

_KNOWLEDGE_PATH = os.path.join("data", "phishing_knowledge.json")

# Cache loaded at module level to avoid repeated file reads
_TEMPLATE_CACHE: Optional[List[Dict]] = None


def _load_templates() -> List[Dict]:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is not None:
        return _TEMPLATE_CACHE

    try:
        if os.path.exists(_KNOWLEDGE_PATH):
            with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
                _TEMPLATE_CACHE = json.load(f)
            logger.debug(f"Loaded {len(_TEMPLATE_CACHE)} phishing templates for matching")
        else:
            _TEMPLATE_CACHE = []
    except Exception as e:
        logger.error(f"Failed to load phishing templates: {e}")
        _TEMPLATE_CACHE = []

    return _TEMPLATE_CACHE


def _count_indicator_hits(text: str, indicators: List[str]) -> int:
    """Count how many indicator phrases appear in text."""
    count = 0
    for ind in indicators:
        if ind.lower() in text:
            count += 1
    return count


def match_phishing_templates(
    message: str = "",
    url: str = ""
) -> Dict[str, Any]:
    """
    Match message+URL against all known phishing template indicators.

    Returns:
        template_matched (bool), matched_template (dict), match_confidence (0-1)
    """
    combined = f"{message.lower()} {url.lower()}"
    templates = _load_templates()

    if not templates or not combined.strip():
        return {
            "template_matched": False,
            "matched_template": None,
            "match_confidence": 0.0,
            "matched_indicators": []
        }

    best_match = None
    best_score = 0
    best_indicators = []

    for template in templates:
        indicators = template.get("indicators", [])
        if not indicators:
            continue

        hits = _count_indicator_hits(combined, indicators)
        score = hits / len(indicators)  # ratio of indicators matched

        if score > best_score:
            best_score = score
            best_match = template
            # Collect matched indicators
            best_indicators = [i for i in indicators if i.lower() in combined]

    # Threshold: at least 2 indicators or ≥30% match ratio
    template_matched = best_score >= 0.30 or (best_match and len(best_indicators) >= 2)
    match_confidence = round(min(best_score, 1.0), 3)

    if template_matched and best_match:
        logger.info(
            f"Template matched: '{best_match.get('title')}' "
            f"confidence={match_confidence:.2f} indicators={best_indicators[:3]}"
        )

    return {
        "template_matched": template_matched,
        "matched_template": {
            "title": best_match.get("title") if best_match else None,
            "brand": best_match.get("brand") if best_match else None,
            "threat_type": best_match.get("threat_type") if best_match else None,
        } if template_matched else None,
        "match_confidence": match_confidence,
        "matched_indicators": best_indicators[:5]
    }
