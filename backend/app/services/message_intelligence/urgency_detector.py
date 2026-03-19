from typing import List, Dict, Any
from app.logger import logger

class UrgencyDetector:
    def __init__(self):
        # List of urgency-indicating keywords and phrases
        self.urgent_keywords = {
            "immediately": 0.8,
            "urgent": 0.9,
            "act now": 0.9,
            "last warning": 1.0,
            "account suspended": 1.0,
            "limited time": 0.7,
            "asap": 0.8,
            "quick": 0.5,
            "hurry": 0.7,
            "warning": 0.8,
            "action required": 0.9,
            "final notice": 1.0,
            "expire": 0.7
        }

    def detect(self, normalized_text: str) -> float:
        """
        Detect urgency in the normalized message text and return a score between 0.0 and 1.0.
        """
        if not normalized_text:
            return 0.0
            
        try:
            score = 0.0
            matches = 0
            
            for keyword, weight in self.urgent_keywords.items():
                if keyword in normalized_text:
                    score += weight
                    matches += 1
                    
            # Basic sentiment/exclamation intensity
            exclamation_count = normalized_text.count("!")
            if exclamation_count > 0:
                score += min(0.3, float(exclamation_count * 0.1))
                
            # Cap the score at 1.0
            final_score = min(1.0, score)
            return float(round(final_score, 2))
        except Exception as e:
            logger.error(f"Error during urgency detection: {e}")
            return 0.0

urgency_detector = UrgencyDetector()


def detect_urgency(text: str) -> float:
    """Public module-level function: detect urgency in a message."""
    return urgency_detector.detect(text)
