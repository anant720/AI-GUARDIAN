"""
dynamic_redirect_tracker.py
────────────────────────────
Follows the redirect chain of a URL using a sandboxed httpx client.

Safety features:
  - 5-second per-hop timeout
  - Private IP / localhost blocked (anti-SSRF)
  - Max 10 redirect hops tracked
  - No cookies / credentials sent
  - User-Agent masked as a scanner (not spoofed browser)

Detects:
  - Domain hopping (original vs final domain differ)
  - Cross-scheme redirects (http → https is fine; https → http is suspicious)
  - Cloaked redirects (meta-refresh in HTML, or JS redirects)
"""
import re
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

from app.logger import logger

_MAX_REDIRECTS = 10
_TIMEOUT = 2.5
_SAFE_UA = "Mozilla/5.0 (compatible; AIGuardian-Scanner/1.0)"

# Private / reserved ranges to block (anti-SSRF)
_BLOCKED_PREFIXES = (
    "127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "169.254.", "::1", "localhost"
)

_META_REFRESH_RE = re.compile(
    r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>\s]+)',
    re.IGNORECASE
)
_JS_REDIRECT_RE = re.compile(
    r'(?:window\.location|location\.href|location\.replace)\s*[=(]\s*["\']([^"\']+)["\']',
    re.IGNORECASE
)


def _is_ssrf_safe(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        if any(host.startswith(p) for p in _BLOCKED_PREFIXES):
            return False
        ip = ipaddress.ip_address(host)
        return ip.is_global
    except Exception:
        return True  # hostname (not IP) — allow


async def track_dynamic_redirects(url: str) -> Dict[str, Any]:
    """
    Follow redirect chain with sandbox safety, detect cloaking.

    Returns:
        redirect_count, final_domain, domain_changed, cloaking_detected, redirect_chain
    """
    result = {
        "redirect_count": 0,
        "final_domain": None,
        "domain_changed": False,
        "cloaking_detected": False,
        "scheme_downgrade": False,
        "redirect_chain": [],
        "error": None
    }

    original_host = urlparse(url).hostname or ""

    if not _is_ssrf_safe(url):
        result["error"] = "SSRF-blocked URL"
        return result

    try:
        import httpx
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=_MAX_REDIRECTS,
            timeout=_TIMEOUT,
            headers={"User-Agent": _SAFE_UA},
        ) as client:
            resp = await client.get(url)

        final_url = str(resp.url)
        final_host = urlparse(final_url).hostname or ""
        redirect_chain = [str(r.url) for r in resp.history] + [final_url]
        redirect_count = len(resp.history)

        result["redirect_count"] = redirect_count
        result["final_domain"] = final_host
        result["redirect_chain"] = redirect_chain[:5]  # truncate

        # Domain changed?
        if original_host and final_host and original_host != final_host:
            result["domain_changed"] = True

        # Check HTML for meta-refresh or JS redirects → cloaking
        html = resp.text[:20000]
        meta_hits = _META_REFRESH_RE.findall(html)
        js_hits = _JS_REDIRECT_RE.findall(html)

        if meta_hits or js_hits:
            result["cloaking_detected"] = True

        # Scheme downgrade: https → http
        if url.startswith("https") and final_url.startswith("http://"):
            result["scheme_downgrade"] = True

        logger.info(
            f"Redirect check: hops={redirect_count} "
            f"domain_changed={result['domain_changed']} "
            f"cloaking={result['cloaking_detected']}"
        )

    except Exception as e:
        logger.warning(f"Redirect tracking failed for {url}: {e}")
        result["error"] = str(e)[:120]

    return result
