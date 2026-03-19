"""
dynamic_domain/__init__.py
Exposes: analyze_domain_behavior(url, cached_html) -> DomainBehaviorReport
"""
import asyncio
from typing import Dict, Any, Optional

from app.services.dynamic_domain.dynamic_redirect_tracker import track_dynamic_redirects
from app.services.dynamic_domain.js_obfuscation_detector import detect_js_obfuscation
from app.services.dynamic_domain.content_mismatch_detector import detect_content_mismatch


async def analyze_domain_behavior(
    url: str,
    cached_html: str = "",
    claimed_brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run all dynamic domain checks concurrently.

    Args:
        url: Full URL to analyse
        cached_html: Pre-fetched HTML from url_report_builder (avoids double fetch)
        claimed_brand: Brand extracted from message (for mismatch check)

    Returns:
        Consolidated DomainBehaviorReport with domain_behavior_risk_score (0-100).
    """
    redirects, obfuscation, mismatch = await asyncio.gather(
        track_dynamic_redirects(url),
        asyncio.to_thread(detect_js_obfuscation, cached_html),
        asyncio.to_thread(detect_content_mismatch, cached_html, claimed_brand)
    )

    # Score
    redirect_pts    = 25 if redirects.get("cloaking_detected") else (10 if redirects.get("domain_changed") else 0)
    obfuscation_pts = int(obfuscation.get("obfuscation_score", 0) * 40)  # max 40
    mismatch_pts    = int(mismatch.get("mismatch_confidence", 0) * 35)   # max 35

    domain_behavior_risk_score = min(redirect_pts + obfuscation_pts + mismatch_pts, 100)

    return {
        "redirect_analysis": redirects,
        "js_obfuscation": obfuscation,
        "content_mismatch": mismatch,
        "domain_behavior_risk_score": domain_behavior_risk_score
    }


__all__ = ["analyze_domain_behavior"]
