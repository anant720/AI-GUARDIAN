from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

PHISHING_KEYWORDS = [
    "verify account", "update payment", "secure login", "confirm identity", 
    "wallet verification", "crypto transfer", "unauthorized access",
    "suspend", "action required", "billing", "re-verify", "validation"
]

def analyze_keywords(url_path: str, page_title: str, html_content: str) -> dict:
    """Scan URL and page content for phishing keywords."""
    found_keywords: list[str] = []
    
    content_text = ""
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        content_text: str = str(soup.get_text()).lower()
        
    page_title_str: str = str(page_title).lower() if page_title else ""
    url_path_str: str = str(url_path).lower() if url_path else ""
    
    for kw in PHISHING_KEYWORDS:
        if kw in url_path_str or kw in page_title_str or kw in content_text:
            found_keywords.append(kw)
            
    return {
        "keyword_count": len(found_keywords),
        "found_keywords": list(set(found_keywords)),
        "is_high_keyword_risk": len(found_keywords) >= 3
    }
