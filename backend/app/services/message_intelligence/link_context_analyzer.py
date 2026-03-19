import tldextract
from typing import Dict, Optional, List, Any
from app.logger import logger

class LinkContextAnalyzer:
    def analyze(self, normalized_text: str, urls: List[str], brand_detected: Optional[str]) -> Dict[str, Any]:
        """
        Analyze logic between message text and URL.
        Checks if brand mentioned in text matches the URL domain.
        """
        results: Dict[str, Any] = {
            "brand_text_match": brand_detected,
            "domain_match": None,
            "mismatch_detected": False
        }
        
        if not urls or not brand_detected:
            return results
            
        try:
            # We'll just check the first URL for simplicity
            url = urls[0]
            extracted = tldextract.extract(url)
            domain = extracted.domain.lower() if extracted.domain else ""
            
            if brand_detected.lower() == domain:
                results["domain_match"] = True
                results["mismatch_detected"] = False
            else:
                results["domain_match"] = False
                results["mismatch_detected"] = True
                
        except Exception as e:
            # Handle malformed extraction
            logger.error(f"Error during link context analysis: {e}")
            results["domain_match"] = False
            results["mismatch_detected"] = True
            
        return results

link_context_analyzer = LinkContextAnalyzer()


def analyze_link_context(text: str, urls: List[str], brand: Optional[str]) -> Dict[str, Any]:
    """Public module-level function: analyze link context in a message."""
    return link_context_analyzer.analyze(text, urls, brand)
