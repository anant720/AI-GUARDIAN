"""
phishing_database_checker.py
─────────────────────────────
Checks URLs and domains against PhishTank's public verified phishing feed.

Strategy:
1. Download PhishTank CSV feed and cache it locally (refreshed every 24h).
2. Normalise submitted URL and domain, check against cached set.
3. Falls back to a heuristics-based check if feed is unavailable.

PhishTank public feed: http://data.phishtank.com/data/online-valid.json
(Free for non-commercial use, no account required for basic access)
"""
import os
import json
import time
import hashlib
import httpx
from typing import Dict, Any, Set, Optional
from app.logger import logger
from app.config import settings

# ── Feed config ───────────────────────────────────────────────────────────────
_PHISHTANK_URL = "http://data.phishtank.com/data/online-valid.json"
_CACHE_PATH = os.path.join(
    getattr(settings, "DATA_DIR", "data"), "phishtank_cache.json"
)
_CACHE_TTL_SECONDS = 86400  # 24 hours

# Runtime in-memory set for O(1) lookups
_phish_url_set: Set[str] = set()
_phish_domain_set: Set[str] = set()
_cache_loaded = False


def _load_phishtank_cache() -> None:
    """Load the cached PhishTank feed into memory."""
    global _phish_url_set, _phish_domain_set, _cache_loaded

    if not os.path.exists(_CACHE_PATH):
        logger.info("PhishTank cache not found — will use heuristics")
        return

    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        urls: list = data.get("urls", [])
        domains: list = data.get("domains", [])
        _phish_url_set = set(urls)
        _phish_domain_set = set(domains)
        _cache_loaded = True
        logger.info(f"PhishTank cache loaded: {len(_phish_url_set)} URLs, {len(_phish_domain_set)} domains")
    except Exception as e:
        logger.warning(f"Failed to load PhishTank cache: {e}")


def _refresh_phishtank_feed() -> None:
    """Download and cache the PhishTank feed."""
    global _phish_url_set, _phish_domain_set, _cache_loaded

    # Check if cache is still fresh
    if os.path.exists(_CACHE_PATH):
        mtime = os.path.getmtime(_CACHE_PATH)
        if time.time() - mtime < _CACHE_TTL_SECONDS:
            return  # Cache is fresh

    logger.info("Refreshing PhishTank feed...")
    try:
        resp = httpx.get(_PHISHTANK_URL, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        entries = resp.json()

        urls = []
        domains = set()
        for entry in entries:
            url = entry.get("url", "").lower().strip()
            if url:
                urls.append(url)
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).hostname or ""
                    if domain:
                        domains.add(domain)
                except Exception:
                    pass

        # Save cache
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"urls": urls, "domains": list(domains), "updated": time.time()}, f)

        _phish_url_set = set(urls)
        _phish_domain_set = domains
        _cache_loaded = True
        logger.info(f"PhishTank feed refreshed: {len(urls)} URLs")
    except Exception as e:
        logger.warning(f"PhishTank feed refresh failed: {e}")


# Load cache at import time (non-blocking if file missing)
_load_phishtank_cache()


def _heuristic_phishing_check(url: str, domain: str) -> Dict[str, Any]:
    """Pattern-based phishing detection when feed is unavailable."""
    PHISHING_PATTERNS = [
        "paypal-security", "secure-paypal", "amazon-prime-renew",
        "apple-id-verify", "microsoft-alert", "irs-refund",
        "account-suspended", "login-verify", "update-payment-info",
        "confirm-your-account", "reset-password-now"
    ]
    url_lower = url.lower()
    for pattern in PHISHING_PATTERNS:
        if pattern in url_lower:
            return {
                "phishing_match": True,
                "database": "heuristic",
                "confidence": 0.75,
                "matched_pattern": pattern
            }
    return {"phishing_match": False, "database": "heuristic", "confidence": 0.0}


def check_phishing_database(url: str, domain: str) -> Dict[str, Any]:
    """
    Check URL/domain against PhishTank feed and local heuristics.

    Returns:
        {phishing_match, database, confidence}
    """
    url_lower = url.lower().strip()
    domain_lower = domain.lower().strip()

    if not _cache_loaded:
        result = _heuristic_phishing_check(url_lower, domain_lower)
        logger.info(f"PhishTank cache absent — heuristic result: {result['phishing_match']}")
        return result

    if url_lower in _phish_url_set:
        logger.warning(f"URL '{url}' found in PhishTank feed")
        return {"phishing_match": True, "database": "phishtank", "confidence": 0.99}

    if domain_lower in _phish_domain_set:
        logger.warning(f"Domain '{domain}' found in PhishTank domain set")
        return {"phishing_match": True, "database": "phishtank_domain", "confidence": 0.90}

    heuristic = _heuristic_phishing_check(url_lower, domain_lower)
    if heuristic["phishing_match"]:
        return heuristic

    logger.info(f"URL '{url[:60]}' not found in phishing databases")
    return {"phishing_match": False, "database": "phishtank", "confidence": 0.0}
