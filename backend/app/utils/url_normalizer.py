import re
from urllib.parse import urlparse, urlunparse
import httpx
from app.logger import logger

# List of common URL shorteners
SHORTENER_DOMAINS = {
    "bit.ly", "t.co", "tinyurl.com", "rebrand.ly", "is.gd", 
    "buff.ly", "goo.gl", "ow.ly", "t.ly"
}

# List of tracking parameters to stripping
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "trk", "mc_cid", "mc_eid"
}

def is_valid_url(url: str) -> bool:
    """Basic validation for URL format and protocols."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        # Only allow http and https
        if parsed.scheme not in ["http", "https"]:
            return False
        # Block internal IPs/localhost (Basic SSRF prevention)
        host = (parsed.hostname or "").lower()
        if not host or host in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
            return False
        # Prevent internal network (e.g., 10.x, 192.168.x, 172.16-31.x)
        if re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)", host):
            return False
        return True
    except Exception:
        return False

async def expand_url(url: str) -> list:
    """Follow redirects and expand shortened URLs."""
    redirect_chain = [url]
    current_url = url
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        try:
            response = await client.head(url)
            # track history
            for r in response.history:
                redirect_chain.append(str(r.url))
            redirect_chain.append(str(response.url))
        except Exception as e:
            logger.error(f"Error expanding URL {url}: {e}")
            
    return list(dict.fromkeys(redirect_chain)) # Deduplicate while preserving order

def normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking params and canonicalizing."""
    try:
        parsed = urlparse(url)
        # Lowercase host
        host = (parsed.hostname or "").lower()
        
        # Strip tracking parameters from query
        query_parts = []
        if parsed.query:
            for part in parsed.query.split("&"):
                key = part.split("=")[0]
                if key not in TRACKING_PARAMS:
                    query_parts.append(part)
        
        new_query = "&".join(query_parts)
        
        # Remove trailing slash from path if it's not the root
        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path.rstrip("/")
            
        # Reconstruct URL
        normalized = urlunparse((
            parsed.scheme,
            host,
            path,
            parsed.params,
            new_query,
            "" # Remove fragment
        ))
        return normalized
    except Exception as e:
        logger.error(f"Error normalizing URL {url}: {e}")
        return url
