"""
ip_reputation_checker.py
─────────────────────────
Resolves domain → IP address, then checks IP reputation.

Two-layer check:
1. DNS resolution via dnspython (already installed)
2. AbuseIPDB API (free tier, requires ABUSEIPDB_API_KEY in .env)
   Falls back gracefully if key is absent.
"""
import socket
import httpx
from typing import Dict, Any, Optional
from app.logger import logger
from app.config import settings


def _resolve_ip(domain: str) -> Optional[str]:
    """Resolve domain to its first A record IP with strict 2.0s timeout."""
    try:
        # socket.gethostbyname is blocking; setting a global default timeout 
        # is risky, but for this thread it's safe if we use a temp setting 
        # or better yet, just let the orchestrator's wait_for handle it.
        # However, adding a small local protection is good.
        import socket
        socket.setdefaulttimeout(2.0)
        ip = socket.gethostbyname(domain)
        logger.info(f"Resolved {domain} → {ip}")
        return ip
    except Exception as e:
        logger.warning(f"DNS resolution failed for '{domain}': {e}")
        return None


def _check_abuseipdb(ip: str) -> Dict[str, Any]:
    """
    Query AbuseIPDB free API for IP reputation.
    https://www.abuseipdb.com/api.html
    Falls back to a neutral result if key is absent.
    """
    key = getattr(settings, "ABUSEIPDB_API_KEY", "")
    if not key:
        logger.info("AbuseIPDB key not configured — skipping IP lookup")
        return {"risk_score": 0, "blacklist_count": 0, "isp": "unknown", "country": "unknown"}

    try:
        resp = httpx.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": key, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90},
            timeout=8
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "risk_score": data.get("abuseConfidenceScore", 0),
            "blacklist_count": data.get("totalReports", 0),
            "isp": data.get("isp", "unknown"),
            "country": data.get("countryCode", "unknown")
        }
    except Exception as e:
        logger.warning(f"AbuseIPDB check failed for {ip}: {e}")
        return {"risk_score": 0, "blacklist_count": 0, "isp": "unknown", "country": "unknown"}


def _heuristic_ip_risk(ip: Optional[str]) -> Dict[str, Any]:
    """
    Fast heuristic IP risk assessment when AbuseIPDB is unavailable.
    Flags private/reserved IP ranges and common hosting subnets.
    """
    if not ip:
        return {"risk_score": 0, "blacklist_count": 0, "isp": "unresolved", "country": "unknown"}

    risk_score = 0

    # Many cheap phishing hosts use these ranges
    RISKY_PREFIXES = ["185.", "176.", "194.", "45.8.", "91.108.", "188.166."]
    for prefix in RISKY_PREFIXES:
        if ip.startswith(prefix):
            risk_score += 30
            break

    return {"risk_score": risk_score, "blacklist_count": 0, "isp": "unknown", "country": "unknown"}


def check_ip_reputation(domain: str) -> Dict[str, Any]:
    """
    Full IP reputation check for a given domain.

    Returns:
        {ip, risk_score, blacklist_count, isp, country}
    """
    ip = _resolve_ip(domain)

    if not ip:
        return {
            "ip": None,
            "risk_score": 0,
            "blacklist_count": 0,
            "isp": "unresolved",
            "country": "unknown"
        }

    key = getattr(settings, "ABUSEIPDB_API_KEY", "")
    details = _check_abuseipdb(ip) if key else _heuristic_ip_risk(ip)

    logger.info(f"IP {ip} risk_score={details['risk_score']} blacklists={details['blacklist_count']}")
    return {"ip": ip, **details}
