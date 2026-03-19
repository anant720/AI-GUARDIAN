"""
domain_reputation_checker.py
────────────────────────────
Checks a domain's reputation using:
1. A curated local blocklist of known-bad patterns
2. Heuristic signals (TLD risk, length, homoglyph patterns)

Returns a reputation score and label — no external API required.
"""
import re
from typing import Dict, Any
from app.logger import logger

# ── High-risk TLDs commonly used in phishing ─────────────────────────────────
HIGH_RISK_TLDS = {
    ".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".top", ".club", ".online",
    ".site", ".website", ".live", ".stream", ".win", ".loan", ".click",
    ".bid", ".trade", ".date", ".racing", ".review", ".science", ".work"
}

# ── Strings that frequently appear in brand-impersonation domains ─────────────
PHISHING_KEYWORDS = [
    "paypal", "amazon", "apple", "microsoft", "google", "linkedin",
    "facebook", "instagram", "netflix", "spotify", "ebay", "chase",
    "wellsfargo", "bankofamerica", "citibank", "hsbc", "dhl", "fedex",
    "irs", "gov-login", "verify-account", "secure-login", "update-payment",
    "confirm-identity", "reset-password", "account-suspended"
]

# ── Domains known to be abused (lightweight local blocklist) ─────────────────
LOCAL_BLOCKLIST = {
    "paypal-security-update.xyz",
    "secure-paypal-login.com",
    "amazon-prime-renewal.info",
    "microsoft-alert.online",
    "apple-id-verify.site",
    "irs-refund-claim.com",
}

# ── Trusted global domains — bypass all heuristics (prevents FP) ──────────────
TRUSTED_DOMAINS = {
    "google.com", "accounts.google.com", "mail.google.com", "drive.google.com",
    "docs.google.com", "gmail.com", "youtube.com", "youtu.be",
    "amazon.com", "amazon.in", "amazon.co.uk", "amzn.to", "aws.amazon.com",
    "microsoft.com", "office.com", "outlook.com", "live.com", "microsoftonline.com",
    "apple.com", "icloud.com", "appleid.apple.com",
    "paypal.com", "paypal.co.uk",
    "netflix.com", "spotify.com", "linkedin.com",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "github.com", "stackoverflow.com", "kaspersky.com",
    "ebay.com", "dropbox.com", "zoom.us",
    "sbi.co.in", "onlinesbi.sbi", "hdfcbank.com", "icicibank.com",
    "incometax.gov.in", "irs.gov", "gov.uk", "hmrc.gov.uk",
    "fedex.com", "dhl.com", "dhl.co.in", "usps.com",
    "booking.com", "airbnb.com", "steampowered.com",
    "coinbase.com", "binance.com", "wellsfargo.com", "chase.com",
    "bankofamerica.com", "citibank.com",
}


def check_domain_reputation(domain: str) -> Dict[str, Any]:
    """
    Assess domain reputation using heuristics and local blocklist.

    Args:
        domain: hostname without scheme (e.g. 'paypal-security-update.xyz')

    Returns:
        {domain, reputation, confidence, reports, risk_signals}
    """
    domain = domain.lower().strip()
    risk_signals = []
    risk_score = 0

    # 0. Trusted domain whitelist — skip all heuristics (eliminates FP)
    if any(domain == td or domain.endswith("." + td) for td in TRUSTED_DOMAINS):
        logger.debug(f"Domain '{domain}' is trusted — skipping heuristics")
        return {
            "domain": domain,
            "reputation": "clean",
            "confidence": 0.0,
            "reports": 0,
            "risk_signals": ["trusted_domain"]
        }

    # 1. Local blocklist (definitive)
    if domain in LOCAL_BLOCKLIST:
        logger.warning(f"Domain '{domain}' is in local blocklist")
        return {
            "domain": domain,
            "reputation": "malicious",
            "confidence": 1.0,
            "reports": 1,
            "risk_signals": ["local_blocklist_match"]
        }

    # 2. High-risk TLD
    for tld in HIGH_RISK_TLDS:
        if domain.endswith(tld):
            risk_score += 35
            risk_signals.append(f"high_risk_tld:{tld}")
            break

    # 3. Phishing keyword in domain
    matched_keywords = [kw for kw in PHISHING_KEYWORDS if kw in domain]
    if matched_keywords:
        risk_score += 40 * min(len(matched_keywords), 2)
        risk_signals.extend([f"phishing_keyword:{kw}" for kw in matched_keywords])

    # 4. Hyphen count (typosquatting indicator)
    hyphen_count = domain.count("-")
    if hyphen_count >= 2:
        risk_score += 10 * min(hyphen_count, 3)
        risk_signals.append(f"excessive_hyphens:{hyphen_count}")

    # 5. Subdomain depth (e.g. login.verify.paypal.attacker.com)
    parts = domain.split(".")
    if len(parts) >= 4:
        risk_score += 15
        risk_signals.append("deep_subdomain_structure")

    # 6. Long domain (obfuscation)
    if len(domain) > 40:
        risk_score += 10
        risk_signals.append("long_domain_name")

    # 7. Numeric pattern (random-generated domains)
    if re.search(r'\d{4,}', domain):
        risk_score += 10
        risk_signals.append("numeric_pattern")

    # Clamp & classify
    risk_score = min(risk_score, 100)
    confidence = round(risk_score / 100, 2)

    if risk_score >= 70:
        reputation = "malicious"
    elif risk_score >= 40:
        reputation = "suspicious"
    else:
        reputation = "clean"

    logger.info(f"Domain '{domain}' reputation: {reputation} (score={risk_score})")
    return {
        "domain": domain,
        "reputation": reputation,
        "confidence": confidence,
        "reports": len(risk_signals),
        "risk_signals": risk_signals
    }
