"""
intent_conflict_detector.py
────────────────────────────
Detects mismatch between the claimed intent/brand in a message
and the actual domain in the URL.

Example conflict:
  Message: "Your Amazon order has been delayed..."
  URL:     https://amaz0n-order-confirm.xyz/track
  → CONFLICT: Amazon claimed, foreign domain detected

Uses brand extraction + domain comparison logic.
No external APIs — fully local.
"""
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from app.logger import logger

# ── Known brand ↔ official domain mappings ─────────────────────────────────────
_BRAND_DOMAINS: Dict[str, List[str]] = {
    "paypal":       ["paypal.com", "paypal.co.uk", "paypal.in"],
    "amazon":       ["amazon.com", "amazon.in", "amazon.co.uk", "amzn.to"],
    "google":       ["google.com", "google.co.in", "accounts.google.com", "docs.google.com", "gmail.com"],
    "microsoft":    ["microsoft.com", "office.com", "outlook.com", "microsoftonline.com", "live.com"],
    "apple":        ["apple.com", "icloud.com", "appleid.apple.com"],
    "netflix":      ["netflix.com"],
    "sbi":          ["sbi.co.in", "onlinesbi.sbi", "sbicards.com"],
    "hdfc":         ["hdfcbank.com"],
    "icici":        ["icicibank.com"],
    "dhl":          ["dhl.com", "dhl.co.in", "dhl.de"],
    "fedex":        ["fedex.com"],
    "usps":         ["usps.com"],
    "irs":          ["irs.gov"],
    "hmrc":         ["hmrc.gov.uk", "gov.uk"],
    "income tax":   ["incometax.gov.in", "incometaxindiaefiling.gov.in"],
    "spotify":      ["spotify.com"],
    "instagram":    ["instagram.com"],
    "facebook":     ["facebook.com", "fb.com"],
    "twitter":      ["twitter.com", "x.com"],
    "linkedin":     ["linkedin.com"],
    "coinbase":     ["coinbase.com"],
    "binance":      ["binance.com"],
    "wellsfargo":   ["wellsfargo.com"],
    "chase":        ["chase.com"],
    "bankofamerica":["bankofamerica.com", "bac.com"],
    "kaspersky":    ["kaspersky.com"],
    "youtube":      ["youtube.com", "youtu.be"],
    "dropbox":      ["dropbox.com"],
    "docusign":     ["docusign.com"],
    "adobe":        ["adobe.com", "adobesign.com"],
    "zoom":         ["zoom.us"],
    "airbnb":       ["airbnb.com"],
    "booking":      ["booking.com"],
    "steam":        ["steampowered.com", "store.steampowered.com"],
}

_BRAND_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(b) for b in _BRAND_DOMAINS.keys()) + r")\b",
    re.IGNORECASE
)


def _extract_brands(text: str) -> List[str]:
    """Extract brand names mentioned in text."""
    return [m.lower() for m in set(_BRAND_PATTERN.findall(text))]


def _get_url_domain(url: str) -> Optional[str]:
    try:
        host = urlparse(url).hostname or ""
        # Strip www.
        return host.lstrip("www.").lower()
    except Exception:
        return None


def detect_intent_conflict(
    message: str = "",
    url: str = "",
    url_signals: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Detect brand-intent mismatch between message and URL.

    Args:
        message: Raw message text
        url: Scanned URL
        url_signals: Optional url_report signals dict (for brand_impersonation hint)

    Returns:
        Dict with conflict_detected, claimed_brand, actual_domain, mismatch_severity (0-1)
    """
    url_signals = url_signals or {}

    result = {
        "conflict_detected": False,
        "claimed_brands": [],
        "actual_domain": None,
        "mismatch_severity": 0.0,
        "conflict_reason": None,
    }

    # Extract brands from message
    claimed_brands = _extract_brands(message)

    # Also check brand_impersonation hint from url_report
    url_brand = url_signals.get("brand_impersonation")
    if url_brand and url_brand not in claimed_brands:
        claimed_brands.append(url_brand.lower())

    result["claimed_brands"] = claimed_brands

    if not claimed_brands:
        return result  # no brand → no conflict possible

    actual_domain = _get_url_domain(url)
    result["actual_domain"] = actual_domain

    if not actual_domain:
        return result

    # Check each claimed brand vs actual domain
    for brand in claimed_brands:
        official_domains = _BRAND_DOMAINS.get(brand, [])
        if not official_domains:
            continue

        # Is the URL on an official domain?
        is_official = any(
            actual_domain == od or actual_domain.endswith("." + od)
            for od in official_domains
        )

        if not is_official:
            # Conflict: brand mentioned but domain is foreign
            # Check if the brand keyword appears in the domain (keyword stuffing)
            brand_in_domain = brand.replace(" ", "") in actual_domain.replace("-", "")

            severity = 0.9 if not brand_in_domain else 0.6
            # Lower severity if brand is in domain (could be a legit subdomain)

            result["conflict_detected"] = True
            result["mismatch_severity"] = max(result["mismatch_severity"], severity)
            result["conflict_reason"] = (
                f"Message claims '{brand}' but domain '{actual_domain}' "
                f"is not an official {brand.title()} domain"
            )

            logger.info(
                f"Intent conflict: brand='{brand}' domain='{actual_domain}' "
                f"severity={severity:.1f}"
            )
            break  # Report first conflict found

    return result
