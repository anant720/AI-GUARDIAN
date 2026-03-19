"""
domain_age_analyzer.py
───────────────────────
Determines how old a domain is using WHOIS data.

Why this matters:
  Phishing domains are typically registered days before use and
  discarded quickly. Very new domains (< 30 days) are a strong
  signal of malicious intent.

Uses python-whois (already installed). Falls back to a neutral
result if WHOIS lookup fails or returns no creation date.
"""
import whois
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.logger import logger


def _parse_creation_date(raw) -> Optional[datetime]:
    """Handle various WHOIS date formats (single date or list)."""
    if raw is None:
        return None
    if isinstance(raw, list):
        raw = raw[0]
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw))
    except Exception:
        return None


def _classify_age(days: int) -> str:
    if days < 0:
        return "unknown"
    if days < 7:
        return "extremely_new_domain"
    if days < 30:
        return "very_new_domain"
    if days < 90:
        return "new_domain"
    if days < 365:
        return "young_domain"
    if days < 1825:   # 5 years
        return "established_domain"
    return "mature_domain"


def analyze_domain_age(domain: str) -> Dict[str, Any]:
    """
    Look up domain creation date via WHOIS and classify its age.

    Args:
        domain: e.g. 'paypal-security-update.xyz'

    Returns:
        {domain_age_days, risk_flag, registrar, creation_date}
    """
    try:
        w = whois.whois(domain)
        creation_date = _parse_creation_date(w.creation_date)
        registrar = getattr(w, "registrar", None) or "unknown"

        if creation_date is None:
            logger.warning(f"WHOIS returned no creation date for '{domain}'")
            return {
                "domain_age_days": None,
                "risk_flag": "whois_no_date",
                "registrar": str(registrar),
                "creation_date": None
            }

        # Ensure timezone-aware
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_days = (now - creation_date).days

        risk_flag = _classify_age(age_days)
        logger.info(f"Domain '{domain}' age: {age_days} days ({risk_flag})")

        return {
            "domain_age_days": age_days,
            "risk_flag": risk_flag,
            "registrar": str(registrar)[:100],
            "creation_date": creation_date.strftime("%Y-%m-%d")
        }

    except Exception as e:
        logger.warning(f"WHOIS lookup failed for '{domain}': {type(e).__name__}: {e}")
        return {
            "domain_age_days": None,
            "risk_flag": "whois_failed",
            "registrar": "unknown",
            "creation_date": None
        }
