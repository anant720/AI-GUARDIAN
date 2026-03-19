from typing import Dict, Optional, Any, List
from app.logger import logger

class ImpersonationDetector:
    def __init__(self):
        # Common brands impersonated in phishing attacks
        self.brands: List[str] = [
            "paypal",
            "amazon",
            "google",
            "microsoft",
            "apple",
            "netflix",
            "meta",
            "facebook",
            "instagram",
            "whatsapp",
            "bank of america",
            "chase",
            "wells fargo",
            "dhl",
            "fedex",
            "ups",
            "usps"
        ]

    def detect(self, normalized_text: str) -> Dict[str, Any]:
        """
        Check if the message pretends to represent a brand.
        Returns the brand name and a confidence score.
        """
        if not normalized_text:
            return {"brand": None, "confidence": 0.0}
            
        try:
            for brand in self.brands:
                if brand in normalized_text:
                    # Basic matching: if brand is found in the text, we return it with high confidence.
                    # In more advanced versions, this could use NER (Named Entity Recognition).
                    return {
                        "brand": brand,
                        "confidence": 0.92
                    }
                    
            return {"brand": None, "confidence": 0.0}
        except Exception as e:
            logger.error(f"Error during brand impersonation detection: {e}")
            return {"brand": None, "confidence": 0.0}

impersonation_detector = ImpersonationDetector()


def detect_impersonation(text: str) -> Dict[str, Any]:
    """Public module-level function: detect brand impersonation in a message."""
    return impersonation_detector.detect(text)
