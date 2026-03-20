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

# ── Generic Authority Keywords ───────────────────────────────────────────────
_AUTHORITY_KEYWORDS = {
    "government": ["gov", "gov.in", "gov.uk", "mil"],
    "police":     ["gov", "police.uk", "police.in"],
    "income tax": ["incometax.gov.in", "irs.gov"],
    "rbi":        ["rbi.org.in"],
    "bank":       ["trusted-bank-list"], # We use this as a flag for high-scrutiny
    "court":      ["gov", "judiciary.uk", "sci.gov.in"],
    "official notice": ["gov", "org"],
}

_AUTHORITY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _AUTHORITY_KEYWORDS.keys()) + r")\b",
    re.IGNORECASE
)

_BRAND_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(b) for b in _BRAND_DOMAINS.keys()) + r")\b",
    re.IGNORECASE
)


def _extract_potential_entities(text: str) -> List[str]:
    """Finds potential service names or brands using fuzzy extraction (Capitalized words)."""
    # Look for capitalized words of length 3-15 that aren't common sentence starters
    # This is a heuristic for "Brand-like" strings
    potential = re.findall(r"\b([A-Z][a-z]{2,15})\b", text)
    # Filter out common non-brand capitalized words if needed, but for phish detection, 
    # we'd rather over-extract and then check if they appear in the domain.
    return list(set(p.lower() for p in potential))


def _detect_structural_deception(entities: List[str], actual_domain: str) -> Optional[Dict[str, Any]]:
    """Detects 'Keyword Stuffing' where a brand/entity name appears in a foreign domain."""
    if not entities or not actual_domain:
        return None

    # Common TLDs/Suffixes to ignore for root matching
    root_domain = actual_domain.split(".")[-2] if "." in actual_domain else actual_domain
    
    for entity in entities:
        # Ignore extremely common words
        if entity in ["the", "your", "this", "from", "with"]:
            continue
            
        # Is the entity name inside the domain/subdomain?
        # e.g. entity='meta', domain='meta-support.io' -> matches
        if entity in actual_domain.replace("-", "").replace(".", ""):
            # But is it the OFFICIAL domain? 
            # We check if the root domain IS the entity
            if root_domain != entity:
                # Structural deception detected: Brand used in a domain it doesn't own
                return {
                    "conflict_detected": True,
                    "claimed_brand": entity,
                    "mismatch_severity": 0.9,
                    "conflict_reason": f"System detected the keyword '{entity.upper()}' used in a deceptive domain structure '{actual_domain}'"
                }
    return None


def _detect_generic_authority_conflict(message: str, actual_domain: str) -> Optional[Dict[str, Any]]:
    """Detects if a message claims general authority but links to a non-government/official domain."""
    message_lower = message.lower()
    matches = _AUTHORITY_PATTERN.findall(message_lower)
    
    if not matches or not actual_domain:
        return None

    # Check if the domain is a known official TLD or in our allowed list
    is_gov_tld = any(actual_domain.endswith(f".{tld}") for tld in ["gov", "gov.in", "gov.uk", "mil", "nic.in"])
    
    # If the message claims "Government" or "Police" but isn't on a .gov domain
    for match in set(matches):
        m_str = str(match)
        # We don't want too many false positives, so we focus on high-risk generic claims
        if m_str in ["government", "income tax", "rbi", "court", "police"]:
            if not is_gov_tld:
                # Potential impersonation of an entire institution
                return {
                    "conflict_detected": True,
                    "claimed_brand": m_str,
                    "mismatch_severity": 1.0, # High severity for gov impersonation
                    "conflict_reason": f"Message claims official {m_str.upper()} authority but links to a non-government domain '{actual_domain}'"
                }

    return None


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
    url_signals: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detect brand-intent mismatch between message and URL.
    Includes Universal Authority Verification and Structural Deception.
    """
    url_signals = url_signals or {}

    result: Dict[str, Any] = {
        "conflict_detected": False,
        "claimed_brands": [],
        "actual_domain": None,
        "mismatch_severity": 0.0,
        "conflict_reason": None,
    }

    actual_domain = _get_url_domain(url)
    result["actual_domain"] = actual_domain

    if not actual_domain:
        return result

    # 1. Start with Universal Authority Verification (Heuristic)
    auth_conflict = _detect_generic_authority_conflict(message, actual_domain)
    if auth_conflict:
        result.update(auth_conflict)
        result["claimed_brands"] = [auth_conflict["claimed_brand"]]
        return result

    # 2. Universal Structural Deception (Zero-Whitelist protection)
    # Extracts ANY capitalized potential entities (Meta, Amazon, Steam, etc.)
    potential_entities = _extract_potential_entities(message)
    structural_conflict = _detect_structural_deception(potential_entities, actual_domain)
    if structural_conflict:
        result.update(structural_conflict)
        result["claimed_brands"] = potential_entities
        return result

    # 3. Traditional Brand Mismatch (Dictionary-based fallback)
    claimed_brands = _extract_brands(message)

    # Also check brand_impersonation hint from url_report
    url_brand = url_signals.get("brand_impersonation")
    if url_brand and url_brand not in claimed_brands:
        claimed_brands.append(url_brand.lower())

    result["claimed_brands"] = claimed_brands

    if not claimed_brands:
        return result 

    # Check each claimed brand vs actual domain
    for brand in claimed_brands:
        official_domains = _BRAND_DOMAINS.get(brand, [])
        if not official_domains:
            continue

        is_official = any(
            actual_domain == od or actual_domain.endswith("." + od)
            for od in official_domains
        )

        if not is_official:
            brand_in_domain = brand.replace(" ", "") in actual_domain.replace("-", "")
            severity = 0.95 if not brand_in_domain else 0.7

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
            break 

    return result
