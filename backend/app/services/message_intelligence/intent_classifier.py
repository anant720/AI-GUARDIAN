from typing import Dict, Any
import os
from app.logger import logger

class IntentClassifier:
    def __init__(self):
        # Lazy-loaded (large) transformer pipeline; avoid import-time downloads/startup stalls.
        self.model_name = os.getenv("INTENT_MODEL", "facebook/bart-large-mnli")
        self._classifier = None
            
        self.candidate_labels = [
            "account_verification",
            "payment_request",
            "crypto_investment",
            "job_offer",
            "delivery_scam",
            "romance_scam",
            "general_information",
            "greeting"
        ]

    def _ensure_loaded(self) -> None:
        if self._classifier is not None:
            return
        try:
            from transformers import pipeline  # heavy import
            logger.info(f"Loading intent classifier model: {self.model_name}")
            self._classifier = pipeline("zero-shot-classification", model=self.model_name)
            logger.info("Intent classifier model ready")
        except Exception as e:
            logger.error(f"Failed to load intent classifier model: {e}")
            self._classifier = False  # sentinel: tried and failed

    def classify(self, text: str) -> Dict[str, Any]:
        """Classify the intent of the message."""
        if not text:
            return {"intent": "unknown", "confidence": 0.0}

        self._ensure_loaded()
        if self._classifier is False:
            return {"intent": "unknown", "confidence": 0.0}
            
        try:
            result = self._classifier(text, candidate_labels=self.candidate_labels)
            # The result is sorted by score
            top_intent = result['labels'][0]
            top_score = result['scores'][0]
            
            return {
                "intent": top_intent,
                "confidence": float(top_score)
            }
        except Exception as e:
            logger.error(f"Error during intent classification: {e}")
            return {"intent": "unknown", "confidence": 0.0}

intent_classifier = IntentClassifier()


def classify_intent(text: str) -> Dict[str, Any]:
    """Public module-level function: classify the intent of a message."""
    return intent_classifier.classify(text)
