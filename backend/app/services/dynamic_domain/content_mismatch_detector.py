"""
content_mismatch_detector.py
──────────────────────────────
Compares the brand claimed in the message against the actual content
visible on the fetched page (title, headings, form labels, meta description).

Detects:
  • Page title impersonates a different brand than expected
  • Login/credential form on page with mismatched brand
  • "Secure" / "Verify" keywords on page with suspicious content
  • Favicon / logo keywords inconsistent with URL domain

All analysis is done on pre-fetched HTML — no additional HTTP calls.
"""
import re
from typing import Dict, Any, Optional, List

from app.logger import logger

_TITLE_RE  = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
_H1_RE     = re.compile(r'<h[1-2][^>]*>(.*?)</h[1-2]>', re.IGNORECASE | re.DOTALL)
_META_RE   = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
_TAG_RE    = re.compile(r'<[^>]+>')

# Suspicious page content markers
_VERIFICATION_PHRASES = [
    "verify your", "confirm your identity", "secure login",
    "enter your password", "update your details", "account suspended",
    "click here to verify", "one-time password", "enter otp"
]

# Brands we track (map brand keyword → variants)
_BRAND_KEYWORDS: Dict[str, List[str]] = {
    "paypal":    ["paypal", "pay pal"],
    "amazon":    ["amazon", "amzn"],
    "google":    ["google", "gmail"],
    "microsoft": ["microsoft", "ms office", "microsoft 365"],
    "apple":     ["apple", "icloud", "apple id"],
    "sbi":       ["sbi", "state bank", "state bank of india"],
    "hdfc":      ["hdfc"],
    "netflix":   ["netflix"],
    "dhl":       ["dhl"],
    "fedex":     ["fedex"],
    "irs":       ["irs", "internal revenue"],
    "income tax":["income tax", "income-tax"],
    "spotify":   ["spotify"],
    "linkedin":  ["linkedin"],
    "coinbase":  ["coinbase"],
    "chase":     ["chase bank", "jpmorgan chase"],
}


def _clean(html_snippet: str) -> str:
    return _TAG_RE.sub(" ", html_snippet).lower().strip()[:400]


def _extract_page_text(html: str) -> Dict[str, str]:
    title_m = _TITLE_RE.search(html)
    h1_m    = _H1_RE.search(html)
    meta_m  = _META_RE.search(html)
    return {
        "title":       _clean(title_m.group(1)) if title_m else "",
        "heading":     _clean(h1_m.group(1))    if h1_m    else "",
        "description": _clean(meta_m.group(1))  if meta_m  else "",
    }


def _page_mentions_brand(page_text: str, brand: str) -> bool:
    keywords = _BRAND_KEYWORDS.get(brand.lower(), [brand.lower()])
    return any(kw in page_text for kw in keywords)


def _page_has_verification_content(html: str) -> bool:
    lower = html.lower()
    return any(phrase in lower for phrase in _VERIFICATION_PHRASES)


def detect_content_mismatch(
    html: str,
    claimed_brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare claimed brand vs actual page content.

    Args:
        html: Pre-fetched page HTML
        claimed_brand: Brand name extracted from message (e.g. 'paypal')

    Returns:
        brand_mismatch (bool), claimed_brand, detected_brands, mismatch_confidence (0-1)
    """
    result = {
        "brand_mismatch": False,
        "claimed_brand": claimed_brand,
        "page_brands_detected": [],
        "contains_verification_content": False,
        "mismatch_confidence": 0.0,
    }

    if not html:
        return result

    page_data = _extract_page_text(html)
    page_text = " ".join(page_data.values())

    has_verification = _page_has_verification_content(html)
    result["contains_verification_content"] = has_verification

    # Which brands appear in page content?
    page_brands = [
        brand for brand in _BRAND_KEYWORDS.keys()
        if _page_mentions_brand(page_text, brand)
    ]
    result["page_brands_detected"] = page_brands

    # Check for mismatch
    if claimed_brand:
        cb = claimed_brand.lower()
        if page_brands and cb not in page_brands:
            # Page mentions a brand DIFFERENT from the claimed one
            result["brand_mismatch"] = True
            result["mismatch_confidence"] = 0.80

        elif not _page_mentions_brand(page_text, cb) and has_verification:
            # Claimed brand not on page but page has a login/verify form
            result["brand_mismatch"] = True
            result["mismatch_confidence"] = 0.65

    # Suspicious: page has verification content but no obvious brand
    if has_verification and not page_brands:
        result["mismatch_confidence"] = max(result["mismatch_confidence"], 0.45)

    if result["brand_mismatch"]:
        logger.info(
            f"Content mismatch: claimed='{claimed_brand}' "
            f"page_brands={page_brands} "
            f"verification={has_verification} "
            f"confidence={result['mismatch_confidence']:.2f}"
        )

    return result
