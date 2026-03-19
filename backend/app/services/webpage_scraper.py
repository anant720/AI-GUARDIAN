import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any
from app.logger import logger

async def fetch_webpage_content(url: str) -> dict:
    """Fetch and extract content from a webpage safely."""
    try:
        # Reduced timeout to 2.5s for real-time performance
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(2.5, connect=1.5),
            headers={"User-Agent": "AI-Guardian-Bot/1.0"}
        ) as client:
            response = await client.get(url, follow_redirects=True)
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Simple content extraction
            title = soup.title.string if soup.title else ""
            meta_description = ""
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag:
                meta_description = desc_tag.get("content", "")
                
            # Extract forms and scripts (basic)
            forms = soup.find_all("form")
            scripts = soup.find_all("script")
            
            return {
                "status_code": response.status_code,
                "title": title.strip() if title else "",
                "meta_description": meta_description,
                "html_content": html[:50000], # Limit content size
                "forms_count": len(forms),
                "scripts_count": len(scripts)
            }
    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")
        return {
            "error": str(e)
        }
        
    return {
        "error": "Unexpected exit from scraper"
    }
