import httpx
from typing import Dict, Any, List
from app.logger import logger

async def track_redirect_chain(url: str) -> dict:
    """Trace the full redirect chain for a URL."""
    chain = []
    try:
        # Reduced timeout to 2.5s for real-time performance
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(2.5, connect=1.5)
        ) as client:
            response = await client.get(url, follow_redirects=True)
            
            for r in response.history:
                chain.append({
                    "url": str(r.url),
                    "status_code": r.status_code,
                    "domain": r.url.host
                })
            
            chain.append({
                "url": str(response.url),
                "status_code": response.status_code,
                "domain": response.url.host
            })
            
            return {
                "redirect_count": len(response.history),
                "chain": chain,
                "final_url": str(response.url),
                "unique_domains_count": len(set(step["domain"] for step in chain))
            }
    except Exception as e:
        logger.error(f"Redirect tracking failed for {url}: {e}")
        return {
            "redirect_count": 0,
            "chain": [{"url": url, "status_code": None, "domain": None}],
            # Ensure callers can still proceed without KeyError
            "final_url": url,
            "unique_domains_count": 0,
            "error": str(e),
        }
    
    return {
        "redirect_count": 0,
        "chain": [],
        "error": "Unexpected exit from tracking"
    }
