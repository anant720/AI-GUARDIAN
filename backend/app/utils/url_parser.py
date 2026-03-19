import re
import tldextract
from urllib.parse import urlparse
from typing import Dict, Any

# Suspicious TLDs frequently used in phishing
SUSPICIOUS_TLDS = {
    "xyz", "top", "live", "gq", "tk", "ml", "cf", "icu", "click", "loan", "men", "date"
}

def parse_url_structure(url: str) -> dict:
    """Extract structural signals from the URL."""
    if not url:
        return {}
    try:
        parsed = urlparse(url)
        extracted = tldextract.extract(url)
        
        # Calculate signals
        subdomains = extracted.subdomain.split(".") if extracted.subdomain else []
        subdomain_count = len(subdomains)
        hyphen_count = url.count("-")
        numeric_count = len(re.findall(r"\d", url))
        
        return {
            "protocol": parsed.scheme,
            "subdomain": extracted.subdomain,
            "domain": extracted.domain,
            "tld": extracted.suffix,
            "path": parsed.path,
            "url_length": len(url),
            "subdomain_count": subdomain_count,
            "hyphen_count": hyphen_count,
            "numeric_count": numeric_count,
            "is_suspicious_tld": extracted.suffix in SUSPICIOUS_TLDS
        }
    except Exception:
        return {}
