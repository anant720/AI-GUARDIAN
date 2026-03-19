"""
threat_report_builder.py
─────────────────────────
Top-level async orchestrator for the Threat Intelligence Engine.

Extracts domain from URL → calls aggregator → returns ThreatIntelligenceReport.
Always returns a safe dict even if all checks fail.
"""
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from app.logger import logger
from app.services.threat_intelligence.threat_feed_aggregator import aggregate_threat_intelligence

_FALLBACK_REPORT: Dict[str, Any] = {
    "domain_reputation": "unknown",
    "domain_confidence": 0.0,
    "domain_risk_signals": [],
    "ip": None,
    "ip_risk_score": 0,
    "ip_blacklist_count": 0,
    "ip_country": "unknown",
    "phishing_match": False,
    "phishing_database": "unavailable",
    "phishing_confidence": 0.0,
    "malware_detected": False,
    "malware_type": None,
    "malware_indicators": [],
    "domain_age_days": None,
    "domain_age_flag": "unknown",
    "registrar": "unknown",
    "threat_score": 0
}


def _extract_domain(url: str) -> Optional[str]:
    """Extract hostname from URL."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Strip 'www.' prefix for cleaner WHOIS/reputation lookups
        if host.startswith("www."):
            host = host[4:]
        return host if host else None
    except Exception:
        return None


async def build_threat_report(url: str) -> Dict[str, Any]:
    """
    Build a full ThreatIntelligenceReport for the given URL.

    Args:
        url: Full URL string (e.g. 'https://paypal-security-update.xyz/login')

    Returns:
        Dict with all threat intelligence signals and a composite threat_score.
    """
    domain = _extract_domain(url)

    if not domain:
        logger.warning(f"Could not extract domain from URL: {url}")
        return dict(_FALLBACK_REPORT)

    try:
        report = await aggregate_threat_intelligence(url, domain)
        return report
    except Exception as e:
        logger.error(f"Threat intelligence engine error: {e}")
        return dict(_FALLBACK_REPORT)
