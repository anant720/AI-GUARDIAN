from typing import Dict, Any
from app.logger import logger

class FinancialScamDetector:
    def __init__(self):
        # Indicators for financial scams mapped to base scores
        self.financial_indicators: Dict[str, float] = {
            "crypto investment": 0.9,
            "bank verification": 0.8,
            "refund": 0.7,
            "gift card": 0.8,
            "bitcoin": 0.6,
            "ethereum": 0.6,
            "transfer funds": 0.9,
            "wire transfer": 0.8,
            "claim prize": 0.9,
            "won lottery": 1.0,
            "send money": 0.8,
            "get paid": 0.6
        }

    def detect(self, normalized_text: str) -> float:
        """
        Detect probability of financial scam in the normalized text.
        Returns a score between 0.0 and 1.0.
        """
        if not normalized_text:
            return 0.0
            
        try:
            score = 0.0
            
            for phrase, weight in self.financial_indicators.items():
                if phrase in normalized_text:
                    score += weight
                    
            final_score = min(1.0, score)
            return float(round(final_score, 2))
        except Exception as e:
            logger.error(f"Error during financial scam detection: {e}")
            return 0.0

financial_scam_detector = FinancialScamDetector()


def detect_financial_scam(text: str) -> float:
    """Public module-level function: detect financial scam probability in a message."""
    return financial_scam_detector.detect(text)
